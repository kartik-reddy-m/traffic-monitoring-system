import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from app.config import STATIC_DIR, BASE_DIR
from app.database import init_db
from app.core.video_processor import VideoProcessor
from app.routers import monitoring, violations, videos, statistics

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database and Video Processor
    print("[Lifespan] Initializing database...")
    init_db()
    print("[Lifespan] Initializing Video Processor...")
    app.state.video_processor = VideoProcessor()
    yield
    # Shutdown: Release resources
    print("[Lifespan] Shutting down and releasing capture...")
    if hasattr(app.state, "video_processor") and app.state.video_processor.cap:
        app.state.video_processor.cap.release()

app = FastAPI(
    title="AI Powered Smart Traffic Monitoring and Violation Detection",
    description="Full-stack traffic surveillance, vehicle tracking, and automated traffic violation detection platform.",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates_dir = BASE_DIR / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Include API Routers
app.include_router(monitoring.router)
app.include_router(violations.router)
app.include_router(videos.router)
app.include_router(statistics.router)

@app.get("/", response_class=HTMLResponse)
async def serve_index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "Traffic Monitoring System"}
