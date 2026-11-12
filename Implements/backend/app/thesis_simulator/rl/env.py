"""``MultiReaderInventoryEnv``: one step = one frame of the next reader.

The thesis engine is event driven: the reader with the earliest clock runs
the next frame. The environment follows the same order. Before each frame it
returns that reader's observation (``rl.features``); the action sets the
reader's (K, p*) for that frame; the reward is credited to that decision.

Readers act interleaved, so the agent seen by a single-agent learner is the
shared policy over the whole system (parameter sharing). A recurrent policy
would need one hidden state per reader; the stacked frame history in the
observation replaces it (``training/algos/mappo.py`` keeps per-reader slots).

Reward of the frame of reader r (``beta`` weights local against team):

    local = ((1 - alpha) * new_ids_r - alpha * collisions_r) / t_frame
    team  = new IDs of all readers since r's previous decision / elapsed time
    reward = (beta * local + (1 - beta) * team) / RATE_SCALE

``alpha`` plays the role of the single-reader paper's Eq. (8) weight on
collisions; ``RATE_SCALE`` keeps rewards O(1).

Each ``reset`` samples a deployment from the environment spec (``DEFAULT_SPEC``):
active readers, their subset of the 18-reader lattice, start offsets,
resource policy, scheme, device count and subtype mix (domain randomization).
"""

from __future__ import annotations

import copy
import math
from typing import Any

import gymnasium as gym
import numpy as np

from app.thesis_simulator.inventory.controller import Decision
from app.thesis_simulator.inventory.episode import (
    EpisodeState,
    _active_readers,
    _done_serving,
    _pick_reader,
    build_episode,
    finish_episode,
    mark_unreachable,
    step_episode,
)
from app.thesis_simulator.inventory.events import EventEmitter
from app.thesis_simulator.inventory.headless import synthetic_scene
from app.thesis_simulator.inventory.state import EpisodeConfig, ReaderState
from app.thesis_simulator.rl.features import ACTION_DIM, FRAME_FEATURES, OBS_DIM, P_FLOOR, apply_action, observation
from app.thesis_simulator.scenario import DEFAULT_ACTIVE_BS_XY, default_bs_positions

RATE_SCALE = 100.0
GLOBAL_DIM = 6 + FRAME_FEATURES

DEFAULT_SPEC: dict[str, Any] = {
    "n_devices": [100, 600],
    "readers": [2, 2],  # inclusive range of active readers
    "subset": "spread",  # spread (farthest-point from the TR's active reader) | random
    "offsets": ["none"],  # any of: none | random | groups
    "offset_max_s": 2.0,
    "resource_modes": ["independent"],
    "schemes": ["aperiodic"],
    "subtype_mix": "uniform",  # uniform | random (homogeneous with probability 0.5)
    "alpha": 0.5,
    "beta": 0.5,
    "t_max_s": 120.0,
    "stall_timeout_s": 120.0,
    "max_frames": 20_000,
    "k_initial": 32,
    "f_freq": None,
}


def spread_subset(k: int) -> list[tuple[float, float]]:
    lattice = default_bs_positions()
    k = max(1, min(k, len(lattice)))
    chosen = [min(lattice, key=lambda p: math.dist(p, DEFAULT_ACTIVE_BS_XY))]
    while len(chosen) < k:
        rest = [p for p in lattice if p not in chosen]
        chosen.append(max(rest, key=lambda p: (min(math.dist(p, c) for c in chosen), -p[1], -p[0])))
    return chosen


def outcome(st: EpisodeState, successes: int, slots: int) -> dict[str, Any]:
    """Episode metrics shared by the environment and ``training/evaluate.py``."""
    w = st.world
    t = w.identified_t
    t = np.sort(t[np.isfinite(t)])
    reachable = int(w.N - (w.dropped & (w.drop_cause == 1)).sum())
    need = int(math.ceil(0.99 * reachable))
    return {
        "identified": int(w.identified.sum()),
        "reachable": reachable,
        "identified_fraction": float(w.identified.sum() / reachable) if reachable else 1.0,
        "t99": float(t[need - 1]) if need and t.size >= need else None,
        "t_mean": float(t.mean()) if t.size else None,
        "sim_time": float(st.sim_time),
        "frames": int(st.rounds_total),
        "resource_efficiency": successes / slots if slots else None,
    }


class AgentController:
    """Controller the environment installs on every reader: it applies the
    action the agent chose for the current frame."""

    name = "agent"

    def __init__(self, env: "MultiReaderInventoryEnv") -> None:
        self.env = env
        self.k_prev: int | None = None
        self.p_prev: float | None = None

    def decide(self, reader: ReaderState, config: EpisodeConfig, group: int, f_r: int) -> Decision:
        from app.thesis_simulator.inventory.controller import _cold_k, _scale_to_grant

        if self.k_prev is None:
            self.k_prev = _scale_to_grant(_cold_k(config), config.consts.f_freq, f_r)
            self.p_prev = max(P_FLOOR, float(reader.estimator.p_star(self.k_prev, group)))
        a = self.env._pending
        if a is None:
            return Decision(k=self.k_prev, pstar=self.p_prev or 1.0)
        k, p, m, q = apply_action(a, self.k_prev, self.p_prev or 1.0, f_r, int(config.consts.k_max))
        self.k_prev, self.p_prev = k, p
        return Decision(k=k, pstar=p, info={"m": m, "q": q})


class MultiReaderInventoryEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(self, spec: dict[str, Any] | None = None) -> None:
        super().__init__()
        self.cfg = {**DEFAULT_SPEC, **(spec or {})}
        self.observation_space = gym.spaces.Box(0.0, 1.0, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(ACTION_DIM,), dtype=np.float32)
        self.state: EpisodeState | None = None
        self.current: ReaderState | None = None
        self._pending = None
        self._emit = EventEmitter(run_id=0)
        self._frames = 0
        self._succ = 0
        self._k_sum = 0
        self._last_decision: dict[int, tuple[float, int]] = {}
        self.episode_info: dict[str, Any] = {}

    # ---------------------------------------------------------- sampling
    def sample_deployment(self, spec: dict[str, Any]) -> tuple[dict[str, Any], EpisodeConfig, dict[str, Any]]:
        rng = self.np_random
        lo, hi = spec["readers"]
        n_readers = int(rng.integers(lo, hi + 1))
        lattice = default_bs_positions()
        if spec["subset"] == "random":
            idx = rng.choice(len(lattice), size=n_readers, replace=False)
            xy = [lattice[int(i)] for i in sorted(idx)]
        else:
            xy = spread_subset(n_readers)
        n_lo, n_hi = spec["n_devices"]
        n_devices = int(rng.integers(n_lo, n_hi + 1))
        mix = (1 / 3, 1 / 3, 1 / 3)
        if spec["subtype_mix"] == "random" and rng.random() < 0.5:
            only = int(rng.integers(0, 3))
            mix = tuple(float(i == only) for i in range(3))
        scene = synthetic_scene(n_devices, reader_xy=xy, seed=int(rng.integers(0, 2**31 - 1)), subtype_mix=mix)
        ids = [int(p["id"]) for p in scene["placements"] if p["kind"] == "radar"]
        offsets_kind = str(rng.choice(spec["offsets"]))
        if offsets_kind == "random":
            offsets = {str(r): float(rng.uniform(0.0, spec["offset_max_s"])) for r in ids}
        elif offsets_kind == "groups":
            offsets = {str(r): (spec["offset_max_s"] if i % 2 else 0.0) for i, r in enumerate(ids)}
        else:
            offsets = {}
        scheme = str(rng.choice(spec["schemes"]))
        mode = str(rng.choice(spec["resource_modes"]))
        cfg = {
            "k_initial": spec["k_initial"], "adaptive_k": True, "max_time_s": spec["t_max_s"],
            "stall_timeout_s": spec["stall_timeout_s"], "reader_start_offsets": offsets,
            "use_grouping": scheme == "periodic", "g": 2, "resource": {"mode": mode},
            **({"f_freq": spec["f_freq"]} if spec.get("f_freq") else {}),
        }
        info = {"readers": n_readers, "devices": n_devices, "offsets": offsets_kind, "scheme": scheme, "resource": mode, "mix": list(mix)}
        return scene, EpisodeConfig.from_json(scheme, cfg), info

    # ---------------------------------------------------------- gym API
    def reset(self, *, seed: int | None = None, options: dict[str, Any] | None = None):
        super().reset(seed=seed)
        spec = {**self.cfg, **((options or {}).get("spec") or {})}
        for _ in range(50):
            scene, config, info = self.sample_deployment(spec)
            engine_rng = np.random.default_rng(int(self.np_random.integers(0, 2**63 - 1)))
            state = build_episode(scene, config, engine_rng)
            if not state.readers or state.world.N == 0:
                continue
            for r in state.readers:
                r.controller = AgentController(self)
            mark_unreachable(state, self._emit)
            self._emit.discard()
            self.state = state
            self._frames = 0
            self._succ = self._k_sum = 0
            self._pending = None
            self._last_decision = {}
            self.episode_info = info
            self.current = self._peek()
            if self.current is not None:
                return observation(self.current, state.config), {**info, **self._info()}
        raise RuntimeError("could not sample a deployment with something to identify")

    def _peek(self) -> ReaderState | None:
        st = self.state
        assert st is not None
        active = _active_readers(st)
        if st.world.N == 0 or _done_serving(st) or not active or st.stalled():
            return None
        return _pick_reader(st, active)

    def _info(self) -> dict[str, Any]:
        st = self.state
        r = self.current
        return {
            "reader_id": None if r is None else r.reader_id,
            "slot": None if r is None else int(r.context.get("slot", 0)),
            "identified": int(st.world.identified.sum()) if st else 0,
            "t": float(st.sim_time) if st else 0.0,
        }

    def step(self, action):
        st, reader = self.state, self.current
        assert st is not None and reader is not None, "call reset() first"
        alpha, beta = float(self.cfg["alpha"]), float(self.cfg["beta"])
        before = int(st.world.identified.sum())
        self._pending = np.asarray(action, dtype=float)
        result = step_episode(st, self._emit)
        self._emit.discard()
        self._pending = None
        self._frames += 1
        reward = 0.0
        if result is not None:
            self._succ += result.success
            self._k_sum += result.k
        if result is not None and result.t_frame > 0:
            local = ((1 - alpha) * result.identified - alpha * result.collision) / result.t_frame
            t_end = reader.clock_s
            t_prev, n_prev = self._last_decision.get(reader.reader_id, (t_end - result.t_frame, before))
            now = int(st.world.identified.sum())
            team = (now - n_prev) / max(1e-6, t_end - t_prev)
            self._last_decision[reader.reader_id] = (t_end, now)
            reward = (beta * local + (1 - beta) * team) / RATE_SCALE
        self.current = self._peek() if result is not None else None
        terminated = truncated = False
        if self.current is None:
            finish_episode(st, self._emit)
            self._emit.discard()
            w = st.world
            terminated = bool(w.identified.sum() + (w.dropped & (w.drop_cause == 1)).sum() >= w.N)
            truncated = not terminated
        elif self._frames >= int(self.cfg["max_frames"]):
            truncated = True
        obs = observation(self.current, st.config) if self.current is not None else np.zeros(OBS_DIM, dtype=np.float32)
        info = self._info()
        if result is not None:
            info.update({"k": result.k, "pstar": result.pstar, "new_ids": result.identified})
        if terminated or truncated:
            info["episode_summary"] = self.summary()
        return obs, float(reward), terminated, truncated, info

    # ---------------------------------------------------------- extras
    def global_state(self) -> np.ndarray:
        """Centralized-critic input (CTDE): true progress plus the readers' mean last frame."""
        st = self.state
        g = np.zeros(GLOBAL_DIM, dtype=np.float32)
        if st is None:
            return g
        w = st.world
        span = np.maximum(w.Ecap - w.Eoff, 1e-12)
        g[0] = w.identified.mean() if w.N else 1.0
        g[1] = min(1.0, st.sim_time / max(1e-9, float(self.cfg["t_max_s"])))
        g[2] = len(st.readers) / 18.0
        g[3] = sum(r.stopped or r.exhausted for r in st.readers) / max(1, len(st.readers))
        g[4] = float(w.on.mean()) if w.N else 0.0
        g[5] = float(np.clip((w.E - w.Eoff) / span, 0.0, 1.0).mean()) if w.N else 0.0
        frames = [observation(r, st.config)[:FRAME_FEATURES] for r in st.readers if r.history]
        if frames:
            g[6:] = np.mean(frames, axis=0)
        return g

    def summary(self) -> dict[str, Any]:
        if self.state is None:
            return {}
        return {**self.episode_info, **outcome(self.state, self._succ, self._k_sum)}

    def clone_cfg(self) -> dict[str, Any]:
        return copy.deepcopy(self.cfg)
