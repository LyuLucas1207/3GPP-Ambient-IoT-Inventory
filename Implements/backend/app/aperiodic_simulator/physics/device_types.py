"""Device types 1, 2a and 2b (Table II).

Type 1 uses its receiver (P_rx) to monitor for paging (P_wurx = P_rx in
Appendix A). Types 2a/2b monitor with the wake-up receiver (WuRX).
"""

from dataclasses import dataclass

import numpy as np

from app.aperiodic_simulator.core.config import SystemParams


@dataclass(frozen=True)
class DeviceType:
    name: str
    index: int
    rx_sensitivity_dbm: float
    p_tx_w: float
    p_rx_w: float
    p_wurx_w: float  # power while monitoring for paging (pre-page MONITOR)
    p_sl_w: float
    e_up_j: float
    e_low_j: float
    uplink: str  # "backscatter" or "active"
    backscatter_loss_db: float = 0.0
    backscatter_gain_db: float = 0.0
    active_tx_power_dbm: float | None = None
    uses_wurx: bool = False


def device_types(system: SystemParams | None = None) -> tuple[DeviceType, DeviceType, DeviceType]:
    s = system or SystemParams()
    t1 = DeviceType(
        name="1",
        index=0,
        rx_sensitivity_dbm=-36.0,
        p_tx_w=1e-6,
        p_rx_w=1e-6,
        p_wurx_w=1e-6,  # P_wurx = P_rx for type 1
        p_sl_w=s.p_sl_w,
        e_up_j=5e-6,
        e_low_j=2.5e-6,
        uplink="backscatter",
        backscatter_loss_db=6.0,
    )
    t2a = DeviceType(
        name="2a",
        index=1,
        rx_sensitivity_dbm=-40.0,
        p_tx_w=200e-6,
        p_rx_w=50e-6,
        p_wurx_w=s.p_wurx_w,
        p_sl_w=s.p_sl_w,
        e_up_j=25e-6,
        e_low_j=12.5e-6,
        uplink="backscatter",
        backscatter_loss_db=6.0,
        backscatter_gain_db=10.0,
        uses_wurx=True,
    )
    t2b = DeviceType(
        name="2b",
        index=2,
        rx_sensitivity_dbm=-70.0,
        p_tx_w=200e-6,
        p_rx_w=50e-6,
        p_wurx_w=s.p_wurx_w,
        p_sl_w=s.p_sl_w,
        e_up_j=25e-6,
        e_low_j=12.5e-6,
        uplink="active",
        active_tx_power_dbm=-20.0,
        uses_wurx=True,
    )
    return t1, t2a, t2b


TYPE_NAMES = ("1", "2a", "2b")


def type_param_arrays(type_idx: np.ndarray, system: SystemParams | None = None) -> dict[str, np.ndarray]:
    """Per-device parameter arrays gathered from the device type index."""
    types = device_types(system)
    out = {}
    for key in ("p_tx_w", "p_rx_w", "p_wurx_w", "p_sl_w", "e_up_j", "e_low_j"):
        table = np.array([getattr(t, key) for t in types], dtype=np.float64)
        out[key] = table[type_idx]
    return out
