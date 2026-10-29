"""Service layer for inventory runs + log queries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.thesis_runs import RunCreateIn
from app.thesis_simulator.inventory.live import LIVE_STATUSES, manager, scene_device_ids
from app.thesis_simulator.inventory.state import STATE_LABELS
from app.thesis_simulator.models import (
    ThesisDeviceEvent,
    ThesisInventoryRun,
    ThesisReaderEvent,
    ThesisRunCheckpoint,
    ThesisRunRound,
    ThesisRunSnapshot,
    ThesisSection,
)
from app.thesis_simulator.serialize import round_out, round_slots_out
from app.thesis_simulator.service import SceneError, get_section, iso, placement_out

INITIALIZED = "initialized"
CONTROL_WAIT_S = 10.0
"""How long pause/stop wait for the runner thread to reach a frame boundary."""

MAX_EVENTS_PER_PAGE = 5000
DEFAULT_EVENTS_PAGE = 1000


def _scene_snapshot(section: ThesisSection) -> dict[str, Any]:
    return {
        "section_id": section.id,
        "width_m": section.width_m,
        "height_m": section.height_m,
        "placements": [placement_out(item) for item in section.placements],
    }


def create_run(db: Session, section_id: int, body: RunCreateIn) -> ThesisInventoryRun:
    """Insert the run and hand it to a background runner (or run it inline when ``sync``)."""
    section = get_section(db, section_id)
    if section.status != INITIALIZED:
        raise SceneError("section_not_initialized")
    run = ThesisInventoryRun(
        section_id=section.id,
        scheme=body.scheme,
        status="pending",
        config_json=body.model_dump(exclude={"sync"}),
        scene_snapshot_json=_scene_snapshot(section),
    )
    db.add(run)
    db.commit()
    manager.start(run.id, speed=body.speed, sync=body.sync)
    db.expire_all()
    return get_run(db, run.id)


def list_runs(db: Session, section_id: int) -> list[dict[str, Any]]:
    section = get_section(db, section_id)
    rows = (
        db.scalars(
            select(ThesisInventoryRun)
            .where(ThesisInventoryRun.section_id == section.id)
            .where(ThesisInventoryRun.deleted_at.is_(None))
            .order_by(ThesisInventoryRun.created_at.desc(), ThesisInventoryRun.id.desc())
        )
        .all()
    )
    return [run_summary(run) for run in rows]


def get_run(db: Session, run_id: int, *, include_deleted: bool = False) -> ThesisInventoryRun:
    run = db.get(ThesisInventoryRun, run_id)
    if run is None or (not include_deleted and run.deleted_at is not None):
        raise SceneError("run_not_found", 404)
    return run


def soft_delete_run(db: Session, run_id: int) -> int:
    """Mark a run deleted and return its id. The actual cascade happens via
    :func:`hard_delete_run` on a background session so the request doesn't block
    on 100k-row DELETEs."""
    run = get_run(db, run_id)
    runner = manager.get(run_id)
    if runner is not None:
        runner.request_stop()
        runner.join(CONTROL_WAIT_S)
        db.expire_all()
        run = get_run(db, run_id)
    run.deleted_at = datetime.now(timezone.utc)
    run.status = "deleted"
    run.updated_at = run.deleted_at
    db.commit()
    return run.id


def hard_delete_run(run_id: int) -> None:
    """Cascade-delete a soft-deleted run using a fresh session.

    Run from a FastAPI BackgroundTasks callback so a slow cascade (hundreds of
    thousands of event rows) does not keep the client POST/DELETE pending.
    """
    from app.thesis_simulator.db import session_factory

    SessionLocal = session_factory()
    db = SessionLocal()
    try:
        run = db.get(ThesisInventoryRun, run_id)
        if run is None:
            return
        db.delete(run)
        db.commit()
    finally:
        db.close()


def pause_run(db: Session, run_id: int) -> ThesisInventoryRun:
    run = get_run(db, run_id)
    runner = manager.get(run_id)
    if runner is None or run.status not in LIVE_STATUSES:
        raise SceneError("run_not_running", 409)
    runner.request_pause()
    runner.join(CONTROL_WAIT_S)
    db.expire_all()
    return get_run(db, run_id)


def resume_run(db: Session, run_id: int) -> ThesisInventoryRun:
    run = get_run(db, run_id)
    if run.status != "paused":
        raise SceneError("run_not_paused", 409)
    run.status = "pending"
    run.updated_at = datetime.now(timezone.utc)
    db.commit()
    manager.start(run_id, speed=(run.config_json or {}).get("speed"))
    db.expire_all()
    return get_run(db, run_id)


def stop_run(db: Session, run_id: int) -> ThesisInventoryRun:
    """Finish a run for good (it cannot be resumed afterwards)."""
    run = get_run(db, run_id)
    runner = manager.get(run_id)
    if runner is not None:
        runner.request_stop()
        runner.join(CONTROL_WAIT_S)
        db.expire_all()
        return get_run(db, run_id)
    if run.status not in {"paused", "pending", "running"}:
        raise SceneError("run_not_running", 409)
    ckpt = db.get(ThesisRunCheckpoint, run_id)
    if ckpt is not None:
        db.delete(ckpt)
    run.status = "stopped"
    run.completed_at = datetime.now(timezone.utc)
    run.updated_at = run.completed_at
    db.commit()
    db.refresh(run)
    return run


def set_run_speed(db: Session, run_id: int, speed: float | None) -> ThesisInventoryRun:
    run = get_run(db, run_id)
    run.config_json = {**(run.config_json or {}), "speed": speed}
    run.updated_at = datetime.now(timezone.utc)
    db.commit()
    runner = manager.get(run_id)
    if runner is not None:
        runner.set_speed(speed)
    db.refresh(run)
    return run


def set_run_name(db: Session, run_id: int, name: str | None) -> ThesisInventoryRun:
    run = get_run(db, run_id)
    cfg = {**(run.config_json or {})}
    if name is None:
        cfg.pop("name", None)
    else:
        cfg["name"] = name
    run.config_json = cfg
    run.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(run)
    return run


def _run_name(cfg: dict[str, Any]) -> str | None:
    raw = cfg.get("name")
    if not isinstance(raw, str):
        return None
    cleaned = raw.strip()
    return cleaned or None


def run_summary(run: ThesisInventoryRun) -> dict[str, Any]:
    summary = run.summary
    cfg = run.config_json or {}
    metrics = (summary.metrics_json or {}) if summary else {}
    return {
        "run_id": run.id,
        "section_id": run.section_id,
        "scheme": run.scheme,
        "status": run.status,
        "name": _run_name(cfg),
        "total_devices": summary.total_devices if summary else len(scene_device_ids(run)),
        "identified_total": summary.identified_total if summary else 0,
        "identified_by_subtype": summary.identified_by_subtype_json if summary else {},
        "died_count": summary.died_count if summary else 0,
        "dropped_count": summary.dropped_count if summary else 0,
        "rounds_total": summary.rounds_total if summary else 0,
        "wall_duration_s": summary.wall_duration_s if summary else 0.0,
        "created_at": iso(run.created_at),
        "completed_at": iso(run.completed_at) if run.completed_at else None,
        "duration_s": run.duration_s,
        "sim_time_s": float(metrics.get("sim_time_s") or 0.0),
        "unreachable_count": int(metrics.get("unreachable") or 0),
        "speed": cfg.get("speed"),
        "max_time_s": cfg.get("max_time_s"),
        "include_d2r": bool(cfg.get("include_d2r", True)),
        "disabled_reader_ids": [int(x) for x in (cfg.get("disabled_reader_ids") or [])],
        "reader_start_groups": [[int(x) for x in g] for g in (cfg.get("reader_start_groups") or [])],
        "reader_start_interval_s": cfg.get("reader_start_interval_s"),
    }


def run_detail(run: ThesisInventoryRun) -> dict[str, Any]:
    cfg = run.config_json or {}
    return {
        "id": run.id,
        "section_id": run.section_id,
        "scheme": run.scheme,
        "status": run.status,
        "name": _run_name(cfg),
        "config": run.config_json,
        "scene_snapshot": run.scene_snapshot_json,
        "requested_at": iso(run.requested_at),
        "started_at": iso(run.started_at) if run.started_at else None,
        "completed_at": iso(run.completed_at) if run.completed_at else None,
        "duration_s": run.duration_s,
        "error_detail": run.error_detail,
        "summary": run_summary(run) if run.summary else None,
    }


def _clamp_limit(limit: int | None) -> int:
    if limit is None:
        return DEFAULT_EVENTS_PAGE
    return max(1, min(MAX_EVENTS_PER_PAGE, int(limit)))


def list_device_events(
    db: Session,
    run_id: int,
    *,
    device_id: int | None = None,
    since: float | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    get_run(db, run_id)
    stmt = select(ThesisDeviceEvent).where(ThesisDeviceEvent.run_id == run_id)
    if device_id is not None:
        stmt = stmt.where(ThesisDeviceEvent.device_id == device_id)
    if since is not None:
        stmt = stmt.where(ThesisDeviceEvent.t_s > float(since))
    cap = _clamp_limit(limit)
    stmt = stmt.order_by(ThesisDeviceEvent.t_s.asc(), ThesisDeviceEvent.id.asc()).limit(cap + 1)
    rows = db.scalars(stmt).all()
    has_more = len(rows) > cap
    rows = rows[:cap]
    next_since = rows[-1].t_s if has_more else None
    return {
        "events": [_device_event_out(row) for row in rows],
        "next_since": next_since,
    }


def list_reader_events(
    db: Session,
    run_id: int,
    *,
    reader_id: int | None = None,
    since: float | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    get_run(db, run_id)
    stmt = select(ThesisReaderEvent).where(ThesisReaderEvent.run_id == run_id)
    if reader_id is not None:
        stmt = stmt.where(ThesisReaderEvent.reader_id == reader_id)
    if since is not None:
        stmt = stmt.where(ThesisReaderEvent.t_s > float(since))
    cap = _clamp_limit(limit)
    stmt = stmt.order_by(ThesisReaderEvent.t_s.asc(), ThesisReaderEvent.id.asc()).limit(cap + 1)
    rows = db.scalars(stmt).all()
    has_more = len(rows) > cap
    rows = rows[:cap]
    next_since = rows[-1].t_s if has_more else None
    return {
        "events": [_reader_event_out(row) for row in rows],
        "next_since": next_since,
    }


def list_rounds(db: Session, run_id: int, *, reader_id: int | None = None) -> list[dict[str, Any]]:
    get_run(db, run_id)
    stmt = select(ThesisRunRound).where(ThesisRunRound.run_id == run_id)
    if reader_id is not None:
        stmt = stmt.where(ThesisRunRound.reader_id == reader_id)
    stmt = stmt.order_by(ThesisRunRound.t_start_s.asc(), ThesisRunRound.id.asc())
    return [round_out(row) for row in db.scalars(stmt).all()]


def round_slots(db: Session, run_id: int, round_id: int) -> dict[str, Any]:
    get_run(db, run_id)
    row = db.get(ThesisRunRound, round_id)
    if row is None or row.run_id != run_id:
        raise SceneError("round_not_found", 404)
    return round_slots_out(row)


def snapshot_times(db: Session, run_id: int) -> list[float]:
    get_run(db, run_id)
    rows = db.scalars(
        select(ThesisRunSnapshot.sim_time_s)
        .where(ThesisRunSnapshot.run_id == run_id)
        .order_by(ThesisRunSnapshot.sim_time_s.asc(), ThesisRunSnapshot.id.asc())
    ).all()
    return [float(t) for t in rows]


def snapshot_at(db: Session, run_id: int, t_s: float | None) -> dict[str, Any]:
    """Device states at (or just before) simulated time ``t_s``; latest when None."""
    import base64

    run = get_run(db, run_id)
    stmt = select(ThesisRunSnapshot).where(ThesisRunSnapshot.run_id == run_id)
    if t_s is not None:
        stmt = stmt.where(ThesisRunSnapshot.sim_time_s <= float(t_s))
    row = db.scalars(
        stmt.order_by(ThesisRunSnapshot.sim_time_s.desc(), ThesisRunSnapshot.id.desc()).limit(1)
    ).first()
    if row is None:
        raise SceneError("snapshot_not_found", 404)
    return {
        "frame_seq": row.frame_seq,
        "sim_time_s": row.sim_time_s,
        "device_ids": scene_device_ids(run),
        "state_labels": list(STATE_LABELS),
        "state_codes_b64": base64.b64encode(row.state_codes).decode("ascii"),
        "energy_b64": base64.b64encode(row.energy_j).decode("ascii"),
    }


def device_timeline(db: Session, run_id: int, device_id: int) -> dict[str, Any]:
    get_run(db, run_id)
    rows = (
        db.scalars(
            select(ThesisDeviceEvent)
            .where(ThesisDeviceEvent.run_id == run_id)
            .where(ThesisDeviceEvent.device_id == device_id)
            .order_by(ThesisDeviceEvent.t_s.asc(), ThesisDeviceEvent.id.asc())
        )
        .all()
    )
    events = [_device_event_out(row) for row in rows]
    final_state = _final_state(rows)
    rounds_touched = sorted({row.round_id for row in rows if row.round_id is not None})
    energy_series: list[list[float]] = [
        [float(row.t_s), float(row.energy_j)] for row in rows if row.energy_j is not None
    ]
    return {
        "device_id": device_id,
        "final_state": final_state,
        "events": events,
        "rounds_touched": rounds_touched,
        "energy_series": energy_series,
    }


def device_map(db: Session, run_id: int) -> dict[str, Any]:
    """Static per-run device layout: subtype and, for every enabled reader, the
    devices inside its coverage disk. Built with the engine's own coverage test
    (``episode._build_readers``) so the frontend's per-reader views match the
    simulation exactly. Indices refer to ``device_ids`` order."""
    import numpy as np

    from app.thesis_simulator.inventory.episode import build_episode
    from app.thesis_simulator.inventory.state import EpisodeConfig

    run = get_run(db, run_id)
    config = EpisodeConfig.from_json(run.scheme, run.config_json or {})
    state = build_episode(dict(run.scene_snapshot_json or {}), config, np.random.default_rng(0), warm_start=False)
    placements = (run.scene_snapshot_json or {}).get("placements", [])
    subtypes = [str(p.get("subtype") or "") for p in placements if p.get("kind") == "device"]
    return {
        "device_ids": scene_device_ids(run),
        "subtypes": subtypes,
        "coverage": {str(r.reader_id): np.nonzero(r.cover_mask)[0].astype(int).tolist() for r in state.readers},
    }


def identifications(db: Session, run_id: int) -> dict[str, Any]:
    """Every identification so far, in time order: device index (``device_ids``
    order), time and identifying reader."""
    run = get_run(db, run_id)
    index = {dev_id: i for i, dev_id in enumerate(scene_device_ids(run))}
    rows = db.execute(
        select(ThesisDeviceEvent.t_s, ThesisDeviceEvent.device_id, ThesisDeviceEvent.reader_id)
        .where(ThesisDeviceEvent.run_id == run_id)
        .where(ThesisDeviceEvent.event_type == "identified")
        .order_by(ThesisDeviceEvent.t_s.asc(), ThesisDeviceEvent.id.asc())
    ).all()
    out: dict[str, list] = {"t": [], "device": [], "reader": []}
    for t_s, dev, rid in rows:
        i = index.get(int(dev))
        if i is None:
            continue
        out["t"].append(float(t_s))
        out["device"].append(i)
        out["reader"].append(None if rid is None else int(rid))
    return out


def device_states(db: Session, run_id: int) -> dict[int, str]:
    """Latest persisted state label per device id."""
    import numpy as np

    run = get_run(db, run_id)
    row = db.scalars(
        select(ThesisRunSnapshot)
        .where(ThesisRunSnapshot.run_id == run_id)
        .order_by(ThesisRunSnapshot.frame_seq.desc(), ThesisRunSnapshot.id.desc())
        .limit(1)
    ).first()
    if row is None:
        return {}
    codes = np.frombuffer(row.state_codes, dtype=np.uint8)
    return {dev_id: STATE_LABELS[int(code)] for dev_id, code in zip(scene_device_ids(run), codes)}


def _final_state(rows: list[ThesisDeviceEvent]) -> str:
    if any(r.event_type == "identified" for r in rows):
        return "identified"
    for r in reversed(rows):
        if r.event_type == "dropped":
            return "unreachable" if r.cause == "unreachable" else "dropped"
    return "pending"


def _device_event_out(row: ThesisDeviceEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "device_id": row.device_id,
        "reader_id": row.reader_id,
        "round_id": row.round_id,
        "t_s": row.t_s,
        "event_type": row.event_type,
        "cause": row.cause,
        "energy_j": row.energy_j,
        "payload": row.payload_json,
    }


def _reader_event_out(row: ThesisReaderEvent) -> dict[str, Any]:
    return {
        "id": row.id,
        "reader_id": row.reader_id,
        "round_id": row.round_id,
        "t_s": row.t_s,
        "event_type": row.event_type,
        "slot_index": row.slot_index,
        "payload": row.payload_json,
    }
