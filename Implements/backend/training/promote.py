"""Copy a finished training run into the policy registry.

    .venv/bin/python -m training.promote training/outputs/ps_ppo_randomized/<run> [--policy-id NAME] [--force]

Writes ``<policy_id>.zip`` and ``<policy_id>.json`` to
``app/simulator_thesis/rl/policies`` (or ``$THESIS_POLICY_DIR``). The zip is
re-hashed after copying; zero-shot runs copy only the sidecar, which keeps
pointing at the aperiodic checkpoint.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from training.common import sha256_file, write_json

_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.\-]*$")


def promote(run: Path, policy_id: str | None = None, force: bool = False) -> str:
    from app.simulator_thesis.rl.policy import load_meta_file, policy_dir

    run = Path(run)
    side = run / "checkpoints" / "final.json"
    meta = load_meta_file(side)  # verifies the SHA-256 before copying
    pid = policy_id or meta["policy_id"]
    if not _ID.match(pid):
        raise ValueError(f"invalid policy id {pid!r}")
    dest = policy_dir()
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / f"{pid}.json"
    if target.exists() and not force:
        raise FileExistsError(f"{target} exists (use --force)")
    out = json.loads(side.read_text())
    out["policy_id"] = pid
    out["promoted_from"] = str(run)
    if meta["algo"] != "zero_shot_aperiodic":
        shutil.copyfile(run / "checkpoints" / "final.zip", dest / f"{pid}.zip")
        out["sha256"] = sha256_file(dest / f"{pid}.zip")
    write_json(target, out)
    return pid


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run")
    ap.add_argument("--policy-id")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args(argv)
    print(promote(Path(a.run), a.policy_id, a.force))


if __name__ == "__main__":
    main()
