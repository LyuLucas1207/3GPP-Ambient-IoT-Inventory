"""Single-reader frame executor (one paging / M1 / EBI / M2 / M3 round).

Timing follows the reference ``grouping_logic.py`` (``T_pre + T_post``)::

    T_frame = T_paging
            + ceil(K / F_r) * T_M1               # K M1 resources spread over the F_r granted subbands
            + T_EBI(K)
            + S_M2 * T_M2                         # periodic: ceil(K * ratio); aperiodic: S
            + ceil(S_M2 / F_r) * T_M3

``F_r`` is the number of subbands the coordination policy grants the reader
(``F`` in the ideal ``independent`` mode). ``K`` and ``p*`` come from the
reader's controller (``inventory/controller.py``).

Energy depletion mirrors the reference ``_kill``: a device whose energy falls
to ``Eoff`` during a stage is forced OFF and ungrouped, counted in
``deaths[stage]`` and keeps competing once it has recharged. Only
``identified`` and ``dropped`` are terminal.

With inter-reader interference (``ictx`` given) four losses are added: a
device that cannot decode the page (R2D SIR), a Msg1 the reader cannot decode
(D2R SINR), a Msg2 the device cannot decode and a Msg3 the reader cannot
decode. Without interference the random stream and every outcome are the
same as the ideal engine's.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

from app.simulator_thesis.inventory.aloha import draw_slots, simulate_frame
from app.simulator_thesis.inventory.controller import build_controller
from app.simulator_thesis.inventory.events import EventEmitter
from app.simulator_thesis.inventory.state import (
    STATE_COLLISION,
    STATE_DEPLETED,
    STATE_M1_SUCCESS,
    STATE_TX,
    SUBTYPE_LABEL,
    UPLINK_ACTIVE,
    DeviceWorld,
    EpisodeConfig,
    ReaderState,
)

if TYPE_CHECKING:
    from app.simulator_thesis.coordination.coordinator import Coordinator, FrameActivityBuilder, FrameInterference

STAGES: tuple[str, ...] = ("paging", "m1", "ebi", "m2", "m3")


@dataclass
class FrameResult:
    t_frame: float
    touched: dict[int, int] = field(default_factory=dict)  # device idx -> transient STATE_*
    identified: int = 0
    depleted: int = 0
    k: int = 0
    pstar: float = 0.0
    success: int = 0
    collision: int = 0
    empty: int = 0
    joiners: int = 0
    f_r: int = 0
    activity: "FrameActivityBuilder | None" = None
    interference: dict[str, int] = field(default_factory=dict)
    new_by_subtype: tuple[int, ...] = (0, 0, 0)  # this frame's new IDs per subtype code


@dataclass
class _FrameStats:
    energy_j: list[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    deaths: dict[str, list[int]] = field(default_factory=lambda: {st: [0, 0, 0] for st in STAGES})

    def energy_json(self) -> dict[str, float]:
        return {SUBTYPE_LABEL[i]: float(v) for i, v in enumerate(self.energy_j)}

    def deaths_json(self) -> dict[str, dict[str, int]]:
        return {st: {SUBTYPE_LABEL[i]: int(v) for i, v in enumerate(vals)} for st, vals in self.deaths.items()}


def run_one_frame(
    reader: ReaderState,
    world: DeviceWorld,
    config: EpisodeConfig,
    rng: np.random.Generator,
    emit: EventEmitter,
    *,
    coord: "Coordinator | None" = None,
    ictx: "FrameInterference | None" = None,
) -> FrameResult:
    consts = config.consts
    F = max(1, int(consts.f_freq))
    subbands = reader.subbands or tuple(range(F))
    F_r = len(subbands)
    sb_set = frozenset(subbands)
    g = max(1, config.g if config.use_grouping else 1)
    cur_group = reader.round_index % g
    periodic = config.scheme == "periodic"
    t0 = reader.clock_s
    if config.single_reply:
        expired = (world.latched_until >= 0.0) & (world.latched_until <= t0)
        if np.any(expired):
            world.latched_reader[expired] = -1
            world.latched_until[expired] = -1.0
    stats = _FrameStats()
    result = FrameResult(t_frame=0.0, f_r=F_r)
    rid = reader.reader_id
    ix = {"r2d_lost": 0, "m1_lost": 0, "m2_lost": 0, "m3_lost": 0}
    interfering = ictx is not None and not ictx.empty
    built = None
    if coord is not None and (ictx is not None or coord.spec.mode == "lbt"):
        from app.simulator_thesis.coordination.coordinator import CW, R2D, FrameActivityBuilder

        built = FrameActivityBuilder()
    a_idx = coord.index[rid] if coord is not None else -1

    # ---------- candidate pool ----------
    alive = ~world.terminal_mask()
    not_locked_elsewhere = (world.latched_reader == -1) | (world.latched_reader == rid)
    visible = alive & reader.cover_mask & not_locked_elsewhere
    backlog_true = int(visible.sum())
    if config.use_grouping:
        returning = visible & (world.grp == cur_group) & (world.latched_reader == rid)
        first_catch = visible & (world.grp < 0) & (world.on > 0.0)
    else:
        returning = np.zeros_like(visible)
        first_catch = visible & (world.on > 0.0)
    awake = returning | first_catch
    on_at_page = int(awake.sum())
    gate_ok = world.E >= (world.Eoff + _frame_rx_cost(world, config))
    candidates = np.where(awake & gate_ok)[0]

    # ---------- K, p* and the join coin ----------
    if reader.controller is None:
        reader.controller = build_controller(config)
    decision = reader.controller.decide(reader, config, cur_group, F_r)
    k = max(1, int(decision.k))
    pstar = float(decision.pstar)
    join_mask = rng.random(candidates.size) < pstar
    joiners = candidates[join_mask]
    skippers = candidates[~join_mask]

    # ---------- phase timing ----------
    T_pg = consts.t_paging()
    T_m1 = consts.t_m1()
    T_m2 = consts.t_m2()
    T_m3 = consts.t_m3()
    T_ebi = consts.t_ebi(k) if config.use_ebi else 0.0
    T_m1_phase = math.ceil(k / F_r) * T_m1
    t_m1_start = t0 + T_pg
    t_ebi_start = t_m1_start + T_m1_phase
    t_m2_start = t_ebi_start + T_ebi

    handle = emit.start_round(
        reader_id=rid,
        round_index=reader.round_index,
        t_start_s=t0,
        t_end_s=t0,
        k=k,
        g=float(g),
        pstar=pstar,
        slot_count=k,
        metadata={
            "scheme": config.scheme, "group": cur_group, "freq_subbands": F, "f_r": F_r,
            "subbands": list(subbands), "color": int(reader.color), "controller": reader.controller.name,
            **({"controller_info": decision.info} if decision.info else {}),
        },
    )
    emit.emit_reader(
        reader_id=rid, round_handle=handle, t_s=t0, event_type="round_start",
        payload={"k": k, "pstar": float(pstar), "group": cur_group, "candidates": int(candidates.size)},
    )
    emit.emit_reader(reader_id=rid, round_handle=handle, t_s=t0, event_type="page_sent", payload={"group": cur_group, "k": k})

    # ---------- paging under interference: devices that cannot decode the page ----------
    if interfering and candidates.size:
        lost = _r2d_lost(ictx, reader, candidates, t0, t0 + T_pg, sb_set, coord.sir_lin)
        if lost.any():
            lost_idx = candidates[lost]
            _debit(world, lost_idx, T_pg, world.p_rx, stats)
            for dev in lost_idx:
                _dev_event(emit, world, rid, handle, t0 + T_pg, int(dev), "missed_page", cause="r2d_interference")
            ix["r2d_lost"] += int(lost_idx.size)
            keep = ~np.isin(joiners, lost_idx)
            joiners = joiners[keep]
            skippers = skippers[~np.isin(skippers, lost_idx)]

    # ---------- paging: skippers pay RX and switch OFF (reference "Skippers") ----------
    if skippers.size:
        _debit(world, skippers, T_pg, world.p_rx, stats)
        world.on[skippers] = 0.0
        world.went_off[skippers] = True
        for dev in skippers:
            _dev_event(emit, world, rid, handle, t0 + T_pg, int(dev), "missed_page", cause="coin")

    # ---------- paging: joiners ----------
    _debit(world, joiners, T_pg, world.p_rx, stats)
    for dev in joiners:
        _dev_event(emit, world, rid, handle, t0 + T_pg, int(dev), "paged", payload={"k": k, "pstar": float(pstar)})
    _paging_acquired(world, joiners, rid, t0 + T_pg)
    if config.use_grouping and joiners.size:
        first = joiners[world.grp[joiners] < 0]
        world.grp[first] = cur_group
        world.latched_reader[first] = rid
        for dev in first:
            _dev_event(emit, world, rid, handle, t0 + T_pg, int(dev), "latched", payload={"group": cur_group})
    joiners = _deplete(world, joiners, "paging", t0 + T_pg, rid, handle, emit, stats, result)
    world.attempts[joiners] += 1
    attempted = joiners.copy()
    result.joiners = int(joiners.size)

    if joiners.size == 0:
        emit.emit_reader(reader_id=rid, round_handle=handle, t_s=t_m1_start, event_type="idle", payload={"group": cur_group})

    # ---------- M1 (framed ALOHA over K resources / F_r subbands) ----------
    rx_power = _rx_power_at_reader(world, reader, joiners)
    slots = None
    decodable = None
    if interfering and joiners.size:
        slots = draw_slots(rng, k, joiners.size)
        decodable = _d2r_decodable(
            ictx, coord, a_idx, joiners, slots, t_m1_start, T_m1, subbands, reader, slot_period=True,
        )
        ix["m1_lost"] += int((~decodable).sum())
    elif built is not None and joiners.size:
        slots = draw_slots(rng, k, joiners.size)
    aloha = simulate_frame(
        joiner_indices=joiners,
        rx_power_dbm=rx_power,
        k=k,
        use_capture=config.use_capture,
        use_energy_detect=config.use_ebi,
        rng=rng,
        consts=consts,
        decodable=decodable,
        slots=slots,
    )
    for i, dev in enumerate(joiners):
        slot = int(aloha.slot_of_device[i])
        t_tx = _slot_time(t_m1_start, slot, F_r, T_m1)
        _dev_event(
            emit, world, rid, handle, t_tx, int(dev), "m1_tx",
            payload={"slot": slot, "rx_power_dbm": float(rx_power[i])},
        )
        if built is not None:
            built.add_tx(t_tx, t_tx + T_m1, subbands[slot % F_r], int(dev))
    _debit(world, joiners, T_m1, world.p_tx, stats)
    for s in np.nonzero(aloha.occupancy)[0]:
        occ = int(aloha.occupancy[s])
        t_slot = _slot_time(t_m1_start, int(s), F_r, T_m1) + 0.5 * T_m1
        in_slot = np.nonzero(aloha.slot_of_device == s)[0]
        won = in_slot[aloha.winners[in_slot]]
        if won.size:
            emit.emit_reader(
                reader_id=rid, round_handle=handle, t_s=t_slot, event_type="m1_rx_success", slot_index=int(s),
                payload={"device_id": int(world.placement_ids[joiners[won[0]]]), "count": occ, "captured": occ > 1},
            )
        else:
            emit.emit_reader(
                reader_id=rid, round_handle=handle, t_s=t_slot, event_type="m1_rx_collision", slot_index=int(s),
                payload={"count": occ},
            )
    dead_m1 = set(_deplete(world, joiners, "m1", t_ebi_start, rid, handle, emit, stats, result, return_dead=True).tolist())
    winner_order: list[tuple[int, int]] = []
    for i, dev in enumerate(joiners):
        dev = int(dev)
        slot = int(aloha.slot_of_device[i])
        t_ev = _slot_time(t_m1_start, slot, F_r, T_m1) + T_m1
        if dev in dead_m1:
            continue
        if aloha.winners[i]:
            _dev_event(emit, world, rid, handle, t_ev, dev, "m1_success", payload={"slot": slot})
            result.touched[dev] = STATE_M1_SUCCESS
            winner_order.append((slot, dev))
        elif decodable is not None and not decodable[i] and aloha.occupancy[slot] == 1:
            _dev_event(emit, world, rid, handle, t_ev, dev, "m1_interfered", cause="d2r_interference", payload={"slot": slot})
            result.touched[dev] = STATE_TX
        elif aloha.occupancy[slot] == 1:
            _dev_event(emit, world, rid, handle, t_ev, dev, "m1_empty", cause="detector_miss", payload={"slot": slot})
            result.touched[dev] = STATE_TX
        else:
            _dev_event(
                emit, world, rid, handle, t_ev, dev, "m1_collision", cause="collision_no_capture",
                payload={"slot": slot, "count": int(aloha.occupancy[slot])},
            )
            result.touched[dev] = STATE_COLLISION
    winner_order.sort()
    winners = np.array([dev for _, dev in winner_order], dtype=np.int64)

    # ---------- EBI ----------
    if config.use_ebi:
        emit.emit_reader(
            reader_id=rid, round_handle=handle, t_s=t_ebi_start, event_type="ebi_sent",
            payload={"k": k, "winners": int(winners.size)},
        )
        if winners.size:
            _debit(world, winners, T_ebi, world.p_rx, stats)
            for dev in winners:
                _dev_event(emit, world, rid, handle, t_ebi_start + T_ebi, int(dev), "ebi_received")
            winners = _deplete(world, winners, "ebi", t_ebi_start + T_ebi, rid, handle, emit, stats, result)

    # ---------- M2 budget ----------
    s_m2_time = int(math.ceil(k * consts.dcm_succ_ratio(config.use_capture))) if periodic else int(aloha.successes)
    s_budget = s_m2_time
    served = winners[:s_budget]
    budget_dropped = winners[s_budget:]
    for dev in budget_dropped:
        _dev_event(emit, world, rid, handle, t_m2_start, int(dev), "budget_drop", cause="no_m2_slot")

    # ---------- M2 (reader -> device ACK, one T_M2 per served device) ----------
    if served.size:
        _debit(world, served, T_m2, world.p_rx, stats)
        for i, dev in enumerate(served):
            _dev_event(emit, world, rid, handle, t_m2_start + (i + 1) * T_m2, int(dev), "m2_rx", payload={"m2_index": i})
        emit.emit_reader(
            reader_id=rid, round_handle=handle, t_s=t_m2_start, event_type="m2_sent", payload={"served": int(served.size)},
        )
        if interfering:
            ok = np.ones(served.size, dtype=bool)
            for i, dev in enumerate(served):
                t_a = t_m2_start + i * T_m2
                lost = _r2d_lost(ictx, reader, np.array([dev]), t_a, t_a + T_m2, sb_set, coord.sir_lin)
                if lost[0]:
                    ok[i] = False
                    _dev_event(emit, world, rid, handle, t_a + T_m2, int(dev), "m2_interfered", cause="r2d_interference")
            ix["m2_lost"] += int((~ok).sum())
            served = served[ok]
        served = _deplete(world, served, "m2", t_m2_start + s_m2_time * T_m2, rid, handle, emit, stats, result)

    # ---------- M3 (device -> reader final response, F_r in parallel) ----------
    t_m3_start = t_m2_start + s_m2_time * T_m2
    n_m3_slots = int(math.ceil(s_m2_time / F_r)) if s_m2_time else 0
    if served.size:
        _debit(world, served, T_m3, world.p_tx, stats)
        order = {int(dev): i for i, dev in enumerate(served)}
        for dev in served:
            t_tx = t_m3_start + (order[int(dev)] // F_r) * T_m3
            _dev_event(emit, world, rid, handle, t_tx, int(dev), "m3_tx")
            if built is not None:
                built.add_tx(t_tx, t_tx + T_m3, subbands[order[int(dev)] % F_r], int(dev))
        served = _deplete(world, served, "m3", t_m3_start + n_m3_slots * T_m3, rid, handle, emit, stats, result)
        if interfering and served.size:
            pos = np.array([order[int(d)] for d in served], dtype=np.int64)
            ok = _d2r_decodable(ictx, coord, a_idx, served, pos, t_m3_start, T_m3, subbands, reader, slot_period=True)
            for dev in served[~ok]:
                t_ev = t_m3_start + (order[int(dev)] // F_r + 1) * T_m3
                _dev_event(emit, world, rid, handle, t_ev, int(dev), "m3_interfered", cause="d2r_interference")
            ix["m3_lost"] += int((~ok).sum())
            served = served[ok]
        for dev in served:
            t_id = t_m3_start + (order[int(dev)] // F_r + 1) * T_m3
            world.identified[dev] = True
            world.identified_t[dev] = t_id
            world.identified_by[dev] = rid
            world.grp[dev] = -1
            world.latched_reader[dev] = -1
            _dev_event(emit, world, rid, handle, t_id, int(dev), "identified", payload={"round_index": reader.round_index})
            result.touched.pop(int(dev), None)
        emit.emit_reader(
            reader_id=rid, round_handle=handle, t_s=t_m3_start + n_m3_slots * T_m3, event_type="m3_rx",
            payload={"identified": int(served.size)},
        )
    result.identified = int(served.size)
    result.new_by_subtype = tuple(int((world.subtype_code[served] == c).sum()) for c in range(len(SUBTYPE_LABEL)))

    t_frame = T_pg + T_m1_phase + T_ebi + s_m2_time * T_m2 + n_m3_slots * T_m3
    t_end = t0 + t_frame

    # ---------- one reply: stay with this reader until this round's end ----------
    # The scheduler runs a whole frame before the next reader's overlapping frame,
    # so the lock is visible to any page that starts before t_end. It expires on
    # its own; a failed device is free again once this round is over.
    if config.single_reply and not config.use_grouping and attempted.size:
        pending = attempted[~world.identified[attempted]]
        keep = pending[world.E[pending] > world.Eoff[pending]]
        if keep.size:
            world.latched_reader[keep] = rid
            world.latched_until[keep] = t_end

    # ---------- per-device CBRA failure bookkeeping ----------
    if attempted.size:
        failed = attempted[~world.identified[attempted]]
        world.cbra_failures[failed] += 1
        world.t_last_fail[failed] = t_end

    # ---------- ungroup low-energy latched members (not terminal) ----------
    if config.use_grouping and consts.ungroup_when_off:
        ungroup = (
            (world.grp == cur_group) & (world.latched_reader == rid) & (world.E <= world.Eoff) & ~world.terminal_mask()
        )
        for dev in np.nonzero(ungroup)[0]:
            _dev_event(emit, world, rid, handle, t_end, int(dev), "ungrouped", cause="energy")
        world.grp[ungroup] = -1
        world.latched_reader[ungroup] = -1

    # ---------- air-time record for the coordinator ----------
    if built is not None:
        built.add(t0, t0 + T_pg, R2D)
        built.add(t_m1_start, t_ebi_start, CW)
        built.add(t_ebi_start, t_m2_start, R2D)
        built.add(t_m2_start, t_m3_start, R2D)
        built.add(t_m3_start, t_end, CW)
        result.activity = built
    ix_total = sum(ix.values())
    result.interference = {**ix, "interferers": 0 if ictx is None else len(ictx.acts)}

    # ---------- estimator + round bookkeeping ----------
    mnot_prev = reader.estimator.mnot_next[cur_group]
    n_hat = reader.estimator.update(cur_group, k, aloha.successes, aloha.collisions, aloha.empties, max(1e-8, pstar))
    by_sub = {
        SUBTYPE_LABEL[c]: int((world.identified & (world.subtype_code == c)).sum()) for c in range(len(SUBTYPE_LABEL))
    }
    if ictx is not None or ix_total:
        emit._rounds[handle].metadata_json["interference"] = result.interference
    emit.finish_round(
        handle,
        t_end_s=t_end,
        success=aloha.successes,
        collision=aloha.collisions,
        empty=aloha.empties,
        extra={
            "candidates": int(candidates.size),
            "joiners": int((join_mask).sum()),
            "on_at_page": on_at_page,
            "backlog_true": backlog_true,
            "served": int(result.identified),
            "s_budget": int(s_budget),
            "budget_dropped": int(budget_dropped.size),
            "n_hat": n_hat,
            "mnot_prev": None if mnot_prev is None else int(mnot_prev),
            "mnot_next": reader.estimator.mnot_next[cur_group],
            "n_done_total": int(world.identified.sum()),
            "identified_json": by_sub,
            "timing_json": {
                "paging": T_pg,
                "m1": T_m1_phase,
                "ebi": T_ebi,
                "m2": s_m2_time * T_m2,
                "m3": n_m3_slots * T_m3,
            },
            "energy_json": stats.energy_json(),
            "deaths_json": stats.deaths_json(),
            "slots_json": {
                "f": F_r,
                "subbands": list(subbands),
                "occ": aloha.occupancy.astype(int).tolist(),
                "res": aloha.slot_result.astype(int).tolist(),
            },
        },
    )
    emit.emit_reader(
        reader_id=rid, round_handle=handle, t_s=t_end, event_type="round_end",
        payload={"success": aloha.successes, "collision": aloha.collisions, "empty": aloha.empties},
    )
    result.t_frame = t_frame
    result.k = k
    result.pstar = pstar
    result.success = int(aloha.successes)
    result.collision = int(aloha.collisions)
    result.empty = int(aloha.empties)
    return result


# ----------------------------------------------------------- helpers


def _slot_time(t_m1_start: float, slot: int, F: int, T_m1: float) -> float:
    """Start time of an M1 slot: K slots are laid out F per T_M1 period."""
    return t_m1_start + (slot // F) * T_m1


def _paging_acquired(world: DeviceWorld, joiners: np.ndarray, rid: int, t: float) -> None:
    """Per-device metrics at a successful paging acquisition (the device joins ``rid``)."""
    if joiners.size == 0:
        return
    pending = np.isfinite(world.t_last_fail[joiners])
    if pending.any():
        idx = joiners[pending]
        gap = t - world.t_last_fail[idx]
        world.fail_to_page_sum[idx] += gap
        world.fail_to_page_max[idx] = np.maximum(world.fail_to_page_max[idx], gap)
        world.fail_to_page_count[idx] += 1
        world.t_last_fail[idx] = np.nan
    prev = world.last_reader[joiners]
    changed = (prev >= 0) & (prev != rid) & world.went_off[joiners]
    world.reader_changes[joiners[changed]] += 1
    world.last_reader[joiners] = rid
    world.went_off[joiners] = False


def _r2d_lost(
    ictx: "FrameInterference",
    reader: ReaderState,
    devs: np.ndarray,
    t_a: float,
    t_b: float,
    subbands: frozenset[int],
    sir_lin: float,
) -> np.ndarray:
    """Devices whose SIR for this reader's R2D signal falls below the target."""
    interference = ictx.device_interference_w(devs, t_a, t_b, subbands)
    signal = reader.Ph_contrib[devs]
    return (interference > 0) & (signal < sir_lin * interference)


def _d2r_decodable(
    ictx: "FrameInterference",
    coord: "Coordinator",
    a: int,
    devs: np.ndarray,
    positions: np.ndarray,
    t_start: float,
    T: float,
    subbands: tuple[int, ...],
    reader: ReaderState,
    *,
    slot_period: bool,
) -> np.ndarray:
    """D2R SINR verdict for uplink transmissions at resource ``positions``.

    Resource ``p`` sits in subband ``subbands[p % F_r]`` during period ``p // F_r``.
    """
    F_r = len(subbands)
    signal = coord.d2r_rx_dbm(devs, a)
    cache: dict[tuple[int, int], float] = {}
    interference = np.zeros(devs.size)
    for i, p in enumerate(positions):
        key = (int(p) // F_r, subbands[int(p) % F_r])
        val = cache.get(key)
        if val is None:
            t_a = t_start + key[0] * T
            val = cache[key] = ictx.reader_interference_w(t_a, t_a + T, key[1])
        interference[i] = val
    sinr = coord.sinr_db(signal, interference, a)
    reader.interference["sinr_sum_db"] += float(np.sum(sinr[interference > 0]))
    reader.interference["sinr_n"] += int((interference > 0).sum())
    return (interference <= 0) | (sinr >= coord.spec.d2r_sinr_db)


def _frame_rx_cost(world: DeviceWorld, config: EpisodeConfig) -> np.ndarray:
    """Rough RX energy needed to survive the paging+EBI+M2+M3 window."""
    consts = config.consts
    t_total = consts.t_paging() + consts.t_m1() + (consts.t_ebi(16) if config.use_ebi else 0.0) + consts.t_m2() + consts.t_m3()
    return world.p_rx * t_total


def _debit(world: DeviceWorld, idx: np.ndarray, dt: float, power: np.ndarray, stats: _FrameStats) -> None:
    if idx.size == 0 or dt <= 0.0:
        return
    before = world.E[idx].copy()
    world.E[idx] = np.maximum(before - power[idx] * dt, 0.0)
    spent = before - world.E[idx]
    for c in range(len(SUBTYPE_LABEL)):
        stats.energy_j[c] += float(spent[world.subtype_code[idx] == c].sum())


def _deplete(
    world: DeviceWorld,
    idx: np.ndarray,
    stage: str,
    t_s: float,
    reader_id: int,
    handle: int,
    emit: EventEmitter,
    stats: _FrameStats,
    result: FrameResult,
    *,
    return_dead: bool = False,
) -> np.ndarray:
    """Force OFF + ungroup devices at or below Eoff (reference ``_kill``).

    Returns the survivors, or the depleted devices when ``return_dead``.
    """
    if idx.size == 0:
        return idx
    dead_mask = world.E[idx] <= world.Eoff[idx]
    dead = idx[dead_mask]
    for dev in dead:
        dev = int(dev)
        world.on[dev] = 0.0
        world.went_off[dev] = True
        world.grp[dev] = -1
        world.latched_reader[dev] = -1
        world.depletions[dev] += 1
        stats.deaths[stage][int(world.subtype_code[dev])] += 1
        result.touched[dev] = STATE_DEPLETED
        result.depleted += 1
        _dev_event(emit, world, reader_id, handle, t_s, dev, "depleted", cause=stage)
    return dead if return_dead else idx[~dead_mask]


def _dev_event(
    emit: EventEmitter,
    world: DeviceWorld,
    reader_id: int,
    handle: int,
    t_s: float,
    dev: int,
    event_type: str,
    *,
    cause: str | None = None,
    payload: dict | None = None,
) -> None:
    emit.emit_device(
        device_id=int(world.placement_ids[dev]),
        reader_id=reader_id,
        round_handle=handle,
        t_s=t_s,
        event_type=event_type,
        cause=cause,
        energy_j=float(world.E[dev]),
        # Remaining on timer: with E it pins the device's energy evolution until its next event.
        payload={**(payload or {}), "on_s": float(world.on[dev])},
    )


def _rx_power_at_reader(world: DeviceWorld, reader: ReaderState, joiners: np.ndarray) -> np.ndarray:
    """Approximate per-joiner received power at the reader (dBm), used for capture ordering."""
    from app.simulator_thesis.inventory.energy import _pl_nlos_vector

    if joiners.size == 0:
        return np.array([])
    d3 = reader.d3d[joiners]
    pl = _pl_nlos_vector(d3, float(reader.rf.get("carrier_ghz", 0.9)))
    is_active = world.uplink_code[joiners] == UPLINK_ACTIVE
    return np.where(
        is_active,
        world.active_tx_power_dbm[joiners] - pl,
        -world.backscatter_loss_db[joiners] + world.backscatter_gain_db[joiners] - pl,
    )
