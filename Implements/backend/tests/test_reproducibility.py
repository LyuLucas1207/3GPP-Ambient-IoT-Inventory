import numpy as np

from simulator.config import paper_device1_config
from simulator.scenario import Scenario
from simulator.simulation import run_strategy


def test_same_seed_same_metrics():
    cfg = paper_device1_config(
        num_devices=40,
        max_time_s=2.0,
        collect_snapshots=False,
        collect_paging_events=False,
        seed=7,
    )
    scenario = Scenario.generate(cfg)
    a = run_strategy(cfg, scenario, "em", rng=np.random.default_rng(11))
    b = run_strategy(cfg, scenario, "em", rng=np.random.default_rng(11))
    assert a.metrics["n_inventoried"] == b.metrics["n_inventoried"]
    assert a.metrics["n_paging"] == b.metrics["n_paging"]
    assert a.n_msg1_attempts == b.n_msg1_attempts
    assert a.ratio_pct == b.ratio_pct
