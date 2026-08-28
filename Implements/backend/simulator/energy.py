"""Energy storage updates for OFF / ON / TX / SLEEP.

All energies in Joules, powers in Watts, dt in seconds.
"""

import numpy as np

from simulator.config import DONE, OFF, ON, SLEEP, TX


def update_energy(
    energy: np.ndarray,
    state: np.ndarray,
    peh_w: np.ndarray,
    dt_s: float,
    p_rx_w: float,
    p_tx_w: float,
    p_sl_w: float,
    e_max_j: float,
) -> None:
    """In-place energy update for one slot. Vectorized over devices."""
    off = state == OFF
    on = state == ON
    sleep = state == SLEEP
    tx = state == TX
    # DONE devices are inventoried; keep energy frozen for inspector plots.

    if np.any(off):
        energy[off] = np.minimum(e_max_j, energy[off] + peh_w[off] * dt_s)
    if np.any(on):
        energy[on] = energy[on] - p_rx_w * dt_s
    if np.any(tx):
        energy[tx] = energy[tx] - p_tx_w * dt_s
    if np.any(sleep):
        energy[sleep] = energy[sleep] + (peh_w[sleep] - p_sl_w) * dt_s

    np.clip(energy, 0.0, e_max_j, out=energy)


def recharge_time_s(delta_e_j: float, peh_w: float) -> float:
    if peh_w <= 0:
        return float("inf")
    return delta_e_j / peh_w
