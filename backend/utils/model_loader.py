import os
import subprocess
from ultralytics import YOLO
import torch
from torch.serialization import add_safe_globals
from torch.nn.modules.container import Sequential
from ultralytics.nn.tasks import DetectionModel

# ✅ Allow YOLO safe unpickling
add_safe_globals([DetectionModel, Sequential])

# ✅ Patch torch.load to always use weights_only=False
_orig_load = torch.load
def unsafe_load(*args, **kwargs):
    kwargs["weights_only"] = False
    return _orig_load(*args, **kwargs)
torch.load = unsafe_load

PANEL_MODEL_PATH = "backend/models/best_panel_detection.pt"
BUBBLE_MODEL_PATH = "backend/models/best.pt"
VERSION_FILE = "mlops/data/model_version.txt"  # ✅ version file path

_panel_model = None
_bubble_model = None

def get_panel_model():
    global _panel_model
    if _panel_model is None:
        print("🔥 Loading panel model...")
        _panel_model = YOLO(PANEL_MODEL_PATH)
    return _panel_model

def get_bubble_model():
    global _bubble_model
    if _bubble_model is None:
        print("🔥 Loading bubble model...")
        _bubble_model = YOLO(BUBBLE_MODEL_PATH)
    return _bubble_model

def get_model_version():
    """Read version number from file, default 0.1 if not set."""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            return f.read().strip()
    return "0.1"

def bump_model_version():
    """Increment version number (e.g., 0.1 → 0.2)."""
    current = float(get_model_version())
    new_version = f"{current + 0.1:.1f}"
    os.makedirs(os.path.dirname(VERSION_FILE), exist_ok=True)
    with open(VERSION_FILE, "w") as f:
        f.write(new_version)
    return new_version

def run_inference_flow(image_path: str) -> str:
    result = subprocess.run(
        ["python", "mlops/manga_inference_flow.py", "--image_path", image_path],
        capture_output=True,
        text=True,
    )
    return result.stdout
