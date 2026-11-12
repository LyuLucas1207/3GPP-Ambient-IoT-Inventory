"""Resource-sharing configuration for multiple readers.

Defaults follow 3GPP TR 38.769 V19.0.0 where it gives numbers:

* ``other_cw_suppression_db = 61``: digital-domain CW suppression reported
  for D1T1-A1/B (CW transmitted by other nodes), clause 6.7.5.2. The TR's
  summary (6.7.5.3) states CW cancellation is implementation specific, so
  this is a sweep parameter.
* ``d2r_sinr_db = 0.5``: the D2R SNR requirement already used for coverage
  (``physics.SNR_REQ_DB``), so a device inside coverage with no interference
  always passes and the ``independent`` mode is unchanged.
* ``conflict_distance_m = None`` (auto): two readers conflict when either one's
  CW, after ``other_cw_suppression_db``, reaches the other's self-interference
  floor, or when their coverage disks overlap. A fixed distance can be given
  instead. Clause 6.6 places the two active readers of D1T1-A2 at least 60 m
  apart and still multiplexes them (7.2.2), so distance alone is not a safe
  criterion.
* ``lbt_max_on_s = 4``, ``lbt_pause_s = 0.1``: ETSI EN 302 208 listen-before-talk
  dwell rule (at most 4 s of continuous transmission, then at least 100 ms
  silent), which keeps a busy neighbour from starving a waiting reader.
* ``r2d_sir_db = 6``: no TR value; OOK envelope-detector margin, swept.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

RESOURCE_MODES = ("independent", "shared", "fdma", "tdma", "hybrid", "lbt")


@dataclass(frozen=True)
class ResourceSpec:
    mode: str = "independent"
    interference: bool = True  # ignored (always off) in ``independent``
    cross_msg1: bool = True  # Msg1/Msg3 of other readers' devices interfere in the same subband
    conflict_distance_m: float | None = None  # None = link-budget conflict graph
    n_colors: int | None = None  # cap on colours; None = as many as greedy colouring needs
    tdma_window_s: float = 0.5
    freq_groups: int = 2  # hybrid: colours split over this many frequency groups
    lbt_backoff_s: float = 0.05
    lbt_max_on_s: float = 4.0
    lbt_pause_s: float = 0.1
    r2d_sir_db: float = 6.0
    d2r_sinr_db: float = 0.5
    other_cw_suppression_db: float = 61.0

    @classmethod
    def from_json(cls, raw: dict[str, Any] | None) -> "ResourceSpec":
        raw = dict(raw or {})
        mode = str(raw.get("mode", "independent"))
        if mode not in RESOURCE_MODES:
            raise ValueError(f"unknown resource mode {mode!r}")
        d = cls()
        n_colors = raw.get("n_colors")
        return cls(
            mode=mode,
            interference=bool(raw.get("interference", d.interference)),
            cross_msg1=bool(raw.get("cross_msg1", d.cross_msg1)),
            conflict_distance_m=None if raw.get("conflict_distance_m") in (None, "") else max(0.0, float(raw["conflict_distance_m"])),
            n_colors=None if n_colors in (None, "", 0) else max(1, int(n_colors)),
            tdma_window_s=max(1e-3, float(raw.get("tdma_window_s", d.tdma_window_s))),
            freq_groups=max(1, int(raw.get("freq_groups", d.freq_groups))),
            lbt_backoff_s=max(0.0, float(raw.get("lbt_backoff_s", d.lbt_backoff_s))),
            lbt_max_on_s=max(1e-3, float(raw.get("lbt_max_on_s", d.lbt_max_on_s))),
            lbt_pause_s=max(0.0, float(raw.get("lbt_pause_s", d.lbt_pause_s))),
            r2d_sir_db=float(raw.get("r2d_sir_db", d.r2d_sir_db)),
            d2r_sinr_db=float(raw.get("d2r_sinr_db", d.d2r_sinr_db)),
            other_cw_suppression_db=float(raw.get("other_cw_suppression_db", d.other_cw_suppression_db)),
        )

    def to_json(self) -> dict[str, Any]:
        return dict(self.__dict__)

    @property
    def is_independent(self) -> bool:
        return self.mode == "independent"

    @property
    def interference_on(self) -> bool:
        return not self.is_independent and self.interference
