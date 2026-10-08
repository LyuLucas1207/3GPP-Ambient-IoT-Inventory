"""Paper-independent inventory-curve metrics shared by both simulators."""

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


def mae_rmse(sim_t: np.ndarray, sim_y: np.ndarray, ref_t: np.ndarray, ref_y: np.ndarray) -> dict:
    y_ref = np.interp(sim_t, ref_t, ref_y)
    err = sim_y - y_ref
    return {
        "mae": float(np.mean(np.abs(err))),
        "rmse": float(np.sqrt(np.mean(err**2))),
    }
