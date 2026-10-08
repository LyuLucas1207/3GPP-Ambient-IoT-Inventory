"""Gymnasium environment: one step = one CBRA round of the proposed aperiodic protocol.

reset() samples an episode from the paper's training distribution (Sec. V-A3):
    N_tot ~ U{100 .. 15000}
    homogeneous (one random type) or heterogeneous (all three types) episodes
    L_1 ~ U{1, 2, 4, 8, 16, 32},  p_1 ~ U(0, 1]
    fresh layout / channel / initial availability (new population seed)
    multi-source harvesting (the paper trains there only)
and plays round 1 with (L_1, p_1); the returned observation is that round's
Eq. (5) vector, so every agent action is a correction to a realised round.

step(action) maps the action to (m, q) and (L_s, p_s) through
``rl.transforms``, runs one round and returns the paper reward (Eq. 8, which
uses the hidden C2 count) computed by the engine.

terminated: every device in N_eff identified. truncated: t >= t_max_s or the
round cap.
"""

import gymnasium as gym
import numpy as np

from app.aperiodic_simulator.core.config import Assumptions, EpisodeConfig, SystemParams
from app.aperiodic_simulator.physics.energy import compute_global_lmax
from app.aperiodic_simulator.rl.transforms import OBS_DIM, action_to_multipliers, apply_action, normalize_observation
from app.aperiodic_simulator.core.simulation import Episode
from app.aperiodic_simulator.core.states import ControllerName, HarvestingScenario, PagingMode

L_INITIAL_CHOICES = (1, 2, 4, 8, 16, 32)
TYPE_NAMES = ("1", "2a", "2b")

TRAINING_DISTRIBUTION = {
    "n_tot": [100, 15000],
    "homogeneous_probability": 0.5,
    "homogeneous_type": "uniform over {1, 2a, 2b}",
    "L_initial": list(L_INITIAL_CHOICES),
    "p_initial": "U(0, 1]",
    "harvesting_scenario": "multi_source",
    "population_seed": "fresh per episode from the env RNG",
}


class AperiodicInventoryEnv(gym.Env):
    metadata = {"render_modes": []}

    def __init__(
        self,
        alpha: float = 0.5,
        scenario: HarvestingScenario | str = HarvestingScenario.MULTI_SOURCE,
        n_range: tuple[int, int] = (100, 15000),
        homogeneous_probability: float = 0.5,
        t_max_s: float = 1200.0,
        max_rounds: int = 20_000,
        fixed: dict | None = None,
    ):
        super().__init__()
        self.system = SystemParams()
        self.assumptions = Assumptions()
        self.F = self.system.F
        self.L_max = compute_global_lmax(self.system)
        self.p_floor = self.assumptions.p_floor
        self.alpha = alpha
        self.scenario = HarvestingScenario(scenario)
        self.n_range = n_range
        self.homogeneous_probability = homogeneous_probability
        self.t_max_s = t_max_s
        self.max_rounds = max_rounds
        self.fixed = fixed or {}
        self.observation_space = gym.spaces.Box(0.0, 1.0, shape=(OBS_DIM,), dtype=np.float32)
        self.action_space = gym.spaces.Box(-1.0, 1.0, shape=(2,), dtype=np.float32)
        self.ep: Episode | None = None
        self.L = 1
        self.p = 1.0

    def sample_config(self) -> EpisodeConfig:
        rng = self.np_random
        f = self.fixed
        n_tot = int(f.get("n_tot", rng.integers(self.n_range[0], self.n_range[1] + 1)))
        if "type_mix" in f:
            mix = f["type_mix"]
        else:
            mix = str(rng.choice(TYPE_NAMES)) if rng.random() < self.homogeneous_probability else "mixed"
        L0 = int(f.get("L_initial", rng.choice(L_INITIAL_CHOICES)))
        p0 = float(f.get("p_initial", 1.0 - rng.random()))
        seed = int(f.get("seed", rng.integers(0, 2**31 - 1)))
        return EpisodeConfig(
            n_tot=n_tot,
            seed=seed,
            harvesting_scenario=self.scenario,
            paging_mode=PagingMode.APERIODIC,
            controller=ControllerName.RECURRENT_PPO,
            L_initial=L0,
            L_fixed=L0,
            p_initial=p0,
            alpha=self.alpha,
            t_max_s=self.t_max_s,
            max_rounds=self.max_rounds,
            type_mix=mix,
            system=self.system,
            assumptions=self.assumptions,
        )

    def _obs(self, rec) -> np.ndarray:
        return normalize_observation(rec.observation(), self.F, self.L_max)

    def reset(self, *, seed=None, options=None):
        super().reset(seed=seed)
        for _ in range(100):
            cfg = self.sample_config()
            ep = Episode(cfg)
            if ep.n == 0:
                continue
            self.L, self.p = max(1, min(cfg.L_initial, self.L_max)), max(cfg.p_initial, self.p_floor)
            rec = ep.step(self.L, self.p)
            if not ep.finished:
                self.ep = ep
                return self._obs(rec), {"n_tot": cfg.n_tot, "n_eff": ep.n, "type_mix": cfg.type_mix, "L1": self.L, "p1": self.p}
            if self.fixed:
                break
        raise RuntimeError("could not sample a non-trivial episode")

    def step(self, action):
        assert self.ep is not None, "call reset() first"
        m, q = action_to_multipliers(action)
        self.L, self.p = apply_action(m, q, self.L, self.p, self.L_max, self.p_floor)
        rec = self.ep.step(self.L, self.p)
        terminated = self.ep.n_done >= self.ep.n
        truncated = (not terminated) and self.ep.finished
        info = {"m": m, "q": q, "L": self.L, "p": self.p, "C2": rec.C2, "n_done": self.ep.n_done, "t": self.ep.t}
        return self._obs(rec), float(rec.reward), terminated, truncated, info
