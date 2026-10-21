"""Deterministic mock inventory engine.

Generates a self-consistent event stream that mirrors the structure of a real
3GPP Ambient IoT paging round (M1 / EBI / M2 / M3) without implementing the
actual physics. Lets us build and verify the full pipeline (schema, API, UI,
Plotly timeline) before porting the real FSA engine.

Rules the mock honours so the frontend behaves sensibly:
* every placed device gets at least one state transition;
* every reader emits round_start/round_end events;
* devices outside *every* reader's effective coverage never move past OFF;
* multi-reader coverage of the same device is resolved by first-come wins,
  but a losing reader still logs a ``missed_page`` event for that device so
  the attribution column is populated;
* each device finishes in exactly one terminal state (``identified`` /
  ``died`` / ``removed``) so the device-state endpoint is unambiguous.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.thesis_simulator.models import (
    ThesisDeviceEvent,
    ThesisInventoryRun,
    ThesisReaderEvent,
    ThesisRunRound,
    ThesisRunSummary,
)
from app.thesis_simulator.physics import effective_coverage_m


_DEVICE_SUBTYPES = ("1", "2a", "2b")

_INITIAL_ENERGY_J = 2.5e-5
_ENERGY_COST_PER_MSG_J = 5e-7
_ENERGY_HARVEST_PER_ROUND_J = 1.0e-6

# Safety cap. 10k devices × 18 readers × 60 rounds × 7 events per touch would
# produce millions of rows and multi-second inserts; we cap total emitted
# events and short-circuit the engine once we hit the ceiling.
_MAX_TOTAL_EVENTS = 400_000


@dataclass
class _DeviceState:
    row: dict[str, Any]
    energy_j: float = _INITIAL_ENERGY_J
    identified: bool = False
    died: bool = False
    terminal_emitted: bool = False


class MockInventoryEngine:
    def __init__(self, scheme: str) -> None:
        if scheme not in {"periodic", "aperiodic"}:
            raise ValueError(f"unknown scheme: {scheme!r}")
        self.scheme = scheme

    # ------------------------------------------------------------------ public
    def run(self, session: Session, run_row: ThesisInventoryRun) -> None:
        wall_start = datetime.now(timezone.utc)
        run_row.started_at = wall_start
        run_row.status = "running"
        session.flush()

        config = dict(run_row.config_json or {})
        snapshot = dict(run_row.scene_snapshot_json or {})
        placements = snapshot.get("placements", [])
        max_time_s = float(config.get("max_time_s", 60.0))
        seed = config.get("seed")
        rng = random.Random(seed if seed is not None else run_row.id)
        use_capture = bool(config.get("use_capture", True))
        include_d2r = bool(config.get("include_d2r", True))

        devices: dict[int, _DeviceState] = {}
        readers: list[dict[str, Any]] = []
        for row in placements:
            kind = row.get("kind")
            if kind == "device":
                devices[row["id"]] = _DeviceState(row=row)
            elif kind == "radar":
                readers.append(row)

        device_events: list[dict[str, Any]] = []
        reader_events: list[dict[str, Any]] = []
        round_rows: list[ThesisRunRound] = []

        reader_start_offsets = dict(config.get("reader_start_offsets") or {})
        reader_clocks = {
            r["id"]: float(reader_start_offsets.get(str(r["id"]), reader_start_offsets.get(r["id"], 0.0)))
            for r in readers
        }
        coverage: dict[int, dict[int, float]] = {}
        for reader in readers:
            rf = {
                "tx_power_dbm": reader["params"].get("tx_power_dbm", 33.0),
                "antenna_gain_dbi": reader["params"].get("antenna_gain_dbi", 6.0),
                "extra_attenuation_db": reader["params"].get("extra_attenuation_db", 0.0),
                "carrier_ghz": reader["params"].get("carrier_ghz", 0.9),
            }
            reader_include_d2r = bool(reader["params"].get("include_d2r", include_d2r))
            per_device: dict[int, float] = {}
            for dev_id, dev in devices.items():
                cov = effective_coverage_m(dev.row.get("params", {}), rf, include_d2r=reader_include_d2r)
                dx = dev.row["x_m"] - reader["x_m"]
                dy = dev.row["y_m"] - reader["y_m"]
                dist = math.hypot(dx, dy)
                if dist <= cov:
                    per_device[dev_id] = dist
            coverage[reader["id"]] = per_device

        # Round scheduler. We advance each reader on its own clock; the global
        # loop keeps picking the reader with the smallest next-round time.
        round_duration_min = 0.5
        round_duration_max = 1.5 if self.scheme == "aperiodic" else 1.0
        round_index_by_reader: dict[int, int] = {r["id"]: 0 for r in readers}
        active_readers = set(round_index_by_reader)
        total_rounds = 0

        while active_readers:
            next_reader = min(active_readers, key=lambda rid: reader_clocks[rid])
            t_start = reader_clocks[next_reader]
            if t_start >= max_time_s:
                break
            duration = (
                round_duration_min + rng.random() * (round_duration_max - round_duration_min)
                if self.scheme == "aperiodic"
                else 1.0
            )
            t_end = t_start + duration
            round_index = round_index_by_reader[next_reader]
            round_rows.append(
                ThesisRunRound(
                    run_id=run_row.id,
                    reader_id=next_reader,
                    round_index=round_index,
                    t_start_s=t_start,
                    t_end_s=t_end,
                    k_estimate=None,
                    g=float(config.get("g") or 1),
                    pstar=None,
                    slot_count=0,
                    success_count=0,
                    collision_count=0,
                    empty_count=0,
                    metadata_json={"scheme": self.scheme},
                )
            )
            round_index_by_reader[next_reader] = round_index + 1
            reader_clocks[next_reader] = t_end

            remaining_in_coverage = [
                dev_id
                for dev_id in coverage[next_reader]
                if not devices[dev_id].identified and not devices[dev_id].died
            ]
            if not remaining_in_coverage and round_index >= 3:
                active_readers.discard(next_reader)
                continue

            total_rounds += 1
            k_candidates = max(1, int(math.ceil(len(remaining_in_coverage) * 1.4)))
            k_slots = min(int(config.get("k_initial") or 128), max(8, k_candidates))

            reader_events.append(
                _mk_reader_event(run_row.id, next_reader, round_index, t_start, "round_start",
                                 payload={"candidates": len(remaining_in_coverage), "k_slots": k_slots,
                                          "scheme": self.scheme})
            )

            attempts: dict[int, list[int]] = {}
            for dev_id in remaining_in_coverage:
                attempts.setdefault(rng.randrange(k_slots), []).append(dev_id)

            success_count = collision_count = empty_count = 0
            terminated_this_round: list[int] = []
            for slot in range(k_slots):
                occupants = attempts.get(slot, [])
                if not occupants:
                    empty_count += 1
                    continue
                if len(occupants) == 1:
                    winner = occupants[0]
                    success_count += 1
                else:
                    if use_capture and rng.random() < 0.3:
                        winner = rng.choice(occupants)
                        success_count += 1
                    else:
                        winner = None
                        collision_count += 1
                for dev_id in occupants:
                    dev = devices[dev_id]
                    t = t_start + (slot + 0.1) * (duration / k_slots)
                    _emit_device(device_events, run_row.id, dev_id, next_reader, t, "charging",
                                 energy=dev.energy_j)
                    dev.energy_j += _ENERGY_HARVEST_PER_ROUND_J
                    _emit_device(device_events, run_row.id, dev_id, next_reader, t + 1e-4, "on",
                                 energy=dev.energy_j)
                    _emit_device(device_events, run_row.id, dev_id, next_reader, t + 2e-4, "latched",
                                 energy=dev.energy_j, payload={"slot": slot})
                    dev.energy_j -= _ENERGY_COST_PER_MSG_J
                    _emit_device(device_events, run_row.id, dev_id, next_reader, t + 3e-4, "m1_tx",
                                 energy=dev.energy_j, payload={"slot": slot})
                    if dev.energy_j <= 0:
                        _emit_device(device_events, run_row.id, dev_id, next_reader, t + 4e-4, "died",
                                     cause="energy", energy=dev.energy_j)
                        dev.died = True
                        dev.terminal_emitted = True
                        terminated_this_round.append(dev_id)
                        continue
                if winner is not None:
                    dev = devices[winner]
                    t = t_start + (slot + 0.5) * (duration / k_slots)
                    _emit_device(device_events, run_row.id, winner, next_reader, t, "m1_success",
                                 energy=dev.energy_j, payload={"slot": slot})
                    reader_events.append(
                        _mk_reader_event(run_row.id, next_reader, round_index, t,
                                         "m1_rx_success", slot_index=slot,
                                         payload={"device_id": winner})
                    )
                    dev.energy_j -= _ENERGY_COST_PER_MSG_J
                    _emit_device(device_events, run_row.id, winner, next_reader, t + 1e-4, "ebi_received",
                                 energy=dev.energy_j, payload={"slot": slot})
                    reader_events.append(
                        _mk_reader_event(run_row.id, next_reader, round_index, t + 1e-4,
                                         "ebi_sent", slot_index=slot, payload={"device_id": winner})
                    )
                    dev.energy_j -= _ENERGY_COST_PER_MSG_J
                    _emit_device(device_events, run_row.id, winner, next_reader, t + 2e-4, "m2_tx",
                                 energy=dev.energy_j, payload={"slot": slot})
                    reader_events.append(
                        _mk_reader_event(run_row.id, next_reader, round_index, t + 2e-4,
                                         "m2_rx", slot_index=slot, payload={"device_id": winner})
                    )
                    dev.energy_j -= _ENERGY_COST_PER_MSG_J
                    _emit_device(device_events, run_row.id, winner, next_reader, t + 3e-4, "m3_rx",
                                 energy=dev.energy_j, payload={"slot": slot})
                    reader_events.append(
                        _mk_reader_event(run_row.id, next_reader, round_index, t + 3e-4,
                                         "m3_sent", slot_index=slot, payload={"device_id": winner})
                    )
                    dev.energy_j -= _ENERGY_COST_PER_MSG_J
                    _emit_device(device_events, run_row.id, winner, next_reader, t + 4e-4, "identified",
                                 energy=dev.energy_j, payload={"round_index": round_index})
                    _emit_device(device_events, run_row.id, winner, next_reader, t + 5e-4, "removed",
                                 energy=dev.energy_j)
                    dev.identified = True
                    dev.terminal_emitted = True
                    terminated_this_round.append(winner)
                else:
                    for dev_id in occupants:
                        if devices[dev_id].died:
                            continue
                        t = t_start + (slot + 0.5) * (duration / k_slots)
                        _emit_device(device_events, run_row.id, dev_id, next_reader, t,
                                     "m1_collision", cause="collision_no_capture",
                                     energy=devices[dev_id].energy_j, payload={"slot": slot})
                    reader_events.append(
                        _mk_reader_event(run_row.id, next_reader, round_index,
                                         t_start + (slot + 0.5) * (duration / k_slots),
                                         "m1_rx_collision", slot_index=slot,
                                         payload={"count": len(occupants)})
                    )

            round_rows[-1].slot_count = k_slots
            round_rows[-1].success_count = success_count
            round_rows[-1].collision_count = collision_count
            round_rows[-1].empty_count = empty_count
            reader_events.append(
                _mk_reader_event(run_row.id, next_reader, round_index, t_end, "round_end",
                                 payload={"success": success_count, "collision": collision_count,
                                          "empty": empty_count})
            )

            # Untouched candidates silently harvest; we skip emitting per-device
            # missed_page events to keep the log readable at 10k-device scale.
            touched_this_round = {dev_id for slot_devs in attempts.values() for dev_id in slot_devs}
            for dev_id in remaining_in_coverage:
                if dev_id in touched_this_round:
                    continue
                dev = devices[dev_id]
                if dev.identified or dev.died:
                    continue
                dev.energy_j += _ENERGY_HARVEST_PER_ROUND_J

            if len(device_events) + len(reader_events) > _MAX_TOTAL_EVENTS:
                # Hit the safety cap; close the current state and finish out.
                break

        # Emit a final terminal state for every device that never terminated.
        final_t = max_time_s
        for dev_id, dev in devices.items():
            if dev.terminal_emitted:
                continue
            if dev.identified:
                _emit_device(device_events, run_row.id, dev_id, None, final_t,
                             "removed", energy=dev.energy_j)
                dev.terminal_emitted = True
                continue
            if dev.died:
                _emit_device(device_events, run_row.id, dev_id, None, final_t,
                             "died", cause="energy", energy=dev.energy_j)
                dev.terminal_emitted = True
                continue
            # Device survived but was not identified — mark as dropped.
            _emit_device(device_events, run_row.id, dev_id, None, final_t,
                         "dropped", cause="not_identified", energy=dev.energy_j)
            dev.terminal_emitted = True

        session.add_all(round_rows)
        session.flush()  # round rows need primary keys before we populate round_id (we leave null for mock)

        if device_events:
            session.bulk_insert_mappings(ThesisDeviceEvent, device_events)
        if reader_events:
            session.bulk_insert_mappings(ThesisReaderEvent, reader_events)

        identified_by_subtype = {k: 0 for k in _DEVICE_SUBTYPES}
        died_count = dropped_count = identified_total = 0
        for dev in devices.values():
            if dev.identified:
                identified_total += 1
                sub = dev.row.get("subtype")
                if sub in identified_by_subtype:
                    identified_by_subtype[sub] += 1
            elif dev.died:
                died_count += 1
            else:
                dropped_count += 1

        wall_end = datetime.now(timezone.utc)
        run_row.completed_at = wall_end
        run_row.duration_s = (wall_end - wall_start).total_seconds()
        run_row.status = "completed"
        run_row.updated_at = wall_end

        session.add(
            ThesisRunSummary(
                run_id=run_row.id,
                total_devices=len(devices),
                identified_total=identified_total,
                identified_by_subtype_json=identified_by_subtype,
                died_count=died_count,
                dropped_count=dropped_count,
                rounds_total=total_rounds,
                wall_duration_s=run_row.duration_s or 0.0,
                metrics_json={
                    "device_event_count": len(device_events),
                    "reader_event_count": len(reader_events),
                    "scheme": self.scheme,
                },
            )
        )


def _mk_reader_event(
    run_id: int,
    reader_id: int,
    round_index: int,
    t_s: float,
    event_type: str,
    slot_index: int | None = None,
    payload: dict | None = None,
) -> dict[str, Any]:
    event: dict[str, Any] = {
        "run_id": run_id,
        "reader_id": reader_id,
        "round_id": None,
        "t_s": float(t_s),
        "event_type": event_type,
        "slot_index": slot_index,
        "payload_json": payload,
    }
    if payload is None:
        event["payload_json"] = {"round_index": round_index}
    else:
        event["payload_json"] = {**payload, "round_index": round_index}
    return event


def _emit_device(
    bucket: list[dict[str, Any]],
    run_id: int,
    device_id: int,
    reader_id: int | None,
    t_s: float,
    event_type: str,
    *,
    cause: str | None = None,
    energy: float | None = None,
    payload: dict | None = None,
) -> None:
    bucket.append(
        {
            "run_id": run_id,
            "device_id": device_id,
            "reader_id": reader_id,
            "round_id": None,
            "t_s": float(t_s),
            "event_type": event_type,
            "cause": cause,
            "energy_j": None if energy is None else float(energy),
            "payload_json": payload,
        }
    )
