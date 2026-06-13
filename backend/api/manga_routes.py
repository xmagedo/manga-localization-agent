# from fastapi import APIRouter, UploadFile, File, Form, HTTPException
# import os
# import csv
# from backend.services.detection_service import detect_bubbles_and_panels
# from backend.utils.model_loader import get_model_version

# router = APIRouter()

# PRODUCTION_CSV = "/Users/abdulmajeedalroumi/Documents/Manga_detection_files/manga_detection_project/mlops/data/production.csv"

# @router.post("/run-inference")
# async def run_inference(
#     file: UploadFile = File(...),
#     panel_ground_truth: int = Form(None),   # ✅ user provides panel GT
#     bubble_ground_truth: int = Form(None)   # ✅ user provides bubble GT
# ):
#     try:
#         # ✅ Save uploaded file
#         os.makedirs("backend/data/input", exist_ok=True)
#         path = os.path.join("backend/data/input", file.filename)
#         with open(path, "wb") as f:
#             f.write(await file.read())

#         print("🔥 Passing path:", path, type(path))

#         # ✅ Run detection
#         results = detect_bubbles_and_panels(path)

#         # ✅ Collect metadata
#         image_name = os.path.basename(path)
#         panel_count = len(results["panels"])
#         bubble_count = len(results["bubbles"])
#         text_count = sum(1 for b in results["bubbles"] if b["japanese_text"])
#         error = 0
#         model_version = get_model_version()

#         # ✅ Combine ground truth into one field or keep as separate columns
#         os.makedirs(os.path.dirname(PRODUCTION_CSV), exist_ok=True)
#         file_exists = os.path.isfile(PRODUCTION_CSV)
#         with open(PRODUCTION_CSV, "a", newline="") as f:
#             writer = csv.writer(f)
#             if not file_exists:
#                 writer.writerow([
#                     "image_name", "panel_count", "bubble_count", "text_count",
#                     "error", "model_version", "prediction",
#                     "panel_ground_truth", "bubble_ground_truth"
#                 ])
#             writer.writerow([
#                 image_name,
#                 panel_count,
#                 bubble_count,
#                 text_count,
#                 error,
#                 model_version,
#                 panel_count + bubble_count,  # prediction metric
#                 panel_ground_truth if panel_ground_truth is not None else "",
#                 bubble_ground_truth if bubble_ground_truth is not None else ""
#             ])

#         return {
#             "results": results,
#             "model_version": model_version,
#             "ground_truth_saved": panel_ground_truth is not None or bubble_ground_truth is not None
#         }

#     except Exception as e:
#         import traceback; traceback.print_exc()
#         raise HTTPException(status_code=500, detail=str(e))




# backend/api/manga_routes.py
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from pathlib import Path
from typing import Optional
import os, csv, json, traceback, datetime

from backend.services.localize import localize
from backend.services.mlflow_utils import ensure_mlflow_ready, log_inference_run

router = APIRouter()

# ---- absolute directories (no dependency on uvicorn CWD) ----
BASE_DIR   = Path(__file__).resolve().parents[2]  # repo root
DATA_DIR   = BASE_DIR / "backend" / "data"
INPUT_DIR  = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
LOG_DIR    = BASE_DIR / "backend" / "logs"
MLOPS_DIR  = BASE_DIR / "mlops" / "data"
PROD_CSV   = MLOPS_DIR / "production.csv"

for p in [INPUT_DIR, OUTPUT_DIR, LOG_DIR, MLOPS_DIR]:
    p.mkdir(parents=True, exist_ok=True)


@router.post("/run-inference")
async def run_inference(
    file: UploadFile = File(...),
    panel_ground_truth: Optional[int] = Form(None),
    bubble_ground_truth: Optional[int] = Form(None),
):
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    stem = Path(file.filename).stem
    log_path = LOG_DIR / f"run_{stem}_{ts}.log"
    json_path = OUTPUT_DIR / f"{stem}.json"
    csv_path  = OUTPUT_DIR / f"{stem}.csv"
    fail_path = OUTPUT_DIR / f"{stem}.FAILED.txt"

    try:
        # 1) Save upload
        image_path = INPUT_DIR / file.filename
        image_path.write_bytes(await file.read())
        log_path.write_text(f"[{ts}] Saved upload to {image_path}\n")

        # 2-4) Run the consolidated pipeline: detection -> OCR -> JP->AR
        #       translation, plus the JSON + per-run CSV outputs. This is the
        #       same work the endpoint used to do inline, now behind localize().
        result = localize(
            str(image_path),
            target_lang="ar",
            output_dir=OUTPUT_DIR,
            log_path=log_path,
        )
        results       = result.results
        model_version = result.model_version
        overlay_path  = result.overlay_path
        json_path     = Path(result.json_path)
        csv_path      = Path(result.csv_path)
        panel_count   = result.panel_count
        bubble_count  = result.bubble_count
        text_count    = result.text_count

        # 5) Append production.csv (summary of this run)
        new_file = not PROD_CSV.exists()
        with PROD_CSV.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new_file:
                w.writerow([
                    "timestamp","image_name","panel_count","bubble_count","text_count",
                    "model_version","panel_ground_truth","bubble_ground_truth"
                ])
            w.writerow([
                ts, image_path.name, panel_count, bubble_count, text_count,
                model_version,
                panel_ground_truth if panel_ground_truth is not None else "",
                bubble_ground_truth if bubble_ground_truth is not None else ""
            ])

        # 6) (JSON + per-run CSV are written inside localize() above.)

        # 7) MLflow (best-effort; won’t block)
        try:
            ensure_mlflow_ready()
            run_name = f"infer_{image_path.name}_{ts}"
            log_inference_run(
                run_name=run_name,
                image_path=image_path,
                overlay_path=overlay_path,
                detections_json_path=json_path,
                per_run_csv_path=csv_path,
                model_version=model_version,
                panel_count=panel_count,
                bubble_count=bubble_count,
                text_count=text_count,
                panel_gt=panel_ground_truth,
                bubble_gt=bubble_ground_truth,
            )
        except Exception as e:
            with open(log_path, "a") as lf:
                lf.write(f"[MLflow] {e}\n")

        # 8) Return file locations + inline detection results.
        #    (Existing keys are unchanged; Option B overlay-package keys are
        #     added on top so existing clients keep working.)
        return {
            "ok": True,
            "results": results,
            "json_path": str(json_path),
            "csv_path": str(csv_path),
            "overlay_path": str(overlay_path),
            "log_path": str(log_path),
            "clean_image_path": result.clean_image_path,
            "overlay_json_path": result.overlay_json_path,
            "manifest": result.manifest,
        }

    except Exception:
        with open(fail_path, "w", encoding="utf-8") as f:
            f.write(traceback.format_exc())
        with open(log_path, "a") as lf:
            lf.write(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed. See {fail_path} and {log_path}")
