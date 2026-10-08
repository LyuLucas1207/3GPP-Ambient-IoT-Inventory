"""Configuration for the aperiodic-paging paper (Table II and named assumptions).

This model is separate from the legacy ``app.simulator.core.config.SimConfig``.

Notation: the legacy code uses ``T_pg`` for the paging *periodicity*. The new
paper's Appendix uses T_pg for the paging *message duration*. To avoid the
conflict, this package never uses ``T_pg``; it uses ``t_page_s``, ``t_msg1_s``,
``t_msg2_s``, ``t_msg3_s``, ``t_ei_s(L)`` and ``periodic_round_interval_s(L)``.
"""

from dataclasses import asdict, dataclass, field, replace

from app.aperiodic_simulator.core.states import (
    ControllerName,
    HarvestingScenario,
    PagingMode,
    RuntimeMode,
)


@dataclass(frozen=True)
class SystemParams:
    """Table II system values (global)."""

    factory_length_m: float = 120.0
    factory_width_m: float = 60.0
    n_bs: int = 18
    bs_spacing_m: float = 20.0
    bs_height_m: float = 8.0
    device_height_m: float = 1.5
    carrier_ghz: float = 0.9
    polarization_loss_db: float = 3.0
    shadow_fading_margin_db: float = 4.0
    on_object_penalty_db: float = 0.9
    bs_rx_sensitivity_dbm: float = -106.0
    bs_tx_power_dbm: float = 33.0
    bs_tx_antenna_gain_dbi: float = 6.0
    F: int = 8
    data_rate_bps: float = 7000.0
    paging_bits: int = 80
    msg1_bits: int = 38
    msg2_bits: int = 88
    msg3_bits: int = 144
    ei_overhead_bits: int = 24
    false_alarm_rate: float = 0.001
    missed_detection_rate: float = 0.01
    capture_ratio_db: float = 6.0
    t_mon_s: float = 0.100
    p_sl_w: float = 0.1e-6
    p_wurx_w: float = 1.0e-6
    single_source_min_pin_dbm: float = -36.0
    n_tot_default: int = 15000


@dataclass(frozen=True)
class Assumptions:
    """Named reproduction assumptions for details the paper leaves open.

    Every value here is reported in API metadata and the validation report.
    """

    # Uplink link budget: P_BS = P_in - L_bs + G_bs - PL + uplink_offset_db.
    # The paper/Table II does not give the full uplink budget of [40]. The
    # residual offset is calibrated so that the paper's reported type-1 and
    # type-2a coverage (Section V-B shares) is reproduced; both device types
    # independently imply the same value (about -5.6 dB).
    uplink_offset_db: float = -5.6
    reader_bs_index: int = 8  # BS at (50 m, 30 m), one of the two central BSs
    # Energy storage is capped at E_up (no capacitor maximum is given).
    energy_cap: str = "E_up"
    # Pre-page MONITOR is not credited with harvested energy: a DCM device
    # monitors for T_mon drawing P_mon*T_mon and then recharges it while OFF,
    # so its duty cycle is P_harv / (P_harv + P_mon) even when P_harv >= P_mon
    # (the DCM model of [19], as in the legacy simulator). Section 12 lists
    # harvesting for OFF and synchronized SLEEP only. Evidence: it reproduces
    # the paper's multi-source N_g=4 first-catch groups (69.5/23.9/4.7/1.9 %);
    # with harvest credit ~99 % of devices monitor continuously and all land in
    # group 1.
    harvest_during_monitor: bool = False
    # OFF, synchronized SLEEP and every in-round state (paging RX, Msg1-3,
    # EI, intra-round waiting) harvest continuously.
    harvest_in_round: bool = True
    # Initial availability: stationary phase of the charging-stage DCM cycle
    # (E_up -> monitor T_mon -> OFF -> recharge to E_up), drawn uniformly.
    initial_availability: str = "stationary_dcm_phase"
    # Periodic synchronized devices wake exactly at their paging opportunity.
    periodic_wake_guard_s: float = 0.0
    # A device that depletes (OFF) loses its low-power clock and must reacquire
    # a page with DCM; periodic devices keep their first-catch group.
    off_loses_sync: bool = True
    # Reader observation: false alarm on an idle AO is observed as a collision
    # (activity without a decodable RN16); missed detection turns an occupied
    # AO into an observed idle AO.
    false_alarm_observed_as: str = "collision"
    # Capture: strongest Msg1 power >= capture ratio x sum of the other powers.
    capture_rule: str = "strongest_over_sum_of_interferers"
    # Aperiodic Msg3 uses ceil(K/F) time slots; the periodic baseline uses the
    # paper's time-equivalent (K/F) * t_msg3 so that the 82 ms / 1089 ms
    # interval oracles hold.
    aperiodic_msg3_slots: str = "ceil(K/F)"
    # PZE fallback when every AO collided (estimator diverges): use I = 1.
    pze_all_collided_idle_floor: float = 1.0
    # Numerical floor for access probability p in (0, 1].
    p_floor: float = 1e-4
    # S_1/S_2a/S_2b count devices identified (Msg3 completed) in the round.
    success_counts: str = "identified_after_msg3"
    # C2 counts physically multi-occupied AOs containing a type 2a/2b device.
    c2_definition: str = "physical_multi_occupancy_with_type2"


@dataclass(frozen=True)
class EpisodeConfig:
    """One simulation episode (one seed)."""

    n_tot: int = 15000
    seed: int = 42
    harvesting_scenario: HarvestingScenario = HarvestingScenario.MULTI_SOURCE
    paging_mode: PagingMode = PagingMode.APERIODIC
    controller: ControllerName = ControllerName.PFSA_PZE
    L_fixed: int = 16
    L_initial: int | None = None
    p_initial: float = 1.0
    N_g: int = 1
    enforce_midround_depletion: bool = True
    alpha: float = 0.5
    t_max_s: float = 1200.0
    max_rounds: int = 2_000_000
    runtime_mode: RuntimeMode = RuntimeMode.PAPER_BATCH
    # Device-type mix: "mixed" = even pre-coverage split; or "1", "2a", "2b".
    type_mix: str = "mixed"
    type_weights: tuple[float, float, float] | None = None
    trace_device_ids: tuple[int, ...] = ()
    n_trace_samples: int = 0
    snapshot_interval_s: float = 0.0
    impairments_enabled: bool = True
    system: SystemParams = field(default_factory=SystemParams)
    assumptions: Assumptions = field(default_factory=Assumptions)

    def with_(self, **kwargs) -> "EpisodeConfig":
        return replace(self, **kwargs)


def config_to_dict(cfg: EpisodeConfig) -> dict:
    d = asdict(cfg)
    for k, v in list(d.items()):
        if hasattr(v, "value"):
            d[k] = v.value
    return d
