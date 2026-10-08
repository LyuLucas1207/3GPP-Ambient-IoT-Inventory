import math

import numpy as np
import pytest

from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.controllers import CMEBEController, DFSASchouteController, PFSAPZEController, make_controller
from app.aperiodic_simulator.controllers.cmebe import cmebe_estimate
from app.aperiodic_simulator.controllers.dfsa_schoute import SCHOUTE_COLLISION_FACTOR, schoute_backlog
from app.aperiodic_simulator.core.runner import run_episode
from app.aperiodic_simulator.core.states import ControllerName, HarvestingScenario


def obs(L, I, C, S=0, p=1.0, F=8):
    return {"S1": S, "S2a": 0, "S2b": 0, "I": I, "C": C, "L": L, "p": p, "decoded": L * F - I - C}


def test_schoute_factor():
    assert SCHOUTE_COLLISION_FACTOR == pytest.approx(2.3922, abs=1e-4)
    assert schoute_backlog(10) == pytest.approx(23.922, abs=1e-3)


def test_schoute_frame_rule_and_p_fixed():
    c = DFSASchouteController(F=8, L_max=83, p_floor=0.001)
    a = c.reset(1, 0.3)
    assert (a.L, a.p) == (1, 1.0)
    a = c.update(obs(L=1, I=0, C=8))  # 8 collided AOs -> backlog 19.1 -> L = ceil(19.1/8) = 3
    assert a.L == 3 and a.p == 1.0
    a = c.update(obs(L=3, I=24, C=0))
    assert a.L == 1
    a = c.update(obs(L=83, I=0, C=664))
    assert a.L == 83  # capped at L_max


def _simulate_frame(n, N, alpha, rng):
    occ = np.bincount(rng.integers(0, N, n), minlength=N)
    e = int((occ == 0).sum())
    single = int((occ == 1).sum())
    coll = occ >= 2
    captured = int((rng.random(N) < alpha)[coll].sum())
    return e, single + captured, int(coll.sum()) - captured


@pytest.mark.parametrize("n,N,alpha", [(200, 128, 0.0), (300, 160, 0.3), (60, 64, 0.2)])
def test_cmebe_recovers_population_and_capture(n, N, alpha):
    rng = np.random.default_rng(1)
    est_n, est_a = [], []
    for _ in range(200):
        e, s, c = _simulate_frame(n, N, alpha, rng)
        nh, ah = cmebe_estimate(e, s, c, N, n_upper=10 * N)
        est_n.append(nh)
        est_a.append(ah)
    assert np.mean(est_n) == pytest.approx(n, rel=0.08)
    assert np.mean(est_a) == pytest.approx(alpha, abs=0.08)


def test_cmebe_no_collision_and_frame_rule():
    n, a = cmebe_estimate(e=5, s=3, c=0, N=8, n_upper=100)
    assert (n, a) == (3.0, 0.0)
    c = CMEBEController(F=8, L_max=83, p_floor=0.001)
    c.reset(1, 1.0)
    act = c.update(obs(L=4, I=10, C=12, S=8))
    n_hat, alpha, backlog = act.info["n_hat"], act.info["alpha_hat"], act.info["backlog_hat"]
    assert backlog == pytest.approx(n_hat - 8)
    assert act.L == min(83, max(1, math.ceil((1 - alpha) * backlog / 8)))
    assert act.p == 1.0


def test_make_controller_registry_returns_distinct_classes():
    assert isinstance(make_controller("pfsa_pze", 8, 83, 0.001), PFSAPZEController)
    assert isinstance(make_controller("dfsa_schoute", 8, 83, 0.001), DFSASchouteController)
    assert isinstance(make_controller("cmebe", 8, 83, 0.001), CMEBEController)
    with pytest.raises(ValueError):
        make_controller("recurrent_ppo", 8, 83, 0.001)


@pytest.mark.parametrize("name", [ControllerName.DFSA_SCHOUTE, ControllerName.CMEBE])
def test_dfsa_baselines_grow_L_and_identify(name):
    cfg = EpisodeConfig(
        n_tot=1500, seed=4, harvesting_scenario=HarvestingScenario.MULTI_SOURCE, controller=name, L_initial=1, t_max_s=600.0
    )
    res = run_episode(cfg)
    Ls = [h["L"] for h in res.controller_history]
    assert Ls[0] == 1 and max(Ls) > 4
    assert all(h["p"] == 1.0 for h in res.controller_history)
    assert res.metrics["final_ratio"] > 0.95
