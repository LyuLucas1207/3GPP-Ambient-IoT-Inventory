"""Inventory-ratio curves and T50/T90/T95/T99."""

import numpy as np

from app.common.metrics import first_time_at_or_above, inventory_curve, mae_rmse

__all__ = ["first_time_at_or_above", "inventory_curve", "mae_rmse", "summarize"]


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
