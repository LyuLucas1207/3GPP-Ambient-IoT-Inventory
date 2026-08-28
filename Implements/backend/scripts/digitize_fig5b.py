#!/usr/bin/env python3
"""Digitize published IEEE Figure 5(b) Device-1 curves from the paper PDF.

Traces pixels on the published figure after axis calibration. Does not invent
points and does not copy simulation output.

    python scripts/digitize_fig5b.py
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.config import data_dir

PAGE_INDEX = 6  # IEEE page 7
PANEL_B_ROW0 = 888
PANEL_B_ROW1 = 1595

# Panel-(b) crop pixels. x-axis 0 … 2.5×10^4 ms; y-axis 0 … 100 %.
# Top spine sits under the in-axes legend (row ~20). Bottom spine is the x-axis.
X0, X1 = 110, 936
Y0, Y1 = 662, 22
X_MAX_MS = 25000.0


def _pdf_path() -> Path:
    here = Path(__file__).resolve()
    name = "Fast_Inventory_for_3GPP_Ambient_IoT_Considering_Device_Unavailability_Due_to_Energy_Harvesting.pdf"
    for p in here.parents:
        cand = p / "Papers" / name
        if cand.exists():
            return cand
    raise FileNotFoundError("Published IEEE PDF not found under Papers/")


def extract_panel_b(pdf_path: Path) -> np.ndarray:
    import pymupdf

    doc = pymupdf.open(pdf_path)
    page = doc[PAGE_INDEX]
    images = page.get_images(full=True)
    if not images:
        raise RuntimeError("No embedded image on IEEE page 7")
    pix = pymupdf.Pixmap(doc, images[0][0])
    if pix.n >= 5:
        pix = pymupdf.Pixmap(pymupdf.csRGB, pix)
    arr = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if arr.shape[2] > 3:
        arr = arr[:, :, :3]
    return arr[PANEL_B_ROW0:PANEL_B_ROW1]


def _hue_sat(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    r = rgb[:, 0].astype(np.float64) / 255.0
    g = rgb[:, 1].astype(np.float64) / 255.0
    b = rgb[:, 2].astype(np.float64) / 255.0
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    chroma = mx - mn
    hue = np.zeros_like(mx)
    m = chroma > 1e-8
    idx = (mx == r) & m
    hue[idx] = np.mod((g[idx] - b[idx]) / chroma[idx], 6.0) / 6.0
    idx = (mx == g) & m
    hue[idx] = ((b[idx] - r[idx]) / chroma[idx] + 2.0) / 6.0
    idx = (mx == b) & m
    hue[idx] = ((r[idx] - g[idx]) / chroma[idx] + 4.0) / 6.0
    sat = np.where(mx > 1e-8, chroma / np.maximum(mx, 1e-8), 0.0)
    return hue, sat


def classify_rgb(rgb: np.ndarray) -> np.ndarray:
    """Return 0=ignore, 1=purple/EM, 2=orange/1-group, 3=green/4-group."""
    dist = np.sqrt(((rgb.astype(np.float64) - 255.0) ** 2).sum(axis=1))
    chroma = rgb.max(axis=1) - rgb.min(axis=1)
    hue, sat = _hue_sat(rgb)
    out = np.zeros(rgb.shape[0], dtype=np.int8)
    coloured = (dist > 10.0) & (chroma >= 10) & (sat >= 0.06)
    purple = coloured & (hue >= 0.72) & (hue <= 0.95)
    orange = coloured & (hue >= 0.03) & (hue <= 0.14)
    green = coloured & (hue >= 0.28) & (hue <= 0.50)
    # Pale anti-aliased strokes near 100 % still keep channel order.
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    purple |= coloured & (r + 8 >= g) & (b + 8 >= g) & (r > 140) & (b > 140) & (g < r - 5)
    orange |= coloured & (r > g + 8) & (g > b + 4)
    green |= coloured & (g > r + 8) & (g > b)
    out[purple] = 1
    out[orange] = 2
    out[green] = 3
    return out


def column_clusters(panel: np.ndarray, x: int, cls: int) -> list[float]:
    labels = classify_rgb(panel[:, x, :])
    rows = np.flatnonzero(labels == cls)
    rows = rows[(rows >= 18) & (rows <= Y0)]
    if rows.size == 0:
        return []
    groups: list[list[int]] = []
    cur = [int(rows[0])]
    for r in rows[1:]:
        if r <= cur[-1] + 3:
            cur.append(int(r))
        else:
            groups.append(cur)
            cur = [int(r)]
    groups.append(cur)
    # Ignore tiny specks and the in-axes legend band for non-green if they sit
    # on the very top; green's plateau is allowed there.
    centres = []
    for g in groups:
        if len(g) < 2:
            continue
        cy = float(np.mean(g))
        centres.append(cy)
    return centres


def follow(panel: np.ndarray, cls: int, y_start: float, prefer: str = "nearest") -> tuple[np.ndarray, np.ndarray]:
    xs: list[float] = []
    ys: list[float] = []
    y = y_start
    missed = 0
    legend_cut = 40.0 if prefer != "top" else 18.0
    for x in range(X0, X1 + 1):
        centres = [c for c in column_clusters(panel, x, cls) if c >= legend_cut]
        if prefer == "top" and x < X0 + 90:
            # Legend sits in the top of the axes; do not snap there in the first ~2.7 s.
            centres = [c for c in centres if c >= 50.0]
        if not centres:
            # Faint anti-aliased tail: accept a near-white tint on the predicted path.
            col = panel[:, x, :].astype(np.float64)
            dist = np.sqrt(((col - 255.0) ** 2).sum(axis=1))
            band = np.flatnonzero(dist > 6)
            band = band[(band >= int(legend_cut)) & (np.abs(band - y) <= 8)]
            if band.size:
                pick = float(np.median(band))
                missed = 0
                y = 0.4 * y + 0.6 * pick
                xs.append(float(x))
                ys.append(pick)
                continue
            missed += 1
            if missed > 40 and xs:
                break
            continue
        if prefer == "top":
            # 4-group is the uppermost stroke after the curves separate.
            pick = min(centres)
        elif prefer == "bottom":
            pick = max(centres)
        else:
            pick = min(centres, key=lambda c: abs(c - y))
            if xs and abs(pick - y) > 40:
                near = [c for c in centres if abs(c - y) <= 40]
                if not near:
                    missed += 1
                    if missed > 40:
                        break
                    continue
                pick = min(near, key=lambda c: abs(c - y))
        missed = 0
        y = 0.15 * y + 0.85 * pick
        xs.append(float(x))
        ys.append(pick)
    return np.asarray(xs), np.asarray(ys)


def to_data(xs: np.ndarray, ys: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    time_ms = np.clip((xs - X0) / (X1 - X0) * X_MAX_MS, 0.0, X_MAX_MS)
    ratio = np.clip((Y0 - ys) / (Y0 - Y1) * 100.0, 0.0, 100.0)
    return time_ms, ratio


def downsample(time_ms: np.ndarray, ratio: np.ndarray, step_ms: float = 100.0):
    if time_ms.size == 0:
        return time_ms, ratio
    order = np.argsort(time_ms)
    time_ms, ratio = time_ms[order], np.maximum.accumulate(ratio[order])
    edges = np.arange(0.0, min(float(time_ms[-1]) + step_ms, X_MAX_MS + step_ms), step_ms)
    out_t = [0.0]
    out_r = [0.0]
    for t1 in edges[1:]:
        sel = (time_ms > out_t[-1]) & (time_ms <= t1)
        if not np.any(sel):
            continue
        out_t.append(float(t1))
        out_r.append(float(np.max(ratio[sel])))
    if time_ms[-1] > out_t[-1] + 1.0:
        out_t.append(float(time_ms[-1]))
        out_r.append(float(ratio[-1]))
    return np.asarray(out_t), np.asarray(out_r)


def write_csv(path: Path, time_ms: np.ndarray, ratio: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["time_ms", "ratio_pct"])
        for t, r in zip(time_ms, ratio):
            w.writerow([f"{t:.1f}", f"{r:.3f}"])


def t_at(time_ms: np.ndarray, ratio: np.ndarray, p: float) -> float | None:
    hit = np.flatnonzero(ratio >= p - 1e-9)
    return None if hit.size == 0 else float(time_ms[hit[0]])


def main() -> None:
    pdf = _pdf_path()
    panel = extract_panel_b(pdf)
    out_dir = data_dir() / "reference_fig5b"
    specs = {
        "em": (1, 640.0, "nearest"),
        "dcm_1_group": (2, 640.0, "bottom"),
        "dcm_4_group": (3, 640.0, "top"),
    }
    meta = {
        "source_pdf": pdf.name,
        "page": 7,
        "panel_b_rows_in_embedded_image": [PANEL_B_ROW0, PANEL_B_ROW1],
        "axis_pixels_in_panel_b": {
            "x0": X0,
            "x1": X1,
            "y0_0pct": Y0,
            "y1_100pct": Y1,
            "x_range_ms": [0, X_MAX_MS],
            "y_range_pct": [0, 100],
        },
        "txx_ms": {},
        "n_raw": {},
        "n_csv": {},
        "last_time_ms": {},
    }
    for key, (cls, y0, prefer) in specs.items():
        xs, ys = follow(panel, cls, y0, prefer=prefer)
        t_raw, r_raw = to_data(xs, ys)
        t, r = downsample(t_raw, r_raw)
        write_csv(out_dir / f"{key}.csv", t, r)
        meta["n_raw"][key] = int(xs.size)
        meta["n_csv"][key] = int(t.size)
        meta["last_time_ms"][key] = None if t.size == 0 else float(t[-1])
        meta["txx_ms"][key] = {
            "t50": t_at(t, r, 50),
            "t90": t_at(t, r, 90),
            "t95": t_at(t, r, 95),
            "t99": t_at(t, r, 99),
        }
        print(
            f"{key}: raw={xs.size} csv={t.size} "
            f"T50={meta['txx_ms'][key]['t50']} T90={meta['txx_ms'][key]['t90']} "
            f"T99={meta['txx_ms'][key]['t99']} last={meta['last_time_ms'][key]}"
        )
    (out_dir / "digitization_run.json").write_text(json.dumps(meta, indent=2))
    print(f"Wrote {out_dir}")


if __name__ == "__main__":
    main()
