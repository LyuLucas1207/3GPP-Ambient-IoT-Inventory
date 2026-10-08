#!/usr/bin/env python3
"""Extract Figures 4-8 of the aperiodic-paging paper from the PDF's vector data.

The paper's figures are MATLAB vector graphics embedded in the PDF, so curves
are recovered exactly (no pixel tracing):

1. ``mutool draw -F svg`` converts the figure pages to SVG.
2. Every stroked path is transformed to page coordinates.
3. Each axes box is found from its dark (#262626) frame; its light-grey
   gridlines (#dfdfdf) sit at the printed tick values, so the data mapping is
   a least-squares fit of gridline positions to tick values (the residual is
   stored as calibration evidence).
4. Curves are identified by MATLAB's default line colours and legend order.

Output: ``backend/scripts/aperiodic/figure*/paper/*.csv`` and
``digitize/calibration.json``. Requires ``mutool`` (MuPDF).

    python scripts/aperiodic/digitize/digitize_figures.py
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT.parents[1]
PDF = REPO / "Papers" / "3GPP Ambient IoT Inventory with Aperiodic Paging.pdf"
OUT = ROOT / "scripts" / "aperiodic"

C_BLUE, C_RED, C_YEL, C_PUR, C_GRN = "#0072bd", "#d95319", "#edb120", "#7e2f8e", "#77ac30"

# page -> list of (figure, panel, x_ticks, y_ticks, {colour: curve name})
FIGURES = {
    8: [
        ("figure4", "cdf", list(range(-36, -15, 2)), [i / 10 for i in range(0, 11)],
         {C_BLUE: "single_source", C_RED: "multi_source"}),
    ],
    9: [
        ("figure5", "a_L16", list(range(0, 1201, 200)), list(range(0, 101, 20)),
         {C_YEL: "aperiodic", C_GRN: "periodic_Ng1", C_PUR: "periodic_Ng1_wo_depletion",
          C_RED: "periodic_Ng4", C_BLUE: "periodic_Ng4_wo_depletion"}),
        ("figure5", "b_L1", list(range(0, 1201, 200)), list(range(0, 101, 20)),
         {C_YEL: "aperiodic", C_GRN: "periodic_Ng1", C_PUR: "periodic_Ng1_wo_depletion",
          C_RED: "periodic_Ng4", C_BLUE: "periodic_Ng4_wo_depletion"}),
    ],
    10: [
        ("figure6", "a_L16", list(range(0, 801, 100)), list(range(0, 101, 20)),
         {C_YEL: "aperiodic", C_GRN: "periodic_Ng1", C_RED: "periodic_Ng4"}),
        ("figure6", "b_L1", list(range(0, 801, 100)), list(range(0, 101, 20)),
         {C_YEL: "aperiodic", C_GRN: "periodic_Ng1", C_RED: "periodic_Ng4"}),
        ("figure7", "main", list(range(0, 201, 50)), list(range(0, 101, 10)),
         {C_BLUE: "recurrent_ppo", C_RED: "dfsa_schoute", C_YEL: "cmebe"}),
    ],
    11: [
        ("figure8", "main", list(range(1, 16)), list(range(0, 41, 10)),
         {C_BLUE: "pfsa_L1", C_RED: "pfsa_L8", C_YEL: "pfsa_L32", C_GRN: "recurrent_ppo"}),
    ],
}

NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def parse_path(d: str) -> list[list[tuple[float, float]]]:
    """Polylines of an SVG path (M/L/H/V/Z, absolute, implicit lineto)."""
    tokens = re.findall(r"[MLHVZmlhvzC]|" + NUM.pattern, d)
    polys: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    cmd, i, x, y = "M", 0, 0.0, 0.0
    while i < len(tokens):
        t = tokens[i]
        if t.isalpha():
            cmd = t
            i += 1
            if cmd in "Zz":
                if cur:
                    cur.append(cur[0])
                continue
            continue
        if cmd == "M":
            if cur:
                polys.append(cur)
            x, y = float(tokens[i]), float(tokens[i + 1])
            cur = [(x, y)]
            i += 2
            cmd = "L"
        elif cmd == "L":
            x, y = float(tokens[i]), float(tokens[i + 1])
            cur.append((x, y))
            i += 2
        elif cmd == "H":
            x = float(tokens[i])
            cur.append((x, y))
            i += 1
        elif cmd == "V":
            y = float(tokens[i])
            cur.append((x, y))
            i += 1
        elif cmd == "C":
            x, y = float(tokens[i + 4]), float(tokens[i + 5])
            cur.append((x, y))
            i += 6
        else:
            i += 1
    if cur:
        polys.append(cur)
    return polys


def page_paths(svg: Path) -> list[dict]:
    out = []
    for el in ET.parse(svg).iter():
        if not el.tag.endswith("path") or el.get("stroke") in (None, "none"):
            continue
        m = re.findall(NUM.pattern, el.get("transform", "matrix(1,0,0,1,0,0)"))
        a, b, c, dd, e, f = map(float, m[:6]) if len(m) >= 6 else (1, 0, 0, 1, 0, 0)
        for poly in parse_path(el.get("d", "")):
            p = np.array(poly)
            xy = np.column_stack([a * p[:, 0] + c * p[:, 1] + e, b * p[:, 0] + dd * p[:, 1] + f])
            out.append({"stroke": el.get("stroke").lower(), "xy": xy})
    return out


def axes_boxes(paths: list[dict]) -> list[tuple[float, float, float, float]]:
    """(x0, x1, y_top, y_bottom) in page coordinates (y grows downward)."""
    hs = []
    for p in paths:
        xy = p["xy"]
        if p["stroke"] == "#262626" and len(xy) == 2 and abs(xy[0, 1] - xy[1, 1]) < 1e-6:
            hs.append((round(min(xy[:, 0]), 2), round(max(xy[:, 0]), 2), xy[0, 1]))
    width = max(h[1] - h[0] for h in hs)
    boxes = []
    by_span: dict[tuple, list[float]] = {}
    for x0, x1, y in hs:
        if x1 - x0 > 0.5 * width:
            by_span.setdefault((x0, x1), []).append(y)
    for (x0, x1), ys in by_span.items():
        ys = sorted(set(round(v, 2) for v in ys))
        for k in range(0, len(ys) - 1, 2):
            boxes.append((x0, x1, ys[k], ys[k + 1]))
    return sorted(boxes, key=lambda b: (b[0], b[2]))


def fit_axis(grid: np.ndarray, ticks: list[float], downward: bool = False) -> tuple[float, float, float]:
    """Map gridline page positions to tick values; page y grows downward."""
    grid = np.sort(np.unique(np.round(grid, 3)))
    if downward:
        grid = grid[::-1]
    if grid.size != len(ticks):
        raise RuntimeError(f"gridline/tick mismatch: {grid.size} gridlines vs {len(ticks)} ticks")
    A = np.column_stack([grid, np.ones_like(grid)])
    (k, b), *_ = np.linalg.lstsq(A, np.asarray(ticks, float), rcond=None)
    resid = float(np.max(np.abs(A @ [k, b] - ticks)))
    return float(k), float(b), resid


def extract_page(svg: Path, specs) -> dict:
    paths = page_paths(svg)
    boxes = axes_boxes(paths)
    if len(boxes) != len(specs):
        raise RuntimeError(f"{svg.name}: found {len(boxes)} axes, expected {len(specs)}")
    results = {}
    for box, (fig, panel, xt, yt, colours) in zip(boxes, specs):
        x0, x1, ytop, ybot = box
        inside = lambda xy: (xy[:, 0] >= x0 - 1) & (xy[:, 0] <= x1 + 1) & (xy[:, 1] >= ytop - 1) & (xy[:, 1] <= ybot + 1)
        gx, gy = [], []
        for p in paths:
            xy = p["xy"]
            if p["stroke"] != "#dfdfdf" or len(xy) != 2 or not inside(xy).all():
                continue
            if abs(xy[0, 0] - xy[1, 0]) < 1e-6:
                gx.append(xy[0, 0])
            elif abs(xy[0, 1] - xy[1, 1]) < 1e-6:
                gy.append(xy[0, 1])
        kx, bx, rx = fit_axis(np.array(gx), xt)
        ky, by, ry = fit_axis(np.array(gy), yt, downward=True)
        curves = {}
        for colour, name in colours.items():
            cands = [p["xy"] for p in paths if p["stroke"] == colour and inside(p["xy"]).all() and len(p["xy"]) > 2]
            if not cands:
                raise RuntimeError(f"{fig}/{panel}: no curve for {name}")
            xy = max(cands, key=len)  # the data line (legend samples are 2-point)
            curves[name] = np.column_stack([kx * xy[:, 0] + bx, ky * xy[:, 1] + by])
        results[(fig, panel)] = {
            "curves": curves,
            "calibration": {
                "axes_box_page_pt": list(box),
                "x_ticks": xt,
                "y_ticks": yt,
                "x_fit": [kx, bx],
                "y_fit": [ky, by],
                "x_max_residual": rx,
                "y_max_residual": ry,
            },
        }
    return results


def main() -> None:
    if not shutil.which("mutool"):
        sys.exit("mutool (MuPDF) is required")
    calib = {"source_pdf": PDF.name, "method": "vector extraction via mutool SVG + gridline least squares", "panels": {}}
    with tempfile.TemporaryDirectory() as tmp:
        for page, specs in FIGURES.items():
            svg = Path(tmp) / f"p{page}.svg"
            subprocess.run(["mutool", "draw", "-q", "-F", "svg", "-o", str(svg), str(PDF), str(page)], check=True)
            for (fig, panel), res in extract_page(svg, specs).items():
                d = OUT / fig / "paper"
                d.mkdir(parents=True, exist_ok=True)
                for name, xy in res["curves"].items():
                    xlab, ylab = ("pin_dbm", "cdf") if fig == "figure4" else (
                        ("n_tot_thousands", "resource_efficiency_pct") if fig == "figure8" else ("time_s", "ratio_pct"))
                    fn = d / f"{panel}_{name}.csv" if panel != "main" and panel != "cdf" else d / f"{name}.csv"
                    np.savetxt(fn, xy, delimiter=",", header=f"{xlab},{ylab}", comments="", fmt="%.6g")
                    print(f"{fn.relative_to(ROOT)}: {len(xy)} points")
                calib["panels"][f"{fig}/{panel}"] = {"page": page, **res["calibration"]}
    (Path(__file__).resolve().parent / "calibration.json").write_text(json.dumps(calib, indent=2))


if __name__ == "__main__":
    main()
