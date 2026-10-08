"""Payload builders for the aperiodic-paging API (engine side of the router)."""

import uuid
from dataclasses import asdict

import numpy as np

from app.aperiodic_simulator.core.batch import run_batch
from app.aperiodic_simulator.core.config import Assumptions, EpisodeConfig, SystemParams, config_to_dict
from app.aperiodic_simulator.physics.device_types import TYPE_NAMES, device_types
from app.aperiodic_simulator.physics.energy import compute_global_lmax, lmax_report
from app.aperiodic_simulator.physics.harvesting import harvest_below_sleep_stats
from app.aperiodic_simulator.physics.layout import bs_positions, reader_position
from app.aperiodic_simulator.analysis.metrics import CURVE_STEP_S, episode_curve
from app.aperiodic_simulator.runtime.run_store import put_run
from app.aperiodic_simulator.core.runner import default_controller, run_episode
from app.aperiodic_simulator.core.simulation import STATE_CODES
from app.aperiodic_simulator.core.states import ControllerName, RuntimeMode
from app.aperiodic_simulator.core.timing import (
    collision_time_equivalent_s,
    periodic_round_interval_s,
    success_time_equivalent_s,
    t_ei_s,
    t_msg1_s,
    t_msg2_s,
    t_msg3_s,
    t_page_s,
)

MAX_ROUND_ROWS = 3000
PAPER = {
    "title": "3GPP Ambient IoT Inventory with Aperiodic Paging",
    "authors": "Kota et al.",
    "pdf": "Papers/3GPP Ambient IoT Inventory with Aperiodic Paging.pdf",
}


def _np(o):
    if isinstance(o, dict):
        return {str(k): _np(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_np(v) for v in o]
    if isinstance(o, np.ndarray):
        return _np(o.tolist())
    if isinstance(o, np.floating):
        return None if not np.isfinite(o) else float(o)
    if isinstance(o, float):
        return None if not np.isfinite(o) else o
    if isinstance(o, np.integer):
        return int(o)
    return o


def about_payload() -> dict:
    return {
        "paper": PAPER,
        "engine": "aperiodic_simulator (continuous-time, one step = one CBRA round)",
        "protocols": ["aperiodic", "periodic"],
        "controllers": [c.value for c in ControllerName],
        "states": STATE_CODES,
        "stages": ["paging", "msg1", "EI", "msg2", "msg3"],
        "note": "Separate from the legacy periodic-paging simulator at /api/simulator.",
    }


def paper_config_payload() -> dict:
    s, a = SystemParams(), Assumptions()
    types = []
    for t in device_types(s):
        d = asdict(t)
        types.append(
            {
                "name": t.name,
                "rx_sensitivity_dbm": t.rx_sensitivity_dbm,
                "P_tx_uW": t.p_tx_w * 1e6,
                "P_rx_uW": t.p_rx_w * 1e6,
                "P_monitor_uW": t.p_wurx_w * 1e6,
                "monitor_receiver": "WuRX" if t.uses_wurx else "RX",
                "P_sl_uW": t.p_sl_w * 1e6,
                "E_up_uJ": t.e_up_j * 1e6,
                "E_low_uJ": t.e_low_j * 1e6,
                "uplink": d["uplink"],
                "backscatter_loss_db": t.backscatter_loss_db,
                "backscatter_gain_db": t.backscatter_gain_db,
                "active_tx_power_dbm": t.active_tx_power_dbm,
            }
        )
    return _np(
        {
            "paper": PAPER,
            "system": asdict(s),
            "device_types": types,
            "assumptions": asdict(a),
            "timing_ms": {
                "t_page": t_page_s(s) * 1e3,
                "t_msg1": t_msg1_s(s) * 1e3,
                "t_msg2": t_msg2_s(s) * 1e3,
                "t_msg3": t_msg3_s(s) * 1e3,
                "t_ei_L1": t_ei_s(1, system=s) * 1e3,
                "t_ei_L16": t_ei_s(16, system=s) * 1e3,
                "periodic_interval_L1": periodic_round_interval_s(1, s) * 1e3,
                "periodic_interval_L16": periodic_round_interval_s(16, s) * 1e3,
                "t_success_equiv": success_time_equivalent_s(s) * 1e3,
                "t_collision_equiv": collision_time_equivalent_s(s) * 1e3,
            },
            "lmax": lmax_report(s),
            "layout": {
                "factory_m": [s.factory_length_m, s.factory_width_m],
                "bs_xy": bs_positions(s),
                "reader_xy": reader_position(s, a),
                "reader_bs_index": a.reader_bs_index,
            },
        }
    )


PAPER_PANELS = {
    "fig5a": ("figure5", "a_L16_"),
    "fig5b": ("figure5", "b_L1_"),
    "fig6a": ("figure6", "a_L16_"),
    "fig6b": ("figure6", "b_L1_"),
    "fig7": ("figure7", ""),
}


def paper_reference_payload(panel_id: str) -> dict:
    """Digitized paper curves of one inventory-vs-time panel (overlay only)."""
    from app.aperiodic_simulator.analysis.reference_targets import DATA_DIR, reference_curve

    figure, prefix = PAPER_PANELS[panel_id]
    curves = {}
    for path in sorted((DATA_DIR / figure).glob(f"{prefix}*.csv")):
        name = path.stem[len(prefix):]
        ref = reference_curve(figure, path.stem)
        if ref is not None:
            curves[name] = {"x": ref[0], "y": ref[1]}
    return _np({"panel": panel_id, "figure": figure, "curves": curves})


def build_config(req) -> EpisodeConfig:
    system = SystemParams(
        F=req.F,
        capture_ratio_db=req.capture_ratio_db,
        missed_detection_rate=req.missed_detection_rate,
        false_alarm_rate=req.false_alarm_rate,
    )
    lmax = compute_global_lmax(system)
    if req.L_mode == "fixed" and req.L_fixed > lmax:
        raise ValueError(f"L_fixed={req.L_fixed} exceeds Lmax={lmax} for F={req.F}")
    interactive = req.runtime_mode == "interactive"
    return EpisodeConfig(
        n_tot=req.num_devices,
        seed=req.seed,
        harvesting_scenario=req.harvesting_scenario,
        paging_mode=req.paging_mode,
        controller=req.controller,
        L_fixed=req.L_fixed,
        L_initial=req.L_initial if req.L_mode == "adaptive" else None,
        p_initial=req.p_initial,
        N_g=req.N_g,
        enforce_midround_depletion=req.enforce_midround_depletion,
        alpha=req.alpha,
        t_max_s=req.max_time_s,
        runtime_mode=RuntimeMode.INTERACTIVE if interactive else RuntimeMode.PAPER_BATCH,
        type_mix=req.type_mix,
        n_trace_samples=req.n_trace_samples,
        snapshot_interval_s=req.snapshot_interval_s if interactive else 0.0,
        impairments_enabled=req.impairments_enabled,
        system=system,
    )


def _downsample(rows: list, limit: int) -> list:
    if len(rows) <= limit:
        return rows
    idx = np.unique(np.linspace(0, len(rows) - 1, limit).astype(int))
    return [rows[i] for i in idx]


def _round_rows(ep, ctrl_hist: list[dict]) -> list[dict]:
    rows = []
    if ep.rounds:
        for rec, h in zip(ep.rounds, ctrl_hist):
            S = rec.S_by_type
            rows.append(
                {
                    "round": rec.index,
                    "t_start_s": rec.t_start_s,
                    "t_end_s": rec.t_end_s,
                    "L": rec.L,
                    "p": rec.p,
                    "group": rec.group,
                    "S1": S["1"],
                    "S2a": S["2a"],
                    "S2b": S["2b"],
                    "idle": rec.idle_obs,
                    "collision": rec.collision_obs,
                    "success": rec.success_obs,
                    "C2": rec.C2,
                    "n_paged": rec.n_paged,
                    "n_participants": rec.n_participants,
                    "n_rejected": rec.n_rejected,
                    "k_decoded": rec.k_decoded,
                    "k_alloc": rec.k_alloc,
                    "k_served": rec.k_served,
                    "msg2_wasted": rec.msg2_wasted,
                    "reward": rec.reward,
                    "resource_efficiency": rec.S_total / rec.n_ao,
                    "n_done": rec.n_done_total,
                    "depleted": sum(rec.depletion_by_stage.values()),
                    **{k: v for k, v in h.items() if k in ("m", "q", "n_hat", "backlog_hat", "alpha_hat", "group")},
                }
            )
    else:
        for row, h in zip(ep.history, ctrl_hist):
            t0, t1, L, p, S, idle, coll, npart, reward, ndone, c2, kd, ka = row
            rows.append(
                {
                    "round": len(rows),
                    "t_start_s": t0,
                    "t_end_s": t1,
                    "L": L,
                    "p": p,
                    "S": S,
                    "idle": idle,
                    "collision": coll,
                    "n_participants": npart,
                    "reward": reward,
                    "n_done": ndone,
                    "C2": c2,
                    "k_decoded": kd,
                    "k_alloc": ka,
                    **{k: v for k, v in h.items() if k in ("m", "q", "n_hat", "backlog_hat")},
                }
            )
    return _downsample(rows, MAX_ROUND_ROWS)


def _population_payload(ep) -> dict:
    pop = ep.population
    return {
        "n_tot": pop.n_tot,
        "n_eff": pop.n_eff,
        "type_counts": pop.type_counts(),
        "type_shares": pop.type_shares(),
        "harvest_below_sleep": harvest_below_sleep_stats(pop, ep.system.p_sl_w),
        "p_harv_uW_quantiles": np.quantile(ep.p_harv * 1e6, [0.05, 0.25, 0.5, 0.75, 0.95]) if ep.n else [],
    }


def _device_sample(ep) -> list[dict]:
    ids = ep.snapshot_ids
    return [
        {
            "id": int(i),
            "x": float(ep.xy[i, 0]),
            "y": float(ep.xy[i, 1]),
            "type": TYPE_NAMES[int(ep.type_idx[i])],
            "p_harv_uW": float(ep.p_harv[i] * 1e6),
            "completion_s": float(ep.t_done[i]) if np.isfinite(ep.t_done[i]) else None,
            "group": int(ep.group[i]) if ep.group[i] >= 0 else None,
            "traced": int(i) in ep.trace.segments,
        }
        for i in ids
    ]


def _warnings(req, metrics: dict, ctrl) -> list[str]:
    w = []
    if metrics["final_ratio"] < 1.0:
        w.append(
            f"Episode ended at {metrics['sim_time_s']:.1f} s with {100 * metrics['final_ratio']:.2f}% inventoried "
            f"(time limit {req.max_time_s:.0f} s)."
        )
    if req.paging_mode == "aperiodic" and metrics["depletion_total"] > 0:
        w.append("Aperiodic run shows mid-round depletion: check L <= Lmax and the energy model.")
    meta = getattr(ctrl, "checkpoint_meta", None)
    if meta and meta.get("training_steps", 0) < 1_000_000:
        w.append(
            f"PPO checkpoint trained for {meta['training_steps']} steps (paper: 1,000,000); "
            "results are from an under-trained policy."
        )
    return w


def simulate(req, controller_factory=None) -> dict:
    cfg = build_config(req)
    run_id = uuid.uuid4().hex[:12]
    factory = controller_factory or default_controller
    if req.runtime_mode == "interactive":
        ctrl = factory(cfg)
        res = run_episode(cfg, controller=ctrl)
        ep = res.episode
        put_run(run_id, req.controller, ep)
        times, ratio = episode_curve(ep, max(ep.t, 1.0), 0.25 if ep.t < 300 else CURVE_STEP_S)
        payload = {
            "run_id": run_id,
            "runtime_mode": "interactive",
            "controller": req.controller,
            "checkpoint": getattr(ctrl, "checkpoint_meta", None),
            "config": config_to_dict(cfg),
            "population": _population_payload(ep),
            "metrics": res.metrics,
            "curve": {"times": times, "ratio": ratio},
            "rounds": _round_rows(ep, res.controller_history),
            "cbra_inspect": ep.cbra_inspect,
            "devices": _device_sample(ep),
            "snapshots": ep.snapshots,
            "state_codes": STATE_CODES,
            "traced_device_ids": ep.trace.ids,
            "warnings": _warnings(req, res.metrics, ctrl),
        }
        return _np(payload)
    br = run_batch(
        cfg,
        req.num_episodes,
        base_seed=req.seed,
        label=req.controller,
        keep_controller_traces=1,
        controller_factory=controller_factory,
    )
    agg = br.aggregate
    first = br.episodes[0]
    ctrl_meta = getattr(factory(cfg), "checkpoint_meta", None) if req.controller == "recurrent_ppo" else None
    payload = {
        "run_id": run_id,
        "runtime_mode": "paper_batch",
        "controller": req.controller,
        "checkpoint": ctrl_meta,
        "config": config_to_dict(cfg),
        "episodes": req.num_episodes,
        "seeds": [req.seed + i for i in range(req.num_episodes)],
        "metrics": first,
        "aggregate": {k: v for k, v in agg.items() if not k.startswith("curve_")},
        "curve": {
            "times": br.times[::4],
            "ratio": agg["curve_mean"][::4],
            "p05": agg["curve_p05"][::4],
            "p95": agg["curve_p95"][::4],
        },
        "rounds": _downsample(br.controller_traces[0], MAX_ROUND_ROWS) if br.controller_traces else [],
        "warnings": _warnings(req, first, None),
    }
    return _np(payload)
