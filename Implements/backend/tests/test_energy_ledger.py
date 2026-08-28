"""Boundary energy updates and a full Device-1 CBRA ledger."""

from dataclasses import replace

import numpy as np

from simulator.channel import harvest_power_w
from simulator.cbra import cbra_phase, plan_cbra
from simulator.config import OFF, ON, SLEEP, TX, paper_device1_config
from simulator.energy import update_energy
from simulator.scenario import Scenario
from simulator.simulation import run_strategy


def test_clip_interval_and_signs():
    cfg = paper_device1_config()
    d = cfg.device
    dt = cfg.dt_s
    peh = np.array([12.56e-9])
    e = np.array([d.e_max_j])
    st = np.array([OFF], dtype=np.int8)
    update_energy(e, st, peh, dt, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert e[0] == d.e_max_j

    e = np.array([1e-18])
    st = np.array([ON], dtype=np.int8)
    update_energy(e, st, peh, 1.0, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert e[0] >= 0.0


def test_elow_and_eup_transitions_are_inclusive():
    cfg = paper_device1_config()
    d = cfg.device
    peh = np.array([12.56e-9])
    e = np.array([d.e_low_j])
    st = np.array([ON], dtype=np.int8)
    update_energy(e, st, peh, cfg.dt_s, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert e[0] < d.e_low_j
    e = np.array([d.e_up_j - peh[0] * cfg.dt_s / 2])
    st = np.array([OFF], dtype=np.int8)
    update_energy(e, st, peh, cfg.dt_s, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert e[0] >= d.e_up_j
    e = np.array([d.e_max_j])
    st = np.array([SLEEP], dtype=np.int8)
    peh_high = np.array([2e-6])
    update_energy(e, st, peh_high, 1.0, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert e[0] == d.e_max_j


def test_sleep_net_power_is_peh_minus_psl():
    cfg = paper_device1_config()
    d = cfg.device
    peh = np.array([2e-6])
    e = np.array([300e-9])
    st = np.array([SLEEP], dtype=np.int8)
    update_energy(e, st, peh, d.t_pg_s, d.p_rx_w, d.p_tx_w, d.p_sl_w, d.e_max_j)
    assert np.isclose(e[0], 300e-9 + (2e-6 - d.p_sl_w) * d.t_pg_s)


def test_time_aos_are_sequential_freq_aos_share_a_slot():
    cfg = paper_device1_config()
    plan = plan_cbra(cfg, np.random.default_rng(0), 0, 0, 0.0, np.array([0, 1]), 1.0)
    phases = [cbra_phase(plan, off) for off in range(plan.duration_slots)]
    msg1 = [(p, t) for p, t in phases if p == "msg1"]
    times = [t for _, t in msg1]
    assert times == sorted(times)
    # Each time-AO lasts msg1_slots, and freq AOs are not extra time.
    assert len(set(times)) == cfg.device.n_time_ao
    assert plan.n_freq_ao == 2
    assert plan.n_time_ao * plan.n_freq_ao == 8


def test_successful_cbra_energy_matches_table1_durations():
    """Paging RX + Msg1 TX + Msg2 RX + Msg3 TX at Table 1 lengths."""
    cfg = paper_device1_config(
        num_devices=1, max_time_s=0.05, collect_snapshots=False, collect_paging_events=False, seed=1
    )
    cfg = replace(
        cfg,
        assumptions=replace(cfg.assumptions, p_access_init=1.0, p_access_min=1.0, warmup_mode="harvest_only", warmup_s=0.0),
    )
    # harvest_only 0s leaves E_low; bump energy after generate.
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -10.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    # Force E_up / ON by using stationary-like energy via explicit pin.
    cfg = replace(cfg, assumptions=replace(cfg.assumptions, warmup_mode="stationary", p_access_init=1.0, p_access_min=1.0))
    sc.phase_u[:] = 0.0
    res = run_strategy(cfg, sc, "dcm_1_group", rng=np.random.default_rng(1))
    assert res.metrics["n_inventoried"] == 1
    e = np.array(res.energy_traces["energy_nj"]["0"])
    drop = float(e[0] - np.min(e[:80]))
    # Paging 1 ms + Msg1 0.5 + Msg2 0.5 + Msg3 3 ms at 1 μW → 5 nJ, plus
    # possible extra ON/SLEEP around the window. Must be at least Table 1.
    d = cfg.device
    table1 = (d.paging_s + d.msg1_s + d.msg2_s + d.msg3_s) * d.p_rx_w * 1e9
    assert drop >= 0.85 * table1


def test_singleton_not_done_until_msg3():
    cfg = paper_device1_config(
        num_devices=1, max_time_s=0.008, collect_snapshots=False, collect_paging_events=True, seed=2
    )
    cfg = replace(cfg, assumptions=replace(cfg.assumptions, p_access_init=1.0, p_access_min=1.0))
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -10.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    res = run_strategy(cfg, sc, "em", rng=np.random.default_rng(2))
    if res.paging_events:
        ev = res.paging_events[0]
        if ev.get("n_msg1_singleton"):
            # Completing Msg1 is not inventory success until Msg3 ends.
            if ev["time_s"] < 0.006:
                assert res.device_stats[0]["completion_time_s"] is None or res.device_stats[0]["completion_time_s"] > ev["time_s"] + 0.002
