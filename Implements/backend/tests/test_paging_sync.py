from dataclasses import replace

import numpy as np

from simulator.channel import harvest_power_w
from simulator.config import paper_device1_config
from simulator.paging import is_periodic_epoch, next_periodic_epoch_slot
from simulator.scenario import Scenario
from simulator.simulation import run_strategy


def test_global_epoch_grid():
    assert is_periodic_epoch(0, 24)
    assert is_periodic_epoch(24, 24)
    assert not is_periodic_epoch(13, 24)
    assert next_periodic_epoch_slot(0, 24) == 24
    assert next_periodic_epoch_slot(12, 24) == 24
    assert next_periodic_epoch_slot(24, 24) == 48


def test_dcm4_wake_period_is_48ms():
    cfg = paper_device1_config(
        num_devices=4,
        max_time_s=0.12,
        collect_snapshots=False,
        collect_paging_events=True,
        seed=0,
    )
    cfg = replace(
        cfg,
        assumptions=replace(cfg.assumptions, p_access_init=0.0, p_access_min=0.0),
    )
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -10.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    res = run_strategy(cfg, sc, "dcm_4_group", rng=np.random.default_rng(0))
    own = [ev["time_s"] for ev in res.paging_events if ev.get("group_index") == 0]
    assert len(own) >= 2
    gaps = np.diff(own)
    assert np.allclose(gaps, 0.048, atol=0.002)


def test_first_paging_time_not_overwritten_on_resync():
    cfg = paper_device1_config(
        num_devices=1,
        max_time_s=0.08,
        collect_snapshots=False,
        collect_paging_events=False,
        seed=1,
    )
    cfg = replace(
        cfg,
        assumptions=replace(
            cfg.assumptions,
            p_access_init=1.0,
            p_access_min=1.0,
            off_clears_inventory_sync=True,
            warmup_mode="stationary",
        ),
        device=replace(
            paper_device1_config().device,
            n_time_ao=1,
            n_freq_ao=1,
            e_low_j=499e-9,
        ),
    )
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -10.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    res = run_strategy(cfg, sc, "dcm_1_group", rng=np.random.default_rng(2))
    st = res.device_stats[0]
    if st["sync_count"] >= 2:
        assert st["first_paging_time_s"] is not None
        assert st["last_sync_time_s"] is not None
        assert st["last_sync_time_s"] >= st["first_paging_time_s"] - 1e-12
        assert abs(st["first_paging_time_s"] - 0.0) < 0.02


def test_keep_sync_reaches_done_after_recharge():
    cfg = paper_device1_config(
        num_devices=1,
        max_time_s=0.4,
        collect_snapshots=False,
        collect_paging_events=False,
        seed=3,
    )
    cfg = replace(
        cfg,
        assumptions=replace(
            cfg.assumptions,
            p_access_init=1.0,
            p_access_min=1.0,
            off_clears_inventory_sync=False,
        ),
    )
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -12.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    res = run_strategy(cfg, sc, "dcm_1_group", rng=np.random.default_rng(3))
    assert res.metrics["n_inventoried"] == 1
    st = res.device_stats[0]
    assert st["inventoried"]
    assert st["sync_count"] >= 1
