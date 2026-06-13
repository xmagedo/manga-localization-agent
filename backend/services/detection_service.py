# # from PIL import Image
# # import numpy as np
# # from .manga_ocr_service import extract_japanese_text
# # from openai import OpenAI
# # import os
# # from dotenv import load_dotenv
# # from backend.utils.model_loader import get_panel_model, get_bubble_model
# # import torchvision.transforms as T
# # from torch.serialization import add_safe_globals
# # import mlflow
# # from backend.core.config import configure_mlflow


# # add_safe_globals([getattr])

# # # Ensure MLflow tracking URI is set
# # configure_mlflow()

# # mlflow.set_experiment("manga-inference")
# # load_dotenv()
# # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # def bubble_center(coords):
# #     x1, y1, x2, y2 = coords
# #     return ((x1 + x2) / 2, (y1 + y2) / 2)

# # def is_center_inside_panel(bubble_coords, panel_coords):
# #     bx, by = bubble_center(bubble_coords)
# #     px1, py1, px2, py2 = panel_coords
# #     return (px1 <= bx <= px2) and (py1 <= by <= py2)

# # def translate_to_arabic(japanese_text):
# #     try:
# #         response = client.chat.completions.create(
# #             model="gpt-3.5-turbo",
# #             messages=[
# #                 {"role": "system", "content": "You are a translator that translates Japanese to Arabic."},
# #                 {"role": "user", "content": f"Translate this Japanese manga sentence to Arabic: {japanese_text}"}
# #             ]
# #         )
# #         return response.choices[0].message.content.strip()
# #     except Exception as e:
# #         print(f"Translation failed: {e}")
# #         return "[ترجمة غير متوفرة]"

# # def detect_bubbles_and_panels(image_path: str):
# #     print("🔥 detect_bubbles_and_panels called with:", image_path, type(image_path))

# #     # ✅ Load models
# #     model_panel = get_panel_model()
# #     model_bubble = get_bubble_model()

# #     # ✅ Open as PIL → numpy array
# #     image = Image.open(image_path).convert("RGB")
# #     image_np = np.array(image)

# #     # ✅ Run YOLO inference
# #     bubble_pred = model_bubble(image_np)
# #     panel_pred = model_panel(image_np)

# #     bubble_results = bubble_pred[0]
# #     panel_results = panel_pred[0]

# #     bubbles = []
# #     panels = []

# #     # --- Process bubbles ---
# #     for box in bubble_results.boxes.xyxy:
# #         x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())
# #         cropped = image.crop((x1, y1, x2, y2))
# #         jp_text = extract_japanese_text(cropped)
# #         bubbles.append({"jp_text": jp_text, "coords": [x1, y1, x2, y2]})

# #     # --- Process panels ---
# #     for box in panel_results.boxes.xyxy:
# #         x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())
# #         panels.append({"coords": [x1, y1, x2, y2]})

# #     # ✅ Sort panels top-to-bottom, left-to-right
# #     panels = sorted(panels, key=lambda p: (p["coords"][1], -p["coords"][0]))

# #     # ✅ Assign panel numbers
# #     for idx, panel in enumerate(panels):
# #         panel["panel_no"] = idx + 1

# #     # ✅ Assign panel numbers to bubbles based on center
# #     for bubble in bubbles:
# #         x1, y1, x2, y2 = bubble["coords"]
# #         assigned_panel_no = 0
# #         for panel in panels:
# #             if is_center_inside_panel([x1, y1, x2, y2], panel["coords"]):
# #                 assigned_panel_no = panel["panel_no"]
# #                 break
# #         bubble["panel_no"] = assigned_panel_no

# #     # ✅ Sort bubbles by panel_no and Y position
# #     sorted_bubbles = sorted(bubbles, key=lambda b: (b["panel_no"], b["coords"][1], -b["coords"][0]))

# #     # ✅ Format bubbles with translations
# #     formatted_bubbles = []
# #     for i, bubble in enumerate(sorted_bubbles):
# #         x1, y1, x2, y2 = bubble["coords"]
# #         jp_text = bubble["jp_text"] or "[OCR failed]"
# #         arabic_text = translate_to_arabic(jp_text) if jp_text.strip() else "[ترجمة غير متوفرة]"
# #         formatted_bubbles.append({
# #             "bubble_no": i + 1,
# #             "panel_no": bubble["panel_no"],
# #             "japanese_text": jp_text,
# #             "arabic_text": arabic_text,
# #             "coordinates": {
# #                 "x1": float(x1),
# #                 "y1": float(y1),
# #                 "x2": float(x2),
# #                 "y2": float(y2)
# #             }
# #         })

# #     # ✅ Map bubbles to panels
# #     panel_bubble_map = {panel["panel_no"]: [] for panel in panels}
# #     for b in formatted_bubbles:
# #         if b["panel_no"] in panel_bubble_map:
# #             panel_bubble_map[b["panel_no"]].append(b["bubble_no"])

# #     # ✅ Format panels
# #     formatted_panels = []
# #     for panel in panels:
# #         formatted_panels.append({
# #             "panel_no": panel["panel_no"],
# #             "coordinates": {
# #                 "x1": float(panel["coords"][0]),
# #                 "y1": float(panel["coords"][1]),
# #                 "x2": float(panel["coords"][2]),
# #                 "y2": float(panel["coords"][3]),
# #             },
# #             "bubble_nos": panel_bubble_map[panel["panel_no"]]
# #         })

# #     # ✅ Return results to the route (no CSV writing here)
# #     return {
# #         "bubbles": formatted_bubbles,
# #         "panels": formatted_panels
# #     }

# from PIL import Image
# import numpy as np
# import os
# import json
# from datetime import datetime

# from dotenv import load_dotenv
# from openai import OpenAI
# import torchvision.transforms as T
# from torch.serialization import add_safe_globals

# from backend.utils.model_loader import get_panel_model, get_bubble_model
# from backend.core.config import configure_mlflow  # ⬅️ on-demand MLflow config
# import mlflow  # ⬅️ safe to import; we won't call network until request time

# add_safe_globals([getattr])
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def _extract_japanese_text_lazy(img):  # ⬅️ lazy import to avoid startup blocking
#     from .manga_ocr_service import extract_japanese_text
#     return extract_japanese_text(img)

# def bubble_center(coords):
#     x1, y1, x2, y2 = coords
#     return ((x1 + x2) / 2, (y1 + y2) / 2)

# def is_center_inside_panel(bubble_coords, panel_coords):
#     bx, by = bubble_center(bubble_coords)
#     px1, py1, px2, py2 = panel_coords
#     return (px1 <= bx <= px2) and (py1 <= by <= py2)

# def translate_to_arabic(japanese_text):
#     try:
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are a translator that translates Japanese to Arabic."},
#                 {"role": "user", "content": f"Translate this Japanese manga sentence to Arabic: {japanese_text}"}
#             ]
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"Translation failed: {e}")
#         return "[ترجمة غير متوفرة]"

# def detect_bubbles_and_panels(image_path: str):
#     print("🔥 detect_bubbles_and_panels called with:", image_path, type(image_path))

#     # ⬅️ Configure MLflow only when a request comes in
#     try:
#         configure_mlflow()
#         mlflow.set_experiment("manga-inference")
#     except Exception as e:
#         # don't fail the request if tracking is down
#         print(f"[MLflow] Skipping tracking setup: {e}")

#     # ✅ Load models
#     model_panel = get_panel_model()
#     model_bubble = get_bubble_model()

#     # ✅ Open as PIL → numpy array
#     image = Image.open(image_path).convert("RGB")
#     image_np = np.array(image)

#     # ✅ Run YOLO inference
#     bubble_pred = model_bubble(image_np)
#     panel_pred = model_panel(image_np)

#     bubble_results = bubble_pred[0]
#     panel_results = panel_pred[0]

#     bubbles = []
#     panels = []

#     # --- Process bubbles ---
#     for box in bubble_results.boxes.xyxy:
#         x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())
#         cropped = image.crop((x1, y1, x2, y2))
#         jp_text = _extract_japanese_text_lazy(cropped)  # ⬅️ lazy call
#         bubbles.append({"jp_text": jp_text, "coords": [x1, y1, x2, y2]})

#     # --- Process panels ---
#     for box in panel_results.boxes.xyxy:
#         x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())
#         panels.append({"coords": [x1, y1, x2, y2]})

#     # ✅ Sort panels top-to-bottom, left-to-right
#     panels = sorted(panels, key=lambda p: (p["coords"][1], -p["coords"][0]))

#     # ✅ Assign panel numbers
#     for idx, panel in enumerate(panels):
#         panel["panel_no"] = idx + 1

#     # ✅ Assign panel numbers to bubbles based on center
#     for bubble in bubbles:
#         x1, y1, x2, y2 = bubble["coords"]
#         assigned_panel_no = 0
#         for panel in panels:
#             if is_center_inside_panel([x1, y1, x2, y2], panel["coords"]):
#                 assigned_panel_no = panel["panel_no"]
#                 break
#         bubble["panel_no"] = assigned_panel_no

#     # ✅ Sort bubbles by panel_no and Y position
#     sorted_bubbles = sorted(bubbles, key=lambda b: (b["panel_no"], b["coords"][1], -b["coords"][0]))

#     # ✅ Format bubbles with translations
#     formatted_bubbles = []
#     for i, bubble in enumerate(sorted_bubbles):
#         x1, y1, x2, y2 = bubble["coords"]
#         jp_text = bubble["jp_text"] or "[OCR failed]"
#         arabic_text = translate_to_arabic(jp_text) if jp_text.strip() else "[ترجمة غير متوفرة]"
#         formatted_bubbles.append({
#             "bubble_no": i + 1,
#             "panel_no": bubble["panel_no"],
#             "japanese_text": jp_text,
#             "arabic_text": arabic_text,
#             "coordinates": {
#                 "x1": float(x1),
#                 "y1": float(y1),
#                 "x2": float(x2),
#                 "y2": float(y2)
#             }
#         })

#     # ✅ Map bubbles to panels
#     panel_bubble_map = {panel["panel_no"]: [] for panel in panels}
#     for b in formatted_bubbles:
#         if b["panel_no"] in panel_bubble_map:
#             panel_bubble_map[b["panel_no"]].append(b["bubble_no"])

#     # ✅ Format panels
#     formatted_panels = []
#     for panel in panels:
#         formatted_panels.append({
#             "panel_no": panel["panel_no"],
#             "coordinates": {
#                 "x1": float(panel["coords"][0]),
#                 "y1": float(panel["coords"][1]),
#                 "x2": float(panel["coords"][2]),
#                 "y2": float(panel["coords"][3]),
#             },
#             "bubble_nos": panel_bubble_map[panel["panel_no"]]
#         })

#     # --- MLflow logging (best-effort; don't crash your API if MLflow is down) ---
#     try:
#         run_name = f"infer_{os.path.basename(image_path)}_{datetime.utcnow().isoformat(timespec='seconds')}"
#         with mlflow.start_run(run_name=run_name):
#             mlflow.log_param("model_panel", "best_panel_detection.pt")
#             mlflow.log_param("model_bubble", "best.pt")
#             mlflow.log_metric("panels", len(formatted_panels))
#             mlflow.log_metric("bubbles", len(formatted_bubbles))

#             if os.path.exists(image_path):
#                 mlflow.log_artifact(image_path, artifact_path="inputs")

#             out_json_path = os.path.join("outputs", os.path.basename(image_path) + ".json")
#             os.makedirs("outputs", exist_ok=True)
#             output_data = {"bubbles": formatted_bubbles, "panels": formatted_panels}
#             with open(out_json_path, "w", encoding="utf-8") as f:
#                 json.dump(output_data, f, ensure_ascii=False, indent=2)
#             mlflow.log_artifact(out_json_path, artifact_path="outputs")
#     except Exception as e:
#         print(f"[MLflow] Logging skipped: {e}")

#     return {"bubbles": formatted_bubbles, "panels": formatted_panels}



# # backend/services/detection_service.py
# from PIL import Image
# import numpy as np
# from .manga_ocr_service import extract_japanese_text
# from openai import OpenAI
# import os
# from dotenv import load_dotenv
# from backend.utils.model_loader import get_panel_model, get_bubble_model
# import torchvision.transforms as T
# from torch.serialization import add_safe_globals

# # NEW: mlflow + viz helpers
# import mlflow
# from backend.core.config import configure_mlflow
# from backend.utils.viz import save_annotated
# from backend.utils.html_viewer import save_click_viewer
# from pathlib import Path
# from datetime import datetime

# add_safe_globals([getattr])
# load_dotenv()
# client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# # MLflow setup
# configure_mlflow()
# mlflow.set_experiment("manga-inference")

# def bubble_center(coords):
#     x1, y1, x2, y2 = coords
#     return ((x1 + x2) / 2, (y1 + y2) / 2)

# def is_center_inside_panel(bubble_coords, panel_coords):
#     bx, by = bubble_center(bubble_coords)
#     px1, py1, px2, py2 = panel_coords
#     return (px1 <= bx <= px2) and (py1 <= by <= py2)

# def translate_to_arabic(japanese_text):
#     try:
#         response = client.chat.completions.create(
#             model="gpt-3.5-turbo",
#             messages=[
#                 {"role": "system", "content": "You are a translator that translates Japanese to Arabic."},
#                 {"role": "user", "content": f"Translate this Japanese manga sentence to Arabic: {japanese_text}"}
#             ]
#         )
#         return response.choices[0].message.content.strip()
#     except Exception as e:
#         print(f"Translation failed: {e}")
#         return "[ترجمة غير متوفرة]"

# def detect_bubbles_and_panels(image_path: str, panel_ground_truth: int | None = None, bubble_ground_truth: int | None = None):
#     print("🔥 detect_bubbles_and_panels called with:", image_path, type(image_path))

#     # ✅ Load models
#     model_panel = get_panel_model()
#     model_bubble = get_bubble_model()

#     # ✅ Open as PIL → numpy array
#     image = Image.open(image_path).convert("RGB")
#     image_np = np.array(image)

#     # ✅ Run YOLO inference
#     bubble_pred = model_bubble(image_np)
#     panel_pred = model_panel(image_np)

#     bubble_results = bubble_pred[0]
#     panel_results = panel_pred[0]

#     bubbles = []
#     panels = []

#     # --- Process bubbles ---
#     for box in bubble_results.boxes.xyxy:
#         x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())
#         cropped = image.crop((x1, y1, x2, y2))
#         jp_text = extract_japanese_text(cropped)
#         bubbles.append({"jp_text": jp_text, "coords": [x1, y1, x2, y2]})

#     # --- Process panels ---
#     for box in panel_results.boxes.xyxy:
#         x1, y1, x2, y2 = map(int, box[:4].cpu().numpy())
#         panels.append({"coords": [x1, y1, x2, y2]})

#     # ✅ Sort panels top-to-bottom, left-to-right
#     panels = sorted(panels, key=lambda p: (p["coords"][1], -p["coords"][0]))

#     # ✅ Assign panel numbers
#     for idx, panel in enumerate(panels):
#         panel["panel_no"] = idx + 1

#     # ✅ Assign panel numbers to bubbles based on center
#     for bubble in bubbles:
#         x1, y1, x2, y2 = bubble["coords"]
#         assigned_panel_no = 0
#         for panel in panels:
#             if is_center_inside_panel([x1, y1, x2, y2], panel["coords"]):
#                 assigned_panel_no = panel["panel_no"]
#                 break
#         bubble["panel_no"] = assigned_panel_no

#     # ✅ Sort bubbles by panel_no and Y position
#     sorted_bubbles = sorted(bubbles, key=lambda b: (b["panel_no"], b["coords"][1], -b["coords"][0]))

#     # ✅ Format bubbles with translations
#     formatted_bubbles = []
#     for i, bubble in enumerate(sorted_bubbles):
#         x1, y1, x2, y2 = bubble["coords"]
#         jp_text = bubble["jp_text"] or "[OCR failed]"
#         arabic_text = translate_to_arabic(jp_text) if jp_text.strip() else "[ترجمة غير متوفرة]"
#         formatted_bubbles.append({
#             "bubble_no": i + 1,
#             "panel_no": bubble["panel_no"],
#             "japanese_text": jp_text,
#             "arabic_text": arabic_text,
#             "coordinates": {
#                 "x1": float(x1),
#                 "y1": float(y1),
#                 "x2": float(x2),
#                 "y2": float(y2)
#             }
#         })

#     # ✅ Map bubbles to panels
#     panel_bubble_map = {}
#     for idx, panel in enumerate(panels):
#         panel_bubble_map[idx + 1] = []

#     for b in formatted_bubbles:
#         if b["panel_no"] in panel_bubble_map:
#             panel_bubble_map[b["panel_no"]].append(b["bubble_no"])

#     # ✅ Format panels
#     formatted_panels = []
#     for panel in panels:
#         formatted_panels.append({
#             "panel_no": panel["panel_no"],
#             "coordinates": {
#                 "x1": float(panel["coords"][0]),
#                 "y1": float(panel["coords"][1]),
#                 "x2": float(panel["coords"][2]),
#                 "y2": float(panel["coords"][3]),
#             },
#             "bubble_nos": panel_bubble_map[panel["panel_no"]]
#         })

#     # ---------- MLflow logging: PNG overlay, HTML viewer, metrics ----------
#     run_name = f"infer_{Path(image_path).name}_{datetime.utcnow().isoformat(timespec='seconds')}"
#     with mlflow.start_run(run_name=run_name) as run:
#         # Params
#         mlflow.log_param("model_panel", "best_panel_detection.pt")
#         mlflow.log_param("model_bubble", "best.pt")

#         # Metrics
#         mlflow.log_metric("panels_detected", len(formatted_panels))
#         mlflow.log_metric("bubbles_detected", len(formatted_bubbles))
#         if panel_ground_truth is not None:
#             mlflow.log_metric("panel_gt", int(panel_ground_truth))
#             mlflow.log_metric("panel_abs_err", abs(len(formatted_panels) - int(panel_ground_truth)))
#         if bubble_ground_truth is not None:
#             mlflow.log_metric("bubble_gt", int(bubble_ground_truth))
#             mlflow.log_metric("bubble_abs_err", abs(len(formatted_bubbles) - int(bubble_ground_truth)))

#         # Save overlay PNG locally, then log
#         overlay_local = f"outputs/annotated/{Path(image_path).stem}_overlay.png"
#         detections_dict = {"panels": formatted_panels, "bubbles": formatted_bubbles}

#         save_annotated(
#             image_path=image_path,
#             panels=formatted_panels,
#             bubbles=formatted_bubbles,
#             out_path=overlay_local,
#         )
#         mlflow.log_artifact(overlay_local, artifact_path="viz")
#         mlflow.log_dict(detections_dict, artifact_file="viz/detections.json")

#         # Clickable HTML viewer
#         viewer_local = "outputs/annotated/viewer.html"
#         save_click_viewer(
#             img_rel_path="viz/" + Path(overlay_local).name,
#             detections=detections_dict,
#             out_html=viewer_local,
#         )
#         mlflow.log_artifact(viewer_local, artifact_path="viz")

#     # ✅ Return results to the route
#     return {
#         "bubbles": formatted_bubbles,
#         "panels": formatted_panels
#     }

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
