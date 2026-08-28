"""Paging schedule helpers.

Periodic DCM uses a global epoch grid 0, T_pg, 2 T_pg, … rather than
pushing the next paging from the previous CBRA start. If a CBRA overruns
an epoch, that occasion is skipped.
"""

from simulator.config import SimConfig, is_periodic


def next_periodic_slot(current_slot: int, t_pg_slots: int) -> int:
    return current_slot + t_pg_slots


def next_periodic_epoch_slot(current_slot: int, t_pg_slots: int) -> int:
    """First epoch slot strictly after `current_slot`."""
    if t_pg_slots <= 0:
        return current_slot + 1
    return (current_slot // t_pg_slots + 1) * t_pg_slots


def is_periodic_epoch(slot: int, t_pg_slots: int) -> bool:
    return t_pg_slots > 0 and slot % t_pg_slots == 0


def next_aperiodic_slot(current_slot: int, cbra_duration_s: float, dt_s: float) -> int:
    extra = max(1, int(round(cbra_duration_s / dt_s)))
    return current_slot + extra


def advance_after_cbra(cfg: SimConfig, strategy: str, slot: int, duration_s: float) -> int:
    """Aperiodic: immediately after this CBRA. Periodic: next global epoch."""
    if is_periodic(strategy):
        return next_periodic_epoch_slot(slot, cfg.slots(cfg.device.t_pg_s))
    return slot + 1
