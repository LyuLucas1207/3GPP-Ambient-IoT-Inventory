"""Regression: shared common/ utilities reproduce pre-extraction legacy values."""

import numpy as np
import pytest

from app.common import metrics as cm
from app.common import rf
from app.simulator.physics import channel as legacy_channel
from app.simulator.analysis import metrics as legacy_metrics

PIN = np.array([-40, -36, -25.5, -10, -9.5, 0, 5.0])
# Values recorded from simulator/channel.py before the extraction.
GOLDEN_XI = [0.01, 0.05, 0.155, 0.31, 0.3, 0.11, 0.01]
GOLDEN_PEH = [
    1e-09,
    1.2559432157547912e-08,
    4.3684935434599055e-07,
    3.1e-05,
    3.366055362905889e-05,
    0.00011,
    3.1622776601683795e-05,
]


def test_dbm_watts_round_trip():
    x = np.linspace(-120, 40, 33)
    np.testing.assert_allclose(rf.watts_to_dbm(rf.dbm_to_watts(x)), x, atol=1e-12)
    assert rf.dbm_to_watts(30.0) == pytest.approx(1.0)
    assert rf.watts_to_dbm(1e-6) == pytest.approx(-30.0)


def test_rf_matches_pre_extraction_values():
    np.testing.assert_allclose(rf.conversion_efficiency(PIN), GOLDEN_XI, rtol=0, atol=1e-15)
    np.testing.assert_allclose(rf.harvest_power_w(PIN), GOLDEN_PEH, rtol=1e-14)
    assert rf.conversion_efficiency(-36.0) == pytest.approx(0.05)


def test_legacy_modules_reexport_common():
    assert legacy_channel.dbm_to_watts is rf.dbm_to_watts
    assert legacy_channel.watts_to_dbm is rf.watts_to_dbm
    assert legacy_channel.conversion_efficiency is rf.conversion_efficiency
    assert legacy_channel.harvest_power_w is rf.harvest_power_w
    assert legacy_metrics.inventory_curve is cm.inventory_curve
    assert legacy_metrics.first_time_at_or_above is cm.first_time_at_or_above
    assert legacy_metrics.mae_rmse is cm.mae_rmse


def test_metrics_match_pre_extraction_values():
    c = np.array([0.12, 0.5, np.inf, 1.7, 0.33, 2.9, np.nan, 0.05])
    t, r = cm.inventory_curve(c, 8, 3.0)
    assert r.sum() == pytest.approx(3162.5)
    assert r[-1] == pytest.approx(75.0)
    assert cm.first_time_at_or_above(t, r, 50.0) == pytest.approx(0.5)
    assert cm.first_time_at_or_above(t, r, 90.0) is None
    err = cm.mae_rmse(t, r, np.array([0, 1, 2, 3.0]), np.array([0, 40, 60, 80.0]))
    assert err["mae"] == pytest.approx(9.565573770491802, rel=1e-14)
    assert err["rmse"] == pytest.approx(12.265004193592942, rel=1e-14)
    s = legacy_metrics.summarize(c, 8, 3.0)
    assert s["t50_s"] == pytest.approx(0.5)
    assert s["n_inventoried"] == 6
