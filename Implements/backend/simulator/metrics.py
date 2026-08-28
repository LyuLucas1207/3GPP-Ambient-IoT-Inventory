"""Inventory-ratio curves and T50/T90/T95/T99."""

from typing import Iterable

import numpy as np


def inventory_curve(
    completion_s: np.ndarray,
    n_devices: int,
    t_max_s: float,
    step_s: float = 0.05,
) -> tuple[np.ndarray, np.ndarray]:
    times = np.arange(0.0, t_max_s + 1e-12, step_s)
    valid = completion_s[np.isfinite(completion_s)]
    if valid.size == 0:
        return times, np.zeros_like(times)
    valid.sort()
    counts = np.searchsorted(valid, times, side="right")
    ratio = 100.0 * counts / n_devices
    return times, ratio


def first_time_at_or_above(times: np.ndarray, ratio: np.ndarray, target: float) -> float | None:
    hits = np.flatnonzero(ratio >= target - 1e-9)
    if hits.size == 0:
        return None
    return float(times[hits[0]])


def summarize(completion_s: np.ndarray, n_devices: int, t_max_s: float) -> dict:
    times, ratio = inventory_curve(completion_s, n_devices, t_max_s)
    n_done = int(np.isfinite(completion_s).sum())
    return {
        "t50_s": first_time_at_or_above(times, ratio, 50.0),
        "t90_s": first_time_at_or_above(times, ratio, 90.0),
        "t95_s": first_time_at_or_above(times, ratio, 95.0),
        "t99_s": first_time_at_or_above(times, ratio, 99.0),
        "final_ratio_pct": float(100.0 * n_done / n_devices) if n_devices else 0.0,
        "n_inventoried": n_done,
        "times_s": times,
        "ratio_pct": ratio,
    }


def mae_rmse(sim_t: np.ndarray, sim_y: np.ndarray, ref_t: np.ndarray, ref_y: np.ndarray) -> dict:
    y_ref = np.interp(sim_t, ref_t, ref_y)
    err = sim_y - y_ref
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
    }
