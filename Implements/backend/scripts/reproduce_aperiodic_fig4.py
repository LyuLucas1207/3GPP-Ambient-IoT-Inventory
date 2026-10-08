#!/usr/bin/env python3
"""Figure 4: CDF of the harvesting incident power, N_eff and type shares.

    python scripts/reproduce_aperiodic_fig4.py [--seed 0] [--n-tot 15000]
"""

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.aperiodic_simulator.analysis.reference_targets import results_dir
from app.aperiodic_simulator.reproduction.reproduce import _jsonable, figure4_data, plot_figure4


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-tot", type=int, default=15000)
    args = ap.parse_args()
    data = figure4_data(args.n_tot, args.seed)
    out = results_dir() / "figure4"
    out.mkdir(parents=True, exist_ok=True)
    (out / "figure4.json").write_text(json.dumps(_jsonable(data), indent=1))
    plot_figure4(data, out / "figure4.png")
    for scen, e in data["scenarios"].items():
        sh = {k: round(100 * v, 1) for k, v in e["type_shares"].items()}
        gap = e.get("paper_cdf_quantile_gap_db", {})
        print(
            f"{scen:14s} N_eff={e['n_eff']} (paper {e['paper_n_eff']}) shares%={sh} (paper {e['paper_type_shares_pct']}) "
            f"P_harv<P_sl={100 * e['harvest_below_sleep']['share_of_n_eff']:.1f}% "
            f"CDF gap vs paper: mean {gap.get('mean_abs', float('nan')):.2f} dB, max {gap.get('max_abs', float('nan')):.2f} dB"
        )
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
