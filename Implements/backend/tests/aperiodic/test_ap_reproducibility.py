import numpy as np

from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.core.runner import run_episode
from app.aperiodic_simulator.core.simulation import Episode
from app.aperiodic_simulator.core.states import HarvestingScenario, PagingMode


def cfg(**kw):
    base = dict(n_tot=2000, seed=5, harvesting_scenario=HarvestingScenario.MULTI_SOURCE, t_max_s=120)
    base.update(kw)
    return EpisodeConfig(**base)


def test_same_seed_same_result():
    a = run_episode(cfg()).metrics
    b = run_episode(cfg()).metrics
    assert a == b


def test_compared_strategies_share_scenario_realization():
    a = Episode(cfg(paging_mode=PagingMode.APERIODIC))
    b = Episode(cfg(paging_mode=PagingMode.PERIODIC, N_g=4))
    np.testing.assert_array_equal(a.xy, b.xy)
    np.testing.assert_array_equal(a.type_idx, b.type_idx)
    np.testing.assert_array_equal(a.anchor, b.anchor)  # same initial availability
    np.testing.assert_array_equal(a.p_harv, b.p_harv)


def test_different_seed_differs():
    assert run_episode(cfg(seed=6)).metrics["T50"] != run_episode(cfg()).metrics["T50"]
