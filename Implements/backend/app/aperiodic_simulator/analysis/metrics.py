"""Episode and batch metrics for the aperiodic-paging paper (spec section 28)."""

import numpy as np

from app.aperiodic_simulator.physics.device_types import TYPE_NAMES
from app.common.metrics import first_time_at_or_above, inventory_curve

TARGETS = (50, 90, 95, 99)
CURVE_STEP_S = 0.5


def completion_times(ep) -> np.ndarray:
    return ep.t_done.copy()


def t_targets(t_done: np.ndarray, n: int, t_max: float, step: float = CURVE_STEP_S) -> dict[str, float | None]:
    times, ratio = inventory_curve(t_done, max(n, 1), t_max, step)
    return {f"T{q}": first_time_at_or_above(times, ratio, q) for q in TARGETS}


def exact_t_targets(t_done: np.ndarray, n: int) -> dict[str, float | None]:
    """Exact time at which q% of the eligible population is identified."""
    done = np.sort(t_done[np.isfinite(t_done)])
    out = {}
    for q in TARGETS:
        need = int(np.ceil(q / 100.0 * n - 1e-9))
        out[f"T{q}"] = float(done[need - 1]) if 0 < need <= done.size else None
    return out


def episode_metrics(ep) -> dict:
    h = np.asarray(ep.history, dtype=float) if ep.history else np.zeros((0, 13))
    n = ep.n
    t_done = ep.t_done
    n_done = int(np.isfinite(t_done).sum())
    total_ao = int(ep.total_ao)
    identified = n_done
    idle = int(h[:, 5].sum()) if h.size else 0
    coll = int(h[:, 6].sum()) if h.size else 0
    k_alloc = float(h[:, 12].sum()) if h.size else 0.0
    k_dec = float(h[:, 11].sum()) if h.size else 0.0
    per_type = {}
    for i, name in enumerate(TYPE_NAMES):
        m = ep.type_idx == i
        td = t_done[m]
        per_type[name] = {
            "n": int(m.sum()),
            "identified": int(np.isfinite(td).sum()),
            "mean_completion_s": float(np.mean(td[np.isfinite(td)])) if np.isfinite(td).any() else None,
            **exact_t_targets(td, int(m.sum())),
        }
    finite = t_done[np.isfinite(t_done)]
    return {
        "n_tot": ep.cfg.n_tot,
        "n_eff": n,
        "type_shares": ep.population.type_shares(),
        "identified": identified,
        "final_ratio": identified / n if n else 0.0,
        "sim_time_s": ep.t,
        "rounds": ep.r,
        **exact_t_targets(t_done, n),
        # Eq. (4): time to identify all N_eff devices (Tables V/VI); None if truncated.
        "T_total_s": float(finite.max()) if n and n_done == n else None,
        "mean_identification_time_s": float(finite.mean()) if finite.size and n_done == n else None,
        "mean_identification_time_partial_s": float(finite.mean()) if finite.size else None,
        "total_ao": total_ao,
        "ao_idle_obs": idle,
        "ao_collision_obs": coll,
        "ao_success_obs": total_ao - idle - coll,
        "msg2_allocated": k_alloc,
        "msg1_decoded": k_dec,
        "msg2_wasted": k_alloc - min(k_alloc, k_dec) if ep.protocol.periodic else 0.0,
        "resource_efficiency": identified / total_ao if total_ao else 0.0,
        "depletion_by_stage": dict(ep.depletion_totals),
        "depletion_total": int(sum(ep.depletion_totals.values())),
        "would_deplete_by_stage": dict(ep.would_deplete_totals),
        "interround_depletions": int(ep.interround_depletions),
        "msg1_success_lost_to_depletion": int(ep.msg1_success_lost),
        "group_populations": ep.group_populations(),
        "per_type": per_type,
        "energy_ledger_uJ": dict(ep.energy_ledger_uj),
        "mean_reward": float(h[:, 8].mean()) if h.size else 0.0,
    }


def episode_curve(ep, t_max: float, step: float = CURVE_STEP_S) -> tuple[np.ndarray, np.ndarray]:
    return inventory_curve(ep.t_done, max(ep.n, 1), t_max, step)


def aggregate(metrics: list[dict], curves: list[np.ndarray] | None = None) -> dict:
    """Mean / quantiles across episodes for scalar metrics."""
    keys = [
        "n_eff", "identified", "final_ratio", "sim_time_s", "rounds", "T50", "T90", "T95", "T99", "T_total_s",
        "mean_identification_time_s", "total_ao", "ao_idle_obs", "ao_collision_obs", "ao_success_obs",
        "msg2_allocated", "msg2_wasted", "resource_efficiency", "depletion_total", "interround_depletions",
    ]
    out: dict = {
        "episodes": len(metrics),
        "episodes_incomplete": sum(1 for m in metrics if m.get("T_total_s") is None),
    }
    for k in keys:
        vals = np.array([m[k] for m in metrics if m.get(k) is not None], dtype=float)
        if vals.size == 0:
            out[k] = None
            continue
        out[k] = {
            "mean": float(vals.mean()),
            "std": float(vals.std(ddof=1)) if vals.size > 1 else 0.0,
            "ci95": float(1.96 * vals.std(ddof=1) / np.sqrt(vals.size)) if vals.size > 1 else 0.0,
            "p05": float(np.quantile(vals, 0.05)),
            "p50": float(np.quantile(vals, 0.5)),
            "p95": float(np.quantile(vals, 0.95)),
            "n": int(vals.size),
        }
    for field in ("depletion_by_stage", "would_deplete_by_stage"):
        stages = metrics[0][field].keys() if metrics else []
        out[field] = {st: float(np.mean([m[field][st] for m in metrics])) for st in stages}
    gps = [m["group_populations"] for m in metrics if m.get("group_populations")]
    if gps:
        out["group_populations"] = {g: float(np.mean([x[g] for x in gps])) for g in gps[0]}
    if curves:
        arr = np.vstack(curves)
        out["curve_mean"] = arr.mean(axis=0)
        out["curve_p05"] = np.quantile(arr, 0.05, axis=0)
        out["curve_p95"] = np.quantile(arr, 0.95, axis=0)
    return out
