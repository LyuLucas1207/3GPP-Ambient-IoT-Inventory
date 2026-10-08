"""Msg1 access-occasion (AO) resolution in three separate layers.

1. Physical occupancy: how many devices transmitted in each AO.
2. Physical resolution: a multi-occupied AO is captured when the strongest
   received Msg1 power is at least the capture ratio (6 dB) above the sum of
   the other powers in that AO (capture model of [44]).
3. Reader observation: an occupied AO is missed with probability 1% (observed
   idle, the device's Msg1 is lost); an idle AO raises a false alarm with
   probability 0.1% (observed as activity without a decodable RN16, i.e. a
   collision). Physical occupancy and reader observation are never merged.
"""

from dataclasses import dataclass

import numpy as np

from app.aperiodic_simulator.core.states import AOObserved, AOPhysical


@dataclass
class AOResolution:
    n_ao: int
    occupancy: np.ndarray  # devices per AO
    physical: np.ndarray  # AOPhysical per AO
    observed: np.ndarray  # AOObserved per AO
    winner: np.ndarray  # participant index decoded in the AO, or -1
    missed: np.ndarray  # bool per AO: occupied but missed by the reader
    false_alarm: np.ndarray  # bool per AO: idle but observed busy
    c2: int  # multi-occupied AOs involving a type 2a/2b device (ground truth)

    def observed_counts(self) -> dict[str, int]:
        return {
            "idle": int((self.observed == AOObserved.IDLE).sum()),
            "success": int((self.observed == AOObserved.SUCCESS).sum()),
            "collision": int((self.observed == AOObserved.COLLISION).sum()),
        }

    def physical_counts(self) -> dict[str, int]:
        return {
            "idle": int((self.physical == AOPhysical.IDLE).sum()),
            "single": int((self.physical == AOPhysical.SINGLE).sum()),
            "captured": int((self.physical == AOPhysical.CAPTURED).sum()),
            "collision": int((self.physical == AOPhysical.COLLISION).sum()),
        }


def resolve_aos(
    ao: np.ndarray,
    rx_power_w: np.ndarray,
    is_type2: np.ndarray,
    n_ao: int,
    rng: np.random.Generator,
    capture_ratio_db: float = 6.0,
    missed_detection_rate: float = 0.01,
    false_alarm_rate: float = 0.001,
    enabled: bool = True,
) -> AOResolution:
    """Resolve one Msg1 phase. ``ao``/``rx_power_w`` are per participant."""
    ao = np.asarray(ao, dtype=np.int64)
    occ = np.bincount(ao, minlength=n_ao)
    winner = np.full(n_ao, -1, dtype=np.int64)
    physical = np.full(n_ao, AOPhysical.IDLE, dtype=np.int8)
    if ao.size:
        order = np.lexsort((-rx_power_w, ao))
        ao_sorted = ao[order]
        first_ao, first_pos = np.unique(ao_sorted, return_index=True)
        strongest = order[first_pos]
        p_max = rx_power_w[strongest]
        p_sum = np.bincount(ao, weights=rx_power_w, minlength=n_ao)[first_ao]
        interference = p_sum - p_max
        n_in = occ[first_ao]
        ratio = 10.0 ** (capture_ratio_db / 10.0)
        if enabled:
            captured = (n_in >= 2) & (p_max >= ratio * interference)
        else:
            captured = np.zeros(n_in.size, dtype=bool)
        phys = np.where(n_in == 1, AOPhysical.SINGLE, np.where(captured, AOPhysical.CAPTURED, AOPhysical.COLLISION))
        physical[first_ao] = phys
        resolved = (n_in == 1) | captured
        winner[first_ao[resolved]] = strongest[resolved]
        t2 = np.bincount(ao, weights=is_type2.astype(np.float64), minlength=n_ao)
        c2 = int(((occ >= 2) & (t2 > 0)).sum())
    else:
        c2 = 0
    occupied = occ > 0
    if enabled:
        draws = rng.random(n_ao)
        missed = occupied & (draws < missed_detection_rate)
        false_alarm = (~occupied) & (draws < false_alarm_rate)
    else:
        missed = np.zeros(n_ao, dtype=bool)
        false_alarm = np.zeros(n_ao, dtype=bool)
    observed = np.full(n_ao, AOObserved.IDLE, dtype=np.int8)
    detected = occupied & ~missed
    decodable = (physical == AOPhysical.SINGLE) | (physical == AOPhysical.CAPTURED)
    observed[detected & decodable] = AOObserved.SUCCESS
    observed[detected & ~decodable] = AOObserved.COLLISION
    observed[false_alarm] = AOObserved.COLLISION
    winner[missed] = -1
    return AOResolution(
        n_ao=n_ao,
        occupancy=occ,
        physical=physical,
        observed=observed,
        winner=winner,
        missed=missed,
        false_alarm=false_alarm,
        c2=c2,
    )
