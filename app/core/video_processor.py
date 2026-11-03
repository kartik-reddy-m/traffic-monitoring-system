import cv2
import time
import os
import threading
import numpy as np
from typing import Optional, Tuple, Dict, Any, Generator
from sqlalchemy.orm import Session

from app.config import (
    YOLO_MODEL_PATH,
    SAMPLE_DATA_DIR,
    TRAFFIC_LIGHT_CYCLE
)
from app.database import SessionLocal, TrafficLog
from app.core.detector import VehicleDetector
from app.core.tracker import VehicleTracker, Track
from app.core.violation_engine import ViolationEngine
from app.core.traffic_analyzer import TrafficAnalyzer

class VideoProcessor:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Core engines
        self.detector = VehicleDetector(YOLO_MODEL_PATH)
        self.tracker = VehicleTracker()
        self.violation_engine = ViolationEngine()
        self.analyzer = TrafficAnalyzer()

        # Video stream state
        self.source_type = "sample" # "sample", "webcam", "upload"
        self.source_path = str(SAMPLE_DATA_DIR / "kitti_traffic.mp4")
        self.webcam_index = 0
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = True
        self.is_paused = False

        # Virtual Traffic Light state
        self.signal_mode = "auto" # "auto", "manual_red", "manual_green", "manual_yellow"
        self.signal_state = "GREEN"
        self.signal_timer = time.time()
        self.cycle_times = TRAFFIC_LIGHT_CYCLE.copy()

        # Virtual Stop Line and Direction settings
        self.stop_line_pct = 0.68 # line at 68% of frame height
        self.allowed_direction = "down" # "down", "up", "left", "right"

        # Frame performance
        self.fps = 0.0
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.last_log_time = time.time()

        # Initialize capture
        self._init_capture()

    def _init_capture(self):
        if self.cap is not None:
            self.cap.release()

        if self.source_type == "webcam":
            self.cap = cv2.VideoCapture(self.webcam_index)
        else:
            if not os.path.exists(self.source_path):
                # Fallback to any mp4 in sample_data
                samples = list(SAMPLE_DATA_DIR.glob("*.mp4"))
                if samples:
                    self.source_path = str(samples[0])
            self.cap = cv2.VideoCapture(self.source_path)

        if not self.cap or not self.cap.isOpened():
            print(f"[VideoProcessor] Warning: Could not open video source: {self.source_path}")

    def set_source(self, source_type: str, source_path: Optional[str] = None, webcam_index: int = 0):
        with self.lock:
            self.source_type = source_type
            if source_path:
                self.source_path = source_path
            self.webcam_index = webcam_index
            self.tracker.reset()
            self.analyzer.reset()
            self._init_capture()

    def update_settings(self, settings: Dict[str, Any]):
        with self.lock:
            if "confidence_threshold" in settings and settings["confidence_threshold"] is not None:
                self.detector.conf_threshold = float(settings["confidence_threshold"])
            if "stop_line_y" in settings and settings["stop_line_y"] is not None:
                self.stop_line_pct = float(settings["stop_line_y"])
            if "allowed_direction" in settings and settings["allowed_direction"] is not None:
                self.allowed_direction = str(settings["allowed_direction"]).lower()
            if "traffic_light_mode" in settings and settings["traffic_light_mode"] is not None:
                self.signal_mode = str(settings["traffic_light_mode"])
                if self.signal_mode == "manual_red":
                    self.signal_state = "RED"
                elif self.signal_mode == "manual_green":
                    self.signal_state = "GREEN"
                elif self.signal_mode == "manual_yellow":
                    self.signal_state = "YELLOW"
            if "traffic_light_green_sec" in settings and settings["traffic_light_green_sec"] is not None:
                self.cycle_times["GREEN"] = float(settings["traffic_light_green_sec"])
            if "traffic_light_yellow_sec" in settings and settings["traffic_light_yellow_sec"] is not None:
                self.cycle_times["YELLOW"] = float(settings["traffic_light_yellow_sec"])
            if "traffic_light_red_sec" in settings and settings["traffic_light_red_sec"] is not None:
                self.cycle_times["RED"] = float(settings["traffic_light_red_sec"])

    def _update_traffic_light(self):
        if self.signal_mode != "auto":
            return

        now = time.time()
        elapsed = now - self.signal_timer
        limit = self.cycle_times.get(self.signal_state, 10.0)

        if elapsed >= limit:
            self.signal_timer = now
            if self.signal_state == "GREEN":
                self.signal_state = "YELLOW"
            elif self.signal_state == "YELLOW":
                self.signal_state = "RED"
            elif self.signal_state == "RED":
                self.signal_state = "GREEN"

    def get_current_stats(self) -> Dict[str, Any]:
        with self.lock:
            src_name = os.path.basename(self.source_path) if self.source_type != "webcam" else f"Webcam #{self.webcam_index}"
            return self.analyzer.get_stats_dict(
                signal_state=self.signal_state,
                fps=self.fps,
                video_source=src_name
            )

    def generate_mjpeg_frames(self) -> Generator[bytes, None, None]:
        db = SessionLocal()
        try:
            while self.is_running:
                if self.is_paused:
                    time.sleep(0.08)
                    continue

                with self.lock:
                    if self.cap is None or not self.cap.isOpened():
                        self._init_capture()
                        if not self.cap or not self.cap.isOpened():
                            time.sleep(0.5)
                            continue

                    ret, frame = self.cap.read()
                    if not ret:
                        # Video finished: loop back to frame 0
                        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                        ret, frame = self.cap.read()
                        if not ret:
                            time.sleep(0.2)
                            continue

                    # Resize frame to standard processing size for CPU inference efficiency
                    h, w = frame.shape[:2]
                    target_w = 720
                    if w > target_w:
                        scale = target_w / float(w)
                        frame = cv2.resize(frame, (target_w, int(h * scale)))
                        h, w = frame.shape[:2]

                    # Update Traffic Light
                    self._update_traffic_light()

                    # Define virtual stop line
                    line_y = int(h * self.stop_line_pct)
                    stop_line = ((0, line_y), (w, line_y))

                    # 1. Detect vehicles and persons
                    vehicles, persons = self.detector.detect(frame)

                    # 2. Track vehicles
                    active_tracks = self.tracker.update(vehicles)

                    # 3. Process traffic statistics
                    self.analyzer.process_tracks(active_tracks, frame.shape)

                    # Periodic DB Logging (every 10s)
                    now_time = time.time()
                    if now_time - self.last_log_time >= 10.0:
                        self.last_log_time = now_time
                        src_name = os.path.basename(self.source_path) if self.source_type != "webcam" else f"Webcam #{self.webcam_index}"
                        log_entry = TrafficLog(
                            total_vehicles=self.analyzer.total_counted,
                            active_vehicles=self.analyzer.active_count,
                            car_count=self.analyzer.class_counts.get("car", 0),
                            bike_count=self.analyzer.class_counts.get("motorcycle", 0) + self.analyzer.class_counts.get("bicycle", 0),
                            bus_count=self.analyzer.class_counts.get("bus", 0),
                            truck_count=self.analyzer.class_counts.get("truck", 0),
                            density_level=self.analyzer.density_level,
                            video_source=src_name
                        )
                        db.add(log_entry)
                        db.commit()

                    # 4. Check Traffic Violations
                    src_label = os.path.basename(self.source_path) if self.source_type != "webcam" else f"Webcam #{self.webcam_index}"
                    for track in active_tracks:
                        # A. Red Light Violation
                        v_rl = self.violation_engine.check_red_light(
                            track, frame, self.signal_state, stop_line, db, src_label
                        )
                        if v_rl:
                            self.analyzer.record_violation(v_rl.violation_type)

                        # B. Wrong Way Violation
                        v_ww = self.violation_engine.check_wrong_way(
                            track, frame, self.allowed_direction, db, src_label
                        )
                        if v_ww:
                            self.analyzer.record_violation(v_ww.violation_type)

                        # C. Triple Riding Violation
                        v_tr = self.violation_engine.check_triple_riding(
                            track, persons, frame, db, src_label
                        )
                        if v_tr:
                            self.analyzer.record_violation(v_tr.violation_type)

                        # D. No Helmet Violation
                        v_nh = self.violation_engine.check_no_helmet(
                            track, persons, frame, db, src_label
                        )
                        if v_nh:
                            self.analyzer.record_violation(v_nh.violation_type)

                    # 5. Draw Visual Annotations
                    annotated_frame = self._render_annotations(
                        frame, active_tracks, persons, stop_line
                    )

                    # Calculate FPS
                    self.frame_count += 1
                    fps_elapsed = time.time() - self.last_fps_time
                    if fps_elapsed >= 1.0:
                        self.fps = self.frame_count / fps_elapsed
                        self.frame_count = 0
                        self.last_fps_time = time.time()

                    # Encode to JPEG
                    ret, buffer = cv2.imencode('.jpg', annotated_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if not ret:
                        continue
                    frame_bytes = buffer.tobytes()

                # Yield frame for multipart streaming
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

                # Minor throttle to prevent CPU saturation
                time.sleep(0.01)

        finally:
            db.close()

    def _render_annotations(
        self,
        frame: np.ndarray,
        tracks: list,
        persons: list,
        stop_line: Tuple[Tuple[int, int], Tuple[int, int]]
    ) -> np.ndarray:
        out = frame.copy()
        h, w = out.shape[:2]

        # Draw Stop Line
        p1, p2 = stop_line
        line_color = (0, 230, 0) # Green
        if self.signal_state == "RED":
            line_color = (0, 0, 245) # Bright Red
        elif self.signal_state == "YELLOW":
            line_color = (0, 215, 255) # Amber Yellow

        cv2.line(out, p1, p2, line_color, 3)
        cv2.putText(out, f"STOP LINE [SIGNAL: {self.signal_state}]", (15, p1[1] - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, line_color, 2)

        # Class colors (BGR)
        color_map = {
            "car": (245, 170, 40),        # Cyan-Blue
            "motorcycle": (230, 215, 0),   # Light Cyan
            "bus": (200, 60, 240),        # Violet
            "truck": (30, 150, 255),      # Orange
            "bicycle": (140, 230, 80)     # Light Green
        }

        # Draw vehicle tracks
        for track in tracks:
            bx1, by1, bx2, by2 = track.box
            
            # Check if this vehicle has committed a violation
            is_violator = track.has_violated
            box_color = (0, 0, 255) if is_violator else color_map.get(track.class_name, (200, 200, 200))

            # Bounding box
            thickness = 3 if is_violator else 2
            cv2.rectangle(out, (bx1, by1), (bx2, by2), box_color, thickness)

            # Draw trajectory path history
            if len(track.history) > 1:
                pts = np.array(track.history, np.int32).reshape((-1, 1, 2))
                cv2.polylines(out, [pts], False, box_color, 2)

            # Label banner
            if is_violator:
                v_names = ",".join([v.replace("_", " ").upper() for v in track.violations])
                label = f"VIOLATION: {v_names} [#{track.track_id}]"
            else:
                label = f"#{track.track_id} {track.class_name.upper()} {track.conf:.2f}"

            # Label background box
            (lw, lh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(out, (bx1, max(0, by1 - lh - 8)), (bx1 + lw + 6, max(lh + 8, by1)), box_color, -1)
            text_color = (255, 255, 255) if is_violator else (10, 10, 10)
            cv2.putText(out, label, (bx1 + 3, max(lh + 4, by1 - 4)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, text_color, 1)

        # Draw Traffic Light Widget in Top-Right
        tl_x = w - 60
        tl_y = 12
        cv2.rectangle(out, (tl_x, tl_y), (tl_x + 48, tl_y + 115), (35, 35, 35), -1)
        cv2.rectangle(out, (tl_x, tl_y), (tl_x + 48, tl_y + 115), (100, 100, 100), 2)

        # Bulbs
        # Red
        red_color = (0, 0, 255) if self.signal_state == "RED" else (30, 30, 70)
        cv2.circle(out, (tl_x + 24, tl_y + 22), 12, red_color, -1)
        # Yellow
        yel_color = (0, 220, 240) if self.signal_state == "YELLOW" else (30, 60, 60)
        cv2.circle(out, (tl_x + 24, tl_y + 57), 12, yel_color, -1)
        # Green
        grn_color = (0, 255, 0) if self.signal_state == "GREEN" else (20, 70, 20)
        cv2.circle(out, (tl_x + 24, tl_y + 92), 12, grn_color, -1)

        # Top-Left HUD Info Overlay
        hud_w = 340
        hud_h = 60
        sub_img = out[10:10+hud_h, 10:10+hud_w]
        white_rect = np.full(sub_img.shape, 20, dtype=np.uint8)
        res = cv2.addWeighted(sub_img, 0.25, white_rect, 0.75, 1.0)
        out[10:10+hud_h, 10:10+hud_w] = res
        cv2.rectangle(out, (10, 10), (10+hud_w, 10+hud_h), (80, 80, 80), 1)

        # Text on HUD
        density_colors = {"LOW": (0, 230, 0), "MEDIUM": (0, 215, 255), "HIGH": (0, 0, 255)}
        d_color = density_colors.get(self.analyzer.density_level, (255, 255, 255))
        
        cv2.putText(out, f"TOTAL COUNT: {self.analyzer.total_counted}  |  ACTIVE: {self.analyzer.active_count}",
                    (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (230, 230, 230), 1)
        
        cv2.putText(out, f"DENSITY: ", (18, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)
        cv2.putText(out, f"{self.analyzer.density_level}", (85, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, d_color, 2)
        
        cv2.putText(out, f"VIOLATIONS: {self.analyzer.violations_count}", (165, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 100, 255), 2)
        cv2.putText(out, f"FPS: {self.fps:.1f}", (280, 55),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)

        return out
