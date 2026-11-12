"""Inventory termination rules.

A reader cannot see how many devices are still unidentified, so it has to
decide from its own frame history when to stop paging. Every rule here uses
only reader-side observations (frame times and the number of new IDs per
frame) plus, for ``energy_bound``, a worst-case recharge time derived from
the link budget. Rules are evaluated per reader after each of its frames; a
stopped reader pages no more, and the episode ends when every reader has
stopped or run out of devices.

The same pure functions drive the live engine and the offline replay
(:func:`replay`), so a rule can be scored on a completed ``oracle`` run
without re-simulating: a rule only reads past observations and does not
change the protocol before it fires.

Rules
-----
* ``oracle``        never stops early (the ideal reference: all devices served).
* ``quiet_rounds``  stop after ``n`` consecutive frames without a new ID.
* ``id_rate``       stop when the new-ID rate over a window (``window_mode``:
  ``rounds``, ``seconds`` or ``ewma``) falls below ``r_min`` IDs/s or below
  ``r_rel`` x the peak rate seen so far.
* ``energy_bound``  stop once no new ID arrived for the worst-case recharge
  time ``T_wc = (E_cap - E_off) / P_h,min + T_on`` (x ``1 + margin``): any
  device that failed must have recharged and been paged again by then.
* ``combined``      ``all`` or ``any`` of a list of sub-rules.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Iterable

RULE_KINDS = ("oracle", "quiet_rounds", "id_rate", "energy_bound", "combined")
WINDOW_MODES = ("rounds", "seconds", "ewma")


@dataclass(frozen=True)
class TerminationSpec:
    kind: str = "oracle"
    quiet_rounds: int = 10
    window_mode: str = "rounds"
    window: float = 20.0  # frames (rounds) or seconds (seconds); ignored by ewma
    ewma_alpha: float = 0.1
    r_min: float | None = None  # absolute floor, IDs per simulated second
    r_rel: float | None = 0.01  # fraction of the peak rate
    min_frames: int = 5  # id_rate: frames after the first ID before the rule may fire
    margin: float = 0.0  # energy_bound safety factor
    energy_source: str = "edge"  # edge: link-budget worst case; actual: true min harvested power
    combine: str = "all"  # combined: all | any
    rules: tuple["TerminationSpec", ...] = ()

    @classmethod
    def from_json(cls, raw: dict[str, Any] | None) -> "TerminationSpec":
        raw = dict(raw or {})
        kind = str(raw.get("kind", "oracle"))
        if kind not in RULE_KINDS:
            raise ValueError(f"unknown termination rule {kind!r}")
        mode = str(raw.get("window_mode", "rounds"))
        if mode not in WINDOW_MODES:
            raise ValueError(f"unknown window_mode {mode!r}")
        default = cls()

        def opt(name: str) -> float | None:
            v = raw.get(name, getattr(default, name))
            return None if v in (None, "") else float(v)

        return cls(
            kind=kind,
            quiet_rounds=max(1, int(raw.get("quiet_rounds", default.quiet_rounds))),
            window_mode=mode,
            window=max(1e-9, float(raw.get("window", default.window))),
            ewma_alpha=min(1.0, max(1e-6, float(raw.get("ewma_alpha", default.ewma_alpha)))),
            r_min=opt("r_min"),
            r_rel=opt("r_rel"),
            min_frames=max(0, int(raw.get("min_frames", default.min_frames))),
            margin=max(0.0, float(raw.get("margin", default.margin))),
            energy_source=str(raw.get("energy_source", default.energy_source)),
            combine=str(raw.get("combine", default.combine)),
            rules=tuple(cls.from_json(r) for r in raw.get("rules", ()) or ()),
        )

    def to_json(self) -> dict[str, Any]:
        out = {k: getattr(self, k) for k in (
            "kind", "quiet_rounds", "window_mode", "window", "ewma_alpha", "r_min", "r_rel",
            "min_frames", "margin", "energy_source", "combine",
        )}
        out["rules"] = [r.to_json() for r in self.rules]
        return out

    @property
    def is_oracle(self) -> bool:
        return self.kind == "oracle"

    def label(self) -> str:
        k = self.kind
        if k == "quiet_rounds":
            return f"quiet_rounds(n={self.quiet_rounds})"
        if k == "id_rate":
            thr = ", ".join(x for x in (
                None if self.r_min is None else f"r_min={self.r_min:g}",
                None if self.r_rel is None else f"r_rel={self.r_rel:g}",
            ) if x)
            win = f"alpha={self.ewma_alpha:g}" if self.window_mode == "ewma" else f"{self.window_mode}={self.window:g}"
            return f"id_rate({win}, {thr})"
        if k == "energy_bound":
            return f"energy_bound({self.energy_source}, margin={self.margin:g})"
        if k == "combined":
            return f"{self.combine}(" + ", ".join(r.label() for r in self.rules) + ")"
        return k


@dataclass
class TermState:
    """Per-reader running statistics the rules read (checkpointed)."""

    t_first: float | None = None  # start of the reader's first frame
    frames: int = 0
    frames_since_first_id: int = 0
    quiet: int = 0
    last_id_t: float | None = None
    ewma: float | None = None
    peak_rate: float = 0.0
    window: deque = field(default_factory=deque)  # (t_start, t_end, new_ids)
    stopped_reason: str | None = None
    stopped_t: float | None = None

    def to_json(self) -> dict[str, Any]:
        return {
            "t_first": self.t_first,
            "frames": self.frames,
            "frames_since_first_id": self.frames_since_first_id,
            "quiet": self.quiet,
            "last_id_t": self.last_id_t,
            "ewma": self.ewma,
            "peak_rate": self.peak_rate,
            "window": [list(x) for x in self.window],
            "stopped_reason": self.stopped_reason,
            "stopped_t": self.stopped_t,
        }

    @classmethod
    def from_json(cls, raw: dict[str, Any] | None) -> "TermState":
        raw = raw or {}
        st = cls(**{k: raw.get(k, getattr(cls(), k)) for k in (
            "t_first", "frames", "frames_since_first_id", "quiet", "last_id_t", "ewma", "peak_rate",
            "stopped_reason", "stopped_t",
        )})
        st.window = deque(tuple(x) for x in raw.get("window", []))
        return st


def _window_cap(spec: TerminationSpec) -> int:
    if spec.window_mode == "rounds":
        return max(1, int(round(spec.window)))
    return 0  # seconds: trimmed by time


def _all_specs(spec: TerminationSpec) -> Iterable[TerminationSpec]:
    yield spec
    for r in spec.rules:
        yield from _all_specs(r)


def window_rate(spec: TerminationSpec, st: TermState) -> float | None:
    if spec.window_mode == "ewma":
        return st.ewma
    if not st.window:
        return None
    t0 = st.window[0][0]
    t1 = st.window[-1][1]
    if spec.window_mode == "seconds":
        t0 = max(t0, t1 - spec.window)
    span = t1 - t0
    if span <= 0:
        return None
    return sum(n for _, _, n in st.window) / span


def observe(st: TermState, spec: TerminationSpec, t_start: float, t_end: float, new_ids: int) -> None:
    """Fold one frame into the reader's running statistics."""
    if st.t_first is None:
        st.t_first = t_start
    st.frames += 1
    if new_ids > 0:
        st.quiet = 0
        st.last_id_t = t_end
    else:
        st.quiet += 1
    if st.last_id_t is not None:
        st.frames_since_first_id += 1
    dt = max(1e-12, t_end - t_start)
    a = spec_ewma_alpha(spec)
    inst = new_ids / dt
    st.ewma = inst if st.ewma is None else a * inst + (1.0 - a) * st.ewma
    st.window.append((t_start, t_end, int(new_ids)))
    cap = max((_window_cap(s) for s in _all_specs(spec) if s.kind == "id_rate"), default=1)
    horizon = max((s.window for s in _all_specs(spec) if s.kind == "id_rate" and s.window_mode == "seconds"), default=0.0)
    if horizon > 0:
        while len(st.window) > 1 and st.window[1][1] <= t_end - horizon:
            st.window.popleft()
    else:
        while len(st.window) > cap:
            st.window.popleft()
    for s in _all_specs(spec):
        if s.kind == "id_rate":
            r = window_rate(s, st)
            if r is not None and st.last_id_t is not None:
                st.peak_rate = max(st.peak_rate, r)


def spec_ewma_alpha(spec: TerminationSpec) -> float:
    for s in _all_specs(spec):
        if s.kind == "id_rate" and s.window_mode == "ewma":
            return s.ewma_alpha
    return spec.ewma_alpha


def evaluate(spec: TerminationSpec, st: TermState, t_now: float, t_wc: float | None) -> str | None:
    """Return a stop reason, or None to keep paging."""
    k = spec.kind
    if k == "oracle":
        return None
    if k == "quiet_rounds":
        return "quiet_rounds" if st.quiet >= spec.quiet_rounds else None
    if k == "id_rate":
        if st.last_id_t is None:
            # Nothing identified yet: fall back to the quiet rule so an empty
            # reader does not page forever.
            return "id_rate_no_ids" if st.frames >= max(spec.min_frames, 1) * 4 else None
        if st.frames_since_first_id < spec.min_frames:
            return None
        rate = window_rate(spec, st)
        if rate is None:
            return None
        if spec.r_min is not None and rate < spec.r_min:
            return "id_rate"
        if spec.r_rel is not None and st.peak_rate > 0 and rate < spec.r_rel * st.peak_rate:
            return "id_rate"
        return None
    if k == "energy_bound":
        if t_wc is None or not math.isfinite(t_wc):
            return None
        ref = st.last_id_t if st.last_id_t is not None else (st.t_first or 0.0)
        return "energy_bound" if t_now - ref >= t_wc * (1.0 + spec.margin) else None
    if k == "combined":
        if not spec.rules:
            return None
        reasons = [evaluate(r, st, t_now, t_wc) for r in spec.rules]
        if spec.combine == "any":
            hit = [r for r in reasons if r]
            return "+".join(hit) if hit else None
        return "+".join(r for r in reasons if r) if all(reasons) else None
    raise ValueError(f"unknown termination rule {k!r}")


def _clone(st: TermState) -> TermState:
    return TermState.from_json(st.to_json())


def advance_empty(st: TermState, spec: TerminationSpec, n: int, t_start: float, frame_s: float) -> None:
    """Fold ``n`` consecutive frames of ``frame_s`` seconds without a new ID, in
    closed form (only the tail of the window that the rules can see is built)."""
    if n <= 0:
        return
    if st.t_first is None:
        st.t_first = t_start
    st.frames += n
    st.quiet += n
    if st.last_id_t is not None:
        st.frames_since_first_id += n
    a = spec_ewma_alpha(spec)
    if st.ewma is not None:
        st.ewma *= (1.0 - a) ** n
    else:
        st.ewma = 0.0
    cap = max((_window_cap(s) for s in _all_specs(spec) if s.kind == "id_rate"), default=1)
    horizon = max((s.window for s in _all_specs(spec) if s.kind == "id_rate" and s.window_mode == "seconds"), default=0.0)
    keep = cap if horizon <= 0 else int(math.ceil(horizon / max(frame_s, 1e-12))) + 2
    first = max(0, n - keep)
    for i in range(first, n):
        st.window.append((t_start + i * frame_s, t_start + (i + 1) * frame_s, 0))
    t_end = t_start + n * frame_s
    if horizon > 0:
        while len(st.window) > 1 and st.window[1][1] <= t_end - horizon:
            st.window.popleft()
    else:
        while len(st.window) > cap:
            st.window.popleft()


def empty_frames_to_stop(
    spec: TerminationSpec,
    st: TermState,
    t_now: float,
    frame_s: float,
    t_wc: float | None,
    *,
    max_frames: int = 10**9,
) -> tuple[int, str] | None:
    """Smallest ``n`` such that the rule fires after ``n`` more empty frames.

    Every rule is monotone in the number of trailing empty frames (quiet count
    and elapsed time grow, the ID rate does not), so an exponential then binary
    search over ``n`` is exact. None when it never fires within ``max_frames``.
    """
    if spec.is_oracle or frame_s <= 0:
        return None

    def fires(n: int) -> str | None:
        probe = _clone(st)
        advance_empty(probe, spec, n, t_now, frame_s)
        return evaluate(spec, probe, t_now + n * frame_s, t_wc)

    if fires(1) is not None:
        return 1, fires(1) or ""
    lo, hi = 1, 2
    while hi <= max_frames and fires(hi) is None:
        lo, hi = hi, hi * 2
    if hi > max_frames:
        if fires(max_frames) is None:
            return None
        hi = max_frames
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if fires(mid) is None:
            lo = mid
        else:
            hi = mid
    return hi, fires(hi) or ""


def worst_case_recharge_s(
    *,
    ecap: Iterable[float],
    eoff: Iterable[float],
    ph: Iterable[float],
    t_on: Iterable[float],
) -> float:
    """``max_i (E_cap,i - E_off,i) / P_h,i + T_on,i`` over the devices given."""
    best = 0.0
    for c, o, p, t in zip(ecap, eoff, ph, t_on):
        if p <= 0:
            return math.inf
        best = max(best, (c - o) / p + t)
    return best


# ------------------------------------------------------------------ offline replay


@dataclass
class ReplayOutcome:
    rule: str
    t_stop: float  # when the last reader stopped (or the run's end)
    reader_stop: dict[int, float]
    identified_before_stop: int
    identified_total: int
    missed: int
    t_last_id: float | None
    extra_time_s: float | None  # t_stop - t_last_id (negative = stopped before the last ID)
    t99: float | None
    extra_vs_t99_s: float | None


def replay(
    spec: TerminationSpec,
    rounds: list[dict[str, Any]],
    *,
    t_wc_by_reader: dict[int, float] | None = None,
    reachable: int | None = None,
    extrapolate: bool = True,
) -> ReplayOutcome:
    """Score ``spec`` on the round log of an ``oracle`` run.

    ``rounds`` need ``reader_id``, ``t_start_s``, ``t_end_s`` and ``served``
    (devices identified by that frame), ordered as the engine ran them.
    A device identified by a frame is credited if that frame ran before its
    reader stopped; the frame that triggers a stop still counts.

    An oracle run ends the moment the last device is identified, which no real
    reader can know. With ``extrapolate`` a reader whose rule has not fired by
    then keeps paging empty frames (the duration of its last frame without a
    new ID) until it does, exactly as the live engine fast-forwards it.
    """
    t_wc_by_reader = t_wc_by_reader or {}
    states: dict[int, TermState] = {}
    stop_at: dict[int, float] = {}
    last_end: dict[int, float] = {}
    empty_s: dict[int, float] = {}
    credited = 0
    total = 0
    id_times: list[float] = []
    t_end_run = 0.0
    for r in rounds:
        rid = int(r["reader_id"])
        served = int(r.get("served") or 0)
        t0, t1 = float(r["t_start_s"]), float(r["t_end_s"])
        total += served
        t_end_run = max(t_end_run, t1)
        if served:
            id_times.extend([t1] * served)
        if rid in stop_at:
            continue
        st = states.setdefault(rid, TermState())
        observe(st, spec, t0, t1, served)
        last_end[rid] = t1
        if served == 0 or rid not in empty_s:
            empty_s[rid] = t1 - t0
        credited += served
        reason = evaluate(spec, st, t1, t_wc_by_reader.get(rid))
        if reason:
            stop_at[rid] = t1
    for rid, st in states.items():
        if rid in stop_at:
            continue
        if extrapolate and not spec.is_oracle:
            hit = empty_frames_to_stop(spec, st, last_end[rid], empty_s.get(rid, 0.0), t_wc_by_reader.get(rid))
            stop_at[rid] = math.inf if hit is None else last_end[rid] + hit[0] * empty_s[rid]
        else:
            stop_at[rid] = t_end_run
    t_stop = max(stop_at.values()) if stop_at else 0.0
    id_times.sort()
    t_last = id_times[-1] if id_times else None
    n_ref = reachable if reachable is not None else total
    need = int(math.ceil(0.99 * n_ref)) if n_ref else 0
    t99 = id_times[need - 1] if need and len(id_times) >= need else None
    return ReplayOutcome(
        rule=spec.label(),
        t_stop=t_stop,
        reader_stop=stop_at,
        identified_before_stop=credited,
        identified_total=total,
        missed=total - credited,
        t_last_id=t_last,
        extra_time_s=None if t_last is None else t_stop - t_last,
        t99=t99,
        extra_vs_t99_s=None if t99 is None else t_stop - t99,
    )
