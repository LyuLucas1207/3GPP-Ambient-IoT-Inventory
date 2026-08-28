from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.simulation import router as simulation_router

app = FastAPI(
    title="3GPP Ambient IoT Inventory Simulator",
    description="Python simulation engine for reproducing Figure 5(b).",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(simulation_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
