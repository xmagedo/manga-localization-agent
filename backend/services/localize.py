"""Single internal entry point for the manga localization pipeline.

`localize()` consolidates the steps that POST /run-inference previously ran
inline: bubble/panel detection -> OCR -> JP->AR translation -> the existing
JSON/CSV outputs. It does NOT reimplement any pipeline logic; it calls the
existing service code (`detect_bubbles_and_panels`).

Stage C adds the "Option B" overlay package (HTML/JSON overlay, NOT image
typesetting):
  - a cleaned page image (each bubble filled white to remove the Japanese),
  - a structured overlay JSON the static viewer renders Arabic over, and
  - a delivery manifest (sha256 of the output image, counts, timestamp, and
    the list of pipeline stages completed).

The job API and croo-sdk integration are intentionally NOT here yet.
"""

from __future__ import annotations

import csv
import datetime
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional, Union

from backend.services.detection_service import detect_bubbles_and_panels
from backend.services.overlay import clean_bubbles, sha256_file
from backend.utils.model_loader import get_model_version

# Same default output location the endpoint already used.
BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
OUTPUT_DIR = BASE_DIR / "backend" / "data" / "output"


@dataclass
class LocalizeResult:
    """Structured result of one localization run (Option B overlay package)."""

    image_path: str
    target_lang: str
    results: dict
    model_version: str
    json_path: str
    csv_path: str
    overlay_path: str            # detection box-overlay PNG (from viz.draw_boxes)
    clean_image_path: str        # cleaned page (bubbles whitened)
    overlay_json_path: str       # structured JSON the HTML viewer loads
    image_width: int
    image_height: int
    panel_count: int
    bubble_count: int
    text_count: int
    manifest: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _utc_now_iso() -> str:
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def localize(
    image: Union[str, Path],
    target_lang: str = "ar",
    *,
    output_dir: Optional[Union[str, Path]] = None,
    log_path: Optional[Union[str, Path]] = None,
) -> LocalizeResult:
    """Run the existing pipeline for a single manga page and build the
    Option B overlay package.

    Args:
        image: Path to the input manga page image.
        target_lang: Target language code. Only "ar" (Arabic) is wired up
            today; the underlying translation step is unchanged.
        output_dir: Where to write outputs (defaults to backend/data/output).
        log_path: Optional log file passed through to the detection service.

    Returns:
        LocalizeResult with detection results, the overlay package paths, and
        the delivery manifest.
    """
    image_path = Path(image)
    out_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = image_path.stem
    json_path = out_dir / f"{stem}.json"
    csv_path = out_dir / f"{stem}.csv"
    clean_image_path = out_dir / f"{stem}_clean.png"
    overlay_json_path = out_dir / f"{stem}.overlay.json"

    stages: list[str] = []

    # 1) Detection + OCR + JP->AR translation (existing service, unchanged).
    results, overlay_path = detect_bubbles_and_panels(
        str(image_path),
        log_path=str(log_path) if log_path is not None else None,
    )
    stages += ["detection", "ocr", "translation"]

    # 2) Model version (same source as before).
    model_version = get_model_version()

    # 3) Write JSON atomically (identical shape to the old endpoint output).
    tmp = json_path.with_suffix(".json.tmp")
    tmp.write_text(
        json.dumps(
            {"results": results, "model_version": model_version},
            indent=4,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    tmp.replace(json_path)
    stages.append("detection_json")

    # 4) Per-run detailed CSV (identical columns to the old endpoint output).
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            ["bubble_no", "panel_no", "japanese_text", "arabic_text", "x1", "y1", "x2", "y2"]
        )
        for b in results.get("bubbles", []):
            c = b["coordinates"]
            w.writerow(
                [
                    b["bubble_no"],
                    b["panel_no"],
                    b["japanese_text"],
                    b["arabic_text"],
                    c["x1"],
                    c["y1"],
                    c["x2"],
                    c["y2"],
                ]
            )
    stages.append("detection_csv")

    bubbles = results.get("bubbles", [])
    panel_count = len(results.get("panels", []))
    bubble_count = len(bubbles)
    text_count = sum(1 for b in bubbles if b.get("japanese_text"))

    # 5) Cleaned page image: fill each bubble white to remove the Japanese.
    _, image_width, image_height = clean_bubbles(image_path, bubbles, clean_image_path)
    stages.append("bubble_cleaning")

    # The overlay JSON (written below) embeds the manifest, so record those two
    # final stages now so the manifest reflects the complete run.
    stages += ["overlay_json", "manifest"]

    # 6) Delivery manifest (sha256 of the output/cleaned image, counts, etc.).
    manifest = {
        "image_name": image_path.name,
        "output_image": clean_image_path.name,
        "output_image_sha256": sha256_file(clean_image_path),
        "target_lang": target_lang,
        "bubble_count": bubble_count,
        "panel_count": panel_count,
        "text_count": text_count,
        "model_version": model_version,
        "timestamp": _utc_now_iso(),
        "stages_completed": stages,
    }

    # 7) Structured overlay JSON for the static HTML viewer.
    overlay_bubbles = [
        {
            "bubble_no": b["bubble_no"],
            "panel_no": b["panel_no"],
            "japanese_text": b["japanese_text"],
            "arabic_text": b["arabic_text"],
            "coordinates": {
                "x1": b["coordinates"]["x1"],
                "y1": b["coordinates"]["y1"],
                "x2": b["coordinates"]["x2"],
                "y2": b["coordinates"]["y2"],
            },
        }
        for b in bubbles
    ]
    overlay_doc = {
        "image": clean_image_path.name,
        "image_width": image_width,
        "image_height": image_height,
        "target_lang": target_lang,
        "bubbles": overlay_bubbles,
        "manifest": manifest,
    }
    tmp_overlay = overlay_json_path.with_suffix(".json.tmp")
    tmp_overlay.write_text(
        json.dumps(overlay_doc, indent=4, ensure_ascii=False), encoding="utf-8"
    )
    tmp_overlay.replace(overlay_json_path)

    return LocalizeResult(
        image_path=str(image_path),
        target_lang=target_lang,
        results=results,
        model_version=model_version,
        json_path=str(json_path),
        csv_path=str(csv_path),
        overlay_path=str(overlay_path),
        clean_image_path=str(clean_image_path),
        overlay_json_path=str(overlay_json_path),
        image_width=image_width,
        image_height=image_height,
        panel_count=panel_count,
        bubble_count=bubble_count,
        text_count=text_count,
        manifest=manifest,
    )
