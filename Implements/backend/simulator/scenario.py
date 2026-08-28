"""Common scenario: shared p_in, positions, and cycle-phase uniforms."""

from dataclasses import dataclass

import numpy as np

from simulator.channel import harvest_power_w, sample_pin_dbm, stratified_unit
from simulator.config import DONE, OFF, ON, SLEEP, SimConfig, is_dcm
from simulator.energy import recharge_time_s
from simulator.warmup import explicit_warmup, harvest_only_warmup, remaining_charge_stats


@dataclass
class Scenario:
    seed: int
    x_m: np.ndarray
    y_m: np.ndarray
    pin_dbm: np.ndarray
    peh_w: np.ndarray
    phase_u: np.ndarray

    @classmethod
    def generate(cls, cfg: SimConfig, rng: np.random.Generator | None = None) -> "Scenario":
        rng = rng or np.random.default_rng(cfg.seed)
        a = cfg.assumptions
        pin = sample_pin_dbm(
            cfg.num_devices,
            rng,
            sensitivity_dbm=a.pin_sensitivity_dbm,
            method=a.pin_sampling,
        )
        x = rng.uniform(0.0, a.factory_length_m, size=cfg.num_devices)
        y = rng.uniform(0.0, a.factory_width_m, size=cfg.num_devices)
        peh = np.asarray(harvest_power_w(pin), dtype=np.float64)
        if a.pin_sampling == "stratified":
            phase_u = stratified_unit(cfg.num_devices, rng)
        else:
            phase_u = rng.random(cfg.num_devices)
        return cls(
            seed=cfg.seed,
            x_m=x,
            y_m=y,
            pin_dbm=pin,
            peh_w=peh,
            phase_u=phase_u,
        )

    def static_devices(self) -> list[dict]:
        peh_nw = self.peh_w * 1e9
        out = []
        for i in range(self.x_m.size):
            out.append(
                {
                    "id": i,
                    "x": float(self.x_m[i]),
                    "y": float(self.y_m[i]),
                    "pin_dbm": float(self.pin_dbm[i]),
                    "harvest_power_nw": float(peh_nw[i]),
                }
            )
        return out


def stationary_em_state(cfg: SimConfig, peh_w: np.ndarray, phase_u: np.ndarray):
    """Place each EM device on its ON/OFF harvesting cycle."""
    d = cfg.device
    n = peh_w.size
    energy = np.empty(n, dtype=np.float64)
    state = np.empty(n, dtype=np.int8)
    delta = d.e_up_j - d.e_low_j
    t_on = delta / d.p_rx_w
    t_off = np.array([recharge_time_s(delta, p) for p in peh_w], dtype=np.float64)
    period = t_on + t_off
    tau = phase_u * period
    charging = tau <= t_off
    state[charging] = OFF
    energy[charging] = d.e_low_j + peh_w[charging] * tau[charging]
    state[~charging] = ON
    energy[~charging] = d.e_up_j - d.p_rx_w * (tau[~charging] - t_off[~charging])
    np.clip(energy, 0.0, d.e_max_j, out=energy)
    return energy, state


def stationary_dcm_preinventory_state(cfg: SimConfig, peh_w: np.ndarray, phase_u: np.ndarray):
    """DCM before first paging: ON for T_on_timer, then OFF until E_up."""
    d = cfg.device
    n = peh_w.size
    energy = np.empty(n, dtype=np.float64)
    state = np.empty(n, dtype=np.int8)
    on_remaining = np.zeros(n, dtype=np.int32)
    drain = d.p_rx_w * d.t_on_timer_s
    t_off = np.array([recharge_time_s(drain, p) for p in peh_w], dtype=np.float64)
    period = d.t_on_timer_s + t_off
    tau = phase_u * period
    on_mask = tau < d.t_on_timer_s
    state[on_mask] = ON
    t_in_on = tau[on_mask]
    energy[on_mask] = d.e_up_j - d.p_rx_w * t_in_on
    remain_s = d.t_on_timer_s - t_in_on
    on_remaining[on_mask] = np.maximum(1, np.round(remain_s / cfg.dt_s).astype(np.int32))
    off_mask = ~on_mask
    state[off_mask] = OFF
    t_in_off = tau[off_mask] - d.t_on_timer_s
    e_after_on = d.e_up_j - drain
    energy[off_mask] = e_after_on + peh_w[off_mask] * t_in_off
    np.clip(energy, 0.0, d.e_max_j, out=energy)
    return energy, state, on_remaining


def initial_arrays(cfg: SimConfig, scenario: Scenario, strategy: str):
    mode = cfg.assumptions.warmup_mode
    if mode == "harvest_only":
        energy, state, on_remaining = harvest_only_warmup(cfg, scenario.peh_w)
    elif mode == "explicit":
        energy, state, on_remaining = explicit_warmup(cfg, scenario.peh_w, strategy)
    elif is_dcm(strategy):
        energy, state, on_remaining = stationary_dcm_preinventory_state(
            cfg, scenario.peh_w, scenario.phase_u
        )
    else:
        energy, state = stationary_em_state(cfg, scenario.peh_w, scenario.phase_u)
        on_remaining = np.zeros(cfg.num_devices, dtype=np.int32)
        mode = "stationary"
    stats = remaining_charge_stats(energy, state, scenario.peh_w, cfg)
    stats["warmup_mode"] = mode
    stats["warmup_s"] = float(cfg.assumptions.warmup_s)
    return energy, state, on_remaining, stats
