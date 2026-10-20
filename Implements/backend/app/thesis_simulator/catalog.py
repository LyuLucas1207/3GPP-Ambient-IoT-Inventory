"""Default device, station, and radar cards for the thesis scene.

Numeric defaults match Table II of the aperiodic-paging paper and the
indoor-factory carrier used there. They are copied here on purpose: this
package does not import ``app.simulator`` or ``app.aperiodic_simulator``.
"""

from __future__ import annotations

from typing import Any

from app.thesis_simulator.physics import effective_coverage_m

DEVICE_SUBTYPES: tuple[str, ...] = ("1", "2a", "2b")


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
        return {**_rf_defaults(), "show_range": False, "show_outer": False}


class RadarSpec(CatalogSpec):
    kind = "radar"
    subtype = None
    shape = "hexagon"

    def defaults(self) -> dict[str, Any]:
        return {**_rf_defaults(), "show_range": False, "show_outer": False, "include_d2r": True}


def catalog_specs() -> tuple[CatalogSpec, ...]:
    return (DeviceType1(), DeviceType2a(), DeviceType2b(), StationSpec(), RadarSpec())


def spec_for(kind: str, subtype: str | None) -> CatalogSpec:
    for spec in catalog_specs():
        if spec.kind == kind and spec.subtype == subtype:
            return spec
    raise KeyError((kind, subtype))


def device_sensitivity_defaults() -> dict[str, float]:
    return {subtype: float(spec_for("device", subtype).defaults()["rx_sensitivity_dbm"]) for subtype in DEVICE_SUBTYPES}


def device_params_defaults() -> dict[str, dict[str, Any]]:
    return {subtype: dict(spec_for("device", subtype).defaults()) for subtype in DEVICE_SUBTYPES}


def derive_reader_ranges(
    rf_params: dict[str, Any],
    device_sensitivities: dict[str, float] | None = None,
    device_params: dict[str, dict[str, Any]] | None = None,
) -> dict[str, float]:
    """Return horizontal reach per device subtype.

    If rf_params includes ``include_d2r=False``, use R2D only (legacy).
    Otherwise use the paper's ``min(R2D, D2R)`` model.
    """
    params = dict(device_params or device_params_defaults())
    if device_sensitivities:
        for subtype, sens in device_sensitivities.items():
            if subtype in params:
                params[subtype] = {**params[subtype], "rx_sensitivity_dbm": float(sens)}
    rf = {
        "tx_power_dbm": float(rf_params.get("tx_power_dbm", 33.0)),
        "antenna_gain_dbi": float(rf_params.get("antenna_gain_dbi", 6.0)),
        "extra_attenuation_db": float(rf_params.get("extra_attenuation_db", 0.0)),
        "carrier_ghz": float(rf_params.get("carrier_ghz", 0.9)),
    }
    include_d2r = bool(rf_params.get("include_d2r", True))
    out: dict[str, float] = {}
    for subtype in DEVICE_SUBTYPES:
        if subtype not in params:
            continue
        out[subtype] = effective_coverage_m(params[subtype], rf, include_d2r=include_d2r)
    return out


def catalog_payload() -> list[dict[str, Any]]:
    sens = device_sensitivity_defaults()
    payload: list[dict[str, Any]] = []
    for spec in catalog_specs():
        entry: dict[str, Any] = {
            "kind": spec.kind,
            "subtype": spec.subtype,
            "shape": spec.shape,
            "defaults": spec.defaults(),
        }
        if spec.kind in {"station", "radar"}:
            entry["derived_ranges"] = derive_reader_ranges(entry["defaults"], sens)
        payload.append(entry)
    return payload
