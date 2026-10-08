"""Step-by-step sessions for the "Step process" view of the aperiodic page.

A session keeps one small episode (all devices traced) in memory and advances
it one CBRA round per request with the same engine, controller and seed
semantics as ``/simulate``. Each response describes the round per device so
the UI can walk through paging -> access -> Msg1 -> EI -> Msg2 -> Msg3 ->
state transitions (paper Fig. 2/3).
"""

import threading
import time
import uuid

import numpy as np

from app.aperiodic_simulator.core.runner import default_controller
from app.aperiodic_simulator.core.simulation import Episode
from app.aperiodic_simulator.core.states import STAGES, Mode, RuntimeMode
from app.aperiodic_simulator.physics.device_types import TYPE_NAMES
from app.aperiodic_simulator.physics.energy import compute_global_lmax
from app.aperiodic_simulator.protocol.cbra import NO_STAGE, Fate

MAX_SESSIONS = 16
TTL_S = 30 * 60
MAX_SKIP_ROUNDS = 20000

_lock = threading.Lock()
_sessions: dict[str, "StepSession"] = {}


def _f(x) -> float | None:
    x = float(x)
    return x if np.isfinite(x) else None


def _uj(x) -> float | None:
    v = _f(x)
    return None if v is None else v * 1e6


class StepSession:
    def __init__(self, cfg, controller_factory=None):
        self.id = uuid.uuid4().hex[:12]
        self.touched = time.monotonic()
        self.lock = threading.Lock()
        self.cfg = cfg
        factory = controller_factory or default_controller
        self.ctrl = factory(cfg)
        l_max = compute_global_lmax(cfg.system)
        if cfg.L_fixed > l_max and not self.ctrl.adapts_L:
            raise ValueError(f"L_fixed={cfg.L_fixed} exceeds the energy-feasible Lmax={l_max}")
        self.ep = Episode(cfg)
        self.ep.capture_detail = True
        L0 = cfg.L_initial if (self.ctrl.adapts_L and cfg.L_initial is not None) else cfg.L_fixed
        self.action = self.ctrl.reset(L0, cfg.p_initial)

    # ------------------------------------------------------------------ info
    def devices_static(self) -> list[dict]:
        ep = self.ep
        return [
            {
                "id": i,
                "type": TYPE_NAMES[int(ep.type_idx[i])],
                "x": float(ep.xy[i, 0]),
                "y": float(ep.xy[i, 1]),
                "p_harv_uW": float(ep.p_harv[i] * 1e6),
                "E_up_uJ": float(ep.e_up[i] * 1e6),
                "E_low_uJ": float(ep.e_low[i] * 1e6),
                "P_mon_uW": float(ep.p_mon[i] * 1e6),
                "cycle_s": float(ep.cycle[i]),
            }
            for i in range(ep.n)
        ]

    def state_now(self) -> dict:
        ep = self.ep
        state, energy = ep.states_at(ep.t)
        return {
            "t_s": ep.t,
            "round": ep.r,
            "n_done": ep.n_done,
            "finished": ep.finished,
            "states": [str(s) for s in state],
            "energy_uJ": [_uj(e) for e in energy],
            "next_action": self._action_dict(self.action),
        }

    def info(self) -> dict:
        ep = self.ep
        pop = ep.population
        return {
            "session_id": self.id,
            "n_tot": pop.n_tot,
            "n_eff": ep.n,
            "F": ep.system.F,
            "N_g": ep.N_g,
            "periodic": ep.protocol.periodic,
            "controller": str(self.cfg.controller),
            "t_mon_s": ep.t_mon,
            "devices": self.devices_static(),
            "now": self.state_now(),
        }

    @staticmethod
    def _action_dict(a) -> dict:
        info = {k: v for k, v in a.info.items() if isinstance(v, (int, float, str, bool)) or v is None}
        return {"L": int(a.L), "p": float(a.p), "info": info}

    # ------------------------------------------------------------------ step
    def next(self, skip_empty: bool = True) -> dict:
        with self.lock:
            return self._next(skip_empty)

    def _next(self, skip_empty: bool) -> dict:
        ep = self.ep
        skipped, t_skip0 = 0, ep.t
        while True:
            if ep.finished:
                return {"finished": True, "skipped_rounds": skipped, "skipped_time_s": ep.t - t_skip0, "now": self.state_now()}
            t0 = ep.t
            state_b, energy_b = ep.states_at(t0)
            mode_b = ep.mode.copy()
            used = self.action
            rec = ep.step(used.L, used.p)
            self.action = self.ctrl.update(rec.observation())
            if not skip_empty or rec.n_paged > 0 or skipped >= MAX_SKIP_ROUNDS:
                break
            skipped += 1
        payload = self._round_payload(rec, used, state_b, energy_b, mode_b)
        payload.update(skipped_rounds=skipped, skipped_time_s=t0 - t_skip0, finished=ep.finished, now=self.state_now())
        return payload

    def _round_payload(self, rec, used, state_b, energy_b, mode_b) -> dict:
        ep, d = self.ep, self.ep.last_detail
        out, res = d["out"], d["out"].resolution
        F, n = ep.system.F, ep.n
        t0, t_end = rec.t_start_s, rec.t_end_s
        state_a, energy_a = ep.states_at(t_end)
        paged, part, rej = d["paged"], d["participants"], d["rejected"]

        via = {}
        dcm_set = set(int(i) for i in d["dcm_idx"])
        for i in d["cand"]:
            via[int(i)] = "monitor" if int(i) in dcm_set else "sync_wake"
        for i in d["resync"]:
            via[int(i)] = "resync"
        page_info = {}
        for j, i in enumerate(paged):
            page_info[int(i)] = (d["e_page_start"][j], d["e_page_end"][j], bool(d["page_depleted"][j]) and ep.cfg.enforce_midround_depletion)
        part_pos = {int(i): j for j, i in enumerate(part)}
        rej_set = set(int(i) for i in rej)
        phase = {int(i): float(p) for i, p in zip(d["dcm_idx"], d["dcm_phase_s"])}

        winner_dev = np.full(res.n_ao, -1, dtype=np.int64)
        has_w = res.winner >= 0
        winner_dev[has_w] = part[res.winner[has_w]]
        ao_devices: list[list[int]] = [[] for _ in range(res.n_ao)]
        for j, i in enumerate(part):
            ao_devices[int(out.ao[j])].append(int(i))

        devices = []
        for i in range(n):
            dev = {
                "id": i,
                "type": TYPE_NAMES[int(ep.type_idx[i])],
                "group": int(ep.group[i]) if ep.group[i] >= 0 else None,
                "before": {"state": str(state_b[i]), "E_uJ": _uj(energy_b[i]), "mode": int(mode_b[i])},
                "after": {"state": str(state_a[i]), "E_uJ": _uj(energy_a[i]), "mode": int(ep.mode[i])},
                "paged_via": via.get(i),
                "monitor_phase_s": phase.get(i),
                "page": None,
                "access": None,
                "ao": None,
                "msg2_index": None,
                "fate": None,
                "depleted_stage": None,
                "exit_time_s": None,
                "stage_energy_uJ": None,
                "segments": [],
            }
            if i in page_info:
                e0, e1, depl = page_info[i]
                dev["page"] = {"E_start_uJ": _uj(e0), "E_end_uJ": _uj(e1), "depleted": depl}
                if depl:
                    dev["fate"] = "depleted_paging"
                    dev["depleted_stage"] = "paging"
                dev["segments"] = self._segments(i, t0, t_end)
            if i in rej_set:
                dev["access"] = "reject"
                dev["fate"] = "rejected"
            if i in part_pos:
                j = part_pos[i]
                ao = int(out.ao[j])
                k = int(out.msg2_index[j])
                ds = int(out.depleted_stage[j])
                dev["access"] = "transmit"
                dev["ao"] = {
                    "index": ao,
                    "slot": ao // F,
                    "freq": ao % F,
                    "physical": int(res.physical[ao]),
                    "observed": int(res.observed[ao]),
                    "occupancy": int(res.occupancy[ao]),
                    "winner": bool(res.winner[ao] == j),
                }
                dev["msg2_index"] = k if k >= 0 else None
                dev["fate"] = Fate.NAMES[int(out.fate[j])]
                dev["depleted_stage"] = STAGES[ds].value if ds != NO_STAGE else None
                dev["exit_time_s"] = float(out.exit_time_s[j])
                dev["stage_energy_uJ"] = {s: float(v[j] * 1e6) for s, v in out.stage_energy_j.items()}
            devices.append(dev)

        k_slots = int(np.floor(out.k_alloc))
        decoded_aos = np.flatnonzero(res.winner >= 0)
        served = decoded_aos[: min(k_slots, decoded_aos.size)]
        msg2 = [
            {"index": m, "ao": int(a), "device": int(winner_dev[a]), "identified": bool(ep.mode[int(winner_dev[a])] == Mode.DONE)}
            for m, a in enumerate(served)
        ]
        msg3 = [{"index": m["index"], "slot": m["index"] // F, "freq": m["index"] % F, "device": m["device"], "identified": m["identified"]} for m in msg2]

        def count(pred) -> int:
            return sum(1 for x in devices if pred(x))

        transitions = {
            "to_done": count(lambda x: x["after"]["state"] == "DONE" and x["before"]["state"] != "DONE"),
            "to_off": count(lambda x: x["paged_via"] is not None and x["after"]["mode"] == int(Mode.DCM)),
            "to_sync": count(lambda x: x["paged_via"] is not None and x["after"]["mode"] == int(Mode.SYNC)),
        }
        return {
            "round": rec.index,
            "t_start_s": t0,
            "t_end_s": t_end,
            "L": rec.L,
            "p": rec.p,
            "F": F,
            "group": rec.group,
            "periodic": ep.protocol.periodic,
            "timeline": {
                "paging": [t0, out.t_msg1_start],
                "msg1": [out.t_msg1_start, out.t_ei_start],
                "ei": [out.t_ei_start, out.t_msg2_start],
                "msg2": [out.t_msg2_start, out.t_msg3_start],
                "msg3": [out.t_msg3_start, out.t_msg3_start + out.msg3_time_s],
                "end": t_end,
            },
            "components_s": rec.components_s,
            "counts": {
                "monitoring_before": int(sum(1 for s in state_b if str(s) == "MONITOR")),
                "paged": rec.n_paged,
                "paged_monitor": sum(1 for v in via.values() if v == "monitor"),
                "paged_sync_wake": sum(1 for v in via.values() if v == "sync_wake"),
                "paged_resync": sum(1 for v in via.values() if v == "resync"),
                "page_depleted": rec.depletion_by_stage.get("paging", 0),
                "rejected": rec.n_rejected,
                "participants": rec.n_participants,
                "idle_obs": rec.idle_obs,
                "success_obs": rec.success_obs,
                "collision_obs": rec.collision_obs,
                "physical": rec.physical,
                "missed": rec.missed,
                "false_alarm": rec.false_alarm,
                "k_decoded": rec.k_decoded,
                "k_alloc": rec.k_alloc,
                "k_served": rec.k_served,
                "identified": rec.S_total,
                "fates": rec.fates,
                "depletion_by_stage": rec.depletion_by_stage,
                **transitions,
            },
            "ao": {
                "occupancy": res.occupancy.tolist(),
                "physical": res.physical.tolist(),
                "observed": res.observed.tolist(),
                "winner_device": [int(w) for w in winner_dev],
                "devices": ao_devices,
                "missed": res.missed.tolist(),
                "false_alarm": res.false_alarm.tolist(),
            },
            "msg2": msg2,
            "msg3": msg3,
            "reward": rec.reward,
            "controller": {"used": self._action_dict(used), "next": self._action_dict(self.action)},
            "n_done": ep.n_done,
            "devices": devices,
        }

    def _segments(self, dev: int, t0: float, t_end: float) -> list[dict]:
        """This round's segments of one device plus the state it was in when the page started."""
        segs = self.ep.trace.segments.get(dev, [])
        out = []
        for s in reversed(segs):
            if s["t1"] <= t0 + 1e-9 and s["state"] != "DONE":
                out.append(dict(s))
                break
            if s["t0"] <= t_end + 1e-9:
                out.append(dict(s))
        out.reverse()
        return out


# ---------------------------------------------------------------------- store
def _evict(now: float) -> None:
    for sid in [k for k, s in _sessions.items() if now - s.touched > TTL_S]:
        del _sessions[sid]
    while len(_sessions) >= MAX_SESSIONS:
        oldest = min(_sessions, key=lambda k: _sessions[k].touched)
        del _sessions[oldest]


def create(cfg, controller_factory=None) -> StepSession:
    cfg = cfg.with_(
        runtime_mode=RuntimeMode.INTERACTIVE,
        n_trace_samples=0,
        trace_device_ids=tuple(range(cfg.n_tot)),
        snapshot_interval_s=0.0,
    )
    s = StepSession(cfg, controller_factory)
    with _lock:
        _evict(time.monotonic())
        _sessions[s.id] = s
    return s


def get(session_id: str) -> StepSession:
    with _lock:
        s = _sessions.get(session_id)
        if s is None:
            raise KeyError("step session not found (expired or unknown id)")
        s.touched = time.monotonic()
        return s


def delete(session_id: str) -> bool:
    with _lock:
        return _sessions.pop(session_id, None) is not None


def session_count() -> int:
    with _lock:
        return len(_sessions)


__all__ = ["StepSession", "create", "get", "delete", "session_count"]
