# # backend/config.py
# import os
# from dotenv import load_dotenv
# from ultralytics import YOLO

# # Load env variables from .env at project root
# load_dotenv()
# # YOLO model paths
# MODEL_PATH_BUBBLE = "models/best.pt"
# MODEL_PATH_PANEL = "models/best_panel_detection.pt"

# # Preload models
# model_bubble = YOLO(MODEL_PATH_BUBBLE, task="predict")
# model_panel = YOLO(MODEL_PATH_PANEL, task="predict")

# # MLflow URI (from CloudFormation public IP)
# MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:8000")

# def configure_mlflow():
#     """Sets MLflow tracking URI from env."""
#     import mlflow
#     mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

import os
from dotenv import load_dotenv

load_dotenv()

def configure_mlflow():
    import mlflow
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://127.0.0.1:5000")  # default is 5000 (MLflow), not 8000
    mlflow.set_tracking_uri(tracking_uri)
