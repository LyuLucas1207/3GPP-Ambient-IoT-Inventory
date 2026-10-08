"""Per-device scientific traces (sampled devices only).

A trace is a list of piecewise-linear energy segments, each with a scientific
state (OFF, MONITOR, RX, TX, INTRA_ROUND_SLEEP, INTERROUND_SYNC_SLEEP, DONE)
and, inside a CBRA round, the stage (paging, msg1, EI, msg2, msg3). DCM duty
cycles between rounds are expanded analytically from the lazy device state.
"""

import math

import numpy as np

from app.aperiodic_simulator.core.states import DeviceState as S
from app.aperiodic_simulator.core.states import Stage

MAX_DCM_CYCLES_PER_GAP = 400


class TraceRecorder:
    def __init__(self, ids: list[int], ep):
        self.ep = ep
        self.ids = ids
        self.mask = np.zeros(ep.n, dtype=bool)
        if ids:
            self.mask[np.asarray(ids)] = True
        self.segments: dict[int, list[dict]] = {i: [] for i in ids}
        self.pending_dcm: dict[int, tuple[float, float]] = {}
        self.pending_sync: dict[int, tuple[float, float]] = {}
        if ids:
            e0 = ep.dcm_energy_at(0.0, np.asarray(ids))
            for i, e in zip(ids, e0):
                self.pending_dcm[i] = (0.0, float(e))

    def _sel(self, idx: np.ndarray) -> np.ndarray:
        if not self.ids or idx.size == 0:
            return np.empty(0, dtype=np.int64)
        return np.flatnonzero(self.mask[idx])

    def _add(self, dev: int, t0: float, t1: float, state: S, e0: float, e1: float, stage: Stage | None = None, **extra) -> None:
        if t1 <= t0 + 1e-12:
            return
        seg = {
            "t0": t0,
            "t1": t1,
            "state": state.value,
            "stage": stage.value if stage else None,
            "e0_uJ": e0 * 1e6,
            "e1_uJ": e1 * 1e6,
        }
        seg.update(extra)
        self.segments[dev].append(seg)

    # ------------------------------------------------------------ DCM expansion
    def _expand_dcm(self, dev: int, t_from: float, e_from: float, t_to: float) -> None:
        ep = self.ep
        a, c, tm = float(ep.anchor[dev]), float(ep.cycle[dev]), ep.t_mon
        e_up, drain, harv = float(ep.e_up[dev]), float(ep.drain[dev]), float(ep.p_harv[dev])
        e_mon_end = e_up - drain * tm
        t = t_from
        if t < a:
            end = min(a, t_to)
            self._add(dev, t, end, S.OFF, e_from, min(e_from + harv * (end - t), e_up))
            t = end
        if t >= t_to:
            return
        k = math.floor((t - a) / c)
        cycles = 0
        while t < t_to - 1e-12:
            w0, w1 = a + k * c, a + k * c + tm
            if t < w1:
                s0 = max(t, w0)
                s1 = min(w1, t_to)
                self._add(dev, s0, s1, S.MONITOR, e_up - drain * (s0 - w0), e_up - drain * (s1 - w0))
                t = s1
            if t >= t_to - 1e-12:
                break
            nxt = a + (k + 1) * c
            if nxt > t:
                s1 = min(nxt, t_to)
                e0 = min(e_mon_end + harv * (t - w1), e_up)
                self._add(dev, t, s1, S.OFF, e0, min(e_mon_end + harv * (s1 - w1), e_up))
                t = s1
            k += 1
            cycles += 1
            if cycles >= MAX_DCM_CYCLES_PER_GAP and t < t_to:
                self._add(dev, t, t_to, S.OFF, e_up, e_up, duty_cycle_compressed=True)
                return

    def _close_pending(self, dev: int, t: float) -> None:
        if dev in self.pending_dcm:
            t0, e0 = self.pending_dcm.pop(dev)
            self._expand_dcm(dev, t0, e0, t)
        if dev in self.pending_sync:
            t0, e0 = self.pending_sync.pop(dev)
            ep = self.ep
            e1 = min(e0 + (float(ep.p_harv[dev]) - float(ep.p_sl[dev])) * (t - t0), float(ep.e_up[dev]))
            self._add(dev, t0, t, S.INTERROUND_SYNC_SLEEP, e0, e1)

    # ------------------------------------------------------------ events
    def enter_dcm(self, idx: np.ndarray, t: np.ndarray, e: np.ndarray) -> None:
        for j in self._sel(idx):
            dev = int(idx[j])
            self._close_pending(dev, float(t[j]))
            self.pending_dcm[dev] = (float(t[j]), float(e[j]))

    def enter_sync(self, idx: np.ndarray, t: np.ndarray, e: np.ndarray) -> None:
        for j in self._sel(idx):
            dev = int(idx[j])
            self.pending_sync[dev] = (float(t[j]), float(e[j]))

    def catch_dcm(self, idx: np.ndarray, t0: float, phase: np.ndarray) -> None:
        for j in self._sel(idx):
            self._close_pending(int(idx[j]), t0)

    def wake_sync(self, idx: np.ndarray, t0: float, e: np.ndarray) -> None:
        for j in self._sel(idx):
            self._close_pending(int(idx[j]), t0)

    def page(self, idx: np.ndarray, t0: float, tpg: float, e0: np.ndarray, e1: np.ndarray) -> None:
        for j in self._sel(idx):
            self._add(int(idx[j]), t0, t0 + tpg, S.RX, float(e0[j]), float(e1[j]), Stage.PAGING)

    def round_participants(self, part: np.ndarray, out, e_start: np.ndarray, L: int, system) -> None:
        sel = self._sel(part)
        if not sel.size:
            return
        from app.aperiodic_simulator.core.timing import t_ei_s, t_msg1_s, t_msg2_s, t_msg3_s

        ep, F = self.ep, system.F
        t1, t2, t3, tei = t_msg1_s(system), t_msg2_s(system), t_msg3_s(system), t_ei_s(L, system=system)
        k_slots = int(math.floor(out.k_alloc))
        for j in sel:
            dev = int(part[j])
            slot = int(out.ao[j]) // F
            k = int(out.msg2_index[j])
            sched: list[tuple[S, Stage, float, float]] = []
            p_tx, p_rx, p_sl = float(ep.p_tx[dev]), float(ep.p_rx[dev]), float(ep.p_sl[dev])
            sched += [
                (S.INTRA_ROUND_SLEEP, Stage.MSG1, slot * t1, p_sl),
                (S.TX, Stage.MSG1, t1, p_tx),
                (S.INTRA_ROUND_SLEEP, Stage.MSG1, (L - 1 - slot) * t1, p_sl),
                (S.RX, Stage.EI, tei, p_rx),
            ]
            if k >= 0:
                sched += [(S.INTRA_ROUND_SLEEP, Stage.MSG2, k * t2, p_sl), (S.RX, Stage.MSG2, t2, p_rx)]
                if bool(out.identified[j]) or out.fate[j] == 0 or out.fate[j] == 5:
                    jj = k // F
                    sched += [
                        (S.INTRA_ROUND_SLEEP, Stage.MSG2, max(k_slots - 1 - k, 0) * t2, p_sl),
                        (S.INTRA_ROUND_SLEEP, Stage.MSG3, jj * t3, p_sl),
                        (S.TX, Stage.MSG3, t3, p_tx),
                    ]
            t = out.t_msg1_start
            e = float(e_start[j])
            t_exit = float(out.exit_time_s[j])
            harv, e_up = float(ep.p_harv_round[dev]), float(ep.e_up[dev])
            for state, stage, dur, pw in sched:
                if t >= t_exit - 1e-12:
                    break
                d = min(dur, t_exit - t)
                e1 = min(e + (harv - pw) * d, e_up)
                self._add(dev, t, t + d, state, e, e1, stage)
                t, e = t + d, e1

    def done(self, idx: np.ndarray, t: np.ndarray) -> None:
        for j in self._sel(idx):
            dev = int(idx[j])
            self.segments[dev].append({"t0": float(t[j]), "t1": float(t[j]), "state": S.DONE.value, "stage": None})

    def finalize(self, t_end: float) -> None:
        for dev in list(self.pending_dcm) + list(self.pending_sync):
            self._close_pending(dev, t_end)

    def payload(self, dev: int) -> dict:
        ep = self.ep
        return {
            "device_id": dev,
            "type": ["1", "2a", "2b"][int(ep.type_idx[dev])],
            "p_harv_uW": float(ep.p_harv[dev]) * 1e6,
            "E_up_uJ": float(ep.e_up[dev]) * 1e6,
            "E_low_uJ": float(ep.e_low[dev]) * 1e6,
            "group": int(ep.group[dev]) if ep.group[dev] >= 0 else None,
            "completion_s": float(ep.t_done[dev]) if np.isfinite(ep.t_done[dev]) else None,
            "segments": self.segments.get(dev, []),
        }
