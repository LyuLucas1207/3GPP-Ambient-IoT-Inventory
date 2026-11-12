"""MAPPO (centralized critic, shared actor) and IPPO, in plain torch.

Centralized training, decentralized execution (CTDE): each reader acts on its
own observation, while the critic also sees the environment's global state
(true progress, energies, every reader's last frame), which only exists in
simulation. ``independent.py`` reuses this loop with one actor and one local
critic per reader slot (no parameter sharing, no global state).

The environment emits one decision at a time (earliest-clock reader), so a
rollout is one interleaved stream per environment; GAE runs over that stream.
"""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
import io
import json
import zipfile

import numpy as np

from training.common import CsvLog

DEFAULT_HP = {
    "learning_rate": 3e-4,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.005,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "hidden": [128, 128],
    "slots": 18,
}


def train(job: dict[str, Any], out_dir: Path, log: CsvLog, *, shared: bool = True, central: bool = True) -> dict[str, Any]:
    import torch

    from app.thesis_simulator.rl.env import GLOBAL_DIM, MultiReaderInventoryEnv
    from app.thesis_simulator.rl.features import ACTION_DIM, OBS_DIM
    from app.thesis_simulator.rl.nets import make_actor, make_critic, save_actor_bytes

    torch.set_num_threads(1)
    torch.manual_seed(int(job["seed"]))
    scale = job["scale"]
    hp = {**DEFAULT_HP, **job.get("hyperparameters", {})}
    hidden = tuple(hp["hidden"])
    n_actors = 1 if shared else int(hp["slots"])
    actors = [make_actor(OBS_DIM, ACTION_DIM, hidden) for _ in range(n_actors)]
    critic_in = OBS_DIM + (GLOBAL_DIM if central else 0)
    critics = [make_critic(critic_in, hidden) for _ in range(1 if (shared or central) else n_actors)]
    params = [p for m in actors + critics for p in m.parameters()]
    opt = torch.optim.Adam(params, lr=hp["learning_rate"])

    n_envs = int(scale["n_envs"])
    envs = [MultiReaderInventoryEnv(job["env"]) for _ in range(n_envs)]
    obs = [env.reset(seed=int(job["seed"]) * 1000 + i)[0] for i, env in enumerate(envs)]
    slots = [int(env._info()["slot"] or 0) for env in envs]
    ret = [0.0] * n_envs
    episodes = 0
    n_steps = int(scale["n_steps"])
    total = int(scale["total_steps"])
    steps_done = 0

    def actor_for(slot: int):
        return actors[0 if shared else slot % n_actors]

    def critic_for(slot: int):
        return critics[0 if len(critics) == 1 else slot % len(critics)]

    def value(o: np.ndarray, g: np.ndarray, slot: int) -> float:
        x = np.concatenate([o, g]) if central else o
        with torch.no_grad():
            return float(critic_for(slot)(torch.as_tensor(x, dtype=torch.float32).reshape(1, -1))[0, 0])

    while steps_done < total:
        buf: list[list[dict[str, Any]]] = [[] for _ in range(n_envs)]
        last_values = [0.0] * n_envs
        for e, env in enumerate(envs):
            for _ in range(n_steps):
                o, slot = obs[e], slots[e]
                g = env.global_state()
                with torch.no_grad():
                    mu, log_std = actor_for(slot)(torch.as_tensor(o, dtype=torch.float32).reshape(1, -1))
                    dist = torch.distributions.Normal(mu, log_std.exp())
                    a = dist.sample()
                    logp = float(dist.log_prob(a).sum())
                a_np = a.numpy().reshape(-1)
                v = value(o, g, slot)
                o2, r, te, tr, info = env.step(np.clip(a_np, -1.0, 1.0))
                ret[e] += r
                buf[e].append({"obs": o, "g": g, "slot": slot, "a": a_np, "logp": logp, "r": r, "done": te or tr, "v": v, "terminal": te})
                steps_done += 1
                if te or tr:
                    s = info.get("episode_summary") or {}
                    episodes += 1
                    log.write({
                        "timesteps": steps_done, "episode": episodes, "return": ret[e],
                        "identified_fraction": s.get("identified", 0) / max(1, s.get("reachable", 1)),
                        "t99": s.get("t99"), "t_mean": s.get("t_mean"), "resource_efficiency": s.get("resource_efficiency"),
                        "readers": s.get("readers"), "resource": s.get("resource"), "devices": s.get("devices"),
                    })
                    ret[e] = 0.0
                    o2, _ = env.reset()
                obs[e] = o2
                slots[e] = int(env._info()["slot"] or 0)
            last_values[e] = value(obs[e], env.global_state(), slots[e])

        # ---- GAE per environment stream
        rows = []
        for e in range(n_envs):
            adv = 0.0
            nxt = last_values[e]
            for t in reversed(range(len(buf[e]))):
                b = buf[e][t]
                nonterminal = 0.0 if b["done"] else 1.0
                # time-limit truncation bootstraps from the value; a true terminal does not
                boot = 0.0 if b["terminal"] else (nxt if not b["done"] else b["v"])
                delta = b["r"] + hp["gamma"] * boot - b["v"]
                adv = delta + hp["gamma"] * hp["gae_lambda"] * nonterminal * adv
                b["adv"], b["ret"] = adv, adv + b["v"]
                nxt = b["v"]
            rows.extend(buf[e])
        O = torch.as_tensor(np.array([b["obs"] for b in rows]), dtype=torch.float32)
        G = torch.as_tensor(np.array([b["g"] for b in rows]), dtype=torch.float32)
        A = torch.as_tensor(np.array([b["a"] for b in rows]), dtype=torch.float32)
        LP = torch.as_tensor([b["logp"] for b in rows], dtype=torch.float32)
        ADV = torch.as_tensor([b["adv"] for b in rows], dtype=torch.float32)
        RET = torch.as_tensor([b["ret"] for b in rows], dtype=torch.float32)
        SL = np.array([b["slot"] for b in rows])
        ADV = (ADV - ADV.mean()) / (ADV.std() + 1e-8)
        X = torch.cat([O, G], dim=1) if central else O
        idx = np.arange(len(rows))
        bs = int(scale["batch_size"])
        for _ in range(int(scale["n_epochs"])):
            np.random.shuffle(idx)
            for start in range(0, len(idx), bs):
                mb = idx[start:start + bs]
                groups = [mb] if shared else [mb[SL[mb] % n_actors == s] for s in np.unique(SL[mb] % n_actors)]
                loss = torch.zeros(())
                for gidx in groups:
                    if gidx.size == 0:
                        continue
                    slot = int(SL[gidx[0]])
                    mu, log_std = actor_for(slot)(O[gidx])
                    dist = torch.distributions.Normal(mu, log_std.exp())
                    new_lp = dist.log_prob(A[gidx]).sum(-1)
                    ratio = (new_lp - LP[gidx]).exp()
                    s1 = ratio * ADV[gidx]
                    s2 = ratio.clamp(1 - hp["clip_range"], 1 + hp["clip_range"]) * ADV[gidx]
                    v = critic_for(slot)(X[gidx]).squeeze(-1)
                    w = gidx.size / mb.size
                    loss = loss + w * (-torch.min(s1, s2).mean() + hp["vf_coef"] * (v - RET[gidx]).pow(2).mean()
                                       - hp["ent_coef"] * dist.entropy().sum(-1).mean())
                opt.zero_grad()
                loss.backward()
                torch.nn.utils.clip_grad_norm_(params, hp["max_grad_norm"])
                opt.step()

    arch = {"obs_dim": OBS_DIM, "act_dim": ACTION_DIM, "hidden": list(hidden), "activation": "tanh", "shared": shared, "central_critic": central}
    path = out_dir / "checkpoints" / "final.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("actors.pt", save_actor_bytes(actors, arch))
        zf.writestr("arch.json", json.dumps(arch, indent=1))
        buf_c = io.BytesIO()
        torch.save([c.state_dict() for c in critics], buf_c)
        zf.writestr("critics.pt", buf_c.getvalue())
    kind = "MAPPO (shared actor, centralized critic)" if shared and central else (
        "IPPO (one actor and local critic per reader slot)" if not shared else "PPO (shared actor, local critic)")
    return {
        "algo": "torch_mlp",
        "artifact": path,
        "training_steps": steps_done,
        "architecture": f"{kind}; actor MLP{hidden} tanh -> Gaussian(2); critic MLP{hidden} on obs{' + global state' if central else ''}",
        "hyperparameters": hp,
    }
