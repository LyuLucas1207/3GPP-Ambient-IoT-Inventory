"""Multi-reader episode, split into build / step / finish so it can be paced,
paused, checkpointed and resumed.

``build_episode`` turns the scene snapshot into a :class:`EpisodeState`;
``step_episode`` advances the earliest-clock reader by exactly one frame;
``finish_episode`` handles the optional ``max_time_s`` cut-off. The episode
ends by itself once every device is terminal (identified, or dropped as
unreachable) or every reader has run out of devices to serve.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.thesis_simulator.catalog import spec_for  # noqa: F401  (kept for catalog alignment)
from app.thesis_simulator.inventory.config import CONSTANTS
from app.thesis_simulator.inventory.energy import (
    advance_availability,
    compute_reader_contribution,
    init_stationary,
)
from app.thesis_simulator.inventory.estimator import BacklogEstimator
from app.thesis_simulator.inventory.events import EventEmitter
from app.thesis_simulator.inventory.frame import FrameResult, run_one_frame
from app.thesis_simulator.inventory.state import (
    DROP_CAUSE_LABEL,
    DROP_MAX_TIME,
    DROP_NO_PROGRESS,
    DROP_UNREACHABLE,
    SUBTYPE_CODE,
    UPLINK_ACTIVE,
    UPLINK_BACKSCATTER,
    DeviceWorld,
    EpisodeConfig,
    ReaderState,
)
from app.thesis_simulator.physics import effective_coverage_m

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
            "dropped": int((w.dropped & ~np.isin(w.drop_cause, (DROP_UNREACHABLE, DROP_NO_PROGRESS))).sum()),
            "unreachable": int((w.dropped & (w.drop_cause == DROP_UNREACHABLE)).sum()),
            "depletions": int(self.depletions_total),
            "rounds": int(self.rounds_total),
            "frame_seq": int(self.frame_seq),
            "no_progress": int((w.dropped & (w.drop_cause == DROP_NO_PROGRESS)).sum()),
        }

    def stalled(self) -> bool:
        limit = self.config.stall_timeout_s
        return limit is not None and self.sim_time - self.last_progress_t >= limit


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
    world.Ph_total[:] = 0.0
    for r in readers:
        world.Ph_total += r.Ph_contrib
    if warm_start and world.N:
        init_stationary(world, rng)
    return EpisodeState(world=world, readers=readers, config=config, rng=rng)


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
    max_t = state.config.max_time_s
    alive = ~state.world.terminal_mask()
    out = []
    for r in state.readers:
        if not r.exhausted and not (r.cover_mask & alive).any():
            r.exhausted = True
        if r.exhausted:
            continue
        if max_t is not None and r.clock_s >= max_t:
            continue
        out.append(r)
    return out


def is_finished(state: EpisodeState) -> bool:
    return next_frame_time(state) is None


def next_frame_time(state: EpisodeState) -> float | None:
    """Simulated start time of the next frame (None when the episode is over)."""
    active = _active_readers(state)
    if state.world.N == 0 or state.world.all_terminal() or not active or state.stalled():
        return None
    return min(r.clock_s for r in active)


def step_episode(state: EpisodeState, emit: EventEmitter) -> FrameResult | None:
    """Run one frame on the earliest-clock reader. Returns None when finished."""
    active = _active_readers(state)
    if state.world.N == 0 or state.world.all_terminal() or not active or state.stalled():
        return None
    reader = min(active, key=lambda r: (r.clock_s, r.reader_id))
    world = state.world
    dt = reader.clock_s - state.sim_time
    if dt > 0:
        advance_availability(dt, world, freeze=world.terminal_mask())
        state.sim_time = reader.clock_s
    emit.frame_seq = state.frame_seq + 1  # rows of this frame; resume truncates rows past the checkpoint
    result = run_one_frame(reader, world, state.config, state.rng, emit)
    reader.clock_s += result.t_frame
    reader.round_index += 1
    state.frame_seq += 1
    state.depletions_total += result.depleted
    state.overlays[reader.reader_id] = result.touched
    if result.identified:
        state.last_progress_t = state.sim_time
    return result


def finish_episode(state: EpisodeState, emit: EventEmitter) -> None:
    """Close the episode, dropping whoever is still pending:

    * ``max_time_reached`` when the optional time cap was hit;
    * ``no_progress`` when nothing was identified for ``stall_timeout_s``.

    An episode that ended because every device is terminal drops nobody.
    """
    world = state.world
    emit.frame_seq = state.frame_seq
    if world.all_terminal():
        state.overlays.clear()
        return
    max_t = state.config.max_time_s
    if state.stalled():
        cause, t_end = DROP_NO_PROGRESS, state.sim_time
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
        reader = ReaderState(
            reader_id=rid,
            x_m=float(p["x_m"]),
            y_m=float(p["y_m"]),
            rf=rf,
            include_d2r=include_d2r,
            freq_subband=rid % CONSTANTS.f_freq,
            clock_s=start_offset,
            round_index=0,
            estimator=BacklogEstimator(groups=max(1, config.g if config.use_grouping else 1), consts=config.consts),
            cover_mask=_build_cover_mask(p, world, include_d2r),
            Ph_contrib=np.zeros(world.N),
            d3d=np.zeros(world.N),
        )
        reader.Ph_contrib = compute_reader_contribution(reader, world)
        reader.d3d = _distances(reader, world)
        readers.append(reader)
    return readers


def _build_cover_mask(reader_placement: dict[str, Any], world: DeviceWorld, include_d2r: bool) -> np.ndarray:
    """Devices within this reader's effective coverage disk.

    The coverage radius depends only on the device's radio parameters, so it is
    computed once per distinct parameter set (a 10k-device scene has a handful)
    and the distance test is vectorized.
    """
    rf = dict(reader_placement.get("params", {}) or {})
    rx = float(reader_placement["x_m"])
    ry = float(reader_placement["y_m"])
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
    return np.hypot(world.x_m - rx, world.y_m - ry) <= radius


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
