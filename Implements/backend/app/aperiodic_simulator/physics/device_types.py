"""Device types 1, 2a and 2b (Table II).

Type 1 uses its receiver (P_rx) to monitor for paging (P_wurx = P_rx in
Appendix A). Types 2a/2b monitor with the wake-up receiver (WuRX).
"""

from dataclasses import dataclass

import numpy as np

from app.aperiodic_simulator.core.config import SystemParams
from app.journal.tables import (
    TYPE1_BACKSCATTER_LOSS_DB,
    TYPE1_E_LOW_J,
    TYPE1_E_UP_J,
    TYPE1_P_RX_W,
    TYPE1_P_TX_W,
    TYPE1_RX_SENSITIVITY_DBM,
    TYPE2A_BACKSCATTER_GAIN_DB,
    TYPE2A_BACKSCATTER_LOSS_DB,
    TYPE2A_E_LOW_J,
    TYPE2A_E_UP_J,
    TYPE2A_P_RX_W,
    TYPE2A_P_TX_W,
    TYPE2A_RX_SENSITIVITY_DBM,
    TYPE2B_ACTIVE_TX_POWER_DBM,
    TYPE2B_E_LOW_J,
    TYPE2B_E_UP_J,
    TYPE2B_P_RX_W,
    TYPE2B_P_TX_W,
    TYPE2B_RX_SENSITIVITY_DBM,
)


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
        rx_sensitivity_dbm=TYPE1_RX_SENSITIVITY_DBM,
        p_tx_w=TYPE1_P_TX_W,
        p_rx_w=TYPE1_P_RX_W,
        p_wurx_w=TYPE1_P_RX_W,  # P_wurx = P_rx for type 1
        p_sl_w=s.p_sl_w,
        e_up_j=TYPE1_E_UP_J,
        e_low_j=TYPE1_E_LOW_J,
        uplink="backscatter",
        backscatter_loss_db=TYPE1_BACKSCATTER_LOSS_DB,
    )
    t2a = DeviceType(
        name="2a",
        index=1,
        rx_sensitivity_dbm=TYPE2A_RX_SENSITIVITY_DBM,
        p_tx_w=TYPE2A_P_TX_W,
        p_rx_w=TYPE2A_P_RX_W,
        p_wurx_w=s.p_wurx_w,
        p_sl_w=s.p_sl_w,
        e_up_j=TYPE2A_E_UP_J,
        e_low_j=TYPE2A_E_LOW_J,
        uplink="backscatter",
        backscatter_loss_db=TYPE2A_BACKSCATTER_LOSS_DB,
        backscatter_gain_db=TYPE2A_BACKSCATTER_GAIN_DB,
        uses_wurx=True,
    )
    t2b = DeviceType(
        name="2b",
        index=2,
        rx_sensitivity_dbm=TYPE2B_RX_SENSITIVITY_DBM,
        p_tx_w=TYPE2B_P_TX_W,
        p_rx_w=TYPE2B_P_RX_W,
        p_wurx_w=s.p_wurx_w,
        p_sl_w=s.p_sl_w,
        e_up_j=TYPE2B_E_UP_J,
        e_low_j=TYPE2B_E_LOW_J,
        uplink="active",
        active_tx_power_dbm=TYPE2B_ACTIVE_TX_POWER_DBM,
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
