"""Job-based localization API (Stage E).

POST /localize       -> { job_id, status: "queued" }  (runs in background)
GET  /jobs/{job_id}  -> status + (when done) the overlay package + manifest

The existing POST /run-inference endpoint is unchanged; this adds a
non-blocking alternative on top of the same localize() pipeline.
"""

from __future__ import annotations

import datetime
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.services.jobs import get_job, submit_localize_job

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = BASE_DIR / "backend" / "data" / "input"
LOG_DIR = BASE_DIR / "backend" / "logs"
for _p in (INPUT_DIR, LOG_DIR):
    _p.mkdir(parents=True, exist_ok=True)


@router.post("/localize")
async def create_localize_job(
    file: UploadFile = File(...),
    target_lang: str = Form("ar"),
):
    """Accept an image, start localization in the background, return a job id."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="missing file")

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    image_path = INPUT_DIR / file.filename
    image_path.write_bytes(await file.read())

    log_path = LOG_DIR / f"localize_{Path(file.filename).stem}_{ts}.log"
    job_id = submit_localize_job(str(image_path), target_lang, log_path=str(log_path))
    return {"job_id": job_id, "status": "queued"}


@router.get("/jobs/{job_id}")
def get_localize_job(job_id: str):
    """Return job status; include the result + manifest once status is 'done'."""
    job = get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="job not found")

    resp = {
        "job_id": job["job_id"],
        "status": job["status"],
        "image_name": job["image_name"],
        "target_lang": job["target_lang"],
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }
    if job["status"] == "done":
        result = job.get("result") or {}
        resp["result"] = result
        resp["manifest"] = result.get("manifest") if isinstance(result, dict) else None
    elif job["status"] == "failed":
        resp["error"] = job.get("error")
    return resp
