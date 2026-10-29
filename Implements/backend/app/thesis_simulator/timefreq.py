"""Time-frequency views of a run: one reader's frames, one device's life.

``reader_timefreq`` returns the frames of one reader inside a time window with
everything needed to draw the paper's resource grid (paging, the K Msg1 slots
over F subbands, EI, Msg2 one after another, Msg3 F in parallel) and which
device used which resource.

``device_trace`` returns one device's protocol events plus its energy between
them, rebuilt with the engine's own on/off model (``energy.advance_availability``
for a single device): ON drains ``P_on`` until the on timer or ``Eoff``, OFF
harvests ``Ph`` up to ``Ecap`` and turns ON again for ``T_on``.
"""

from __future__ import annotations

import math
from functools import lru_cache
from typing import Any

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.thesis_simulator.inventory.state import EpisodeConfig
from app.thesis_simulator.models import (
    ThesisDeviceEvent,
    ThesisReaderEvent,
    ThesisRunRound,
    ThesisRunSnapshot,
)
from app.thesis_simulator.runs_service import _device_event_out, get_run, scene_device_ids
from app.thesis_simulator.service import SceneError

MAX_ROUNDS_PER_WINDOW = 400
MAX_ENERGY_SEGMENTS = 20000
_EPS = 1e-15


def _consts_out(config: EpisodeConfig) -> dict[str, float]:
    c = config.consts
    return {
        "t_paging": c.t_paging(),
        "t_m1": c.t_m1(),
        "t_m2": c.t_m2(),
        "t_m3": c.t_m3(),
        "f": max(1, int(c.f_freq)),
    }


def reader_timefreq(db: Session, run_id: int, reader_id: int, t0: float, t1: float) -> dict[str, Any]:
    run = get_run(db, run_id)
    config = EpisodeConfig.from_json(run.scheme, run.config_json or {})
    t_end = db.scalar(
        select(func.max(ThesisRunRound.t_end_s))
        .where(ThesisRunRound.run_id == run_id)
        .where(ThesisRunRound.reader_id == reader_id)
    )
    t_first = db.scalar(
        select(func.min(ThesisRunRound.t_start_s))
        .where(ThesisRunRound.run_id == run_id)
        .where(ThesisRunRound.reader_id == reader_id)
    )
    rows = db.scalars(
        select(ThesisRunRound)
        .where(ThesisRunRound.run_id == run_id)
        .where(ThesisRunRound.reader_id == reader_id)
        .where(ThesisRunRound.t_end_s >= t0)
        .where(ThesisRunRound.t_start_s <= t1)
        .order_by(ThesisRunRound.t_start_s.asc())
        .limit(MAX_ROUNDS_PER_WINDOW)
    ).all()
    ids = [r.id for r in rows]

    winners: dict[int, dict[int, list]] = {rid: {} for rid in ids}
    m2: dict[int, list[tuple[int, int]]] = {rid: [] for rid in ids}
    m3: dict[int, list[tuple[float, int]]] = {rid: [] for rid in ids}
    identified: dict[int, set[int]] = {rid: set() for rid in ids}
    if ids:
        for ev in db.scalars(
            select(ThesisReaderEvent)
            .where(ThesisReaderEvent.run_id == run_id)
            .where(ThesisReaderEvent.round_id.in_(ids))
            .where(ThesisReaderEvent.event_type == "m1_rx_success")
        ):
            p = ev.payload_json or {}
            if ev.slot_index is not None:
                winners[ev.round_id][int(ev.slot_index)] = [int(p.get("device_id", -1)), bool(p.get("captured", False))]
        for ev in db.scalars(
            select(ThesisDeviceEvent)
            .where(ThesisDeviceEvent.run_id == run_id)
            .where(ThesisDeviceEvent.round_id.in_(ids))
            .where(ThesisDeviceEvent.event_type.in_(("m2_rx", "m3_tx", "identified")))
        ):
            if ev.event_type == "m2_rx":
                m2[ev.round_id].append((int((ev.payload_json or {}).get("m2_index", 0)), int(ev.device_id)))
            elif ev.event_type == "m3_tx":
                m3[ev.round_id].append((float(ev.t_s), int(ev.device_id)))
            else:
                identified[ev.round_id].add(int(ev.device_id))

    frames = []
    for r in rows:
        slots = r.slots_json or {}
        m2_order = [dev for _, dev in sorted(m2[r.id])]
        m2_rank = {dev: i for i, dev in enumerate(m2_order)}
        # Msg3 shares a time slot across F subbands; within one slot the
        # subband follows the served (Msg2) order, as in the engine.
        m3_rows: list[list] = []
        by_t: dict[float, list[int]] = {}
        for t_s, dev in m3[r.id]:
            by_t.setdefault(round(t_s, 9), []).append(dev)
        for t_s in sorted(by_t):
            devs = sorted(by_t[t_s], key=lambda d: m2_rank.get(d, 1 << 30))
            for row, dev in enumerate(devs):
                m3_rows.append([t_s, row, dev, dev in identified[r.id]])
        frames.append(
            {
                "id": r.id,
                "round_index": r.round_index,
                "t_start_s": r.t_start_s,
                "t_end_s": r.t_end_s,
                "k": r.slot_count,
                "group": (r.metadata_json or {}).get("group"),
                "pstar": r.pstar,
                "timing": r.timing_json or {},
                "f": int(slots.get("f") or 1),
                "occ": slots.get("occ") or [],
                "res": slots.get("res") or [],
                "winners": {str(s): v for s, v in winners[r.id].items()},
                "m2": m2_order,
                "m3": m3_rows,
                "budget_dropped": r.budget_dropped or 0,
            }
        )
    return {
        "reader_id": reader_id,
        "scheme": run.scheme,
        "t_first": float(t_first or 0.0),
        "t_end": float(t_end or 0.0),
        "consts": _consts_out(config),
        "truncated": len(rows) >= MAX_ROUNDS_PER_WINDOW,
        "frames": frames,
    }


@lru_cache(maxsize=8)
def _energy_params(run_id: int, scheme: str, config_key: str) -> dict[str, np.ndarray]:
    """Per-device energy parameters of a run (the scene snapshot never changes)."""
    import json

    from app.thesis_simulator.db import session_factory
    from app.thesis_simulator.inventory.episode import build_episode

    with session_factory()() as db:
        run = get_run(db, run_id, include_deleted=True)
        config = EpisodeConfig.from_json(scheme, json.loads(config_key))
        state = build_episode(dict(run.scene_snapshot_json or {}), config, np.random.default_rng(0), warm_start=False)
    w = state.world
    return {
        "Ph": w.Ph_total.copy(),
        "P_on": w.P_on.copy(),
        "Ecap": w.Ecap.copy(),
        "Eoff": w.Eoff.copy(),
        "T_on": w.T_on_default.copy(),
    }


def _evolve(E: float, on: float, dt: float, p: dict[str, float], t: float, out: list[list]) -> tuple[float, float]:
    """Single-device ``advance_availability``: append [t_a, t_b, E_a, E_b, kind] segments."""
    rem = dt
    while rem > _EPS and len(out) < MAX_ENERGY_SEGMENTS:
        if on > 0.0:
            t_eoff = (E - p["Eoff"]) / p["P_on"] if p["P_on"] > 0 else math.inf
            ta = min(rem, on, max(0.0, t_eoff))
            e1 = E - p["P_on"] * ta
            if ta > 0:
                out.append([t, t + ta, E, e1, "on"])
            E, on, rem, t = e1, on - ta, rem - ta, t + ta
            if on <= 0.0 or E <= p["Eoff"] + _EPS:
                on = 0.0
            continue
        if p["Ph"] <= 0.0:
            out.append([t, t + rem, E, E, "off"])
            return E, 0.0
        t_cap = max(0.0, (p["Ecap"] - E) / p["Ph"])
        tb = min(rem, t_cap)
        e1 = min(p["Ecap"], E + p["Ph"] * tb)
        if tb > 0:
            out.append([t, t + tb, E, e1, "off"])
        E, rem, t = e1, rem - tb, t + tb
        if rem > _EPS:
            E, on = p["Ecap"], p["T_on"]
    return E, on


def device_trace(db: Session, run_id: int, device_id: int) -> dict[str, Any]:
    import json

    run = get_run(db, run_id)
    config = EpisodeConfig.from_json(run.scheme, run.config_json or {})
    ids = scene_device_ids(run)
    try:
        idx = ids.index(device_id)
    except ValueError as exc:
        raise SceneError("device_not_found", 404) from exc

    rows = db.scalars(
        select(ThesisDeviceEvent)
        .where(ThesisDeviceEvent.run_id == run_id)
        .where(ThesisDeviceEvent.device_id == device_id)
        .order_by(ThesisDeviceEvent.t_s.asc(), ThesisDeviceEvent.id.asc())
    ).all()
    round_ids = sorted({r.round_id for r in rows if r.round_id is not None})
    rounds = []
    if round_ids:
        for r in db.scalars(select(ThesisRunRound).where(ThesisRunRound.id.in_(round_ids)).order_by(ThesisRunRound.t_start_s)):
            rounds.append(
                {
                    "id": r.id,
                    "reader_id": r.reader_id,
                    "round_index": r.round_index,
                    "t_start_s": r.t_start_s,
                    "t_end_s": r.t_end_s,
                    "k": r.slot_count,
                    "timing": r.timing_json or {},
                }
            )

    all_params = _energy_params(run.id, run.scheme, json.dumps(run.config_json or {}, sort_keys=True))
    p = {k: float(v[idx]) for k, v in all_params.items()}

    first = db.scalars(
        select(ThesisRunSnapshot)
        .where(ThesisRunSnapshot.run_id == run_id)
        .order_by(ThesisRunSnapshot.frame_seq.asc(), ThesisRunSnapshot.id.asc())
        .limit(1)
    ).first()
    t_end = float(
        db.scalar(select(func.max(ThesisRunRound.t_end_s)).where(ThesisRunRound.run_id == run_id)) or 0.0
    )

    # Energy between events: rebuilt from each event's (E, on timer). Runs
    # recorded before the on timer was logged have no ``on_s``; their gaps are
    # left to the client as straight (unknown) lines.
    segments: list[list] = []
    exact = True
    anchor_t, anchor_e, anchor_on = None, None, None
    if first is not None:
        energy0 = np.frombuffer(first.energy_j, dtype=np.float32)
        codes0 = np.frombuffer(first.state_codes, dtype=np.uint8)
        if idx < energy0.size:
            anchor_t = float(first.sim_time_s)
            anchor_e = float(energy0[idx])
            anchor_on = p["T_on"] if int(codes0[idx]) != 0 else 0.0
    terminal = False
    for row in rows:
        if row.energy_j is None:
            continue
        if anchor_t is not None and not terminal and row.t_s > anchor_t:
            if anchor_on is None:
                exact = False
            else:
                _evolve(anchor_e, anchor_on, row.t_s - anchor_t, p, anchor_t, segments)
        on_s = (row.payload_json or {}).get("on_s")
        anchor_t, anchor_e = float(row.t_s), float(row.energy_j)
        anchor_on = float(on_s) if on_s is not None else None
        if row.event_type in ("identified", "dropped"):
            terminal = True
    if anchor_t is not None and not terminal and anchor_on is not None and t_end > anchor_t:
        _evolve(anchor_e, anchor_on, t_end - anchor_t, p, anchor_t, segments)

    return {
        "device_id": device_id,
        "scheme": run.scheme,
        "t_end": t_end,
        "consts": _consts_out(config),
        "energy": {"ecap": p["Ecap"], "eoff": p["Eoff"], "p_on": p["P_on"], "ph": p["Ph"], "t_on": p["T_on"]},
        "energy_exact": exact,
        "events": [_device_event_out(r) for r in rows],
        "rounds": rounds,
        "segments": segments,
        "truncated": len(segments) >= MAX_ENERGY_SEGMENTS,
    }
