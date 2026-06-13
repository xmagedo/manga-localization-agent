"""Tiny in-memory job store for asynchronous localization jobs.

POST /localize submits a job here and returns immediately; the heavy
`localize()` call runs on a background thread pool so it never blocks the API.
GET /jobs/{job_id} reads the job's current status/result.

This is intentionally simple (process-local dict). It is NOT durable across
restarts -- good enough for the hackathon; a real deployment would use a
queue + persistent store.
"""

from __future__ import annotations

import datetime
import os
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_JOBS: Dict[str, Dict[str, Any]] = {}
_EXECUTOR = ThreadPoolExecutor(
    max_workers=int(os.getenv("LOCALIZE_WORKERS", "2")),
    thread_name_prefix="localize",
)

# status values: "queued" -> "processing" -> "done" | "failed"


def _now() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def create_job(image_name: str, target_lang: str) -> str:
    job_id = uuid.uuid4().hex
    with _LOCK:
        _JOBS[job_id] = {
            "job_id": job_id,
            "status": "queued",
            "image_name": image_name,
            "target_lang": target_lang,
            "created_at": _now(),
            "updated_at": _now(),
            "result": None,
            "error": None,
        }
    return job_id


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        job = _JOBS.get(job_id)
        return dict(job) if job else None


def _update(job_id: str, **fields: Any) -> None:
    with _LOCK:
        job = _JOBS.get(job_id)
        if job is not None:
            job.update(fields)
            job["updated_at"] = _now()


def submit_localize_job(
    image_path: str,
    target_lang: str = "ar",
    *,
    log_path: Optional[str] = None,
) -> str:
    """Create a job and run localize(image_path, target_lang) in the background.

    Returns the job_id immediately.
    """
    image_name = os.path.basename(str(image_path))
    job_id = create_job(image_name, target_lang)
    _EXECUTOR.submit(_run, job_id, str(image_path), target_lang, log_path)
    return job_id


def _run(job_id: str, image_path: str, target_lang: str, log_path: Optional[str]) -> None:
    _update(job_id, status="processing")
    try:
        # Imported lazily so importing this module doesn't pull in torch/OCR.
        from backend.services.localize import localize

        result = localize(image_path, target_lang, log_path=log_path)
        _update(job_id, status="done", result=result.to_dict())
    except Exception as e:  # noqa: BLE001 - surface any failure to the caller
        _update(
            job_id,
            status="failed",
            error=f"{type(e).__name__}: {e}",
            traceback=traceback.format_exc(),
        )
