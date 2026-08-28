from uuid import uuid4

from fastapi import APIRouter, HTTPException

from app.schemas.simulation import SimulateRequest
from simulator.config import (
    device1_params,
    device2_params,
    paper_device1_config,
    strategy_label,
    validate_strategies,
)
from simulator.run_store import device_trace_payload, get_run, put_run
from simulator.paper_reference import fig5b_reference_payload
from simulator.simulation import result_to_web_payload, run_paper_comparison

router = APIRouter()


def _paper_payload() -> dict:
    cfg = paper_device1_config()
    d = cfg.device
    a = cfg.assumptions
    return {
        "num_devices": cfg.num_devices,
        "device_type": cfg.device_type,
        "seed": cfg.seed,
        "max_time_s": cfg.max_time_s,
        "dt_ms": cfg.dt_s * 1e3,
        "strategies": list(cfg.strategies),
        "paper_parameters": {
            "E_max_nJ": d.e_max_j * 1e9,
            "E_up_nJ": d.e_up_j * 1e9,
            "E_low_nJ": d.e_low_j * 1e9,
            "P_rx_uW": d.p_rx_w * 1e6,
            "P_tx_uW": d.p_tx_w * 1e6,
            "P_sl_uW": d.p_sl_w * 1e6,
            "paging_ms": d.paging_s * 1e3,
            "T_pg_ms": d.t_pg_s * 1e3,
            "Msg1_ms": d.msg1_s * 1e3,
            "Msg2_ms": d.msg2_s * 1e3,
            "Msg3_ms": d.msg3_s * 1e3,
            "T_on_DCM_ms": d.t_on_dcm_s * 1e3,
            "T_on_timer_ms": d.t_on_timer_s * 1e3,
            "n_time_ao": d.n_time_ao,
            "n_freq_ao": d.n_freq_ao,
            "n_ao": d.n_ao,
        },
        "reproduction_assumptions": {
            "pin_source": "Digitized Figure 5(a) CDF. Factory (x, y) is visualization only.",
            "warmup": (
                f"{a.warmup_mode}. explicit runs the ON/OFF machine for warmup_s from E_low; "
                "stationary is a closed-form cycle phase. They are not equivalent."
            ),
            "access_probability": (
                f"Controller `{a.access_controller}` (not specified by the paper). "
                "poisson_idle holds p when occupancy is energy-limited."
            ),
            "aperiodic_paging": "EM: earliest feasible paging after the previous CBRA ends.",
            "periodic_paging": "DCM: global epoch 0, T_pg, 2 T_pg, … .",
            "group_assignment": (
                "even_id_mod: preconfigured g = device_id % N_groups "
                "(reproduction assumption, not a published procedure)."
            ),
            "off_clears_sync": a.off_clears_inventory_sync,
        },
        "factory": {
            "length_m": a.factory_length_m,
            "width_m": a.factory_width_m,
            "reader_x_m": a.reader_x_m,
            "reader_y_m": a.reader_y_m,
        },
        "strategy_labels": {s: strategy_label(s) for s in cfg.strategies},
    }


@router.get("/config/paper")
def paper_config() -> dict:
    return _paper_payload()


@router.get("/config/fig5b-reference")
def fig5b_reference() -> dict:
    return fig5b_reference_payload()


@router.get("/about")
def about() -> dict:
    return {
        "title": "3GPP Ambient IoT Inventory Simulator",
        "paper": (
            "Fast Inventory for 3GPP Ambient IoT Considering "
            "Device Unavailability Due to Energy Harvesting"
        ),
        "target": "Figure 5(b), Device 1",
        "canonical_source": "published IEEE version",
        "arxiv": "2501.15020v1",
    }


@router.post("/simulate")
def simulate(req: SimulateRequest) -> dict:
    try:
        cfg = paper_device1_config(
            num_devices=req.num_devices,
            device_type=req.device_type,
            seed=req.seed,
            max_time_s=req.max_time_s,
            snapshot_interval_s=req.snapshot_interval_ms / 1000.0,
            collect_snapshots=req.collect_snapshots,
            collect_paging_events=req.collect_paging_events,
            strategies=tuple(req.strategies),
            device=device2_params() if req.device_type == 2 else device1_params(),
        )
        bundle = run_paper_comparison(cfg)
        run_id = str(uuid4())
        payload = result_to_web_payload(cfg, bundle, run_id=run_id)
        traces = {
            key: res.trace_bank
            for key, res in bundle["results"].items()
            if res.trace_bank is not None
        }
        put_run(
            run_id,
            payload,
            traces,
            {
                "seed": cfg.seed,
                "group_assignment": cfg.assumptions.group_assignment,
            },
        )
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/simulation/{run_id}/strategies/{strategy}/devices/{device_id}/trace")
def device_trace(run_id: str, strategy: str, device_id: int) -> dict:
    stored = get_run(run_id)
    if stored is None:
        raise HTTPException(
            status_code=404,
            detail="Unknown or expired run_id. Re-run the simulation.",
        )
    try:
        validate_strategies([strategy])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    bank = stored.traces.get(strategy)
    if bank is None:
        raise HTTPException(status_code=404, detail=f"No trace bank for {strategy}.")
    try:
        body = device_trace_payload(bank, device_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Device {device_id} not in this run.") from None
    body["run_id"] = run_id
    body["strategy"] = strategy
    body["seed"] = stored.payload.get("metadata", {}).get("seed")
    return body
