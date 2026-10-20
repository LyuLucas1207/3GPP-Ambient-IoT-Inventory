"""One-shot: strip legacy radius_m / show_range from station & radar placements.

The thesis simulator used to store a hard radius on infrastructure placements.
Readers now carry per-device-type derived ranges and stations have no hard
range at all, so the old keys are dead. Running this script is idempotent.

Usage:
    python -m scripts.cleanup_radius_fields
"""

from __future__ import annotations

from sqlalchemy import text

from app.thesis_simulator.db import get_engine, init_db


def main() -> None:
    init_db()
    with get_engine().begin() as conn:
        result = conn.execute(
            text(
                """
                UPDATE thesis_placements
                SET params_json = params_json - 'radius_m' - 'show_range'
                WHERE kind IN ('station','radar')
                  AND (params_json ? 'radius_m' OR params_json ? 'show_range')
                """
            )
        )
        print(f"Updated {result.rowcount} placements")


if __name__ == "__main__":
    main()
