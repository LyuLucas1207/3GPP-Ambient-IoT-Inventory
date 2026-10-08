"""In-memory store of recent aperiodic runs for device-trace lookup.

Separate from the legacy ``app.simulator.runtime.run_store`` because traces carry the new
paper's scientific states (OFF, MONITOR, RX, TX, INTRA_ROUND_SLEEP,
INTERROUND_SYNC_SLEEP, DONE) and stages (paging, Msg1, EI, Msg2, Msg3).
"""

import threading
from collections import OrderedDict

MAX_RUNS = 8

_lock = threading.Lock()
_runs: "OrderedDict[str, dict]" = OrderedDict()


def put_run(run_id: str, controller: str, episode) -> None:
    with _lock:
        _runs[run_id] = {"controller": controller, "episode": episode}
        _runs.move_to_end(run_id)
        while len(_runs) > MAX_RUNS:
            _runs.popitem(last=False)


def device_trace(run_id: str, controller: str, device_id: int) -> dict:
    with _lock:
        run = _runs.get(run_id)
    if run is None:
        raise KeyError("run not found (expired or unknown run_id)")
    if run["controller"] != controller:
        raise KeyError(f"run {run_id} used controller {run['controller']}")
    ep = run["episode"]
    if device_id not in ep.trace.segments:
        raise KeyError(f"device {device_id} was not traced; traced: {ep.trace.ids}")
    return ep.trace.payload(device_id)
