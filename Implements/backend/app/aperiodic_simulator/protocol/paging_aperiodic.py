"""Proposed aperiodic paging protocol (Sec. III-B, Fig. 2).

    OFF/harvest -> E_up -> MONITOR (<= T_mon)
        no page within T_mon -> OFF
        page -> receive page -> access decision p_s
            rejected             -> OFF after the opportunity
            CBRA success         -> DONE
            collision / missed / other failure -> OFF
    -> harvest back to E_up -> monitor again and reacquire a later page

There is no cross-round paging synchronization. Msg2/Msg3 are provisioned from
the round's decoded Msg1 (EI), and the next page starts when the round ends.
"""

import numpy as np

from app.aperiodic_simulator.core.timing import aperiodic_round_duration_s


class AperiodicPaging:
    name = "aperiodic"
    periodic = False

    def __init__(self, episode):
        self.ep = episode

    def before_round(self, r: int, t0: float) -> int:
        return 0

    def select(self, r: int, t0: float, dcm_idx: np.ndarray, e_dcm: np.ndarray):
        """All devices that caught the page are candidates."""
        empty = np.empty(0, dtype=np.int64)
        return dcm_idx, e_dcm, empty, np.empty(0), None

    def round_end(self, t0: float, L: int, k_decoded: int) -> float:
        return t0 + aperiodic_round_duration_s(L, k_decoded, self.ep.system)

    def after_exit(self, r: int, idx: np.ndarray, t: np.ndarray, e: np.ndarray, forced_off: np.ndarray) -> None:
        """Rejected or failed devices return to OFF and recharge (no sync)."""
        if idx.size:
            self.ep._to_dcm(idx, t, e)

    def after_resync(self, r: int, idx: np.ndarray, t: np.ndarray, e: np.ndarray) -> None:
        if idx.size:
            raise RuntimeError("aperiodic paging has no resynchronization")
