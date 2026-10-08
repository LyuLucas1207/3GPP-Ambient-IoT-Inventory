"""Recurrent PPO controller adapter (inference from a trained checkpoint).

Input: the Eq. (5) observation of the previous round (scaled by
``rl.transforms.normalize_observation``) and the LSTM state carried across
rounds. Output: physical (L_s, p_s) after the environment rules of Eqs. (6)-(7),
plus diagnostics (m, q). The hidden state resets in ``reset()`` (episode start).
"""

import numpy as np

from app.aperiodic_simulator.core.config import EpisodeConfig
from app.aperiodic_simulator.controllers.base import Action, Controller
from app.aperiodic_simulator.physics.energy import compute_global_lmax
from app.aperiodic_simulator.rl.checkpoint import checkpoint_path, load_meta
from app.aperiodic_simulator.rl.transforms import action_to_multipliers, apply_action, normalize_observation

_MODELS: dict[tuple[str, str], object] = {}


def _load_model(path: str, sha: str):
    key = (path, sha)
    if key not in _MODELS:
        import torch
        from sb3_contrib import RecurrentPPO

        torch.set_num_threads(1)
        _MODELS[key] = RecurrentPPO.load(path, device="cpu")
    return _MODELS[key]


class RecurrentPPOController(Controller):
    name = "recurrent_ppo"
    adapts_L = True
    adapts_p = True

    def __init__(self, F: int, L_max: int, p_floor: float, model, checkpoint_meta: dict, deterministic: bool = True):
        super().__init__(F, L_max, p_floor)
        self.model = model
        self.checkpoint_meta = checkpoint_meta
        self.deterministic = deterministic
        self.L, self.p = 1, 1.0
        self.state = None
        self.episode_start = np.ones((1,), dtype=bool)

    def reset(self, L0: int, p0: float) -> Action:
        self.L, self.p = self.clip(L0, p0)
        self.state = None
        self.episode_start = np.ones((1,), dtype=bool)
        return Action(self.L, self.p, {"m": None, "q": None})

    def update(self, obs: dict) -> Action:
        x = normalize_observation(obs, self.F, self.L_max)
        a, self.state = self.model.predict(x, state=self.state, episode_start=self.episode_start, deterministic=self.deterministic)
        self.episode_start = np.zeros((1,), dtype=bool)
        m, q = action_to_multipliers(a)
        self.L, self.p = apply_action(m, q, obs["L"], obs["p"], self.L_max, self.p_floor)
        return Action(self.L, self.p, {"m": m, "q": q})


class PPOControllerFactory:
    """Picklable ``cfg -> controller`` factory (used by batch worker processes)."""

    def __init__(self, alpha: float = 0.5, deterministic: bool = True):
        self.alpha = alpha
        self.deterministic = deterministic
        self.meta = {k: v for k, v in load_meta(alpha).items() if k != "training_config"}

    def __call__(self, cfg: EpisodeConfig) -> RecurrentPPOController:
        model = _load_model(str(checkpoint_path(self.alpha)), self.meta["sha256"])
        s = cfg.system
        return RecurrentPPOController(s.F, compute_global_lmax(s), cfg.assumptions.p_floor, model, self.meta, self.deterministic)


def ppo_controller_factory(alpha: float = 0.5, deterministic: bool = True) -> PPOControllerFactory:
    """Raises ``CheckpointMissing`` when no verified checkpoint exists for ``alpha``."""
    return PPOControllerFactory(alpha, deterministic)
