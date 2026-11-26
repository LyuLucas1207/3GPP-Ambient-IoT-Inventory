"""Scientific state, stage and mode enumerations for the aperiodic-paging paper."""

from enum import IntEnum, StrEnum


class DeviceState(StrEnum):
    """Per-device scientific state used in traces and the UI."""

    OFF = "OFF"
    MONITOR = "MONITOR"
    RX = "RX"
    TX = "TX"
    INTRA_ROUND_SLEEP = "INTRA_ROUND_SLEEP"
    INTERROUND_SYNC_SLEEP = "INTERROUND_SYNC_SLEEP"  # periodic baseline only
    DONE = "DONE"


class Stage(StrEnum):
    """CBRA stages used for energy ledgers and mid-round depletion counts."""

    PAGING = "paging"
    MSG1 = "msg1"
    EI = "EI"
    MSG2 = "msg2"
    MSG3 = "msg3"


STAGES: tuple[Stage, ...] = (Stage.PAGING, Stage.MSG1, Stage.EI, Stage.MSG2, Stage.MSG3)


class PagingMode(StrEnum):
    APERIODIC = "aperiodic"
    PERIODIC = "periodic"


class HarvestingScenario(StrEnum):
    SINGLE_SOURCE = "single_source"
    MULTI_SOURCE = "multi_source"


class ControllerName(StrEnum):
    PFSA_PZE = "pfsa_pze"
    DFSA_SCHOUTE = "dfsa_schoute"
    CMEBE = "cmebe"
    RECURRENT_PPO = "recurrent_ppo"


class RuntimeMode(StrEnum):
    INTERACTIVE = "interactive"
    PAPER_BATCH = "paper_batch"


class Mode(IntEnum):
    """Internal lazy-state mode of a device between rounds."""

    DCM = 0  # OFF/MONITOR duty cycle (initial acquisition, aperiodic idle, post-depletion)
    SYNC = 1  # periodic baseline: synchronized inter-round SLEEP
    DONE = 2


class AOPhysical(IntEnum):
    IDLE = 0
    SINGLE = 1
    CAPTURED = 2  # collision resolved by capture
    COLLISION = 3


class AOObserved(IntEnum):
    IDLE = 0
    SUCCESS = 1
    COLLISION = 2
