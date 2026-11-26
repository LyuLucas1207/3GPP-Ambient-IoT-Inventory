"""Background jobs for long reproduction presets (real job/status model)."""

import threading
import time
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor

MAX_JOBS = 32

_lock = threading.Lock()
_jobs: dict[str, dict] = {}
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="aperiodic-job")


def submit(job_target: str, fn, **kwargs) -> dict:
    job_id = uuid.uuid4().hex[:12]
    job = {
        "job_id": job_id,
        "target": job_target,
        "status": "queued",
        "progress": [],
        "submitted_at": time.time(),
        "started_at": None,
        "finished_at": None,
        "result": None,
        "error": None,
    }
    with _lock:
        _jobs[job_id] = job
        if len(_jobs) > MAX_JOBS:
            for k in sorted(_jobs, key=lambda k: _jobs[k]["submitted_at"])[: len(_jobs) - MAX_JOBS]:
                if _jobs[k]["status"] in ("done", "error"):
                    _jobs.pop(k)

    def log(msg: str) -> None:
        with _lock:
            job["progress"].append(msg)

    def run() -> None:
        job["status"] = "running"
        job["started_at"] = time.time()
        try:
            job["result"] = fn(progress=log, **kwargs)
            job["status"] = "done"
        except Exception as exc:  # reported to the client, not swallowed
            job["error"] = f"{type(exc).__name__}: {exc}"
            job["progress"].append(traceback.format_exc(limit=3))
            job["status"] = "error"
        finally:
            job["finished_at"] = time.time()

    _pool.submit(run)
    return status(job_id)


def status(job_id: str, with_result: bool = False) -> dict:
    with _lock:
        job = _jobs.get(job_id)
        if job is None:
            raise KeyError(job_id)
        out = {k: v for k, v in job.items() if k != "result"}
        out["progress"] = list(job["progress"])
        if with_result and job["status"] == "done":
            out["result"] = job["result"]
    return out
