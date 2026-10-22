from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RunScheme = Literal["periodic", "aperiodic"]
RunStatus = Literal["pending", "running", "paused", "completed", "stopped", "failed", "deleted"]


class RunCreateIn(BaseModel):
    scheme: RunScheme = "periodic"
    # None = no time cap: the run ends when every device is identified (or
    # unreachable), or when the user pauses / stops it.
    max_time_s: float | None = Field(default=None, gt=0.0, le=86400.0)
    # Simulated seconds per wall-clock second; None = as fast as possible.
    speed: float | None = Field(default=1.0, gt=0.0, le=1000.0)
    # End automatically after this much simulated time with no new
    # identification (None disables the guard; max_time_s still applies).
    stall_timeout_s: float | None = Field(default=300.0, gt=0.0, le=86400.0)
    k_initial: int | None = Field(default=None, ge=4, le=4096)
    g: int | None = Field(default=None, ge=1, le=64)
    use_grouping: bool = False
    use_capture: bool = True
    use_ebi: bool = True
    include_d2r: bool = True
    seed: int | None = None
    reader_start_offsets: dict[str, float] = Field(default_factory=dict)
    disabled_reader_ids: list[int] = Field(default_factory=list)
    # Run to completion inside the request (tests / scripted sweeps).
    sync: bool = False


class RunSpeedIn(BaseModel):
    speed: float | None = Field(default=None, gt=0.0, le=1000.0)


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
    sim_time_s: float = 0.0
    unreachable_count: int = 0
    speed: float | None = None
    max_time_s: float | None = None


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
    frame_seq: int | None = None
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
    candidates: int | None = None
    joiners: int | None = None
    on_at_page: int | None = None
    backlog_true: int | None = None
    served: int | None = None
    s_budget: int | None = None
    budget_dropped: int | None = None
    n_hat: float | None = None
    mnot_prev: int | None = None
    mnot_next: int | None = None
    n_done_total: int | None = None
    identified_by_subtype: dict[str, int] | None = None
    timing: dict[str, float] | None = None
    energy_j: dict[str, float] | None = None
    deaths: dict[str, dict[str, int]] | None = None
    metadata: dict[str, Any] | None


class RoundSlotsOut(BaseModel):
    id: int
    reader_id: int
    round_index: int
    slots: dict[str, Any] | None


class SnapshotOut(BaseModel):
    frame_seq: int
    sim_time_s: float
    device_ids: list[int]
    state_labels: list[str]
    state_codes_b64: str
    energy_b64: str


class DeviceMapOut(BaseModel):
    device_ids: list[int]
    subtypes: list[str]
    coverage: dict[str, list[int]]


class IdentificationsOut(BaseModel):
    t: list[float]
    device: list[int]
    reader: list[int | None]


class SnapshotIndexOut(BaseModel):
    times: list[float]


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


class RoundBreakdownOut(BaseModel):
    reader_id: int
    round_index: int
    t_start_s: float
    t_end_s: float
    success: int
    collision: int
    empty: int


class RoundAggregatesOut(BaseModel):
    slots_total: int
    success_total: int
    collision_total: int
    empty_total: int
    resource_efficiency: float
    overhead_s: dict[str, float]
    deaths_by_stage: dict[str, dict[str, int]]
    energy_j_by_subtype: dict[str, float]


class AnalysisOut(BaseModel):
    run_id: int
    scheme: RunScheme
    status: RunStatus
    summary: RunSummaryOut
    config: dict[str, Any] = Field(default_factory=dict)
    identification_curve: list[tuple[float, int]]
    identification_by_subtype: dict[str, list[tuple[float, int]]] = Field(default_factory=dict)
    # percentiles of the identified devices / of the whole population
    completion_times: dict[str, float | None]
    population_completion_times: dict[str, float | None] = Field(default_factory=dict)
    reader_contribution: dict[int, int]
    rounds_breakdown: list[RoundBreakdownOut]
    aggregates: RoundAggregatesOut | None = None


class CompareRunsIn(BaseModel):
    run_ids: list[int] = Field(..., min_length=1, max_length=8)


class CompareRunsOut(BaseModel):
    runs: list[AnalysisOut]
