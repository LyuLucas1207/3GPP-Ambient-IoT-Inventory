"""New-paper periodic paging baseline with first-catch grouping (Sec. II-D, Fig. 1).

    initial DCM acquisition
    -> first detected page establishes inventory synchronization
    -> the device joins the group of that page (first catch), N_g in {1, 4}
    -> synchronized inter-round SLEEP (low-power clock), waking only for its
       group's paging opportunity (every N_g-th page)
    -> access decision / CBRA; failure or rejection keeps periodic retries
    -> energy below E_low -> OFF; recharge to E_up and reacquire a page by DCM

Rounds have the fixed interval T_periodic(L) with K_fixed = 0.5 L F reserved
Msg2/Msg3 resources. Group g is paged in rounds r with r mod N_g == g.

Assumptions (see ``config.Assumptions``): synchronized devices wake exactly at
their page; a device that turns OFF loses its clock and reacquires a page by
DCM but keeps its first-catch group (it resynchronizes if the caught page
belongs to another group). ``first_paging_spread`` from the legacy code is not
used.
"""

import numpy as np

from app.aperiodic_simulator.core.states import Mode
from app.aperiodic_simulator.core.timing import periodic_round_interval_s


class PeriodicPaging:
    name = "periodic"
    periodic = True

    def __init__(self, episode):
        self.ep = episode

    def before_round(self, r: int, t0: float) -> int:
        """Synchronized sleepers whose energy reached E_low before t0 turn OFF."""
        ep = self.ep
        sync = np.flatnonzero(ep.mode == Mode.SYNC)
        if not sync.size:
            return 0
        drift = ep.p_harv[sync] - ep.p_sl[sync]
        neg = drift < 0
        t_die = np.full(sync.size, np.inf)
        t_die[neg] = ep.t_last[sync][neg] + (ep.e_last[sync][neg] - ep.e_low[sync][neg]) / (-drift[neg])
        dead = t_die <= t0
        if dead.any():
            di = sync[dead]
            ep._to_dcm(di, t_die[dead], ep.e_low[di])
        return int(dead.sum())

    def select(self, r: int, t0: float, dcm_idx: np.ndarray, e_dcm: np.ndarray):
        ep = self.ep
        g_now = r % ep.N_g
        new = ep.group[dcm_idx] < 0
        ep.group[dcm_idx[new]] = g_now  # first-catch group assignment
        other = ep.group[dcm_idx] != g_now
        resync_idx, resync_e = dcm_idx[other], e_dcm[other]
        acq_idx, acq_e = dcm_idx[~other], e_dcm[~other]
        wake = np.flatnonzero((ep.mode == Mode.SYNC) & (ep.wake_round == r))
        e_wake = np.minimum(
            ep.e_last[wake] + (ep.p_harv[wake] - ep.p_sl[wake]) * (t0 - ep.t_last[wake]),
            ep.e_up[wake],
        )
        ep.trace.wake_sync(wake, t0, e_wake)
        cand = np.concatenate([acq_idx, wake])
        e_start = np.concatenate([acq_e, e_wake])
        return cand, e_start, resync_idx, resync_e, g_now

    def round_end(self, t0: float, L: int, k_decoded: int) -> float:
        return t0 + periodic_round_interval_s(L, self.ep.system)

    def after_exit(self, r: int, idx: np.ndarray, t: np.ndarray, e: np.ndarray, forced_off: np.ndarray) -> None:
        """Failed/rejected devices sleep until their group's next page."""
        ep = self.ep
        off = forced_off | (e < ep.e_low[idx])
        if off.any():
            ep._to_dcm(idx[off], t[off], e[off])
        keep = ~off
        if keep.any():
            ep._to_sync(idx[keep], t[keep], e[keep], r)

    def after_resync(self, r: int, idx: np.ndarray, t: np.ndarray, e: np.ndarray) -> None:
        self.after_exit(r, idx, t, e, np.zeros(idx.size, dtype=bool))
