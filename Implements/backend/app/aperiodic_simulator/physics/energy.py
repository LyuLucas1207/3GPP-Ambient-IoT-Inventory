"""Appendix A per-round energy feasibility and per-stage energy costs.

    E_wc(L) = E_base + L * E_scale
    E_base  = P_wurx T_mon + P_rx T_pg + P_rx B_EI / R
              + (P_tx - P_sl)(T_Msg1 + T_Msg3) + (P_rx - P_sl) T_Msg2
    E_scale = P_rx F / R + P_sl (T_Msg1 + F T_Msg2 + T_Msg3)
    Lmax_type = floor((E_up - E_low - E_base) / E_scale)
    Lmax = min over device types

(T_pg in the Appendix is the paging *message duration*, ``t_page_s`` here.)
The bound assumes zero harvesting during the round.
"""

import math

from app.aperiodic_simulator.core.config import SystemParams
from app.aperiodic_simulator.physics.device_types import DeviceType, device_types
from app.aperiodic_simulator.core.timing import t_ei_s, t_msg1_s, t_msg2_s, t_msg3_s, t_page_s


def e_base_j(t: DeviceType, system: SystemParams | None = None) -> float:
    s = system or SystemParams()
    return (
        t.p_wurx_w * s.t_mon_s
        + t.p_rx_w * t_page_s(s)
        + t.p_rx_w * s.ei_overhead_bits / s.data_rate_bps
        + (t.p_tx_w - t.p_sl_w) * (t_msg1_s(s) + t_msg3_s(s))
        + (t.p_rx_w - t.p_sl_w) * t_msg2_s(s)
    )


def e_scale_j(t: DeviceType, system: SystemParams | None = None) -> float:
    s = system or SystemParams()
    return t.p_rx_w * s.F / s.data_rate_bps + t.p_sl_w * (t_msg1_s(s) + s.F * t_msg2_s(s) + t_msg3_s(s))


def e_worst_case_j(t: DeviceType, L: int, system: SystemParams | None = None) -> float:
    return e_base_j(t, system) + L * e_scale_j(t, system)


def e_worst_case_direct_j(t: DeviceType, L: int, system: SystemParams | None = None) -> float:
    """Eq. (10) evaluated term by term (cross-check of the affine form)."""
    s = system or SystemParams()
    F = s.F
    return (
        t.p_wurx_w * s.t_mon_s
        + t.p_rx_w * t_page_s(s)
        + ((L - 1) * t.p_sl_w + t.p_tx_w) * t_msg1_s(s)
        + t.p_rx_w * t_ei_s(L, system=s)
        + ((L * F - 1) * t.p_sl_w + t.p_rx_w) * t_msg2_s(s)
        + ((L - 1) * t.p_sl_w + t.p_tx_w) * t_msg3_s(s)
    )


def lmax_type(t: DeviceType, system: SystemParams | None = None) -> int:
    return math.floor((t.e_up_j - t.e_low_j - e_base_j(t, system)) / e_scale_j(t, system))


def compute_global_lmax(system: SystemParams | None = None) -> int:
    return min(lmax_type(t, system) for t in device_types(system))


def lmax_report(system: SystemParams | None = None) -> dict:
    s = system or SystemParams()
    out = {}
    for t in device_types(s):
        out[t.name] = {
            "E_base_uJ": e_base_j(t, s) * 1e6,
            "E_scale_uJ": e_scale_j(t, s) * 1e6,
            "budget_uJ": (t.e_up_j - t.e_low_j) * 1e6,
            "Lmax": lmax_type(t, s),
        }
    return {"per_type": out, "Lmax": compute_global_lmax(s)}
