"""Tiny smoke test for the consolidated localize() entry point.

Runs localize() on one sample manga page and prints what it returns, so we can
confirm the Stage B refactor didn't break the pipeline.

Run it directly:

    python -m backend.tests.test_localize

It picks the first available image from backend/data/input/. If none of the
sample images or the model weights are present, it skips cleanly instead of
failing (those files are intentionally not committed to the repo).
"""

from __future__ import annotations

import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]
INPUT_DIR = BASE_DIR / "backend" / "data" / "input"
CANDIDATES = ["5.png", "3.png", "test.jpeg", "result.jpg"]


def _pick_sample() -> Path | None:
    for name in CANDIDATES:
        p = INPUT_DIR / name
        if p.exists():
            return p
    existing = sorted(INPUT_DIR.glob("*"))
    return existing[0] if existing else None


def main() -> int:
    sample = _pick_sample()
    if sample is None:
        print(f"SKIP: no sample image found in {INPUT_DIR}")
        return 0

    print(f"Running localize() on: {sample}")

    # Imported here so the SKIP path above doesn't require torch/manga-ocr.
    from backend.services.localize import localize

    result = localize(str(sample), target_lang="ar")

    print("\n=== localize() returned ===")
    print(f"type             : {type(result).__name__}")
    print(f"image_path       : {result.image_path}")
    print(f"target_lang      : {result.target_lang}")
    print(f"model_version    : {result.model_version}")
    print(f"panel_count      : {result.panel_count}")
    print(f"bubble_count     : {result.bubble_count}")
    print(f"text_count       : {result.text_count}")
    print(f"json_path        : {result.json_path}")
    print(f"csv_path         : {result.csv_path}")
    print(f"overlay_path     : {result.overlay_path}")

    bubbles = result.results.get("bubbles", [])
    if bubbles:
        print("\nfirst bubble (sample):")
        print(json.dumps(bubbles[0], indent=2, ensure_ascii=False))

    # Basic sanity assertions.
    assert Path(result.json_path).exists(), "JSON output was not written"
    assert Path(result.csv_path).exists(), "CSV output was not written"
    assert isinstance(result.results, dict) and "bubbles" in result.results
    print("\nOK: outputs written and result shape looks correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
