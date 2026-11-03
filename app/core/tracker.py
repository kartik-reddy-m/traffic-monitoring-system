import numpy as np
from scipy.optimize import linear_sum_assignment
from typing import List, Dict, Any, Optional

def compute_iou(boxA, boxB):
    # box format: [x1, y1, x2, y2]
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA) * max(0, yB - yA)
    boxAArea = max(1, (boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
    boxBArea = max(1, (boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

class Track:
    def __init__(self, track_id: int, box: List[int], class_id: int, class_name: str, conf: float):
        self.track_id = track_id
        self.box = box
        self.class_id = class_id
        self.class_name = class_name
        self.conf = conf
        self.lost_frames = 0
        self.age = 1
        
        cx = int((box[0] + box[2]) / 2)
        cy = int((box[1] + box[3]) / 2)
        self.history = [(cx, cy)] # list of centroids
        
        # Traffic & Violation state
        self.counted = False
        self.has_violated = False
        self.violations = set() # e.g. {"red_light", "wrong_way", "triple_riding", "no_helmet"}
        self.direction_vector = (0.0, 0.0)

    def update(self, box: List[int], conf: float):
        self.box = box
        self.conf = conf
        self.lost_frames = 0
        self.age += 1
        
        cx = int((box[0] + box[2]) / 2)
        cy = int((box[1] + box[3]) / 2)
        self.history.append((cx, cy))
        if len(self.history) > 30:
            self.history.pop(0)

        # Update smoothed direction vector over last 5-10 frames
        if len(self.history) >= 4:
            past_cx, past_cy = self.history[-4]
            dx = cx - past_cx
            dy = cy - past_cy
            dist = np.hypot(dx, dy)
            if dist > 5.0:
                self.direction_vector = (dx / dist, dy / dist)

    @property
    def centroid(self):
        if self.history:
            return self.history[-1]
        return (int((self.box[0] + self.box[2]) / 2), int((self.box[1] + self.box[3]) / 2))

    @property
    def prev_centroid(self):
        if len(self.history) >= 2:
            return self.history[-2]
        return self.centroid


class VehicleTracker:
    def __init__(self, max_lost: int = 15, iou_threshold: float = 0.3):
        self.next_id = 1
        self.tracks: Dict[int, Track] = {}
        self.max_lost = max_lost
        self.iou_threshold = iou_threshold

    def update(self, detections: List[Dict[str, Any]]) -> List[Track]:
        """
        Updates tracks with detections for the current frame using Hungarian algorithm.
        detections: list of dicts [{'box': [x1, y1, x2, y2], 'conf': float, 'class_id': int, 'class_name': str}]
        """
        active_track_ids = list(self.tracks.keys())
        num_tracks = len(active_track_ids)
        num_dets = len(detections)

        if num_tracks == 0:
            for det in detections:
                new_track = Track(
                    self.next_id,
                    det["box"],
                    det["class_id"],
                    det["class_name"],
                    det["conf"]
                )
                self.tracks[self.next_id] = new_track
                self.next_id += 1
            return list(self.tracks.values())

        if num_dets == 0:
            to_delete = []
            for tid, track in self.tracks.items():
                track.lost_frames += 1
                if track.lost_frames > self.max_lost:
                    to_delete.append(tid)
            for tid in to_delete:
                del self.tracks[tid]
            return [t for t in self.tracks.values() if t.lost_frames == 0]

        # Cost matrix based on IoU and centroid distance
        cost_matrix = np.zeros((num_tracks, num_dets), dtype=np.float32)

        for i, tid in enumerate(active_track_ids):
            track_box = self.tracks[tid].box
            tcx, tcy = self.tracks[tid].centroid
            for j, det in enumerate(detections):
                det_box = det["box"]
                iou = compute_iou(track_box, det_box)
                
                # Check class match preference
                class_penalty = 0.0 if self.tracks[tid].class_id == det["class_id"] else 0.5
                
                dcx = (det_box[0] + det_box[2]) / 2.0
                dcy = (det_box[1] + det_box[3]) / 2.0
                dist = np.hypot(tcx - dcx, tcy - dcy) / 300.0 # normalized dist

                # Cost is high when IoU is low
                cost_matrix[i, j] = (1.0 - iou) + class_penalty + min(dist, 1.0) * 0.5

        # Solve assignment problem
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        assigned_tracks = set()
        assigned_dets = set()

        for r, c in zip(row_ind, col_ind):
            tid = active_track_ids[r]
            det = detections[c]
            iou = compute_iou(self.tracks[tid].box, det["box"])

            # If match is plausible
            if iou >= self.iou_threshold or cost_matrix[r, c] < 0.8:
                self.tracks[tid].update(det["box"], det["conf"])
                assigned_tracks.add(r)
                assigned_dets.add(c)

        # Unmatched tracks
        to_delete = []
        for i, tid in enumerate(active_track_ids):
            if i not in assigned_tracks:
                self.tracks[tid].lost_frames += 1
                if self.tracks[tid].lost_frames > self.max_lost:
                    to_delete.append(tid)

        for tid in to_delete:
            del self.tracks[tid]

        # Unmatched detections -> create new tracks
        for j, det in enumerate(detections):
            if j not in assigned_dets:
                new_track = Track(
                    self.next_id,
                    det["box"],
                    det["class_id"],
                    det["class_name"],
                    det["conf"]
                )
                self.tracks[self.next_id] = new_track
                self.next_id += 1

        # Return currently visible tracks (lost_frames == 0)
        return [t for t in self.tracks.values() if t.lost_frames == 0]

    def reset(self):
        self.tracks.clear()
        self.next_id = 1
