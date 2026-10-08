#!/usr/bin/env python3
"""Figure 8: resource efficiency vs N_tot (1000..15000), RL vs PFSA L=1/8/32, multi-source.

    python scripts/aperiodic/figure8/reproduce_fig8.py --episodes 100 [--workers 8]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.aperiodic._cli import controller_target_main

if __name__ == "__main__":
    controller_target_main("figure8")
