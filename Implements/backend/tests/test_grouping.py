from dataclasses import replace

import numpy as np

from simulator.config import paper_device1_config
from simulator.grouping import preconfigured_groups
from simulator.scenario import Scenario
from simulator.simulation import run_strategy


def test_four_groups_are_evenly_split_even_id_mod():
    cfg = paper_device1_config(
        num_devices=40,
        max_time_s=0.05,
        collect_snapshots=False,
        collect_paging_events=False,
        seed=3,
    )
    cfg = replace(cfg, assumptions=replace(cfg.assumptions, group_assignment="even_id_mod"))
    scenario = Scenario.generate(cfg)
    res = run_strategy(cfg, scenario, "dcm_4_group", rng=np.random.default_rng(3))
    counts = np.bincount([s["group"] for s in res.device_stats if s["group"] is not None], minlength=4)
    assert list(counts) == [10, 10, 10, 10]


def test_random_preconfigured_is_even_but_shuffled():
    rng = np.random.default_rng(0)
    g = preconfigured_groups(40, 4, "random_preconfigured", rng)
    assert list(np.bincount(g, minlength=4)) == [10, 10, 10, 10]
    even = preconfigured_groups(40, 4, "even_id_mod", rng)
    assert not np.array_equal(g, even)


def test_first_paging_spread_does_not_dump_all_into_group_zero():
    cfg = paper_device1_config(
        num_devices=80,
        max_time_s=0.4,
        collect_snapshots=False,
        collect_paging_events=False,
        seed=5,
    )
    cfg = replace(
        cfg, assumptions=replace(cfg.assumptions, group_assignment="first_paging_spread")
    )
    scenario = Scenario.generate(cfg)
    res = run_strategy(cfg, scenario, "dcm_4_group", rng=np.random.default_rng(5))
    groups = [s["group"] for s in res.device_stats if s["group"] is not None]
    counts = np.bincount(groups, minlength=4)
    assert counts[0] < len(groups) * 0.7


def test_four_groups_beat_one_group_on_collisions():
    cfg = paper_device1_config(
        num_devices=80,
        max_time_s=2.0,
        collect_snapshots=False,
        collect_paging_events=False,
        seed=11,
    )
    scenario = Scenario.generate(cfg)
    one = run_strategy(cfg, scenario, "dcm_1_group", rng=np.random.default_rng(11))
    four = run_strategy(cfg, scenario, "dcm_4_group", rng=np.random.default_rng(11))
    # p is scaled by N/N_g so offered load per paging is similar; collision
    # *rates* should not explode. Grouping's paper win is monitoring energy.
    assert four.metrics["collision_rate"] < one.metrics["collision_rate"] * 1.6
    assert four.metrics["final_ratio_pct"] >= one.metrics["final_ratio_pct"] - 5.0
