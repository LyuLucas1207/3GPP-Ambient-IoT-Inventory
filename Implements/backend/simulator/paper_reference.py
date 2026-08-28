"""Published Figure 5(b) reference overlay.

Pixel-digitized Device-1 curves live in backend/data/reference_fig5b/{em,dcm_1_group,dcm_4_group}.csv
(time_ms,ratio_pct). They are **not** invented: if the files are absent, the
overlay is omitted. Paper-stated T99 anchors (text, not a curve) are always
available.
"""

from pathlib import Path

import numpy as np

from simulator.config import data_dir
from simulator.metrics import mae_rmse


PAPER_STATED_T99_S = {
    "em": 20.0,
    "dcm_1_group": None,  # published: close to EM, no large gain
    "dcm_4_group": 10.0,
}

SOURCE_NOTE = (
    "IEEE published Figure 5(b), Device 1. T99 anchors are from the paper text "
    "(EM ≈ 20 s; DCM with grouping ≈ 10 s). Pixel-digitized curves are used only "
    "when CSV files exist under backend/data/reference_fig5b/. The arXiv 6-page "
    "preprint does not include a readable Device-1 three-strategy plot."
)


def reference_dir() -> Path:
    return data_dir() / "reference_fig5b"


def load_fig5b_reference() -> dict[str, dict]:
    root = reference_dir()
    out: dict[str, dict] = {}
    if not root.is_dir():
        return out
    for key in ("em", "dcm_1_group", "dcm_4_group"):
        path = root / f"{key}.csv"
        if not path.exists():
            continue
        data = np.loadtxt(path, delimiter=",", skiprows=1)
        if data.ndim == 1:
            data = data.reshape(1, -1)
        out[key] = {
            "time_ms": data[:, 0].astype(np.float64).tolist(),
            "ratio_pct": data[:, 1].astype(np.float64).tolist(),
            "file": path.name,
        }
    return out


def fig5b_reference_payload() -> dict:
    curves = load_fig5b_reference()
    return {
        "available": bool(curves),
        "source": SOURCE_NOTE,
        "paper_stated_t99_s": PAPER_STATED_T99_S,
        "curves": curves,
    }


def compare_curves(
    sim_t_ms: np.ndarray,
    sim_y: np.ndarray,
    ref_t_ms: np.ndarray,
    ref_y: np.ndarray,
    t99_s: float | None = None,
    paper_t99_s: float | None = None,
) -> dict:
    err = mae_rmse(sim_t_ms, sim_y, ref_t_ms, ref_y)
    if t99_s is not None and paper_t99_s is not None:
        err["t99_error_s"] = float(t99_s - paper_t99_s)
    else:
        err["t99_error_s"] = None
    return err
