"""Device population, coverage (N_eff) and RF energy harvesting.

Single-source: only the reader BS provides CW energy; devices with incident
power below -36 dBm are excluded (paper Sec. V-A2, following [19]).

Multi-source: all 18 BSs provide CW energy. Their incident powers are summed in
linear watts. The extra BSs are energy sources only; signaling and coverage
remain with the reader BS.

Harvested power uses the shared published efficiency model:
P_harv = xi(P_in) * P_in (``app.common.rf.harvest_power_w``).
"""

from dataclasses import dataclass

import numpy as np

from app.aperiodic_simulator.physics.channel import (
    distance_3d_m,
    incident_power_dbm,
    inf_dh_path_loss_db,
    uplink_rx_power_dbm,
)
from app.aperiodic_simulator.core.config import Assumptions, SystemParams
from app.aperiodic_simulator.physics.device_types import TYPE_NAMES, device_types
from app.aperiodic_simulator.physics.layout import bs_positions, reader_position, sample_device_positions
from app.aperiodic_simulator.core.states import HarvestingScenario
from app.common.rf import dbm_to_watts, harvest_power_w, watts_to_dbm


@dataclass
class Population:
    """All N_tot devices plus the eligible (N_eff) subset."""

    xy: np.ndarray
    type_idx: np.ndarray
    path_loss_db: np.ndarray
    pin_reader_dbm: np.ndarray
    pin_harvest_dbm: np.ndarray
    p_harv_w: np.ndarray
    p_ul_dbm: np.ndarray
    downlink_ok: np.ndarray
    uplink_ok: np.ndarray
    harvest_ok: np.ndarray
    eligible: np.ndarray
    scenario: HarvestingScenario

    @property
    def n_tot(self) -> int:
        return int(self.type_idx.size)

    @property
    def n_eff(self) -> int:
        return int(self.eligible.sum())

    def type_shares(self) -> dict[str, float]:
        t = self.type_idx[self.eligible]
        n = max(t.size, 1)
        return {name: float((t == i).sum() / n) for i, name in enumerate(TYPE_NAMES)}

    def type_counts(self) -> dict[str, int]:
        t = self.type_idx[self.eligible]
        return {name: int((t == i).sum()) for i, name in enumerate(TYPE_NAMES)}


def assign_types(
    n: int,
    rng: np.random.Generator,
    type_mix: str = "mixed",
    weights: tuple[float, float, float] | None = None,
) -> np.ndarray:
    """Even pre-coverage split for "mixed"; a single type for "1"/"2a"/"2b"."""
    if type_mix in TYPE_NAMES:
        return np.full(n, TYPE_NAMES.index(type_mix), dtype=np.int8)
    if weights is not None:
        w = np.asarray(weights, dtype=np.float64)
        counts = np.floor(n * w / w.sum()).astype(int)
    else:
        counts = np.full(3, n // 3)
    counts[: n - counts.sum()] += 1
    t = np.repeat(np.arange(3, dtype=np.int8), counts)
    rng.shuffle(t)
    return t


def incident_power_all_bs_dbm(xy: np.ndarray, system: SystemParams) -> np.ndarray:
    total_w = np.zeros(xy.shape[0])
    for bs in bs_positions(system):
        pl = inf_dh_path_loss_db(distance_3d_m(xy, bs, system), system.carrier_ghz)
        total_w += dbm_to_watts(incident_power_dbm(pl, system))
    return watts_to_dbm(total_w)


def build_population(
    n_tot: int,
    rng: np.random.Generator,
    scenario: HarvestingScenario,
    system: SystemParams | None = None,
    assumptions: Assumptions | None = None,
    type_mix: str = "mixed",
    type_weights: tuple[float, float, float] | None = None,
) -> Population:
    s = system or SystemParams()
    a = assumptions or Assumptions()
    xy = sample_device_positions(n_tot, rng, s)
    type_idx = assign_types(n_tot, rng, type_mix, type_weights)
    reader = reader_position(s, a)
    pl = inf_dh_path_loss_db(distance_3d_m(xy, reader, s), s.carrier_ghz)
    pin_reader = incident_power_dbm(pl, s)
    if scenario == HarvestingScenario.MULTI_SOURCE:
        pin_harvest = incident_power_all_bs_dbm(xy, s)
    else:
        pin_harvest = pin_reader.copy()
    p_harv = np.asarray(harvest_power_w(pin_harvest), dtype=np.float64)
    p_ul = uplink_rx_power_dbm(type_idx, pin_reader, pl, s, a)
    sens = np.array([t.rx_sensitivity_dbm for t in device_types(s)])[type_idx]
    downlink_ok = pin_reader >= sens
    uplink_ok = p_ul >= s.bs_rx_sensitivity_dbm
    if scenario == HarvestingScenario.SINGLE_SOURCE:
        harvest_ok = pin_harvest >= s.single_source_min_pin_dbm
    else:
        harvest_ok = np.ones(n_tot, dtype=bool)
    eligible = downlink_ok & uplink_ok & harvest_ok
    return Population(
        xy=xy,
        type_idx=type_idx,
        path_loss_db=pl,
        pin_reader_dbm=pin_reader,
        pin_harvest_dbm=pin_harvest,
        p_harv_w=p_harv,
        p_ul_dbm=p_ul,
        downlink_ok=downlink_ok,
        uplink_ok=uplink_ok,
        harvest_ok=harvest_ok,
        eligible=eligible,
        scenario=scenario,
    )


def incident_power_cdf(pop: Population, n_points: int = 200) -> dict:
    """Figure-4-style CDF of the harvesting incident power over the layout.

    Single-source: devices with P_in < -36 dBm are excluded (as in Fig. 4).
    """
    pin = pop.pin_harvest_dbm
    if pop.scenario == HarvestingScenario.SINGLE_SOURCE:
        pin = pin[pop.harvest_ok]
    pin = np.sort(pin)
    q = np.linspace(0.0, 1.0, n_points)
    return {
        "pin_dbm": np.quantile(pin, q).tolist(),
        "cdf": q.tolist(),
        "min_dbm": float(pin.min()),
        "max_dbm": float(pin.max()),
        "median_dbm": float(np.median(pin)),
    }


def harvest_below_sleep_stats(pop: Population, p_sl_w: float) -> dict:
    """Share of eligible devices with P_harv < P_sl and its type composition."""
    m = pop.eligible
    below = (pop.p_harv_w < p_sl_w) & m
    n_below = int(below.sum())
    t = pop.type_idx[below]
    type2 = int(((t == 1) | (t == 2)).sum())
    return {
        "share_of_n_eff": float(n_below / max(int(m.sum()), 1)),
        "type2_share_of_below": float(type2 / max(n_below, 1)),
        "count": n_below,
    }
