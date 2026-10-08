"""Continuous-time, phase-driven engine for the aperiodic-paging paper.

The reader timeline is a sequence of back-to-back CBRA rounds; one engine step
is one round (never a 0.5 ms tick). Devices hold lazy state that is only
evaluated when a page is issued:

* ``Mode.DCM``  - OFF/MONITOR duty cycle. After reaching E_up at ``anchor`` the
  device monitors for T_mon, returns OFF and recharges to E_up; the cycle is
  periodic with ``cycle`` = T_mon + recharge time. A page starting at t0 is
  caught iff (t0 - anchor) mod cycle <= T_mon.
* ``Mode.SYNC`` - periodic baseline only: synchronized inter-round SLEEP with
  energy (e_last, t_last) and net drift P_harv - P_sl, waking at round
  ``wake_round``. If the drift is negative it turns OFF when E hits E_low.
* ``Mode.DONE`` - identified.

Protocol semantics live in ``paging_periodic`` / ``paging_aperiodic``; the
round itself in ``cbra``.
"""

from dataclasses import dataclass, field

import numpy as np

from app.aperiodic_simulator.protocol.cbra import NO_STAGE, Fate, ParticipantInputs, run_cbra
from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.physics.device_types import TYPE_NAMES, type_param_arrays
from app.aperiodic_simulator.protocol.grouping import group_populations
from app.aperiodic_simulator.physics.harvesting import Population, build_population
from app.aperiodic_simulator.protocol.paging_aperiodic import AperiodicPaging
from app.aperiodic_simulator.protocol.paging_periodic import PeriodicPaging
from app.aperiodic_simulator.core.states import STAGES, DeviceState, Mode, PagingMode, RuntimeMode
from app.aperiodic_simulator.core.timing import (
    collision_time_equivalent_s,
    success_time_equivalent_s,
    t_msg3_s,
    t_page_s,
)
from app.aperiodic_simulator.core.trace import TraceRecorder
from app.common.rf import dbm_to_watts

SNAPSHOT_SAMPLE = 400
INSPECT_FIRST_ROUNDS = 200
INSPECT_STRIDE = 20
INSPECT_MAX = 400
STATE_CODES = [s.value for s in DeviceState]


@dataclass
class RoundRecord:
    index: int
    t_start_s: float
    t_end_s: float
    L: int
    p: float
    n_ao: int
    group: int | None
    n_paged: int
    n_candidates: int
    n_participants: int
    n_rejected: int
    n_resync: int
    S_by_type: dict[str, int]
    idle_obs: int
    collision_obs: int
    success_obs: int
    physical: dict[str, int]
    missed: int
    false_alarm: int
    C2: int
    k_decoded: int
    k_alloc: float
    k_served: int
    msg2_wasted: float
    msg1_success_lost_to_depletion: int
    depletion_by_stage: dict[str, int]
    would_deplete_by_stage: dict[str, int]
    interround_depletions: int
    reward: float
    components_s: dict[str, float]
    energy_ledger_uj: dict[str, float]
    n_done_total: int
    fates: dict[str, int] = field(default_factory=dict)

    @property
    def S_total(self) -> int:
        return sum(self.S_by_type.values())

    @property
    def duration_s(self) -> float:
        return self.t_end_s - self.t_start_s

    def observation(self) -> dict:
        """The only round information a controller may see (Eq. 5)."""
        return {
            "S1": self.S_by_type["1"],
            "S2a": self.S_by_type["2a"],
            "S2b": self.S_by_type["2b"],
            "I": self.idle_obs,
            "C": self.collision_obs,
            "L": self.L,
            "p": self.p,
            "decoded": self.success_obs,
        }

    def to_dict(self) -> dict:
        d = {k: getattr(self, k) for k in self.__dataclass_fields__}
        d["S_total"] = self.S_total
        d["duration_s"] = self.duration_s
        return d


class Episode:
    def __init__(self, cfg: EpisodeConfig, population: Population | None = None):
        self.cfg = cfg
        s = cfg.system
        self.system = s
        ss = np.random.SeedSequence(cfg.seed)
        (r_pop, r_init, self.rng_access, self.rng_ao, self.rng_imp, self.rng_misc) = (
            np.random.default_rng(c) for c in ss.spawn(6)
        )
        self.population = population or build_population(
            cfg.n_tot, r_pop, cfg.harvesting_scenario, s, cfg.assumptions, cfg.type_mix, cfg.type_weights
        )
        pop = self.population
        self.global_ids = np.flatnonzero(pop.eligible)
        n = self.global_ids.size
        self.n = n
        self.type_idx = pop.type_idx[self.global_ids].astype(np.int64)
        self.is_type2 = self.type_idx > 0
        par = type_param_arrays(self.type_idx, s)
        self.p_tx, self.p_rx, self.p_mon = par["p_tx_w"], par["p_rx_w"], par["p_wurx_w"]
        self.p_sl, self.e_up, self.e_low = par["p_sl_w"], par["e_up_j"], par["e_low_j"]
        self.p_harv = np.maximum(pop.p_harv_w[self.global_ids], 1e-15)
        self.p_ul_w = dbm_to_watts(pop.p_ul_dbm[self.global_ids])
        self.xy = pop.xy[self.global_ids]
        self.t_mon = s.t_mon_s
        if cfg.assumptions.harvest_during_monitor:
            self.drain = np.maximum(self.p_mon - self.p_harv, 0.0)
        else:
            self.drain = self.p_mon.copy()
        self.p_harv_round = self.p_harv if cfg.assumptions.harvest_in_round else np.zeros(n)
        self.cycle = self.t_mon + self.drain * self.t_mon / self.p_harv
        # Stationary charging-stage DCM phase (initial availability).
        self.anchor = -r_init.random(n) * self.cycle
        self.mode = np.full(n, Mode.DCM, dtype=np.int8)
        self.e_last = self.e_up.copy()
        self.t_last = np.zeros(n)
        self.wake_round = np.full(n, -1, dtype=np.int64)
        self.group = np.full(n, -1, dtype=np.int64)
        self.t_done = np.full(n, np.inf)
        self.first_page_time = np.full(n, np.inf)
        self.mode_paging = PagingMode(cfg.paging_mode)
        periodic = self.mode_paging == PagingMode.PERIODIC
        self.N_g = max(1, int(cfg.N_g)) if periodic else 1
        self.protocol = PeriodicPaging(self) if periodic else AperiodicPaging(self)
        self.L_periodic: int | None = None
        self.t = 0.0
        self.r = 0
        self.keep_rounds = cfg.runtime_mode == RuntimeMode.INTERACTIVE
        self.rounds: list[RoundRecord] = []
        self.history: list[tuple] = []
        self.depletion_totals = {st.value: 0 for st in STAGES}
        self.would_deplete_totals = {st.value: 0 for st in STAGES}
        self.interround_depletions = 0
        self.energy_ledger_uj = {"monitor": 0.0, **{st.value: 0.0 for st in STAGES}}
        self.total_ao = 0
        self.msg1_successes_nominal = 0
        self.msg1_success_lost = 0
        trace_ids = set(int(i) for i in cfg.trace_device_ids if 0 <= int(i) < n)
        if cfg.n_trace_samples > 0 and n > 0:
            pick = r_init.choice(n, size=min(cfg.n_trace_samples, n), replace=False)
            trace_ids.update(int(i) for i in pick)
        self.trace = TraceRecorder(sorted(trace_ids), self)
        self.snapshots: list[dict] = []
        self._next_snapshot_t = 0.0
        # Interactive playback covers a device sample, never the full population.
        k = min(SNAPSHOT_SAMPLE, n)
        self.snapshot_ids = np.sort(self.rng_misc.choice(n, size=k, replace=False)) if k else np.empty(0, dtype=np.int64)
        self.cbra_inspect: list[dict] = []

    # ------------------------------------------------------------------ state
    @property
    def n_done(self) -> int:
        return int((self.mode == Mode.DONE).sum())

    @property
    def finished(self) -> bool:
        return (
            self.n_done >= self.n
            or self.t >= self.cfg.t_max_s
            or self.r >= self.cfg.max_rounds
        )

    def dcm_energy_at(self, t: float, idx: np.ndarray) -> np.ndarray:
        a, c = self.anchor[idx], self.cycle[idx]
        e_up = self.e_up[idx]
        before = t < a
        phase = np.mod(t - a, c)
        mon_end_e = e_up - self.drain[idx] * self.t_mon
        e_cycle = np.where(
            phase <= self.t_mon,
            e_up - self.drain[idx] * phase,
            np.minimum(mon_end_e + self.p_harv[idx] * (phase - self.t_mon), e_up),
        )
        e_before = e_up - self.p_harv[idx] * (a - t)
        return np.where(before, e_before, e_cycle)

    def states_at(self, t: float) -> tuple[np.ndarray, np.ndarray]:
        """Scientific state and energy of all devices at time t (between rounds)."""
        idx = np.arange(self.n)
        state = np.full(self.n, DeviceState.OFF.value, dtype=object)
        energy = np.zeros(self.n)
        dcm = self.mode == Mode.DCM
        e = self.dcm_energy_at(t, idx[dcm])
        a = self.anchor[dcm]
        mon = (t >= a) & (np.mod(t - a, self.cycle[dcm]) <= self.t_mon)
        state[dcm] = np.where(mon, DeviceState.MONITOR.value, DeviceState.OFF.value)
        energy[dcm] = e
        sync = self.mode == Mode.SYNC
        state[sync] = DeviceState.INTERROUND_SYNC_SLEEP.value
        energy[sync] = np.minimum(
            self.e_last[sync] + (self.p_harv[sync] - self.p_sl[sync]) * (t - self.t_last[sync]),
            self.e_up[sync],
        )
        done = self.mode == Mode.DONE
        state[done] = DeviceState.DONE.value
        energy[done] = np.nan
        return state, energy

    def _next_group_round(self, r: int, group: np.ndarray) -> np.ndarray:
        return r + 1 + np.mod(group - (r + 1), self.N_g)

    def _to_dcm(self, idx: np.ndarray, t_off: np.ndarray, e_off: np.ndarray) -> None:
        e_off = np.clip(e_off, 0.0, self.e_up[idx])
        self.mode[idx] = Mode.DCM
        self.anchor[idx] = t_off + (self.e_up[idx] - e_off) / self.p_harv[idx]
        self.wake_round[idx] = -1
        self.trace.enter_dcm(idx, t_off, e_off)

    def _to_sync(self, idx: np.ndarray, t: np.ndarray, e: np.ndarray, r: int) -> None:
        self.mode[idx] = Mode.SYNC
        self.e_last[idx] = e
        self.t_last[idx] = t
        self.wake_round[idx] = self._next_group_round(r, self.group[idx])
        self.trace.enter_sync(idx, t, e)

    # ------------------------------------------------------------------ round
    def step(self, L: int, p: float) -> RoundRecord:
        cfg, s = self.cfg, self.system
        L = int(L)
        if L < 1:
            raise ValueError("L must be >= 1")
        p = float(min(max(p, cfg.assumptions.p_floor), 1.0))
        if self.protocol.periodic:
            if self.L_periodic is None:
                self.L_periodic = L
            elif L != self.L_periodic:
                raise ValueError("periodic paging uses a fixed L across rounds")
        r, t0 = self.r, self.t
        tpg = t_page_s(s)
        enforce = cfg.enforce_midround_depletion
        self._maybe_snapshot(t0)

        interround = self.protocol.before_round(r, t0)
        self.interround_depletions += interround

        # DCM catchers: a page starting within the device's monitoring window.
        dcm = np.flatnonzero((self.mode == Mode.DCM) & (self.anchor <= t0))
        phase = np.mod(t0 - self.anchor[dcm], self.cycle[dcm])
        catch = phase <= self.t_mon
        dcm_idx, dcm_phase = dcm[catch], phase[catch]
        e_dcm = self.e_up[dcm_idx] - self.drain[dcm_idx] * dcm_phase
        mon_energy = self.p_mon[dcm_idx] * dcm_phase
        self.trace.catch_dcm(dcm_idx, t0, dcm_phase)

        cand, e_start, resync_idx, resync_e, group_now = self.protocol.select(r, t0, dcm_idx, e_dcm)
        self.first_page_time[cand] = np.minimum(self.first_page_time[cand], t0)

        # Paging reception (P_rx for t_page) for every device that heard the page.
        paged = np.concatenate([cand, resync_idx])
        page_cost = self.p_rx[paged] * tpg
        e_pg = np.minimum(
            np.concatenate([e_start, resync_e]) - page_cost + self.p_harv_round[paged] * tpg,
            self.e_up[paged],
        )
        t_after_page = t0 + tpg
        self.trace.page(paged, t0, tpg, np.concatenate([e_start, resync_e]), e_pg)
        dep_pg = e_pg < self.e_low[paged]
        depletion = {st.value: 0 for st in STAGES}
        would = {st.value: 0 for st in STAGES}
        (depletion if enforce else would)["paging"] = int(dep_pg.sum())
        if enforce and dep_pg.any():
            di = paged[dep_pg]
            self._to_dcm(di, np.full(di.size, t_after_page), self.e_low[di])
        n_c = cand.size
        if resync_idx.size:
            ok = ~dep_pg[n_c:] if enforce else np.ones(resync_idx.size, dtype=bool)
            self.protocol.after_resync(r, resync_idx[ok], np.full(int(ok.sum()), t_after_page), e_pg[n_c:][ok])
        ok = ~dep_pg[:n_c] if enforce else np.ones(n_c, dtype=bool)
        cand, e_c = cand[ok], e_pg[:n_c][ok]

        # Access-probability decision.
        go = self.rng_access.random(cand.size) < p
        rej, e_rej = cand[~go], e_c[~go]
        part, e_part = cand[go], e_c[go]

        out = run_cbra(
            t0,
            L,
            self.mode_paging,
            ParticipantInputs(
                energy_j=e_part,
                p_tx_w=self.p_tx[part],
                p_rx_w=self.p_rx[part],
                p_sl_w=self.p_sl[part],
                p_harv_w=self.p_harv_round[part],
                e_low_j=self.e_low[part],
                e_up_j=self.e_up[part],
                p_ul_w=self.p_ul_w[part],
                is_type2=self.is_type2[part],
            ),
            self.rng_ao,
            self.rng_imp,
            s,
            enforce_depletion=enforce,
            impairments_enabled=cfg.impairments_enabled,
        )
        t_end = self.protocol.round_end(t0, L, out.k_decoded)
        self.trace.round_participants(part, out, e_part, L, s)

        for code, st in enumerate(STAGES):
            cnt = int((out.depleted_stage == code).sum())
            (depletion if enforce else would)[st.value] += cnt
        has_msg2 = out.msg2_index >= 0
        lost = int((has_msg2 & (out.fate == Fate.DEPLETED)).sum())
        self.msg1_successes_nominal += int((out.fate == Fate.SUCCESS).sum()) + lost
        self.msg1_success_lost += lost

        # Transitions.
        ident = part[out.identified]
        self.mode[ident] = Mode.DONE
        self.t_done[ident] = out.exit_time_s[out.identified]
        self.trace.done(ident, out.exit_time_s[out.identified])
        failed = ~out.identified
        f_dep = (out.depleted_stage[failed] != NO_STAGE) & enforce
        self.protocol.after_exit(
            r,
            np.concatenate([rej, part[failed]]),
            np.concatenate([np.full(rej.size, t_after_page), out.exit_time_s[failed]]),
            np.concatenate([e_rej, out.exit_energy_j[failed]]),
            np.concatenate([np.zeros(rej.size, dtype=bool), f_dep]),
        )

        ledger = {st.value: float(out.stage_energy_j[st.value].sum()) * 1e6 for st in STAGES}
        ledger["paging"] = float(page_cost.sum()) * 1e6
        ledger["monitor"] = float(mon_energy.sum()) * 1e6
        for k_, v in ledger.items():
            self.energy_ledger_uj[k_] += v
        S_by_type = {name: int((self.type_idx[ident] == i).sum()) for i, name in enumerate(TYPE_NAMES)}
        obs = out.resolution.observed_counts()
        T_round = t_end - t0
        alpha = cfg.alpha
        reward = (
            (1 - alpha) * sum(S_by_type.values()) * success_time_equivalent_s(s)
            - alpha * out.resolution.c2 * collision_time_equivalent_s(s)
        ) / T_round
        rec = RoundRecord(
            index=r,
            t_start_s=t0,
            t_end_s=t_end,
            L=L,
            p=p,
            n_ao=L * s.F,
            group=group_now,
            n_paged=int(paged.size),
            n_candidates=int(n_c),
            n_participants=int(part.size),
            n_rejected=int(rej.size),
            n_resync=int(resync_idx.size),
            S_by_type=S_by_type,
            idle_obs=obs["idle"],
            collision_obs=obs["collision"],
            success_obs=obs["success"],
            physical=out.resolution.physical_counts(),
            missed=int(out.resolution.missed.sum()),
            false_alarm=int(out.resolution.false_alarm.sum()),
            C2=out.resolution.c2,
            k_decoded=out.k_decoded,
            k_alloc=out.k_alloc,
            k_served=out.k_served,
            msg2_wasted=float(out.k_alloc - out.k_served),
            msg1_success_lost_to_depletion=lost,
            depletion_by_stage=depletion,
            would_deplete_by_stage=would,
            interround_depletions=interround,
            reward=float(reward),
            components_s={
                "paging_s": tpg,
                "msg1_s": out.t_ei_start - out.t_msg1_start,
                "ei_s": out.t_msg2_start - out.t_ei_start,
                "msg2_s": out.t_msg3_start - out.t_msg2_start,
                "msg3_s": out.msg3_time_s,
            },
            energy_ledger_uj=ledger,
            n_done_total=self.n_done,
            fates={name: int((out.fate == i).sum()) for i, name in enumerate(Fate.NAMES)},
        )
        for k_, v in depletion.items():
            self.depletion_totals[k_] += v
        for k_, v in would.items():
            self.would_deplete_totals[k_] += v
        self.total_ao += L * s.F
        if self.keep_rounds:
            self.rounds.append(rec)
            if len(self.cbra_inspect) < INSPECT_MAX and (r < INSPECT_FIRST_ROUNDS or r % INSPECT_STRIDE == 0):
                res = out.resolution
                self.cbra_inspect.append(
                    {
                        "round": r,
                        "t_start_s": t0,
                        "t_end_s": t_end,
                        "L": L,
                        "F": s.F,
                        "occupancy": res.occupancy.tolist(),
                        "physical": res.physical.tolist(),
                        "observed": res.observed.tolist(),
                        "k_decoded": out.k_decoded,
                        "k_alloc": out.k_alloc,
                        "k_served": out.k_served,
                        "msg3_slots": out.msg3_time_s / t_msg3_s(s),
                        "components_s": rec.components_s,
                        "n_paged": rec.n_paged,
                        "n_participants": rec.n_participants,
                        "n_rejected": rec.n_rejected,
                        "identified": rec.S_total,
                        "periodic": self.protocol.periodic,
                    }
                )
        self.history.append(
            (t0, t_end, L, p, rec.S_total, rec.idle_obs, rec.collision_obs, rec.n_participants,
             rec.reward, rec.n_done_total, rec.C2, rec.k_decoded, rec.k_alloc)
        )
        self.r += 1
        self.t = t_end
        return rec

    def _maybe_snapshot(self, t: float, force: bool = False) -> None:
        iv = self.cfg.snapshot_interval_s
        if iv <= 0 or (t < self._next_snapshot_t and not force):
            return
        if self.snapshots and self.snapshots[-1]["time_s"] == round(t, 6):
            return
        state, energy = self.states_at(t)
        ids = self.snapshot_ids
        self.snapshots.append(
            {
                "time_s": round(t, 6),
                "state": [STATE_CODES.index(s) for s in state[ids]],
                "energy_uJ": np.round(np.nan_to_num(energy[ids] * 1e6, nan=-1.0), 3).tolist(),
                "n_done": self.n_done,
            }
        )
        self._next_snapshot_t = t + iv

    def finalize(self) -> None:
        self._maybe_snapshot(self.t, force=True)
        self.trace.finalize(self.t)

    def group_populations(self) -> dict[str, float] | None:
        if not self.protocol.periodic:
            return None
        return group_populations(self.group, self.N_g)
