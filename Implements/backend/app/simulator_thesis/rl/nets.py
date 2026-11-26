"""Small torch networks shared by the MAPPO / IPPO trainer and policy loading."""

from __future__ import annotations

import io
from typing import Any


def build_mlp(in_dim: int, out_dim: int, hidden: tuple[int, ...], activation: str = "tanh"):
    import torch.nn as nn

    act = {"tanh": nn.Tanh, "relu": nn.ReLU}[activation]
    layers: list[Any] = []
    d = in_dim
    for h in hidden:
        layers += [nn.Linear(d, h), act()]
        d = h
    layers.append(nn.Linear(d, out_dim))
    return nn.Sequential(*layers)


def make_actor(obs_dim: int, act_dim: int, hidden: tuple[int, ...] = (128, 128), activation: str = "tanh"):
    """Gaussian actor: ``mean = mlp(obs)``, state-independent ``log_std``."""
    import torch
    import torch.nn as nn

    class Actor(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.mu = build_mlp(obs_dim, act_dim, hidden, activation)
            self.log_std = nn.Parameter(torch.full((act_dim,), -0.5))

        def forward(self, obs):
            return self.mu(obs), self.log_std.expand(obs.shape[0], -1)

    return Actor()


def make_critic(in_dim: int, hidden: tuple[int, ...] = (128, 128), activation: str = "tanh"):
    return build_mlp(in_dim, 1, hidden, activation)


def save_actor_bytes(actors: list, arch: dict[str, Any]) -> bytes:
    import torch

    buf = io.BytesIO()
    torch.save({"arch": arch, "actors": [a.state_dict() for a in actors]}, buf)
    return buf.getvalue()


def load_actors(blob: bytes) -> tuple[list, dict[str, Any]]:
    import torch

    data = torch.load(io.BytesIO(blob), map_location="cpu", weights_only=False)
    arch = data["arch"]
    actors = []
    for sd in data["actors"]:
        a = make_actor(arch["obs_dim"], arch["act_dim"], tuple(arch["hidden"]), arch.get("activation", "tanh"))
        a.load_state_dict(sd)
        a.eval()
        actors.append(a)
    return actors, arch
