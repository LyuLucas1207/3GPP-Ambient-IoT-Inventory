"""Database-free episode driver for sweeps, RL environments and tests.

The live runner (``live.py``) persists every frame to PostgreSQL. Batch work
(termination sweeps, resource-policy sweeps, RL rollouts) only needs the
per-round statistics and the final device arrays, so this module runs the
same ``build_episode`` / ``step_episode`` / ``finish_episode`` loop with the
event buffer discarded after every frame.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from app.simulator_thesis.inventory.episode import (
    EpisodeState,
    build_episode,
    finish_episode,
    mark_unreachable,
    step_episode,
)
from app.simulator_thesis.inventory.events import EventEmitter
from app.simulator_thesis.inventory.frame import FrameResult
from app.simulator_thesis.inventory.state import EpisodeConfig
from app.simulator_thesis.scenario import HALL_HEIGHT_M, HALL_WIDTH_M, default_bs_positions

ROUND_FIELDS = (
    "reader_id", "round_index", "t_start_s", "t_end_s", "k_estimate", "pstar",
    "success_count", "collision_count", "empty_count", "served", "n_done_total",
)


@dataclass
class HeadlessResult:
    state: EpisodeState
    rounds: list[dict[str, Any]] = field(default_factory=list)
    frames: int = 0

    @property
    def identified(self) -> int:
        return int(self.state.world.identified.sum())

    def identification_times(self) -> np.ndarray:
        t = self.state.world.identified_t
        return np.sort(t[np.isfinite(t)])

    def t_quantile(self, q: float) -> float | None:
        """Time by which ``q`` of the reachable devices were identified (T99 for q=0.99)."""
        w = self.state.world
        reachable = int(w.N - (w.dropped & (w.drop_cause == 1)).sum())
        need = int(math.ceil(q * reachable))
        times = self.identification_times()
        if need <= 0:
            return 0.0
        if times.size < need:
            return None
        return float(times[need - 1])


def _round_dict(row: Any) -> dict[str, Any]:
    out = {name: getattr(row, name) for name in ROUND_FIELDS}
    out["metadata"] = row.metadata_json or {}
    return out


def run_headless(
    snapshot: dict[str, Any],
    config: EpisodeConfig,
    seed: int,
    *,
    keep_rounds: bool = True,
    max_frames: int | None = None,
    on_frame: Callable[[EpisodeState, FrameResult], None] | None = None,
) -> HeadlessResult:
    rng = np.random.default_rng(seed)
    state = build_episode(snapshot, config, rng)
    emit = EventEmitter(run_id=0)
    mark_unreachable(state, emit)
    emit.discard()
    return drive(state, keep_rounds=keep_rounds, max_frames=max_frames, on_frame=on_frame)


def drive(
    state: EpisodeState,
    *,
    keep_rounds: bool = True,
    max_frames: int | None = None,
    on_frame: Callable[[EpisodeState, FrameResult], None] | None = None,
    finish: bool = True,
) -> HeadlessResult:
    """Step an already built (or checkpoint-restored) episode; ``finish=False``
    leaves it open after ``max_frames`` so it can be checkpointed."""
    emit = EventEmitter(run_id=0)
    emit.frame_seq = state.frame_seq
    out = HeadlessResult(state=state)
    while max_frames is None or out.frames < max_frames:
        result = step_episode(state, emit)
        if result is None:
            break
        out.frames += 1
        if keep_rounds:
            out.rounds.extend(_round_dict(r) for r in emit._rounds)
        emit.discard()
        if on_frame is not None:
            on_frame(state, result)
    if finish:
        finish_episode(state, emit)
        emit.discard()
    return out


def synthetic_scene(
    n_devices: int,
    *,
    reader_xy: list[tuple[float, float]] | None = None,
    width_m: float = HALL_WIDTH_M,
    height_m: float = HALL_HEIGHT_M,
    seed: int = 0,
    subtype_mix: tuple[float, float, float] = (1 / 3, 1 / 3, 1 / 3),
    reader_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """A scene snapshot in the same shape the API stores (``placements`` list).

    Devices are uniform over the hall; readers default to the 18-BS lattice.
    Device ids start at 1, reader ids at 100000 so they never collide.
    """
    rng = np.random.default_rng(seed)
    xy = reader_xy if reader_xy is not None else default_bs_positions()
    probs = np.asarray(subtype_mix, dtype=float)
    probs = probs / probs.sum()
    subtypes = rng.choice(np.array(["1", "2a", "2b"]), size=n_devices, p=probs)
    xs = rng.uniform(0.0, width_m, size=n_devices)
    ys = rng.uniform(0.0, height_m, size=n_devices)
    placements: list[dict[str, Any]] = [
        {"id": i + 1, "kind": "device", "subtype": str(subtypes[i]), "x_m": float(xs[i]), "y_m": float(ys[i]), "params": {}}
        for i in range(n_devices)
    ]
    for j, (x, y) in enumerate(xy):
        placements.append(
            {"id": 100_000 + j, "kind": "radar", "subtype": None, "x_m": float(x), "y_m": float(y), "params": dict(reader_params or {})}
        )
    return {"width_m": width_m, "height_m": height_m, "placements": placements}


def reader_ids(snapshot: dict[str, Any]) -> list[int]:
    return [int(p["id"]) for p in snapshot.get("placements", []) if p.get("kind") == "radar"]


def fingerprint(result: HeadlessResult) -> str:
    """Stable digest of an episode's outcome, used by the regression tests."""
    w = result.state.world
    h = hashlib.sha256()
    for arr in (np.nan_to_num(w.identified_t, nan=-1.0), w.identified_by, w.depletions, w.attempts, w.drop_cause, w.E):
        h.update(np.ascontiguousarray(arr).tobytes())
    for r in result.rounds:
        h.update(repr(tuple(r[k] for k in ROUND_FIELDS)).encode())
    return h.hexdigest()
