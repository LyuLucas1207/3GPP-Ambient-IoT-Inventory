import math

from app.thesis_simulator import physics
from app.thesis_simulator.catalog import derive_reader_ranges, device_params_defaults


def test_r2d_matches_r2d_horizontal_radius_formula():
    # EIRP 39 dBm, MPL = 39 - 0.9 - 7 - threshold, bisection on PL_NLOS.
    assert math.isclose(physics.range_from_sensitivity_m(-36.0), 36.588, abs_tol=0.01)
    assert math.isclose(physics.range_from_sensitivity_m(-40.0), 56.215, abs_tol=0.01)
    assert physics.range_from_sensitivity_m(-70.0) > 1000


def test_d2r_backscatter_is_tighter_than_r2d_for_dev1():
    # Dev 1: Gbs = -6+0 = -6, P_req = 33 - 140 + 0.5 = -106.5
    # D2R MPL = 0.5 * (33 + (-6) - 7 - (-106.5)) = 63.25 dB -> ~24m horizontal
    d2r = physics.d2r_backscatter_range_m(backscatter_loss_db=6.0, backscatter_gain_db=0.0)
    assert math.isclose(d2r, 23.92, abs_tol=0.05)


def test_d2r_backscatter_benefits_from_amplification_for_dev2a():
    # Dev 2a: Gbs = -6+10 = +4
    d2r = physics.d2r_backscatter_range_m(backscatter_loss_db=6.0, backscatter_gain_db=10.0)
    assert math.isclose(d2r, 41.43, abs_tol=0.05)


def test_d2r_active_for_dev2b():
    # P_tx = -20 dBm, MPL = -20 - 7 - (-106.5) = 79.5 dB
    d2r = physics.d2r_active_range_m(active_tx_power_dbm=-20.0)
    assert math.isclose(d2r, 136.71, abs_tol=0.1)


def test_effective_coverage_takes_min_of_r2d_and_d2r():
    rf = {"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9}
    params = device_params_defaults()
    assert math.isclose(physics.effective_coverage_m(params["1"], rf), 23.92, abs_tol=0.05)
    assert math.isclose(physics.effective_coverage_m(params["2a"], rf), 41.43, abs_tol=0.05)
    assert math.isclose(physics.effective_coverage_m(params["2b"], rf), 136.71, abs_tol=0.1)


def test_derive_reader_ranges_uses_effective_coverage():
    out = derive_reader_ranges({"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9})
    assert set(out) == {"1", "2a", "2b"}
    # Values must match effective_coverage (not raw R2D).
    assert out["1"] < 36.0  # less than R2D of 36.59
    assert out["2b"] < 200  # way less than R2D of 1326


def test_tighter_sensitivity_still_capped_by_d2r_for_dev1():
    # Even if we tighten Dev 1 sensitivity, D2R backscatter stays ~24 m.
    out = derive_reader_ranges(
        {"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9},
        device_sensitivities={"1": -50.0},
    )
    assert math.isclose(out["1"], 23.92, abs_tol=0.05)


def test_extra_attenuation_shrinks_effective_range():
    rf = {"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 10.0, "carrier_ghz": 0.9}
    out = derive_reader_ranges(rf)
    base = derive_reader_ranges({"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9})
    for subtype in ("1", "2a", "2b"):
        assert out[subtype] < base[subtype]


def test_include_d2r_false_returns_r2d_only():
    rf = {"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9, "include_d2r": False}
    out = derive_reader_ranges(rf)
    # R2D-only numbers: Device 1 ~36.59, 2a ~56.22, 2b ~1326.
    assert math.isclose(out["1"], 36.588, abs_tol=0.05)
    assert math.isclose(out["2a"], 56.215, abs_tol=0.05)
    assert out["2b"] > 1000


def test_include_d2r_true_tighter_than_false_everywhere():
    rf_tight = {"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9, "include_d2r": True}
    rf_loose = dict(rf_tight, include_d2r=False)
    tight = derive_reader_ranges(rf_tight)
    loose = derive_reader_ranges(rf_loose)
    for subtype in ("1", "2a", "2b"):
        assert tight[subtype] <= loose[subtype]
