"""Device arrays and visualization-state helpers."""

import numpy as np

from simulator.config import DONE, OFF, ON, SLEEP, TX, VIZ_ACCESS, VIZ_COLLISION, VIZ_DONE, VIZ_OFF, VIZ_ON, VIZ_SLEEP


def viz_from_scientific(
    state: np.ndarray,
    access_mask: np.ndarray | None = None,
    collision_mask: np.ndarray | None = None,
) -> list[str]:
    names = []
    for i, s in enumerate(state):
        if s == DONE:
            names.append(VIZ_DONE)
        elif collision_mask is not None and collision_mask[i]:
            names.append(VIZ_COLLISION)
        elif access_mask is not None and access_mask[i]:
            names.append(VIZ_ACCESS)
        elif s == OFF:
            names.append(VIZ_OFF)
        elif s == SLEEP:
            names.append(VIZ_SLEEP)
        elif s == TX:
            names.append(VIZ_ACCESS)
        else:
            names.append(VIZ_ON)
    return names


def compact_snapshot(state: np.ndarray, energy_j: np.ndarray, inventoried: np.ndarray) -> dict:
    return {
        "state": viz_from_scientific(state),
        "energy_nj": (energy_j * 1e9).astype(np.float32).tolist(),
        "inventoried": inventoried.astype(bool).tolist(),
    }
