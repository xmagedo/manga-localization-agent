# backend/services/detection_service.py
from pathlib import Path
from typing import Optional
from PIL import Image
import numpy as np, os, json, traceback
from dotenv import load_dotenv
from openai import OpenAI

from backend.utils.model_loader import get_panel_model, get_bubble_model
from backend.services.manga_ocr_service import extract_japanese_text
from backend.utils.viz import draw_boxes

load_dotenv()
_openai_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=_openai_key) if _openai_key else None

BASE_DIR   = Path(__file__).resolve().parents[2]
OUTPUT_DIR = BASE_DIR / "backend" / "data" / "output"
ANN_DIR    = OUTPUT_DIR / "annotated"
for p in [OUTPUT_DIR, ANN_DIR]: p.mkdir(parents=True, exist_ok=True)

def _log(log_path: Optional[str], msg: str):
    if log_path:
        with open(log_path, "a") as f: f.write(msg.rstrip() + "\n")

def _translate_ar(jp: str, log_path: Optional[str]) -> str:
    if not jp or not jp.strip(): return "[ترجمة غير متوفرة]"
    if client is None:
        _log(log_path, "[translate] OPENAI_API_KEY missing; skipping.")
        return "[ترجمة غير متوفرة]"
    try:
        rsp = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role":"system","content":"You are a translator that translates Japanese to Arabic."},
                {"role":"user","content":f"Translate this Japanese manga sentence to Arabic: {jp}"}
            ],
            temperature=0.2,
        )
        return rsp.choices[0].message.content.strip()
    except Exception as e:
        _log(log_path, f"[translate] {e}")
        return "[ترجمة غير متوفرة]"

def detect_bubbles_and_panels(image_path: str, log_path: Optional[str] = None):
    """
    Returns (results_dict, overlay_png_path)
    Writes detailed progress to log_path if provided.
    """
    try:
        _log(log_path, f"[detect] image={image_path}")
        img = Image.open(image_path).convert("RGB")
        img_np = np.array(img)

        model_panel  = get_panel_model()
        model_bubble = get_bubble_model()
        _log(log_path, "[detect] models loaded")

        panel_pred  = model_panel(img_np)[0]
        bubble_pred = model_bubble(img_np)[0]
        _log(log_path, "[detect] predictions done")

        # Panels
        panels = []
        for b in panel_pred.boxes.xyxy:
            x1,y1,x2,y2 = map(int, b[:4].cpu().numpy())
            panels.append({"coords":[x1,y1,x2,y2]})
        panels = sorted(panels, key=lambda p: (p["coords"][1], p["coords"][0]))
        for i,p in enumerate(panels, start=1): p["panel_no"] = i

        # Bubbles (per-bubble try/except so a single OCR failure doesn't kill the run)
        bubbles = []
        for b in bubble_pred.boxes.xyxy:
            x1,y1,x2,y2 = map(int, b[:4].cpu().numpy())
            jp, ar = "[OCR failed]", "[ترجمة غير متوفرة]"
            try:
                crop = img.crop((x1,y1,x2,y2))
                jp = extract_japanese_text(crop) or "[OCR failed]"
                ar = _translate_ar(jp, log_path) if jp != "[OCR failed]" else "[ترجمة غير متوفرة]"
            except Exception as e:
                _log(log_path, f"[bubble OCR] {e}")
            bubbles.append({"coords":[x1,y1,x2,y2], "jp":jp, "ar":ar})

        # Assign panel_no
        def center(c): x1,y1,x2,y2 = c; return ((x1+x2)/2.0, (y1+y2)/2.0)
        def inside(p, c): x1,y1,x2,y2 = p; cx,cy = c; return (x1<=cx<=x2) and (y1<=cy<=y2)

        for bub in bubbles:
            cx,cy = center(bub["coords"])
            assigned = 0
            for p in panels:
                if inside(p["coords"], (cx,cy)): assigned = p["panel_no"]; break
            bub["panel_no"] = assigned
        bubbles = sorted(bubbles, key=lambda b: (b["panel_no"], b["coords"][1], b["coords"][0]))

        # Format
        formatted_bubbles = []
        for i,b in enumerate(bubbles, start=1):
            x1,y1,x2,y2 = b["coords"]
            formatted_bubbles.append({
                "bubble_no": i,
                "panel_no": b["panel_no"],
                "japanese_text": b["jp"],
                "arabic_text": b["ar"],
                "coordinates": {"x1":float(x1),"y1":float(y1),"x2":float(x2),"y2":float(y2)}
            })

        panel_map = {p["panel_no"]: [] for p in panels}
        for b in formatted_bubbles:
            if b["panel_no"] in panel_map: panel_map[b["panel_no"]].append(b["bubble_no"])

        formatted_panels = []
        for p in panels:
            x1,y1,x2,y2 = p["coords"]
            formatted_panels.append({
                "panel_no": p["panel_no"],
                "coordinates": {"x1":float(x1),"y1":float(y1),"x2":float(x2),"y2":float(y2)},
                "bubble_nos": panel_map[p["panel_no"]],
            })

        results = {"bubbles": formatted_bubbles, "panels": formatted_panels}

        # Overlay
        overlay_path = ANN_DIR / f"{Path(image_path).stem}_overlay.png"
        try:
            draw_boxes(img, formatted_panels, formatted_bubbles, overlay_path)
            _log(log_path, f"[detect] overlay saved: {overlay_path}")
        except Exception as e:
            _log(log_path, f"[overlay] {e}")

        return results, overlay_path

    except Exception:
        # Propagate up; the route will create <name>.FAILED.txt and copy this traceback to log
        _log(log_path, traceback.format_exc())
        raise
