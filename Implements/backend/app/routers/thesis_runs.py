from collections.abc import Iterator

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from sqlalchemy.orm import Session

from app.schemas.thesis_runs import (
    AnalysisOut,
    CompareRunsIn,
    CompareRunsOut,
    DeviceEventListOut,
    DeviceMapOut,
    IdentificationsOut,
    DeviceStatesOut,
    ReaderEventListOut,
    RoundOut,
    RoundSlotsOut,
    RunCreateIn,
    RunDetailOut,
    RunNameIn,
    RunSpeedIn,
    RunSummaryOut,
    SnapshotIndexOut,
    SnapshotOut,
    TimelineOut,
)
from app.thesis_simulator.db import ensure_db, get_db, session_factory
from app.thesis_simulator.inventory.live import stream_events
from app.thesis_simulator.analysis import analysis_bundle
from app.thesis_simulator.runs_service import (
    create_run,
    device_map,
    device_states,
    identifications,
    device_timeline,
    get_run,
    hard_delete_run,
    list_device_events,
    list_reader_events,
    list_rounds,
    list_runs,
    pause_run,
    resume_run,
    round_slots,
    run_detail,
    run_summary,
    set_run_name,
    set_run_speed,
    snapshot_at,
    snapshot_times,
    soft_delete_run,
    stop_run,
)
from app.thesis_simulator.service import get_section
from app.thesis_simulator.service import SceneError
from app.thesis_simulator.timefreq import device_trace, reader_timefreq

router = APIRouter(tags=["thesis-simulator-runs"])


def _guard(exc: SceneError) -> HTTPException:
    return HTTPException(status_code=exc.status, detail=exc.code)


@router.get("/sections/{section_id}/runs", response_model=list[RunSummaryOut])
def read_runs(section_id: int, db: Session = Depends(get_db)) -> list[dict]:
    try:
        return list_runs(db, section_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/sections/{section_id}/runs", response_model=RunDetailOut, status_code=201)
def post_run(section_id: int, body: RunCreateIn, db: Session = Depends(get_db)) -> dict:
    try:
        return run_detail(create_run(db, section_id, body))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}", response_model=RunDetailOut)
def read_run(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return run_detail(get_run(db, run_id))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/summary", response_model=RunSummaryOut)
def read_run_summary(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return run_summary(get_run(db, run_id))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.delete("/runs/{run_id}", status_code=204)
def remove_run(run_id: int, background: BackgroundTasks, db: Session = Depends(get_db)) -> Response:
    try:
        run_id = soft_delete_run(db, run_id)
    except SceneError as exc:
        raise _guard(exc) from exc
    background.add_task(hard_delete_run, run_id)
    return Response(status_code=204)


@router.post("/runs/{run_id}/stop", response_model=RunSummaryOut)
def post_stop(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return run_summary(stop_run(db, run_id))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/runs/{run_id}/pause", response_model=RunSummaryOut)
def post_pause(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return run_summary(pause_run(db, run_id))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/runs/{run_id}/resume", response_model=RunSummaryOut)
def post_resume(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return run_summary(resume_run(db, run_id))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/runs/{run_id}/speed", response_model=RunSummaryOut)
def post_speed(run_id: int, body: RunSpeedIn, db: Session = Depends(get_db)) -> dict:
    try:
        return run_summary(set_run_speed(db, run_id, body.speed))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/runs/{run_id}/name", response_model=RunSummaryOut)
def post_name(run_id: int, body: RunNameIn, db: Session = Depends(get_db)) -> dict:
    try:
        return run_summary(set_run_name(db, run_id, body.name))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/rounds/{round_id}/slots", response_model=RoundSlotsOut)
def read_round_slots(run_id: int, round_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return round_slots(db, run_id, round_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/device-map", response_model=DeviceMapOut)
def read_device_map(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return device_map(db, run_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/identifications", response_model=IdentificationsOut)
def read_identifications(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return identifications(db, run_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/snapshots", response_model=SnapshotIndexOut)
def read_snapshot_index(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return {"times": snapshot_times(db, run_id)}
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/snapshot", response_model=SnapshotOut)
def read_snapshot(
    run_id: int,
    t: float | None = Query(default=None, description="simulated time (s); latest when omitted"),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return snapshot_at(db, run_id, t)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/device-events", response_model=DeviceEventListOut)
def read_device_events(
    run_id: int,
    device_id: int | None = Query(default=None),
    since: float | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return list_device_events(db, run_id, device_id=device_id, since=since, limit=limit)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/reader-events", response_model=ReaderEventListOut)
def read_reader_events(
    run_id: int,
    reader_id: int | None = Query(default=None),
    since: float | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=5000),
    db: Session = Depends(get_db),
) -> dict:
    try:
        return list_reader_events(db, run_id, reader_id=reader_id, since=since, limit=limit)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/rounds", response_model=list[RoundOut])
def read_rounds(
    run_id: int,
    reader_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[dict]:
    try:
        return list_rounds(db, run_id, reader_id=reader_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/device/{device_id}/timeline", response_model=TimelineOut)
def read_timeline(run_id: int, device_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return device_timeline(db, run_id, device_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/readers/{reader_id}/timefreq")
def read_reader_timefreq(
    run_id: int,
    reader_id: int,
    t0: float = Query(default=0.0, ge=0.0),
    t1: float = Query(default=10.0, ge=0.0),
    db: Session = Depends(get_db),
) -> dict:
    """Frames of one reader overlapping [t0, t1] with the resource each device used."""
    try:
        return reader_timefreq(db, run_id, reader_id, t0, max(t0, t1))
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/device/{device_id}/trace")
def read_device_trace(run_id: int, device_id: int, db: Session = Depends(get_db)) -> dict:
    """One device from start to end: protocol events, its frames and its energy between them."""
    try:
        return device_trace(db, run_id, device_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/device-states", response_model=DeviceStatesOut)
def read_device_states(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return {"states": device_states(db, run_id)}
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/analysis", response_model=AnalysisOut)
def read_analysis(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return analysis_bundle(db, run_id)
    except SceneError as exc:
        raise _guard(exc) from exc


@router.post("/sections/{section_id}/runs/compare", response_model=CompareRunsOut)
def post_compare(section_id: int, body: CompareRunsIn, db: Session = Depends(get_db)) -> dict:
    try:
        get_section(db, section_id)
        bundles = []
        for rid in body.run_ids:
            run = get_run(db, rid)
            if run.section_id != section_id:
                raise SceneError("run_section_mismatch", 400)
            bundles.append(analysis_bundle(db, rid))
        return {"runs": bundles}
    except SceneError as exc:
        raise _guard(exc) from exc


def _require_run(run_id: int) -> int:
    """Validate the run with a short-lived session (an SSE response can stay
    open for minutes; it must not pin a pooled connection)."""
    ensure_db()
    with session_factory()() as db:
        try:
            get_run(db, run_id)
        except SceneError as exc:
            raise _guard(exc) from exc
    return run_id


@router.get("/runs/{run_id}/stream", response_class=EventSourceResponse)
def stream_run(run_id: int = Depends(_require_run)) -> Iterator[ServerSentEvent]:
    """Live run feed (Server-Sent Events): ``snapshot`` then ``tick``s, ``status``, ``done``."""
    yield from stream_events(run_id)
