import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.aperiodic_simulator import router as aperiodic_router
from app.routers.simulator import router as simulator_router
from app.routers.thesis_runs import router as thesis_runs_router
from app.routers.thesis_simulator import router as thesis_router
from app.thesis_simulator.inventory.live import manager as run_manager
from app.thesis_simulator.inventory.live import recover_interrupted_runs

log = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs that a previous process left mid-flight become "paused" so they can
    # be resumed from their last checkpoint.
    try:
        recover_interrupted_runs()
    except Exception:  # noqa: BLE001 - the thesis DB is optional for the other simulators
        log.warning("thesis run recovery skipped (database unavailable?)", exc_info=True)
    yield
    # Shutdown / --reload: checkpoint live runs instead of losing them.
    run_manager.pause_all()


app = FastAPI(
    lifespan=lifespan,
    title="3GPP Ambient IoT Inventory Simulators",
    description=(
        "Three separate simulators: the legacy periodic-paging paper "
        "(/api/simulator), the aperiodic-paging paper (/api/aperiodic-simulator), "
        "and the thesis scene store (/api/thesis-simulator)."
    ),
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulator_router, prefix="/api/simulator")
app.include_router(aperiodic_router, prefix="/api/aperiodic-simulator")
app.include_router(thesis_router, prefix="/api/thesis-simulator")
app.include_router(thesis_runs_router, prefix="/api/thesis-simulator")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
