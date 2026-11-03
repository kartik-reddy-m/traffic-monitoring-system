import os
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
APP_DIR = BASE_DIR / "app"
MODELS_DIR = BASE_DIR / "models"
STATIC_DIR = BASE_DIR / "static"
EVIDENCE_DIR = STATIC_DIR / "evidence"
SAMPLE_DATA_DIR = BASE_DIR / "sample_data"
UPLOADS_DIR = BASE_DIR / "uploads"
TEMP_YOLO_DIR = BASE_DIR / "temp_yolo"
TEMP_MPL_DIR = BASE_DIR / "temp_mpl"

# Create directories if they do not exist
for directory in [MODELS_DIR, STATIC_DIR, EVIDENCE_DIR, SAMPLE_DATA_DIR, UPLOADS_DIR, TEMP_YOLO_DIR, TEMP_MPL_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Ensure Ultralytics and Matplotlib use local writable paths
os.environ["YOLO_CONFIG_DIR"] = str(TEMP_YOLO_DIR)
os.environ["MPLCONFIGDIR"] = str(TEMP_MPL_DIR)

# Monkey patch Ultralytics checks to avoid network timeouts/hangs
try:
    import ultralytics.utils.checks as checks
    checks.check_online = lambda: False
    checks.check_version = lambda *a, **k: None
    checks.check_requirements = lambda *a, **k: True
except Exception:
    pass

# Database Configuration
DATABASE_URL = f"sqlite:///{BASE_DIR / 'traffic_monitoring.db'}"

# Model Configuration
YOLO_MODEL_PATH = MODELS_DIR / "yolov8n.pt"
CONFIDENCE_THRESHOLD = 0.35
IOU_THRESHOLD = 0.45

# Target Vehicle Class IDs (COCO dataset)
VEHICLE_CLASS_MAP = {
    2: "car",
    3: "motorcycle",
    5: "bus",
    7: "truck",
    1: "bicycle"
}

PERSON_CLASS_ID = 0

# Traffic Density Thresholds (based on active vehicle count)
DENSITY_LOW_MAX = 4
DENSITY_MED_MAX = 10
# Above DENSITY_MED_MAX is considered "High"

# Video Processing Defaults
DEFAULT_FPS = 25
DEFAULT_WIDTH = 640
DEFAULT_HEIGHT = 360

# Default Traffic Light cycle timing (in seconds)
TRAFFIC_LIGHT_CYCLE = {
    "GREEN": 12.0,
    "YELLOW": 3.0,
    "RED": 10.0
}
