"""Per-device diagnostics of a run.

Four metrics answer the supervisor's questions about multi-reader behaviour:

* ``readers_in_range``  - how many readers' coverage contains the device;
* ``cbra_failures``     - joined attempts (paged + Msg1) that did not end identified;
* ``reader_changes``    - joins at a different reader than the previous one,
  counted only when the device went OFF in between (a re-acquisition);
* ``fail_to_page``      - time from the end of a failed attempt until the
  device next acquires a paging message (mean and max per device).

The arrays live on :class:`DeviceWorld`; this module packs them into the run
summary (aggregates in ``metrics_json``, full arrays as a compressed blob).
"""

from __future__ import annotations

import io
from typing import Any

import numpy as np

from app.simulator_thesis.inventory.state import SUBTYPE_CODE, DeviceWorld

PER_DEVICE_FIELDS = (
    "placement_ids", "subtype_code", "x_m", "y_m",
    "readers_in_range", "cbra_failures", "reader_changes",
    "fail_to_page_sum", "fail_to_page_max", "fail_to_page_count",
    "attempts", "depletions", "identified", "identified_t", "identified_by", "drop_cause",
)


def _stats(x: np.ndarray) -> dict[str, float | int | None]:
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"n": 0, "mean": None, "p50": None, "p95": None, "max": None}
    return {
        "n": int(x.size),
        "mean": float(x.mean()),
        "p50": float(np.percentile(x, 50)),
        "p95": float(np.percentile(x, 95)),
        "max": float(x.max()),
    }


def _hist(x: np.ndarray, cap: int = 12) -> dict[str, int]:
    """Integer histogram, values above ``cap`` folded into ``"{cap}+"``."""
    x = np.asarray(x, dtype=int)
    out: dict[str, int] = {}
    for v in range(0, cap):
        c = int((x == v).sum())
        if c:
            out[str(v)] = c
    over = int((x >= cap).sum())
    if over:
        out[f"{cap}+"] = over
    return out


def fail_to_page_mean(world: DeviceWorld) -> np.ndarray:
    n = world.fail_to_page_count
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(n > 0, world.fail_to_page_sum / np.maximum(n, 1), np.nan)


def aggregate(world: DeviceWorld) -> dict[str, Any]:
    """Summary statistics, overall and per device subtype."""
    mean_wait = fail_to_page_mean(world)
    has_wait = world.fail_to_page_count > 0

    def block(mask: np.ndarray) -> dict[str, Any]:
        return {
            "devices": int(mask.sum()),
            "readers_in_range": {**_stats(world.readers_in_range[mask]), "hist": _hist(world.readers_in_range[mask])},
            "cbra_failures": {**_stats(world.cbra_failures[mask]), "hist": _hist(world.cbra_failures[mask])},
            "reader_changes": {
                **_stats(world.reader_changes[mask]),
                "hist": _hist(world.reader_changes[mask]),
                "fraction_changed": float((world.reader_changes[mask] > 0).mean()) if mask.any() else None,
            },
            "fail_to_page_mean_s": _stats(mean_wait[mask & has_wait]),
            "fail_to_page_max_s": _stats(world.fail_to_page_max[mask & has_wait]),
        }

    everyone = np.ones(world.N, dtype=bool)
    return {
        "all": block(everyone),
        "by_subtype": {label: block(world.subtype_code == code) for label, code in SUBTYPE_CODE.items() if (world.subtype_code == code).any()},
    }


def device_metrics_blob(world: DeviceWorld) -> bytes:
    buf = io.BytesIO()
    np.savez_compressed(buf, **{name: getattr(world, name) for name in PER_DEVICE_FIELDS})
    return buf.getvalue()


def load_device_metrics(blob: bytes) -> dict[str, np.ndarray]:
    with np.load(io.BytesIO(blob), allow_pickle=False) as data:
        return {name: data[name].copy() for name in data.files}


def device_metrics_rows(arrays: dict[str, np.ndarray]) -> list[dict[str, Any]]:
    """One JSON row per device (API / CSV)."""
    labels = {code: label for label, code in SUBTYPE_CODE.items()}
    n = arrays["placement_ids"].size
    cnt = arrays["fail_to_page_count"]
    mean = np.where(cnt > 0, arrays["fail_to_page_sum"] / np.maximum(cnt, 1), np.nan)
    rows = []
    for i in range(n):
        t_id = float(arrays["identified_t"][i])
        rows.append({
            "device_id": int(arrays["placement_ids"][i]),
            "subtype": labels.get(int(arrays["subtype_code"][i])),
            "x_m": float(arrays["x_m"][i]),
            "y_m": float(arrays["y_m"][i]),
            "readers_in_range": int(arrays["readers_in_range"][i]),
            "cbra_failures": int(arrays["cbra_failures"][i]),
            "reader_changes": int(arrays["reader_changes"][i]),
            "fail_to_page_count": int(cnt[i]),
            "fail_to_page_mean_s": None if not np.isfinite(mean[i]) else float(mean[i]),
            "fail_to_page_max_s": float(arrays["fail_to_page_max"][i]) if cnt[i] > 0 else None,
            "attempts": int(arrays["attempts"][i]),
            "depletions": int(arrays["depletions"][i]),
            "identified": bool(arrays["identified"][i]),
            "identified_t": None if not np.isfinite(t_id) else t_id,
            "identified_by": None if int(arrays["identified_by"][i]) < 0 else int(arrays["identified_by"][i]),
            "drop_cause": int(arrays["drop_cause"][i]),
        })
    return rows
