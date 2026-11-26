"""Reader coordination: resource grants, start-time rules and interference.

Policies (``ResourceSpec.mode``)
--------------------------------
* ``independent`` - the ideal reference: every reader has its own F subbands,
  no interference (the engine before coordination existed).
* ``shared``      - uncoordinated: every reader uses all F subbands whenever it
  wants; neighbours interfere.
* ``fdma``        - the conflict graph (readers closer than
  ``conflict_distance_m``) is coloured greedily (Welsh-Powell); the F subbands
  are split among colours, so a reader gets ``F_r = F / colours`` subbands.
* ``tdma``        - colours take turns: colour ``c`` may only start a frame
  inside window ``c`` of a superframe of ``colours x tdma_window_s``
  (Colorwave-style time colouring, centrally assigned).
* ``hybrid``      - colours are spread over ``freq_groups`` subband groups and
  the colours sharing a group take turns in time.
* ``lbt``         - listen-before-talk (ETSI EN 302 208 style): before a frame a
  reader senses its conflicting neighbours and defers, with a random backoff,
  while one of them is transmitting.

Interference model
------------------
The engine runs one reader frame at a time, earliest clock first. When reader
A starts a frame at ``t0`` every frame that started before ``t0`` is already
committed to the :class:`ActivityLedger`; readers whose clock falls inside A's
expected frame will start during it, and their activity is predicted from
their previous frame (paging then CW). The interference A sees is the sum of

* reader-to-device (R2D): other co-channel readers' transmissions at the
  device during A's paging and Msg2 (SIR test, ``r2d_sir_db``);
* reader-to-reader (D2R): other readers' modulated R2D at full power, or
  their CW reduced by ``other_cw_suppression_db``, at A's receiver during
  Msg1 / Msg3, plus (``cross_msg1``) Msg1/Msg3 of their devices in the same
  subband and time (SINR test, ``d2r_sinr_db`` over the reader's
  self-interference floor ``P_tx - cancel_depth``).

The earlier of two overlapping frames does not see the later one; this
one-sided view is the price of the sequential engine and is documented in
``Docs/THESIS_MULTI_READER_DESIGN.md``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

import numpy as np

from app.simulator_thesis import physics
from app.simulator_thesis.coordination.spec import ResourceSpec

if TYPE_CHECKING:
    from app.simulator_thesis.inventory.state import DeviceWorld, EpisodeConfig, ReaderState

R2D = 0
CW = 1
DEFAULT_FRAME_S = 0.25


def _db_to_lin(db: float) -> float:
    return 10.0 ** (db / 10.0)


def _dbm_to_w(dbm: np.ndarray | float) -> np.ndarray | float:
    return 10.0 ** ((np.asarray(dbm) - 30.0) / 10.0)


def _pl_nlos(d_m: np.ndarray, fc_ghz: float) -> np.ndarray:
    d = np.asarray(d_m, dtype=float) + 1e-3
    los = 31.84 + 21.5 * np.log10(d) + 19.0 * math.log10(fc_ghz)
    plus = 33.63 + 21.9 * np.log10(d) + 20.0 * math.log10(fc_ghz)
    return np.maximum(los, plus)


# ------------------------------------------------------------------ colouring


def conflict_graph(xy: np.ndarray, distance_m: float) -> np.ndarray:
    d = np.hypot(xy[:, None, 0] - xy[None, :, 0], xy[:, None, 1] - xy[None, :, 1])
    adj = d < distance_m
    np.fill_diagonal(adj, False)
    return adj


def greedy_coloring(adj: np.ndarray, cap: int | None = None) -> np.ndarray:
    """Welsh-Powell: highest degree first, smallest colour unused by neighbours.

    With ``cap`` colours, a node that cannot get a conflict-free colour takes
    the one used by the fewest of its neighbours.
    """
    n = adj.shape[0]
    colors = np.full(n, -1, dtype=int)
    order = sorted(range(n), key=lambda i: (-int(adj[i].sum()), i))
    for i in order:
        used = [colors[j] for j in np.nonzero(adj[i])[0] if colors[j] >= 0]
        limit = cap if cap is not None else n
        free = [c for c in range(limit) if c not in used]
        if free:
            colors[i] = free[0]
        else:
            counts = {c: used.count(c) for c in range(limit)}
            colors[i] = min(range(limit), key=lambda c: (counts[c], c))
    return colors


# ------------------------------------------------------------------ ledger


@dataclass
class Activity:
    """What one committed (or predicted) frame put on the air."""

    reader_idx: int
    subbands: frozenset[int]
    t0: float
    t1: float
    intervals: list[tuple[float, float, int]]  # (start, end, R2D | CW)
    # Device uplink transmissions (Msg1 / Msg3) of this frame.
    tx_t0: np.ndarray = field(default_factory=lambda: np.zeros(0))
    tx_t1: np.ndarray = field(default_factory=lambda: np.zeros(0))
    tx_sb: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=int))
    tx_dev: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=int))
    tx_prad_dbm: np.ndarray = field(default_factory=lambda: np.zeros(0))
    predicted: bool = False

    def to_json(self) -> dict[str, Any]:
        return {
            "reader_idx": self.reader_idx, "subbands": sorted(self.subbands), "t0": self.t0, "t1": self.t1,
            "intervals": [list(iv) for iv in self.intervals],
            "tx_t0": self.tx_t0.tolist(), "tx_t1": self.tx_t1.tolist(), "tx_sb": self.tx_sb.tolist(),
            "tx_dev": self.tx_dev.tolist(), "tx_prad_dbm": self.tx_prad_dbm.tolist(),
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any]) -> "Activity":
        return cls(
            reader_idx=int(raw["reader_idx"]), subbands=frozenset(int(s) for s in raw["subbands"]),
            t0=float(raw["t0"]), t1=float(raw["t1"]),
            intervals=[(float(a), float(b), int(k)) for a, b, k in raw["intervals"]],
            tx_t0=np.asarray(raw["tx_t0"], dtype=float), tx_t1=np.asarray(raw["tx_t1"], dtype=float),
            tx_sb=np.asarray(raw["tx_sb"], dtype=int), tx_dev=np.asarray(raw["tx_dev"], dtype=int),
            tx_prad_dbm=np.asarray(raw["tx_prad_dbm"], dtype=float),
        )


@dataclass
class FrameActivityBuilder:
    """Collected by ``run_one_frame`` and committed after the frame."""

    intervals: list[tuple[float, float, int]] = field(default_factory=list)
    tx: list[tuple[float, float, int, int]] = field(default_factory=list)  # t0, t1, subband, device

    def add(self, t0: float, t1: float, kind: int) -> None:
        if t1 > t0:
            self.intervals.append((t0, t1, kind))

    def add_tx(self, t0: float, t1: float, subband: int, dev: int) -> None:
        self.tx.append((t0, t1, subband, dev))


class FrameInterference:
    """Interference reader A sees during one frame (built by :meth:`Coordinator.context`)."""

    def __init__(self, coord: "Coordinator", a: int, activities: list[Activity]) -> None:
        self.coord = coord
        self.a = a
        self.acts = activities
        self.spec = coord.spec

    @property
    def empty(self) -> bool:
        return not self.acts

    def _overlap(self, act: Activity, t_a: float, t_b: float) -> int | None:
        """Strongest kind of ``act`` overlapping [t_a, t_b): R2D beats CW."""
        best = None
        for s, e, kind in act.intervals:
            if s < t_b and e > t_a:
                if kind == R2D:
                    return R2D
                best = CW
        return best

    def _kinds(self, t_a: float, t_b: float, match) -> dict[int, int]:
        """Strongest overlapping kind per interfering reader: a reader transmits one
        signal at a time, so its committed and predicted frames must not add up."""
        out: dict[int, int] = {}
        for act in self.acts:
            if not match(act):
                continue
            kind = self._overlap(act, t_a, t_b)
            if kind is None:
                continue
            prev = out.get(act.reader_idx)
            if prev is None or kind < prev:
                out[act.reader_idx] = kind
        return out

    def device_interference_w(self, devs: np.ndarray, t_a: float, t_b: float, subbands: frozenset[int]) -> np.ndarray:
        """Total power (W) other readers put on each device during [t_a, t_b)."""
        out = np.zeros(devs.size)
        if devs.size == 0:
            return out
        for b in self._kinds(t_a, t_b, lambda act: bool(act.subbands & subbands)):
            out += self.coord.pin_w[b][devs]
        return out

    def reader_interference_w(self, t_a: float, t_b: float, subband: int) -> float:
        """Total interference (W) at reader A's receiver in subband ``subband`` during [t_a, t_b)."""
        total = 0.0
        c = self.coord
        for b, kind in self._kinds(t_a, t_b, lambda act: subband in act.subbands).items():
            p = c.p_rr_w[b, self.a]
            total += p if kind == R2D else p * c.cw_supp_lin
        for act in self.acts:
            if subband not in act.subbands:
                continue
            if self.spec.cross_msg1 and act.tx_t0.size:
                hit = (act.tx_sb == subband) & (act.tx_t0 < t_b) & (act.tx_t1 > t_a)
                if hit.any():
                    devs = act.tx_dev[hit]
                    pl = _pl_nlos(c.d_dev_reader(devs, self.a), c.fc_ghz[self.a])
                    total += float(_dbm_to_w(act.tx_prad_dbm[hit] - pl).sum())
        return total


class Coordinator:
    def __init__(self, spec: ResourceSpec, readers: list["ReaderState"], world: "DeviceWorld", config: "EpisodeConfig") -> None:
        self.spec = spec
        self.readers = readers
        self.world = world
        self.F = max(1, int(config.consts.f_freq))
        self.index = {r.reader_id: i for i, r in enumerate(readers)}
        n = len(readers)
        self.xy = np.array([[r.x_m, r.y_m] for r in readers], dtype=float).reshape(n, 2)
        self.tx_dbm = np.array([float(r.rf.get("tx_power_dbm", physics.P_TX_CW_DBM)) for r in readers])
        self.gain_dbi = np.array([float(r.rf.get("antenna_gain_dbi", physics.G_TX_ANT_DBI)) for r in readers])
        self.extra_db = np.array([float(r.rf.get("extra_attenuation_db", 0.0)) for r in readers])
        self.fc_ghz = np.array([float(r.rf.get("carrier_ghz", physics.FC_GHZ)) for r in readers])
        # Reader b -> reader a received power (same mounting height: 3-D = horizontal distance).
        d_rr = np.hypot(self.xy[:, None, 0] - self.xy[None, :, 0], self.xy[:, None, 1] - self.xy[None, :, 1])
        self.d_rr = d_rr
        d_rr = np.maximum(d_rr, 1.0)
        pl_rr = np.stack([_pl_nlos(d_rr[b], self.fc_ghz[b]) for b in range(n)]) if n else np.zeros((0, 0))
        self.p_rr_w = _dbm_to_w((self.tx_dbm + self.gain_dbi)[:, None] - pl_rr) if n else np.zeros((0, 0))
        self.cw_supp_lin = _db_to_lin(-spec.other_cw_suppression_db)
        self.pin_w = [r.Ph_contrib for r in readers]
        # Reader self-interference floor after cancellation: SINR reference of the coverage model.
        self.floor_w = _dbm_to_w(self.tx_dbm - physics.CANCEL_DEPTH_DB)
        self.sinr_lin = _db_to_lin(spec.d2r_sinr_db)

        if spec.conflict_distance_m is not None:
            self.adj = conflict_graph(self.xy, spec.conflict_distance_m) if n else np.zeros((0, 0), dtype=bool)
        else:
            self.adj = self._link_budget_conflicts()
        if spec.mode in ("fdma", "tdma", "hybrid", "lbt") and n:
            self.colors = greedy_coloring(self.adj, spec.n_colors)
        else:
            self.colors = np.zeros(n, dtype=int)
        self.n_colors = int(self.colors.max()) + 1 if n else 0
        self._assign()
        self.sir_lin = _db_to_lin(spec.r2d_sir_db)
        self.ledger: list[Activity] = []
        # LBT dwell: reader index -> [burst start, end of last frame] of its continuous transmission.
        self.burst: dict[int, list[float]] = {}

    def _link_budget_conflicts(self) -> np.ndarray:
        """Readers conflict when one's suppressed CW reaches the other's floor
        (D2R) or their coverage disks overlap (R2D at shared devices)."""
        n = len(self.readers)
        if n == 0:
            return np.zeros((0, 0), dtype=bool)
        cw = self.p_rr_w * self.cw_supp_lin  # [b, a]
        d2r = (cw >= self.floor_w[None, :]) | (cw.T >= self.floor_w[:, None])
        radius = np.array([float(np.max(r.coverage_radius)) if r.coverage_radius is not None and r.coverage_radius.size else 0.0 for r in self.readers])
        r2d = self.d_rr < radius[:, None] + radius[None, :]
        adj = d2r | r2d
        np.fill_diagonal(adj, False)
        return adj

    # ---------------------------------------------------------- grants
    def _assign(self) -> None:
        F, mode = self.F, self.spec.mode
        for i, r in enumerate(self.readers):
            c = int(self.colors[i])
            r.color = c
            if mode == "fdma":
                groups = max(1, min(self.n_colors, F))
                sb = tuple(s for s in range(F) if s % groups == c % groups)
            elif mode == "hybrid":
                groups = max(1, min(self.spec.freq_groups, F))
                sb = tuple(s for s in range(F) if s % groups == c % groups)
            else:
                sb = tuple(range(F))
            r.subbands = sb

    def time_slot(self, i: int) -> tuple[int, int]:
        """(slot index, slots per superframe) for TDMA / hybrid."""
        c = int(self.colors[i])
        if self.spec.mode == "tdma":
            return c, max(1, self.n_colors)
        groups = max(1, min(self.spec.freq_groups, self.F))
        return c // groups, max(1, math.ceil(self.n_colors / groups))

    # ---------------------------------------------------------- start rules
    def next_start(self, reader: "ReaderState", t: float, rng: np.random.Generator) -> float:
        mode = self.spec.mode
        i = self.index[reader.reader_id]
        if mode in ("tdma", "hybrid"):
            slot, slots = self.time_slot(i)
            w = self.spec.tdma_window_s
            sf = slots * w
            phase = t % sf
            lo, hi = slot * w, (slot + 1) * w
            if lo <= phase < hi:
                return t
            base = t - phase
            nxt = base + lo if phase < lo else base + sf + lo
            return nxt
        if mode == "lbt":
            t_new = t
            burst = self.burst.get(i)
            if burst is not None and t - burst[1] <= 1e-9 and t - burst[0] >= self.spec.lbt_max_on_s:
                t_new = burst[1] + self.spec.lbt_pause_s
                self.burst.pop(i, None)
            for _ in range(64):
                busy_until = None
                for act in self.ledger:
                    j = act.reader_idx
                    if j == i or not self.adj[i, j] or not (act.subbands & frozenset(reader.subbands)):
                        continue
                    if act.t0 <= t_new < act.t1:
                        busy_until = act.t1 if busy_until is None else max(busy_until, act.t1)
                if busy_until is None:
                    return t_new
                t_new = busy_until + float(rng.uniform(0.0, self.spec.lbt_backoff_s))
            return t_new
        return t

    # ---------------------------------------------------------- interference
    def _expected_frame_s(self, r: "ReaderState") -> float:
        if r.history:
            h = r.history[-1]
            return max(1e-3, h.t_end - h.t_start)
        return DEFAULT_FRAME_S

    def _predicted_start(self, other: "ReaderState", b: int, a: int) -> float | None:
        """When reader ``b`` will start its next frame, as far as reader ``a``'s frame is concerned.

        Under LBT a conflicting neighbour senses ``a``'s frame and defers, so it
        never starts inside it; under TDMA / hybrid it waits for its window.
        """
        mode = self.spec.mode
        if mode == "lbt":
            return None if self.adj[a, b] else other.clock_s
        if mode in ("tdma", "hybrid"):
            return self.next_start(other, other.clock_s, None)
        return other.clock_s

    def context(self, reader: "ReaderState", t0: float, active: list["ReaderState"]) -> FrameInterference | None:
        if not self.spec.interference_on:
            return None
        a = self.index[reader.reader_id]
        horizon = t0 + 2.0 * self._expected_frame_s(reader)
        mine = frozenset(reader.subbands)
        acts = [act for act in self.ledger if act.reader_idx != a and act.t1 > t0 and act.t0 < horizon and act.subbands & mine]
        for other in active:
            b = self.index[other.reader_id]
            if b == a or other.stopped:
                continue
            c = self._predicted_start(other, b, a)
            if c is None or not (t0 <= c < horizon):
                continue
            sb = frozenset(other.subbands)
            if not (sb & mine):
                continue
            dur = self._expected_frame_s(other)
            t_pg = min(dur, 80.0 / 7000.0)
            acts.append(Activity(
                reader_idx=b, subbands=sb, t0=c, t1=c + dur,
                intervals=[(c, c + t_pg, R2D), (c + t_pg, c + dur, CW)], predicted=True,
            ))
        return FrameInterference(self, a, acts)

    def d_dev_reader(self, devs: np.ndarray, a: int) -> np.ndarray:
        w = self.world
        dx = w.x_m[devs] - self.xy[a, 0]
        dy = w.y_m[devs] - self.xy[a, 1]
        dz = physics.H_BS - physics.H_AIOT
        return np.sqrt(dx * dx + dy * dy + dz * dz)

    def d2r_rx_dbm(self, devs: np.ndarray, a: int) -> np.ndarray:
        """Absolute D2R power at reader ``a`` from its own devices (coverage-model link budget)."""
        pl = _pl_nlos(self.d_dev_reader(devs, a), self.fc_ghz[a])
        return self.prad_dbm(devs, a) - pl

    def prad_dbm(self, devs: np.ndarray, own: int) -> np.ndarray:
        """Device uplink power before the device-to-receiver path loss (dBm)."""
        w = self.world
        is_active = w.uplink_code[devs] == 1
        gbs = -w.backscatter_loss_db[devs] + w.backscatter_gain_db[devs]
        pl_own = _pl_nlos(self.d_dev_reader(devs, own), self.fc_ghz[own])
        backscatter = self.tx_dbm[own] + gbs - physics.FIXED_DEV_DB - self.extra_db[own] - pl_own
        active = np.nan_to_num(w.active_tx_power_dbm[devs], nan=-200.0) - physics.FIXED_DEV_DB - self.extra_db[own]
        return np.where(is_active, active, backscatter)

    def sinr_db(self, signal_dbm: np.ndarray, interference_w: np.ndarray | float, a: int) -> np.ndarray:
        noise = self.floor_w[a] + np.asarray(interference_w)
        return np.asarray(signal_dbm) - 10.0 * np.log10(noise * 1e3)

    def commit(self, reader: "ReaderState", t0: float, t1: float, built: FrameActivityBuilder) -> None:
        if not self.spec.interference_on and self.spec.mode != "lbt":
            return
        a = self.index[reader.reader_id]
        burst = self.burst.get(a)
        if burst is not None and t0 - burst[1] <= 1e-9:
            burst[1] = t1
        else:
            self.burst[a] = [t0, t1]
        if built.tx:
            arr = np.array(built.tx, dtype=float)
            devs = arr[:, 3].astype(int)
            act = Activity(
                reader_idx=a, subbands=frozenset(reader.subbands), t0=t0, t1=t1, intervals=list(built.intervals),
                tx_t0=arr[:, 0], tx_t1=arr[:, 1], tx_sb=arr[:, 2].astype(int), tx_dev=devs,
                tx_prad_dbm=self.prad_dbm(devs, a),
            )
        else:
            act = Activity(reader_idx=a, subbands=frozenset(reader.subbands), t0=t0, t1=t1, intervals=list(built.intervals))
        self.ledger.append(act)

    def prune(self, t_min: float) -> None:
        if self.ledger:
            self.ledger = [act for act in self.ledger if act.t1 > t_min]

    # ---------------------------------------------------------- reporting
    def summary(self) -> dict[str, Any]:
        return {
            "mode": self.spec.mode,
            "n_colors": int(self.n_colors),
            "readers": {
                int(r.reader_id): {
                    "color": int(r.color),
                    "subbands": list(r.subbands),
                    "time_slot": list(self.time_slot(i)) if self.spec.mode in ("tdma", "hybrid") else None,
                    "neighbors": [int(self.readers[j].reader_id) for j in np.nonzero(self.adj[i])[0]],
                }
                for i, r in enumerate(self.readers)
            },
        }
