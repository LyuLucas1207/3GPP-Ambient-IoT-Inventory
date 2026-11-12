"""Per-reader (K, p*) controllers.

``K`` is the total number of Msg1 resources of a frame (``L_s x F_r``) and
``p*`` the paging/access probability. A controller sees only what a real
reader sees: its own frame history and its resource grant.

* ``fixed``  - every frame uses ``k_initial`` resources, i.e. ``L_s = k_initial / F``
  Msg1 periods. With fewer granted subbands ``F_r`` the controller keeps
  ``L_s`` and asks for ``L_s x F_r`` resources.
* ``dfsa``   - ``k_initial`` is the cold-start K; later frames follow the
  Schoute / empty-slot backlog rule ``K = 2 N_hat``.
* ``policy`` - a trained RL policy from the registry (``app.thesis_simulator.rl``).

In every case ``p*`` comes from the reader's backlog estimator unless the
controller overrides it.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from app.thesis_simulator.inventory.state import EpisodeConfig, ReaderState

HISTORY_LEN = 16
"""Frames of per-reader history kept for controllers and termination rules."""

DEFAULT_COLD_K = 128


@dataclass(frozen=True)
class FrameRecord:
    """What a reader observed in one of its frames."""

    t_start: float
    t_end: float
    k: int
    pstar: float
    success: int
    collision: int
    empty: int
    new_ids: int
    joiners: int
    f_r: int
    new_by_subtype: tuple[int, ...] = (0, 0, 0)

    def to_json(self) -> dict[str, Any]:
        out = dict(self.__dict__)
        out["new_by_subtype"] = list(self.new_by_subtype)
        return out

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> "FrameRecord":
        raw = dict(raw)
        raw["new_by_subtype"] = tuple(raw.get("new_by_subtype", (0, 0, 0)))
        return cls(**raw)


def new_history() -> deque[FrameRecord]:
    return deque(maxlen=HISTORY_LEN)


@dataclass(frozen=True)
class ControllerSpec:
    kind: str = "auto"  # auto | fixed | dfsa | policy
    policy_id: str | None = None
    deterministic: bool = True

    @classmethod
    def from_json(cls, raw: dict[str, Any] | None) -> "ControllerSpec":
        raw = raw or {}
        return cls(
            kind=str(raw.get("kind", "auto")),
            policy_id=raw.get("policy_id"),
            deterministic=bool(raw.get("deterministic", True)),
        )

    def to_json(self) -> dict[str, Any]:
        return {"kind": self.kind, "policy_id": self.policy_id, "deterministic": self.deterministic}


@dataclass
class Decision:
    k: int
    pstar: float
    info: dict[str, Any] = field(default_factory=dict)


class ReaderController(Protocol):
    name: str

    def decide(self, reader: "ReaderState", config: "EpisodeConfig", group: int, f_r: int) -> Decision: ...


def _cold_k(config: "EpisodeConfig") -> int:
    return max(8, int(config.k_initial)) if config.k_initial is not None else DEFAULT_COLD_K


def _scale_to_grant(k: int, F: int, f_r: int) -> int:
    """Keep the Msg1 length ``L_s = ceil(K/F)`` when only ``f_r`` of ``F`` subbands are granted."""
    if f_r >= F:
        return k
    return max(1, math.ceil(k / F)) * max(1, f_r)


class FixedController:
    name = "fixed"

    def decide(self, reader: "ReaderState", config: "EpisodeConfig", group: int, f_r: int) -> Decision:
        k = _scale_to_grant(_cold_k(config), config.consts.f_freq, f_r)
        return Decision(k=k, pstar=reader.estimator.p_star(k, group))


class DfsaController:
    name = "dfsa"

    def decide(self, reader: "ReaderState", config: "EpisodeConfig", group: int, f_r: int) -> Decision:
        cold = _scale_to_grant(_cold_k(config), config.consts.f_freq, f_r)
        est = reader.estimator.mnot_next[group]
        k = cold if est is None or est <= 0 else max(16, min(config.consts.k_max, int(2 * est)))
        return Decision(k=k, pstar=reader.estimator.p_star(k, group))


def build_controller(config: "EpisodeConfig") -> ReaderController:
    spec = config.controller
    kind = spec.kind
    if kind == "auto":
        kind = "dfsa" if config.adaptive_k else "fixed"
    if kind == "fixed":
        return FixedController()
    if kind == "dfsa":
        return DfsaController()
    if kind == "policy":
        from app.thesis_simulator.rl.policy import PolicyController

        return PolicyController.from_registry(spec.policy_id, deterministic=spec.deterministic)
    raise ValueError(f"unknown controller kind {spec.kind!r}")
