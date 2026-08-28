"""Slot-level inventory simulation. Independent of FastAPI / React."""

from dataclasses import dataclass, field

import numpy as np

from simulator.cbra import (
    CBRAResult,
    ao_to_dict,
    apply_cbra_slot,
    cbra_phase,
    drop_if_energy_fail,
    finish_cbra,
    is_first_slot_of_time_ao,
    is_first_slot_of_phase,
    mark_completed,
    maybe_enable_msg23,
    plan_cbra,
    record_msg1_energy_after,
    resolve_msg1_time_ao,
)
from simulator.config import (
    DONE,
    OFF,
    ON,
    SLEEP,
    TX,
    SimConfig,
    Strategy,
    is_dcm,
    n_groups_for,
    strategy_label,
    validate_strategies,
)
from simulator.channel import pin_cdf_fingerprint
from simulator.device import compact_snapshot, viz_from_scientific
from simulator.energy import format_sleep_net_min, update_energy
from simulator.metrics import summarize
from simulator.fig5b_validation import evaluate_fig5b
from simulator.grouping import (
    FIRST_PAGING,
    PRECONFIGURED,
    assign_at_first_paging,
    group_populations,
    preconfigured_groups,
)
from simulator.paging import advance_after_cbra, is_periodic_epoch
from simulator.paper_reference import compare_curves, fig5b_reference_payload
from simulator.reader import make_reader
from simulator.run_store import DeviceTraceBank
from simulator.scenario import Scenario, initial_arrays
from simulator.strategies.dcm import (
    apply_dcm_pre_inventory,
    apply_elow,
    expire_synced_on_window,
    recover_keep_sync_off,
    return_to_sleep,
)
from simulator.strategies.em import apply_em_thresholds

_STRATEGY_SEED = {
    Strategy.EM.value: 101,
    Strategy.DCM_1_GROUP.value: 202,
    Strategy.DCM_4_GROUP.value: 303,
}


def _stable_strategy_seed(strategy: str) -> int:
    return _STRATEGY_SEED.get(strategy, 404)


@dataclass
class StrategyResult:
    strategy: str
    label: str
    metrics: dict
    times_s: list[float]
    ratio_pct: list[float]
    snapshots: list[dict] = field(default_factory=list)
    paging_events: list[dict] = field(default_factory=list)
    p_access_history: list[list[float]] = field(default_factory=list)
    device_stats: list[dict] = field(default_factory=list)
    n_paging: int = 0
    n_msg1_attempts: int = 0
    n_collisions: int = 0
    warnings: list[str] = field(default_factory=list)
    energy_traces: dict | None = None
    trace_bank: DeviceTraceBank | None = None
    warmup_stats: dict | None = None


def _cbra_event_dict(result: CBRAResult) -> dict:
    return {
        "paging_index": result.paging_index,
        "time_s": result.time_s,
        "p_access": result.p_access,
        "p_access_after": result.p_access_after,
        "group_index": result.group_index,
        "n_on": result.n_on,
        "n_eligible": len(result.eligible_ids),
        "n_attempting": result.n_planned_attempts,
        "n_planned_attempts": result.n_planned_attempts,
        "n_actual_tx": result.n_actual_tx,
        "n_success": len(result.completed_ids),
        "n_msg1_singleton": len(result.msg1_singleton_ids),
        "n_collision": len(result.collision_ids),
        "idle_count": result.idle_count,
        "collision_ao_count": result.collision_ao_count,
        "success_ao_count": result.success_ao_count,
        "n_heard_no_attempt": result.n_heard_no_attempt,
        "attempting_ids": result.attempting_ids,
        "actual_tx_ids": result.actual_tx_ids,
        "success_ids": result.completed_ids,
        "msg1_singleton_ids": result.msg1_singleton_ids,
        "dropped_before_msg1_ids": result.dropped_before_msg1_ids,
        "energy_fail": result.energy_fail,
        "aos": [ao_to_dict(ao) for ao in result.aos],
    }


def _device_stats(
    n: int,
    completion: np.ndarray,
    group: np.ndarray,
    attempts: np.ndarray,
    collisions: np.ndarray,
    first_page: np.ndarray,
    first_time: np.ndarray,
    last_sync_time: np.ndarray,
    sync_count: np.ndarray,
    lost_sync_count: np.ndarray,
    n_paging_eligible: np.ndarray | None = None,
    n_access_reject: np.ndarray | None = None,
    n_energy_fail: np.ndarray | None = None,
    initial_energy_j: np.ndarray | None = None,
    initial_state: np.ndarray | None = None,
) -> list[dict]:
    out = []
    for i in range(n):
        done = bool(np.isfinite(completion[i]))
        rec = {
            "id": i,
            "inventoried": done,
            "completion_time_s": None if not done else float(completion[i]),
            "group": int(group[i]) if group[i] >= 0 else None,
            "attempts": int(attempts[i]),
            "collisions": int(collisions[i]),
            "first_paging_detected": bool(first_page[i]),
            "first_paging_time_s": None
            if not first_page[i]
            else float(first_time[i]),
            "last_sync_time_s": None
            if not np.isfinite(last_sync_time[i])
            else float(last_sync_time[i]),
            "sync_count": int(sync_count[i]),
            "lost_sync_count": int(lost_sync_count[i]),
        }
        if n_paging_eligible is not None:
            rec["n_paging_eligible"] = int(n_paging_eligible[i])
        if n_access_reject is not None:
            rec["n_access_reject"] = int(n_access_reject[i])
        if n_energy_fail is not None:
            rec["n_energy_fail"] = int(n_energy_fail[i])
        if initial_energy_j is not None:
            rec["initial_energy_nj"] = float(initial_energy_j[i] * 1e9)
        if initial_state is not None:
            rec["initial_state"] = int(initial_state[i])
        out.append(rec)
    return out


def run_strategy(
    cfg: SimConfig,
    scenario: Scenario,
    strategy: str,
    rng: np.random.Generator | None = None,
) -> StrategyResult:
    rng = rng or np.random.default_rng(cfg.seed + _stable_strategy_seed(strategy))
    n = cfg.num_devices
    d = cfg.device
    dt = cfg.dt_s
    n_slots = cfg.n_slots
    ng = n_groups_for(strategy)
    dcm = is_dcm(strategy)
    t_pg_slots = cfg.slots(d.t_pg_s)
    ton_dcm_slots = max(1, cfg.slots(d.t_on_dcm_s))

    energy, state, on_remaining, warmup_stats = initial_arrays(cfg, scenario, strategy)
    peh = scenario.peh_w
    inventoried = np.zeros(n, dtype=bool)
    completion = np.full(n, np.nan, dtype=np.float64)
    synced = np.zeros(n, dtype=bool)
    group_mode = cfg.assumptions.group_assignment
    if dcm and group_mode in PRECONFIGURED:
        group = preconfigured_groups(n, ng, group_mode, rng)
    else:
        group = np.full(n, -1, dtype=np.int16)
    use_first_paging_group = dcm and group_mode in FIRST_PAGING
    initial_energy_j = energy.copy()
    initial_state = state.copy()
    n_paging_eligible = np.zeros(n, dtype=np.int32)
    n_access_reject = np.zeros(n, dtype=np.int32)
    n_energy_fail_dev = np.zeros(n, dtype=np.int32)
    first_page = np.zeros(n, dtype=bool)
    first_time = np.full(n, np.nan)
    last_sync_time = np.full(n, np.nan)
    sync_count = np.zeros(n, dtype=np.int32)
    lost_sync_count = np.zeros(n, dtype=np.int32)
    attempts = np.zeros(n, dtype=np.int32)
    collisions = np.zeros(n, dtype=np.int32)
    wake_slot = np.full(n, -1, dtype=np.int32)
    access_flash = np.zeros(n, dtype=bool)
    collision_flash = np.zeros(n, dtype=bool)
    flash_until = np.zeros(n, dtype=np.int32)

    reader = make_reader(cfg, n_load=max(1, n // ng) if dcm else n, n_groups=ng)

    snapshots: list[dict] = []
    paging_events: list[dict] = []
    p_hist: list[list[float]] = []
    n_paging = 0
    n_attempts = 0
    n_coll = 0
    n_heard_no_attempt = 0
    warnings: list[str] = []
    energy_fail_counts = {
        "paging": 0,
        "msg1": 0,
        "msg1_dropped": 0,
        "msg2": 0,
        "msg3": 0,
    }

    next_paging_slot = 0
    paging_index = 0
    stride = cfg.snapshot_stride
    plan = None
    plan_offset = 0
    msg1_j = d.p_tx_w * d.msg1_s

    trace_stride = 1
    tmax = n_slots // trace_stride + 2
    tr_energy = np.empty((n, tmax), dtype=np.float32)
    tr_state = np.empty((n, tmax), dtype=np.uint8)
    tr_phase = np.zeros((n, tmax), dtype=np.uint8)
    tr_page = np.full((n, tmax), -1, dtype=np.int16)
    tr_tao = np.full((n, tmax), -1, dtype=np.int8)
    tr_fao = np.full((n, tmax), -1, dtype=np.int8)
    tr_times = np.empty(tmax, dtype=np.float32)
    tr_k = 0
    dev_events: list[list[dict]] = [[] for _ in range(n)]

    def note(ids, event: str, **extra) -> None:
        rec = {"event": event, "time_s": float(t), "sample_index": max(0, tr_k - 1), **extra}
        for i in np.atleast_1d(ids):
            dev_events[int(i)].append(dict(rec))

    for slot in range(n_slots):
        t = slot * dt

        tx_busy = (state == TX) & (~inventoried)
        if np.any(tx_busy):
            state[tx_busy] = ON

        if dcm:
            due = synced & (~inventoried) & (wake_slot == slot)
            starved = due & (state == OFF)
            wake_now = due & ~starved
            if np.any(wake_now):
                state[wake_now] = ON
                on_remaining[wake_now] = ton_dcm_slots
            if np.any(starved):
                wake_slot[starved] = slot + ng * t_pg_slots

        if plan is not None:
            first_ao = is_first_slot_of_time_ao(plan, plan_offset)
            if first_ao is not None:
                resolve_msg1_time_ao(
                    plan, first_ao, energy, state, inventoried, d.e_low_j, msg1_j
                )
                maybe_enable_msg23(plan)
                if plan.aos:
                    tx_now = []
                    coll_now = []
                    drop_now = []
                    single_now = []
                    for ao in plan.aos:
                        if ao.time_ao != first_ao:
                            continue
                        tx_now.extend(ao.transmitted_ids)
                        drop_now.extend(ao.dropped_before_msg1)
                        if ao.status == "COLLISION":
                            coll_now.extend(ao.transmitted_ids)
                        elif ao.status == "MSG1_SINGLETON":
                            single_now.extend(ao.transmitted_ids)
                    if tx_now:
                        n_attempts += len(tx_now)
                        attempts[np.asarray(tx_now, dtype=int)] += 1
                        access_flash[np.asarray(tx_now, dtype=int)] = True
                        flash_until[np.asarray(tx_now, dtype=int)] = slot + max(
                            1, cfg.slots(0.05)
                        )
                        note(tx_now, "msg1", paging_index=plan.paging_index, time_ao=first_ao)
                    if drop_now:
                        note(
                            drop_now,
                            "dropped_before_msg1",
                            paging_index=plan.paging_index,
                            time_ao=first_ao,
                        )
                    if coll_now:
                        n_coll += len(coll_now)
                        collisions[np.asarray(coll_now, dtype=int)] += 1
                        collision_flash[np.asarray(coll_now, dtype=int)] = True
                        flash_until[np.asarray(coll_now, dtype=int)] = slot + max(
                            1, cfg.slots(0.05)
                        )
                        note(
                            coll_now,
                            "collision",
                            paging_index=plan.paging_index,
                            time_ao=first_ao,
                        )
                    if single_now:
                        note(
                            single_now,
                            "msg1_singleton",
                            paging_index=plan.paging_index,
                            time_ao=first_ao,
                        )
            apply_cbra_slot(plan, plan_offset, state, inventoried)

        update_energy(
            energy,
            state,
            peh,
            dt,
            d.p_rx_w,
            d.p_tx_w,
            d.p_sl_w,
            d.e_max_j,
            sleep_net_min_w=cfg.assumptions.sleep_net_power_min_w,
        )

        if plan is not None:
            phase, t_ao = cbra_phase(plan, plan_offset)
            extra = None
            if phase == "paging" and plan.eligible_ids.size:
                extra = plan.eligible_ids
            elif phase == "msg1" and plan.actual_tx_ids.size:
                extra = plan.actual_tx_ids
            dropped = drop_if_energy_fail(plan, energy, d.e_low_j, phase, extra_ids=extra)
            if dropped.size:
                n_energy_fail_dev[dropped] += 1
                note(dropped, f"energy_fail_{phase}", paging_index=plan.paging_index)
            if phase == "msg1" and t_ao >= 0:
                last_of_ao = ((plan_offset - plan.paging_slots) % plan.msg1_slots) == (
                    plan.msg1_slots - 1
                )
                if last_of_ao:
                    record_msg1_energy_after(plan, t_ao, energy)

        if dcm:
            apply_dcm_pre_inventory(energy, state, on_remaining, synced, cfg)
            skip_expire = np.zeros(n, dtype=bool)
            if plan is not None:
                if plan.pending_success.size:
                    skip_expire[plan.pending_success] = True
                if plan.attempting_ids.size:
                    skip_expire[plan.attempting_ids] = True
            expire_synced_on_window(
                state, on_remaining, synced & (~skip_expire), inventoried
            )
            hit_low = apply_elow(energy, state, cfg, synced)
            if np.any(hit_low):
                was_synced = hit_low & synced
                lost_sync_count[was_synced] += 1
                if np.any(was_synced):
                    note(np.flatnonzero(was_synced), "lost_sync")
                if cfg.assumptions.off_clears_inventory_sync:
                    synced[hit_low] = False
                    wake_slot[hit_low] = -1
                    on_remaining[hit_low] = 0
                    if use_first_paging_group:
                        group[hit_low] = -1
            if not cfg.assumptions.off_clears_inventory_sync:
                recover_keep_sync_off(
                    energy,
                    state,
                    on_remaining,
                    synced,
                    inventoried,
                    wake_slot,
                    slot,
                    ng * t_pg_slots,
                    d.e_up_j,
                    ton_dcm_slots,
                )
        else:
            apply_em_thresholds(energy, state, cfg)

        if plan is None and slot >= next_paging_slot and not bool(inventoried.all()):
            if dcm and not is_periodic_epoch(slot, t_pg_slots):
                pass
            else:
                if dcm:
                    paging_index = slot // t_pg_slots
                this_g = paging_index % ng
                n_on_now = int(np.count_nonzero((state == ON) & (~inventoried)))
                if dcm:
                    can_hear = (state == ON) & (~inventoried)
                    newly = can_hear & (~synced)
                    if np.any(newly):
                        first_new = newly & (~first_page)
                        if np.any(first_new):
                            first_page[first_new] = True
                            first_time[first_new] = t
                        last_sync_time[newly] = t
                        sync_count[newly] += 1
                        synced[newly] = True
                        note(np.flatnonzero(newly), "sync", paging_index=paging_index)
                        if use_first_paging_group:
                            ids = np.flatnonzero(newly)
                            group[ids] = assign_at_first_paging(
                                newly, paging_index, ng, group_mode, rng
                            )
                    eligible_mask = (
                        (state == ON)
                        & (~inventoried)
                        & synced
                        & (group == this_g)
                        & (energy > d.e_low_j)
                    )
                else:
                    eligible_mask = (
                        (state == ON)
                        & (~inventoried)
                        & (energy > d.e_low_j)
                    )
                    newly_em = eligible_mask & (~first_page)
                    if np.any(newly_em):
                        first_page[newly_em] = True
                        first_time[newly_em] = t
                eligible_ids = np.flatnonzero(eligible_mask)
                p_now = reader.p_for_group(this_g if dcm else 0)
                plan = plan_cbra(
                    cfg,
                    rng,
                    paging_index,
                    slot,
                    t,
                    eligible_ids,
                    p_now,
                    group_index=this_g if dcm else None,
                    n_on=n_on_now,
                )
                plan_offset = 0
                n_paging += 1
                n_heard_no_attempt += max(
                    0, int(eligible_ids.size) - int(plan.attempting_ids.size)
                )
                if plan.eligible_ids.size:
                    n_paging_eligible[plan.eligible_ids] += 1
                    note(plan.eligible_ids, "paging", paging_index=plan.paging_index)
                    attempting_set = set(int(i) for i in plan.attempting_ids.tolist())
                    ao_of = {
                        int(did): (int(plan.time_ao[j]), int(plan.freq_ao[j]))
                        for j, did in enumerate(plan.attempting_ids.tolist())
                    }
                    for j, did in enumerate(plan.eligible_ids.tolist()):
                        u = float(plan.access_u[j]) if j < plan.access_u.size else None
                        attempted = int(did) in attempting_set
                        extra = {
                            "p_access": plan.p_access,
                            "u": u,
                            "attempted": attempted,
                            "paging_index": plan.paging_index,
                        }
                        if attempted and int(did) in ao_of:
                            extra["time_ao"], extra["freq_ao"] = ao_of[int(did)]
                        note([did], "access_draw", **extra)
                    rejected = [int(i) for i in plan.eligible_ids.tolist() if int(i) not in attempting_set]
                    if rejected:
                        n_access_reject[np.asarray(rejected, dtype=int)] += 1
                        note(rejected, "paging_rejected", paging_index=plan.paging_index)
                if plan.attempting_ids.size:
                    note(plan.attempting_ids, "msg1_planned", paging_index=plan.paging_index)
                    access_flash[plan.attempting_ids] = True
                    flash_until[plan.attempting_ids] = slot + max(1, cfg.slots(0.05))
                missed_mask = (state == ON) & (~inventoried) & (~eligible_mask)
                missed = np.flatnonzero(missed_mask)
                if missed.size:
                    note(missed, "paging_missed", paging_index=plan.paging_index)

                if dcm:
                    own = synced & (~inventoried) & (group == this_g) & (state == ON)
                    wake_slot[own] = slot + ng * t_pg_slots
                    att = np.zeros(n, dtype=bool)
                    if plan.attempting_ids.size:
                        att[plan.attempting_ids] = True
                    attempters = own & att
                    idle_own = own & ~att
                    if np.any(attempters):
                        # Keep the Table 1 T_on_DCM window open through Msg1.
                        # CBRA may last longer (Msg2/Msg3); it must not be shorter.
                        on_remaining[attempters] = ton_dcm_slots
                    if cfg.assumptions.sleep_when_not_attempting and np.any(idle_own):
                        # Experimental early-sleep: not the paper default.
                        return_to_sleep(state, on_remaining, idle_own)
                    elif np.any(idle_own):
                        # Paper: T_on_DCM is the monitoring window after inventory
                        # sync, including devices that draw “no access”.
                        on_remaining[idle_own] = ton_dcm_slots
                    other = synced & (~inventoried) & (group != this_g) & (state == ON)
                    if np.any(other):
                        offset = (group.astype(np.int32) - this_g) % ng
                        return_to_sleep(state, on_remaining, other)
                        wake_slot[other] = slot + np.maximum(offset[other], 1) * t_pg_slots

                apply_cbra_slot(plan, 0, state, inventoried)

        if plan is not None:
            last = plan_offset >= plan.duration_slots - 1
            if last and plan.pending_success.size:
                idx = plan.pending_success
                still = idx[energy[idx] > d.e_low_j]
                if still.size:
                    note(still, "msg3", paging_index=plan.paging_index)
                    done_time = t + dt
                    inventoried[still] = True
                    completion[still] = done_time
                    state[still] = DONE
                    wake_slot[still] = -1
                    on_remaining[still] = 0
                    mark_completed(plan, still)
                    note(still, "done", paging_index=plan.paging_index)
                    plan.pending_success = still
                else:
                    drop_if_energy_fail(plan, energy, d.e_low_j, "msg3")
                    plan.pending_success = np.array([], dtype=int)
            if last and dcm and plan.attempting_ids.size:
                # CBRA already occupied ≥ T_on_DCM (paging + Msg1, plus Msg2/Msg3
                # if singleton). Do not start a second 3 ms ON after the occasion.
                leftover = np.zeros(n, dtype=bool)
                leftover[plan.attempting_ids] = True
                leftover &= (~inventoried) & (state != DONE) & (state != OFF)
                return_to_sleep(state, on_remaining, leftover)
            if last:
                for stage, ids in plan.failed_energy.items():
                    key = stage if stage in energy_fail_counts else (
                        "msg1" if str(stage).startswith("msg1") else stage
                    )
                    energy_fail_counts[key] = energy_fail_counts.get(key, 0) + len(set(ids))
                cbra = finish_cbra(plan, cfg)
                if reader.controller is not None:
                    reader.observe(
                        cbra.idle_count,
                        n_eligible=len(cbra.eligible_ids),
                        n_transmitted=cbra.n_actual_tx,
                        singleton_ao_count=cbra.success_ao_count,
                        collision_ao_count=cbra.collision_ao_count,
                        group_index=cbra.group_index,
                    )
                cbra.p_access_after = reader.p_access
                plan.p_access_after = reader.p_access
                reader.note(t)
                p_hist.append([t, reader.p_access])
                if cfg.collect_paging_events:
                    paging_events.append(_cbra_event_dict(cbra))
                next_paging_slot = advance_after_cbra(
                    cfg, strategy, slot, cbra.duration_s
                )
                if not dcm:
                    paging_index += 1
                plan = None
                plan_offset = 0
            else:
                if (
                    is_first_slot_of_phase(plan, plan_offset, "msg2")
                    and plan.pending_success.size
                ):
                    note(plan.pending_success, "msg2", paging_index=plan.paging_index)
                if (
                    is_first_slot_of_phase(plan, plan_offset, "msg3")
                    and plan.pending_success.size
                ):
                    note(plan.pending_success, "msg3_start", paging_index=plan.paging_index)
                plan_offset += 1

        expired_flash = flash_until <= slot
        access_flash[expired_flash] = False
        collision_flash[expired_flash] = False

        if slot % trace_stride == 0:
            tr_times[tr_k] = t
            tr_energy[:, tr_k] = (energy * 1e9).astype(np.float32)
            tr_state[:, tr_k] = state.astype(np.uint8)
            if plan is not None:
                ph, tao = cbra_phase(plan, plan_offset)
                ph_i = {"paging": 1, "msg1": 2, "msg2": 3, "msg3": 4}.get(ph, 0)
                involved = np.zeros(n, dtype=bool)
                if ph == "paging" and plan.eligible_ids.size:
                    involved[plan.eligible_ids] = True
                elif ph == "msg1":
                    if plan.actual_tx_ids.size:
                        involved[plan.actual_tx_ids] = True
                    if plan.attempting_ids.size:
                        waiting = plan.attempting_ids[plan.time_ao >= tao]
                        involved[waiting] = True
                elif ph in ("msg2", "msg3") and plan.pending_success.size:
                    involved[plan.pending_success] = True
                tr_phase[involved, tr_k] = ph_i
                tr_page[involved, tr_k] = plan.paging_index
                if ph == "msg1" and plan.attempting_ids.size:
                    for i, did in enumerate(plan.attempting_ids):
                        if involved[int(did)]:
                            tr_tao[int(did), tr_k] = plan.time_ao[i]
                            tr_fao[int(did), tr_k] = plan.freq_ao[i]
            tr_k += 1

        if cfg.collect_snapshots and (slot % stride == 0):
            snap = compact_snapshot(state, energy, inventoried)
            snap["state"] = viz_from_scientific(state, access_flash, collision_flash)
            snapshots.append({"time_s": t, **snap})

        if bool(inventoried.all()):
            if cfg.collect_snapshots and (
                not snapshots or snapshots[-1]["time_s"] < t
            ):
                snap = compact_snapshot(state, energy, inventoried)
                snapshots.append({"time_s": t, **snap})
            break

    metrics = summarize(completion, n, cfg.max_time_s)
    metrics["n_paging"] = n_paging
    metrics["n_msg1_attempts"] = int(n_attempts)
    metrics["n_collisions"] = int(n_coll)
    metrics["collision_rate"] = (
        float(n_coll / n_attempts) if n_attempts else 0.0
    )
    metrics["t50_ms"] = None if metrics["t50_s"] is None else metrics["t50_s"] * 1e3
    metrics["t90_ms"] = None if metrics["t90_s"] is None else metrics["t90_s"] * 1e3
    metrics["t99_ms"] = None if metrics["t99_s"] is None else metrics["t99_s"] * 1e3
    metrics["n_heard_no_attempt"] = int(n_heard_no_attempt)
    metrics["energy_fail"] = energy_fail_counts
    if dcm:
        metrics["group_population"] = group_populations(group, ng)
        metrics["group_assignment"] = group_mode
    idle_frac = []
    coll_frac = []
    for ev in paging_events:
        nao = max(1, len(ev.get("aos") or []))
        idle_frac.append(ev["idle_count"] / nao)
        coll_frac.append(ev["collision_ao_count"] / nao)
    if idle_frac:
        metrics["idle_ao_frac_mean"] = float(np.mean(idle_frac))
        metrics["collision_ao_frac_mean"] = float(np.mean(coll_frac))
    if paging_events:
        metrics["attempts_per_ao_mean"] = float(
            np.mean([ev.get("n_actual_tx", 0) / max(1, len(ev.get("aos") or [1])) for ev in paging_events])
        )
    if metrics["t99_s"] is None:
        warnings.append(
            f"{strategy_label(strategy)}: T99 not reached before max_time_s={cfg.max_time_s}."
        )

    times, ratio = metrics.pop("times_s"), metrics.pop("ratio_pct")
    tr_k = max(tr_k, 1)
    bank = DeviceTraceBank(
        dt_s=trace_stride * dt,
        simulation_dt_s=dt,
        times_s=tr_times[:tr_k],
        energy_nj=tr_energy[:, :tr_k],
        state=tr_state[:, :tr_k],
        phase=tr_phase[:, :tr_k],
        paging_index=tr_page[:, :tr_k],
        time_ao=tr_tao[:, :tr_k],
        freq_ao=tr_fao[:, :tr_k],
        harvest_nw=scenario.peh_w * 1e9,
        completion_s=completion.copy(),
        inventoried=inventoried.copy(),
        events=dev_events,
        p_rx_w=d.p_rx_w,
        p_tx_w=d.p_tx_w,
        p_sl_w=d.p_sl_w,
        e_up_nj=d.e_up_j * 1e9,
        e_low_nj=d.e_low_j * 1e9,
    )
    export_n = n if n <= 32 else min(16, n)
    export_ids = list(range(export_n)) if n <= 32 else list(
        np.unique(
            np.concatenate(
                [
                    np.argsort(scenario.pin_dbm)[:8],
                    np.argsort(scenario.pin_dbm)[max(0, n // 2 - 2) : n // 2 + 2],
                    np.argsort(scenario.pin_dbm)[-4:],
                ]
            )
        )
    )
    compact_traces = {
        "dt_s": bank.dt_s,
        "device_ids": [int(i) for i in export_ids],
        "times_s": bank.times_s.tolist(),
        "energy_nj": {str(i): bank.energy_nj[int(i)].tolist() for i in export_ids},
        "state": {str(i): bank.state[int(i)].tolist() for i in export_ids},
        "frozen_after_done": True,
        "on_demand": True,
    }
    return StrategyResult(
        strategy=strategy,
        label=strategy_label(strategy),
        metrics=metrics,
        times_s=times.tolist(),
        ratio_pct=ratio.tolist(),
        snapshots=snapshots,
        paging_events=paging_events,
        p_access_history=p_hist,
        device_stats=_device_stats(
            n,
            completion,
            group,
            attempts,
            collisions,
            first_page,
            first_time,
            last_sync_time,
            sync_count,
            lost_sync_count,
            n_paging_eligible=n_paging_eligible,
            n_access_reject=n_access_reject,
            n_energy_fail=n_energy_fail_dev,
            initial_energy_j=initial_energy_j,
            initial_state=initial_state,
        ),
        n_paging=n_paging,
        n_msg1_attempts=int(n_attempts),
        n_collisions=int(n_coll),
        warnings=warnings,
        energy_traces=compact_traces,
        trace_bank=bank,
        warmup_stats=warmup_stats,
    )


def run_paper_comparison(
    cfg: SimConfig,
    scenario: Scenario | None = None,
) -> dict:
    strategies = validate_strategies(cfg.strategies)
    scenario = scenario or Scenario.generate(cfg)
    results: dict[str, StrategyResult] = {}
    warnings: list[str] = []
    for i, strat in enumerate(strategies):
        rng = np.random.default_rng(cfg.seed + 17 * (i + 1))
        results[strat] = run_strategy(cfg, scenario, strat, rng=rng)
        warnings.extend(results[strat].warnings)
    return {
        "scenario": scenario,
        "results": results,
        "warnings": warnings,
    }


def result_to_web_payload(cfg: SimConfig, bundle: dict, run_id: str | None = None) -> dict:
    scenario: Scenario = bundle["scenario"]
    results: dict[str, StrategyResult] = bundle["results"]
    strategies = {}
    metrics = {}
    curves = {}
    snapshots = {}
    events = {}
    p_hist = {}
    stats = {}
    for key, res in results.items():
        metrics[key] = {
            k: res.metrics[k]
            for k in (
                "t50_s",
                "t90_s",
                "t95_s",
                "t99_s",
                "t50_ms",
                "t90_ms",
                "t99_ms",
                "final_ratio_pct",
                "n_inventoried",
                "n_paging",
                "n_msg1_attempts",
                "n_collisions",
                "collision_rate",
                "n_heard_no_attempt",
            )
        }
        if "energy_fail" in res.metrics:
            metrics[key]["energy_fail"] = res.metrics["energy_fail"]
        curves[key] = {
            "times_s": res.times_s,
            "ratio_pct": res.ratio_pct,
            "label": res.label,
        }
        snapshots[key] = res.snapshots
        events[key] = res.paging_events
        p_hist[key] = res.p_access_history
        stats[key] = res.device_stats
        strategies[key] = res.label

    d = cfg.device
    a = cfg.assumptions
    cdf = pin_cdf_fingerprint()
    warmup_diagnostics = {
        key: (res.warmup_stats or {}) for key, res in results.items()
    }
    ref_payload = fig5b_reference_payload()
    curve_error = {}
    if ref_payload.get("available"):
        for key, res in results.items():
            ref = ref_payload["curves"].get(key)
            if not ref:
                continue
            curve_error[key] = compare_curves(
                np.asarray(res.times_s) * 1e3,
                np.asarray(res.ratio_pct),
                np.asarray(ref["time_ms"]),
                np.asarray(ref["ratio_pct"]),
                t99_s=res.metrics.get("t99_s"),
                paper_t99_s=ref_payload.get("paper_stated_t99_s", {}).get(key),
            )
    return {
        "run_id": run_id,
        "metadata": {
            "run_id": run_id,
            "seed": cfg.seed,
            "num_devices": cfg.num_devices,
            "device_type": cfg.device_type,
            "max_time_s": cfg.max_time_s,
            "dt_s": cfg.dt_s,
            "snapshot_interval_s": cfg.snapshot_interval_s,
            "group_assignment": a.group_assignment,
            "warmup_mode": a.warmup_mode,
            "pin_sampling": a.pin_sampling,
            "access_controller": a.access_controller,
            "p_access_scope": a.p_access_scope,
            "cdf": cdf,
        },
        "paper_parameters": {
            "N": cfg.num_devices,
            "E_max_nJ": d.e_max_j * 1e9,
            "E_up_nJ": d.e_up_j * 1e9,
            "E_low_nJ": d.e_low_j * 1e9,
            "P_rx_uW": d.p_rx_w * 1e6,
            "P_tx_uW": d.p_tx_w * 1e6,
            "P_sl_uW": d.p_sl_w * 1e6,
            "paging_ms": d.paging_s * 1e3,
            "T_pg_ms": d.t_pg_s * 1e3,
            "Msg1_ms": d.msg1_s * 1e3,
            "Msg2_ms": d.msg2_s * 1e3,
            "Msg3_ms": d.msg3_s * 1e3,
            "T_on_DCM_ms": d.t_on_dcm_s * 1e3,
            "T_on_timer_ms": d.t_on_timer_s * 1e3,
            "n_time_ao": d.n_time_ao,
            "n_freq_ao": d.n_freq_ao,
            "n_ao": d.n_ao,
        },
        "reproduction_assumptions": {
            "pin_source": (
                "Digitized Figure 5(a) CDF (visualization x,y do not set p_in). "
                f"Sampling: {a.pin_sampling} (stratified covers the CDF tail)."
            ),
            "warmup": (
                f"{a.warmup_mode} (charging stage is not on the Figure 5(b) axis). "
                "explicit = E_low/OFF state machine for warmup_s; "
                "stationary = closed-form cycle phase. They are not equivalent."
            ),
            "access_probability": (
                f"Controller `{a.access_controller}` — unpublished. "
                "Paper has no p_access equation. occupancy_counts uses Schoute "
                "n̂ = S + 2.39 C from AO occupancy (target ~1 attempt/AO). "
                f"Scope `{a.p_access_scope}`."
            ),
            "aperiodic_paging": (
                "EM: next paging at the slot after the previous CBRA ends."
            ),
            "periodic_paging": (
                "DCM: global epoch grid 0, T_pg, 2 T_pg, … . "
                "A CBRA that overruns an epoch skips that occasion."
            ),
            "off_clears_sync": a.off_clears_inventory_sync,
            "sleep_when_not_attempting": a.sleep_when_not_attempting,
            "dcm_on_mode": (
                "experimental_early_sleep_after_access_rejection"
                if a.sleep_when_not_attempting
                else "strict_paper_fixed_ton_dcm"
            ),
            "sleep_net_power_min": format_sleep_net_min(a.sleep_net_power_min_w),
            "group_assignment": (
                f"`{a.group_assignment}`. Paper: first detected paging sets the "
                "wake phase (odd/even example). first_paging_spread assigns a "
                "group at first detection without stacking simultaneous hearers. "
                "even_id_mod / random_preconfigured are preconfigured splits. "
                "first_paging_mod uses paging_index % N_g (often unbalanced)."
            ),
            "p_access_scope": a.p_access_scope,
            "channel_errors": (
                "Noise / interference / decoding failures are NOT modelled. "
                "Msg1 fails only on AO collision or energy depletion."
            ),
        },
        "reader": {
            "x": a.reader_x_m,
            "y": a.reader_y_m,
            "tx_dbm": a.reader_tx_dbm,
        },
        "static_devices": scenario.static_devices(),
        "strategy_labels": strategies,
        "metrics": metrics,
        "curves": curves,
        "snapshots": snapshots,
        "paging_events": events,
        "p_access_history": p_hist,
        "device_stats": stats,
        "energy_trace": {
            "dt_s": cfg.dt_s,
            "on_demand": True,
            "path": "/api/simulation/{run_id}/strategies/{strategy}/devices/{device_id}/trace",
        },
        "warmup_diagnostics": warmup_diagnostics,
        "paper_fig5b": ref_payload,
        "curve_error": curve_error,
        "fig5b_validation": evaluate_fig5b(results, scenario.pin_dbm),
        "warnings": bundle["warnings"],
    }
