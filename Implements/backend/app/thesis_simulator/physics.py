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

B_HZ = 30_000.0
NF_DB = 5.0
SNR_REQ_DB = 0.5
CANCEL_DEPTH_DB = 140.0


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
    """R2D (reader → device) horizontal reach limited only by device RX sensitivity."""
    eirp = tx_power_dbm + antenna_gain_dbi
    mpl = eirp - L_OBJ_DB - FIXED_DEV_DB - extra_atten_db - rx_sens_dbm
    if mpl <= 0.0:
        return 0.0
    d3d = _solve_distance_from_mpl(mpl, carrier_ghz)
    return _horizontal_from_3d(d3d, h_tx, h_rx)


def reader_required_level_dbm(
    tx_power_dbm: float = P_TX_CW_DBM,
    cancel_depth_db: float = CANCEL_DEPTH_DB,
    snr_req_db: float = SNR_REQ_DB,
) -> float:
    """Reader-side minimum RX power = CW self-leak residual + SNR margin."""
    return tx_power_dbm - cancel_depth_db + snr_req_db


def _mpl_to_horizontal_m(mpl_db: float, carrier_ghz: float, h_tx: float, h_rx: float) -> float:
    if mpl_db <= 0.0:
        return 0.0
    d3d = _solve_distance_from_mpl(mpl_db, carrier_ghz)
    return _horizontal_from_3d(d3d, h_tx, h_rx)


def d2r_backscatter_range_m(
    backscatter_loss_db: float,
    backscatter_gain_db: float,
    tx_power_dbm: float = P_TX_CW_DBM,
    extra_atten_db: float = 0.0,
    carrier_ghz: float = FC_GHZ,
    h_tx: float = H_BS,
    h_rx: float = H_AIOT,
) -> float:
    """D2R horizontal reach for backscatter uplink (Device 1 and 2a)."""
    gbs = -backscatter_loss_db + backscatter_gain_db
    p_req = reader_required_level_dbm(tx_power_dbm)
    mpl = 0.5 * (tx_power_dbm + gbs - FIXED_DEV_DB - extra_atten_db - p_req)
    return _mpl_to_horizontal_m(mpl, carrier_ghz, h_tx, h_rx)


def d2r_active_range_m(
    active_tx_power_dbm: float,
    tx_power_dbm: float = P_TX_CW_DBM,
    extra_atten_db: float = 0.0,
    carrier_ghz: float = FC_GHZ,
    h_tx: float = H_BS,
    h_rx: float = H_AIOT,
) -> float:
    """D2R horizontal reach for active uplink (Device 2b)."""
    p_req = reader_required_level_dbm(tx_power_dbm)
    mpl = active_tx_power_dbm - FIXED_DEV_DB - extra_atten_db - p_req
    return _mpl_to_horizontal_m(mpl, carrier_ghz, h_tx, h_rx)


def effective_coverage_m(
    device_params: dict,
    reader_rf: dict,
    include_d2r: bool = True,
) -> float:
    """Horizontal radius a reader can inventory this device at.

    include_d2r=True (default) returns min(R2D, D2R), aligned with the paper.
    include_d2r=False returns R2D only, matching the "legacy" single-leg model.
    """
    tx = float(reader_rf.get("tx_power_dbm", P_TX_CW_DBM))
    gain = float(reader_rf.get("antenna_gain_dbi", G_TX_ANT_DBI))
    extra = float(reader_rf.get("extra_attenuation_db", 0.0))
    carrier = float(reader_rf.get("carrier_ghz", FC_GHZ))

    r2d = range_from_sensitivity_m(
        rx_sens_dbm=float(device_params["rx_sensitivity_dbm"]),
        tx_power_dbm=tx,
        antenna_gain_dbi=gain,
        extra_atten_db=extra,
        carrier_ghz=carrier,
    )
    if not include_d2r:
        return r2d
    uplink = device_params.get("uplink", "backscatter")
    if uplink == "active":
        active_tx = device_params.get("active_tx_power_dbm")
        if active_tx is None:
            return 0.0
        d2r = d2r_active_range_m(
            active_tx_power_dbm=float(active_tx),
            tx_power_dbm=tx,
            extra_atten_db=extra,
            carrier_ghz=carrier,
        )
    else:
        d2r = d2r_backscatter_range_m(
            backscatter_loss_db=float(device_params.get("backscatter_loss_db", 6.0)),
            backscatter_gain_db=float(device_params.get("backscatter_gain_db", 0.0)),
            tx_power_dbm=tx,
            extra_atten_db=extra,
            carrier_ghz=carrier,
        )
    return min(r2d, d2r)
