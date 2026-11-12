"""Framed ALOHA + capture-effect receiver.

Thin, deterministic port of ``Sources/.../grouping_logic.py``'s
``simulate_frame_latched_enrolled`` (lines 104-240). We only keep the
behaviour the paper actually needs: K slots per frame, uniform random slot
pick per joiner, max-power pick with CAPTURE_F ratio, plus the energy-
detector false-alarm / miss-detect toggle. The function is pure — it only
reads/writes the arrays passed in, no module globals.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from app.thesis_simulator.inventory.config import CONSTANTS, EngineConstants


@dataclass
class AlohaResult:
    """Per-slot outcome of one framed-ALOHA phase.

    ``slot_of_device`` maps joiner-index (in the input order) to its chosen
    slot [0..K). Devices that collided and did NOT win capture are still
    recorded; the caller distinguishes winners via ``winners`` membership.
    ``rx_power_dbm_per_slot`` keeps the strongest device's received power in
    each slot (useful for the reader-event payload).
    """

    k: int
    slot_of_device: np.ndarray  # shape (J,), int, in [0, K)
    winners: np.ndarray  # bool shape (J,); True = this joiner won capture
    successes: int = 0
    collisions: int = 0
    empties: int = 0
    singletons: int = 0  # physical singleton slots (collisions is multi-device)
    rx_power_dbm_per_slot: np.ndarray = field(default_factory=lambda: np.array([]))
    occupancy: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.int32))
    slot_result: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.uint8))


# Per-slot physical outcome codes (``AlohaResult.slot_result``).
SLOT_IDLE = 0
SLOT_SINGLE = 1
SLOT_CAPTURED = 2
SLOT_COLLISION = 3
SLOT_MISSED = 4  # singleton lost to the energy detector (miss-detect)
SLOT_INTERFERED = 5  # inter-reader interference pushed the slot below the D2R SINR target


def draw_slots(rng: np.random.Generator, k: int, j: int) -> np.ndarray:
    """Uniform Msg1 resource pick of ``j`` joiners (the frame's first random draw)."""
    return rng.integers(0, max(1, k), size=j, dtype=np.int64)


def simulate_frame(
    *,
    joiner_indices: np.ndarray,
    rx_power_dbm: np.ndarray,
    k: int,
    use_capture: bool,
    use_energy_detect: bool,
    rng: np.random.Generator,
    consts: EngineConstants = CONSTANTS,
    decodable: np.ndarray | None = None,
    slots: np.ndarray | None = None,
) -> AlohaResult:
    """Simulate one M1 frame.

    Parameters
    ----------
    joiner_indices: device indices (as integers into the DeviceWorld arrays)
        that actually transmit in this frame. Length J.
    rx_power_dbm: per-joiner received power at the reader (dBm). Length J.
    k: slot count.
    use_capture: enable capture-effect decoding.
    use_energy_detect: apply false-alarm / miss-detect gating per slot.
    rng: numpy Generator (seeded).
    decodable: per-joiner D2R SINR verdict under inter-reader interference.
        An undecodable singleton looks empty to the reader; in a multi-device
        slot only a decodable device can win capture. ``None`` = all decodable.
    """
    j = len(joiner_indices)
    slot = draw_slots(rng, k, j) if slots is None else np.asarray(slots, dtype=np.int64)
    winners = np.zeros(j, dtype=bool)
    rx_power_per_slot = np.full(k, -np.inf)
    occupancy = np.bincount(slot, minlength=k).astype(np.int32) if j else np.zeros(k, dtype=np.int32)
    slot_result = np.zeros(k, dtype=np.uint8)

    # Group joiners by slot
    successes = collisions = empties = singletons = 0
    for s in range(k):
        in_slot = np.where(slot == s)[0]
        if in_slot.size == 0:
            empties += 1
            # energy-detector false alarm converts empty -> apparent singleton that fails later
            if use_energy_detect and rng.random() < consts.p_fa:
                # The paper treats this as a "noise burst"; no decode. Keep as empty for stats.
                pass
            continue
        if in_slot.size == 1:
            singletons += 1
            if decodable is not None and not decodable[in_slot[0]]:
                empties += 1
                slot_result[s] = SLOT_INTERFERED
                continue
            if use_energy_detect and rng.random() < consts.p_md:
                collisions += 1
                slot_result[s] = SLOT_MISSED
                continue
            slot_result[s] = SLOT_SINGLE
            winners[in_slot[0]] = True
            rx_power_per_slot[s] = rx_power_dbm[in_slot[0]]
            successes += 1
            continue
        # Multiple devices in slot
        powers = rx_power_dbm[in_slot]
        rx_power_per_slot[s] = float(np.max(powers))
        if not use_capture:
            collisions += 1
            slot_result[s] = SLOT_COLLISION
            continue
        # Capture: strongest wins if it dominates runners-up by at least 6 dB
        max_idx = int(np.argmax(powers))
        max_p = float(powers[max_idx])
        others = np.concatenate([powers[:max_idx], powers[max_idx + 1:]])
        max_other = float(np.max(others))
        strongest_ok = decodable is None or bool(decodable[in_slot[max_idx]])
        # Lin domain: max_p_lin >= CAPTURE_F * max_other_lin
        if strongest_ok and max_p - max_other >= 10.0 * np.log10(consts.capture_f_lin):
            winners[in_slot[max_idx]] = True
            successes += 1
            slot_result[s] = SLOT_CAPTURED
        else:
            collisions += 1
            slot_result[s] = SLOT_COLLISION

    return AlohaResult(
        k=k,
        slot_of_device=slot,
        winners=winners,
        successes=successes,
        collisions=collisions,
        empties=empties,
        singletons=singletons,
        rx_power_dbm_per_slot=rx_power_per_slot,
        occupancy=occupancy,
        slot_result=slot_result,
    )
