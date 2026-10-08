from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.aperiodic_simulator import router as aperiodic_router
from app.routers.simulator import router as simulator_router

app = FastAPI(
    title="3GPP Ambient IoT Inventory Simulators",
    description=(
        "Two separate paper simulators: the legacy periodic-paging paper "
        "(/api/simulator) and the aperiodic-paging paper (/api/aperiodic-simulator)."
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


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
