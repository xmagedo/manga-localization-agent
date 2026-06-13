# backend/api/review_routes.py
from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict
import datetime
import json
import re

router = APIRouter()

# Repo root: backend/api/review_routes.py -> parents[2] is the repo root.
BASE_DIR = Path(__file__).resolve().parents[2]
REVIEWS_DIR = BASE_DIR / "backend" / "data" / "reviews"
REVIEWS_DIR.mkdir(parents=True, exist_ok=True)

# Whitelist for filename stems; everything else collapses to "_".
_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_stem(name: Optional[str]) -> str:
    if not name:
        return "review"
    stem = Path(name).stem
    stem = _UNSAFE.sub("_", stem).strip("._-")
    return stem or "review"


def _coerce_bubble_no(raw: Any) -> Optional[int]:
    """Return a positive integer if ``raw`` represents one, else ``None``.

    Accepts: int, float (only if integral), digit-only str. Rejects: bool,
    None, "", non-integer floats, non-numeric strings, zero, negatives.
    """
    if raw is None or raw == "":
        return None
    # bool is a subclass of int in Python; reject it explicitly.
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    if isinstance(raw, float):
        if raw.is_integer() and raw > 0:
            return int(raw)
        return None
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            n = int(s)
        except ValueError:
            return None
        return n if n > 0 else None
    return None


def _validate_bubble_numbers(bubbles: list) -> None:
    """Validate every bubble has a unique, positive-integer ``bubble_no``.

    Mutates each bubble dict in place to normalize ``bubble_no`` to ``int``.
    Raises ``HTTPException(400)`` with a combined detail message on any
    failure (missing, non-integer, non-positive, or duplicate values).
    """
    errors: list[str] = []
    seen: dict[int, list[int]] = {}

    for idx, bubble in enumerate(bubbles):
        if not isinstance(bubble, dict):
            errors.append(f"results.bubbles[{idx}] must be an object")
            continue
        raw = bubble.get("bubble_no")
        n = _coerce_bubble_no(raw)
        if n is None:
            if raw is None or raw == "":
                errors.append(f"results.bubbles[{idx}]: bubble_no is required")
            else:
                errors.append(
                    f"results.bubbles[{idx}]: bubble_no must be a positive integer "
                    f"(got {raw!r})"
                )
            continue
        bubble["bubble_no"] = n  # normalize stored value
        seen.setdefault(n, []).append(idx)

    duplicates = {n: idxs for n, idxs in seen.items() if len(idxs) > 1}
    if duplicates:
        parts = []
        for n in sorted(duplicates):
            idxs = duplicates[n]
            parts.append(f"{n} (rows {', '.join(str(i) for i in idxs)})")
        errors.append("Duplicate bubble_no values found: " + "; ".join(parts))

    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))


class ReviewPayload(BaseModel):
    """Loose envelope for an edited review.

    Extra fields are allowed so the frontend can grow the payload (e.g.,
    edited_at, edited_bubbles, source markers) without breaking validation.
    """

    model_config = ConfigDict(extra="allow")

    image_name: Optional[str] = None
    panel_ground_truth: Optional[Any] = None
    bubble_ground_truth: Optional[Any] = None
    results: Optional[Any] = None
    edited_at: Optional[str] = None
    saved_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Saved-JSON schema helpers (schema_version 1.0)
# ---------------------------------------------------------------------------

SCHEMA_VERSION = "1.0"

# Static model metadata captured with every saved review. Move to env/config
# when the model lifecycle (versioning, deploy target) becomes dynamic.
MODEL_BLOCK = {
    "model_version": "local-yolo-manga-v1",
    "panel_model": "best_panel_detection.pt",
    "bubble_model": "best.pt",
}


def _coerce_count(raw: Any) -> Optional[int]:
    """Like ``_coerce_bubble_no`` but allows zero (used for ground-truth counts)."""
    if raw is None or raw == "":
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw >= 0 else None
    if isinstance(raw, float):
        if raw.is_integer() and raw >= 0:
            return int(raw)
        return None
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            return None
        try:
            n = int(s)
        except ValueError:
            return None
        return n if n >= 0 else None
    return None


def _project_panel(panel: dict) -> dict:
    """Project a panel dict to the canonical saved-schema field set."""
    bubble_nos = panel.get("bubble_nos")
    if not isinstance(bubble_nos, list):
        bubble_nos = []
    return {
        "panel_no": panel.get("panel_no"),
        "coordinates": panel.get("coordinates"),
        "bubble_nos": list(bubble_nos),
    }


def _project_bubble(bubble: dict) -> dict:
    """Project a bubble dict to the canonical saved-schema field set.

    Infers ``source`` from ``status`` when missing (``"Added"`` ->
    ``"human_added"`` else ``"model_detected"``). Normalizes ``panel_no`` to
    a non-negative int; falls back to 0 if it can't be coerced.
    """
    status = bubble.get("status") or "Auto"
    source = bubble.get("source")
    if not source:
        source = "human_added" if status == "Added" else "model_detected"
    panel_no = _coerce_count(bubble.get("panel_no"))
    if panel_no is None:
        panel_no = 0
    return {
        "bubble_no": bubble.get("bubble_no"),
        "panel_no": panel_no,
        "japanese_text": bubble.get("japanese_text", "") or "",
        "arabic_text": bubble.get("arabic_text", "") or "",
        "coordinates": bubble.get("coordinates"),
        "status": status,
        "source": source,
    }


def _panel_sort_key(panel: dict):
    n = panel.get("panel_no")
    if isinstance(n, bool) or not isinstance(n, (int, float)):
        return float("inf")
    return n


def _bubble_sort_key(bubble: dict):
    panel_n = bubble.get("panel_no")
    bubble_n = bubble.get("bubble_no")
    pk = (
        panel_n
        if isinstance(panel_n, (int, float)) and not isinstance(panel_n, bool)
        else float("inf")
    )
    bk = (
        bubble_n
        if isinstance(bubble_n, (int, float)) and not isinstance(bubble_n, bool)
        else float("inf")
    )
    return (pk, bk)


@router.post("/reviews/save")
def save_review(payload: ReviewPayload):
    """Persist an edited review as a timestamped JSON file under backend/data/reviews/."""
    if payload.results is None:
        raise HTTPException(status_code=400, detail="results is required")
    if not isinstance(payload.results, dict):
        raise HTTPException(status_code=400, detail="results must be an object")

    panels = payload.results.get("panels")
    bubbles = payload.results.get("bubbles")
    if not isinstance(panels, list):
        raise HTTPException(status_code=400, detail="results.panels must be a list")
    if not isinstance(bubbles, list):
        raise HTTPException(status_code=400, detail="results.bubbles must be a list")

    # Data-quality gate: every bubble must have a unique, positive-integer
    # bubble_no. Normalizes string/float "5" -> int 5 in place.
    _validate_bubble_numbers(bubbles)

    # --- project + sort -----------------------------------------------------
    projected_panels = [
        _project_panel(p) for p in (panels or []) if isinstance(p, dict)
    ]
    projected_panels.sort(key=_panel_sort_key)
    projected_bubbles = [
        _project_bubble(b) for b in (bubbles or []) if isinstance(b, dict)
    ]
    projected_bubbles.sort(key=_bubble_sort_key)

    # --- counts -------------------------------------------------------------
    detected_panels = len(projected_panels)
    detected_bubbles = len(projected_bubbles)
    edited_count = sum(1 for b in projected_bubbles if b["status"] == "Edited")
    added_count = sum(1 for b in projected_bubbles if b["status"] == "Added")
    model_detected_count = sum(
        1 for b in projected_bubbles if b["status"] in ("Auto", "Edited")
    )

    # --- ground truth + differences ----------------------------------------
    panel_gt = _coerce_count(payload.panel_ground_truth)
    bubble_gt = _coerce_count(payload.bubble_ground_truth)
    panel_diff = (detected_panels - panel_gt) if panel_gt is not None else None
    bubble_diff = (detected_bubbles - bubble_gt) if bubble_gt is not None else None

    # --- IDs and timestamps -------------------------------------------------
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    stem = _safe_stem(payload.image_name)
    review_id = f"{stem}_review_{ts}"
    review_path = REVIEWS_DIR / f"{review_id}.json"
    saved_at = datetime.datetime.utcnow().isoformat() + "Z"

    # --- enriched body ------------------------------------------------------
    body = {
        "schema_version": SCHEMA_VERSION,
        "review_id": review_id,
        "image": {
            "image_name": payload.image_name,
            "source": "frontend_review",
        },
        "model": dict(MODEL_BLOCK),
        "ground_truth": {
            "panel_count": panel_gt,
            "bubble_count": bubble_gt,
        },
        "ai_prediction_summary": {
            "detected_panels": detected_panels,
            "detected_bubbles": detected_bubbles,
            "panel_difference": panel_diff,
            "bubble_difference": bubble_diff,
        },
        "results": {
            "panels": projected_panels,
            "bubbles": projected_bubbles,
        },
        "review_metadata": {
            "status": "reviewed",
            "saved_at": saved_at,
            "edited_bubbles_count": edited_count,
            "added_bubbles_count": added_count,
            "model_detected_bubbles_count": model_detected_count,
            "data_quality_status": "passed",
        },
    }

    # --- atomic write -------------------------------------------------------
    tmp = review_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(body, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(review_path)

    return {
        "ok": True,
        "review_id": review_id,
        "review_path": str(review_path),
        "saved_at": saved_at,
        "summary": {
            "detected_panels": detected_panels,
            "detected_bubbles": detected_bubbles,
            "edited_bubbles_count": edited_count,
            "added_bubbles_count": added_count,
            "data_quality_status": "passed",
        },
    }
