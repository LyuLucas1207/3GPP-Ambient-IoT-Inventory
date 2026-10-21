from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.schemas.thesis_runs import (
    DeviceEventListOut,
    DeviceStatesOut,
    ReaderEventListOut,
    RoundOut,
    RunCreateIn,
    RunDetailOut,
    RunSummaryOut,
    TimelineOut,
)
from app.thesis_simulator.db import get_db
from app.thesis_simulator.runs_service import (
    create_run,
    device_states,
    device_timeline,
    get_run,
    hard_delete_run,
    list_device_events,
    list_reader_events,
    list_rounds,
    list_runs,
    run_detail,
    run_summary,
    soft_delete_run,
    stop_run,
)
from app.thesis_simulator.service import SceneError

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


@router.get("/runs/{run_id}/device-states", response_model=DeviceStatesOut)
def read_device_states(run_id: int, db: Session = Depends(get_db)) -> dict:
    try:
        return {"states": device_states(db, run_id)}
    except SceneError as exc:
        raise _guard(exc) from exc


@router.get("/runs/{run_id}/stream")
def stream_run(run_id: int, db: Session = Depends(get_db)) -> StreamingResponse:
    try:
        run = get_run(db, run_id)
    except SceneError as exc:
        raise _guard(exc) from exc

    def iterator():
        yield f"event: snapshot\ndata: {{\"run_id\": {run.id}, \"status\": \"{run.status}\"}}\n\n"
        yield "event: done\ndata: {}\n\n"

    return StreamingResponse(iterator(), media_type="text/event-stream")
