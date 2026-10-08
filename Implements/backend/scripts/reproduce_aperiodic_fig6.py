#!/usr/bin/env python3
"""Figure 6 (multi-source, L=16 and L=1, aperiodic vs periodic N_g=1/4).

    python scripts/reproduce_aperiodic_fig6.py --episodes 100 [--workers 8]
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._aperiodic_cli import protocol_figure_main

if __name__ == "__main__":
    protocol_figure_main("figure6")
