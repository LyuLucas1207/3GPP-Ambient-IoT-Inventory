"""Classify why a tail device finished late."""

from __future__ import annotations

from collections import Counter

import numpy as np

from simulator.config import STATE_NAME


def _sample_index(times: np.ndarray, t_s: float) -> int:
    if times.size == 0:
        return 0
    k = int(np.searchsorted(times, t_s, side="right") - 1)
    return int(np.clip(k, 0, times.size - 1))


def first_off_time_s(events: list[dict], transitions: list[dict]) -> float | None:
    lost = [float(e["time_s"]) for e in events if e.get("event") == "lost_sync"]
    if lost:
        return min(lost)
    offs = [
        float(tr["time_s"])
        for tr in transitions
        if tr.get("to") == "OFF" and tr.get("from") in ("ON", "SLEEP", "TX")
    ]
    if offs:
        return min(offs)
    return None


def remaining_census_at(res, scenario, t_s: float, p_sl_w: float = 0.1e-6) -> dict:
    """State of devices that are not yet inventoried at time t_s.

    DONE devices are excluded: they do not occupy later paging/CBRA.
    """
    n = scenario.pin_dbm.size
    completion = np.array(
        [np.nan if s["completion_time_s"] is None else s["completion_time_s"] for s in res.device_stats],
        dtype=np.float64,
    )
    remaining = [
        i
        for i in range(n)
        if (not np.isfinite(completion[i])) or (completion[i] > t_s + 1e-12)
    ]
    bank = res.trace_bank
    counts = {name: 0 for name in ("OFF", "ON", "SLEEP", "TX", "DONE")}
    n_synced = 0
    n_peh_lt_psl = 0
    n_repeat_collision = 0
    devices = []
    k = 0
    if bank is not None and bank.times_s.size:
        k = _sample_index(bank.times_s, t_s)
    for i in remaining:
        st = res.device_stats[i]
        events = list(bank.events[i]) if bank is not None else []
        trans = []
        name = "OFF"
        energy_nj = None
        if bank is not None and bank.times_s.size:
            trans = reconstruct_transitions(bank.state[i], bank.times_s)
            name = STATE_NAME.get(int(bank.state[i, k]), str(int(bank.state[i, k])))
            energy_nj = float(bank.energy_nj[i, k])
        counts[name] = counts.get(name, 0) + 1
        peh = float(scenario.peh_w[i])
        if peh < p_sl_w:
            n_peh_lt_psl += 1
        last_sync = st.get("last_sync_time_s")
        lost = int(st.get("lost_sync_count") or 0)
        if name == "OFF":
            synced = False
        elif last_sync is not None:
            lost_times = [float(e["time_s"]) for e in events if e.get("event") == "lost_sync"]
            last_lost = max(lost_times) if lost_times else None
            synced = last_lost is None or float(last_sync) > last_lost + 1e-12
        if synced:
            n_synced += 1
        attempts = int(st.get("attempts") or 0)
        collisions = int(st.get("collisions") or 0)
        if collisions >= 3:
            n_repeat_collision += 1
        devices.append({
            "device_id": i,
            "group_id": st.get("group"),
            "state": name,
            "energy_nj": energy_nj,
            "p_in_dbm": float(scenario.pin_dbm[i]),
            "P_eh_nw": peh * 1e9,
            "peh_below_psl": peh < p_sl_w,
            "synced_estimate": bool(synced),
            "last_sync_time_s": last_sync,
            "lost_sync_count": lost,
            "first_off_time_s": first_off_time_s(events, trans),
            "attempts": attempts,
            "collisions": collisions,
            "n_access_reject": st.get("n_access_reject"),
            "completion_time_s": st.get("completion_time_s"),
        })
    waiting_epoch = counts.get("SLEEP", 0)
    return {
        "t_s": float(t_s),
        "n_remaining": len(remaining),
        "n_done": n - len(remaining),
        "ratio_done_pct": 100.0 * (n - len(remaining)) / max(n, 1),
        "state_counts": counts,
        "n_synced_estimate": n_synced,
        "n_sleep_waiting_epoch": waiting_epoch,
        "n_peh_below_psl": n_peh_lt_psl,
        "n_repeat_collision_ge3": n_repeat_collision,
        "devices": devices,
    }


def reconstruct_transitions(state: np.ndarray, times: np.ndarray) -> list[dict]:
    out = []
    prev = int(state[0]) if state.size else None
    if prev is None:
        return out
    out.append({"event": "state", "time_s": float(times[0]), "state": STATE_NAME.get(prev, str(prev))})
    for i in range(1, state.size):
        cur = int(state[i])
        if cur != prev:
            out.append({
                "event": "state",
                "time_s": float(times[i]),
                "from": STATE_NAME.get(prev, str(prev)),
                "to": STATE_NAME.get(cur, str(cur)),
            })
            prev = cur
    return out


def classify_delay(
    stat: dict,
    pin_dbm: float,
    peh_w: float,
    events: list[dict],
    initial_energy_nj: float | None,
    e_low_nj: float = 250.0,
    e_up_nj: float = 500.0,
) -> dict:
    t_done = stat.get("completion_time_s")
    first_pg = stat.get("first_paging_time_s")
    lost = int(stat.get("lost_sync_count") or 0)
    attempts = int(stat.get("attempts") or 0)
    collisions = int(stat.get("collisions") or 0)
    rejects = int(stat.get("n_access_reject") or 0)
    eligible = int(stat.get("n_paging_eligible") or 0)
    t_charge = (e_up_nj - e_low_nj) * 1e-9 / max(peh_w, 1e-30)

    reasons: list[str] = []
    if first_pg is not None and first_pg > 8.0:
        reasons.append("late_first_paging")
    if lost >= 1:
        reasons.append("lost_sync_rejoin")
    if collisions >= 3 and attempts > 0 and collisions / max(attempts, 1) >= 0.5:
        reasons.append("congestion_collisions")
    if eligible >= 8 and attempts <= 2:
        reasons.append("low_access_probability")
    if initial_energy_nj is not None and initial_energy_nj <= e_low_nj + 15.0:
        if t_charge > 8.0:
            reasons.append("charging_from_elow_p1")
    if peh_w < 0.12e-6:
        reasons.append("sleep_net_drain")  # P_sl = 0.1 μW
    if not reasons:
        reasons.append("protocol_wait")

    primary = reasons[0]
    # Prefer the physically heaviest explanation for the 99% tail.
    for key in ("lost_sync_rejoin", "charging_from_elow_p1", "low_access_probability",
                "congestion_collisions", "late_first_paging", "sleep_net_drain"):
        if key in reasons:
            primary = key
            break

    event_counts = Counter(ev.get("event") for ev in events)
    return {
        "primary_delay": primary,
        "reasons": reasons,
        "pin_dbm": float(pin_dbm),
        "peh_nw": float(peh_w * 1e9),
        "elow_to_eup_charge_s": float(t_charge),
        "completion_time_s": t_done,
        "first_paging_time_s": first_pg,
        "lost_sync_count": lost,
        "attempts": attempts,
        "collisions": collisions,
        "n_paging_eligible": eligible,
        "n_access_reject": rejects,
        "event_counts": dict(event_counts),
        "why_late": _explain(primary, t_done, first_pg, t_charge, lost, attempts, eligible),
    }


def _explain(primary, t_done, first_pg, t_charge, lost, attempts, eligible) -> str:
    t = "?" if t_done is None else f"{t_done:.2f}s"
    if primary == "charging_from_elow_p1":
        return (
            f"Finished at {t}. Started near E_low; charging E_low→E_up takes "
            f"{t_charge:.1f}s at this P_eh (paper P1, ~20s at −36 dBm)."
        )
    if primary == "lost_sync_rejoin":
        return (
            f"Finished at {t} after {lost} lost-sync event(s). Hitting E_low "
            "clears DCM sync, so the device must recharge and detect paging again."
        )
    if primary == "low_access_probability":
        return (
            f"Finished at {t}. Eligible on {eligible} pagings but only {attempts} "
            "Msg1 attempts — p_access stayed too low for the remaining load."
        )
    if primary == "congestion_collisions":
        return f"Finished at {t} after repeated Msg1 collisions ({attempts} attempts)."
    if primary == "late_first_paging":
        return (
            f"Finished at {t}; first paging only at {first_pg:.2f}s "
            f"(still charging or off-cycle)."
        )
    if primary == "sleep_net_drain":
        return (
            f"Finished at {t}. P_eh < P_sl so SLEEP still drains; the device "
            "has a short ON budget before E_low."
        )
    return f"Finished at {t} after ordinary protocol waits."
