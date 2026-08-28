from simulator.fig5b_validation import evaluate_fig5b, weakest_recharge_s
from simulator.channel import sample_pin_dbm
import numpy as np


class _Res:
    def __init__(self, t99, times, ratio):
        self.metrics = {"t99_s": t99}
        self.times_s = times
        self.ratio_pct = ratio


def test_validation_fails_when_four_group_is_slower():
    times = list(np.linspace(0, 20, 21))
    ratio = list(np.linspace(0, 100, 21))
    results = {
        "em": _Res(14.0, times, ratio),
        "dcm_1_group": _Res(16.0, times, ratio),
        "dcm_4_group": _Res(16.5, times, ratio),
    }
    pin = sample_pin_dbm(600, np.random.default_rng(42))
    val = evaluate_fig5b(results, pin)
    assert val["status"] == "FAIL"
    assert any(c["id"] == "t99_4_faster_than_em" and not c["ok"] for c in val["checks"])


def test_validation_passes_paper_direction():
    times = list(np.linspace(0, 25, 26))
    ratio = list(np.linspace(0, 100, 26))
    results = {
        "em": _Res(20.0, times, ratio),
        "dcm_1_group": _Res(19.5, times, ratio),
        "dcm_4_group": _Res(10.0, times, ratio),
    }
    pin = sample_pin_dbm(600, np.random.default_rng(42))
    val = evaluate_fig5b(results, pin)
    assert val["pass"]
    assert 0.4 <= val["reduction_4_vs_em"] <= 0.6


def test_validation_rejects_80pct_reduction_as_near_50():
    """Early-sleep ~80% T99 cut must not PASS as the paper's ~50%."""
    times = list(np.linspace(0, 25, 26))
    ratio = list(np.linspace(0, 100, 26))
    results = {
        "em": _Res(14.65, times, ratio),
        "dcm_1_group": _Res(12.95, times, ratio),
        "dcm_4_group": _Res(2.90, times, ratio),
    }
    pin = sample_pin_dbm(600, np.random.default_rng(42))
    val = evaluate_fig5b(results, pin)
    assert val["status"] == "FAIL"
    assert any(c["id"] == "t99_4_reduction_near_50pct" and not c["ok"] for c in val["checks"])
    assert any(c["id"] == "t99_4_near_paper_10s" and not c["ok"] for c in val["checks"])


def test_remaining_census_excludes_done():
    from dataclasses import replace

    from simulator.channel import harvest_power_w
    from simulator.config import paper_device1_config
    from simulator.scenario import Scenario
    from simulator.simulation import run_strategy
    from simulator.tail_diagnosis import remaining_census_at

    cfg = paper_device1_config(
        num_devices=6, max_time_s=0.08, collect_snapshots=False, collect_paging_events=False, seed=1
    )
    cfg = replace(cfg, assumptions=replace(cfg.assumptions, p_access_init=1.0, p_access_min=1.0))
    sc = Scenario.generate(cfg)
    sc.phase_u[:] = 0.0
    sc.pin_dbm[:] = -10.0
    sc.peh_w[:] = harvest_power_w(sc.pin_dbm)
    res = run_strategy(cfg, sc, "em", rng=np.random.default_rng(1))
    c0 = remaining_census_at(res, sc, 0.0)
    assert c0["n_remaining"] == 6
    assert c0["state_counts"]["DONE"] == 0
    c_end = remaining_census_at(res, sc, 0.08)
    assert c_end["n_remaining"] + c_end["n_done"] == 6
    assert c_end["state_counts"]["DONE"] == 0


def test_weakest_charge_near_20s():
    pin = sample_pin_dbm(600, np.random.default_rng(42))
    st = weakest_recharge_s(pin)
    assert st["close_to_20s"]
    assert 17.0 <= st["elow_to_eup_s_max"] <= 22.0
