#!/usr/bin/env python3
"""Tail-device diagnosis for Figure 5(b) Device-1.

    python scripts/diagnose_fig5b_tail.py
    python scripts/diagnose_fig5b_tail.py --quick
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.config import STATE_NAME, paper_device1_config, results_dir
from simulator.fig5b_validation import evaluate_fig5b
from simulator.scenario import Scenario
from simulator.simulation import run_paper_comparison
from simulator.tail_diagnosis import classify_delay, reconstruct_transitions, remaining_census_at


def _percentile_ids(completion: np.ndarray, lo_pct: float, hi_pct: float) -> list[int]:
    done = np.isfinite(completion)
    if not np.any(done):
        return []
    ids = np.flatnonzero(done)
    times = completion[ids]
    lo = np.percentile(times, lo_pct)
    hi = np.percentile(times, hi_pct)
    pick = ids[(times >= lo) & (times <= hi)]
    order = np.argsort(completion[pick])
    return [int(i) for i in pick[order]]


def _strategy_tail(res, scenario: Scenario, cfg) -> dict:
    n = cfg.num_devices
    completion = np.array(
        [np.nan if s["completion_time_s"] is None else s["completion_time_s"] for s in res.device_stats]
    )
    tail_ids = _percentile_ids(completion, 95.0, 100.0)
    # Always include the T99 device and the slowest device.
    finite = completion[np.isfinite(completion)]
    extra = []
    if finite.size:
        extra.append(int(np.nanargmax(completion)))
        t99 = np.percentile(finite, 99)
        extra.extend(int(i) for i in np.flatnonzero(np.abs(completion - t99) < 1e-9)[:3])
    ids = []
    for i in list(tail_ids) + extra:
        if i not in ids:
            ids.append(i)

    bank = res.trace_bank
    devices = []
    for i in ids:
        st = res.device_stats[i]
        events = list(bank.events[i]) if bank is not None else []
        trans = []
        if bank is not None:
            trans = reconstruct_transitions(bank.state[i], bank.times_s)
        diag = classify_delay(
            st,
            float(scenario.pin_dbm[i]),
            float(scenario.peh_w[i]),
            events,
            st.get("initial_energy_nj"),
            e_low_nj=cfg.device.e_low_j * 1e9,
            e_up_nj=cfg.device.e_up_j * 1e9,
        )
        init_st = st.get("initial_state")
        devices.append({
            "device_id": i,
            "group_id": st.get("group"),
            "p_in_dbm": float(scenario.pin_dbm[i]),
            "P_eh_nw": float(scenario.peh_w[i] * 1e9),
            "inventory_t0_energy_nj": st.get("initial_energy_nj"),
            "inventory_t0_state": None if init_st is None else STATE_NAME.get(int(init_st), str(init_st)),
            "first_paging_time_s": st.get("first_paging_time_s"),
            "last_sync_time_s": st.get("last_sync_time_s"),
            "sync_count": st.get("sync_count"),
            "lost_sync_count": st.get("lost_sync_count"),
            "completion_time_s": st.get("completion_time_s"),
            "attempts": st.get("attempts"),
            "collisions": st.get("collisions"),
            "n_paging_eligible": st.get("n_paging_eligible"),
            "n_access_reject": st.get("n_access_reject"),
            "n_energy_fail": st.get("n_energy_fail"),
            "diagnosis": diag,
            "state_transitions": trans[:400],
            "events": events[:800],
        })
    reasons = [d["diagnosis"]["primary_delay"] for d in devices]
    return {
        "strategy": res.strategy,
        "label": res.label,
        "metrics": {
            "t50_s": res.metrics.get("t50_s"),
            "t90_s": res.metrics.get("t90_s"),
            "t95_s": res.metrics.get("t95_s"),
            "t99_s": res.metrics.get("t99_s"),
            "collision_rate": res.metrics.get("collision_rate"),
            "group_population": res.metrics.get("group_population"),
        },
        "n_tail": len(devices),
        "primary_delay_counts": {k: reasons.count(k) for k in sorted(set(reasons))},
        "devices": devices,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true", help="N=80, 4 s")
    p.add_argument("--seed", type=int, default=42)
    args = p.parse_args()
    if args.quick:
        cfg = paper_device1_config(
            num_devices=80, max_time_s=6.0, seed=args.seed,
            collect_snapshots=False, collect_paging_events=True,
        )
    else:
        cfg = paper_device1_config(
            collect_snapshots=False, collect_paging_events=True, seed=args.seed,
        )
    print(f"Diagnosing tails  N={cfg.num_devices} seed={cfg.seed} max_t={cfg.max_time_s}s")
    bundle = run_paper_comparison(cfg)
    scenario = bundle["scenario"]
    validation = evaluate_fig5b(bundle["results"], scenario.pin_dbm)
    out = {
        "seed": cfg.seed,
        "num_devices": cfg.num_devices,
        "assumptions": {
            "group_assignment": cfg.assumptions.group_assignment,
            "access_controller": cfg.assumptions.access_controller,
            "p_access_scope": cfg.assumptions.p_access_scope,
            "warmup_mode": cfg.assumptions.warmup_mode,
            "sleep_when_not_attempting": cfg.assumptions.sleep_when_not_attempting,
        },
        "validation": validation,
        "plateau_census": {},
        "strategies": {},
    }
    census_times = (3.0, 5.0, 10.0)
    for key, res in bundle["results"].items():
        out["strategies"][key] = _strategy_tail(res, scenario, cfg)
        censuses = [remaining_census_at(res, scenario, t, p_sl_w=cfg.device.p_sl_w) for t in census_times]
        out["plateau_census"][key] = [
            {k: v for k, v in c.items() if k != "devices"} | {"n_devices_listed": len(c["devices"])}
            for c in censuses
        ]
        # Keep per-device rows only for 4-group t=3s (the paper plateau).
        if key == "dcm_4_group":
            out["plateau_census"][key][0]["devices"] = censuses[0]["devices"]
        m = res.metrics
        print(f"\n{res.label}")
        print(f"  T50={m.get('t50_s')} T90={m.get('t90_s')} T95={m.get('t95_s')} T99={m.get('t99_s')}")
        tail = out["strategies"][key]
        print(f"  tail delay causes: {tail['primary_delay_counts']}")
        for c in censuses:
            sc = c["state_counts"]
            print(
                f"  t={c['t_s']:.0f}s remaining={c['n_remaining']} "
                f"(done {c['ratio_done_pct']:.1f}%)  "
                f"OFF={sc['OFF']} SLEEP={sc['SLEEP']} ON={sc['ON']} TX={sc['TX']}  "
                f"synced≈{c['n_synced_estimate']}  P_eh<P_sl={c['n_peh_below_psl']}  "
                f"coll≥3={c['n_repeat_collision_ge3']}"
            )
            if key == "dcm_4_group" and c["devices"]:
                pins = [d["p_in_dbm"] for d in c["devices"]]
                pehs = [d["P_eh_nw"] for d in c["devices"]]
                offs = [d["first_off_time_s"] for d in c["devices"] if d["first_off_time_s"] is not None]
                att = [d["attempts"] for d in c["devices"]]
                coll = [d["collisions"] for d in c["devices"]]
                print(
                    f"    remaining pin median={float(np.median(pins)):.2f} dBm  "
                    f"Peh median={float(np.median(pehs)):.1f} nW  "
                    f"first_OFF n={len(offs)} median={float(np.median(offs)) if offs else float('nan'):.2f}s  "
                    f"attempts mean={float(np.mean(att)):.1f}  collisions mean={float(np.mean(coll)):.1f}"
                )
        if key == "dcm_4_group" and tail["devices"]:
            last = tail["devices"][-1]
            print("  slowest 4-group device:")
            print(f"    id={last['device_id']} group={last['group_id']} "
                  f"pin={last['p_in_dbm']:.2f} dBm Peh={last['P_eh_nw']:.2f} nW")
            print(f"    t0 E={last['inventory_t0_energy_nj']} nJ state={last['inventory_t0_state']}")
            print(f"    first paging={last['first_paging_time_s']} done={last['completion_time_s']}")
            print(f"    {last['diagnosis']['why_late']}")

    dest = results_dir()
    dest.mkdir(parents=True, exist_ok=True)
    json_path = dest / "fig5b_tail_diagnosis.json"
    json_path.write_text(json.dumps(out, indent=2, default=str))
    csv_path = dest / "fig5b_tail_diagnosis.csv"
    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "strategy", "device_id", "group_id", "p_in_dbm", "P_eh_nw",
                "t0_energy_nj", "t0_state", "first_paging_s", "completion_s",
                "attempts", "collisions", "lost_sync", "primary_delay", "why_late",
            ],
        )
        w.writeheader()
        for key, block in out["strategies"].items():
            for d in block["devices"]:
                w.writerow({
                    "strategy": key,
                    "device_id": d["device_id"],
                    "group_id": d["group_id"],
                    "p_in_dbm": d["p_in_dbm"],
                    "P_eh_nw": d["P_eh_nw"],
                    "t0_energy_nj": d["inventory_t0_energy_nj"],
                    "t0_state": d["inventory_t0_state"],
                    "first_paging_s": d["first_paging_time_s"],
                    "completion_s": d["completion_time_s"],
                    "attempts": d["attempts"],
                    "collisions": d["collisions"],
                    "lost_sync": d["lost_sync_count"],
                    "primary_delay": d["diagnosis"]["primary_delay"],
                    "why_late": d["diagnosis"]["why_late"],
                })
    print(f"\nValidation: {validation['status']}")
    print(f"Saved {json_path}")
    print(f"Saved {csv_path}")
    plat_csv = dest / "fig5b_plateau_census.csv"
    with plat_csv.open("w", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "t_s", "device_id", "group_id", "state", "energy_nj", "p_in_dbm",
                "P_eh_nw", "peh_below_psl", "synced_estimate", "first_off_time_s",
                "attempts", "collisions", "n_access_reject", "completion_time_s",
            ],
        )
        w.writeheader()
        g4 = out["plateau_census"].get("dcm_4_group") or []
        if g4 and g4[0].get("devices"):
            for d in g4[0]["devices"]:
                w.writerow({"t_s": 3.0, **{k: d.get(k) for k in w.fieldnames if k != "t_s"}})
    print(f"Saved {plat_csv}")


if __name__ == "__main__":
    main()
