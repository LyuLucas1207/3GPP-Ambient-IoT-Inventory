"""Engine constants ported from the 3GPP aperiodic reference ``constants.py``.

Only the subset the FSA + DCM + energy engine actually reads. The RL block,
grouping variants, and import-time ``_validate_params_or_exit()`` print/exit
are deliberately omitted — this module must be side-effect free.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EngineConstants:
    # Message bits + line rate -> message durations (s)
    r_bps: float = 7000.0
    b_page: int = 80
    b_m1: int = 38
    b_m2: int = 88
    b_m3: int = 144
    ebi_preamble_bits: int = 16

    # Capture-effect ratio (6 dB) and energy-detector thresholds
    capture_f_lin: float = 10.0 ** (6.0 / 10.0)
    nplusi_dbm: float = -106.0
    det_nc: int = 4
    det_k_th: float = 4.0
    p_fa: float = 1e-3
    p_md: float = 1e-2

    # Frequency subbands per round (determines parallel M1 capacity)
    f_freq: int = 8

    # Per-type RX/TX (W) — used for mid-frame energy debits
    p_rx_1: float = 1e-6
    p_tx_1: float = 1e-6
    p_rx_2a: float = 50e-6
    p_tx_2a: float = 200e-6
    p_rx_2b: float = 50e-6
    p_tx_2b: float = 200e-6
    p_sleep: float = 1e-7

    # Estimator cold-start
    p0_init: float = 0.1
    p_min: float = 1e-8
    k_max: int = 668
    schoute_const: float = 2.39

    # Scheduling knobs that the UI never touches directly
    midframe_dying: bool = True
    ungroup_when_off: bool = True
    consider_weak_devices_in_grouping: bool = True

    def dcm_succ_ratio(self, use_capture: bool) -> float:
        return 0.5 if use_capture else 0.37

    def t_paging(self) -> float:
        return self.b_page / self.r_bps

    def t_m1(self) -> float:
        return self.b_m1 / self.r_bps

    def t_m2(self) -> float:
        return self.b_m2 / self.r_bps

    def t_m3(self) -> float:
        return self.b_m3 / self.r_bps

    def t_ebi(self, k: int, crc_bits: int = 6) -> float:
        return (self.ebi_preamble_bits + k + crc_bits) / self.r_bps

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.r_bps <= 0:
            problems.append("r_bps must be > 0")
        if not (0 < self.p_fa < 1):
            problems.append("p_fa must be in (0, 1)")
        if self.f_freq < 1:
            problems.append("f_freq must be >= 1")
        return problems


CONSTANTS = EngineConstants()
"""Default singleton — override by constructing a new EngineConstants if needed."""
