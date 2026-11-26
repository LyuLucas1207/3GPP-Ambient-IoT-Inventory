"""Multi-reader episode, split into build / step / finish so it can be paced,
paused, checkpointed and resumed.

``build_episode`` turns the scene snapshot into a :class:`EpisodeState`;
``step_episode`` advances the earliest-clock reader by exactly one frame;
``finish_episode`` handles the optional ``max_time_s`` cut-off. The episode
ends by itself once every device is terminal (identified, or dropped as
unreachable), every reader has run out of devices to serve, or every reader
stopped on its termination rule (``inventory/termination.py``).

The :class:`~app.simulator_thesis.coordination.coordinator.Coordinator`
grants each reader its subbands, may defer a frame start (TDMA windows,
listen-before-talk) and supplies the interference a frame sees.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.simulator_thesis import physics
from app.simulator_thesis.catalog import spec_for  # noqa: F401  (kept for catalog alignment)
from app.simulator_thesis.coordination.coordinator import Coordinator
from app.simulator_thesis.inventory.config import CONSTANTS
from app.simulator_thesis.inventory.controller import FrameRecord
from app.simulator_thesis.inventory.energy import (
    _pl_nlos_vector,
    advance_availability,
    compute_reader_contribution,
    harvested_power_w,
    incident_cw_w,
    init_full,
    init_stationary,
)
from app.simulator_thesis.inventory.estimator import BacklogEstimator
from app.simulator_thesis.inventory.events import EventEmitter
from app.simulator_thesis.inventory.frame import FrameResult, run_one_frame
from app.simulator_thesis.inventory.state import (
    DROP_CAUSE_LABEL,
    DROP_MAX_TIME,
    DROP_NO_PROGRESS,
    DROP_TERMINATED,
    DROP_UNREACHABLE,
    SUBTYPE_CODE,
    UPLINK_ACTIVE,
    UPLINK_BACKSCATTER,
    DeviceWorld,
    EpisodeConfig,
    ReaderState,
)
from app.simulator_thesis.inventory.termination import (
    _all_specs,
    advance_empty,
    empty_frames_to_stop,
    energy_wait_s,
    evaluate,
    observe,
    worst_case_recharge_s,
)
from app.simulator_thesis.physics import effective_coverage_m

SNAPSHOT_EVERY_S = 0.5
"""Simulated-time spacing of persisted device-state snapshots."""


@dataclass
class EpisodeState:
    world: DeviceWorld
    readers: list[ReaderState]
    config: EpisodeConfig
    rng: np.random.Generator
    sim_time: float = 0.0
    frame_seq: int = 0
    next_snapshot_t: float = 0.0
    depletions_total: int = 0
    last_progress_t: float = 0.0  # sim time of the latest identification
    # reader_id -> {device idx: transient state code} from that reader's last frame
    overlays: dict[int, dict[int, int]] = field(default_factory=dict)
    coord: Coordinator | None = None

    @property
    def rounds_total(self) -> int:
        return sum(r.round_index for r in self.readers)

    def state_codes(self) -> np.ndarray:
        codes = self.world.base_state_codes()
        terminal = self.world.terminal_mask()
        for overlay in self.overlays.values():
            for dev, code in overlay.items():
                if not terminal[dev]:
                    codes[dev] = code
        return codes

    def counters(self) -> dict[str, Any]:
        w = self.world
        by_sub = {label: int((w.identified & (w.subtype_code == code)).sum()) for label, code in SUBTYPE_CODE.items()}
        return {
            "sim_time_s": float(self.sim_time),
            "total": int(w.N),
            "identified": int(w.identified.sum()),
            "identified_by_subtype": by_sub,
            "dropped": int((w.dropped & ~np.isin(w.drop_cause, (DROP_UNREACHABLE, DROP_NO_PROGRESS, DROP_TERMINATED))).sum()),
            "unreachable": int((w.dropped & (w.drop_cause == DROP_UNREACHABLE)).sum()),
            "depletions": int(self.depletions_total),
            "rounds": int(self.rounds_total),
            "frame_seq": int(self.frame_seq),
            "no_progress": int((w.dropped & (w.drop_cause == DROP_NO_PROGRESS)).sum()),
            "terminated_early": int((w.dropped & (w.drop_cause == DROP_TERMINATED)).sum()),
            "readers_stopped": int(sum(1 for r in self.readers if r.stopped)),
        }

    def stall_limit(self) -> float | None:
        """``stall_timeout_s``, widened for ``energy_bound`` rules so the guard never
        cuts a reader that is still waiting out its worst-case recharge time."""
        limit = self.config.stall_timeout_s
        spec = self.config.termination
        if limit is None or spec.is_oracle:
            return limit
        waits = [
            w for s in _all_specs(spec) if s.kind == "energy_bound"
            for w in (energy_wait_s(s, r.t_wc_s) for r in self.readers) if w is not None
        ]
        if waits:
            limit = max(limit, 1.2 * max(waits))
        return limit

    def stalled(self) -> bool:
        limit = self.stall_limit()
        return limit is not None and self.sim_time - self.last_progress_t >= limit

    def reader_summary(self) -> dict[str, Any]:
        """Per-reader termination / coordination / interference state (run summary)."""
        coord = self.coord.summary() if self.coord is not None else {"readers": {}}
        out: dict[str, Any] = {}
        for r in self.readers:
            info = dict(coord["readers"].get(int(r.reader_id), {}))
            info.update({
                "rounds": int(r.round_index),
                "clock_s": float(r.clock_s),
                "stopped": bool(r.stopped),
                "stop_reason": r.term.stopped_reason,
                "stop_t": r.term.stopped_t,
                "t_wc_s": None if r.t_wc_s is None or not math.isfinite(r.t_wc_s) else float(r.t_wc_s),
                "exhausted": bool(r.exhausted),
                "interference": dict(r.interference),
                "f_r": int(r.f_r),
            })
            out[str(r.reader_id)] = info
        return {"mode": coord.get("mode", "independent"), "n_colors": coord.get("n_colors", 1), "readers": out}


def build_episode(
    snapshot: dict[str, Any],
    config: EpisodeConfig,
    rng: np.random.Generator,
    *,
    warm_start: bool = True,
) -> EpisodeState:
    """Build world + readers from the scene. ``warm_start=False`` skips the
    random stationary energy init (used when restoring from a checkpoint)."""
    placements = snapshot.get("placements", [])
    world = _build_world(placements)
    readers = _build_readers(placements, world, config) if world.N else []
    # Paper multi-source harvest: every BS transmits CW. Readers page; stations
    # only add incident power (no paging, no extra uplink interference).
    pin_total = np.zeros(world.N)
    for r in readers:
        pin_total += r.Ph_contrib
    if config.station_cw:
        for p in placements:
            if p.get("kind") != "station":
                continue
            pin_total += incident_cw_w(float(p["x_m"]), float(p["y_m"]), dict(p.get("params") or {}), world)
    world.Ph_total[:] = harvested_power_w(pin_total)
    if readers:
        world.readers_in_range[:] = np.sum([r.cover_mask for r in readers], axis=0).astype(np.int16)
    _assign_recharge_bounds(readers, world, config)
    if warm_start and world.N:
        if config.full_energy:
            init_full(world)
        else:
            init_stationary(world, rng)
    coord = Coordinator(config.resource, readers, world, config) if readers else None
    width = float(snapshot.get("width_m") or 120.0)
    height = float(snapshot.get("height_m") or 60.0)
    for i, r in enumerate(readers):
        offset = config.reader_start_offsets.get(str(r.reader_id), config.reader_start_offsets.get(r.reader_id, 0.0))
        r.context = {
            "n_readers": float(len(readers)),
            "neighbors": float(coord.adj[i].sum()) if coord is not None else 0.0,
            "color": float(r.color),
            "n_colors": float(coord.n_colors) if coord is not None else 1.0,
            "start_offset_s": float(offset),
            "x_norm": r.x_m / width if width > 0 else 0.0,
            "y_norm": r.y_m / height if height > 0 else 0.0,
            "slot": float(i),
        }
    return EpisodeState(world=world, readers=readers, config=config, rng=rng, coord=coord)


def mark_unreachable(state: EpisodeState, emit: EventEmitter) -> int:
    """Drop devices no enabled reader can ever serve (outside every coverage
    disk). Without this an open-ended run could never finish."""
    world = state.world
    covered = np.zeros(world.N, dtype=bool)
    for r in state.readers:
        covered |= r.cover_mask
    lost = np.nonzero(~covered & ~world.terminal_mask())[0]
    for dev in lost:
        world.dropped[dev] = True
        world.drop_cause[dev] = DROP_UNREACHABLE
        emit.emit_device(
            device_id=int(world.placement_ids[dev]),
            reader_id=None,
            round_handle=None,
            t_s=0.0,
            event_type="dropped",
            cause=DROP_CAUSE_LABEL[DROP_UNREACHABLE],
            energy_j=float(world.E[dev]),
        )
    return int(lost.size)


def _active_readers(state: EpisodeState) -> list[ReaderState]:
    """Readers that may run another frame.

    Under the ``oracle`` rule a reader with nothing left to serve is dropped at
    once (it "knows" it is done). Under any other rule it keeps paging until its
    rule fires, as a real reader would.
    """
    max_t = state.config.max_time_s
    oracle = state.config.termination.is_oracle
    alive = ~state.world.terminal_mask()
    out = []
    for r in state.readers:
        if not r.exhausted and not (r.cover_mask & alive).any():
            r.exhausted = True
        if r.stopped or (oracle and r.exhausted):
            continue
        if max_t is not None and r.clock_s >= max_t:
            continue
        out.append(r)
    return out


def is_finished(state: EpisodeState) -> bool:
    return next_frame_time(state) is None


def _done_serving(state: EpisodeState) -> bool:
    """Nothing is left to identify (every reader exhausted)."""
    return state.world.all_terminal() or all(r.exhausted for r in state.readers)


def next_frame_time(state: EpisodeState) -> float | None:
    """Simulated start time of the next frame (None when the episode is over)."""
    active = _active_readers(state)
    if state.world.N == 0 or _done_serving(state) or not active or state.stalled():
        return None
    return min(r.clock_s for r in active)


def _empty_frame_s(reader: ReaderState, others: list[ReaderState]) -> float:
    for h in reversed(reader.history):
        if h.new_ids == 0:
            return h.t_end - h.t_start
    if reader.history:
        return reader.history[-1].t_end - reader.history[-1].t_start
    durations = [o.history[-1].t_end - o.history[-1].t_start for o in others if o.history]
    return float(np.median(durations)) if durations else 0.0


def fast_forward_tail(state: EpisodeState, emit: EventEmitter) -> None:
    """Once nothing is left to identify, every reader that has not stopped
    would only page empty frames until its rule fires; jump there in closed form."""
    spec = state.config.termination
    if spec.is_oracle or not _done_serving(state):
        return
    max_t = state.config.max_time_s
    t_end = state.sim_time
    for r in state.readers:
        if r.stopped:
            t_end = max(t_end, r.term.stopped_t or r.clock_s)
            continue
        frame_s = _empty_frame_s(r, state.readers)
        limit = None
        if max_t is not None and frame_s > 0:
            limit = max(0, int(math.floor((max_t - r.clock_s) / frame_s)))
        hit = empty_frames_to_stop(spec, r.term, r.clock_s, frame_s, r.t_wc_s, max_frames=limit if limit is not None else 10**9)
        if hit is None:
            n = limit or 0
            advance_empty(r.term, spec, n, r.clock_s, frame_s)
            r.clock_s += n * frame_s
            r.round_index += n
            t_end = max(t_end, r.clock_s)
            continue
        n, reason = hit
        advance_empty(r.term, spec, n, r.clock_s, frame_s)
        r.clock_s += n * frame_s
        r.round_index += n
        r.stopped = True
        r.term.stopped_reason = reason
        r.term.stopped_t = r.clock_s
        r.interference["tail_frames"] = r.interference.get("tail_frames", 0) + n
        emit.emit_reader(reader_id=r.reader_id, round_handle=None, t_s=r.clock_s, event_type="terminated",
                         payload={"reason": reason, "tail_frames": n})
        t_end = max(t_end, r.clock_s)
    state.sim_time = max(state.sim_time, t_end)


def _pick_reader(state: EpisodeState, active: list[ReaderState]) -> ReaderState | None:
    """Earliest-clock reader whose start is allowed by the coordination policy."""
    coord = state.coord
    max_t = state.config.max_time_s
    for _ in range(10_000):
        if not active:
            return None
        reader = min(active, key=lambda r: (r.clock_s, r.reader_id))
        if coord is None or coord.spec.mode not in ("tdma", "hybrid", "lbt"):
            return reader
        start = coord.next_start(reader, reader.clock_s, state.rng)
        if start <= reader.clock_s:
            return reader
        reader.interference["deferred_s"] += start - reader.clock_s
        reader.interference["deferrals"] += 1
        reader.clock_s = start
        if max_t is not None and start >= max_t:
            active = [r for r in active if r is not reader]
    raise RuntimeError("coordination kept deferring every reader")


def step_episode(state: EpisodeState, emit: EventEmitter) -> FrameResult | None:
    """Run one frame on the earliest-clock reader. Returns None when finished."""
    active = _active_readers(state)
    if state.world.N == 0 or _done_serving(state) or not active or state.stalled():
        return None
    reader = _pick_reader(state, active)
    if reader is None:
        return None
    world = state.world
    dt = reader.clock_s - state.sim_time
    if dt > 0:
        advance_availability(dt, world, freeze=world.terminal_mask())
        state.sim_time = reader.clock_s
    coord = state.coord
    ictx = None
    if coord is not None:
        coord.prune(min(r.clock_s for r in active))
        ictx = coord.context(reader, reader.clock_s, active)
    emit.frame_seq = state.frame_seq + 1  # rows of this frame; resume truncates rows past the checkpoint
    t0 = reader.clock_s
    result = run_one_frame(reader, world, state.config, state.rng, emit, coord=coord, ictx=ictx)
    if coord is not None and result.activity is not None:
        coord.commit(reader, t0, t0 + result.t_frame, result.activity)
    if result.interference and sum(v for k, v in result.interference.items() if k.endswith("_lost")):
        reader.interference["frames_hit"] += 1
        for key in ("r2d_lost", "m1_lost", "m2_lost", "m3_lost"):
            reader.interference[key] += int(result.interference.get(key, 0))
    reader.clock_s += result.t_frame
    reader.round_index += 1
    t_end = t0 + result.t_frame
    reader.history.append(FrameRecord(
        t_start=t0, t_end=t_end, k=result.k, pstar=result.pstar, success=result.success,
        collision=result.collision, empty=result.empty, new_ids=result.identified,
        joiners=result.joiners, f_r=result.f_r, new_by_subtype=result.new_by_subtype,
    ))
    spec = state.config.termination
    observe(reader.term, spec, t0, t_end, result.identified)
    if not spec.is_oracle:
        reason = evaluate(spec, reader.term, t_end, reader.t_wc_s)
        if reason:
            reader.stopped = True
            reader.term.stopped_reason = reason
            reader.term.stopped_t = t_end
            emit.emit_reader(reader_id=reader.reader_id, round_handle=None, t_s=t_end, event_type="terminated", payload={"reason": reason})
    state.frame_seq += 1
    state.depletions_total += result.depleted
    state.overlays[reader.reader_id] = result.touched
    if result.identified:
        state.last_progress_t = state.sim_time
    return result


def finish_episode(state: EpisodeState, emit: EventEmitter) -> None:
    """Close the episode, dropping whoever is still pending:

    * ``max_time_reached`` when the optional time cap was hit;
    * ``no_progress`` when nothing was identified for ``stall_timeout_s``;
    * ``terminated_early`` when every reader stopped on its termination rule.

    An episode that ended because every device is terminal drops nobody.
    """
    world = state.world
    emit.frame_seq = state.frame_seq
    fast_forward_tail(state, emit)
    if world.all_terminal():
        state.overlays.clear()
        return
    max_t = state.config.max_time_s
    rule_stopped = any(r.stopped for r in state.readers) and all(r.stopped or r.exhausted for r in state.readers)
    if state.stalled():
        cause, t_end = DROP_NO_PROGRESS, state.sim_time
    elif rule_stopped:
        t_stop = max((r.term.stopped_t or 0.0) for r in state.readers)
        if t_stop > state.sim_time:
            advance_availability(t_stop - state.sim_time, world, freeze=world.terminal_mask())
            state.sim_time = t_stop
        cause, t_end = DROP_TERMINATED, state.sim_time
    elif max_t is not None:
        if state.sim_time < max_t:
            advance_availability(max_t - state.sim_time, world, freeze=world.terminal_mask())
            state.sim_time = max_t
        cause, t_end = DROP_MAX_TIME, max_t
    else:
        cause, t_end = DROP_NO_PROGRESS, state.sim_time  # every reader exhausted
    for dev in np.nonzero(~world.terminal_mask())[0]:
        world.dropped[dev] = True
        world.drop_cause[dev] = cause
        emit.emit_device(
            device_id=int(world.placement_ids[dev]),
            reader_id=None,
            round_handle=None,
            t_s=t_end,
            event_type="dropped",
            cause=DROP_CAUSE_LABEL[cause],
            energy_j=float(world.E[dev]),
        )
    state.overlays.clear()


def _assign_recharge_bounds(readers: list[ReaderState], world: DeviceWorld, config: EpisodeConfig) -> None:
    """Worst-case recharge time per reader for the ``energy_bound`` rule.

    ``edge``: link-budget worst case the reader can compute from device-type
    knowledge alone - every covered device placed at its type's coverage edge
    and charged by this reader only. ``actual``: the true minimum harvested
    power among covered devices (CW from every reader and station), an oracle variant.
    """
    bounds = [s for s in _all_specs(config.termination) if s.kind == "energy_bound"]
    source = "actual" if bounds and all(s.energy_source == "actual" for s in bounds) else "edge"
    caps = [s.edge_cap_m for s in bounds if s.energy_source == "edge"]
    edge_cap = max(caps) if caps and None not in caps else None
    for r in readers:
        cov = r.cover_mask
        if not cov.any():
            r.t_wc_s = 0.0
            continue
        if source == "actual":
            ph = world.Ph_total[cov]
        else:
            radius = r.coverage_radius[cov]
            if edge_cap is not None:
                radius = np.minimum(radius, edge_cap)
            d3 = np.sqrt(radius * radius + (physics.H_BS - physics.H_AIOT) ** 2)
            rf = r.rf
            pin_dbm = (
                float(rf.get("tx_power_dbm", physics.P_TX_CW_DBM)) + float(rf.get("antenna_gain_dbi", physics.G_TX_ANT_DBI))
                - _pl_nlos_vector(d3, float(rf.get("carrier_ghz", physics.FC_GHZ)))
                - physics.FIXED_DEV_DB - physics.L_OBJ_DB - float(rf.get("extra_attenuation_db", 0.0))
            )
            ph = harvested_power_w(10.0 ** ((pin_dbm - 30.0) / 10.0))
        t_on = np.maximum(world.T_on_default[cov], world.T_on_dcm[cov])
        r.t_wc_s = worst_case_recharge_s(ecap=world.Ecap[cov], eoff=world.Eoff[cov], ph=ph, t_on=t_on)


def _build_world(placements: list[dict[str, Any]]) -> DeviceWorld:
    devices = [p for p in placements if p.get("kind") == "device"]
    n = len(devices)
    placement_ids = np.array([p["id"] for p in devices], dtype=np.int64)
    subtype_code = np.array([SUBTYPE_CODE.get(p.get("subtype", "1"), 0) for p in devices], dtype=np.int8)
    x = np.array([p["x_m"] for p in devices], dtype=np.float64)
    y = np.array([p["y_m"] for p in devices], dtype=np.float64)

    E = np.zeros(n)
    on = np.zeros(n)
    Ph_total = np.zeros(n)

    Ecap = np.zeros(n)
    Eoff = np.zeros(n)
    P_on = np.zeros(n)
    T_on_default = np.zeros(n)
    T_on_dcm = np.zeros(n)
    p_rx = np.zeros(n)
    p_tx = np.zeros(n)
    rx_sens = np.zeros(n)
    uplink_code = np.zeros(n, dtype=np.int8)
    bs_loss = np.zeros(n)
    bs_gain = np.zeros(n)
    active_tx = np.full(n, np.nan)

    for i, p in enumerate(devices):
        params = p.get("params", {}) or {}
        E_cap, E_off, P_on_i, T_on_i, T_on_dcm_i = _per_subtype_energy(subtype_code[i])
        Ecap[i] = E_cap
        Eoff[i] = E_off
        P_on[i] = P_on_i
        T_on_default[i] = T_on_i
        T_on_dcm[i] = T_on_dcm_i
        p_rx[i] = params.get("p_rx_w", _per_subtype_p_rx(subtype_code[i]))
        p_tx[i] = params.get("p_tx_w", _per_subtype_p_tx(subtype_code[i]))
        rx_sens[i] = params.get("rx_sensitivity_dbm", _per_subtype_sens(subtype_code[i]))
        uplink_code[i] = UPLINK_ACTIVE if params.get("uplink") == "active" else UPLINK_BACKSCATTER
        bs_loss[i] = params.get("backscatter_loss_db", 6.0)
        bs_gain[i] = params.get("backscatter_gain_db", 0.0 if subtype_code[i] != 1 else 10.0)
        atp = params.get("active_tx_power_dbm")
        if atp is not None:
            active_tx[i] = float(atp)

    world = DeviceWorld(
        placement_ids=placement_ids,
        subtype_code=subtype_code,
        x_m=x,
        y_m=y,
        E=E,
        on=on,
        Ph_total=Ph_total,
        Ecap=Ecap,
        Eoff=Eoff,
        P_on=P_on,
        T_on_default=T_on_default,
        T_on_dcm=T_on_dcm,
        p_rx=p_rx,
        p_tx=p_tx,
        rx_sens_dbm=rx_sens,
        uplink_code=uplink_code,
        backscatter_loss_db=bs_loss,
        backscatter_gain_db=bs_gain,
        active_tx_power_dbm=active_tx,
        include_d2r_default=True,
        grp=np.full(n, -1, dtype=np.int32),
        latched_reader=np.full(n, -1, dtype=np.int32),
        latched_until=np.full(n, -1.0, dtype=np.float64),
        attempts=np.zeros(n, dtype=np.int32),
        identified=np.zeros(n, dtype=bool),
        dropped=np.zeros(n, dtype=bool),
        drop_cause=np.zeros(n, dtype=np.int8),
        depletions=np.zeros(n, dtype=np.int32),
        identified_t=np.full(n, np.nan),
        identified_by=np.full(n, -1, dtype=np.int32),
    )
    return world


def _build_readers(placements: list[dict[str, Any]], world: DeviceWorld, config: EpisodeConfig) -> list[ReaderState]:
    radars = [p for p in placements if p.get("kind") == "radar"]
    disabled = frozenset(int(x) for x in (config.disabled_reader_ids or []))
    readers: list[ReaderState] = []
    for p in radars:
        rid = int(p["id"])
        if rid in disabled:
            continue
        start_offset = float(
            config.reader_start_offsets.get(str(rid), config.reader_start_offsets.get(rid, 0.0))
        )
        rf = dict(p.get("params", {}) or {})
        include_d2r = bool(rf.get("include_d2r", config.include_d2r))
        radius = _coverage_radius(p, world, include_d2r)
        reader = ReaderState(
            reader_id=rid,
            x_m=float(p["x_m"]),
            y_m=float(p["y_m"]),
            rf=rf,
            include_d2r=include_d2r,
            freq_subband=rid % config.consts.f_freq,
            clock_s=start_offset,
            round_index=0,
            estimator=BacklogEstimator(groups=max(1, config.g if config.use_grouping else 1), consts=config.consts),
            cover_mask=np.hypot(world.x_m - float(p["x_m"]), world.y_m - float(p["y_m"])) <= radius,
            Ph_contrib=np.zeros(world.N),
            d3d=np.zeros(world.N),
            coverage_radius=radius,
        )
        reader.Ph_contrib = compute_reader_contribution(reader, world)
        reader.d3d = _distances(reader, world)
        readers.append(reader)
    return readers


def _build_cover_mask(reader_placement: dict[str, Any], world: DeviceWorld, include_d2r: bool) -> np.ndarray:
    """Devices within this reader's effective coverage disk."""
    radius = _coverage_radius(reader_placement, world, include_d2r)
    rx = float(reader_placement["x_m"])
    ry = float(reader_placement["y_m"])
    return np.hypot(world.x_m - rx, world.y_m - ry) <= radius


def _coverage_radius(reader_placement: dict[str, Any], world: DeviceWorld, include_d2r: bool) -> np.ndarray:
    """Effective coverage radius (m) of this reader for every device.

    The coverage radius depends only on the device's radio parameters, so it is
    computed once per distinct parameter set (a 10k-device scene has a handful)
    and the distance test is vectorized.
    """
    rf = dict(reader_placement.get("params", {}) or {})
    radius = np.empty(world.N)
    cache: dict[tuple, float] = {}
    for i in range(world.N):
        active = None if np.isnan(world.active_tx_power_dbm[i]) else float(world.active_tx_power_dbm[i])
        key = (
            float(world.rx_sens_dbm[i]),
            int(world.uplink_code[i]),
            float(world.backscatter_loss_db[i]),
            float(world.backscatter_gain_db[i]),
            active,
        )
        r = cache.get(key)
        if r is None:
            dev_params = {
                "rx_sensitivity_dbm": key[0],
                "uplink": "active" if key[1] == UPLINK_ACTIVE else "backscatter",
                "backscatter_loss_db": key[2],
                "backscatter_gain_db": key[3],
                "active_tx_power_dbm": active,
            }
            r = cache[key] = float(effective_coverage_m(dev_params, rf, include_d2r=include_d2r))
        radius[i] = r
    return radius


def _distances(reader: ReaderState, world: DeviceWorld) -> np.ndarray:
    dx = world.x_m - reader.x_m
    dy = world.y_m - reader.y_m
    dz = 8.0 - 1.5
    return np.sqrt(dx * dx + dy * dy + dz * dz)


# ---------- per-subtype defaults (align with catalog) ----------

def _per_subtype_energy(code: int) -> tuple[float, float, float, float, float]:
    if code == 0:  # Device 1
        return 5e-6, 2.5e-6, 1e-6, 100e-3, 12e-3
    return 25e-6, 12.5e-6, 1e-6, 100e-3, 12e-3


def _per_subtype_p_rx(code: int) -> float:
    if code == 0:
        return 1e-6
    return 50e-6


def _per_subtype_p_tx(code: int) -> float:
    if code == 0:
        return 1e-6
    return 200e-6


def _per_subtype_sens(code: int) -> float:
    return (-36.0, -40.0, -70.0)[int(code)]
