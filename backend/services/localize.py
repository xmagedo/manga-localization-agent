"""Single internal entry point for the manga localization pipeline.

`localize()` consolidates the steps that POST /run-inference previously ran
inline: bubble/panel detection -> OCR -> JP->AR translation -> the existing
JSON/CSV outputs. It does NOT reimplement any pipeline logic; it simply calls
the existing service code (`detect_bubbles_and_panels`) and writes the same
output files in the same format as before.

Typesetting, the delivery manifest, and the job API are intentionally NOT here
yet -- they are later stages.
"""

from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional, Union

from backend.services.detection_service import detect_bubbles_and_panels
from backend.utils.model_loader import get_model_version

# Same default output location the endpoint already used.
BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
OUTPUT_DIR = BASE_DIR / "backend" / "data" / "output"


@dataclass
class LocalizeResult:
    """Structured result of one localization run."""

    image_path: str
    target_lang: str
    results: dict
    model_version: str
    json_path: str
    csv_path: str
    overlay_path: str
    panel_count: int
    bubble_count: int
    text_count: int

    def to_dict(self) -> dict:
        return asdict(self)


def localize(
    image: Union[str, Path],
    target_lang: str = "ar",
    *,
    output_dir: Optional[Union[str, Path]] = None,
    log_path: Optional[Union[str, Path]] = None,
) -> LocalizeResult:
    """Run the existing pipeline for a single manga page.

    Args:
        image: Path to the input manga page image.
        target_lang: Target language code. Only "ar" (Arabic) is wired up
            today; the underlying translation step is unchanged.
        output_dir: Where to write the JSON/CSV outputs (defaults to the
            existing backend/data/output directory).
        log_path: Optional log file passed through to the detection service.

    Returns:
        LocalizeResult with the detection results, written file paths, and
        summary counts.
    """
    image_path = Path(image)
    out_dir = Path(output_dir) if output_dir is not None else OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    stem = image_path.stem
    json_path = out_dir / f"{stem}.json"
    csv_path = out_dir / f"{stem}.csv"

    # 1) Detection + OCR + JP->AR translation (existing service, unchanged).
    results, overlay_path = detect_bubbles_and_panels(
        str(image_path),
        log_path=str(log_path) if log_path is not None else None,
    )

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

    panel_count = len(results.get("panels", []))
    bubble_count = len(results.get("bubbles", []))
    text_count = sum(1 for b in results.get("bubbles", []) if b.get("japanese_text"))

    return LocalizeResult(
        image_path=str(image_path),
        target_lang=target_lang,
        results=results,
        model_version=model_version,
        json_path=str(json_path),
        csv_path=str(csv_path),
        overlay_path=str(overlay_path),
        panel_count=panel_count,
        bubble_count=bubble_count,
        text_count=text_count,
    )
