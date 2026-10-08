"""HTTP API for the aperiodic-paging paper, mounted at /api/aperiodic-simulator.

Thin layer: request validation here, all science in ``app.aperiodic_simulator``.
"""

from fastapi import APIRouter, HTTPException

from app.aperiodic_simulator.runtime import jobs, service
from app.aperiodic_simulator.reproduction import presets
from app.aperiodic_simulator.runtime.run_store import device_trace
from app.schemas.aperiodic_simulator import AperiodicSimulateRequest, ReproduceRequest

router = APIRouter()


@router.get("/about")
def about() -> dict:
    return service.about_payload()


@router.get("/config/paper")
def paper_config() -> dict:
    return service.paper_config_payload()


@router.post("/simulate")
def simulate(req: AperiodicSimulateRequest) -> dict:
    factory = None
    if req.controller == "recurrent_ppo":
        from app.aperiodic_simulator.rl.checkpoint import CheckpointMissing
        from app.aperiodic_simulator.controllers.recurrent_ppo import ppo_controller_factory

        try:
            factory = ppo_controller_factory(alpha=req.alpha)
        except CheckpointMissing as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
    try:
        return service.simulate(req, controller_factory=factory)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/reproduce/{target}")
def reproduce(target: str, req: ReproduceRequest) -> dict:
    if target not in presets.TARGETS:
        raise HTTPException(status_code=404, detail=f"unknown target {target}; one of {presets.TARGETS}")
    if req.use_cached:
        cached = presets.load_cached(target)
        if cached is not None:
            return {"status": "done", "target": target, "result": cached}
    return jobs.submit(
        target,
        presets.compute,
        target=target,
        episodes=req.episodes,
        base_seed=req.base_seed,
        panels=req.panels,
        workers=req.workers,
    )


@router.get("/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    try:
        return jobs.status(job_id, with_result=True)
    except KeyError:
        raise HTTPException(status_code=404, detail="job not found") from None


@router.get("/ppo/status")
def ppo_status() -> dict:
    from app.aperiodic_simulator.rl.checkpoint import ppo_status_payload

    return ppo_status_payload()


@router.get("/runs/{run_id}/controllers/{controller}/devices/{device_id}/trace")
def trace(run_id: str, controller: str, device_id: int) -> dict:
    try:
        return service._np(device_trace(run_id, controller, device_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
