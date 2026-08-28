from dataclasses import replace

import numpy as np

from simulator.config import OFF, paper_device1_config
from simulator.scenario import Scenario, initial_arrays, stationary_em_state
from simulator.warmup import _advance_em_one, explicit_warmup, remaining_charge_stats


def test_explicit_em_matches_closed_form_partial_charge():
    cfg = paper_device1_config()
    d = cfg.device
    peh = 50e-9
    duration = 1.0
    e, st = _advance_em_one(d.e_low_j, OFF, peh, duration, d.e_up_j, d.e_low_j, d.p_rx_w, d.e_max_j)
    assert st == OFF
    assert abs(e - (d.e_low_j + peh * duration)) < 1e-15


def test_explicit_warmup_is_wired_from_config():
    cfg = paper_device1_config(num_devices=8, seed=1)
    cfg = replace(cfg, assumptions=replace(cfg.assumptions, warmup_mode="explicit", warmup_s=2.0))
    sc = Scenario.generate(cfg)
    e_stat, _s_stat = stationary_em_state(cfg, sc.peh_w, sc.phase_u)
    e_exp, s_exp, _ = explicit_warmup(cfg, sc.peh_w, "em")
    # Common start from E_low is not the uniform stationary phase.
    assert not np.allclose(e_stat, e_exp)
    energy, state, _, stats = initial_arrays(cfg, sc, "em")
    assert stats["warmup_mode"] == "explicit"
    assert np.allclose(energy, e_exp)
    assert np.array_equal(state, s_exp)


def test_stationary_independent_phase_can_place_devices_near_elow():
    """Paper EM T99 ~ 20 s needs some devices near E_low at inventory t=0."""
    cfg = paper_device1_config(num_devices=600, seed=42)
    sc = Scenario.generate(cfg)
    e_s, s_s = stationary_em_state(cfg, sc.peh_w, sc.phase_u)
    st = remaining_charge_stats(e_s, s_s, sc.peh_w, cfg)
    assert st["time_until_on_s_p99"] > 12.0
    assert st["time_until_on_s_max"] > 15.0
