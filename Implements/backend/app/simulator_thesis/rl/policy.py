"""Registry of trained multi-reader policies and the live ``PolicyController``.

A policy is chosen by its ``policy_id`` (e.g.
``ps_ppo_randomized__a0p5__s0__20261110T190000``), never rebuilt from alpha, so
several policies with the same alpha can coexist. Each registry entry in
``policies/`` (or ``$THESIS_POLICY_DIR``) is ``<policy_id>.json`` plus, except
for ``zero_shot_aperiodic``, ``<policy_id>.zip``; the sidecar holds the
algorithm, alpha, seed, scale, training config, observation / action specs,
package versions and the zip's SHA-256, which is verified before loading.

Algorithms
----------
* ``sb3_ppo``             - stable-baselines3 PPO (MLP, parameter sharing).
* ``torch_mlp``           - actors exported by ``training/algos/mappo.py``
  (one shared actor, or one per reader slot for the independent baseline).
* ``zero_shot_aperiodic`` - the original Sources ``A_IoT_PPO_LSTM.zip`` on
  every reader, each with its own LSTM state. Observation and action follow
  that script (raw counts, multipliers already in [0.25, 10] and [0.1, 10]).
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from app.simulator_thesis.rl.source_policy import apply_source_action, source_observation
from app.simulator_thesis.inventory.controller import Decision, _cold_k, _scale_to_grant
from app.simulator_thesis.rl.features import P_FLOOR, apply_action, observation

if TYPE_CHECKING:
    from app.simulator_thesis.inventory.state import EpisodeConfig, ReaderState

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_POLICY_DIR = Path(__file__).resolve().parent / "policies"
ALGOS = ("sb3_ppo", "torch_mlp", "zero_shot_aperiodic")


class PolicyMissing(RuntimeError):
    pass


def policy_dir() -> Path:
    return Path(os.environ.get("THESIS_POLICY_DIR", DEFAULT_POLICY_DIR))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact(meta: dict[str, Any], json_path: Path) -> Path:
    if meta.get("algo") == "zero_shot_aperiodic":
        src = Path(meta["source"])
        return src if src.is_absolute() else BACKEND_ROOT / src
    return json_path.with_suffix(".zip")


def load_meta(policy_id: str, verify: bool = True) -> dict[str, Any]:
    if not policy_id or "/" in policy_id or "\\" in policy_id or policy_id.startswith("."):
        raise PolicyMissing(f"invalid policy id {policy_id!r}")
    mp = policy_dir() / f"{policy_id}.json"
    if not mp.exists():
        raise PolicyMissing(f"policy {policy_id!r} is not in the registry ({policy_dir()})")
    return load_meta_file(mp, verify, policy_id)


def load_meta_file(mp: Path, verify: bool = True, policy_id: str | None = None) -> dict[str, Any]:
    """Load a sidecar outside the registry (e.g. ``training/outputs/.../checkpoints/final.json``)."""
    policy_id = policy_id or mp.stem
    meta = json.loads(mp.read_text())
    if meta.get("algo") not in ALGOS:
        raise PolicyMissing(f"policy {policy_id!r}: unknown algo {meta.get('algo')!r}")
    art = _artifact(meta, mp)
    if not art.exists():
        raise PolicyMissing(f"policy {policy_id!r}: artifact {art} is missing")
    if verify:
        digest = sha256_file(art)
        if digest != meta.get("sha256"):
            raise PolicyMissing(f"policy {policy_id!r} fails SHA-256 verification (metadata {meta.get('sha256')}, file {digest})")
    meta["path"] = str(art)
    meta.setdefault("policy_id", policy_id)
    return meta


def list_policies() -> list[dict[str, Any]]:
    out = []
    d = policy_dir()
    if not d.exists():
        return out
    for mp in sorted(d.glob("*.json")):
        pid = mp.stem
        try:
            meta = load_meta(pid)
            ok, reason = True, None
        except (PolicyMissing, json.JSONDecodeError, KeyError) as exc:
            meta = {"policy_id": pid}
            try:
                meta.update(json.loads(mp.read_text()))
            except json.JSONDecodeError:
                pass
            ok, reason = False, str(exc)
        out.append({
            "policy_id": pid,
            "available": ok,
            "reason": reason,
            "algo": meta.get("algo"),
            "experiment": meta.get("experiment"),
            "alpha": meta.get("alpha"),
            "beta": meta.get("beta"),
            "seed": meta.get("seed"),
            "scale": meta.get("scale"),
            "training_steps": meta.get("training_steps"),
            "created_at": meta.get("created_at"),
            "sha256": meta.get("sha256"),
            "train_config": meta.get("train_config"),
            "eval_summary": meta.get("eval_summary"),
            "notes": meta.get("notes"),
        })
    return out


# ------------------------------------------------------------------ actors

_CACHE: dict[tuple[str, str], Any] = {}


class _Sb3Actor:
    recurrent = False

    def __init__(self, path: str) -> None:
        import torch
        from stable_baselines3 import PPO

        torch.set_num_threads(1)
        self.model = PPO.load(path, device="cpu")

    def act(self, obs: np.ndarray, slot: int, state: Any, deterministic: bool) -> tuple[np.ndarray, Any]:
        a, _ = self.model.predict(obs, deterministic=deterministic)
        return np.asarray(a, dtype=float), None


class _TorchActor:
    recurrent = False

    def __init__(self, path: str) -> None:
        import torch

        from app.simulator_thesis.rl.nets import load_actors

        torch.set_num_threads(1)
        with zipfile.ZipFile(path) as zf:
            self.actors, self.arch = load_actors(zf.read("actors.pt"))
        self.shared = len(self.actors) == 1

    def act(self, obs: np.ndarray, slot: int, state: Any, deterministic: bool) -> tuple[np.ndarray, Any]:
        import torch

        actor = self.actors[0 if self.shared else slot % len(self.actors)]
        with torch.no_grad():
            mu, log_std = actor(torch.as_tensor(obs, dtype=torch.float32).reshape(1, -1))
            a = mu if deterministic else mu + torch.randn_like(mu) * log_std.exp()
        return np.clip(a.numpy().reshape(-1), -1.0, 1.0), None


class _ZeroShotActor:
    """Original Sources RecurrentPPO, one LSTM state per reader."""

    recurrent = True

    def __init__(self, path: str) -> None:
        import torch
        from sb3_contrib import RecurrentPPO

        torch.set_num_threads(1)
        self.model = RecurrentPPO.load(path, device="cpu")

    def observe(self, reader: "ReaderState") -> np.ndarray:
        """Raw counts in the order ``RL.py`` trained: S2b, S2a, S1, empty, collisions, K, p."""
        h = reader.history[-1]
        s1, s2a, s2b = (h.new_by_subtype + (0, 0, 0))[:3]
        return source_observation(s2b, s2a, s1, h.empty, h.collision, h.k, h.pstar)

    def act(self, obs: np.ndarray, slot: int, state: Any, deterministic: bool) -> tuple[np.ndarray, Any]:
        lstm, start = state if state is not None else (None, True)
        a, lstm = self.model.predict(obs, state=lstm, episode_start=np.array([start]), deterministic=deterministic)
        return np.asarray(a, dtype=float), (lstm, False)


def _load_actor(meta: dict[str, Any]):
    key = (meta["path"], meta["sha256"])
    if key not in _CACHE:
        algo = meta["algo"]
        if algo == "sb3_ppo":
            _CACHE[key] = _Sb3Actor(meta["path"])
        elif algo == "torch_mlp":
            _CACHE[key] = _TorchActor(meta["path"])
        else:
            _CACHE[key] = _ZeroShotActor(meta["path"])
    return _CACHE[key]


# ------------------------------------------------------------------ controller


class PolicyController:
    """``ReaderController`` that asks a trained policy for (K, p*) every frame.

    One instance per reader (the engine builds controllers per reader); the
    loaded network is shared through a module cache. The first frame of a
    reader uses the cold-start K and the estimator's p*, as the DFSA does.
    """

    name = "policy"

    def __init__(self, meta: dict[str, Any], actor: Any, deterministic: bool = True, slot: int = 0) -> None:
        self.meta = meta
        self.policy_id = meta["policy_id"]
        self.actor = actor
        self.deterministic = deterministic
        self.slot = slot
        self.k_prev: int | None = None
        self.p_prev: float | None = None
        self.state: Any = None

    @classmethod
    def from_registry(cls, policy_id: str | None, deterministic: bool = True) -> "PolicyController":
        if not policy_id:
            raise PolicyMissing("controller kind 'policy' needs a policy_id")
        meta = load_meta(policy_id)
        return cls(meta, _load_actor(meta), deterministic)

    @classmethod
    def from_meta(cls, meta: dict[str, Any], deterministic: bool = True) -> "PolicyController":
        return cls(meta, _load_actor(meta), deterministic)

    def _obs(self, reader: "ReaderState", config: "EpisodeConfig") -> np.ndarray:
        if isinstance(self.actor, _ZeroShotActor):
            return self.actor.observe(reader)
        return observation(reader, config)

    def decide(self, reader: "ReaderState", config: "EpisodeConfig", group: int, f_r: int) -> Decision:
        if not reader.history or self.k_prev is None:
            k = _scale_to_grant(_cold_k(config), config.consts.f_freq, f_r)
            p = max(P_FLOOR, float(reader.estimator.p_star(k, group)))
            self.k_prev, self.p_prev = k, p
            return Decision(k=k, pstar=p, info={"policy_id": self.policy_id, "cold_start": True})
        slot = int(reader.context.get("slot", self.slot))
        a, self.state = self.actor.act(self._obs(reader, config), slot, self.state, self.deterministic)
        if isinstance(self.actor, _ZeroShotActor):
            k, p, m, q = apply_source_action(a, self.k_prev, self.p_prev or 1.0, f_r, int(config.consts.f_freq))
        else:
            k, p, m, q = apply_action(a, self.k_prev, self.p_prev or 1.0, f_r, int(config.consts.k_max))
        self.k_prev, self.p_prev = k, p
        return Decision(k=k, pstar=p, info={"policy_id": self.policy_id, "m": m, "q": q})

    def state_dict(self) -> dict[str, Any]:
        """Recurrent state is not checkpointed: a resumed zero-shot reader restarts its LSTM."""
        return {"k_prev": self.k_prev, "p_prev": self.p_prev}

    def load_state_dict(self, raw: dict[str, Any]) -> None:
        self.k_prev = raw.get("k_prev")
        self.p_prev = raw.get("p_prev")
        self.state = None
