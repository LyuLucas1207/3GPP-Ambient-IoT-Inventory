"""Training scales: how big a run is.

``--scale`` takes a preset name, ``<preset>:<factor>`` or a bare float. A
float multiplies ``full`` (the single-reader paper's 1e6 steps), so
``--scale 0.1`` is a tenth of the paper budget; ``small:3`` is three times
``small``. The factor scales total steps and evaluation episodes; the preset
fixes the rest. Individual flags (``--steps``, ``--n-envs``,
``--eval-episodes``, ``--n-devices``) override any value.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, replace


@dataclass(frozen=True)
class Scale:
    name: str
    total_steps: int
    n_envs: int
    n_devices: tuple[int, int]  # device count range sampled per training episode
    eval_episodes: int  # per evaluation cell
    eval_grid: str  # mini | standard | full (see evaluate.EVAL_GRIDS)
    n_steps: int  # rollout length per env before an update
    batch_size: int
    n_epochs: int
    t_max_s: float  # simulated time cap of an episode
    max_frames: int

    def to_json(self) -> dict:
        out = asdict(self)
        out["n_devices"] = list(self.n_devices)
        return out


PRESETS: dict[str, Scale] = {
    "smoke": Scale("smoke", 1_024, 1, (40, 120), 1, "mini", 256, 64, 2, 40.0, 2_000),
    "small": Scale("small", 50_000, 4, (100, 400), 3, "standard", 1_024, 256, 5, 120.0, 10_000),
    "medium": Scale("medium", 250_000, 8, (100, 1_000), 5, "standard", 2_048, 256, 10, 300.0, 20_000),
    "full": Scale("full", 1_000_000, 8, (100, 3_000), 10, "full", 2_048, 256, 10, 600.0, 50_000),
}


def resolve_scale(value: str) -> Scale:
    value = str(value).strip()
    if value in PRESETS:
        return PRESETS[value]
    if ":" in value:
        name, factor = value.split(":", 1)
        base = PRESETS[name]
    else:
        base, factor = PRESETS["full"], value
    f = float(factor)
    if f <= 0:
        raise ValueError("scale factor must be > 0")
    return replace(
        base,
        name=f"{base.name}x{f:g}",
        total_steps=max(base.n_steps * base.n_envs, int(round(base.total_steps * f))),
        eval_episodes=max(1, int(math.ceil(base.eval_episodes * f))) if f >= 1 else base.eval_episodes,
    )


def with_overrides(scale: Scale, *, steps: int | None = None, n_envs: int | None = None, eval_episodes: int | None = None,
                   n_devices: tuple[int, int] | None = None, eval_grid: str | None = None) -> Scale:
    kw = {}
    if steps:
        kw["total_steps"] = int(steps)
    if n_envs:
        kw["n_envs"] = int(n_envs)
    if eval_episodes:
        kw["eval_episodes"] = int(eval_episodes)
    if n_devices:
        kw["n_devices"] = (int(n_devices[0]), int(n_devices[1]))
    if eval_grid:
        kw["eval_grid"] = eval_grid
    return replace(scale, **kw) if kw else scale
