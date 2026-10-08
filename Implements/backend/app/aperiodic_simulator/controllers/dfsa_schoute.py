"""DFSA with Schoute's backlog estimator (Figure 7 baseline).

F. Schoute, "Dynamic frame length ALOHA", IEEE Trans. Commun. 31(4), 1983.

Schoute shows that, when the frame length equals the number of contenders
(load 1), the number of contenders that collided in a slot is Poisson with
mean 1 conditioned on >= 2, whose mean is

    E[k | k >= 2] = (1 - e^-1) / (1 - 2 e^-1) = 2.3922

so the backlog left after a frame with C collided slots is

    B_hat = 2.39 * C

and the next frame length is set equal to B_hat (Schoute, Sec. III).

Mapping to the A-IoT round (paper Sec. V-C): a "slot" is an AO, a frame has
N = L*F AOs and F is fixed, so the controller sets L = ceil(B_hat / F),
clipped to [1, L_max]. Per the paper, DFSA adapts the access resources only
and does not control the access probability: p = 1 every round. Only the
observed collision count C is used; idle/success counts are not needed.
"""

import math

from app.aperiodic_simulator.controllers.base import Action, Controller

SCHOUTE_COLLISION_FACTOR = (1.0 - math.exp(-1.0)) / (1.0 - 2.0 * math.exp(-1.0))  # 2.3922


def schoute_backlog(C: float) -> float:
    return SCHOUTE_COLLISION_FACTOR * float(C)


class DFSASchouteController(Controller):
    name = "dfsa_schoute"
    adapts_L = True
    adapts_p = False

    def __init__(self, F: int, L_max: int, p_floor: float):
        super().__init__(F, L_max, p_floor)
        self.L = 1

    def reset(self, L0: int, p0: float) -> Action:
        self.L, _ = self.clip(L0, 1.0)
        return Action(self.L, 1.0, {"backlog_hat": None})

    def update(self, obs: dict) -> Action:
        backlog = schoute_backlog(obs["C"])
        self.L, _ = self.clip(math.ceil(backlog / self.F), 1.0)
        return Action(self.L, 1.0, {"backlog_hat": backlog})
