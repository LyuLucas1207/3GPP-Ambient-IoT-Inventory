import math

from app.thesis_simulator import physics
from app.thesis_simulator.catalog import derive_reader_ranges


def test_range_matches_r2d_horizontal_radius_formula():
    # EIRP 39 dBm, MPL = 39 - 0.9 - 7 - threshold, bisection on PL_NLOS.
    # Values verified against aiot_layout.r2d_horizontal_radius().
    assert math.isclose(physics.range_from_sensitivity_m(-36.0), 36.588, abs_tol=0.01)
    assert math.isclose(physics.range_from_sensitivity_m(-40.0), 56.215, abs_tol=0.01)
    assert physics.range_from_sensitivity_m(-70.0) > 1000


def test_catalog_derive_reader_ranges_matches_defaults():
    out = derive_reader_ranges({"tx_power_dbm": 33.0, "antenna_gain_dbi": 6.0, "extra_attenuation_db": 0.0, "carrier_ghz": 0.9})
    assert set(out) == {"1", "2a", "2b"}
    assert math.isclose(out["1"], 36.588, abs_tol=0.01)
    assert math.isclose(out["2a"], 56.215, abs_tol=0.01)
    assert out["2b"] > 1000


def test_higher_sensitivity_expands_range():
    base = physics.range_from_sensitivity_m(-36.0)
    tighter = physics.range_from_sensitivity_m(-50.0)
    assert tighter > base


def test_extra_attenuation_shrinks_range():
    base = physics.range_from_sensitivity_m(-36.0)
    loss = physics.range_from_sensitivity_m(-36.0, extra_atten_db=10.0)
    assert loss < base
