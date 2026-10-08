"""Recurrent PPO training (sb3-contrib RecurrentPPO) with the paper's Table III settings.

Architecture: separate actor and critic LSTMs (1 x 128) each followed by an
MLP 128-128 with ReLU (``shared_lstm=False, enable_critic_lstm=True``).
The LSTM state persists across rounds and is reset at episode boundaries by
RecurrentPPO's ``episode_starts`` handling; minibatches are sequence-based
(truncated BPTT over rollout segments).

"Value normalization" (paper Sec. IV-C4) is realised with SB3's
``VecNormalize(norm_obs=False, norm_reward=True)``: rewards are scaled by a
running estimate of the discounted-return std, so value targets stay O(1).
It affects training only; inference uses raw rewards (none) and the fixed
observation scaling of ``rl.transforms``.
"""

import hashlib
import json
import platform
import subprocess
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np

from app.aperiodic_simulator.core.config import SystemParams
from app.aperiodic_simulator.physics.energy import compute_global_lmax
from app.aperiodic_simulator.rl.checkpoint import CHECKPOINT_DIR, alpha_tag, sha256_file
from app.aperiodic_simulator.rl.env import TRAINING_DISTRIBUTION, AperiodicInventoryEnv
from app.aperiodic_simulator.rl.transforms import ACTION_TRANSFORM, OBSERVATION_NORMALIZATION

PAPER_TRAINING_STEPS = 1_000_000

HYPERPARAMETERS = {
    "learning_rate": 3e-4,
    "gamma": 0.9,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.01,
    "vf_coef": 0.02,
    "max_grad_norm": 0.5,
    "n_steps": 2048,
    "batch_size": 256,
    "n_epochs": 10,
}
ARCHITECTURE = "actor: LSTM(1x128) -> MLP(128,128,ReLU) -> Gaussian(2); critic: LSTM(1x128) -> MLP(128,128,ReLU) -> value"


def policy_kwargs():
    import torch.nn as nn

    return {
        "lstm_hidden_size": 128,
        "n_lstm_layers": 1,
        "shared_lstm": False,
        "enable_critic_lstm": True,
        "net_arch": {"pi": [128, 128], "vf": [128, 128]},
        "activation_fn": nn.ReLU,
    }


def _git_commit() -> str | None:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, cwd=Path(__file__).parent, timeout=5)
        return out.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def _versions() -> dict:
    import gymnasium
    import sb3_contrib
    import stable_baselines3
    import torch

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "torch": torch.__version__,
        "stable_baselines3": stable_baselines3.__version__,
        "sb3_contrib": sb3_contrib.__version__,
        "gymnasium": gymnasium.__version__,
    }


def training_config(alpha: float, seed: int, steps: int) -> dict:
    s = SystemParams()
    return {
        "algorithm": "sb3_contrib.RecurrentPPO / MlpLstmPolicy",
        "alpha": alpha,
        "seed": seed,
        "total_timesteps": steps,
        "hyperparameters": HYPERPARAMETERS,
        "architecture": ARCHITECTURE,
        "training_distribution": TRAINING_DISTRIBUTION,
        "reward": "((1-alpha)*(S1+S2a+S2b)*t_S - alpha*C2*t_C)/T_round; t_S=t_msg1/F+t_msg2+t_msg3/F, t_C=t_msg1/F",
        "value_normalization": "VecNormalize(norm_obs=False, norm_reward=True, gamma=0.9)",
        "action_transform": ACTION_TRANSFORM,
        "observation_normalization": OBSERVATION_NORMALIZATION,
        "L_max": compute_global_lmax(s),
        "system": {k: v for k, v in asdict(s).items() if isinstance(v, (int, float, str))},
    }


class _Progress:
    def __init__(self, total: int, log, every: int = 2048):
        from stable_baselines3.common.callbacks import BaseCallback

        outer = self

        class CB(BaseCallback):
            def _on_step(self) -> bool:
                n = self.num_timesteps
                for info in self.locals.get("infos", []):
                    if "episode" in info:
                        outer.returns.append(info["episode"]["r"])
                        outer.lengths.append(info["episode"]["l"])
                if n - outer.last >= every:
                    outer.last = n
                    r = np.mean(outer.returns[-20:]) if outer.returns else float("nan")
                    log(f"step {n}/{total}  episodes {len(outer.returns)}  mean_return(last20) {r:.3f}  {time.time() - outer.t0:.0f}s")
                return True

        self.returns: list[float] = []
        self.lengths: list[int] = []
        self.last = 0
        self.t0 = time.time()
        self.callback = CB()


def _log(msg: str) -> None:
    print(msg, flush=True)


def train(steps: int, seed: int = 42, alpha: float = 0.5, out_dir: Path = CHECKPOINT_DIR, log=_log) -> dict:
    import torch
    from sb3_contrib import RecurrentPPO
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.utils import set_random_seed
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

    set_random_seed(seed)
    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    venv = DummyVecEnv([lambda: Monitor(AperiodicInventoryEnv(alpha=alpha))])
    venv.seed(seed)
    venv = VecNormalize(venv, norm_obs=False, norm_reward=True, gamma=HYPERPARAMETERS["gamma"])
    model = RecurrentPPO("MlpLstmPolicy", venv, policy_kwargs=policy_kwargs(), seed=seed, device="cpu", verbose=0, **HYPERPARAMETERS)
    prog = _Progress(steps, log)
    t0 = time.time()
    model.learn(total_timesteps=steps, callback=prog.callback)
    wall = time.time() - t0

    out_dir.mkdir(parents=True, exist_ok=True)
    zpath = out_dir / f"recurrent_ppo_alpha_{alpha_tag(alpha)}.zip"
    model.save(zpath)
    cfg = training_config(alpha, seed, steps)
    meta = {
        "alpha": alpha,
        "seed": seed,
        "training_steps": int(model.num_timesteps),
        "requested_steps": steps,
        "paper_training_steps": PAPER_TRAINING_STEPS,
        "fully_trained": int(model.num_timesteps) >= PAPER_TRAINING_STEPS,
        "architecture": ARCHITECTURE,
        "trained_scenario": "multi_source",
        "config_hash": hashlib.sha256(json.dumps(cfg, sort_keys=True, default=str).encode()).hexdigest(),
        "training_config": cfg,
        "action_transform": ACTION_TRANSFORM,
        "observation_normalization": OBSERVATION_NORMALIZATION,
        "package_versions": _versions(),
        "git_commit": _git_commit(),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "wall_time_s": round(wall, 1),
        "training_episodes": len(prog.returns),
        "mean_return_last20": float(np.mean(prog.returns[-20:])) if prog.returns else None,
        "sha256": sha256_file(zpath),
    }
    zpath.with_suffix(".json").write_text(json.dumps(meta, indent=2, default=str))
    log(f"saved {zpath} ({meta['training_steps']} steps, sha256 {meta['sha256'][:16]}…)")
    return meta
