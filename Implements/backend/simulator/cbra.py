"""Contention-based random access (CBRA) over time-frequency AOs.

Device 1: 4 time-domain AOs × 2 frequency-domain AOs = 8 AOs.
Each attempting device *plans* one AO uniformly. Occupancy is decided
only when that time-AO is executed: devices that hit E_low (or go OFF)
before their Msg1 slot do not transmit, so they cannot create collisions.

Access draw is computed once per paging; energy is applied on the real
timeline by the slot loop.
"""

from dataclasses import dataclass, field

import numpy as np

from simulator.config import OFF, ON, TX, SimConfig

AO_IDLE = "IDLE"
AO_SINGLETON = "MSG1_SINGLETON"
AO_COLLISION = "COLLISION"
AO_PENDING = "PENDING"


@dataclass
class AOOutcome:
    ao_index: int
    time_ao: int
    freq_ao: int
    planned_ids: list[int] = field(default_factory=list)
    transmitted_ids: list[int] = field(default_factory=list)
    dropped_before_msg1: list[int] = field(default_factory=list)
    status: str = AO_PENDING  # PENDING until this time-AO executes
    msg1_result: str | None = None  # IDLE | MSG1_SINGLETON | COLLISION
    final_result: str | None = None  # completed | energy_failed_msg2 | energy_failed_msg3 | collided | dropped_before_msg1
    energy_before_msg1_nj: dict[int, float] = field(default_factory=dict)
    energy_after_msg1_nj: dict[int, float] = field(default_factory=dict)

    @property
    def device_ids(self) -> list[int]:
        """Actual transmitters (occupancy). Empty until resolved."""
        return self.transmitted_ids


@dataclass
class CBRAResult:
    paging_index: int
    time_s: float
    p_access: float
    eligible_ids: list[int]
    attempting_ids: list[int]
    success_ids: list[int]
    collision_ids: list[int]
    idle_count: int
    collision_ao_count: int
    success_ao_count: int
    aos: list[AOOutcome] = field(default_factory=list)
    used_full_msg23: bool = False
    duration_s: float = 0.0
    n_heard_no_attempt: int = 0
    energy_fail_stage: str | None = None
    msg1_singleton_ids: list[int] = field(default_factory=list)
    completed_ids: list[int] = field(default_factory=list)
    dropped_before_msg1_ids: list[int] = field(default_factory=list)
    actual_tx_ids: list[int] = field(default_factory=list)
    energy_fail: dict = field(default_factory=dict)
    group_index: int | None = None
    n_on: int | None = None
    p_access_after: float | None = None
    n_planned_attempts: int = 0
    n_actual_tx: int = 0


@dataclass
class CBRAPlan:
    """Slot-level schedule for one paging + CBRA.

    Occupancy (idle / singleton / collision) is *not* frozen at creation.
    """

    paging_index: int
    start_slot: int
    time_s: float
    p_access: float
    eligible_ids: np.ndarray
    attempting_ids: np.ndarray
    access_u: np.ndarray
    time_ao: np.ndarray
    freq_ao: np.ndarray
    aos: list[AOOutcome]
    paging_slots: int
    msg1_slots: int
    n_time_ao: int
    n_freq_ao: int
    msg2_slots: int
    msg3_slots: int
    has_msg23: bool
    duration_slots: int
    pending_success: np.ndarray
    collision_ids: np.ndarray
    msg1_success_ids: np.ndarray
    actual_tx_ids: np.ndarray
    dropped_before_msg1: np.ndarray
    resolved_time_ao: set[int] = field(default_factory=set)
    failed_energy: dict = field(default_factory=dict)
    idle_count: int = 0
    collision_ao_count: int = 0
    success_ao_count: int = 0
    group_index: int | None = None
    n_on: int = 0
    p_access_after: float | None = None


def _empty_int() -> np.ndarray:
    return np.array([], dtype=int)


def plan_cbra(
    cfg: SimConfig,
    rng: np.random.Generator,
    paging_index: int,
    start_slot: int,
    time_s: float,
    eligible_ids: np.ndarray,
    p_access: float,
    group_index: int | None = None,
    n_on: int = 0,
) -> CBRAPlan:
    """Access probability draw + planned AO choices. No occupancy yet."""
    d = cfg.device
    n_ao = d.n_ao
    n_time = d.n_time_ao
    n_freq = d.n_freq_ao
    paging_slots = max(1, cfg.slots(d.paging_s))
    msg1_slots = max(1, cfg.slots(d.msg1_s))
    msg2_slots = max(1, cfg.slots(d.msg2_s))
    msg3_slots = max(1, cfg.slots(d.msg3_s))

    attempting = _empty_int()
    access_u = np.array([], dtype=np.float64)
    if eligible_ids.size > 0:
        access_u = rng.random(eligible_ids.size)
        attempting = eligible_ids[access_u < p_access]

    time_ao = np.full(attempting.size, -1, dtype=np.int16)
    freq_ao = np.full(attempting.size, -1, dtype=np.int16)
    planned_by_ao: list[list[int]] = [[] for _ in range(n_ao)]
    if attempting.size:
        chosen = rng.integers(0, n_ao, size=attempting.size)
        for i, ao in enumerate(chosen):
            planned_by_ao[int(ao)].append(int(attempting[i]))
            time_ao[i] = int(ao) // n_freq
            freq_ao[i] = int(ao) % n_freq

    outcomes = []
    for ao in range(n_ao):
        t_ao, f_ao = divmod(ao, n_freq)
        outcomes.append(
            AOOutcome(
                ao_index=ao,
                time_ao=t_ao,
                freq_ao=f_ao,
                planned_ids=planned_by_ao[ao],
                status=AO_PENDING,
            )
        )

    # Msg2/Msg3 reserved until a real Msg1 singleton exists. Duration starts
    # as paging + all Msg1 time-AOs; maybe_enable_msg23 extends if needed.
    duration_slots = paging_slots + n_time * msg1_slots
    skip = cfg.assumptions.aperiodic_skip_unused_msg23
    # Keep a slot for Msg2/Msg3 if skip is off (reader always runs them).
    has_msg23 = not skip
    if has_msg23:
        duration_slots += msg2_slots + msg3_slots

    return CBRAPlan(
        paging_index=paging_index,
        start_slot=start_slot,
        time_s=time_s,
        p_access=float(p_access),
        eligible_ids=np.asarray(eligible_ids, dtype=int),
        attempting_ids=np.asarray(attempting, dtype=int),
        access_u=np.asarray(access_u, dtype=np.float64),
        time_ao=time_ao,
        freq_ao=freq_ao,
        aos=outcomes,
        paging_slots=paging_slots,
        msg1_slots=msg1_slots,
        n_time_ao=n_time,
        n_freq_ao=n_freq,
        msg2_slots=msg2_slots,
        msg3_slots=msg3_slots,
        has_msg23=has_msg23,
        duration_slots=int(duration_slots),
        pending_success=_empty_int(),
        collision_ids=_empty_int(),
        msg1_success_ids=_empty_int(),
        actual_tx_ids=_empty_int(),
        dropped_before_msg1=_empty_int(),
        group_index=group_index,
        n_on=int(n_on),
    )


def cbra_phase(plan: CBRAPlan, offset: int) -> tuple[str, int]:
    """Return (phase, time_ao_or_-1) for this slot inside the plan."""
    if offset < plan.paging_slots:
        return "paging", -1
    t0 = plan.paging_slots
    msg1_span = plan.n_time_ao * plan.msg1_slots
    if offset < t0 + msg1_span:
        t_ao = (offset - t0) // plan.msg1_slots
        return "msg1", int(t_ao)
    if not plan.has_msg23:
        return "idle", -1
    t1 = t0 + msg1_span
    if offset < t1 + plan.msg2_slots:
        return "msg2", -1
    return "msg3", -1


def is_first_slot_of_phase(plan: CBRAPlan, offset: int, name: str) -> bool:
    phase, _ = cbra_phase(plan, offset)
    if phase != name:
        return False
    if name == "msg2":
        t1 = plan.paging_slots + plan.n_time_ao * plan.msg1_slots
        return offset == t1
    if name == "msg3":
        t1 = plan.paging_slots + plan.n_time_ao * plan.msg1_slots
        return offset == t1 + plan.msg2_slots
    if name == "paging":
        return offset == 0
    return False


def is_first_slot_of_time_ao(plan: CBRAPlan, offset: int) -> int | None:
    phase, t_ao = cbra_phase(plan, offset)
    if phase != "msg1" or t_ao < 0:
        return None
    t0 = plan.paging_slots
    if (offset - t0) % plan.msg1_slots == 0:
        return t_ao
    return None


def _can_transmit(
    device_id: int,
    energy: np.ndarray,
    state: np.ndarray,
    inventoried: np.ndarray,
    e_low_j: float,
    msg1_j: float,
) -> bool:
    i = int(device_id)
    if inventoried[i]:
        return False
    if state[i] in (OFF,):
        return False
    # Need energy to finish this Msg1 slot without already being at E_low.
    if energy[i] <= e_low_j:
        return False
    if energy[i] < e_low_j + msg1_j:
        return False
    return True


def resolve_msg1_time_ao(
    plan: CBRAPlan,
    t_ao: int,
    energy: np.ndarray,
    state: np.ndarray,
    inventoried: np.ndarray,
    e_low_j: float,
    msg1_j: float,
) -> None:
    """Decide idle / singleton / collision from devices that actually TX."""
    if t_ao in plan.resolved_time_ao:
        return
    plan.resolved_time_ao.add(int(t_ao))

    tx_ids: list[int] = []
    drop_ids: list[int] = []
    singleton: list[int] = []
    collided: list[int] = []

    for ao in plan.aos:
        if ao.time_ao != t_ao:
            continue
        planned = ao.planned_ids
        actual: list[int] = []
        dropped: list[int] = []
        before: dict[int, float] = {}
        for d_id in planned:
            before[d_id] = float(energy[d_id] * 1e9)
            if _can_transmit(d_id, energy, state, inventoried, e_low_j, msg1_j):
                actual.append(d_id)
            else:
                dropped.append(d_id)
                ao.final_result = "dropped_before_msg1"
        ao.transmitted_ids = actual
        ao.dropped_before_msg1 = dropped
        ao.energy_before_msg1_nj = before
        if len(actual) == 0:
            ao.status = AO_IDLE
            ao.msg1_result = AO_IDLE
            if planned and ao.final_result is None:
                ao.final_result = "dropped_before_msg1"
        elif len(actual) == 1:
            ao.status = AO_SINGLETON
            ao.msg1_result = AO_SINGLETON
            singleton.extend(actual)
        else:
            ao.status = AO_COLLISION
            ao.msg1_result = AO_COLLISION
            ao.final_result = "collided"
            collided.extend(actual)
        tx_ids.extend(actual)
        drop_ids.extend(dropped)

    if tx_ids:
        plan.actual_tx_ids = np.unique(
            np.concatenate([plan.actual_tx_ids, np.asarray(tx_ids, dtype=int)])
        )
    if drop_ids:
        plan.dropped_before_msg1 = np.unique(
            np.concatenate([plan.dropped_before_msg1, np.asarray(drop_ids, dtype=int)])
        )
        plan.failed_energy.setdefault("msg1_dropped", [])
        plan.failed_energy["msg1_dropped"].extend(int(i) for i in drop_ids)
    if singleton:
        plan.msg1_success_ids = np.unique(
            np.concatenate([plan.msg1_success_ids, np.asarray(singleton, dtype=int)])
        )
        plan.pending_success = np.unique(
            np.concatenate([plan.pending_success, np.asarray(singleton, dtype=int)])
        )
    if collided:
        plan.collision_ids = np.unique(
            np.concatenate([plan.collision_ids, np.asarray(collided, dtype=int)])
        )

    _recount_ao_stats(plan)


def maybe_enable_msg23(plan: CBRAPlan) -> None:
    """If a real Msg1 singleton appeared, run Msg2/Msg3 on the timeline."""
    if plan.pending_success.size == 0 or plan.has_msg23:
        return
    plan.has_msg23 = True
    plan.duration_slots = (
        plan.paging_slots
        + plan.n_time_ao * plan.msg1_slots
        + plan.msg2_slots
        + plan.msg3_slots
    )


def _recount_ao_stats(plan: CBRAPlan) -> None:
    idle = suc = coll = 0
    for ao in plan.aos:
        if ao.status == AO_IDLE:
            idle += 1
        elif ao.status == AO_SINGLETON:
            suc += 1
        elif ao.status == AO_COLLISION:
            coll += 1
    plan.idle_count = idle
    plan.success_ao_count = suc
    plan.collision_ao_count = coll


def apply_cbra_slot(
    plan: CBRAPlan,
    offset: int,
    state: np.ndarray,
    inventoried: np.ndarray,
) -> None:
    """Set TX/ON for devices that actually participate this slot."""
    phase, t_ao = cbra_phase(plan, offset)
    if phase == "msg1" and t_ao >= 0:
        tx = []
        for ao in plan.aos:
            if ao.time_ao == t_ao:
                tx.extend(ao.transmitted_ids)
        if tx:
            ids = np.asarray(tx, dtype=int)
            ids = ids[~inventoried[ids]] if ids.size else ids
            if ids.size:
                state[ids] = TX
    elif phase == "msg2" and plan.pending_success.size:
        ids = plan.pending_success[~inventoried[plan.pending_success]]
        if ids.size:
            state[ids] = ON
    elif phase == "msg3" and plan.pending_success.size:
        ids = plan.pending_success[~inventoried[plan.pending_success]]
        if ids.size:
            state[ids] = TX


def record_msg1_energy_after(plan: CBRAPlan, t_ao: int, energy: np.ndarray) -> None:
    for ao in plan.aos:
        if ao.time_ao != t_ao:
            continue
        for d_id in ao.transmitted_ids:
            ao.energy_after_msg1_nj[d_id] = float(energy[d_id] * 1e9)


def drop_if_energy_fail(
    plan: CBRAPlan,
    energy: np.ndarray,
    e_low_j: float,
    stage: str,
    extra_ids: np.ndarray | None = None,
) -> np.ndarray:
    """Record E_low hits. Pending-success devices are removed from Msg2/Msg3."""
    dropped = []
    if extra_ids is not None and extra_ids.size:
        bad = extra_ids[energy[extra_ids] <= e_low_j]
        if bad.size:
            plan.failed_energy.setdefault(stage, [])
            plan.failed_energy[stage].extend(int(i) for i in bad)
            dropped.extend(int(i) for i in bad)
    if plan.pending_success.size:
        ids = plan.pending_success
        bad = ids[energy[ids] <= e_low_j]
        if bad.size:
            plan.failed_energy.setdefault(stage, [])
            plan.failed_energy[stage].extend(int(i) for i in bad)
            keep = np.isin(plan.pending_success, bad, invert=True)
            plan.pending_success = plan.pending_success[keep]
            dropped.extend(int(i) for i in bad)
            tag = {
                "msg2": "energy_failed_msg2",
                "msg3": "energy_failed_msg3",
                "msg1": "energy_failed_msg1",
                "paging": "energy_failed_paging",
            }.get(stage, f"energy_failed_{stage}")
            bad_set = {int(i) for i in bad}
            for ao in plan.aos:
                if any(d in bad_set for d in ao.transmitted_ids) and ao.status == AO_SINGLETON:
                    if ao.final_result is None or ao.final_result == "completed":
                        ao.final_result = tag
    return np.asarray(dropped, dtype=int) if dropped else _empty_int()


def mark_completed(plan: CBRAPlan, completed_ids: np.ndarray) -> None:
    done = {int(i) for i in completed_ids}
    for ao in plan.aos:
        if ao.status == AO_SINGLETON and any(d in done for d in ao.transmitted_ids):
            ao.final_result = "completed"


def finish_cbra(plan: CBRAPlan, cfg: SimConfig) -> CBRAResult:
    # Unresolved time-AOs (should not happen in a full run) count as idle.
    for ao in plan.aos:
        if ao.status == AO_PENDING:
            ao.status = AO_IDLE
            ao.msg1_result = AO_IDLE
    _recount_ao_stats(plan)
    duration_s = plan.duration_slots * cfg.dt_s
    completed = plan.pending_success.tolist()
    return CBRAResult(
        paging_index=plan.paging_index,
        time_s=plan.time_s,
        p_access=plan.p_access,
        eligible_ids=plan.eligible_ids.tolist(),
        attempting_ids=plan.attempting_ids.tolist(),
        success_ids=completed,
        collision_ids=plan.collision_ids.tolist(),
        idle_count=plan.idle_count,
        collision_ao_count=plan.collision_ao_count,
        success_ao_count=plan.success_ao_count,
        aos=plan.aos,
        used_full_msg23=plan.has_msg23,
        duration_s=duration_s,
        n_heard_no_attempt=max(
            0, int(plan.eligible_ids.size) - int(plan.attempting_ids.size)
        ),
        msg1_singleton_ids=plan.msg1_success_ids.tolist(),
        completed_ids=completed,
        dropped_before_msg1_ids=plan.dropped_before_msg1.tolist(),
        actual_tx_ids=plan.actual_tx_ids.tolist(),
        energy_fail={k: list(v) for k, v in plan.failed_energy.items()},
        group_index=plan.group_index,
        n_on=plan.n_on,
        p_access_after=plan.p_access_after,
        n_planned_attempts=int(plan.attempting_ids.size),
        n_actual_tx=int(plan.actual_tx_ids.size),
    )


def run_cbra(
    cfg: SimConfig,
    rng: np.random.Generator,
    paging_index: int,
    time_s: float,
    eligible_ids: np.ndarray,
    p_access: float,
) -> CBRAResult:
    """Access draw + planned AOs. Occupancy is unresolved (unit-test helper)."""
    plan = plan_cbra(cfg, rng, paging_index, 0, time_s, eligible_ids, p_access)
    return finish_cbra(plan, cfg)


def ao_to_dict(ao: AOOutcome) -> dict:
    return {
        "ao_index": ao.ao_index,
        "time_ao": ao.time_ao,
        "freq_ao": ao.freq_ao,
        "status": ao.status if ao.status != AO_PENDING else AO_IDLE,
        "msg1_result": ao.msg1_result or ao.status,
        "final_result": ao.final_result,
        "planned_ids": list(ao.planned_ids),
        "transmitted_ids": list(ao.transmitted_ids),
        "dropped_before_msg1": list(ao.dropped_before_msg1),
        "device_ids": list(ao.transmitted_ids),
        "energy_before_msg1_nj": {str(k): v for k, v in ao.energy_before_msg1_nj.items()},
        "energy_after_msg1_nj": {str(k): v for k, v in ao.energy_after_msg1_nj.items()},
    }
