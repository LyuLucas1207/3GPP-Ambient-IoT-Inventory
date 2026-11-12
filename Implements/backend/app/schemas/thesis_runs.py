from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

RunScheme = Literal["periodic", "aperiodic"]
RunStatus = Literal["pending", "running", "paused", "completed", "stopped", "failed", "deleted"]


def _normalize_run_name(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


ControllerKind = Literal["auto", "fixed", "dfsa", "policy"]
ResourceMode = Literal["independent", "shared", "fdma", "tdma", "hybrid", "lbt"]
TerminationKind = Literal["oracle", "quiet_rounds", "id_rate", "energy_bound", "combined"]


class ControllerIn(BaseModel):
    """Per-reader (K, p*) controller. ``auto`` = DFSA when ``adaptive_k`` else fixed K."""

    kind: ControllerKind = "auto"
    policy_id: str | None = Field(default=None, max_length=160)
    deterministic: bool = True


class ResourceIn(BaseModel):
    """How readers share the F subbands (``coordination/spec.py``)."""

    mode: ResourceMode = "independent"
    interference: bool = True
    cross_msg1: bool = True
    conflict_distance_m: float | None = Field(default=None, ge=0.0, le=1000.0)  # None = link-budget graph
    n_colors: int | None = Field(default=None, ge=1, le=64)
    tdma_window_s: float = Field(default=0.5, gt=0.0, le=60.0)
    freq_groups: int = Field(default=2, ge=1, le=64)
    lbt_backoff_s: float = Field(default=0.05, ge=0.0, le=10.0)
    lbt_max_on_s: float = Field(default=4.0, gt=0.0, le=600.0)
    lbt_pause_s: float = Field(default=0.1, ge=0.0, le=60.0)
    r2d_sir_db: float = Field(default=6.0, ge=-30.0, le=60.0)
    d2r_sinr_db: float = Field(default=0.5, ge=-30.0, le=60.0)
    other_cw_suppression_db: float = Field(default=61.0, ge=0.0, le=200.0)


class TerminationIn(BaseModel):
    """When a reader stops paging (``inventory/termination.py``)."""

    kind: TerminationKind = "oracle"
    quiet_rounds: int = Field(default=10, ge=1, le=100000)
    window_mode: Literal["rounds", "seconds", "ewma"] = "rounds"
    window: float = Field(default=20.0, gt=0.0, le=1e6)
    ewma_alpha: float = Field(default=0.1, gt=0.0, le=1.0)
    r_min: float | None = Field(default=None, ge=0.0)
    r_rel: float | None = Field(default=0.01, ge=0.0, le=1.0)
    min_frames: int = Field(default=5, ge=0, le=100000)
    margin: float = Field(default=0.0, ge=0.0, le=100.0)
    energy_source: Literal["edge", "actual"] = "edge"
    combine: Literal["all", "any"] = "all"
    rules: list["TerminationIn"] = Field(default_factory=list, max_length=8)


class RunCreateIn(BaseModel):
    scheme: RunScheme = "periodic"
    # Optional display label; empty/whitespace becomes None (UI falls back to #id).
    name: str | None = Field(default=None, max_length=80)
    # None = no time cap: the run ends when every device is identified (or
    # unreachable), or when the user pauses / stops it.
    max_time_s: float | None = Field(default=None, gt=0.0, le=86400.0)
    # Simulated seconds per wall-clock second; None = as fast as possible.
    speed: float | None = Field(default=1.0, gt=0.0, le=1000.0)
    # End automatically after this much simulated time with no new
    # identification (None disables the guard; max_time_s still applies).
    stall_timeout_s: float | None = Field(default=300.0, gt=0.0, le=86400.0)
    k_initial: int | None = Field(default=None, ge=4, le=4096)
    # True: Schoute/empty-slot DFSA after round 1; k_initial is only the cold-start K.
    # False / omitted with a set k_initial: every round uses that fixed K (legacy).
    adaptive_k: bool = False
    g: int | None = Field(default=None, ge=1, le=64)
    use_grouping: bool = False
    use_capture: bool = True
    use_ebi: bool = True
    include_d2r: bool = True
    seed: int | None = None
    reader_start_offsets: dict[str, float] = Field(default_factory=dict)
    # Staggered start, recorded for analysis: reader ids per start group (group i
    # starts i * reader_start_interval_s after the first). Offsets above are what the engine uses.
    reader_start_groups: list[list[int]] = Field(default_factory=list)
    reader_start_interval_s: float | None = Field(default=None, ge=0.0, le=3600.0)
    disabled_reader_ids: list[int] = Field(default_factory=list)
    # Frequency subbands F (None = the paper's 8).
    f_freq: int | None = Field(default=None, ge=1, le=64)
    controller: ControllerIn = Field(default_factory=ControllerIn)
    resource: ResourceIn = Field(default_factory=ResourceIn)
    termination: TerminationIn = Field(default_factory=TerminationIn)
    # Run to completion inside the request (tests / scripted sweeps).
    sync: bool = False

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return _normalize_run_name(value)


class RunSpeedIn(BaseModel):
    speed: float | None = Field(default=None, gt=0.0, le=1000.0)


class RunNameIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)

    @field_validator("name")
    @classmethod
    def _name(cls, value: str | None) -> str | None:
        return _normalize_run_name(value)


class RunSummaryOut(BaseModel):
    run_id: int
    section_id: int
    scheme: RunScheme
    status: RunStatus
    name: str | None = None
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
    terminated_early_count: int = 0
    readers_stopped: int = 0
    controller_kind: str = "auto"
    policy_id: str | None = None
    resource_mode: str = "independent"
    termination_label: str = "oracle"


class RunDetailOut(BaseModel):
    id: int
    section_id: int
    scheme: RunScheme
    status: RunStatus
    name: str | None = None
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
    reachable_completion_times: dict[str, float | None] = Field(default_factory=dict)
    reader_contribution: dict[int, int]
    rounds_breakdown: list[RoundBreakdownOut]
    aggregates: RoundAggregatesOut | None = None


class DeviceMetricsOut(BaseModel):
    aggregate: dict[str, Any]
    devices: list[dict[str, Any]]


class InterferenceOut(BaseModel):
    mode: str
    n_colors: int
    readers: dict[str, dict[str, Any]]
    # per frame: [t_start_s, reader_id, r2d_lost, m1_lost, m2_lost, m3_lost]
    frames: list[list[float]]


class TerminationReplayIn(BaseModel):
    rules: list[TerminationIn] = Field(..., min_length=1, max_length=64)


class TerminationReplayOut(BaseModel):
    run_id: int
    oracle: bool
    reachable: int
    t99: float | None
    t_last_id: float | None
    outcomes: list[dict[str, Any]]


class CompareRunsIn(BaseModel):
    run_ids: list[int] = Field(..., min_length=1, max_length=8)


class CompareRunsOut(BaseModel):
    runs: list[AnalysisOut]
