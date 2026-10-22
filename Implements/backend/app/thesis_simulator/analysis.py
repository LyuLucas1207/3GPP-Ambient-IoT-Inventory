"""Analysis helpers for Sub-Project 1 (multi-reader inventory comparison).

Pure session-level functions. Every helper raises :class:`SceneError` via
:func:`runs_service.get_run` when the run is deleted or missing.
"""

from __future__ import annotations

import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.thesis_simulator.models import (
    ThesisDeviceEvent,
    ThesisInventoryRun,
    ThesisRunRound,
)
from app.thesis_simulator.runs_service import get_run, run_summary

PERCENTILES = (50, 90, 95, 99, 100)
STAGES = ("paging", "m1", "ebi", "m2", "m3")
SUBTYPES = ("1", "2a", "2b")


def identification_curve(session: Session, run_id: int) -> list[tuple[float, int]]:
    get_run(session, run_id)
    rows = session.scalars(
        select(ThesisDeviceEvent.t_s)
        .where(ThesisDeviceEvent.run_id == run_id)
        .where(ThesisDeviceEvent.event_type == "identified")
        .order_by(ThesisDeviceEvent.t_s.asc(), ThesisDeviceEvent.id.asc())
    ).all()
    return [(float(t), i + 1) for i, t in enumerate(rows)]


def completion_time_percentiles(
    session: Session,
    run_id: int,
    *,
    curve: list[tuple[float, int]] | None = None,
    total_identified: int | None = None,
) -> dict[str, float | None]:
    """Return {'50': t_s|None, '90': t_s|None, '100': t_s|None}.

    ``curve`` and ``total_identified`` may be injected to avoid redundant SQL
    when the caller already has them (e.g. when building the full bundle).
    """
    if curve is None:
        curve = identification_curve(session, run_id)
    if total_identified is None:
        run = get_run(session, run_id)
        total_identified = int(run.summary.identified_total) if run.summary else len(curve)
    out: dict[str, float | None] = {str(p): None for p in PERCENTILES}
    if total_identified <= 0:
        return out
    targets = {pct: math.ceil(pct * total_identified / 100) for pct in PERCENTILES}
    remaining = {k: v for k, v in targets.items()}
    for t_s, cumulative in curve:
        for pct, target in list(remaining.items()):
            if cumulative >= target and out[str(pct)] is None:
                out[str(pct)] = float(t_s)
                remaining.pop(pct)
        if not remaining:
            break
    return out


def reader_contribution(session: Session, run_id: int) -> dict[int, int]:
    get_run(session, run_id)
    rows = session.execute(
        select(ThesisDeviceEvent.reader_id, ThesisDeviceEvent.id)
        .where(ThesisDeviceEvent.run_id == run_id)
        .where(ThesisDeviceEvent.event_type == "identified")
        .where(ThesisDeviceEvent.reader_id.is_not(None))
    ).all()
    result: dict[int, int] = {}
    for reader_id, _ in rows:
        result[int(reader_id)] = result.get(int(reader_id), 0) + 1
    return result


def scheme_vs_round_breakdown(session: Session, run_id: int) -> list[dict[str, Any]]:
    get_run(session, run_id)
    rows = session.scalars(
        select(ThesisRunRound)
        .where(ThesisRunRound.run_id == run_id)
        .order_by(ThesisRunRound.reader_id.asc(), ThesisRunRound.round_index.asc())
    ).all()
    return [
        {
            "reader_id": int(row.reader_id),
            "round_index": int(row.round_index),
            "t_start_s": float(row.t_start_s),
            "t_end_s": float(row.t_end_s),
            "success": int(row.success_count),
            "collision": int(row.collision_count),
            "empty": int(row.empty_count),
        }
        for row in rows
    ]


def identification_curve_by_subtype(session: Session, run_id: int) -> dict[str, list[tuple[float, int]]]:
    """Cumulative identifications per device subtype (subtype read from the run's scene snapshot)."""
    run = get_run(session, run_id)
    subtype_of = {
        int(p["id"]): str(p.get("subtype"))
        for p in (run.scene_snapshot_json or {}).get("placements", [])
        if p.get("kind") == "device"
    }
    rows = session.execute(
        select(ThesisDeviceEvent.t_s, ThesisDeviceEvent.device_id)
        .where(ThesisDeviceEvent.run_id == run_id)
        .where(ThesisDeviceEvent.event_type == "identified")
        .order_by(ThesisDeviceEvent.t_s.asc(), ThesisDeviceEvent.id.asc())
    ).all()
    out: dict[str, list[tuple[float, int]]] = {s: [] for s in SUBTYPES}
    for t_s, dev in rows:
        sub = subtype_of.get(int(dev))
        if sub in out:
            out[sub].append((float(t_s), len(out[sub]) + 1))
    return out


def round_aggregates(session: Session, run_id: int) -> dict[str, Any]:
    """Totals over every round: resource efficiency, time overhead per stage,
    depletions per stage x subtype, protocol energy per subtype."""
    rows = session.scalars(select(ThesisRunRound).where(ThesisRunRound.run_id == run_id)).all()
    slots = sum(int(r.slot_count or 0) for r in rows)
    success = sum(int(r.success_count or 0) for r in rows)
    collision = sum(int(r.collision_count or 0) for r in rows)
    empty = sum(int(r.empty_count or 0) for r in rows)
    overhead = {st: 0.0 for st in STAGES}
    deaths = {st: {sub: 0 for sub in SUBTYPES} for st in STAGES}
    energy = {sub: 0.0 for sub in SUBTYPES}
    for r in rows:
        for st in STAGES:
            overhead[st] += float((r.timing_json or {}).get(st, 0.0))
            for sub in SUBTYPES:
                deaths[st][sub] += int(((r.deaths_json or {}).get(st) or {}).get(sub, 0))
        for sub in SUBTYPES:
            energy[sub] += float((r.energy_json or {}).get(sub, 0.0))
    return {
        "slots_total": slots,
        "success_total": success,
        "collision_total": collision,
        "empty_total": empty,
        "resource_efficiency": (success / slots) if slots else 0.0,
        "overhead_s": overhead,
        "deaths_by_stage": deaths,
        "energy_j_by_subtype": energy,
    }


def analysis_bundle(session: Session, run_id: int) -> dict[str, Any]:
    run = get_run(session, run_id)
    summary = run_summary(run)
    curve = identification_curve(session, run_id)
    total = int(summary.get("identified_total", 0))
    percentiles = completion_time_percentiles(
        session, run_id, curve=curve, total_identified=total
    )
    # Percentiles of the whole population (not just of what got identified).
    population = int(summary.get("total_devices", 0))
    population_times = completion_time_percentiles(
        session, run_id, curve=curve, total_identified=population
    ) if population else {str(p): None for p in PERCENTILES}
    contribution = reader_contribution(session, run_id)
    breakdown = scheme_vs_round_breakdown(session, run_id)
    return {
        "run_id": run.id,
        "scheme": run.scheme,
        "status": run.status,
        "summary": summary,
        "config": run.config_json or {},
        "identification_curve": curve,
        "identification_by_subtype": identification_curve_by_subtype(session, run_id),
        "completion_times": percentiles,
        "population_completion_times": population_times,
        "reader_contribution": contribution,
        "rounds_breakdown": breakdown,
        "aggregates": round_aggregates(session, run_id),
    }
