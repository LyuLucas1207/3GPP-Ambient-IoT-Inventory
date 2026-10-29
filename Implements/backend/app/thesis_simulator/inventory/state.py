"""In-memory per-run state for the FSA engine.

``DeviceWorld`` keeps every per-device scalar in a numpy array (length N).
Everything about a device is addressable by its integer index in the arrays.
The scene-snapshot placement id is kept in ``placement_ids`` so emitted event
rows can carry the DB-side ``device_id``.

Terminal states are only ``identified`` and ``dropped`` (with a cause). A
mid-frame energy depletion is *not* terminal: as in the reference
``grouping_logic._kill`` the device is forced OFF, ungrouped, and later
recharges and competes again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.thesis_simulator.inventory.config import CONSTANTS, EngineConstants
from app.thesis_simulator.inventory.estimator import BacklogEstimator

SUBTYPE_CODE: dict[str, int] = {"1": 0, "2a": 1, "2b": 2}
SUBTYPE_LABEL: tuple[str, str, str] = ("1", "2a", "2b")
UPLINK_BACKSCATTER = 0
UPLINK_ACTIVE = 1

# Why a device ended up ``dropped``.
DROP_NONE = 0
DROP_UNREACHABLE = 1
DROP_MAX_TIME = 2
DROP_STOPPED = 3
DROP_NO_PROGRESS = 4
DROP_CAUSE_LABEL: tuple[str, ...] = ("", "unreachable", "max_time_reached", "stopped", "no_progress")

DEFAULT_STALL_TIMEOUT_S = 300.0
"""An open-ended run ends by itself after this much simulated time without a
single new identification (devices in coverage that can never be served)."""

# Live per-device state code (uint8) pushed to the browser. 0-2 and 6/8/9 are
# derived from the world arrays; 3/4/5/7 are transient outcomes of the last
# frame each reader ran.
STATE_OFF = 0
STATE_ON = 1
STATE_LATCHED = 2
STATE_TX = 3
STATE_M1_SUCCESS = 4
STATE_COLLISION = 5
STATE_IDENTIFIED = 6
STATE_DEPLETED = 7
STATE_DROPPED = 8
STATE_UNREACHABLE = 9
STATE_LABELS: tuple[str, ...] = (
    "off",
    "on",
    "latched",
    "tx",
    "m1_success",
    "collision",
    "identified",
    "depleted",
    "dropped",
    "unreachable",
)


@dataclass
class DeviceWorld:
    placement_ids: np.ndarray  # int64, length N
    subtype_code: np.ndarray  # int8, 0/1/2
    x_m: np.ndarray
    y_m: np.ndarray

    E: np.ndarray  # float64, J
    on: np.ndarray  # float64, s
    Ph_total: np.ndarray  # float64, W (summed across readers)

    Ecap: np.ndarray
    Eoff: np.ndarray
    P_on: np.ndarray
    T_on_default: np.ndarray
    T_on_dcm: np.ndarray

    p_rx: np.ndarray
    p_tx: np.ndarray
    rx_sens_dbm: np.ndarray
    uplink_code: np.ndarray  # int8: 0 backscatter / 1 active
    backscatter_loss_db: np.ndarray
    backscatter_gain_db: np.ndarray
    active_tx_power_dbm: np.ndarray  # NaN for backscatter devices
    include_d2r_default: bool

    grp: np.ndarray  # int32, -1 unlatched
    latched_reader: np.ndarray  # int32, -1 unlatched
    attempts: np.ndarray  # int32
    identified: np.ndarray  # bool
    dropped: np.ndarray  # bool
    drop_cause: np.ndarray  # int8, DROP_*
    depletions: np.ndarray  # int32, mid-frame energy depletions so far
    identified_t: np.ndarray  # float64, NaN until identified
    identified_by: np.ndarray  # int32 reader id, -1 until identified

    MUTABLE_FIELDS = (
        "E", "on", "grp", "latched_reader", "attempts", "identified",
        "dropped", "drop_cause", "depletions", "identified_t", "identified_by",
    )

    def __post_init__(self) -> None:
        n = len(self.placement_ids)
        for name in (
            "subtype_code", "x_m", "y_m", "E", "on", "Ph_total",
            "Ecap", "Eoff", "P_on", "T_on_default", "T_on_dcm",
            "p_rx", "p_tx", "rx_sens_dbm", "uplink_code",
            "backscatter_loss_db", "backscatter_gain_db", "active_tx_power_dbm",
            *self.MUTABLE_FIELDS,
        ):
            arr = getattr(self, name)
            if len(arr) != n:
                raise ValueError(f"{name} length {len(arr)} does not match N={n}")

    @property
    def N(self) -> int:
        return len(self.placement_ids)

    def terminal_mask(self) -> np.ndarray:
        return self.identified | self.dropped

    def all_terminal(self) -> bool:
        return bool(self.terminal_mask().all())

    def base_state_codes(self) -> np.ndarray:
        codes = np.where(self.on > 0.0, STATE_ON, STATE_OFF).astype(np.uint8)
        codes[self.grp >= 0] = STATE_LATCHED
        codes[self.identified] = STATE_IDENTIFIED
        codes[self.dropped] = STATE_DROPPED
        codes[self.dropped & (self.drop_cause == DROP_UNREACHABLE)] = STATE_UNREACHABLE
        return codes


@dataclass
class ReaderState:
    reader_id: int
    x_m: float
    y_m: float
    rf: dict[str, Any]
    include_d2r: bool
    freq_subband: int

    clock_s: float
    round_index: int
    estimator: BacklogEstimator

    cover_mask: np.ndarray  # bool, length N
    Ph_contrib: np.ndarray  # W per device
    d3d: np.ndarray  # m per device
    exhausted: bool = False  # no non-terminal device left in coverage


@dataclass
class EpisodeConfig:
    scheme: str  # 'periodic' | 'aperiodic'
    max_time_s: float | None
    k_initial: int | None
    g: int
    use_grouping: bool
    use_capture: bool
    use_ebi: bool
    include_d2r: bool
    seed: int | None
    reader_start_offsets: dict[str, float]
    disabled_reader_ids: list[int] = field(default_factory=list)
    stall_timeout_s: float | None = DEFAULT_STALL_TIMEOUT_S

    consts: EngineConstants = field(default_factory=lambda: CONSTANTS)

    @classmethod
    def from_json(cls, scheme: str, cfg: dict[str, Any]) -> "EpisodeConfig":
        max_time = cfg.get("max_time_s")
        stall = cfg.get("stall_timeout_s", DEFAULT_STALL_TIMEOUT_S)
        # Grouping is a periodic-paging mechanism; aperiodic devices never stay
        # aligned to a group's paging times.
        grouped = scheme == "periodic" and bool(cfg.get("use_grouping", False))
        return cls(
            scheme=scheme,
            max_time_s=None if max_time in (None, "") else float(max_time),
            k_initial=cfg.get("k_initial"),
            g=int(cfg.get("g") or 1) if grouped else 1,
            use_grouping=grouped,
            use_capture=bool(cfg.get("use_capture", True)),
            use_ebi=bool(cfg.get("use_ebi", True)),
            include_d2r=bool(cfg.get("include_d2r", True)),
            seed=cfg.get("seed"),
            reader_start_offsets=dict(cfg.get("reader_start_offsets") or {}),
            disabled_reader_ids=list(cfg.get("disabled_reader_ids") or []),
            stall_timeout_s=None if stall in (None, "") else float(stall),
            consts=CONSTANTS,
        )
