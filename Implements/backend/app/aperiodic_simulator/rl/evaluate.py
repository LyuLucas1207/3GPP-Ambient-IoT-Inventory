"""Evaluate a trained Recurrent PPO checkpoint with the same batch runner as every baseline."""

from app.aperiodic_simulator.core.batch import BatchResult, run_batch
from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.controllers.recurrent_ppo import ppo_controller_factory
from app.aperiodic_simulator.core.states import ControllerName, HarvestingScenario


def evaluate_ppo(
    alpha: float = 0.5,
    scenario: HarvestingScenario | str = HarvestingScenario.MULTI_SOURCE,
    n_tot: int = 15000,
    episodes: int = 10,
    base_seed: int = 0,
    L_initial: int = 1,
    workers: int | None = None,
    t_max_s: float = 1200.0,
) -> BatchResult:
    cfg = EpisodeConfig(
        n_tot=n_tot,
        harvesting_scenario=HarvestingScenario(scenario),
        controller=ControllerName.RECURRENT_PPO,
        L_initial=L_initial,
        L_fixed=L_initial,
        p_initial=1.0,
        alpha=alpha,
        t_max_s=t_max_s,
    )
    return run_batch(cfg, episodes, base_seed, label="recurrent_ppo", workers=workers, controller_factory=ppo_controller_factory(alpha))
