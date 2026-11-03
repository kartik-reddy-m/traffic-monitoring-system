import os
import sys
from pathlib import Path

# Add current directory to python path
current_dir = Path(__file__).resolve().parent
if str(current_dir) not in sys.path:
    sys.path.insert(0, str(current_dir))

# Configure offline Ultralytics & Matplotlib environment
os.environ["YOLO_CONFIG_DIR"] = str(current_dir / "temp_yolo")
os.environ["MPLCONFIGDIR"] = str(current_dir / "temp_mpl")

import uvicorn
from app.config import YOLO_MODEL_PATH

def main():
    print("=" * 70)
    print(" AI Powered Smart Traffic Monitoring and Violation Detection System")
    print("=" * 70)
    print(f"[*] Base Directory: {current_dir}")
    print(f"[*] YOLOv8 Model:   {YOLO_MODEL_PATH} ({'Found' if YOLO_MODEL_PATH.exists() else 'Missing!'})")
    print("[*] Starting FastAPI Server on http://127.0.0.1:8000 ...")
    print("[*] Press Ctrl+C to terminate.")
    print("=" * 70)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

if __name__ == "__main__":
    main()
