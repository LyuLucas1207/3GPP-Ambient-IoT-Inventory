"""Event buffer between the engine and PostgreSQL.

The engine stashes rounds and events here; :meth:`EventEmitter.flush`
persists everything buffered so far (rounds first, so events can carry
``round_id``) and returns the inserted round rows. The live runner flushes
every few hundred milliseconds, so the database closely mirrors the run
while the per-row cost stays low.

Events are kept as tuples in COPY column order and written with psycopg's
``Cursor.copy`` (PostgreSQL ``COPY ... FROM STDIN``): a 10k-device scene
emits tens of thousands of rows per simulated second, far beyond what
executemany ``INSERT`` sustains.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.thesis_simulator.models import ThesisRunRound

_DEVICE_COPY = (
    "COPY thesis_device_events "
    "(run_id, device_id, reader_id, round_id, t_s, event_type, cause, energy_j, payload_json, frame_seq) FROM STDIN"
)
_READER_COPY = (
    "COPY thesis_reader_events "
    "(run_id, reader_id, round_id, t_s, event_type, slot_index, payload_json, frame_seq) FROM STDIN"
)

# Buffered row layouts (round handle resolved to round_id at flush time):
#   device: (device_id, reader_id, handle, t_s, event_type, cause, energy_j, payload_json, frame_seq)
#   reader: (reader_id, handle, t_s, event_type, slot_index, payload_json, frame_seq)


class EventEmitter:
    def __init__(self, run_id: int) -> None:
        self.run_id = run_id
        self.frame_seq = 0  # stamped on every buffered row; set by the runner before each frame
        self._rounds: list[ThesisRunRound] = []
        self._device_events: list[tuple[Any, ...]] = []
        self._reader_events: list[tuple[Any, ...]] = []
        self.device_event_total = 0
        self.reader_event_total = 0
        self.round_total = 0

    # -------------------------------------------------- rounds
    def start_round(
        self,
        *,
        reader_id: int,
        round_index: int,
        t_start_s: float,
        t_end_s: float,
        k: int,
        g: float | None,
        pstar: float | None,
        slot_count: int,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        row = ThesisRunRound(
            run_id=self.run_id,
            reader_id=reader_id,
            round_index=round_index,
            t_start_s=float(t_start_s),
            t_end_s=float(t_end_s),
            k_estimate=None if k is None else float(k),
            g=g,
            pstar=pstar,
            slot_count=slot_count,
            success_count=0,
            collision_count=0,
            empty_count=0,
            metadata_json=metadata,
            frame_seq=self.frame_seq,
        )
        self._rounds.append(row)
        return len(self._rounds) - 1  # handle = index into the unflushed buffer

    def finish_round(
        self,
        handle: int,
        *,
        t_end_s: float,
        success: int,
        collision: int,
        empty: int,
        extra: dict[str, Any] | None = None,
    ) -> None:
        r = self._rounds[handle]
        r.t_end_s = float(t_end_s)
        r.success_count = int(success)
        r.collision_count = int(collision)
        r.empty_count = int(empty)
        for key, value in (extra or {}).items():
            setattr(r, key, value)

    # -------------------------------------------------- events
    def emit_device(
        self,
        *,
        device_id: int,
        reader_id: int | None,
        round_handle: int | None,
        t_s: float,
        event_type: str,
        cause: str | None = None,
        energy_j: float | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._device_events.append(
            (
                int(device_id),
                None if reader_id is None else int(reader_id),
                round_handle,
                float(t_s),
                event_type,
                cause,
                None if energy_j is None else float(energy_j),
                None if payload is None else json.dumps(payload),
                self.frame_seq,
            )
        )

    def emit_reader(
        self,
        *,
        reader_id: int,
        round_handle: int | None,
        t_s: float,
        event_type: str,
        slot_index: int | None = None,
        payload: dict[str, Any] | None = None,
    ) -> None:
        self._reader_events.append(
            (
                int(reader_id),
                round_handle,
                float(t_s),
                event_type,
                None if slot_index is None else int(slot_index),
                None if payload is None else json.dumps(payload),
                self.frame_seq,
            )
        )

    @property
    def pending_event_count(self) -> int:
        return len(self._device_events) + len(self._reader_events)

    @property
    def pending_round_count(self) -> int:
        return len(self._rounds)

    # -------------------------------------------------- persistence
    def flush(self, session: Session) -> list[ThesisRunRound]:
        """Insert every buffered round + event (no commit). Returns the round rows."""
        rounds = self._rounds
        if rounds:
            session.add_all(rounds)
            session.flush()
        ids = [r.id for r in rounds]
        run_id = self.run_id
        if self._device_events or self._reader_events:
            raw = session.connection().connection  # psycopg connection of this transaction
            with raw.cursor() as cur:
                if self._device_events:
                    with cur.copy(_DEVICE_COPY) as copy:
                        for dev, rid, h, t, et, cause, e, payload, seq in self._device_events:
                            copy.write_row((run_id, dev, rid, None if h is None else ids[h], t, et, cause, e, payload, seq))
                if self._reader_events:
                    with cur.copy(_READER_COPY) as copy:
                        for rid, h, t, et, slot, payload, seq in self._reader_events:
                            copy.write_row((run_id, rid, None if h is None else ids[h], t, et, slot, payload, seq))
        self.device_event_total += len(self._device_events)
        self.reader_event_total += len(self._reader_events)
        self.round_total += len(rounds)
        self.discard()
        return rounds

    def discard(self) -> None:
        """Drop the buffer (used by engine-only tests that skip the DB)."""
        self._rounds = []
        self._device_events = []
        self._reader_events = []
