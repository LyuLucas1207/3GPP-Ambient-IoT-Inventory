from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.aperiodic_simulator import router as aperiodic_router
from app.routers.simulator import router as simulator_router
from app.routers.thesis_runs import router as thesis_runs_router
from app.routers.thesis_simulator import router as thesis_router

app = FastAPI(
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
