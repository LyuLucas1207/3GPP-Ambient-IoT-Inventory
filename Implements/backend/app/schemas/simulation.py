from typing import Literal

from pydantic import BaseModel, Field


class SimulateRequest(BaseModel):
    num_devices: int = Field(default=600, ge=1, le=5000)
    device_type: Literal[1, 2] = 1
    strategies: list[Literal["em", "dcm_1_group", "dcm_4_group"]] = [
        "em",
        "dcm_1_group",
        "dcm_4_group",
    ]
    seed: int = Field(default=42, ge=0)
    max_time_s: float = Field(default=25.0, gt=0.5, le=120.0)
    snapshot_interval_ms: float = Field(default=100.0, ge=20.0, le=1000.0)
    collect_snapshots: bool = True
    collect_paging_events: bool = True
