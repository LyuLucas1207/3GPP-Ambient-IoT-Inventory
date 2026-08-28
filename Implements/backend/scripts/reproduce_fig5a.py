#!/usr/bin/env python3
"""Plot the digitized Figure 5(a) p_in CDF used by the simulator."""

import sys
from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from simulator.channel import load_pin_cdf
from simulator.config import results_dir


def main():
    cdf, pin = load_pin_cdf()
    out = results_dir()
    out.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    ax.plot(pin, cdf * 100.0, color="#4c78a8", lw=2)
    ax.set_xlabel(r"$p_{\mathrm{in}}$ (dBm)")
    ax.set_ylabel("CDF (%)")
    ax.set_title("Figure 5(a) digitized $p_{in}$ CDF")
    ax.grid(True, alpha=0.35)
    fig.tight_layout()
    path = out / "fig5a_pin_cdf.png"
    fig.savefig(path, dpi=160)
    print(f"Saved {path}")


if __name__ == "__main__":
    main()
