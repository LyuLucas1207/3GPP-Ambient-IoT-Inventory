"""Default device, station, and radar cards for the thesis scene.

Numeric defaults match Table II of the aperiodic-paging paper and the
indoor-factory carrier used there. They are copied here on purpose: this
package does not import ``app.simulator`` or ``app.aperiodic_simulator``.
"""

from __future__ import annotations

from typing import Any


class CatalogSpec:
    """Immutable default card. Instances store their own JSON copy."""

    kind: str
    subtype: str | None
    shape: str

    def defaults(self) -> dict[str, Any]:
        raise NotImplementedError


def _rf_defaults() -> dict[str, Any]:
    return {
        "tx_power_dbm": 33.0,
        "antenna_gain_dbi": 6.0,
        "extra_attenuation_db": 0.0,
        "carrier_ghz": 0.9,
    }


class DeviceType1(CatalogSpec):
    kind = "device"
    subtype = "1"
    shape = "circle"

    def defaults(self) -> dict[str, Any]:
        return {
            "rx_sensitivity_dbm": -36.0,
            "p_tx_w": 1e-6,
            "p_rx_w": 1e-6,
            "p_wurx_w": 1e-6,
            "p_sl_w": 1e-7,
            "e_up_j": 5e-6,
            "e_low_j": 2.5e-6,
            "uplink": "backscatter",
            "backscatter_loss_db": 6.0,
            "backscatter_gain_db": 0.0,
            "active_tx_power_dbm": None,
            "uses_wurx": False,
        }


class DeviceType2a(CatalogSpec):
    kind = "device"
    subtype = "2a"
    shape = "circle"

    def defaults(self) -> dict[str, Any]:
        return {
            "rx_sensitivity_dbm": -40.0,
            "p_tx_w": 200e-6,
            "p_rx_w": 50e-6,
            "p_wurx_w": 1e-6,
            "p_sl_w": 1e-7,
            "e_up_j": 25e-6,
            "e_low_j": 12.5e-6,
            "uplink": "backscatter",
            "backscatter_loss_db": 6.0,
            "backscatter_gain_db": 10.0,
            "active_tx_power_dbm": None,
            "uses_wurx": True,
        }


class DeviceType2b(CatalogSpec):
    kind = "device"
    subtype = "2b"
    shape = "circle"

    def defaults(self) -> dict[str, Any]:
        return {
            "rx_sensitivity_dbm": -70.0,
            "p_tx_w": 200e-6,
            "p_rx_w": 50e-6,
            "p_wurx_w": 1e-6,
            "p_sl_w": 1e-7,
            "e_up_j": 25e-6,
            "e_low_j": 12.5e-6,
            "uplink": "active",
            "backscatter_loss_db": 0.0,
            "backscatter_gain_db": 0.0,
            "active_tx_power_dbm": -20.0,
            "uses_wurx": True,
        }


class StationSpec(CatalogSpec):
    kind = "station"
    subtype = None
    shape = "diamond"

    def defaults(self) -> dict[str, Any]:
        return {
            **_rf_defaults(),
            "radius_m": 20.0,
            "show_range": False,
        }


class RadarSpec(CatalogSpec):
    kind = "radar"
    subtype = None
    shape = "hexagon"

    def defaults(self) -> dict[str, Any]:
        return {
            **_rf_defaults(),
            "radius_m": 30.0,
            "show_range": False,
        }


def catalog_specs() -> tuple[CatalogSpec, ...]:
    return (DeviceType1(), DeviceType2a(), DeviceType2b(), StationSpec(), RadarSpec())


def spec_for(kind: str, subtype: str | None) -> CatalogSpec:
    for spec in catalog_specs():
        if spec.kind == kind and spec.subtype == subtype:
            return spec
    raise KeyError((kind, subtype))


def catalog_payload() -> list[dict[str, Any]]:
    return [
        {
            "kind": spec.kind,
            "subtype": spec.subtype,
            "shape": spec.shape,
            "defaults": spec.defaults(),
        }
        for spec in catalog_specs()
    ]
