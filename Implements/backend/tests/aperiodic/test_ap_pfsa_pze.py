import math

import pytest

from app.aperiodic_simulator.controllers.grouped import GroupedController
from app.aperiodic_simulator.controllers.pfsa_pze import PFSAPZEController, pze_backlog_estimate, pze_next_p


@pytest.mark.parametrize("n,N,p", [(50, 128, 1.0), (500, 128, 0.3), (10, 8, 1.0)])
def test_pze_inverts_expected_idle_count(n, N, p):
    I = N * (1 - p / N) ** n
    assert pze_backlog_estimate(I, N, p) == pytest.approx(n, rel=1e-9)


def test_all_idle_fallback_p_one():
    p, n_hat = pze_next_p(I=128, S=0, N=128, p=0.01)
    assert p == 1.0 and n_hat == 0.0


def test_all_collided_uses_idle_floor():
    n_hat = pze_backlog_estimate(0, 8, 1.0, idle_floor=1.0)
    assert n_hat == pytest.approx(math.log(1 / 8) / math.log(1 - 1 / 8))


def test_p_bounds():
    for I in range(0, 129):
        for S in (0, 5, 50):
            p, _ = pze_next_p(I, S, 128, 0.5)
            assert 0 < p <= 1


def test_controller_keeps_L_fixed_and_clips():
    c = PFSAPZEController(F=8, L_max=83, p_floor=1e-4)
    a = c.reset(16, 1.0)
    assert (a.L, a.p) == (16, 1.0)
    a = c.update({"S1": 0, "S2a": 0, "S2b": 0, "I": 0, "C": 128, "L": 16, "p": 1.0, "decoded": 0})
    assert a.L == 16 and 1e-4 <= a.p < 1
    a = c.update({"S1": 0, "S2a": 0, "S2b": 0, "I": 128, "C": 0, "L": 16, "p": a.p, "decoded": 0})
    assert a.p == 1.0


def test_grouped_controller_keeps_state_per_group():
    g = GroupedController([PFSAPZEController(8, 83, 1e-4) for _ in range(2)])
    g.reset(1, 1.0)
    busy = {"S1": 0, "S2a": 0, "S2b": 0, "I": 0, "C": 8, "L": 1, "p": 1.0, "decoded": 0}
    idle = {"S1": 0, "S2a": 0, "S2b": 0, "I": 8, "C": 0, "L": 1, "p": 1.0, "decoded": 0}
    a1 = g.update(busy)  # round 0 (group 0) -> action for group 1
    assert a1.info["group"] == 1 and a1.p == 1.0
    a2 = g.update(idle)  # round 1 (group 1) -> action for group 0
    assert a2.info["group"] == 0 and a2.p < 1.0
