import time
from typing import List, Dict, Any, Optional
from app.config import DENSITY_LOW_MAX, DENSITY_MED_MAX
from app.core.tracker import Track

class TrafficAnalyzer:
    def __init__(self):
        self.total_counted = 0
        self.class_counts = {
            "car": 0,
            "motorcycle": 0,
            "bus": 0,
            "truck": 0,
            "bicycle": 0
        }
        self.counted_ids = set()
        
        # Vehicle timestamps for flow rate calculation
        self.count_timestamps = []
        
        # Current active statistics
        self.active_count = 0
        self.density_level = "LOW"
        self.density_ratio = 0.0
        self.violations_count = 0
        self.violations_by_type = {
            "Red Light Violation": 0,
            "Wrong-Way Driving": 0,
            "Triple Riding": 0,
            "No Helmet": 0
        }

    def process_tracks(self, tracks: List[Track], frame_shape: tuple):
        """
        Processes active tracks in current frame, updates unique counts and traffic density.
        """
        now = time.time()
        self.active_count = len(tracks)

        # Update unique cumulative vehicle counts
        total_box_area = 0
        for track in tracks:
            bx1, by1, bx2, by2 = track.box
            bw = max(0, bx2 - bx1)
            bh = max(0, by2 - by1)
            total_box_area += (bw * bh)

            if not track.counted and track.track_id not in self.counted_ids:
                track.counted = True
                self.counted_ids.add(track.track_id)
                self.total_counted += 1
                
                cname = track.class_name
                if cname in self.class_counts:
                    self.class_counts[cname] += 1
                else:
                    self.class_counts[cname] = 1

                self.count_timestamps.append(now)

        # Clean old timestamps (> 60s)
        self.count_timestamps = [t for t in self.count_timestamps if (now - t) <= 60.0]

        # Calculate density
        if self.active_count <= DENSITY_LOW_MAX:
            self.density_level = "LOW"
        elif self.active_count <= DENSITY_MED_MAX:
            self.density_level = "MEDIUM"
        else:
            self.density_level = "HIGH"

        # Frame area occupancy ratio
        fh, fw = frame_shape[:2]
        frame_area = max(1, fw * fh)
        self.density_ratio = min(1.0, round(total_box_area / frame_area, 3))

    def record_violation(self, violation_type: str):
        self.violations_count += 1
        if violation_type in self.violations_by_type:
            self.violations_by_type[violation_type] += 1
        else:
            self.violations_by_type[violation_type] = 1

    @property
    def flow_rate_per_min(self) -> int:
        """Estimated vehicle flow per minute based on rolling 60-second window."""
        return len(self.count_timestamps)

    def get_stats_dict(self, signal_state: str = "GREEN", fps: float = 0.0, video_source: str = "") -> Dict[str, Any]:
        return {
            "total_vehicles_counted": self.total_counted,
            "active_vehicles_count": self.active_count,
            "counts_by_class": self.class_counts.copy(),
            "density_level": self.density_level,
            "density_ratio": self.density_ratio,
            "flow_rate_per_min": self.flow_rate_per_min,
            "violations_count": self.violations_count,
            "violations_by_type": self.violations_by_type.copy(),
            "signal_state": signal_state,
            "fps": round(fps, 1),
            "video_source": video_source
        }

    def reset(self):
        self.total_counted = 0
        for k in self.class_counts:
            self.class_counts[k] = 0
        self.counted_ids.clear()
        self.count_timestamps.clear()
        self.active_count = 0
        self.density_level = "LOW"
        self.density_ratio = 0.0
        self.violations_count = 0
        for k in self.violations_by_type:
            self.violations_by_type[k] = 0
