"""InF-DH D1T1 scene defaults from 3GPP TR 38.769 Table 4.2.2-2.

Mirrors ``Sources/Standard_3GPP/.../aiot_layout.py`` (BS_POS_FULL, N_DEVICES,
hall geometry) so the thesis simulator can boot with the paper's canonical
scenario without reaching outside this package.
"""

from __future__ import annotations

HALL_WIDTH_M = 120.0
HALL_HEIGHT_M = 60.0
BS_LATTICE_SPACING_M = 20.0
DEFAULT_N_DEVICES = 10_000
DEFAULT_ACTIVE_BS_XY = (50.0, 30.0)
MAX_PLACEMENTS = 20_000


def default_bs_positions() -> list[tuple[float, float]]:
    xs = [10.0, 30.0, 50.0, 70.0, 90.0, 110.0]
    ys = [10.0, 30.0, 50.0]
    return [(x, y) for y in ys for x in xs]


def scenario_defaults_payload() -> dict:
    return {
        "width_m": HALL_WIDTH_M,
        "height_m": HALL_HEIGHT_M,
        "bs_lattice_spacing_m": BS_LATTICE_SPACING_M,
        "bs_positions": [list(xy) for xy in default_bs_positions()],
        "active_bs_xy": list(DEFAULT_ACTIVE_BS_XY),
        "default_n_devices": DEFAULT_N_DEVICES,
        "max_placements": MAX_PLACEMENTS,
    }
