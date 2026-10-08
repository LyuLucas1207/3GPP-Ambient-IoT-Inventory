"""Paper-independent RF utilities shared by both simulators.

RF-to-DC conversion efficiency (published IEEE version of the periodic-paging
paper; the aperiodic-paging paper reuses the same harvesting model):

    xi(p_in) = (p_in + 41) / 100      if p_in <= -10 dBm
    xi(p_in) = (-2 * p_in + 11) / 100 if p_in >  -10 dBm

with p_in the numerical dBm value, clipped to [0, 1].
"""

import numpy as np


def dbm_to_watts(dbm: np.ndarray | float) -> np.ndarray | float:
    return 10.0 ** ((np.asarray(dbm, dtype=np.float64) - 30.0) / 10.0)


def watts_to_dbm(watts: np.ndarray | float) -> np.ndarray | float:
    w = np.asarray(watts, dtype=np.float64)
    return 10.0 * np.log10(w) + 30.0


def conversion_efficiency(pin_dbm: np.ndarray | float) -> np.ndarray | float:
    """Published piecewise RF-to-DC efficiency xi(p_in)."""
    x = np.asarray(pin_dbm, dtype=np.float64)
    low = (x + 41.0) / 100.0
    high = (-2.0 * x + 11.0) / 100.0
    xi = np.where(x <= -10.0, low, high)
    xi = np.clip(xi, 0.0, 1.0)
    if np.isscalar(pin_dbm):
        return float(xi)
    return xi


def harvest_power_w(pin_dbm: np.ndarray | float) -> np.ndarray | float:
    """P_eh = p_in * xi(p_in)."""
    pin_w = dbm_to_watts(pin_dbm)
    xi = conversion_efficiency(pin_dbm)
    return pin_w * xi
