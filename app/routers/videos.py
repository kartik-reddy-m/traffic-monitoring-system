import os
import shutil
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Request, HTTPException
from app.config import SAMPLE_DATA_DIR, UPLOADS_DIR
from app.schemas import VideoSourceUpdate

router = APIRouter(prefix="/api/videos", tags=["Videos"])

def get_processor(request: Request):
    return request.app.state.video_processor

@router.get("/sources")
def list_video_sources():
    sample_videos = []
    if SAMPLE_DATA_DIR.exists():
        for p in SAMPLE_DATA_DIR.glob("*.*"):
            if p.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv"]:
                sample_videos.append({
                    "name": p.name,
                    "path": str(p),
                    "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
                    "type": "sample"
                })

    uploaded_videos = []
    if UPLOADS_DIR.exists():
        for p in UPLOADS_DIR.glob("*.*"):
            if p.suffix.lower() in [".mp4", ".avi", ".mov", ".mkv"]:
                uploaded_videos.append({
                    "name": p.name,
                    "path": str(p),
                    "size_mb": round(p.stat().st_size / (1024 * 1024), 2),
                    "type": "uploaded"
                })

    return {
        "samples": sample_videos,
        "uploads": uploaded_videos,
        "webcam_available": True
    }

@router.post("/select")
def select_video_source(update: VideoSourceUpdate, request: Request):
    processor = get_processor(request)
    
    if update.source_type == "webcam":
        processor.set_source("webcam", webcam_index=update.webcam_index or 0)
        return {"status": "success", "message": f"Switched to Webcam #{update.webcam_index or 0}"}
    
    if not update.source_path or not os.path.exists(update.source_path):
        raise HTTPException(status_code=400, detail="Invalid source path or file not found")

    processor.set_source(update.source_type, source_path=update.source_path)
    return {"status": "success", "message": f"Switched to {os.path.basename(update.source_path)}"}

@router.post("/upload")
async def upload_video(file: UploadFile = File(...), auto_play: bool = Form(True), request: Request = None):
    allowed_exts = {".mp4", ".avi", ".mov", ".mkv"}
    ext = Path(file.filename).suffix.lower()
    if ext not in allowed_exts:
        raise HTTPException(status_code=400, detail=f"Unsupported video format: {ext}. Allowed: {allowed_exts}")

    clean_filename = "".join(c for c in file.filename if c.isalnum() or c in "._- ")
    save_path = UPLOADS_DIR / clean_filename

    with open(save_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    if auto_play and request is not None:
        processor = get_processor(request)
        processor.set_source("upload", source_path=str(save_path))

    return {
        "status": "success",
        "filename": clean_filename,
        "path": str(save_path),
        "size_mb": round(save_path.stat().st_size / (1024 * 1024), 2),
        "active": auto_play
    }
