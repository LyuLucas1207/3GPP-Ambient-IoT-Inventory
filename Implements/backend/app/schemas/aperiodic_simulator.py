"""Request models for the aperiodic-paging paper API (/api/aperiodic-simulator).

Separate from the legacy ``app.schemas.simulator`` models: no legacy strategy
enums and no ``paper_mode`` flag.
"""

from typing import Literal

from pydantic import BaseModel, Field, model_validator

LMAX = 83

Scenario = Literal["single_source", "multi_source"]
ControllerLiteral = Literal["pfsa_pze", "dfsa_schoute", "cmebe", "recurrent_ppo"]


class AperiodicSimulateRequest(BaseModel):
    num_devices: int = Field(15000, ge=10, le=15000)
    seed: int = Field(42, ge=0)
    harvesting_scenario: Scenario = "multi_source"
    paging_mode: Literal["aperiodic", "periodic"] = "aperiodic"
    controller: ControllerLiteral = "pfsa_pze"
    ppo_enabled: bool = False
    L_mode: Literal["fixed", "adaptive"] = "fixed"
    L_fixed: int = Field(16, ge=1, le=LMAX)
    L_initial: int = Field(1, ge=1, le=LMAX)
    p_initial: float = Field(1.0, gt=0.0, le=1.0)
    N_g: int = Field(1, ge=1, le=16)
    enforce_midround_depletion: bool = True
    alpha: float = Field(0.5, ge=0.0, le=1.0)
    F: int = Field(8, ge=1, le=32)
    type_mix: Literal["mixed", "1", "2a", "2b"] = "mixed"
    impairments_enabled: bool = True
    capture_ratio_db: float = Field(6.0, ge=0.0, le=30.0)
    missed_detection_rate: float = Field(0.01, ge=0.0, le=0.5)
    false_alarm_rate: float = Field(0.001, ge=0.0, le=0.5)
    runtime_mode: Literal["interactive", "paper_batch"] = "interactive"
    num_episodes: int = Field(1, ge=1, le=100)
    max_time_s: float = Field(1200.0, gt=0.0, le=3600.0)
    n_trace_samples: int = Field(12, ge=0, le=64)
    snapshot_interval_s: float = Field(1.0, ge=0.1, le=60.0)

    @model_validator(mode="after")
    def _combinations(self):
        if self.ppo_enabled:
            if self.paging_mode != "aperiodic":
                raise ValueError("PPO is defined for the proposed aperiodic protocol only")
            if self.controller != "recurrent_ppo":
                raise ValueError("ppo_enabled=true requires controller='recurrent_ppo'")
            if self.L_mode != "adaptive":
                raise ValueError("PPO adapts L and p: L_mode must be 'adaptive'")
        elif self.controller == "recurrent_ppo":
            raise ValueError("controller='recurrent_ppo' requires ppo_enabled=true")
        if self.controller in ("dfsa_schoute", "cmebe"):
            if self.L_mode != "adaptive":
                raise ValueError("DFSA baselines adapt the frame size: L_mode must be 'adaptive'")
            if self.paging_mode != "aperiodic":
                raise ValueError("controller-level baselines run under the proposed aperiodic protocol")
        if self.controller == "pfsa_pze" and self.L_mode != "fixed":
            raise ValueError("PFSA/PZE keeps L fixed: L_mode must be 'fixed'")
        if self.paging_mode == "aperiodic" and self.N_g != 1:
            raise ValueError("the proposed aperiodic protocol has no group scheduling (N_g must be 1)")
        if self.runtime_mode == "interactive" and self.num_episodes > 1:
            raise ValueError("interactive mode runs a single episode")
        return self


class ReproduceRequest(BaseModel):
    episodes: int = Field(10, ge=1, le=100)
    base_seed: int = Field(0, ge=0)
    use_cached: bool = True
    panels: list[str] | None = None
    workers: int | None = Field(None, ge=1, le=32)
