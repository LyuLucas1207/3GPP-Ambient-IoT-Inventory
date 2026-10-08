"""3GPP InF-DH path loss and the Table II link budget.

TR 38.901 Table 7.4.1-1 (InF), f_c in GHz, d_3D in m:

    PL_LOS   = 31.84 + 21.50 log10(d_3D) + 19.00 log10(f_c)
    PL_DH    = 33.63 + 21.90 log10(d_3D) + 20.00 log10(f_c)
    PL_InF-DH(NLOS) = max(PL_LOS, PL_DH)

The paper uses a deterministic shadow-fading *margin* (4 dB) rather than random
shadowing, so path loss is a deterministic function of distance.

Downlink incident power at a device from one BS:

    P_in = P_tx,BS + G_tx,BS - PL - L_pol - M_SF - L_obj

Uplink received power at the reader:

    backscatter (types 1, 2a):  P_BS = P_in,reader - L_bs + G_bs - PL + uplink_offset
    active (type 2b):           P_BS = P_tx,2b - PL + uplink_offset

``uplink_offset`` is a named assumption (see ``config.Assumptions``).
"""

import numpy as np

from app.aperiodic_simulator.core.config import Assumptions, SystemParams
from app.aperiodic_simulator.physics.device_types import device_types


def distance_3d_m(xy: np.ndarray, bs_xy: np.ndarray, system: SystemParams) -> np.ndarray:
    dx = xy[..., 0] - bs_xy[0]
    dy = xy[..., 1] - bs_xy[1]
    dh = system.bs_height_m - system.device_height_m
    return np.sqrt(dx * dx + dy * dy + dh * dh)


def inf_dh_path_loss_db(d3d_m: np.ndarray | float, fc_ghz: float = 0.9) -> np.ndarray:
    d = np.maximum(np.asarray(d3d_m, dtype=np.float64), 1.0)
    pl_los = 31.84 + 21.50 * np.log10(d) + 19.00 * np.log10(fc_ghz)
    pl_dh = 33.63 + 21.90 * np.log10(d) + 20.00 * np.log10(fc_ghz)
    return np.maximum(pl_los, pl_dh)


def downlink_penalties_db(system: SystemParams) -> float:
    return system.polarization_loss_db + system.shadow_fading_margin_db + system.on_object_penalty_db


def incident_power_dbm(path_loss_db: np.ndarray, system: SystemParams) -> np.ndarray:
    eirp = system.bs_tx_power_dbm + system.bs_tx_antenna_gain_dbi
    return eirp - path_loss_db - downlink_penalties_db(system)


def uplink_rx_power_dbm(
    type_idx: np.ndarray,
    pin_reader_dbm: np.ndarray,
    path_loss_db: np.ndarray,
    system: SystemParams,
    assumptions: Assumptions,
) -> np.ndarray:
    types = device_types(system)
    out = np.empty_like(pin_reader_dbm)
    for t in types:
        m = type_idx == t.index
        if t.uplink == "backscatter":
            out[m] = (
                pin_reader_dbm[m]
                - t.backscatter_loss_db
                + t.backscatter_gain_db
                - path_loss_db[m]
                + assumptions.uplink_offset_db
            )
        else:
            out[m] = t.active_tx_power_dbm - path_loss_db[m] + assumptions.uplink_offset_db
    return out


def link_budget_summary(system: SystemParams, assumptions: Assumptions) -> dict:
    """Static link-budget terms exposed in diagnostics."""
    return {
        "path_loss_model": "3GPP TR 38.901 InF-DH (NLOS): max(PL_LOS, PL_DH)",
        "carrier_ghz": system.carrier_ghz,
        "bs_tx_power_dbm": system.bs_tx_power_dbm,
        "bs_tx_antenna_gain_dbi": system.bs_tx_antenna_gain_dbi,
        "polarization_loss_db": system.polarization_loss_db,
        "shadow_fading_margin_db": system.shadow_fading_margin_db,
        "on_object_penalty_db": system.on_object_penalty_db,
        "downlink_total_penalty_db": downlink_penalties_db(system),
        "bs_rx_sensitivity_dbm": system.bs_rx_sensitivity_dbm,
        "uplink_offset_db": assumptions.uplink_offset_db,
        "bs_height_m": system.bs_height_m,
        "device_height_m": system.device_height_m,
    }
