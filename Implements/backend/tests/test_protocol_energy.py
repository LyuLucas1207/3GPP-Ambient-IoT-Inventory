from dataclasses import replace

import numpy as np

from simulator.channel import harvest_power_w
from simulator.config import paper_device1_config
from simulator.scenario import Scenario
from simulator.simulation import run_strategy


def _one_device(strategy: str, p_access: float, max_time_s: float = 0.05):
    cfg = paper_device1_config(
        num_devices=1,
        max_time_s=max_time_s,
        collect_snapshots=False,
        collect_paging_events=False,
        seed=1,
    )
    cfg = replace(
        cfg,
        assumptions=replace(
            cfg.assumptions,
            p_access_init=p_access,
            p_access_min=p_access,
        ),
    )
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -10.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    res = run_strategy(cfg, sc, strategy, rng=np.random.default_rng(1))
    e = np.array(res.energy_traces["energy_nj"]["0"])
    return res, e


def test_dcm_listen_window_pays_full_ton():
    """p_access=0: still pay T_on_DCM * P_rx, not a single dt."""
    res, e = _one_device("dcm_1_group", p_access=0.0, max_time_s=0.03)
    drop = float(e[0] - np.min(e[:20]))
    expected = 1e-6 * 3e-3 * 1e9  # 3 nJ
    assert drop >= 0.85 * expected
    assert drop < 8.0
    assert res.metrics["n_msg1_attempts"] == 0


def test_successful_cbra_pays_absolute_rx_tx():
    """Device 1 P_tx=P_rx, so (P_tx-P_rx) extra would be ~0. Must still drain."""
    res, e = _one_device("dcm_1_group", p_access=1.0, max_time_s=0.05)
    drop = float(e[0] - np.min(e[:40]))
    assert drop >= 4.0
    assert res.metrics["n_inventoried"] == 1
    t_done = res.device_stats[0]["completion_time_s"]
    assert t_done is not None
    assert t_done >= 0.006
    names = [ev["event"] for ev in res.trace_bank.events[0]]
    if "done" in names and "msg3" in names:
        assert names.index("msg3") < names.index("done")
    if "msg3_start" in names and "msg3" in names:
        assert names.index("msg3_start") < names.index("msg3")
    assert abs(float(res.energy_traces["dt_s"]) - 0.5e-3) < 1e-12


def test_collision_does_not_mark_done():
    cfg = paper_device1_config(
        num_devices=2,
        max_time_s=0.02,
        collect_snapshots=False,
        collect_paging_events=True,
        seed=0,
    )
    cfg = replace(
        cfg,
        assumptions=replace(cfg.assumptions, p_access_init=1.0, p_access_min=1.0),
        device=replace(cfg.device, n_time_ao=1, n_freq_ao=1),
    )
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -10.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    res = run_strategy(cfg, sc, "em", rng=np.random.default_rng(0))
    ev0 = res.paging_events[0]
    if ev0["n_collision"] > 0:
        assert ev0["n_success"] == 0
        assert res.metrics["n_inventoried"] == 0 or res.device_stats[0]["completion_time_s"] != ev0["time_s"]
