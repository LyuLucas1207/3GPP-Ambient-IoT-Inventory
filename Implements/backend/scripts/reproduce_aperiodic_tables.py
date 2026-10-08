#!/usr/bin/env python3
"""Tables V (RL vs PFSA, mean total identification time) and VI (alpha sweep).

Table IV (mid-round depletion) is produced by reproduce_aperiodic_fig5.py.

    python scripts/reproduce_aperiodic_tables.py --episodes 100 [--workers 8]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._aperiodic_cli import controller_target_main

if __name__ == "__main__":
    controller_target_main("tables")
