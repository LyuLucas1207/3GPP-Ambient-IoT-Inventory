#!/usr/bin/env python3
"""Figure 7: RL vs DFSA-Schoute vs CMEBE, multi-source, N_tot=15000, L1=1.

    python scripts/aperiodic/figure7/reproduce_fig7.py --episodes 100 [--workers 8]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.aperiodic._cli import controller_target_main

if __name__ == "__main__":
    controller_target_main("figure7")
