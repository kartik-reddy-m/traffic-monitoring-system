import os
import cv2
import numpy as np
from pathlib import Path
from ultralytics import YOLO
from app.config import (
    YOLO_MODEL_PATH,
    CONFIDENCE_THRESHOLD,
    VEHICLE_CLASS_MAP,
    PERSON_CLASS_ID,
    TEMP_YOLO_DIR,
    TEMP_MPL_DIR
)

class VehicleDetector:
    def __init__(self, model_path: Path = YOLO_MODEL_PATH, conf_threshold: float = CONFIDENCE_THRESHOLD):
        self.conf_threshold = conf_threshold
        self.model_path = str(model_path)
        
        # Ensure environment paths are set
        os.environ["YOLO_CONFIG_DIR"] = str(TEMP_YOLO_DIR)
        os.environ["MPLCONFIGDIR"] = str(TEMP_MPL_DIR)
        
        # Load YOLO model
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Model file not found at: {self.model_path}")
            
        self.model = YOLO(self.model_path)
        # Warmup model with dummy image
        dummy = np.zeros((320, 320, 3), dtype=np.uint8)
        self.model(dummy, verbose=False)
        print(f"[VehicleDetector] Successfully loaded YOLO model from {self.model_path}")

    def detect(self, frame: np.ndarray, conf: float = None):
        """
        Runs object detection on a single frame.
        Returns:
            vehicles: list of dicts [{'box': [x1, y1, x2, y2], 'conf': float, 'class_id': int, 'class_name': str}]
            persons: list of dicts [{'box': [x1, y1, x2, y2], 'conf': float}]
        """
        if conf is None:
            conf = self.conf_threshold

        results = self.model(frame, conf=conf, verbose=False)
        vehicles = []
        persons = []

        if not results or len(results) == 0:
            return vehicles, persons

        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return vehicles, persons

        for box in boxes:
            cls_id = int(box.cls[0].item())
            confidence = float(box.conf[0].item())
            xyxy = box.xyxy[0].cpu().numpy().astype(int).tolist()

            if cls_id in VEHICLE_CLASS_MAP:
                vehicles.append({
                    "box": xyxy,
                    "conf": confidence,
                    "class_id": cls_id,
                    "class_name": VEHICLE_CLASS_MAP[cls_id]
                })
            elif cls_id == PERSON_CLASS_ID:
                persons.append({
                    "box": xyxy,
                    "conf": confidence,
                    "class_id": cls_id,
                    "class_name": "person"
                })

        return vehicles, persons
