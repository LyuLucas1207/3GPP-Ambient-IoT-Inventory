"""Service layer for inventory runs + log queries."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.schemas.thesis_runs import RunCreateIn
from app.thesis_simulator.inventory import make_engine
from app.thesis_simulator.models import (
    ThesisDeviceEvent,
    ThesisInventoryRun,
    ThesisReaderEvent,
    ThesisRunRound,
    ThesisRunSummary,
    ThesisSection,
)
from app.thesis_simulator.service import SceneError, get_section, iso, placement_out

INITIALIZED = "initialized"

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
    section = get_section(db, section_id)
    if section.status != INITIALIZED:
        raise SceneError("section_not_initialized")
    config = body.model_dump()
    run = ThesisInventoryRun(
        section_id=section.id,
        scheme=body.scheme,
        status="pending",
        config_json=config,
        scene_snapshot_json=_scene_snapshot(section),
    )
    db.add(run)
    db.flush()
    try:
        make_engine(body.scheme).run(db, run)
    except Exception as exc:  # noqa: BLE001 - log and surface via run row
        run.status = "failed"
        run.error_detail = str(exc)[:2000]
        run.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise
    db.commit()
    db.refresh(run)
    return run


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
    run.deleted_at = datetime.now(timezone.utc)
    run.status = "deleted" if run.status not in {"running", "pending"} else run.status
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


def stop_run(db: Session, run_id: int) -> ThesisInventoryRun:
    run = get_run(db, run_id)
    if run.status not in {"running", "pending"}:
        raise SceneError("run_not_running", 409)
    # Mock engine is synchronous; nothing to cancel. Mark stopped.
    run.status = "stopped"
    run.completed_at = datetime.now(timezone.utc)
    run.updated_at = run.completed_at
    db.commit()
    db.refresh(run)
    return run


def run_summary(run: ThesisInventoryRun) -> dict[str, Any]:
    summary = run.summary
    if summary is None:
        return {
            "run_id": run.id,
            "section_id": run.section_id,
            "scheme": run.scheme,
            "status": run.status,
            "total_devices": 0,
            "identified_total": 0,
            "identified_by_subtype": {},
            "died_count": 0,
            "dropped_count": 0,
            "rounds_total": 0,
            "wall_duration_s": 0.0,
            "created_at": iso(run.created_at),
            "completed_at": iso(run.completed_at) if run.completed_at else None,
            "duration_s": run.duration_s,
        }
    return {
        "run_id": run.id,
        "section_id": run.section_id,
        "scheme": run.scheme,
        "status": run.status,
        "total_devices": summary.total_devices,
        "identified_total": summary.identified_total,
        "identified_by_subtype": summary.identified_by_subtype_json,
        "died_count": summary.died_count,
        "dropped_count": summary.dropped_count,
        "rounds_total": summary.rounds_total,
        "wall_duration_s": summary.wall_duration_s,
        "created_at": iso(run.created_at),
        "completed_at": iso(run.completed_at) if run.completed_at else None,
        "duration_s": run.duration_s,
    }


def run_detail(run: ThesisInventoryRun) -> dict[str, Any]:
    return {
        "id": run.id,
        "section_id": run.section_id,
        "scheme": run.scheme,
        "status": run.status,
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
    stmt = stmt.order_by(ThesisRunRound.t_start_s.asc())
    return [_round_out(row) for row in db.scalars(stmt).all()]


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


def device_states(db: Session, run_id: int) -> dict[int, str]:
    get_run(db, run_id)
    rows = (
        db.scalars(
            select(ThesisDeviceEvent)
            .where(ThesisDeviceEvent.run_id == run_id)
            .where(ThesisDeviceEvent.event_type.in_(("identified", "died", "dropped")))
            .order_by(ThesisDeviceEvent.t_s.asc(), ThesisDeviceEvent.id.asc())
        )
        .all()
    )
    result: dict[int, str] = {}
    for row in rows:
        if row.event_type == "identified":
            result[row.device_id] = "identified"
        elif row.event_type == "died":
            # died beats dropped; identified beats both
            if result.get(row.device_id) != "identified":
                result[row.device_id] = "died"
        else:  # dropped
            result.setdefault(row.device_id, "dropped")
    return result


def _final_state(rows: list[ThesisDeviceEvent]) -> str:
    identified = any(r.event_type == "identified" for r in rows)
    if identified:
        return "identified"
    for r in reversed(rows):
        if r.event_type == "died":
            return "died"
        if r.event_type == "dropped":
            return "dropped"
    return "unknown"


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


def _round_out(row: ThesisRunRound) -> dict[str, Any]:
    return {
        "id": row.id,
        "reader_id": row.reader_id,
        "round_index": row.round_index,
        "t_start_s": row.t_start_s,
        "t_end_s": row.t_end_s,
        "k_estimate": row.k_estimate,
        "g": row.g,
        "pstar": row.pstar,
        "slot_count": row.slot_count,
        "success_count": row.success_count,
        "collision_count": row.collision_count,
        "empty_count": row.empty_count,
        "metadata": row.metadata_json,
    }
