"""Reader-side inventory control (paging + access probability)."""

from dataclasses import dataclass, field

from simulator.access_control import AccessProbabilityController
from simulator.config import SimConfig


@dataclass
class Reader:
    p_access: float
    paging_index: int = 0
    controller: AccessProbabilityController | None = None
    p_history: list[tuple[float, float]] = field(default_factory=list)

    def note(self, time_s: float) -> None:
        self.p_history.append((time_s, self.p_access))


def make_reader(cfg: SimConfig, n_load: int | None = None) -> Reader:
    """n_load: devices expected to contend per paging (N / N_groups for DCM)."""
    ctrl = AccessProbabilityController(
        n_ao=cfg.device.n_ao,
        n_devices=cfg.num_devices if n_load is None else n_load,
        p_init=cfg.assumptions.p_access_init,
        p_min=cfg.assumptions.p_access_min,
        smoothing=cfg.assumptions.p_access_smoothing,
        target_attempts_per_ao=cfg.assumptions.target_attempts_per_ao,
        mode=cfg.assumptions.access_controller,
    )
    return Reader(p_access=ctrl.p, controller=ctrl)
