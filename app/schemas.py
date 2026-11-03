import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ViolationRecordBase(BaseModel):
    violation_type: str
    vehicle_type: str
    vehicle_id: int
    confidence: float
    evidence_path: str
    video_source: Optional[str] = "Live Stream"
    details: Optional[str] = ""
    status: Optional[str] = "Logged"

class ViolationRecordCreate(ViolationRecordBase):
    pass

class ViolationRecordResponse(ViolationRecordBase):
    id: int
    timestamp: datetime.datetime

    class Config:
        from_attributes = True

class TrafficStatsResponse(BaseModel):
    total_vehicles_counted: int
    active_vehicles_count: int
    counts_by_class: Dict[str, int]
    density_level: str
    density_ratio: float
    violations_count: int
    violations_by_type: Dict[str, int]
    signal_state: str
    fps: float
    video_source: str

class VideoSourceUpdate(BaseModel):
    source_type: str # "sample", "webcam", "upload"
    source_path: Optional[str] = None
    webcam_index: Optional[int] = 0

class SettingsUpdate(BaseModel):
    confidence_threshold: Optional[float] = None
    stop_line_y: Optional[float] = None # percentage of height (0.0 - 1.0)
    allowed_direction: Optional[str] = None # "down", "up", "left", "right"
    traffic_light_mode: Optional[str] = None # "auto", "manual_red", "manual_green", "manual_yellow"
    traffic_light_green_sec: Optional[float] = None
    traffic_light_yellow_sec: Optional[float] = None
    traffic_light_red_sec: Optional[float] = None
