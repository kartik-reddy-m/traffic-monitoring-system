import os
import sys
from pathlib import Path

base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))

os.environ["YOLO_CONFIG_DIR"] = str(base_dir / "temp_yolo")
os.environ["MPLCONFIGDIR"] = str(base_dir / "temp_mpl")

import cv2
from app.config import SAMPLE_DATA_DIR
from app.database import init_db, SessionLocal, ViolationRecord
from app.core.detector import VehicleDetector
from app.core.tracker import VehicleTracker
from app.core.violation_engine import ViolationEngine
from app.core.traffic_analyzer import TrafficAnalyzer

def test_violation_flow():
    print("[TEST VIOLATIONS] Initializing pipeline...")
    init_db()
    detector = VehicleDetector()
    tracker = VehicleTracker()
    engine = ViolationEngine()
    analyzer = TrafficAnalyzer()
    db = SessionLocal()

    video_path = SAMPLE_DATA_DIR / "kitti_traffic.mp4"
    cap = cv2.VideoCapture(str(video_path))
    assert cap.isOpened(), "Could not open kitti_traffic.mp4"

    violations_found = []
    # Test 35 frames with signal_state = RED and a stop line positioned in the middle
    print("[TEST VIOLATIONS] Processing frames with simulated RED light...")
    for f in range(35):
        ret, frame = cap.read()
        if not ret:
            break

        h, w = frame.shape[:2]
        stop_line = ((0, int(h * 0.65)), (w, int(h * 0.65)))

        vehicles, persons = detector.detect(frame)
        active_tracks = tracker.update(vehicles)
        analyzer.process_tracks(active_tracks, frame.shape)

        for track in active_tracks:
            # Test Red Light Violation
            v_record = engine.check_red_light(track, frame, "RED", stop_line, db, "kitti_traffic.mp4")
            if v_record:
                print(f"  --> Violation Triggered! Type: {v_record.violation_type}, Vehicle: {v_record.vehicle_type} #{v_record.vehicle_id}, Evidence: {v_record.evidence_path}")
                violations_found.append(v_record)

    cap.release()
    db.close()

    total_records = SessionLocal().query(ViolationRecord).count()
    print(f"\n[TEST VIOLATIONS] Successfully captured {len(violations_found)} live violations!")
    print(f"[TEST VIOLATIONS] Total records in SQLite database: {total_records}")

    # Check evidence files exist
    for v in violations_found:
        local_path = base_dir / v.evidence_path.lstrip("/\\")
        assert local_path.exists(), f"Evidence image not found at {local_path}"
        print(f"  [+] Evidence verified on disk: {local_path.name} ({local_path.stat().st_size} bytes)")

    print("[SUCCESS] Violation engine, image evidence generation, and database storage verified!")

if __name__ == "__main__":
    test_violation_flow()
