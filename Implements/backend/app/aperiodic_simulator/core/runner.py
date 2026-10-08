"""Episode driver: controller <-> engine loop (one iteration = one CBRA round)."""

from dataclasses import dataclass

from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.controllers.base import Controller
from app.aperiodic_simulator.controllers.factory import make_controller
from app.aperiodic_simulator.controllers.grouped import GroupedController
from app.aperiodic_simulator.physics.energy import compute_global_lmax
from app.aperiodic_simulator.physics.harvesting import Population
from app.aperiodic_simulator.analysis.metrics import episode_metrics
from app.aperiodic_simulator.core.simulation import Episode
from app.aperiodic_simulator.core.states import PagingMode


@dataclass
class EpisodeResult:
    episode: Episode
    metrics: dict
    controller_history: list[dict]


def default_controller(cfg: EpisodeConfig) -> Controller:
    s = cfg.system

    def build() -> Controller:
        return make_controller(
            cfg.controller,
            s.F,
            compute_global_lmax(s),
            cfg.assumptions.p_floor,
            idle_floor=cfg.assumptions.pze_all_collided_idle_floor,
        )

    if PagingMode(cfg.paging_mode) == PagingMode.PERIODIC and cfg.N_g > 1:
        return GroupedController([build() for _ in range(cfg.N_g)])
    return build()


def run_episode(
    cfg: EpisodeConfig,
    controller: Controller | None = None,
    population: Population | None = None,
) -> EpisodeResult:
    l_max = compute_global_lmax(cfg.system)
    if cfg.L_fixed > l_max and not (controller and controller.adapts_L):
        raise ValueError(f"L_fixed={cfg.L_fixed} exceeds the energy-feasible Lmax={l_max}")
    ctrl = controller or default_controller(cfg)
    if PagingMode(cfg.paging_mode) == PagingMode.PERIODIC and ctrl.adapts_L:
        raise ValueError("the periodic baseline keeps L fixed")
    ep = Episode(cfg, population)
    L0 = cfg.L_initial if (ctrl.adapts_L and cfg.L_initial is not None) else cfg.L_fixed
    action = ctrl.reset(L0, cfg.p_initial)
    history: list[dict] = []
    while not ep.finished:
        rec = ep.step(action.L, action.p)
        history.append({"round": rec.index, "t_end_s": rec.t_end_s, "L": action.L, "p": action.p, **action.info})
        action = ctrl.update(rec.observation())
    ep.finalize()
    return EpisodeResult(ep, episode_metrics(ep), history)
