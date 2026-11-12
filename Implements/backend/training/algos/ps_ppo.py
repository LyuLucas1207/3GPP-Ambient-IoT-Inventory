"""Parameter-sharing PPO (stable-baselines3) on ``MultiReaderInventoryEnv``.

The interleaved reader decisions form one stream, so a single MLP policy is
trained on every reader's frames; the observation's context features
(readers, neighbours, colour, F_r, offset, position) let it adapt per reader.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

from training.common import CsvLog

DEFAULT_HP = {
    "learning_rate": 3e-4,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.005,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "net_arch": [128, 128],
}


def make_env_fn(env_cfg: dict[str, Any], seed: int):
    def _make():
        from app.thesis_simulator.rl.env import MultiReaderInventoryEnv

        env = MultiReaderInventoryEnv(env_cfg)
        env.reset(seed=seed)
        return env

    return _make


def train(job: dict[str, Any], out_dir: Path, log: CsvLog) -> dict[str, Any]:
    import torch
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import BaseCallback
    from stable_baselines3.common.vec_env import DummyVecEnv, SubprocVecEnv

    torch.set_num_threads(1)
    scale = job["scale"]
    hp = {**DEFAULT_HP, **job.get("hyperparameters", {})}
    n_envs = int(scale["n_envs"])
    fns = [make_env_fn(job["env"], job["seed"] * 1000 + i) for i in range(n_envs)]
    vec = SubprocVecEnv(fns) if job.get("vec") == "subproc" and n_envs > 1 else DummyVecEnv(fns)

    class EpisodeLog(BaseCallback):
        def __init__(self) -> None:
            super().__init__()
            self.ret = [0.0] * n_envs
            self.episodes = 0

        def _on_step(self) -> bool:
            for i, (r, d, info) in enumerate(zip(self.locals["rewards"], self.locals["dones"], self.locals["infos"])):
                self.ret[i] += float(r)
                if d:
                    s = info.get("episode_summary") or {}
                    self.episodes += 1
                    log.write({
                        "timesteps": self.num_timesteps, "episode": self.episodes, "return": self.ret[i],
                        "identified_fraction": (s.get("identified", 0) / max(1, s.get("reachable", 1))),
                        "t99": s.get("t99"), "t_mean": s.get("t_mean"), "resource_efficiency": s.get("resource_efficiency"),
                        "readers": s.get("readers"), "resource": s.get("resource"), "devices": s.get("devices"),
                    })
                    self.ret[i] = 0.0
            return True

    tb = None
    if importlib.util.find_spec("tensorboard") is not None:
        tb = str(out_dir / "tb")
    model = PPO(
        "MlpPolicy", vec,
        n_steps=int(scale["n_steps"]), batch_size=int(scale["batch_size"]), n_epochs=int(scale["n_epochs"]),
        learning_rate=hp["learning_rate"], gamma=hp["gamma"], gae_lambda=hp["gae_lambda"], clip_range=hp["clip_range"],
        ent_coef=hp["ent_coef"], vf_coef=hp["vf_coef"], max_grad_norm=hp["max_grad_norm"],
        policy_kwargs={"net_arch": list(hp["net_arch"])}, seed=int(job["seed"]), device="cpu", verbose=0, tensorboard_log=tb,
    )
    model.learn(total_timesteps=int(scale["total_steps"]), callback=EpisodeLog())
    path = out_dir / "checkpoints" / "final.zip"
    model.save(str(path))
    vec.close()
    return {
        "algo": "sb3_ppo",
        "artifact": path,
        "training_steps": int(model.num_timesteps),
        "architecture": f"MLP{tuple(hp['net_arch'])} tanh -> Gaussian(2) (shared by all readers); critic MLP{tuple(hp['net_arch'])}",
        "hyperparameters": hp,
    }
