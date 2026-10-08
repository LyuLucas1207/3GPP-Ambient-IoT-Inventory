import numpy as np
import pytest

from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.core.runner import run_episode
from app.aperiodic_simulator.core.simulation import Episode
from app.aperiodic_simulator.core.states import HarvestingScenario, Mode, PagingMode, RuntimeMode

MULTI = HarvestingScenario.MULTI_SOURCE
SINGLE = HarvestingScenario.SINGLE_SOURCE


def ep(mode=PagingMode.APERIODIC, n=600, scen=MULTI, **kw):
    return Episode(EpisodeConfig(n_tot=n, seed=11, harvesting_scenario=scen, paging_mode=mode, **kw))


def test_aperiodic_rejection_goes_off():
    e = ep()
    rec = e.step(4, 1e-4)
    assert rec.n_rejected > 0
    assert (e.mode != Mode.SYNC).all()
    off = e.mode == Mode.DCM
    # Rejected catchers must recharge first: their anchor lies after the page.
    assert (e.anchor[off] >= rec.t_start_s - e.cycle[off]).all()
    assert (e.anchor[off] > rec.t_start_s).sum() >= rec.n_rejected - 1


def test_aperiodic_success_done_and_failure_off_without_sync():
    e = ep(n=3000)
    for _ in range(30):
        rec = e.step(2, 1.0)
        assert (e.mode != Mode.SYNC).all()  # no cross-round synchronization
        assert rec.group is None
    assert e.n_done > 0
    assert np.isfinite(e.t_done[e.mode == Mode.DONE]).all()


def test_aperiodic_round_interval_is_round_driven():
    e = ep()
    rec = e.step(16, 1.0)
    assert rec.t_end_s - rec.t_start_s == pytest.approx(sum(rec.components_s.values()))
    assert e.step(16, 1.0).t_start_s == pytest.approx(rec.t_end_s)


def test_periodic_failure_keeps_synchronized_retry():
    e = ep(PagingMode.PERIODIC, n=3000)
    e.step(1, 1.0)
    sync = e.mode == Mode.SYNC
    assert sync.any()
    assert (e.wake_round[sync] == 1).all()  # N_g = 1: next paging opportunity
    assert (e.group[sync] == 0).all()


def test_periodic_first_catch_group_assignment():
    e = ep(PagingMode.PERIODIC, n=3000, scen=SINGLE, N_g=4)
    seen = set()
    for r in range(8):
        before = e.group.copy()
        e.step(1, 1.0)
        new = (before < 0) & (e.group >= 0)
        assert (e.group[new] == r % 4).all()
        seen.update(np.unique(e.group[new]).tolist())
    assert seen == {0, 1, 2, 3}
    sync = e.mode == Mode.SYNC
    assert (np.mod(e.wake_round[sync], 4) == e.group[sync]).all()


def test_periodic_depletion_goes_off_and_recharges():
    e = ep(PagingMode.PERIODIC, n=3000, scen=SINGLE)
    for _ in range(300):
        e.step(16, 1.0)
    assert sum(e.depletion_totals.values()) + e.interround_depletions > 0
    reacq = (e.group >= 0) & (e.mode == Mode.DCM)
    assert reacq.any()


@pytest.mark.parametrize("L", [1, 16, 83])
def test_aperiodic_has_zero_midround_depletion(L):
    r = run_episode(EpisodeConfig(n_tot=1500, seed=3, harvesting_scenario=SINGLE, L_fixed=L, t_max_s=200))
    assert r.metrics["depletion_total"] == 0


def test_L_above_lmax_rejected():
    with pytest.raises(ValueError):
        run_episode(EpisodeConfig(n_tot=100, L_fixed=84))


def test_periodic_L_must_stay_fixed():
    e = ep(PagingMode.PERIODIC)
    e.step(4, 1.0)
    with pytest.raises(ValueError):
        e.step(5, 1.0)


def test_interactive_snapshots_and_traces():
    cfg = EpisodeConfig(
        n_tot=300, seed=2, runtime_mode=RuntimeMode.INTERACTIVE, snapshot_interval_s=1.0, n_trace_samples=4, t_max_s=30
    )
    r = run_episode(cfg)
    e = r.episode
    assert len(e.rounds) == e.r
    times = [s["time_s"] for s in e.snapshots]
    assert times[0] == 0.0 and len(times) >= int(e.t)
    assert all(b - a >= 1.0 - 1e-9 for a, b in zip(times[:-1], times[1:-1]))
    assert times[-1] == pytest.approx(e.t, abs=1e-6)
    assert e.snapshots[-1]["n_done"] == e.n_done
    for dev in e.trace.ids:
        segs = e.trace.payload(dev)["segments"]
        timed = [s for s in segs if s["state"] != "DONE"]
        assert timed[0]["t0"] == 0.0
        for a, b in zip(timed, timed[1:]):
            assert b["t0"] == pytest.approx(a["t1"], abs=1e-9)
    stages = {s["stage"] for d in e.trace.ids for s in e.trace.payload(d)["segments"]}
    assert "EI" in stages or e.n_done == 0
