"""Self-contained RF physics for the thesis scene.

Values and formulas are copied from the 3GPP TR 38.769 aperiodic-paging
reference under ``Sources/Standard_3GPP/.../Controller-Level/Code/``
(``constants.py`` lines 177-198 and ``aiot_layout.py`` lines 189-252)
so this package has no dependency on ``app.simulator`` or ``Sources/``.
Only pure functions are copied; nothing stateful.
"""

from __future__ import annotations

import math

FC_GHZ = 0.9
H_BS = 8.0
H_AIOT = 1.5

P_TX_CW_DBM = 33.0
G_TX_ANT_DBI = 6.0
P_EIRP_BS_DBM = P_TX_CW_DBM + G_TX_ANT_DBI

FIXED_DEV_DB = 7.0
L_OBJ_DB = 0.9


def dbm_to_w(dbm: float) -> float:
    return 10.0 ** ((dbm - 30.0) / 10.0)


def w_to_dbm(w: float) -> float:
    if w <= 0.0:
        return -math.inf
    return 10.0 * math.log10(w) + 30.0


def pl_los(d_m: float, fc_ghz: float = FC_GHZ) -> float:
    return 31.84 + 21.5 * math.log10(d_m + 1e-3) + 19.0 * math.log10(fc_ghz)


def pl_plus_nlos(d_m: float, fc_ghz: float = FC_GHZ) -> float:
    return 33.63 + 21.9 * math.log10(d_m + 1e-3) + 20.0 * math.log10(fc_ghz)


def pl_nlos(d_m: float, fc_ghz: float = FC_GHZ) -> float:
    return max(pl_los(d_m, fc_ghz), pl_plus_nlos(d_m, fc_ghz))


def harvest_efficiency(pin_dbm: float) -> float:
    if pin_dbm <= -10.0:
        eta = (pin_dbm + 41.0) / 100.0
    else:
        eta = (-2.0 * pin_dbm + 11.0) / 100.0
    return max(0.0, min(1.0, eta))


def incident_pin_dbm(
    d_m: float,
    tx_power_dbm: float = P_TX_CW_DBM,
    antenna_gain_dbi: float = G_TX_ANT_DBI,
    extra_atten_db: float = 0.0,
    carrier_ghz: float = FC_GHZ,
) -> float:
    eirp = tx_power_dbm + antenna_gain_dbi
    return eirp - pl_nlos(d_m, carrier_ghz) - FIXED_DEV_DB - L_OBJ_DB - extra_atten_db


def _solve_distance_from_mpl(
    mpl_db: float,
    fc_ghz: float = FC_GHZ,
    d_min_m: float = 1e-3,
    d_max_m: float = 1_000.0,
    tol: float = 1e-6,
    max_iter: int = 80,
) -> float:
    if pl_nlos(d_min_m, fc_ghz) > mpl_db:
        return d_min_m
    hi = d_max_m
    while pl_nlos(hi, fc_ghz) < mpl_db and hi < 1e6:
        hi *= 2.0
    lo = d_min_m
    for _ in range(max_iter):
        mid = 0.5 * (lo + hi)
        if abs(pl_nlos(mid, fc_ghz) - mpl_db) < tol:
            return mid
        if pl_nlos(mid, fc_ghz) < mpl_db:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _horizontal_from_3d(d3d_m: float, h_tx_m: float, h_rx_m: float) -> float:
    dz = abs(h_tx_m - h_rx_m)
    if d3d_m <= dz:
        return 0.0
    return math.sqrt(d3d_m * d3d_m - dz * dz)


def range_from_sensitivity_m(
    rx_sens_dbm: float,
    tx_power_dbm: float = P_TX_CW_DBM,
    antenna_gain_dbi: float = G_TX_ANT_DBI,
    extra_atten_db: float = 0.0,
    carrier_ghz: float = FC_GHZ,
    h_tx: float = H_BS,
    h_rx: float = H_AIOT,
) -> float:
    eirp = tx_power_dbm + antenna_gain_dbi
    mpl = eirp - L_OBJ_DB - FIXED_DEV_DB - extra_atten_db - rx_sens_dbm
    if mpl <= 0.0:
        return 0.0
    d3d = _solve_distance_from_mpl(mpl, carrier_ghz)
    return _horizontal_from_3d(d3d, h_tx, h_rx)
