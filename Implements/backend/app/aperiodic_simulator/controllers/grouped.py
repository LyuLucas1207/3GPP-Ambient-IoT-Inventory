"""Per-group controller state for the periodic baseline with N_g > 1.

With grouping, round r pages only group r mod N_g, so consecutive rounds see
unrelated backlogs. The reader knows which group it pages and keeps one
estimator state per group: the observation of round r updates group
r mod N_g, and the action of round r+1 is that group's current action.
"""

from app.aperiodic_simulator.controllers.base import Action, Controller


class GroupedController(Controller):
    def __init__(self, members: list[Controller]):
        first = members[0]
        super().__init__(first.F, first.L_max, first.p_floor)
        self.members = members
        self.name = first.name
        self.adapts_L = first.adapts_L
        self.n_groups = len(members)
        self.actions: list[Action] = []
        self.r = 0

    def reset(self, L0: int, p0: float) -> Action:
        self.actions = [m.reset(L0, p0) for m in self.members]
        self.r = 0
        return self._tagged(0)

    def update(self, obs: dict) -> Action:
        g = self.r % self.n_groups
        self.actions[g] = self.members[g].update(obs)
        self.r += 1
        return self._tagged(self.r % self.n_groups)

    def _tagged(self, g: int) -> Action:
        a = self.actions[g]
        return Action(a.L, a.p, {**a.info, "group": g})
