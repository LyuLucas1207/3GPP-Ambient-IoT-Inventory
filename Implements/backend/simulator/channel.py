"""RF received power, conversion efficiency, and harvested electrical power.

Canonical efficiency (published IEEE, physically consistent):

    xi(p_in) = (p_in + 41) / 100     if p_in <= -10 dBm
    xi(p_in) = (-2 * p_in + 11) / 100 if p_in >  -10 dBm

where p_in is the numerical dBm value. At p_in = -36 dBm, xi = 0.05.

The arXiv v1 preprint swaps the piecewise condition; do not use that form.
See docs/PAPER_NOTES.md.
"""

from pathlib import Path
import hashlib

import numpy as np

from simulator.config import data_dir


def dbm_to_watts(dbm: np.ndarray | float) -> np.ndarray | float:
    return 10.0 ** ((np.asarray(dbm, dtype=np.float64) - 30.0) / 10.0)


def watts_to_dbm(watts: np.ndarray | float) -> np.ndarray | float:
    w = np.asarray(watts, dtype=np.float64)
    return 10.0 * np.log10(w) + 30.0


def conversion_efficiency(pin_dbm: np.ndarray | float) -> np.ndarray | float:
    """Published piecewise RF-to-DC efficiency ξ(p_in)."""
    x = np.asarray(pin_dbm, dtype=np.float64)
    low = (x + 41.0) / 100.0
    high = (-2.0 * x + 11.0) / 100.0
    xi = np.where(x <= -10.0, low, high)
    xi = np.clip(xi, 0.0, 1.0)
    if np.isscalar(pin_dbm):
        return float(xi)
    return xi


def harvest_power_w(pin_dbm: np.ndarray | float) -> np.ndarray | float:
    """P_eh = p_in * ξ(p_in)."""
    pin_w = dbm_to_watts(pin_dbm)
    xi = conversion_efficiency(pin_dbm)
    return pin_w * xi


def load_pin_cdf(csv_path: Path | None = None) -> tuple[np.ndarray, np.ndarray]:
    path = csv_path or (data_dir() / "fig5a_pin_cdf.csv")
    if not path.exists():
        raise FileNotFoundError(
            f"Digitized Figure 5(a) CDF not found: {path}. "
            "Restore backend/data/fig5a_pin_cdf.csv."
        )
    data = np.loadtxt(path, delimiter=",", skiprows=1)
    cdf = data[:, 0].astype(np.float64)
    pin = data[:, 1].astype(np.float64)
    order = np.argsort(cdf)
    cdf, pin = cdf[order], pin[order]
    cdf[0] = 0.0
    cdf[-1] = 1.0
    return cdf, pin


def stratified_unit(n: int, rng: np.random.Generator) -> np.ndarray:
    """One sample per equal-probability stratum, then shuffled."""
    u = (np.arange(n, dtype=np.float64) + rng.random(n)) / max(n, 1)
    rng.shuffle(u)
    return u


def sample_pin_dbm(
    n: int,
    rng: np.random.Generator,
    csv_path: Path | None = None,
    sensitivity_dbm: float = -36.0,
    method: str = "stratified",
) -> np.ndarray:
    """Inverse-CDF sampling from digitized Figure 5(a).

    stratified (default): one draw per n-quantile bin so the empirical CDF
    covers the published tail (needed for EM T99). iid: independent uniforms.
    """
    cdf, pin = load_pin_cdf(csv_path)
    if method == "iid":
        u = rng.uniform(0.0, 1.0, size=n)
    else:
        u = stratified_unit(n, rng)
    samples = np.interp(u, cdf, pin)
    samples = np.maximum(samples, sensitivity_dbm)
    return samples


def pin_cdf_fingerprint(csv_path: Path | None = None) -> dict:
    path = csv_path or (data_dir() / "fig5a_pin_cdf.csv")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "file": path.name,
        "sha256_12": digest[:12],
        "sha256": digest,
    }
