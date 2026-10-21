from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RunScheme = Literal["periodic", "aperiodic"]
RunStatus = Literal["pending", "running", "completed", "stopped", "failed"]


class RunCreateIn(BaseModel):
    scheme: RunScheme = "periodic"
    max_time_s: float = Field(default=60.0, gt=0.0, le=3600.0)
    k_initial: int | None = Field(default=None, ge=4, le=4096)
    g: int | None = Field(default=None, ge=1, le=64)
    use_grouping: bool = False
    use_capture: bool = True
    use_ebi: bool = True
    include_d2r: bool = True
    seed: int | None = None
    reader_start_offsets: dict[str, float] = Field(default_factory=dict)


class RunSummaryOut(BaseModel):
    run_id: int
    section_id: int
    scheme: RunScheme
    status: RunStatus
    total_devices: int
    identified_total: int
    identified_by_subtype: dict[str, int]
    died_count: int
    dropped_count: int
    rounds_total: int
    wall_duration_s: float
    created_at: str
    completed_at: str | None = None
    duration_s: float | None = None


class RunDetailOut(BaseModel):
    id: int
    section_id: int
    scheme: RunScheme
    status: RunStatus
    config: dict[str, Any]
    scene_snapshot: dict[str, Any]
    requested_at: str
    started_at: str | None
    completed_at: str | None
    duration_s: float | None
    error_detail: str | None
    summary: RunSummaryOut | None


class DeviceEventOut(BaseModel):
    id: int
    device_id: int
    reader_id: int | None
    round_id: int | None
    t_s: float
    event_type: str
    cause: str | None
    energy_j: float | None
    payload: dict[str, Any] | None


class ReaderEventOut(BaseModel):
    id: int
    reader_id: int
    round_id: int | None
    t_s: float
    event_type: str
    slot_index: int | None
    payload: dict[str, Any] | None


class RoundOut(BaseModel):
    id: int
    reader_id: int
    round_index: int
    t_start_s: float
    t_end_s: float
    k_estimate: float | None
    g: float | None
    pstar: float | None
    slot_count: int
    success_count: int
    collision_count: int
    empty_count: int
    metadata: dict[str, Any] | None


class DeviceEventListOut(BaseModel):
    events: list[DeviceEventOut]
    next_since: float | None


class ReaderEventListOut(BaseModel):
    events: list[ReaderEventOut]
    next_since: float | None


class TimelineOut(BaseModel):
    device_id: int
    final_state: str
    events: list[DeviceEventOut]
    rounds_touched: list[int]
    energy_series: list[list[float]]


class DeviceStatesOut(BaseModel):
    states: dict[int, str]
