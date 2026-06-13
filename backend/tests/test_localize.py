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
    print(f"type              : {type(result).__name__}")
    print(f"image_path        : {result.image_path}")
    print(f"target_lang       : {result.target_lang}")
    print(f"model_version     : {result.model_version}")
    print(f"image size        : {result.image_width} x {result.image_height}")
    print(f"panel_count       : {result.panel_count}")
    print(f"bubble_count      : {result.bubble_count}")
    print(f"text_count        : {result.text_count}")
    print(f"json_path         : {result.json_path}")
    print(f"csv_path          : {result.csv_path}")
    print(f"overlay_path      : {result.overlay_path}")
    print(f"clean_image_path  : {result.clean_image_path}")
    print(f"overlay_json_path : {result.overlay_json_path}")

    print("\n=== delivery manifest ===")
    print(json.dumps(result.manifest, indent=2, ensure_ascii=False))

    bubbles = result.results.get("bubbles", [])
    if bubbles:
        print("\nfirst bubble (sample):")
        print(json.dumps(bubbles[0], indent=2, ensure_ascii=False))

    # --- sanity assertions: outputs exist ---
    assert Path(result.json_path).exists(), "JSON output was not written"
    assert Path(result.csv_path).exists(), "CSV output was not written"
    assert Path(result.clean_image_path).exists(), "cleaned image was not written"
    assert Path(result.overlay_json_path).exists(), "overlay JSON was not written"

    # --- sanity assertions: overlay JSON shape ---
    overlay = json.loads(Path(result.overlay_json_path).read_text(encoding="utf-8"))
    for key in ("image", "image_width", "image_height", "target_lang", "bubbles", "manifest"):
        assert key in overlay, f"overlay JSON missing key: {key}"
    for b in overlay["bubbles"]:
        for key in ("bubble_no", "panel_no", "japanese_text", "arabic_text", "coordinates"):
            assert key in b, f"overlay bubble missing key: {key}"
        for ck in ("x1", "y1", "x2", "y2"):
            assert ck in b["coordinates"], f"bubble coordinates missing: {ck}"

    # --- sanity assertions: manifest shape ---
    for key in ("output_image_sha256", "bubble_count", "target_lang", "timestamp", "stages_completed"):
        assert key in result.manifest, f"manifest missing key: {key}"
    assert len(result.manifest["output_image_sha256"]) == 64, "sha256 looks wrong"
    assert result.manifest["bubble_count"] == result.bubble_count

    print("\nOK: overlay package + manifest written and shapes look correct.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
