"""Several independent episodes of one config, kept only as averages.

Episode i uses ``base_seed + i``. Nothing per-device is written: an average
run has a mean identification curve (and a 5–95% band) for the analysis
page, and no warehouse replay, device energy trace, or reader time-frequency.
"""

from __future__ import annotations

import threading
from typing import Any

import numpy as np

from app.simulator_thesis.inventory.episode import build_episode, finish_episode, mark_unreachable, step_episode
from app.simulator_thesis.inventory.events import EventEmitter
from app.simulator_thesis.inventory.state import SUBTYPE_CODE, EpisodeConfig

CURVE_STEP_S = 0.25
STAGES = ("paging", "m1", "ebi", "m2", "m3")
SUBTYPES = ("1", "2a", "2b")
_LABEL = {code: label for label, code in SUBTYPE_CODE.items()}


def sample_episode(
    scene: dict[str, Any],
    config: EpisodeConfig,
    seed: int,
    stop: threading.Event,
) -> dict[str, Any] | None:
    """Run one episode in memory. ``None`` if ``stop`` is set before it finishes."""
    state = build_episode(scene, config, np.random.default_rng(seed))
    emit = EventEmitter(run_id=0)
    world = state.world
    sub_of = {int(world.placement_ids[i]): _LABEL.get(int(world.subtype_code[i]), "1") for i in range(world.N)}
    ident: list[float] = []
    by_sub: dict[str, list[float]] = {s: [] for s in SUBTYPES}
    by_reader: dict[int, int] = {}
    totals = _blank_totals()
    mark_unreachable(state, emit)
    _take(emit, sub_of, ident, by_sub, by_reader, totals)
    while True:
        if stop.is_set():
            return None
        result = step_episode(state, emit)
        _take(emit, sub_of, ident, by_sub, by_reader, totals)
        if result is None:
            finish_episode(state, emit)
            _take(emit, sub_of, ident, by_sub, by_reader, totals)
            break
    counters = state.counters()
    ident.sort()
    for times in by_sub.values():
        times.sort()
    return {
        "sim_time_s": float(counters["sim_time_s"]),
        "total": int(counters["total"]),
        "identified": int(counters["identified"]),
        "identified_by_subtype": {k: int(v) for k, v in counters["identified_by_subtype"].items()},
        "unreachable": int(counters["unreachable"]),
        "depletions": int(counters["depletions"]),
        "dropped": int(counters["dropped"]) + int(counters["unreachable"]) + int(counters["no_progress"]) + int(counters["terminated_early"]),
        "rounds": int(counters["rounds"]),
        "terminated_early": int(counters["terminated_early"]),
        "readers_stopped": int(counters["readers_stopped"]),
        "ident": ident,
        "by_sub": by_sub,
        "by_reader": by_reader,
        "totals": totals,
    }


def average_samples(samples: list[dict[str, Any]], *, episodes: int, base_seed: int) -> dict[str, Any]:
    """Mean of finished episodes, plus the 5–95% band of the identification curve."""
    n = len(samples)
    grid = _grid(max(s["sim_time_s"] for s in samples))
    mean, p05, p95 = _band(grid, [s["ident"] for s in samples])
    by_subtype = {label: _band(grid, [s["by_sub"][label] for s in samples])[0] for label in SUBTYPES}
    readers: dict[str, float] = {}
    keys = {rid for s in samples for rid in s["by_reader"]}
    for rid in keys:
        readers[str(rid)] = sum(s["by_reader"].get(rid, 0) for s in samples) / n
    return {
        "episodes": episodes,
        "episodes_done": n,
        "base_seed": base_seed,
        "total": int(samples[0]["total"]),
        "identified": _mean(samples, "identified"),
        "identified_by_subtype": {
            label: sum(s["identified_by_subtype"].get(label, 0) for s in samples) / n for label in SUBTYPES
        },
        "sim_time_s": _mean(samples, "sim_time_s"),
        "unreachable": _mean(samples, "unreachable"),
        "depletions": _mean(samples, "depletions"),
        "dropped": _mean(samples, "dropped"),
        "rounds": _mean(samples, "rounds"),
        "terminated_early": _mean(samples, "terminated_early"),
        "readers_stopped": _mean(samples, "readers_stopped"),
        "curve": _pack(grid, mean),
        "band": _pack_band(grid, p05, p95),
        "by_subtype": {label: _pack(grid, series) for label, series in by_subtype.items()},
        "contribution": readers,
        "aggregates": _mean_totals([s["totals"] for s in samples]),
    }


def _take(emit: EventEmitter, sub_of: dict[int, str], ident: list[float], by_sub: dict[str, list[float]], by_reader: dict[int, int], totals: dict[str, Any]) -> None:
    for dev, rid, _handle, t_s, event_type, *_rest in emit._device_events:
        if event_type != "identified":
            continue
        ident.append(float(t_s))
        label = sub_of.get(int(dev))
        if label in by_sub:
            by_sub[label].append(float(t_s))
        if rid is not None:
            by_reader[int(rid)] = by_reader.get(int(rid), 0) + 1
    for row in emit._rounds:
        totals["slots"] += int(row.slot_count or 0)
        totals["success"] += int(row.success_count or 0)
        totals["collision"] += int(row.collision_count or 0)
        totals["empty"] += int(row.empty_count or 0)
        timing = row.timing_json or {}
        deaths = row.deaths_json or {}
        energy = row.energy_json or {}
        for stage in STAGES:
            totals["overhead"][stage] += float(timing.get(stage, 0.0))
            stage_deaths = deaths.get(stage) or {}
            for label in SUBTYPES:
                totals["deaths"][stage][label] += int(stage_deaths.get(label, 0))
        for label in SUBTYPES:
            totals["energy"][label] += float(energy.get(label, 0.0))
    emit.discard()


def _blank_totals() -> dict[str, Any]:
    return {
        "slots": 0,
        "success": 0,
        "collision": 0,
        "empty": 0,
        "overhead": {stage: 0.0 for stage in STAGES},
        "deaths": {stage: {label: 0 for label in SUBTYPES} for stage in STAGES},
        "energy": {label: 0.0 for label in SUBTYPES},
    }


def _mean_totals(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    slots = sum(r["slots"] for r in rows) / n
    success = sum(r["success"] for r in rows) / n
    return {
        "slots_total": slots,
        "success_total": success,
        "collision_total": sum(r["collision"] for r in rows) / n,
        "empty_total": sum(r["empty"] for r in rows) / n,
        "resource_efficiency": (success / slots) if slots else 0.0,
        "overhead_s": {stage: sum(r["overhead"][stage] for r in rows) / n for stage in STAGES},
        "deaths_by_stage": {
            stage: {label: sum(r["deaths"][stage][label] for r in rows) / n for label in SUBTYPES} for stage in STAGES
        },
        "energy_j_by_subtype": {label: sum(r["energy"][label] for r in rows) / n for label in SUBTYPES},
    }


def _grid(t_max: float) -> np.ndarray:
    n = max(1, int(np.ceil(t_max / CURVE_STEP_S)))
    grid = np.arange(n + 1, dtype=float) * CURVE_STEP_S
    if grid[-1] < t_max:
        grid = np.append(grid, t_max)
    return grid


def _band(grid: np.ndarray, series: list[list[float]]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    cols = [np.searchsorted(np.asarray(times, dtype=float), grid, side="right").astype(float) for times in series]
    arr = np.vstack(cols)
    return arr.mean(axis=0), np.quantile(arr, 0.05, axis=0), np.quantile(arr, 0.95, axis=0)


def _pack(grid: np.ndarray, values: np.ndarray) -> list[list[float]]:
    return [[round(float(t), 4), round(float(v), 2)] for t, v in zip(grid, values)]


def _pack_band(grid: np.ndarray, low: np.ndarray, high: np.ndarray) -> list[list[float]]:
    return [[round(float(t), 4), round(float(lo), 2), round(float(hi), 2)] for t, lo, hi in zip(grid, low, high)]


def _mean(samples: list[dict[str, Any]], key: str) -> float:
    return sum(s[key] for s in samples) / len(samples)
