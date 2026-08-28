"""Energy-based monitoring: ON while E_up ≥ e ≥ E_low."""

import numpy as np

from simulator.config import DONE, OFF, ON, SimConfig


def apply_em_thresholds(energy: np.ndarray, state: np.ndarray, cfg: SimConfig) -> None:
    d = cfg.device
    active = state != DONE
    to_on = active & (state == OFF) & (energy >= d.e_up_j)
    to_off = active & (state == ON) & (energy <= d.e_low_j)
    state[to_on] = ON
    state[to_off] = OFF
