"""Message durations and CBRA round timing (bits / data rate).

Round structure: Paging -> L Msg1 time slots (F AOs each) -> EI -> Msg2
(one frequency resource, sequential) -> Msg3 (parallel over F).

Periodic baseline: every round reserves K_fixed = 0.5 * L * F Msg2/Msg3
resources, so the round (= paging) interval is fixed:

    T_periodic(L) = t_page + L t_msg1 + t_EI(L) + K_fixed t_msg2 + (K_fixed / F) t_msg3

Proposed aperiodic paging: Msg2/Msg3 are provisioned from the round's actual
decoded Msg1 successes K, and the next page starts when the round ends.
"""

import math

from app.aperiodic_simulator.core.config import SystemParams

_S = SystemParams()


def t_page_s(system: SystemParams = _S) -> float:
    return system.paging_bits / system.data_rate_bps


def t_msg1_s(system: SystemParams = _S) -> float:
    return system.msg1_bits / system.data_rate_bps


def t_msg2_s(system: SystemParams = _S) -> float:
    return system.msg2_bits / system.data_rate_bps


def t_msg3_s(system: SystemParams = _S) -> float:
    return system.msg3_bits / system.data_rate_bps


def t_ei_s(L: int, F: int | None = None, B_EI: int | None = None, R: float | None = None, system: SystemParams = _S) -> float:
    F = system.F if F is None else F
    B_EI = system.ei_overhead_bits if B_EI is None else B_EI
    R = system.data_rate_bps if R is None else R
    return (L * F + B_EI) / R


def periodic_k_fixed(L: int, system: SystemParams = _S) -> float:
    return 0.5 * L * system.F


def periodic_round_interval_s(L: int, system: SystemParams = _S) -> float:
    k = periodic_k_fixed(L, system)
    return (
        t_page_s(system)
        + L * t_msg1_s(system)
        + t_ei_s(L, system=system)
        + k * t_msg2_s(system)
        + (k / system.F) * t_msg3_s(system)
    )


def aperiodic_msg3_slots(K: int, system: SystemParams = _S) -> int:
    return math.ceil(K / system.F) if K > 0 else 0


def aperiodic_round_duration_s(L: int, K: int, system: SystemParams = _S) -> float:
    return (
        t_page_s(system)
        + L * t_msg1_s(system)
        + t_ei_s(L, system=system)
        + K * t_msg2_s(system)
        + aperiodic_msg3_slots(K, system) * t_msg3_s(system)
    )


def round_components_s(L: int, n_msg2: float, msg3_time_s: float, system: SystemParams = _S) -> dict:
    return {
        "paging_s": t_page_s(system),
        "msg1_s": L * t_msg1_s(system),
        "ei_s": t_ei_s(L, system=system),
        "msg2_s": n_msg2 * t_msg2_s(system),
        "msg3_s": msg3_time_s,
    }


def success_time_equivalent_s(system: SystemParams = _S) -> float:
    """t_S = T_Msg1/F + T_Msg2 + T_Msg3/F (Appendix B, Eq. 13)."""
    return t_msg1_s(system) / system.F + t_msg2_s(system) + t_msg3_s(system) / system.F


def collision_time_equivalent_s(system: SystemParams = _S) -> float:
    """t_C = T_Msg1/F (Appendix B, Eq. 14)."""
    return t_msg1_s(system) / system.F
