"""Paper reproduction presets served by the API (computed or loaded from script output)."""

import json

from app.aperiodic_simulator.reproduction.controller_reproduce import cached_episodes
from app.aperiodic_simulator.analysis.reference_targets import reference_curve, results_dir
from app.aperiodic_simulator.reproduction.reproduce import (
    _jsonable,
    figure4_data,
    run_protocol_figure,
    slim_figure,
    write_figure_outputs,
)

TARGETS = ("figure4", "figure5", "figure6", "figure7", "figure8", "tables")


def _cache_path(target: str):
    if target == "tables":
        return results_dir() / "tables" / "tables.json"
    return results_dir() / target / f"{target}.json"


def load_cached(target: str) -> dict | None:
    path = _cache_path(target)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    if target in ("figure5", "figure6"):
        for panel, p in data.get("panels", {}).items():
            for name, c in p["curves"].items():
                if "paper_reference" not in c:
                    ref = reference_curve(target, f"{panel}_{name}")
                    c["paper_reference"] = {"x": ref[0].tolist(), "y": ref[1].tolist()} if ref is not None else None
    data["source"] = {"kind": "cached_script_output", "path": str(path)}
    return data


def compute(target: str, episodes: int, base_seed: int, panels=None, workers=None, progress=print) -> dict:
    if target == "figure4":
        data = _jsonable(figure4_data(15000, base_seed))
        for scen, e in data["scenarios"].items():
            ref = reference_curve("figure4", scen)
            e["paper_reference"] = {"x": ref[0].tolist(), "y": ref[1].tolist()} if ref is not None else None
        data["figure"] = "figure4"
        progress("figure4: populations built")
    elif target in ("figure5", "figure6"):
        raw = run_protocol_figure(target, episodes, base_seed, workers, panels=panels, progress=progress)
        if not panels and cached_episodes(_cache_path(target)) <= episodes:
            write_figure_outputs(raw, results_dir() / target)
        data = slim_figure(raw)
    else:
        from app.aperiodic_simulator.reproduction.controller_reproduce import compute_controller_target

        data = compute_controller_target(target, episodes, base_seed, workers=workers, progress=progress)
    data["source"] = {"kind": "computed", "episodes": episodes, "base_seed": base_seed}
    return data
