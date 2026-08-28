"""Duty-cycled monitoring before and after first inventory paging."""

import numpy as np

from simulator.config import DONE, OFF, ON, SLEEP, SimConfig


def apply_dcm_pre_inventory(
    energy: np.ndarray,
    state: np.ndarray,
    on_remaining: np.ndarray,
    synced: np.ndarray,
    cfg: SimConfig,
) -> None:
    """Before first paging: ON for T_on_timer, then OFF even if e > E_low."""
    d = cfg.device
    active = (state != DONE) & (~synced)
    to_on = active & (state == OFF) & (energy >= d.e_up_j)
    if np.any(to_on):
        state[to_on] = ON
        on_remaining[to_on] = cfg.slots(d.t_on_timer_s)
    on_pre = active & (state == ON)
    if np.any(on_pre):
        on_remaining[on_pre] -= 1
        expired = on_pre & (on_remaining <= 0)
        state[expired] = OFF
        on_remaining[expired] = 0
    to_off_low = active & (state == ON) & (energy <= d.e_low_j)
    state[to_off_low] = OFF
    on_remaining[to_off_low] = 0


def expire_synced_on_window(
    state: np.ndarray,
    on_remaining: np.ndarray,
    synced: np.ndarray,
    inventoried: np.ndarray,
) -> np.ndarray:
    """After first paging: stay ON for T_on_DCM, then SLEEP. Returns expired mask."""
    on_post = synced & (~inventoried) & (state == ON)
    if not np.any(on_post):
        return np.zeros(state.shape, dtype=bool)
    on_remaining[on_post] -= 1
    expired = on_post & (on_remaining <= 0)
    state[expired] = SLEEP
    on_remaining[expired] = 0
    return expired


def return_to_sleep(
    state: np.ndarray,
    on_remaining: np.ndarray,
    mask: np.ndarray,
) -> None:
    """Leave RX/TX and keep the DCM sleep timer. OFF/DONE are left unchanged."""
    live = mask & (state != DONE) & (state != OFF)
    if not np.any(live):
        return
    state[live] = SLEEP
    on_remaining[live] = 0


def apply_elow(energy: np.ndarray, state: np.ndarray, cfg: SimConfig, synced: np.ndarray) -> np.ndarray:
    """Return mask of devices that just hit E_low (lose sync if configured)."""
    d = cfg.device
    hit = (state != DONE) & (state != OFF) & (energy <= d.e_low_j)
    state[hit] = OFF
    return hit


def roll_missed_wakes(
    wake_slot: np.ndarray,
    mask: np.ndarray,
    slot: int,
    period: int,
) -> None:
    """Push overdue wake_slot values to the next period after `slot`."""
    if period <= 0:
        return
    due = mask & (wake_slot >= 0) & (wake_slot < slot)
    if not np.any(due):
        return
    lag = slot - wake_slot[due]
    n_skip = lag // period + 1
    wake_slot[due] = wake_slot[due] + n_skip.astype(np.int32) * period


def recover_keep_sync_off(
    energy: np.ndarray,
    state: np.ndarray,
    on_remaining: np.ndarray,
    synced: np.ndarray,
    inventoried: np.ndarray,
    wake_slot: np.ndarray,
    slot: int,
    period: int,
    e_up_j: float,
    ton_slots: int,
) -> None:
    """OFF but still synced: harvest to E_up, then SLEEP until the next group epoch.

    Do not wake a depleted device into ON — that path produced thousands of
    collisions when off_clears_inventory_sync=False.
    """
    off_sync = synced & (~inventoried) & (state == OFF)
    if not np.any(off_sync):
        return
    roll_missed_wakes(wake_slot, off_sync, slot, period)
    ready = off_sync & (energy >= e_up_j)
    if not np.any(ready):
        return
    at_wake = ready & (wake_slot == slot)
    wait = ready & ~at_wake
    state[wait] = SLEEP
    if np.any(at_wake):
        state[at_wake] = ON
        on_remaining[at_wake] = ton_slots

