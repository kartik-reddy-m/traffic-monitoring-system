from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from app.schemas import TrafficStatsResponse, SettingsUpdate
from typing import Dict, Any

router = APIRouter(prefix="/api/monitoring", tags=["Monitoring"])

def get_processor(request: Request):
    return request.app.state.video_processor

@router.get("/stream")
def video_stream(request: Request):
    processor = get_processor(request)
    return StreamingResponse(
        processor.generate_mjpeg_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/stats")
def get_live_stats(request: Request) -> Dict[str, Any]:
    processor = get_processor(request)
    return processor.get_current_stats()

@router.post("/control")
def control_stream(action: str, request: Request):
    processor = get_processor(request)
    if action == "pause":
        processor.is_paused = True
    elif action == "resume":
        processor.is_paused = False
    elif action == "reset":
        processor.tracker.reset()
        processor.analyzer.reset()
    return {"status": "success", "action": action, "is_paused": processor.is_paused}

@router.post("/settings")
def update_settings(settings: SettingsUpdate, request: Request):
    processor = get_processor(request)
    processor.update_settings(settings.model_dump(exclude_unset=True))
    return {"status": "success", "message": "Settings updated"}
