# backend/services/mlflow_utils.py
from __future__ import annotations
from pathlib import Path
from typing import Optional
import csv
import os
import mlflow

# ---- config (env-driven; safe defaults for local dev) ----
EXPERIMENT = os.getenv("MLFLOW_EXPERIMENT", "manga_detection")
MLFLOW_SERVER = os.getenv("MLFLOW_TRACKING_URI", "file:./mlruns")
MLFLOW_ENABLED = os.getenv("MLFLOW_ENABLED", "true").strip().lower() in ("true", "1", "yes")

def ensure_mlflow_ready():
    """
    Ensure MLflow points to the right server and experiment.
    Will auto-create the experiment if it doesn't exist.
    No-op when MLFLOW_ENABLED=false.
    """
    if not MLFLOW_ENABLED:
        return
    mlflow.set_tracking_uri(MLFLOW_SERVER)
    mlflow.set_experiment(EXPERIMENT)

def make_csv_row(
    image_name: str,
    results: dict,
    model_version: str,
    panel_gt: Optional[int],
    bubble_gt: Optional[int],
    timestamp: str,
) -> dict:
    panel_count  = len(results.get("panels", []))
    bubble_count = len(results.get("bubbles", []))
    text_count   = sum(1 for b in results.get("bubbles", []) if b.get("japanese_text"))
    return {
        "timestamp": timestamp,
        "image_name": image_name,
        "panel_count": panel_count,
        "bubble_count": bubble_count,
        "text_count": text_count,
        "model_version": model_version,
        "panel_ground_truth": panel_gt if panel_gt is not None else "",
        "bubble_ground_truth": bubble_gt if bubble_gt is not None else "",
    }

def append_csv(csv_path: Path, row: dict):
    csv_path = Path(csv_path)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not file_exists:
            w.writeheader()
        w.writerow(row)

def log_inference_run(
    run_name: str,
    image_path: Path,
    overlay_path: Path,
    detections_json_path: Path,
    per_run_csv_path: Path,
    model_version: str,
    panel_count: int,
    bubble_count: int,
    text_count: int,
    panel_gt: Optional[int],
    bubble_gt: Optional[int],
):
    """
    Logs inference results, params, metrics, and artifacts to MLflow.
    No-op when MLFLOW_ENABLED=false.
    """
    if not MLFLOW_ENABLED:
        return
    ensure_mlflow_ready()
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tag("source", "uvicorn")
        mlflow.set_tag("run_name", run_name)

        # Params
        mlflow.log_param("model_version", model_version)
        if panel_gt is not None:
            mlflow.log_param("panel_gt", int(panel_gt))
        if bubble_gt is not None:
            mlflow.log_param("bubble_gt", int(bubble_gt))

        # Metrics
        mlflow.log_metric("panels_detected", int(panel_count))
        mlflow.log_metric("bubbles_detected", int(bubble_count))
        mlflow.log_metric("texts_detected", int(text_count))
        if panel_gt is not None:
            mlflow.log_metric("panel_abs_err", abs(int(panel_count) - int(panel_gt)))
        if bubble_gt is not None:
            mlflow.log_metric("bubble_abs_err", abs(int(bubble_count) - int(bubble_gt)))

        # Artifacts (safe logging)
        paths = {
            "inputs": [image_path],
            "viz": [overlay_path],
            "outputs": [detections_json_path, per_run_csv_path],
        }
        for subdir, files in paths.items():
            for f in files:
                f = Path(f)
                if f.exists():
                    mlflow.log_artifact(str(f), artifact_path=subdir)
