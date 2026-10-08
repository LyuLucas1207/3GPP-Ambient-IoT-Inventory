import numpy as np
import pytest

from app.aperiodic_simulator.physics.channel import inf_dh_path_loss_db
from app.aperiodic_simulator.core.config import SystemParams
from app.aperiodic_simulator.physics.harvesting import build_population, harvest_below_sleep_stats, incident_power_cdf
from app.aperiodic_simulator.physics.layout import bs_positions, central_bs_indices, reader_position
from app.aperiodic_simulator.core.states import HarvestingScenario


def pop(scen, seed=7, n=15000):
    return build_population(n, np.random.default_rng(seed), scen)


def test_layout_and_reader():
    bs = bs_positions()
    assert bs.shape == (18, 2)
    assert set(np.unique(bs[:, 0])) == {10, 30, 50, 70, 90, 110}
    assert set(np.unique(bs[:, 1])) == {10, 30, 50}
    assert 8 in central_bs_indices()
    assert reader_position().tolist() == [50.0, 30.0]


def test_inf_dh_is_max_of_los_and_dh():
    d = np.array([5.0, 20.0, 80.0])
    pl = inf_dh_path_loss_db(d, 0.9)
    los = 31.84 + 21.5 * np.log10(d) + 19.0 * np.log10(0.9)
    dh = 33.63 + 21.9 * np.log10(d) + 20.0 * np.log10(0.9)
    np.testing.assert_allclose(pl, np.maximum(los, dh))


def test_single_source_neff_and_shares():
    p = pop(HarvestingScenario.SINGLE_SOURCE)
    assert p.n_eff == pytest.approx(6440, rel=0.03)
    sh = p.type_shares()
    assert sh["1"] == pytest.approx(0.173, abs=0.015)
    assert sh["2a"] == pytest.approx(0.413, abs=0.015)
    assert sh["2b"] == pytest.approx(0.413, abs=0.015)
    # Single-source requires P_in >= -36 dBm from the reader.
    assert (p.pin_harvest_dbm[p.eligible] >= -36.0).all()


def test_multi_source_neff_and_shares():
    p = pop(HarvestingScenario.MULTI_SOURCE)
    assert p.n_eff == pytest.approx(9035, rel=0.03)
    sh = p.type_shares()
    assert sh["1"] == pytest.approx(0.123, abs=0.015)
    assert sh["2a"] == pytest.approx(0.323, abs=0.015)
    assert sh["2b"] == pytest.approx(0.553, abs=0.015)


def test_multi_source_harvests_at_least_single_source():
    a, b = pop(HarvestingScenario.SINGLE_SOURCE), pop(HarvestingScenario.MULTI_SOURCE)
    np.testing.assert_array_equal(a.xy, b.xy)  # same seed -> same placement
    assert (b.pin_harvest_dbm >= a.pin_harvest_dbm - 1e-9).all()
    assert (b.p_harv_w >= a.p_harv_w - 1e-15).all()


def test_harvest_below_sleep_share_single_source():
    st = harvest_below_sleep_stats(pop(HarvestingScenario.SINGLE_SOURCE), SystemParams().p_sl_w)
    assert st["share_of_n_eff"] == pytest.approx(0.619, abs=0.03)
    assert st["type2_share_of_below"] > 0.85


def test_cdf_monotone():
    c = incident_power_cdf(pop(HarvestingScenario.MULTI_SOURCE))
    assert np.all(np.diff(c["pin_dbm"]) >= 0)
    assert c["cdf"][0] == 0.0 and c["cdf"][-1] == 1.0


def test_same_seed_same_population():
    a, b = pop(HarvestingScenario.MULTI_SOURCE, 3), pop(HarvestingScenario.MULTI_SOURCE, 3)
    np.testing.assert_array_equal(a.xy, b.xy)
    np.testing.assert_array_equal(a.type_idx, b.type_idx)
    c = pop(HarvestingScenario.MULTI_SOURCE, 4)
    assert not np.array_equal(a.xy, c.xy)
