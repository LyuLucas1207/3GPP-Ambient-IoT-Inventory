"""In-memory last-N simulation runs for on-demand device traces."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import numpy as np

_MAX_RUNS = 3
_lock = Lock()
_runs: OrderedDict[str, "StoredRun"] = OrderedDict()


@dataclass
class DeviceTraceBank:
    dt_s: float
    times_s: np.ndarray
    energy_nj: np.ndarray
    state: np.ndarray
    phase: np.ndarray
    paging_index: np.ndarray
    time_ao: np.ndarray
    freq_ao: np.ndarray
    harvest_nw: np.ndarray
    completion_s: np.ndarray
    inventoried: np.ndarray
    events: list[list[dict]] = field(default_factory=list)
    p_rx_w: float = 1e-6
    p_tx_w: float = 1e-6
    p_sl_w: float = 0.1e-6
    e_up_nj: float = 500.0
    e_low_nj: float = 250.0
    simulation_dt_s: float = 0.5e-3


@dataclass
class StoredRun:
    run_id: str
    payload: dict
    traces: dict[str, DeviceTraceBank]
    cfg_meta: dict


def put_run(run_id: str, payload: dict, traces: dict[str, DeviceTraceBank], cfg_meta: dict) -> None:
    with _lock:
        _runs[run_id] = StoredRun(run_id, payload, traces, cfg_meta)
        while len(_runs) > _MAX_RUNS:
            _runs.popitem(last=False)


def get_run(run_id: str) -> StoredRun | None:
    with _lock:
        return _runs.get(run_id)


def device_trace_payload(bank: DeviceTraceBank, device_id: int) -> dict[str, Any]:
    n = int(bank.energy_nj.shape[0])
    if device_id < 0 or device_id >= n:
        raise KeyError(device_id)
    t = bank.times_s.tolist()
    energy = bank.energy_nj[device_id].tolist()
    state_i = bank.state[device_id]
    phase_i = bank.phase[device_id]
    names = ["OFF", "ON", "SLEEP", "TX", "DONE"]
    phases = ["idle", "paging", "msg1", "msg2", "msg3"]
    scientific = [names[int(s)] if 0 <= int(s) < len(names) else "OFF" for s in state_i]
    proto = [phases[int(p)] if 0 <= int(p) < len(phases) else "idle" for p in phase_i]
    peh = float(bank.harvest_nw[device_id])
    draw = []
    for s in state_i:
        s = int(s)
        if s == 0:  # OFF: harvest, no draw
            draw.append(0.0)
        elif s == 1:  # ON
            draw.append(bank.p_rx_w * 1e9)
        elif s == 2:  # SLEEP
            draw.append(bank.p_sl_w * 1e9)
        elif s == 3:  # TX
            draw.append(bank.p_tx_w * 1e9)
        else:
            draw.append(0.0)
    event_at = [""] * len(t)
    for ev in bank.events[device_id]:
        idx = int(ev.get("sample_index", -1))
        if 0 <= idx < len(event_at):
            event_at[idx] = str(ev.get("event", ""))
    done = bool(bank.inventoried[device_id])
    comp = bank.completion_s[device_id]
    return {
        "device_id": device_id,
        "dt_s": float(bank.dt_s),
        "time_s": t,
        "energy_nj": energy,
        "scientific_state": scientific,
        "protocol_phase": proto,
        "power_draw_nw": draw,
        "harvest_power_nw": peh,
        "paging_index": [int(v) for v in bank.paging_index[device_id]],
        "time_ao": [int(v) for v in bank.time_ao[device_id]],
        "freq_ao": [int(v) for v in bank.freq_ao[device_id]],
        "event": event_at,
        "events": bank.events[device_id],
        "inventoried": done,
        "completion_time_s": None if not np.isfinite(comp) else float(comp),
        "e_up_nj": float(bank.e_up_nj),
        "e_low_nj": float(bank.e_low_nj),
        "frozen_after_done": True,
        "simulation_dt_s": float(bank.simulation_dt_s),
        "source": (
            f"{bank.dt_s * 1e3:g} ms scientific trace (on-demand)"
        ),
    }
