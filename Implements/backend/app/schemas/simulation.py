from typing import Literal

from pydantic import BaseModel, Field, field_validator


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
    # Paper default False: each synced DCM occasion stays ON for Table 1
    # T_on_DCM (Device 1: 3 ms). True is experimental early-sleep, not the
    # published Figure 5(b) model.
    sleep_when_not_attempting: bool = False
    # SLEEP net-power floor in nW. null / omitted = −∞ (paper formula).
    # 0 means max(0, P_eh − P_sl): weak devices do not drain in SLEEP.
    sleep_net_power_min_nw: float | None = None

    @field_validator("sleep_net_power_min_nw", mode="before")
    @classmethod
    def _parse_sleep_net_min(cls, value):
        if value is None or value == "":
            return None
        if isinstance(value, str):
            s = value.strip().lower().replace("∞", "inf").replace("−", "-")
            if s in {"-inf", "-infinity"}:
                return None
        return value
