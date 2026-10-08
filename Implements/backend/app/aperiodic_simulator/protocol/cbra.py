"""One CBRA round after paging: Msg1 -> EI -> Msg2 -> Msg3.

Per-participant energy follows Fig. 3 / Appendix A, with harvesting added
continuously:

    Msg1: P_tx during the device's own Msg1 slot, P_sl in the other L-1 slots
    EI:   P_rx for T_EI(L)
    Msg2: P_sl until the device's Msg2 slot, P_rx in it, P_sl for the remaining
          Msg2 slots (attributed to the Msg2 stage as in Eq. 10)
    Msg3: P_sl until the device's Msg3 time slot, P_tx in it

Msg2/Msg3 provisioning:
    periodic baseline  -> fixed K_alloc = 0.5 L F; decoded devices beyond it
                          are not served; unused slots are wasted resources
    aperiodic proposal -> K_alloc = number of decoded Msg1 (EI-driven)

EI semantics: one flag per AO; set only for AOs with a decoded RN16 that is
served with a Msg2. Devices in a captured AO that lost the capture see the flag,
listen to the Msg2 and find a foreign RN16 (fail after Msg2). Devices in
missed/collided/unserved AOs fail after EI.
"""

from dataclasses import dataclass, field

import numpy as np

from app.aperiodic_simulator.core.config import SystemParams
from app.aperiodic_simulator.physics.impairments import AOResolution, resolve_aos
from app.aperiodic_simulator.core.states import STAGES, PagingMode, Stage
from app.aperiodic_simulator.core.timing import (
    aperiodic_msg3_slots,
    periodic_k_fixed,
    t_ei_s,
    t_msg1_s,
    t_msg2_s,
    t_msg3_s,
    t_page_s,
)

STAGE_CODE = {s: i for i, s in enumerate(STAGES)}
NO_STAGE = -1


class Fate:
    SUCCESS = 0
    MISSED = 1  # AO missed by the reader
    COLLISION = 2  # unresolved collision
    UNSERVED = 3  # decoded but no Msg2 resource (periodic under-allocation)
    CAPTURE_LOSS = 4  # lost the capture in its AO
    DEPLETED = 5  # fell below E_low mid-round

    NAMES = ("success", "missed_detection", "collision", "unserved", "capture_loss", "depleted")


@dataclass
class ParticipantInputs:
    energy_j: np.ndarray  # energy at the start of Msg1
    p_tx_w: np.ndarray
    p_rx_w: np.ndarray
    p_sl_w: np.ndarray
    p_harv_w: np.ndarray
    e_low_j: np.ndarray
    e_up_j: np.ndarray
    p_ul_w: np.ndarray
    is_type2: np.ndarray


@dataclass
class CBRAOutcome:
    ao: np.ndarray
    msg2_index: np.ndarray  # -1 if no Msg2
    fate: np.ndarray
    exit_time_s: np.ndarray  # absolute time the device leaves the round
    exit_energy_j: np.ndarray
    depleted_stage: np.ndarray  # first stage with E < E_low (NO_STAGE if none)
    identified: np.ndarray
    stage_energy_j: dict[str, np.ndarray]  # consumed energy per stage (participants)
    resolution: AOResolution
    k_decoded: int
    k_alloc: float
    k_served: int
    t_msg1_start: float
    t_ei_start: float
    t_msg2_start: float
    t_msg3_start: float
    t_round_end: float
    msg3_time_s: float
    timeline: dict = field(default_factory=dict)


def run_cbra(
    t0: float,
    L: int,
    mode: PagingMode,
    parts: ParticipantInputs,
    rng_ao: np.random.Generator,
    rng_imp: np.random.Generator,
    system: SystemParams,
    enforce_depletion: bool = True,
    impairments_enabled: bool = True,
) -> CBRAOutcome:
    F = system.F
    n_ao = L * F
    n = parts.energy_j.size
    t1, t2, t3 = t_msg1_s(system), t_msg2_s(system), t_msg3_s(system)
    tei = t_ei_s(L, system=system)
    t_msg1_start = t0 + t_page_s(system)
    t_ei_start = t_msg1_start + L * t1
    t_msg2_start = t_ei_start + tei

    ao = rng_ao.integers(0, n_ao, size=n)
    res = resolve_aos(
        ao,
        parts.p_ul_w,
        parts.is_type2,
        n_ao,
        rng_imp,
        capture_ratio_db=system.capture_ratio_db,
        missed_detection_rate=system.missed_detection_rate,
        false_alarm_rate=system.false_alarm_rate,
        enabled=impairments_enabled,
    )

    decoded_aos = np.flatnonzero(res.winner >= 0)  # AO order = time slot, then frequency
    k_decoded = int(decoded_aos.size)
    if mode == PagingMode.PERIODIC:
        k_alloc = periodic_k_fixed(L, system)
        k_slots = int(np.floor(k_alloc))
        msg3_time = (k_alloc / F) * t3
    else:
        k_slots = k_decoded
        k_alloc = float(k_decoded)
        msg3_time = aperiodic_msg3_slots(k_decoded, system) * t3
    served_aos = decoded_aos[: min(k_slots, k_decoded)]
    k_served = int(served_aos.size)
    ao_msg2 = np.full(n_ao, -1, dtype=np.int64)
    ao_msg2[served_aos] = np.arange(k_served)
    t_msg3_start = t_msg2_start + k_slots * t2
    t_round_end = t_msg3_start + msg3_time

    k = ao_msg2[ao]  # Msg2 index of the device's AO (-1: EI flag not set)
    is_winner = np.zeros(n, dtype=bool)
    if n:
        w = res.winner[ao]
        is_winner = w == np.arange(n)
    fate = np.full(n, Fate.COLLISION, dtype=np.int8)
    fate[(k < 0) & (res.winner[ao] >= 0)] = Fate.UNSERVED
    fate[res.missed[ao]] = Fate.MISSED
    fate[(k >= 0) & ~is_winner] = Fate.CAPTURE_LOSS
    fate[(k >= 0) & is_winner] = Fate.SUCCESS

    e = parts.energy_j.copy()
    harv, psl = parts.p_harv_w, parts.p_sl_w
    e_low, e_up = parts.e_low_j, parts.e_up_j
    dep = np.full(n, NO_STAGE, dtype=np.int8)
    alive = np.ones(n, dtype=bool)  # still in the round
    exit_t = np.full(n, t_round_end)
    stage_e = {s.value: np.zeros(n) for s in STAGES}

    def apply(stage: Stage, cons: np.ndarray, dur: np.ndarray, end_t: np.ndarray, mask: np.ndarray) -> None:
        nonlocal e
        idx = mask & alive
        stage_e[stage.value][idx] += cons[idx]
        e[idx] = np.minimum(e[idx] - cons[idx] + harv[idx] * dur[idx], e_up[idx])
        crossed = idx & (e < e_low) & (dep == NO_STAGE)
        dep[crossed] = STAGE_CODE[stage]
        if enforce_depletion:
            exit_t[crossed] = end_t[crossed]
            e[crossed] = e_low[crossed]
            alive[crossed] = False

    ones = np.ones(n)
    # Msg1
    d1 = L * t1 * ones
    apply(Stage.MSG1, parts.p_tx_w * t1 + psl * (L - 1) * t1, d1, (t_ei_start) * ones, ones.astype(bool))
    # EI
    apply(Stage.EI, parts.p_rx_w * tei, tei * ones, t_msg2_start * ones, ones.astype(bool))
    leave_after_ei = alive & (k < 0)
    exit_t[leave_after_ei] = t_msg2_start
    alive[leave_after_ei] = False
    # Msg2
    kk = np.maximum(k, 0).astype(np.float64)
    own_end = t_msg2_start + (kk + 1) * t2
    loser = alive & (fate == Fate.CAPTURE_LOSS)
    apply(Stage.MSG2, psl * kk * t2 + parts.p_rx_w * t2, (kk + 1) * t2, own_end, loser)
    exit_t[loser & alive] = own_end[loser & alive]
    alive[loser] = False
    win = alive & (fate == Fate.SUCCESS)
    rest = np.maximum(k_slots - 1 - kk, 0.0)
    apply(
        Stage.MSG2,
        psl * (kk + rest) * t2 + parts.p_rx_w * t2,
        (kk + 1 + rest) * t2,
        t_msg3_start * ones,
        win,
    )
    # Msg3
    j = np.floor(kk / F)
    msg3_end = t_msg3_start + (j + 1) * t3
    apply(Stage.MSG3, psl * j * t3 + parts.p_tx_w * t3, (j + 1) * t3, msg3_end, win & alive)
    identified = win & alive
    exit_t[identified] = msg3_end[identified]
    if enforce_depletion:
        fate[dep != NO_STAGE] = Fate.DEPLETED
    else:
        e = np.maximum(e, 0.0)

    return CBRAOutcome(
        ao=ao,
        msg2_index=k,
        fate=fate,
        exit_time_s=exit_t,
        exit_energy_j=e,
        depleted_stage=dep,
        identified=identified,
        stage_energy_j=stage_e,
        resolution=res,
        k_decoded=k_decoded,
        k_alloc=k_alloc,
        k_served=k_served,
        t_msg1_start=t_msg1_start,
        t_ei_start=t_ei_start,
        t_msg2_start=t_msg2_start,
        t_msg3_start=t_msg3_start,
        t_round_end=t_round_end,
        msg3_time_s=msg3_time,
    )
