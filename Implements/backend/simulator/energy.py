"""Energy storage updates for OFF / ON / TX / SLEEP.

All energies in Joules, powers in Watts, dt in seconds.
"""

import numpy as np

from simulator.config import DONE, OFF, ON, SLEEP, TX


def sleep_net_min_w_from_nw(nw: float | None) -> float:
    """UI/API nW → Watts. None means paper −∞ (no floor)."""
    if nw is None:
        return float("-inf")
    return float(nw) * 1e-9


def format_sleep_net_min(w: float) -> str:
    if not np.isfinite(w):
        return "-inf"
    return f"{w * 1e9:g} nW"


def update_energy(
    energy: np.ndarray,
    state: np.ndarray,
    peh_w: np.ndarray,
    dt_s: float,
    p_rx_w: float,
    p_tx_w: float,
    p_sl_w: float,
    e_max_j: float,
    sleep_net_min_w: float = float("-inf"),
) -> None:
    """In-place energy update for one slot. Vectorized over devices.

    SLEEP: ΔE = max(x, P_eh − P_sl) Δt. Paper x = −∞ (no floor). A finite
    x (e.g. 0) is an experimental clamp so weak devices do not drain.
    """
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
        # Paper: x = −∞ → max(−∞, P_eh−P_sl) = P_eh−P_sl.
        # Experimental: x = 0 → SLEEP never drains.
        net = np.maximum(sleep_net_min_w, peh_w[sleep] - p_sl_w)
        energy[sleep] = energy[sleep] + net * dt_s

    np.clip(energy, 0.0, e_max_j, out=energy)


def recharge_time_s(delta_e_j: float, peh_w: float) -> float:
    if peh_w <= 0:
        return float("inf")
    return delta_e_j / peh_w
