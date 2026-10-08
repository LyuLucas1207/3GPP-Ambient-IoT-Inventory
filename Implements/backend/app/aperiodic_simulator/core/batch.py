"""Seeded multi-episode batches (paper_batch runtime mode).

Episode i of every compared strategy uses seed ``base_seed + i``; the
population, initial DCM phases and all random streams are derived from that
seed alone, so compared strategies see the same scenario realization.
"""

import os
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

import numpy as np

from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.analysis.metrics import CURVE_STEP_S, aggregate, episode_curve


@dataclass
class BatchResult:
    label: str
    cfg: EpisodeConfig
    times: np.ndarray
    episodes: list[dict]
    curves: list[np.ndarray]
    aggregate: dict
    controller_traces: list[list[dict]]


def _one(args) -> tuple[dict, np.ndarray, list[dict]]:
    cfg, t_curve, step, keep_ctrl, ctrl_factory = args
    from app.aperiodic_simulator.core.runner import run_episode

    ctrl = ctrl_factory(cfg) if ctrl_factory else None
    res = run_episode(cfg, controller=ctrl)
    _, curve = episode_curve(res.episode, t_curve, step)
    hist = res.controller_history if keep_ctrl else []
    return res.metrics, curve.astype(np.float32), hist


def default_workers() -> int:
    return max(1, min(8, (os.cpu_count() or 2) - 1))


def run_batch(
    cfg: EpisodeConfig,
    episodes: int,
    base_seed: int = 0,
    label: str = "",
    workers: int | None = None,
    t_curve: float | None = None,
    step: float = CURVE_STEP_S,
    keep_controller_traces: int = 0,
    controller_factory=None,
) -> BatchResult:
    t_curve = cfg.t_max_s if t_curve is None else t_curve
    jobs = [
        (cfg.with_(seed=base_seed + i), t_curve, step, i < keep_controller_traces, controller_factory)
        for i in range(episodes)
    ]
    w = workers or default_workers()
    if w <= 1 or episodes == 1:
        outs = [_one(j) for j in jobs]
    else:
        with ProcessPoolExecutor(max_workers=w) as ex:
            outs = list(ex.map(_one, jobs))
    metrics = [o[0] for o in outs]
    curves = [o[1] for o in outs]
    times = np.arange(0.0, t_curve + 1e-12, step)
    return BatchResult(
        label=label,
        cfg=cfg,
        times=times,
        episodes=metrics,
        curves=curves,
        aggregate=aggregate(metrics, curves),
        controller_traces=[o[2] for o in outs if o[2]],
    )
