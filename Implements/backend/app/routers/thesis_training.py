"""Policy registry and training outputs (training runs themselves are started from the CLI)."""

import sys

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.thesis_simulator.rl.policy import PolicyMissing, list_policies
from app.thesis_simulator.training_registry import (
    BACKEND_ROOT,
    TrainingNotFound,
    experiment_detail,
    list_experiments,
    plot_path,
    run_path,
)

router = APIRouter(tags=["thesis-simulator-training"])


class PromoteIn(BaseModel):
    policy_id: str | None = Field(default=None, max_length=160)
    force: bool = False


@router.get("/policies")
def read_policies() -> list[dict]:
    return list_policies()


@router.get("/training/experiments")
def read_experiments() -> list[dict]:
    return list_experiments()


@router.get("/training/experiments/{name}")
def read_experiment(name: str) -> dict:
    try:
        return experiment_detail(name)
    except TrainingNotFound as exc:
        raise HTTPException(status_code=404, detail="experiment_not_found") from exc


@router.get("/training/experiments/{name}/runs/{run}/plots/{plot}")
def read_plot(name: str, run: str, plot: str) -> FileResponse:
    try:
        return FileResponse(plot_path(name, run, plot), media_type="image/png")
    except TrainingNotFound as exc:
        raise HTTPException(status_code=404, detail="plot_not_found") from exc


@router.post("/training/experiments/{name}/runs/{run}/promote")
def post_promote(name: str, run: str, body: PromoteIn) -> dict:
    try:
        path = run_path(name, run)
    except TrainingNotFound as exc:
        raise HTTPException(status_code=404, detail="run_not_found") from exc
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from training.promote import promote

    try:
        pid = promote(path, body.policy_id, body.force)
    except FileExistsError as exc:
        raise HTTPException(status_code=409, detail="policy_exists") from exc
    except (ValueError, PolicyMissing, FileNotFoundError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"policy_id": pid}
