import math

import numpy as np

from simulator.channel import conversion_efficiency, dbm_to_watts, harvest_power_w, sample_pin_dbm
from simulator.config import paper_device1_config


def test_dbm_to_watts_minus_36():
    p = float(dbm_to_watts(-36.0))
    assert math.isclose(p, 2.51188643150958e-7, rel_tol=1e-6)
    assert math.isclose(p * 1e6, 0.251188643150958, rel_tol=1e-6)


def test_xi_minus_36_is_5_percent():
    assert math.isclose(float(conversion_efficiency(-36.0)), 0.05, abs_tol=1e-12)


def test_xi_breakpoint_continuous():
    lo = float(conversion_efficiency(-10.0))
    hi = float(conversion_efficiency(-9.999999))
    assert math.isclose(lo, 0.31, abs_tol=1e-9)
    assert hi < lo


def test_harvest_power_minus_36():
    peh = float(harvest_power_w(-36.0))
    assert math.isclose(peh, 12.5594321575479e-9, rel_tol=1e-6)


def test_recharge_time_sanity():
    peh = float(harvest_power_w(-36.0))
    t = 250e-9 / peh
    assert math.isclose(t, 19.9, rel_tol=0.02)


def test_pin_samples_respect_sensitivity():
    rng = np.random.default_rng(0)
    cfg = paper_device1_config()
    pin = sample_pin_dbm(200, rng, sensitivity_dbm=cfg.assumptions.pin_sensitivity_dbm)
    assert pin.min() >= -36.0 - 1e-9
    assert pin.max() <= -5.0


def test_fig5a_cdf_anchors():
    from simulator.channel import load_pin_cdf

    cdf, pin = load_pin_cdf()
    assert np.all(np.diff(cdf) >= -1e-12)
    assert np.all(np.diff(pin) >= -1e-12)
    f_m30 = float(np.interp(-30.0, pin, cdf))
    f_m35 = float(np.interp(-35.0, pin, cdf))
    assert abs(f_m30 - 0.5) <= 0.06
    assert 0.06 <= f_m35 <= 0.16


def test_fig5a_sampled_median():
    rng = np.random.default_rng(42)
    pin = sample_pin_dbm(20000, rng, method="iid")
    assert abs(float(np.median(pin)) - (-30.0)) < 1.0
    assert pin.min() >= -36.0 - 1e-9


def test_stratified_covers_cdf_tail():
    rng = np.random.default_rng(42)
    pin = sample_pin_dbm(600, rng, method="stratified")
    assert float(np.min(pin)) <= -35.4
    assert abs(float(np.median(pin)) - (-30.0)) < 0.8
    assert float(np.percentile(pin, 1)) <= -35.0
