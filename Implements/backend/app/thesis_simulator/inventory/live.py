"""Live inventory runs: a background thread per run, paced against the wall
clock, persisted frame by frame and fanned out to SSE subscribers.

Plumbing is standard library only: ``threading.Thread`` / ``threading.Event``
for the runner and its pause/stop/speed signals, ``queue.Queue`` per
subscriber. The SSE wire format is produced by FastAPI's built-in
``EventSourceResponse`` in the router.
"""

from __future__ import annotations

import base64
import logging
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Iterator

import numpy as np
from fastapi.sse import ServerSentEvent
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.thesis_simulator.inventory.checkpoint import dump_state, load_state
from app.thesis_simulator.inventory.episode import (
    SNAPSHOT_EVERY_S,
    EpisodeState,
    build_episode,
    finish_episode,
    mark_unreachable,
    next_frame_time,
    step_episode,
)
from app.thesis_simulator.inventory.events import EventEmitter
from app.thesis_simulator.inventory.state import STATE_LABELS, EpisodeConfig
from app.thesis_simulator.models import (
    ThesisDeviceEvent,
    ThesisInventoryRun,
    ThesisReaderEvent,
    ThesisRunCheckpoint,
    ThesisRunRound,
    ThesisRunSnapshot,
    ThesisRunSummary,
)
from app.thesis_simulator.serialize import round_out

log = logging.getLogger(__name__)

CHECKPOINT_EVERY_WALL_S = 5.0
FLUSH_EVERY_WALL_S = 0.25
"""Buffered rounds/events are written (COPY) and committed at most this often;
the SSE feed still gets every frame immediately."""
FLUSH_MAX_PENDING_EVENTS = 200_000
SUBSCRIBER_QUEUE_SIZE = 4096
MAX_LAG_S = 1.0
"""If the runner falls this far behind the wall clock (slow DB, huge frame),
re-anchor instead of bursting to catch up."""

TERMINAL_STATUSES = frozenset({"completed", "stopped", "failed"})
LIVE_STATUSES = frozenset({"pending", "running"})


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def b64(arr: np.ndarray) -> str:
    return base64.b64encode(np.ascontiguousarray(arr).tobytes()).decode("ascii")


# ------------------------------------------------------------------ fan-out


class Subscription:
    def __init__(self) -> None:
        self.queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=SUBSCRIBER_QUEUE_SIZE)
        self.overflow = False


class RunBus:
    """Fan one runner's messages out to every connected SSE client."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._subs: list[Subscription] = []

    def subscribe(self, initial: Callable[[], dict[str, Any] | None]) -> tuple[Subscription, dict[str, Any] | None]:
        # Taking the snapshot under the publish lock guarantees no frame falls
        # between the snapshot and the first queued message.
        sub = Subscription()
        with self._lock:
            snap = initial()
            self._subs.append(sub)
        return sub, snap

    def unsubscribe(self, sub: Subscription) -> None:
        with self._lock:
            if sub in self._subs:
                self._subs.remove(sub)

    def publish(self, message: dict[str, Any], *, before: Callable[[], None] | None = None) -> None:
        with self._lock:
            if before is not None:
                before()
            for sub in self._subs:
                try:
                    sub.queue.put_nowait(message)
                except queue.Full:
                    sub.overflow = True  # client resyncs from a fresh snapshot


# ------------------------------------------------------------------ runner


class LiveRunner(threading.Thread):
    def __init__(self, run_id: int, manager: "RunManager", *, speed: float | None) -> None:
        super().__init__(name=f"thesis-run-{run_id}", daemon=True)
        self.run_id = run_id
        self.manager = manager
        self.bus = manager.bus(run_id)
        self._speed = speed
        self._pause = threading.Event()
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._reanchor = True
        self._live_lock = threading.Lock()
        self._live: dict[str, Any] | None = None
        self.status = "pending"

    # ---------------------------------------------------------- controls
    @property
    def speed(self) -> float | None:
        return self._speed

    def set_speed(self, speed: float | None) -> None:
        self._speed = speed
        self._reanchor = True
        self._wake.set()
        self._publish_status()

    def request_pause(self) -> None:
        self._pause.set()
        self._wake.set()

    def request_stop(self) -> None:
        self._stop.set()
        self._wake.set()

    def live_snapshot(self) -> dict[str, Any] | None:
        with self._live_lock:
            return None if self._live is None else dict(self._live, status=self.status, speed=self._speed)

    def live_energy_b64(self) -> str | None:
        with self._live_lock:
            return None if self._live is None else self._live["energy_b64"]

    # ---------------------------------------------------------- thread body
    def run(self) -> None:
        from app.thesis_simulator.db import session_factory

        db = session_factory()()
        try:
            self._run(db)
        except Exception as exc:  # noqa: BLE001 - surface on the run row
            log.exception("thesis run %s failed", self.run_id)
            db.rollback()
            run = db.get(ThesisInventoryRun, self.run_id)
            if run is not None:
                run.status = "failed"
                run.error_detail = f"{type(exc).__name__}: {exc}"[:2000]
                run.completed_at = utcnow()
                run.updated_at = run.completed_at
                db.commit()
            self.status = "failed"
            self._publish_status()
        finally:
            db.close()
            self.manager._forget(self)

    def _run(self, db: Session) -> None:
        run = db.get(ThesisInventoryRun, self.run_id)
        if run is None:
            return
        config = EpisodeConfig.from_json(run.scheme, run.config_json or {})
        scene = dict(run.scene_snapshot_json or {})
        emit = EventEmitter(run_id=run.id)
        ckpt = db.get(ThesisRunCheckpoint, run.id)
        if ckpt is not None:
            state = load_state(ckpt.state_blob, scene, config)
            _truncate_after(db, run.id, ckpt.frame_seq)
            metrics = (run.summary.metrics_json or {}) if run.summary else {}
            emit.device_event_total = int(metrics.get("device_event_count", 0))
            emit.reader_event_total = int(metrics.get("reader_event_count", 0))
        else:
            _truncate_after(db, run.id, -1)
            seed = config.seed if config.seed is not None else int(run.id)
            state = build_episode(scene, config, np.random.default_rng(seed))
            mark_unreachable(state, emit)
            emit.flush(db)
            self._write_snapshot(db, state)

        run.status = "running"
        run.started_at = run.started_at or utcnow()
        run.completed_at = None
        run.updated_at = utcnow()
        self._write_summary(db, run, state, emit, 0.0)
        db.commit()
        self.status = "running"
        self._set_live(state)
        self._publish_status()

        active_since = time.monotonic()
        last_ckpt = last_flush = active_since
        prev_codes = state.state_codes()
        self._reanchor = True
        wall_anchor = sim_anchor = 0.0

        while True:
            # ---- real-time pacing: wait until the next frame's start time
            t_next = next_frame_time(state)
            speed = self._speed
            if t_next is not None and speed is not None and not (self._pause.is_set() or self._stop.is_set()):
                if self._reanchor:
                    wall_anchor, sim_anchor, self._reanchor = time.monotonic(), state.sim_time, False
                delay = wall_anchor + (t_next - sim_anchor) / speed - time.monotonic()
                if delay > 0:
                    self._wake.wait(delay)
                    self._wake.clear()
                    if self._reanchor or self._pause.is_set() or self._stop.is_set():
                        continue
                elif delay < -MAX_LAG_S:
                    self._reanchor = True

            if self._stop.is_set():
                self._persist(db, run, state, emit, time.monotonic() - active_since)
                self._end(db, run, state, emit, active_since, "stopped")
                return
            if self._pause.is_set():
                self._persist(db, run, state, emit, time.monotonic() - active_since)
                self._write_checkpoint(db, state)
                self._write_snapshot(db, state)
                self._finish_status(db, run, state, emit, active_since, "paused")
                return

            result = step_episode(state, emit)
            if result is None:
                finish_episode(state, emit)
                self._persist(db, run, state, emit, time.monotonic() - active_since)
                self._end(db, run, state, emit, active_since, "completed")
                return

            if state.sim_time >= state.next_snapshot_t:
                self._write_snapshot(db, state)  # ORM add only; inserted at the next flush
                state.next_snapshot_t = (int(state.sim_time / SNAPSHOT_EVERY_S) + 1) * SNAPSHOT_EVERY_S

            # Every frame goes to the browser right away ...
            codes = state.state_codes()
            changed = np.nonzero(codes != prev_codes)[0]
            prev_codes = codes
            self.bus.publish(
                {
                    "type": "frame",
                    "seq": state.frame_seq,
                    "sim_time_s": float(state.sim_time),
                    "changes": [[int(i), int(codes[i])] for i in changed],
                    "rounds": [],
                    "counters": state.counters(),
                },
                before=lambda: self._set_live(state, codes),
            )

            # ... while the database is written in batches.
            now = time.monotonic()
            if now - last_flush >= FLUSH_EVERY_WALL_S or emit.pending_event_count >= FLUSH_MAX_PENDING_EVENTS:
                if now - last_ckpt >= CHECKPOINT_EVERY_WALL_S:
                    emit_ckpt = True
                    last_ckpt = now
                else:
                    emit_ckpt = False
                self._persist(db, run, state, emit, now - active_since, checkpoint=emit_ckpt)
                last_flush = time.monotonic()

    def _persist(
        self,
        db: Session,
        run: ThesisInventoryRun,
        state: EpisodeState,
        emit: EventEmitter,
        active_wall_s: float,
        *,
        checkpoint: bool = False,
    ) -> None:
        """Write buffered rounds/events (+ optional checkpoint), commit, and
        publish the new round rows (they need their database ids)."""
        rounds = emit.flush(db)
        if checkpoint:
            self._write_checkpoint(db, state)
        self._write_summary(db, run, state, emit, active_wall_s)
        db.commit()
        if rounds:
            self.bus.publish(
                {
                    "type": "frame",
                    "seq": state.frame_seq,
                    "sim_time_s": float(state.sim_time),
                    "changes": [],
                    "rounds": [round_out(r) for r in rounds],
                    "counters": state.counters(),
                }
            )

    # ---------------------------------------------------------- terminal transitions
    def _end(self, db: Session, run: ThesisInventoryRun, state: EpisodeState, emit: EventEmitter, active_since: float, status: str) -> None:
        self._write_snapshot(db, state)
        ckpt = db.get(ThesisRunCheckpoint, run.id)
        if ckpt is not None:
            db.delete(ckpt)
        self._finish_status(db, run, state, emit, active_since, status)

    def _finish_status(self, db: Session, run: ThesisInventoryRun, state: EpisodeState, emit: EventEmitter, active_since: float, status: str) -> None:
        active = time.monotonic() - active_since
        run.duration_s = (run.duration_s or 0.0) + active
        run.status = status
        run.updated_at = utcnow()
        run.completed_at = run.updated_at if status in TERMINAL_STATUSES else None
        self._write_summary(db, run, state, emit, 0.0)
        db.commit()
        self.status = status
        self._set_live(state)
        self._publish_status()

    # ---------------------------------------------------------- persistence helpers
    def _write_snapshot(self, db: Session, state: EpisodeState) -> None:
        db.add(
            ThesisRunSnapshot(
                run_id=self.run_id,
                frame_seq=state.frame_seq,
                sim_time_s=float(state.sim_time),
                state_codes=state.state_codes().tobytes(),
                energy_j=state.world.E.astype(np.float32).tobytes(),
            )
        )

    def _write_checkpoint(self, db: Session, state: EpisodeState) -> None:
        blob = dump_state(state)
        ckpt = db.get(ThesisRunCheckpoint, self.run_id)
        if ckpt is None:
            db.add(ThesisRunCheckpoint(run_id=self.run_id, frame_seq=state.frame_seq, sim_time_s=state.sim_time, state_blob=blob))
        else:
            ckpt.frame_seq = state.frame_seq
            ckpt.sim_time_s = state.sim_time
            ckpt.state_blob = blob
            ckpt.created_at = utcnow()

    def _write_summary(self, db: Session, run: ThesisInventoryRun, state: EpisodeState, emit: EventEmitter, extra_wall: float) -> None:
        c = state.counters()
        summary = run.summary
        if summary is None:
            summary = ThesisRunSummary(run_id=run.id, identified_by_subtype_json={})
            db.add(summary)
            run.summary = summary
        summary.total_devices = c["total"]
        summary.identified_total = c["identified"]
        summary.identified_by_subtype_json = c["identified_by_subtype"]
        summary.died_count = c["depletions"]
        summary.dropped_count = c["dropped"] + c["unreachable"] + c["no_progress"]
        summary.rounds_total = c["rounds"]
        summary.wall_duration_s = float((run.duration_s or 0.0) + extra_wall)
        summary.metrics_json = {
            **c,
            "device_event_count": emit.device_event_total,
            "reader_event_count": emit.reader_event_total,
        }

    # ---------------------------------------------------------- live state for SSE
    def _set_live(self, state: EpisodeState, codes: np.ndarray | None = None) -> None:
        codes = state.state_codes() if codes is None else codes
        live = {
            "seq": state.frame_seq,
            "sim_time_s": float(state.sim_time),
            "state_codes_b64": b64(codes.astype(np.uint8)),
            "energy_b64": b64(state.world.E.astype(np.float32)),
            "counters": state.counters(),
        }
        with self._live_lock:
            self._live = live

    def _publish_status(self) -> None:
        self.bus.publish({"type": "status", "status": self.status, "speed": self._speed})


def _truncate_after(db: Session, run_id: int, frame_seq: int) -> None:
    """Delete rows a crashed/killed runner wrote after the checkpoint it resumes from."""
    for model in (ThesisDeviceEvent, ThesisReaderEvent, ThesisRunSnapshot, ThesisRunRound):
        db.execute(delete(model).where(model.run_id == run_id).where(model.frame_seq > frame_seq))
    db.flush()


# ------------------------------------------------------------------ registry


class RunManager:
    def __init__(self) -> None:
        # Re-entrant: start() holds it while LiveRunner.__init__ fetches its bus.
        self._lock = threading.RLock()
        self._runners: dict[int, LiveRunner] = {}
        self._buses: dict[int, RunBus] = {}

    def bus(self, run_id: int) -> RunBus:
        with self._lock:
            return self._buses.setdefault(run_id, RunBus())

    def get(self, run_id: int) -> LiveRunner | None:
        with self._lock:
            return self._runners.get(run_id)

    def start(self, run_id: int, *, speed: float | None, sync: bool = False) -> LiveRunner:
        with self._lock:
            existing = self._runners.get(run_id)
            if existing is not None:
                return existing
            runner = LiveRunner(run_id, self, speed=None if sync else speed)
            self._runners[run_id] = runner
        if sync:
            runner.run()
        else:
            runner.start()
        return runner

    def _forget(self, runner: LiveRunner) -> None:
        with self._lock:
            if self._runners.get(runner.run_id) is runner:
                del self._runners[runner.run_id]

    def pause_all(self, timeout_s: float = 10.0) -> None:
        """Checkpoint every live run (app shutdown / code reload)."""
        with self._lock:
            runners = list(self._runners.values())
        for r in runners:
            r.request_pause()
        deadline = time.monotonic() + timeout_s
        for r in runners:
            r.join(max(0.0, deadline - time.monotonic()))


manager = RunManager()


def recover_interrupted_runs() -> int:
    """At startup, runs left ``running``/``pending`` by a killed process become
    ``paused`` so the user can resume them from their last checkpoint."""
    from app.thesis_simulator.db import ensure_db, session_factory

    ensure_db()
    with session_factory()() as db:
        rows = db.scalars(
            select(ThesisInventoryRun)
            .where(ThesisInventoryRun.status.in_(tuple(LIVE_STATUSES)))
            .where(ThesisInventoryRun.deleted_at.is_(None))
        ).all()
        for run in rows:
            if manager.get(run.id) is None:
                run.status = "paused"
                run.updated_at = utcnow()
        db.commit()
        return len(rows)


def snapshot_payload(run: ThesisInventoryRun, db: Session) -> dict[str, Any]:
    """Snapshot of a run that is not live: latest persisted device states."""
    device_ids = scene_device_ids(run)
    row = db.scalars(
        select(ThesisRunSnapshot)
        .where(ThesisRunSnapshot.run_id == run.id)
        .order_by(ThesisRunSnapshot.frame_seq.desc(), ThesisRunSnapshot.id.desc())
        .limit(1)
    ).first()
    n = len(device_ids)
    if row is None:
        codes = np.zeros(n, dtype=np.uint8)
        energy = np.zeros(n, dtype=np.float32)
        seq, sim_t = 0, 0.0
    else:
        codes = np.frombuffer(row.state_codes, dtype=np.uint8)
        energy = np.frombuffer(row.energy_j, dtype=np.float32)
        seq, sim_t = row.frame_seq, row.sim_time_s
    metrics = (run.summary.metrics_json or {}) if run.summary else {}
    return {
        "run_id": run.id,
        "status": run.status,
        "speed": (run.config_json or {}).get("speed"),
        "seq": seq,
        "sim_time_s": float(sim_t),
        "device_ids": device_ids,
        "state_labels": list(STATE_LABELS),
        "state_codes_b64": b64(codes),
        "energy_b64": b64(energy),
        "counters": {k: metrics.get(k) for k in (
            "sim_time_s", "total", "identified", "identified_by_subtype", "dropped",
            "unreachable", "no_progress", "depletions", "rounds", "frame_seq",
        )},
    }


def scene_device_ids(run: ThesisInventoryRun) -> list[int]:
    placements = (run.scene_snapshot_json or {}).get("placements", [])
    return [int(p["id"]) for p in placements if p.get("kind") == "device"]


# ------------------------------------------------------------------ SSE stream

TICK_S = 0.1
"""Wall-clock batching window: every frame in it is merged into one ``tick``."""
ENERGY_EVERY_S = 1.0
"""Full per-device energy array is attached to a tick at most this often."""


def stream_events(run_id: int) -> Iterator[ServerSentEvent]:
    """SSE messages for one run (consumed by FastAPI's ``EventSourceResponse``).

    * ``snapshot`` - full device state; sent first and after any resync.
    * ``tick``     - merged frames: state changes, new rounds, counters.
    * ``status``   - running / paused / completed / stopped / failed, speed.
    * ``done``     - the run is not live any more; the client should close.
    """
    from app.thesis_simulator.db import session_factory

    with session_factory()() as db:
        run = db.get(ThesisInventoryRun, run_id)
        if run is None:
            return
        static = {"run_id": run.id, "device_ids": scene_device_ids(run), "state_labels": list(STATE_LABELS)}
        stored = snapshot_payload(run, db)

    runner = manager.get(run_id)
    sub: Subscription | None = None
    snap: dict[str, Any] | None = None
    if runner is not None:
        sub, snap = runner.bus.subscribe(runner.live_snapshot)
    try:
        first = stored if snap is None else {**stored, **static, **snap}
        yield ServerSentEvent(event="snapshot", data=first, id=str(first["seq"]))
        status = first["status"] if snap is not None else stored["status"]
        if runner is None or sub is None or (snap is not None and status not in LIVE_STATUSES):
            yield ServerSentEvent(event="done", data={"status": status})
            return

        last_energy = time.monotonic()
        while True:
            messages = _drain(sub.queue, TICK_S)
            if sub.overflow:
                sub.overflow = False
                _drain(sub.queue, 0.0)
                fresh = runner.live_snapshot()
                if fresh is not None:
                    fresh = {**stored, **static, **fresh}
                    yield ServerSentEvent(event="snapshot", data=fresh, id=str(fresh["seq"]))
                continue
            frames = [m for m in messages if m["type"] == "frame"]
            if frames:
                tick = _merge_frames(frames)
                if time.monotonic() - last_energy >= ENERGY_EVERY_S:
                    tick["energy_b64"] = runner.live_energy_b64()
                    last_energy = time.monotonic()
                yield ServerSentEvent(event="tick", data=tick, id=str(tick["seq"]))
            for msg in messages:
                if msg["type"] != "status":
                    continue
                yield ServerSentEvent(event="status", data={"status": msg["status"], "speed": msg["speed"]})
                if msg["status"] not in LIVE_STATUSES:
                    final = runner.live_snapshot()
                    if final is not None:
                        final = {**stored, **static, **final}
                        yield ServerSentEvent(event="snapshot", data=final, id=str(final["seq"]))
                    yield ServerSentEvent(event="done", data={"status": msg["status"]})
                    return
    finally:
        if runner is not None and sub is not None:
            runner.bus.unsubscribe(sub)


def _drain(q: "queue.Queue[dict[str, Any]]", window_s: float) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    deadline = time.monotonic() + window_s
    while True:
        remaining = deadline - time.monotonic()
        try:
            out.append(q.get(timeout=remaining) if remaining > 0 else q.get_nowait())
        except queue.Empty:
            return out


def _merge_frames(frames: list[dict[str, Any]]) -> dict[str, Any]:
    changes: dict[int, int] = {}
    rounds: list[dict[str, Any]] = []
    for f in frames:
        for idx, code in f["changes"]:
            changes[idx] = code
        rounds.extend(f["rounds"])
    last = frames[-1]
    return {
        "seq": last["seq"],
        "sim_time_s": last["sim_time_s"],
        "changes": [[i, c] for i, c in changes.items()],
        "rounds": rounds,
        "counters": last["counters"],
        "frames": len(frames),
    }
