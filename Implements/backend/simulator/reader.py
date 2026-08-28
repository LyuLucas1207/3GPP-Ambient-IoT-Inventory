"""Reader-side inventory control (paging + access probability)."""

from dataclasses import dataclass, field

from simulator.access_control import AccessProbabilityController
from simulator.config import SimConfig


@dataclass
class Reader:
    p_access: float
    paging_index: int = 0
    controller: AccessProbabilityController | None = None
    controllers: list[AccessProbabilityController] = field(default_factory=list)
    p_history: list[tuple[float, float]] = field(default_factory=list)
    p_access_scope: str = "per_group"

    def note(self, time_s: float) -> None:
        self.p_history.append((time_s, self.p_access))

    def p_for_group(self, group_index: int | None) -> float:
        if self.p_access_scope == "per_group" and self.controllers:
            g = 0 if group_index is None else int(group_index) % len(self.controllers)
            return self.controllers[g].p
        if self.controller is not None:
            return self.controller.p
        return self.p_access

    def observe(
        self,
        idle_count: int,
        n_eligible: int | None = None,
        n_transmitted: int | None = None,
        singleton_ao_count: int | None = None,
        collision_ao_count: int | None = None,
        group_index: int | None = None,
    ) -> float:
        if self.p_access_scope == "per_group" and self.controllers:
            g = 0 if group_index is None else int(group_index) % len(self.controllers)
            ctrl = self.controllers[g]
        else:
            ctrl = self.controller
        if ctrl is None:
            return self.p_access
        self.p_access = ctrl.observe(
            idle_count,
            n_eligible=n_eligible,
            n_transmitted=n_transmitted,
            singleton_ao_count=singleton_ao_count,
            collision_ao_count=collision_ao_count,
        )
        # Keep .controller pointing at the last-updated unit for tests.
        self.controller = ctrl
        return self.p_access


def make_reader(cfg: SimConfig, n_load: int | None = None, n_groups: int = 1) -> Reader:
    """n_load: devices expected to contend per paging (N / N_groups for DCM)."""
    a = cfg.assumptions
    n_devices = cfg.num_devices if n_load is None else n_load
    n_g = max(1, int(n_groups))
    scope = str(getattr(a, "p_access_scope", "per_group"))
    if scope not in ("per_group", "global"):
        scope = "per_group"
    n_ctrl = n_g if scope == "per_group" else 1
    controllers = [
        AccessProbabilityController(
            n_ao=cfg.device.n_ao,
            n_devices=n_devices,
            p_init=a.p_access_init,
            p_min=a.p_access_min,
            smoothing=a.p_access_smoothing,
            target_attempts_per_ao=a.target_attempts_per_ao,
            mode=a.access_controller,
        )
        for _ in range(n_ctrl)
    ]
    return Reader(
        p_access=controllers[0].p,
        controller=controllers[0],
        controllers=controllers,
        p_access_scope=scope,
    )
