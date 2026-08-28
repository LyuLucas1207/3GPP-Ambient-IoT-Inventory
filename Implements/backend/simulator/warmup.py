"""Charging-stage warmup before Figure 5(b) t = 0.

`stationary`: closed-form ON/OFF (EM) or pre-inventory timer (DCM) phase.
`explicit`: the same energy machine for `warmup_s`, starting every device at
E_low / OFF (no reader paging). O(1) per device via cycle skipping.

These two are **not** equivalent: after a common 60 s charge from E_low, weak
devices sit mid-cycle with little remaining charge time, whereas a uniform
stationary phase can place ~1% of them near E_low (paper EM T99 ~ 20 s).
"""

from __future__ import annotations

import numpy as np

from simulator.config import OFF, ON, SimConfig, is_dcm


def time_until_on_s(
    energy: np.ndarray,
    state: np.ndarray,
    peh_w: np.ndarray,
    e_up_j: float,
    e_low_j: float,
    p_rx_w: float,
) -> np.ndarray:
    """Seconds until the device next reaches ON at E_up (EM-style cycle)."""
    out = np.zeros_like(energy, dtype=np.float64)
    off = state == OFF
    on = state == ON
    peh = np.maximum(peh_w, 1e-30)
    out[off] = (e_up_j - energy[off]) / peh[off]
    t_drain = np.maximum(energy[on] - e_low_j, 0.0) / p_rx_w
    t_chg = (e_up_j - e_low_j) / peh[on]
    out[on] = t_drain + t_chg
    return out


def remaining_charge_stats(energy, state, peh_w, cfg: SimConfig) -> dict:
    t = time_until_on_s(
        energy, state, peh_w, cfg.device.e_up_j, cfg.device.e_low_j, cfg.device.p_rx_w
    )
    t = t[np.isfinite(t)]
    if t.size == 0:
        return {"n_off": int(np.count_nonzero(state == OFF)), "n_on": int(np.count_nonzero(state == ON))}
    return {
        "n_off": int(np.count_nonzero(state == OFF)),
        "n_on": int(np.count_nonzero(state == ON)),
        "time_until_on_s_p90": float(np.percentile(t, 90)),
        "time_until_on_s_p95": float(np.percentile(t, 95)),
        "time_until_on_s_p99": float(np.percentile(t, 99)),
        "time_until_on_s_max": float(np.max(t)),
    }


def _advance_em_one(
    e: float,
    st: int,
    peh: float,
    duration: float,
    e_up: float,
    e_low: float,
    p_rx: float,
    e_max: float,
) -> tuple[float, int]:
    if duration <= 0:
        return e, st
    if peh <= 0:
        if st == ON:
            dt = min(duration, max(e - e_low, 0.0) / p_rx)
            e = max(e_low, e - p_rx * dt)
            return (e_low, OFF) if e <= e_low + 1e-18 else (e, ON)
        return e, OFF

    t_on = (e_up - e_low) / p_rx
    t_off = (e_up - e_low) / peh
    t = 0.0
    if st == OFF:
        need = max(e_up - e, 0.0) / peh
        if need >= duration:
            return min(e_max, e + peh * duration), OFF
        e = e_up
        t += need
        st = ON
    else:
        need = max(e - e_low, 0.0) / p_rx
        if need >= duration:
            return e - p_rx * duration, ON
        e = e_low
        t += need
        st = OFF

    remaining = duration - t
    period = t_on + t_off
    remaining -= period * (remaining // period)
    if st == ON:
        # At E_up after a completed OFF (or start-ON that finished drain+charge).
        if remaining <= t_on:
            return e_up - p_rx * remaining, ON
        return e_low + peh * (remaining - t_on), OFF
    if remaining <= t_off:
        return e_low + peh * remaining, OFF
    return e_up - p_rx * (remaining - t_off), ON


def _advance_dcm_one(
    e: float,
    st: int,
    on_rem_s: float,
    peh: float,
    duration: float,
    e_up: float,
    p_rx: float,
    t_on_timer: float,
    e_max: float,
) -> tuple[float, int, float]:
    """Pre-inventory: ON for T_on_timer from E_up, then OFF until E_up."""
    if duration <= 0:
        return e, st, on_rem_s
    drain = p_rx * t_on_timer
    t_off = drain / peh if peh > 0 else float("inf")

    t = 0.0
    if st == OFF:
        need = max(e_up - e, 0.0) / peh if peh > 0 else duration
        if need >= duration:
            return min(e_max, e + peh * duration), OFF, 0.0
        e = e_up
        t += need
        st = ON
        on_rem_s = t_on_timer
    elif st == ON:
        need = on_rem_s if on_rem_s > 0 else t_on_timer
        if need >= duration:
            return e - p_rx * duration, ON, need - duration
        e = e - p_rx * need
        t += need
        st = OFF
        on_rem_s = 0.0

    remaining = duration - t
    period = t_on_timer + t_off
    if np.isfinite(period) and period > 0:
        remaining -= period * (remaining // period)
    if st == ON:
        if remaining <= t_on_timer:
            return e_up - p_rx * remaining, ON, t_on_timer - remaining
        return (e_up - drain) + peh * (remaining - t_on_timer), OFF, 0.0
    if remaining <= t_off:
        return (e_up - drain) + peh * remaining, OFF, 0.0
    left = remaining - t_off
    return e_up - p_rx * left, ON, t_on_timer - left


def harvest_only_warmup(cfg: SimConfig, peh_w: np.ndarray):
    """Identical physical charge for every strategy: stay OFF, harvest warmup_s.

    Devices that reach E_up remain OFF until inventory t=0 (no monitoring
    during the charging stage). Used as a comparability experiment, not as
    the paper default: the paper's EM T99 ≈ 20 s needs some devices near
    E_low when inventory starts.
    """
    d = cfg.device
    duration = float(cfg.assumptions.warmup_s)
    energy = np.minimum(d.e_max_j, d.e_low_j + peh_w * duration)
    state = np.full(int(peh_w.size), OFF, dtype=np.int8)
    on_remaining = np.zeros(int(peh_w.size), dtype=np.int32)
    np.clip(energy, 0.0, d.e_max_j, out=energy)
    return energy, state, on_remaining


def explicit_warmup(cfg: SimConfig, peh_w: np.ndarray, strategy: str):
    """Start at E_low / OFF, run warmup_s of the energy machine, no paging."""
    d = cfg.device
    n = int(peh_w.size)
    duration = float(cfg.assumptions.warmup_s)
    energy = np.full(n, d.e_low_j, dtype=np.float64)
    state = np.full(n, OFF, dtype=np.int8)
    on_remaining = np.zeros(n, dtype=np.int32)
    peh = peh_w
    if is_dcm(strategy):
        on_rem_s = np.zeros(n, dtype=np.float64)
        for i in range(n):
            e, st, rem = _advance_dcm_one(
                float(energy[i]),
                int(state[i]),
                float(on_rem_s[i]),
                float(peh[i]),
                duration,
                d.e_up_j,
                d.p_rx_w,
                d.t_on_timer_s,
                d.e_max_j,
            )
            energy[i] = e
            state[i] = st
            on_remaining[i] = (
                max(1, int(round(rem / cfg.dt_s))) if st == ON and rem > 0 else 0
            )
    else:
        for i in range(n):
            e, st = _advance_em_one(
                float(energy[i]),
                int(state[i]),
                float(peh[i]),
                duration,
                d.e_up_j,
                d.e_low_j,
                d.p_rx_w,
                d.e_max_j,
            )
            energy[i] = e
            state[i] = st
    np.clip(energy, 0.0, d.e_max_j, out=energy)
    return energy, state, on_remaining
