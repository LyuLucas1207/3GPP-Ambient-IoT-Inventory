"""Central paper parameters and reproduction-assumption knobs.

Paper-specified values live in DeviceParams / PaperParams.
Reproduction assumptions are grouped in AssumptionParams and must not be
silently mixed with Table 1 numbers.
"""

from dataclasses import dataclass, field, replace
from enum import Enum
from pathlib import Path
from typing import Sequence


class Strategy(str, Enum):
    EM = "em"
    DCM_1_GROUP = "dcm_1_group"
    DCM_4_GROUP = "dcm_4_group"


class DeviceType(int, Enum):
    DEVICE_1 = 1
    DEVICE_2 = 2


# Scientific state machine (protocol / energy).
OFF = 0
ON = 1
SLEEP = 2
TX = 3
DONE = 4

STATE_NAME = {
    OFF: "OFF",
    ON: "ON",
    SLEEP: "SLEEP",
    TX: "TX",
    DONE: "DONE",
}

# Visualization overlays (may replace ON/TX for a snapshot).
VIZ_OFF = "OFF"
VIZ_ON = "ON"
VIZ_SLEEP = "SLEEP"
VIZ_ACCESS = "ACCESS"
VIZ_COLLISION = "COLLISION"
VIZ_DONE = "DONE"


@dataclass(frozen=True)
class DeviceParams:
    """Published IEEE Table 1 parameters. All values are SI units."""

    device_type: int
    e_max_j: float
    e_up_j: float
    e_low_j: float
    p_rx_w: float
    p_tx_w: float
    p_sl_w: float
    paging_s: float
    t_pg_s: float
    msg1_s: float
    msg2_s: float
    msg3_s: float
    t_on_dcm_s: float
    t_on_timer_s: float
    n_time_ao: int
    n_freq_ao: int
    p_wakeup_w: float | None = None

    @property
    def n_ao(self) -> int:
        return self.n_time_ao * self.n_freq_ao

    @property
    def cbra_min_s(self) -> float:
        """Paging + sequential Msg1 time-AOs (Msg2/Msg3 added if any success)."""
        return self.paging_s + self.n_time_ao * self.msg1_s

    @property
    def cbra_full_s(self) -> float:
        return self.cbra_min_s + self.msg2_s + self.msg3_s


def device1_params() -> DeviceParams:
    """Published IEEE Table 1, Device 1."""
    e_max = 500e-9
    return DeviceParams(
        device_type=1,
        e_max_j=e_max,
        e_up_j=e_max,
        e_low_j=0.5 * e_max,
        p_rx_w=1e-6,
        p_tx_w=1e-6,
        p_sl_w=0.1e-6,
        paging_s=1e-3,
        t_pg_s=12e-3,
        msg1_s=0.5e-3,
        msg2_s=0.5e-3,
        msg3_s=3e-3,
        t_on_dcm_s=3e-3,
        t_on_timer_s=18e-3,
        n_time_ao=4,
        n_freq_ao=2,
        p_wakeup_w=None,
    )


def device2_params() -> DeviceParams:
    """Published IEEE Table 1, Device 2 (not the Fig. 5(b) target)."""
    e_max = 5000e-9
    return DeviceParams(
        device_type=2,
        e_max_j=e_max,
        e_up_j=e_max,
        e_low_j=0.5 * e_max,
        p_rx_w=50e-6,
        p_tx_w=200e-6,
        p_sl_w=0.1e-6,
        paging_s=1e-3,
        t_pg_s=14e-3,
        msg1_s=0.5e-3,
        msg2_s=0.5e-3,
        msg3_s=3e-3,
        t_on_dcm_s=1e-3,
        t_on_timer_s=26e-3,
        n_time_ao=4,
        n_freq_ao=4,
        p_wakeup_w=1e-6,
    )


@dataclass(frozen=True)
class AssumptionParams:
    """Implementation choices that the paper does not fully specify."""

    # Stationary energy-cycle phase stands in for a long charging stage
    # that is not on the Figure 5(b) time axis. "explicit" runs the
    # same ON/OFF machine for warmup_s instead of the closed-form cycle.
    warmup_mode: str = "stationary"
    warmup_s: float = 60.0
    # Grouping. Paper: first detected paging sets the wake phase (odd/even
    # example). Default first_paging_spread assigns a group at that moment
    # without stacking every simultaneous hearer into one group.
    # even_id_mod / random_preconfigured: preconfigured splits.
    # first_paging_mod: g = paging_index % N_g (paper-literal, often unbalanced).
    group_assignment: str = "first_paging_spread"
    pin_sampling: str = "stratified"  # stratified | iid
    # Access-probability controller (unpublished; paper has no equation).
    # occupancy_counts: Schoute n̂ from idle/singleton/collision AO counts.
    # poisson_idle: idle-AO Poisson; freeze p when TX < n_AO/2.
    # poisson_idle_ungated: same without the freeze.
    # fixed: p stays at p_init.
    access_controller: str = "occupancy_counts"
    # per_group: each paging/group has its own p (paper: p is in the paging).
    # global: one p shared across groups.
    p_access_scope: str = "per_group"
    p_access_init: float | None = None  # None → n_ao / n_load
    p_access_min: float = 0.002
    p_access_smoothing: float = 0.45
    target_attempts_per_ao: float = 1.0
    # Aperiodic paging: start next paging as soon as the previous CBRA ends.
    aperiodic_skip_unused_msg23: bool = True
    # IC off loses DCM inventory sync (sleep timer lives on the IC).
    # False keeps group/sync and must recharge then wait for the next epoch.
    off_clears_inventory_sync: bool = True
    # Paper default: after inventory-stage sync, each DCM occasion stays ON
    # for Table 1 T_on_DCM (Device 1: 3 ms). T_sl + T_on = T_pg (1-group)
    # or N_g T_pg (grouping). The paper does not say a failed access draw
    # may end the ON window after the 1 ms paging.
    # True is an experimental early-sleep optimization, not the paper model.
    sleep_when_not_attempting: bool = False
    # Lower bound on SLEEP net power: max(x, P_eh − P_sl).
    # Paper: −∞ (weak devices still drain). Experimental: 0 nW → no drain.
    sleep_net_power_min_w: float = float("-inf")
    # Factory visualization only; p_in is NOT computed from (x, y).
    factory_length_m: float = 120.0
    factory_width_m: float = 60.0
    reader_x_m: float = 60.0
    reader_y_m: float = 30.0
    pin_sensitivity_dbm: float = -36.0
    reader_tx_dbm: float = 33.0


@dataclass
class SimConfig:
    num_devices: int = 600
    device_type: int = 1
    seed: int = 42
    max_time_s: float = 25.0
    dt_s: float = 0.5e-3
    snapshot_interval_s: float = 0.1
    collect_snapshots: bool = True
    collect_paging_events: bool = True
    collect_energy_history: bool = True
    strategies: tuple[str, ...] = (
        Strategy.EM.value,
        Strategy.DCM_1_GROUP.value,
        Strategy.DCM_4_GROUP.value,
    )
    device: DeviceParams = field(default_factory=device1_params)
    assumptions: AssumptionParams = field(default_factory=AssumptionParams)

    @property
    def n_slots(self) -> int:
        return int(round(self.max_time_s / self.dt_s))

    @property
    def snapshot_stride(self) -> int:
        return max(1, int(round(self.snapshot_interval_s / self.dt_s)))

    def slots(self, seconds: float) -> int:
        return int(round(seconds / self.dt_s))

    def with_updates(self, **kwargs) -> "SimConfig":
        return replace(self, **kwargs)


def paper_device1_config(**overrides) -> SimConfig:
    cfg = SimConfig(device=device1_params(), device_type=1)
    if overrides:
        cfg = replace(cfg, **overrides)
    if cfg.device_type == 2:
        cfg = replace(cfg, device=device2_params())
    return cfg


def n_groups_for(strategy: str) -> int:
    if strategy == Strategy.DCM_4_GROUP.value:
        return 4
    if strategy == Strategy.DCM_1_GROUP.value:
        return 1
    return 1


def is_dcm(strategy: str) -> bool:
    return strategy.startswith("dcm")


def is_periodic(strategy: str) -> bool:
    return is_dcm(strategy)


def data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data"


def repo_root() -> Path:
    # backend/simulator/config.py → Implements/
    return Path(__file__).resolve().parents[2]


def results_dir() -> Path:
    return repo_root() / "results"


def strategy_label(strategy: str) -> str:
    return {
        Strategy.EM.value: "EM, aperiodic paging",
        Strategy.DCM_1_GROUP.value: "DCM, periodic paging, 1 group",
        Strategy.DCM_4_GROUP.value: "DCM, periodic paging, 4 groups",
    }.get(strategy, strategy)


def validate_strategies(strategies: Sequence[str]) -> tuple[str, ...]:
    allowed = {s.value for s in Strategy}
    out = []
    for s in strategies:
        if s not in allowed:
            raise ValueError(f"Unknown strategy '{s}'. Allowed: {sorted(allowed)}")
        if s not in out:
            out.append(s)
    if not out:
        raise ValueError("At least one strategy is required.")
    return tuple(out)
