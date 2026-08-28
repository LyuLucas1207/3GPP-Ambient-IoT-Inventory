"""Scientific Figure 5(b) checks. No hard-coded single-seed T99 targets."""

from __future__ import annotations

import numpy as np

from simulator.channel import harvest_power_w
from simulator.config import Strategy
from simulator.paper_reference import PAPER_STATED_T99_S, compare_curves, load_fig5b_reference


def weakest_recharge_s(pin_dbm: np.ndarray, delta_e_j: float = 250e-9) -> dict:
    peh = np.asarray(harvest_power_w(pin_dbm), dtype=np.float64)
    t = delta_e_j / np.maximum(peh, 1e-30)
    return {
        "pin_min_dbm": float(np.min(pin_dbm)),
        "peh_min_nw": float(np.min(peh) * 1e9),
        "elow_to_eup_s_max": float(np.max(t)),
        "elow_to_eup_s_p99": float(np.percentile(t, 99)),
        "paper_example_s": 20.0,
        "close_to_20s": bool(np.max(t) > 15.0),
    }


def evaluate_fig5b(results: dict, pin_dbm: np.ndarray) -> dict:
    """Direction + tolerance checks. PASS requires the paper's qualitative order."""
    em = results.get(Strategy.EM.value)
    g1 = results.get(Strategy.DCM_1_GROUP.value)
    g4 = results.get(Strategy.DCM_4_GROUP.value)
    checks: list[dict] = []

    def t99(res) -> float | None:
        if res is None:
            return None
        return res.metrics.get("t99_s")

    t_em, t_1, t_4 = t99(em), t99(g1), t99(g4)
    reduction = None if (t_em is None or t_4 is None or t_em <= 0) else 1.0 - t_4 / t_em

    checks.append({
        "id": "t99_4_faster_than_em",
        "ok": t_em is not None and t_4 is not None and t_4 < t_em,
        "detail": {"t99_em_s": t_em, "t99_4_s": t_4},
    })
    # Paper: ~50% T99 cut vs EM. Band is around 50%, not 25–85%.
    # An 80% cut (T99 collapsing to T90) is not "near 50%".
    checks.append({
        "id": "t99_4_reduction_near_50pct",
        "ok": reduction is not None and 0.30 <= reduction <= 0.70,
        "detail": {"reduction": reduction, "band": [0.30, 0.70], "paper": 0.50},
    })
    # DCM 1-group must not be a clear win vs EM (paper: no material improvement).
    one_vs_em = None if (t_em is None or t_1 is None or t_em <= 0) else t_1 / t_em
    checks.append({
        "id": "dcm1_not_clearly_better_than_em",
        "ok": one_vs_em is None or one_vs_em >= 0.85,
        "detail": {"t99_1_over_em": one_vs_em},
    })
    recharge = weakest_recharge_s(pin_dbm)
    checks.append({
        "id": "weakest_harvester_charge_near_20s",
        "ok": recharge["close_to_20s"],
        "detail": recharge,
    })
    # Paper text: EM T99 ≈ 20 s, 4-group T99 ≈ 10 s. Not a fitted point,
    # but 2.9 s vs 10 s (or 14 s vs 20 s) must not silently pass.
    checks.append({
        "id": "t99_4_near_paper_10s",
        "ok": t_4 is not None and 6.0 <= t_4 <= 16.0,
        "detail": {"t99_4_s": t_4, "paper_s": 10.0, "band_s": [6.0, 16.0]},
    })
    checks.append({
        "id": "t99_em_near_paper_20s",
        "ok": t_em is not None and 12.0 <= t_em <= 28.0,
        "detail": {"t99_em_s": t_em, "paper_s": 20.0, "band_s": [12.0, 28.0]},
    })

    ref = load_fig5b_reference()
    curve_error = {}
    for key, res in results.items():
        if key not in ref:
            continue
        curve_error[key] = compare_curves(
            np.asarray(res.times_s) * 1e3,
            np.asarray(res.ratio_pct),
            np.asarray(ref[key]["time_ms"]),
            np.asarray(ref[key]["ratio_pct"]),
            t99_s=res.metrics.get("t99_s"),
            paper_t99_s=PAPER_STATED_T99_S.get(key),
        )
    if curve_error:
        # MAE is in inventory-ratio points. A failed reproduction often exceeds 25.
        maes = [v["mae"] for v in curve_error.values()]
        checks.append({
            "id": "digitized_mae_not_pathological",
            "ok": bool(maes) and float(np.mean(maes)) < 20.0,
            "detail": {"mae_mean": float(np.mean(maes)), "per_strategy": curve_error},
        })
        t4_err = curve_error.get("dcm_4_group", {}).get("t99_error_s")
        checks.append({
            "id": "t99_4_digitized_or_stated_error",
            "ok": t4_err is None or abs(float(t4_err)) <= 6.0,
            "detail": {"t99_error_s": t4_err, "max_abs_s": 6.0},
        })

    required = {
        "t99_4_faster_than_em",
        "t99_4_reduction_near_50pct",
        "dcm1_not_clearly_better_than_em",
        "weakest_harvester_charge_near_20s",
        "t99_4_near_paper_10s",
        "t99_em_near_paper_20s",
    }
    core = [c for c in checks if c["id"] in required]
    passed = all(c["ok"] for c in core)
    return {
        "pass": passed,
        "status": "PASS" if passed else "FAIL",
        "checks": checks,
        "t99_s": {"em": t_em, "dcm_1_group": t_1, "dcm_4_group": t_4},
        "reduction_4_vs_em": reduction,
        "curve_error": curve_error,
        "note": (
            "PASS requires the published qualitative order, not a single-seed "
            "T99 match. Reduction band is 30–70% around the paper's ~50%. "
            "4-group T99 must lie in [6, 16] s (paper ≈ 10 s); "
            "EM T99 in [12, 28] s (paper ≈ 20 s)."
        ),
    }
