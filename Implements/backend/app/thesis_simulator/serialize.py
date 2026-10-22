"""Row -> dict converters shared by the REST endpoints and the SSE stream."""

from __future__ import annotations

from typing import Any

from app.thesis_simulator.models import ThesisRunRound


def round_out(row: ThesisRunRound) -> dict[str, Any]:
    return {
        "id": row.id,
        "frame_seq": row.frame_seq,
        "reader_id": row.reader_id,
        "round_index": row.round_index,
        "t_start_s": row.t_start_s,
        "t_end_s": row.t_end_s,
        "k_estimate": row.k_estimate,
        "g": row.g,
        "pstar": row.pstar,
        "slot_count": row.slot_count,
        "success_count": row.success_count,
        "collision_count": row.collision_count,
        "empty_count": row.empty_count,
        "candidates": row.candidates,
        "joiners": row.joiners,
        "on_at_page": row.on_at_page,
        "backlog_true": row.backlog_true,
        "served": row.served,
        "s_budget": row.s_budget,
        "budget_dropped": row.budget_dropped,
        "n_hat": row.n_hat,
        "mnot_prev": row.mnot_prev,
        "mnot_next": row.mnot_next,
        "n_done_total": row.n_done_total,
        "identified_by_subtype": row.identified_json,
        "timing": row.timing_json,
        "energy_j": row.energy_json,
        "deaths": row.deaths_json,
        "metadata": row.metadata_json,
    }


def round_slots_out(row: ThesisRunRound) -> dict[str, Any]:
    """The heavy per-slot payload, served on demand for the time-frequency map."""
    return {"id": row.id, "reader_id": row.reader_id, "round_index": row.round_index, "slots": row.slots_json}
