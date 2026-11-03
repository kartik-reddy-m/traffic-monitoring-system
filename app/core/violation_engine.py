import cv2
import datetime
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.config import EVIDENCE_DIR, MODELS_DIR
from app.database import ViolationRecord
from app.core.tracker import Track

def ccw(A, B, C):
    return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

def line_segments_intersect(A, B, C, D):
    """Returns True if line segment AB intersects line segment CD."""
    return ccw(A, C, D) != ccw(B, C, D) and ccw(A, B, C) != ccw(A, B, D)

class ViolationEngine:
    def __init__(self, evidence_dir: Path = EVIDENCE_DIR):
        self.evidence_dir = evidence_dir
        self.evidence_dir.mkdir(parents=True, exist_ok=True)
        
        # Check if optional custom helmet model is present
        self.custom_helmet_model = None
        custom_helmet_path = MODELS_DIR / "helmet_yolov8.pt"
        if custom_helmet_path.exists():
            try:
                from ultralytics import YOLO
                self.custom_helmet_model = YOLO(str(custom_helmet_path))
                print(f"[ViolationEngine] Loaded custom helmet model: {custom_helmet_path}")
            except Exception as e:
                print(f"[ViolationEngine] Warning: Could not load custom helmet model: {e}")

    def check_red_light(
        self,
        track: Track,
        frame: np.ndarray,
        signal_state: str,
        stop_line: Tuple[Tuple[int, int], Tuple[int, int]],
        db: Session,
        video_source: str = "Live Feed"
    ) -> Optional[ViolationRecord]:
        """
        Detects if vehicle crosses the stop line while signal is RED.
        """
        if signal_state != "RED":
            return None
        if "red_light" in track.violations:
            return None

        # Check line crossing
        pt_a = track.prev_centroid
        pt_b = track.centroid
        line_p1, line_p2 = stop_line

        # Only check if vehicle actually moved
        if pt_a == pt_b:
            return None

        # Check if centroid trajectory crosses stop line
        has_crossed = line_segments_intersect(pt_a, pt_b, line_p1, line_p2)
        
        # Also check if vehicle bottom edge crossed (for realistic approach)
        if not has_crossed:
            bottom_prev = (pt_a[0], track.box[3] - 10)
            bottom_curr = (pt_b[0], track.box[3])
            has_crossed = line_segments_intersect(bottom_prev, bottom_curr, line_p1, line_p2)

        if has_crossed:
            track.violations.add("red_light")
            track.has_violated = True
            
            # Save evidence snapshot
            evidence_rel_path = self._save_evidence(
                frame=frame,
                track=track,
                violation_type="Red Light Violation",
                details=f"Crossed stop-line at {pt_b} during RED signal phase",
                stop_line=stop_line,
                signal_state=signal_state
            )

            record = ViolationRecord(
                timestamp=datetime.datetime.utcnow(),
                violation_type="Red Light Violation",
                vehicle_type=track.class_name,
                vehicle_id=track.track_id,
                confidence=round(track.conf, 3),
                evidence_path=evidence_rel_path,
                video_source=video_source,
                details=f"Crossed stop-line while signal was RED. Trajectory: {pt_a} -> {pt_b}",
                status="Logged"
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        return None

    def check_wrong_way(
        self,
        track: Track,
        frame: np.ndarray,
        allowed_direction: str,
        db: Session,
        video_source: str = "Live Feed"
    ) -> Optional[ViolationRecord]:
        """
        Detects if vehicle travels against the allowed flow direction.
        """
        if "wrong_way" in track.violations:
            return None
        if len(track.history) < 6:
            return None

        # Map allowed direction name to unit vector
        dir_map = {
            "down": (0.0, 1.0),
            "up": (0.0, -1.0),
            "right": (1.0, 0.0),
            "left": (-1.0, 0.0)
        }
        target_vec = dir_map.get(allowed_direction.lower(), (0.0, 1.0))

        # Calculate total displacement over last 6-10 frames
        start_pt = track.history[-6]
        curr_pt = track.history[-1]
        dx = curr_pt[0] - start_pt[0]
        dy = curr_pt[1] - start_pt[1]
        dist = np.hypot(dx, dy)

        # Minimum movement distance to filter stationary jitter
        if dist < 25.0:
            return None

        ux = dx / dist
        uy = dy / dist

        # Dot product
        dot = (ux * target_vec[0]) + (uy * target_vec[1])

        # If dot product < -0.4, direction opposes allowed flow (>115 degrees)
        if dot < -0.4:
            track.violations.add("wrong_way")
            track.has_violated = True

            evidence_rel_path = self._save_evidence(
                frame=frame,
                track=track,
                violation_type="Wrong-Way Driving",
                details=f"Direction vector ({ux:.2f}, {uy:.2f}) opposes allowed flow ({allowed_direction}) with dot={dot:.2f}"
            )

            record = ViolationRecord(
                timestamp=datetime.datetime.utcnow(),
                violation_type="Wrong-Way Driving",
                vehicle_type=track.class_name,
                vehicle_id=track.track_id,
                confidence=round(track.conf, 3),
                evidence_path=evidence_rel_path,
                video_source=video_source,
                details=f"Vehicle moving opposite to allowed {allowed_direction} direction (opposing factor: {dot:.2f})",
                status="Logged"
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        return None

    def check_triple_riding(
        self,
        track: Track,
        persons: List[Dict[str, Any]],
        frame: np.ndarray,
        db: Session,
        video_source: str = "Live Feed"
    ) -> Optional[ViolationRecord]:
        """
        Detects if 3 or more riders are present on a single two-wheeler (motorcycle or bicycle).
        """
        if track.class_name not in ["motorcycle", "bicycle"]:
            return None
        if "triple_riding" in track.violations:
            return None

        bx1, by1, bx2, by2 = track.box
        bw = bx2 - bx1
        bh = by2 - by1

        # Search zone for riders: riders typically sit on or slightly above the two-wheeler
        zone_x1 = bx1 - int(bw * 0.25)
        zone_x2 = bx2 + int(bw * 0.25)
        zone_y1 = by1 - int(bh * 0.40)
        zone_y2 = by2

        associated_persons = []
        for p in persons:
            px1, py1, px2, py2 = p["box"]
            pcx = (px1 + px2) / 2
            pcy = (py1 + py2) / 2

            # Check if person center falls in the two-wheeler riding zone
            if zone_x1 <= pcx <= zone_x2 and zone_y1 <= pcy <= zone_y2:
                associated_persons.append(p)

        if len(associated_persons) >= 3:
            track.violations.add("triple_riding")
            track.has_violated = True

            evidence_rel_path = self._save_evidence(
                frame=frame,
                track=track,
                violation_type="Triple Riding",
                details=f"{len(associated_persons)} riders detected on {track.class_name} #{track.track_id}",
                extra_boxes=[p["box"] for p in associated_persons]
            )

            record = ViolationRecord(
                timestamp=datetime.datetime.utcnow(),
                violation_type="Triple Riding",
                vehicle_type=track.class_name,
                vehicle_id=track.track_id,
                confidence=round(track.conf, 3),
                evidence_path=evidence_rel_path,
                video_source=video_source,
                details=f"Detected {len(associated_persons)} persons on two-wheeler (Max legal capacity: 2 riders)",
                status="Logged"
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            return record

        return None

    def check_no_helmet(
        self,
        track: Track,
        persons: List[Dict[str, Any]],
        frame: np.ndarray,
        db: Session,
        video_source: str = "Live Feed"
    ) -> Optional[ViolationRecord]:
        """
        Detects if rider(s) on a two-wheeler are not wearing helmets.
        Uses head ROI computer vision analysis (hair/skin color tone vs helmet shell contour)
        or custom helmet model if provided.
        """
        if track.class_name not in ["motorcycle", "bicycle"]:
            return None
        if "no_helmet" in track.violations:
            return None

        bx1, by1, bx2, by2 = track.box
        bw = bx2 - bx1
        bh = by2 - by1

        # Find riders on this bike
        riders = []
        for p in persons:
            px1, py1, px2, py2 = p["box"]
            pcx = (px1 + px2) / 2
            pcy = (py1 + py2) / 2
            if (bx1 - bw * 0.2) <= pcx <= (bx2 + bw * 0.2) and (by1 - bh * 0.4) <= pcy <= by2:
                riders.append(p)

        if not riders:
            return None

        # Check each rider's head region
        for rider in riders:
            rx1, ry1, rx2, ry2 = rider["box"]
            rw = max(1, rx2 - rx1)
            rh = max(1, ry2 - ry1)

            # Head region is top ~28% of person box
            hx1 = max(0, rx1)
            hy1 = max(0, ry1)
            hx2 = min(frame.shape[1], rx2)
            hy2 = min(frame.shape[0], ry1 + int(rh * 0.28))

            head_crop = frame[hy1:hy2, hx1:hx2]
            if head_crop.size == 0 or head_crop.shape[0] < 10 or head_crop.shape[1] < 10:
                continue

            has_helmet = self._analyze_head_for_helmet(head_crop)

            if not has_helmet:
                track.violations.add("no_helmet")
                track.has_violated = True

                evidence_rel_path = self._save_evidence(
                    frame=frame,
                    track=track,
                    violation_type="No Helmet Detection",
                    details=f"Two-wheeler rider detected without protective helmet",
                    extra_boxes=[rider["box"], [hx1, hy1, hx2, hy2]]
                )

                record = ViolationRecord(
                    timestamp=datetime.datetime.utcnow(),
                    violation_type="No Helmet",
                    vehicle_type=track.class_name,
                    vehicle_id=track.track_id,
                    confidence=round(rider["conf"], 3),
                    evidence_path=evidence_rel_path,
                    video_source=video_source,
                    details=f"Rider on {track.class_name} #{track.track_id} detected without mandatory safety helmet",
                    status="Logged"
                )
                db.add(record)
                db.commit()
                db.refresh(record)
                return record

        return None

    def _analyze_head_for_helmet(self, head_crop: np.ndarray) -> bool:
        """
        Determines if head region has a helmet:
        1. If custom helmet model is available, run inference.
        2. Otherwise, use computer vision analysis:
           - Helmets present a high curvature convex shell, uniform outer reflection, or protective cap.
           - Bare head shows high human hair / skin tone color presence, non-uniform hairline, lack of shell contour.
        """
        if self.custom_helmet_model is not None:
            try:
                res = self.custom_helmet_model(head_crop, conf=0.4, verbose=False)
                for b in res[0].boxes:
                    cname = self.custom_helmet_model.names[int(b.cls[0].item())].lower()
                    if "helmet" in cname and "no" not in cname:
                        return True
                    if "no_helmet" in cname or "without" in cname:
                        return False
            except Exception:
                pass

        # Computer vision analysis on head crop
        try:
            hsv = cv2.cvtColor(head_crop, cv2.COLOR_BGR2HSV)
            h, w = head_crop.shape[:2]

            # Skin tone mask in HSV
            lower_skin = np.array([0, 20, 70], dtype=np.uint8)
            upper_skin = np.array([25, 255, 255], dtype=np.uint8)
            skin_mask = cv2.inRange(hsv, lower_skin, upper_skin)
            skin_ratio = cv2.countNonZero(skin_mask) / float(h * w)

            # Hair/dark tone mask
            lower_hair = np.array([0, 0, 0], dtype=np.uint8)
            upper_hair = np.array([180, 255, 50], dtype=np.uint8)
            hair_mask = cv2.inRange(hsv, lower_hair, upper_hair)
            hair_ratio = cv2.countNonZero(hair_mask) / float(h * w)

            # Edge density (hair has high textural edge frequency; smooth helmet shell has low high-frequency texture)
            gray = cv2.cvtColor(head_crop, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            edge_density = cv2.countNonZero(edges) / float(h * w)

            # Circularity of upper crown
            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            is_smooth_curve = False
            for c in contours:
                area = cv2.contourArea(c)
                peri = cv2.arcLength(c, True)
                if peri > 0:
                    circularity = 4 * np.pi * (area / (peri * peri))
                    if circularity > 0.65:
                        is_smooth_curve = True
                        break

            # If smooth helmet shell contour detected or low bare skin/hair
            if is_smooth_curve and skin_ratio < 0.20:
                return True

            # If prominent bare hair/skin without smooth helmet contour -> No Helmet
            if (skin_ratio + hair_ratio > 0.45) and not is_smooth_curve:
                return False

            return True
        except Exception:
            return True

    def _save_evidence(
        self,
        frame: np.ndarray,
        track: Track,
        violation_type: str,
        details: str,
        stop_line: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None,
        signal_state: Optional[str] = None,
        extra_boxes: Optional[List[List[int]]] = None
    ) -> str:
        """
        Creates an annotated evidence snapshot with headers and details,
        saves to disk, and returns the relative path for web display.
        """
        snap = frame.copy()
        h, w = snap.shape[:2]

        # Draw vehicle bounding box in bright red/neon
        bx1, by1, bx2, by2 = track.box
        cv2.rectangle(snap, (bx1, by1), (bx2, by2), (0, 0, 255), 3)

        # Draw extra boxes if provided (e.g. riders, head crop)
        if extra_boxes:
            for ebox in extra_boxes:
                cv2.rectangle(snap, (ebox[0], ebox[1]), (ebox[2], ebox[3]), (0, 140, 255), 2)

        # Draw stop line if relevant
        if stop_line and signal_state == "RED":
            p1, p2 = stop_line
            cv2.line(snap, p1, p2, (0, 0, 255), 4)
            cv2.putText(snap, "STOP LINE (SIGNAL RED)", (p1[0] + 10, max(20, p1[1] - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)

        # Top Header Banner
        banner_h = 70
        canvas = np.zeros((h + banner_h + 35, w, 3), dtype=np.uint8)
        
        # Red Header
        canvas[:banner_h, :] = (20, 20, 160) # Dark red / crimson
        cv2.putText(canvas, f"TRAFFIC VIOLATION EVIDENCE: {violation_type.upper()}",
                    (15, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sub_text = f"Vehicle: {track.class_name.upper()} #{track.track_id} | Conf: {track.conf:.2f} | Time: {now_str}"
        cv2.putText(canvas, sub_text, (15, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (220, 220, 220), 1)

        # Insert frame
        canvas[banner_h:banner_h + h, :] = snap

        # Bottom details bar
        canvas[banner_h + h:, :] = (30, 30, 30)
        cv2.putText(canvas, f"Details: {details[:95]}", (15, banner_h + h + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1)

        # Generate unique filename
        filename = f"violation_{track.track_id}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
        save_path = self.evidence_dir / filename
        cv2.imwrite(str(save_path), canvas)

        return f"/static/evidence/{filename}"
