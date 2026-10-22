"""Exact-analytical energy evolution (ported from
``Sources/.../grouping_logic.py`` _advance_availability lines 349-486)."""

from __future__ import annotations

import math

import numpy as np

from app.thesis_simulator import physics
from app.thesis_simulator.inventory.state import DeviceWorld, ReaderState


def advance_availability(dt: float, world: DeviceWorld, *, freeze: np.ndarray | None = None) -> None:
    """Vectorized version where Ecap/Eoff/P_on are per-device arrays."""
    if dt <= 0.0:
        return
    n = world.N
    if n == 0:
        return

    if freeze is None:
        freeze = np.zeros(n, dtype=bool)

    E = world.E
    on = world.on
    Ph = world.Ph_total
    P_on = world.P_on
    Ecap = world.Ecap
    Eoff = world.Eoff
    T_on_v = world.T_on_default  # updated to T_on_dcm when latched (see latch helper)

    # 1) Frozen population: only timer counts down
    if np.any(freeze):
        on[freeze] = np.maximum(0.0, on[freeze] - dt)

    active = ~freeze
    if not np.any(active):
        return

    dt_rem = np.zeros_like(E)
    dt_rem[active] = float(dt)

    # Phase A: devices currently ON consume energy
    on_now = active & (on > 0.0)
    if np.any(on_now):
        t_to_eoff = np.where(P_on > 0.0, np.maximum(0.0, (E - Eoff) / np.where(P_on > 0.0, P_on, 1.0)), np.inf)
        tA = np.minimum(dt_rem, np.minimum(on, t_to_eoff))
        tA = np.where(on_now, tA, 0.0)
        E -= P_on * tA
        on -= tA
        dt_rem -= tA
        turn_off = on_now & ((on <= 0.0) | (E <= Eoff))
        on[turn_off] = 0.0

    # Phase B: OFF devices harvest toward Ecap
    off_now = active & (on <= 0.0)
    if np.any(off_now):
        t_to_cap = np.where(Ph > 0.0, np.maximum(0.0, (Ecap - E) / np.where(Ph > 0.0, Ph, 1.0)), np.inf)
        tB = np.minimum(dt_rem, t_to_cap)
        tB = np.where(off_now, tB, 0.0)
        E += Ph * tB
        np.clip(E, 0.0, np.inf, out=E)
        np.minimum(E, Ecap, out=E)
        dt_rem -= tB

        hit_cap = off_now & (dt_rem > 1e-18) & np.isfinite(t_to_cap)
        if np.any(hit_cap):
            E[hit_cap] = Ecap[hit_cap]
            on[hit_cap] = T_on_v[hit_cap]

    # Phase C: collapse full ON->OFF->cap cycles with remaining dt
    cyc = active & (dt_rem > 1e-18) & (on > 0.0)
    if np.any(cyc):
        idx = np.where(cyc)[0]
        Ph_i = Ph[idx]
        Ton_i = T_on_v[idx]
        dt_i = dt_rem[idx]
        P_on_i = P_on[idx]
        Ecap_i = Ecap[idx]
        Eoff_i = Eoff[idx]

        dE_span = Ecap_i - Eoff_i
        t_on_energy = np.where(P_on_i > 0.0, dE_span / np.where(P_on_i > 0.0, P_on_i, 1.0), np.inf)
        t_on_full = np.minimum(Ton_i, t_on_energy)
        dE_full = P_on_i * t_on_full

        t_off_full = np.where(Ph_i > 0.0, dE_full / np.where(Ph_i > 0.0, Ph_i, 1.0), np.inf)
        period = t_on_full + t_off_full

        n_full = np.where(np.isfinite(period) & (period > 0.0), np.floor(dt_i / period).astype(np.int64), 0)
        used_full = n_full.astype(float) * period
        dt_i = dt_i - used_full

        E[idx] = Ecap_i
        on[idx] = Ton_i

        t1 = np.minimum(dt_i, t_on_full)
        E[idx] -= P_on_i * t1
        on[idx] -= t1
        dt_i = dt_i - t1

        if np.any(dt_i > 1e-18):
            t2_full = np.where(Ph_i > 0.0, dE_full / np.where(Ph_i > 0.0, Ph_i, 1.0), np.inf)
            t2 = np.minimum(dt_i, t2_full)
            E[idx] += Ph_i * t2
            np.minimum(E, Ecap, out=E)
            hit_exact = np.isfinite(t2_full) & (np.abs(t2 - t2_full) < 1e-12)
            on[idx] = np.where(hit_exact, Ton_i, on[idx])

    np.clip(E, 0.0, Ecap, out=E)
    on[on < 0.0] = 0.0


def init_stationary(world: DeviceWorld, rng: np.random.Generator) -> None:
    """Phase-randomized warm-up — ports ``harvest.py`` _init_stationary."""
    n = world.N
    if n == 0:
        return
    Ecap = world.Ecap
    Eoff = world.Eoff
    P_on = world.P_on
    Ph = world.Ph_total
    T_on_v = world.T_on_default

    dE_span = np.minimum(P_on * T_on_v, Ecap - Eoff)
    t_on = np.where(P_on > 0.0, dE_span / np.where(P_on > 0.0, P_on, 1.0), 0.0)
    t_off = np.where(Ph > 0.0, dE_span / np.where(Ph > 0.0, Ph, 1.0), np.inf)
    rho = np.where(Ph > 0.0, 1.0 / (1.0 + np.where(Ph > 0.0, P_on / np.where(Ph > 0.0, Ph, 1.0), 0.0)), 0.0)

    is_on = (rng.random(n) < rho) & (t_on > 0.0)

    tau_on = np.zeros(n)
    if np.any(is_on):
        tau_on[is_on] = rng.random(int(is_on.sum())) * t_on[is_on]

    world.E[is_on] = Ecap[is_on] - P_on[is_on] * tau_on[is_on]
    world.on[is_on] = t_on[is_on] - tau_on[is_on]

    is_off = ~is_on
    if np.any(is_off):
        deficit = np.zeros(n)
        cnt = int(is_off.sum())
        if cnt:
            deficit[is_off] = rng.random(cnt) * dE_span[is_off]
        world.E[is_off] = Ecap[is_off] - deficit[is_off]
        world.on[is_off] = 0.0

    np.clip(world.E, 0.0, Ecap, out=world.E)
    world.on[world.on < 0.0] = 0.0


def compute_reader_contribution(reader: ReaderState, world: DeviceWorld) -> np.ndarray:
    """Return per-device Pin (W) contributed by this reader."""
    rf = reader.rf
    tx = float(rf.get("tx_power_dbm", 33.0))
    gain = float(rf.get("antenna_gain_dbi", 6.0))
    extra = float(rf.get("extra_attenuation_db", 0.0))
    carrier = float(rf.get("carrier_ghz", 0.9))
    dx = world.x_m - reader.x_m
    dy = world.y_m - reader.y_m
    dz = physics.H_BS - physics.H_AIOT
    d3 = np.sqrt(dx * dx + dy * dy + dz * dz)
    pl = _pl_nlos_vector(d3, carrier)
    pin_dbm = tx + gain - pl - physics.FIXED_DEV_DB - physics.L_OBJ_DB - extra
    return _dbm_to_w_vector(pin_dbm)


def _pl_nlos_vector(d_m: np.ndarray, fc_ghz: float) -> np.ndarray:
    d = d_m + 1e-3
    pl_los = 31.84 + 21.5 * np.log10(d) + 19.0 * math.log10(fc_ghz)
    pl_plus = 33.63 + 21.9 * np.log10(d) + 20.0 * math.log10(fc_ghz)
    return np.maximum(pl_los, pl_plus)


def _dbm_to_w_vector(dbm: np.ndarray) -> np.ndarray:
    return 10.0 ** ((dbm - 30.0) / 10.0)
