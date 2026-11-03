# AI Powered Smart Traffic Monitoring and Violation Detection

A full-stack, automated intelligent traffic surveillance web application that detects vehicles, monitors traffic flow and density, and identifies traffic rule violations using deep learning (Ultralytics YOLOv8) and computer vision (OpenCV).

---

## 1. Key Features

### A. Vehicle Detection & Multi-Object Tracking
- **Multi-Class Vehicle Detection:** Detects cars, motorcycles/bikes, buses, trucks, and bicycles using YOLOv8 nano.
- **Bounding Boxes & Confidence Scores:** Visual overlays with distinct color-coding for each vehicle category.
- **Trajectory & Unique IDs:** Hungarian assignment algorithm (`scipy.optimize.linear_sum_assignment`) combines spatial IoU and centroid distance metrics to maintain unique vehicle tracks across frames, preventing duplicate counts.

### B. Real-Time Traffic Monitoring
- **Vehicle Categorization:** Cumulative unique vehicle counters categorized into Cars, Motorcycles/Bikes, Buses, and Trucks.
- **Active Vehicle Count:** Live measurement of vehicles currently present in the surveillance frame.
- **Traffic Density Estimation:** Real-time classification into **LOW**, **MEDIUM**, or **HIGH** density with visual badge indicators and frame occupancy ratio.
- **Flow Rate:** Automatic calculation of traffic flow rate (vehicles per minute).

### C. Traffic Violation Detection Engine
- **Red-Light Signal Violation:**
  - Virtual traffic signal state machine (Green, Yellow, Red) with auto-cycle or manual force controls.
  - Configurable virtual stop-line geometry across the roadway.
  - Automatically captures vehicles crossing the stop-line during the RED signal phase.
- **Wrong-Way Driving Detection:**
  - Calculates vehicle trajectory displacement vectors $\vec{v} = (\Delta x, \Delta y)$ over historical frames.
  - Compares vehicle direction against the allowed lane flow vector (Downward, Upward, Leftward, Rightward).
  - Vehicles moving opposite to the flow (>115° deviation) are flagged.
- **Triple Riding Detection:**
  - Detects riders on two-wheelers (motorcycles and bicycles).
  - Associates detected `person` bounding boxes with two-wheelers using spatial containment and vertical rider zone analysis.
  - Flags any motorcycle carrying 3 or more riders.
- **No Helmet Detection:**
  - Isolates the head ROI (top crown region) of two-wheeler riders.
  - Computer vision pipeline analyzes skin/hair tones vs protective helmet shell curvature and edge textures.
  - Supports drop-in custom helmet YOLO models (`models/helmet_yolov8.pt`) for specialized deep-learning helmet detection.

### D. Evidence Capture & Violation Records
- Saves full-frame evidence snapshots with a top violation header banner, vehicle ID, timestamp, and highlighted red bounding box to `static/evidence/`.
- Stores detailed records in SQLite (`traffic_monitoring.db`).
- Interactive history table with search, category filtering, evidence modal viewer, and one-click CSV export.

### E. Video Processing & Inputs
- **Bundled Sample Videos:** Real-world urban street video (`kitti_traffic.mp4`) and multi-lane violation demo video (`traffic_violations_demo.mp4`).
- **File Upload:** Upload any `.mp4`, `.avi`, `.mov`, or `.mkv` video for instant analysis.
- **Live Webcam:** Real-time stream processing from connected USB/integrated cameras.
- **High-Performance MJPEG Stream:** Frame-by-frame streaming with real-time HUD annotations.

---

## 2. Technology Stack

| Layer | Technology |
|---|---|
| **Programming Language** | Python 3.11 |
| **Deep Learning / AI** | Ultralytics YOLOv8 (`yolov8n.pt`) & PyTorch |
| **Computer Vision** | OpenCV (`cv2`) & SciPy (Hungarian algorithm) |
| **Backend Web Framework** | FastAPI & Uvicorn (ASGI) |
| **Database & ORM** | SQLite 3 & SQLAlchemy |
| **Frontend** | Vanilla HTML5, CSS3, JavaScript (Clean, minimal, responsive dashboard) |

---

## 3. Project Directory Structure

```
traffic_monitoring_app/
├── app/
│   ├── __init__.py
│   ├── config.py              # Application settings, paths, class maps, offline configs
│   ├── database.py            # SQLite schema models (ViolationRecord, TrafficLog)
│   ├── schemas.py             # Pydantic validation schemas
│   ├── main.py                # FastAPI app initialization, routes, lifecycle
│   ├── core/
│   │   ├── __init__.py
│   │   ├── detector.py        # YOLOv8 inference wrapper
│   │   ├── tracker.py         # Hungarian assignment & IoU multi-object tracker
│   │   ├── violation_engine.py# Violation detection algorithms & snapshot generator
│   │   ├── traffic_analyzer.py# Vehicle counter, traffic density & flow rate calculator
│   │   └── video_processor.py # Video capture, annotation overlays & MJPEG generator
│   └── routers/
│       ├── __init__.py
│       ├── monitoring.py      # Video stream & live stats API
│       ├── violations.py      # Violation query, filter, CSV export, delete API
│       ├── videos.py          # Video source switcher & file upload API
│       └── statistics.py      # Traffic density summary & historical timeline API
├── models/
│   └── yolov8n.pt             # Pre-configured YOLOv8 nano model weights
├── sample_data/
│   ├── kitti_traffic.mp4      # Real-world urban traffic video
│   ├── traffic_violations_demo.mp4 # Synthetic benchmark video with violations
│   └── generate_demo_video.py # Python script to generate synthetic test videos
├── static/
│   ├── css/style.css          # Clean, professional dashboard stylesheet
│   ├── js/
│   │   ├── app.js             # Navigation, modal popups, notifications
│   │   ├── dashboard.js       # Real-time statistics poller & category breakdown
│   │   ├── live_monitor.js    # Stream player, source selector, calibration controls
│   │   └── violations.js      # Live alert stream, history table, filters
│   └── evidence/              # Stored snapshot evidence images
├── templates/
│   └── index.html             # Single-page dashboard application
├── requirements.txt           # Python dependencies
├── run.py                     # Application startup entrypoint
├── test_app.py                # End-to-end automated test suite
├── test_violations.py         # Violation engine & persistence verification script
└── README.md                  # Complete documentation
```

---

## 4. Setup & Execution Instructions (Windows PowerShell)

### Step 1: Open Windows PowerShell and Navigate to Project
```powershell
cd C:\Users\khyat\.gemini\antigravity\scratch\traffic_monitoring_app
```

### Step 2: Install Dependencies (if not already installed)
The packages are already installed in the current environment. To reinstall or update:
```powershell
pip install -r requirements.txt
```

### Step 3: YOLO Model Configuration
The pre-trained **YOLOv8n** model (`yolov8n.pt`, 6.2 MB) is already placed inside the `models/` folder.
If you ever need to redownload the model manually, run:
```powershell
curl.exe -L "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8n.pt" -o "models\yolov8n.pt"
```

#### Optional: Custom Helmet Detection Model
The system has built-in computer vision algorithms to inspect rider head ROIs for helmets. If you train or download a specialized YOLO helmet model, simply place the `.pt` file inside the `models/` directory named `helmet_yolov8.pt`:
```
models/helmet_yolov8.pt
```
The application will automatically detect and load it on startup.

---

### Step 4: Run the Automated Verification Tests
Run the self-testing script to verify that all endpoints, the YOLO detector, the video stream, and database persistence operate correctly:
```powershell
python test_app.py
```
Expected output:
```
 PASS   | Health Check              | 200
 PASS   | Frontend Webpage          | 200
 PASS   | Live Stats API            | 200
 PASS   | Violations API            | 200
 PASS   | Video Sources API         | 200
 PASS   | Statistics Summary API    | 200
 PASS   | Update Settings API       | 200
 PASS   | Video Stream MJPEG        | Stream Active
==================================================
[SUCCESS] All system verification tests PASSED flawlessly!
```

---

### Step 5: Start the Application Server
Run the application using `run.py`:
```powershell
python run.py
```
Or directly with Uvicorn:
```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open your browser and navigate to:
```
http://127.0.0.1:8000
```

---

## 5. Website Navigation Guide

The application features 5 sections accessible via the sidebar:

1. **Dashboard:**
   - Real-time KPI summary: Total counted vehicles, Active vehicles, Traffic Density status, and Logged Violations.
   - Vehicle category breakdown counters (Cars, Motorcycles, Buses, Trucks).
   - Violation distribution breakdown (Red Light, Wrong Way, Triple Riding, No Helmet).
   - Recent violations table with instant snapshot previews.

2. **Live Monitoring:**
   - Live video stream display with real-time detection bounding boxes, track IDs, motion trails, and stop line.
   - Interactive Traffic Light widget with current phase display.
   - **Video Source Switcher:** Switch between bundled sample videos, uploaded videos, or live webcam.
   - **Video Upload:** Drag and drop or browse any video file to start monitoring.
   - **Traffic Signal Simulation:** Switch between Auto-Cycle and manual force RED / GREEN / YELLOW to test violation triggers.
   - **Rule Calibration:** Adjust the virtual stop-line position slider (height %), change allowed lane flow direction, and adjust detection confidence threshold.

3. **Violation Detection (Live Alerts):**
   - Real-time card feed showing every detected violation snapshot with time, vehicle class, ID, confidence, and video source.
   - Click "View Evidence Proof" to inspect the high-resolution evidence snapshot with annotated red warning banner.

4. **Violation History:**
   - Filterable table of all recorded violations.
   - Filter by violation type (Red Light, Wrong-Way, Triple Riding, No Helmet) and vehicle class (Car, Motorcycle, Bus, Truck).
   - Search by text (vehicle ID, notes, or video source).
   - **Export CSV:** One-click download of the complete violations database.
   - Individual deletion and "Clear All" controls.

5. **About System:**
   - Detailed architectural breakdown, algorithms, and model documentation.

---

## 6. REST API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Web dashboard application |
| `GET` | `/health` | Health check endpoint |
| `GET` | `/api/monitoring/stream` | Multipart MJPEG real-time video stream |
| `GET` | `/api/monitoring/stats` | Current live traffic and violation metrics |
| `POST`| `/api/monitoring/control` | Control stream (`action=pause`, `resume`, `reset`) |
| `POST`| `/api/monitoring/settings`| Update calibration (stop line, direction, signal mode) |
| `GET` | `/api/violations` | List violations with search and type filters |
| `DELETE`| `/api/violations/{id}` | Delete violation record and evidence image |
| `GET` | `/api/violations/export/csv` | Download complete violation records as CSV |
| `POST`| `/api/violations/clear` | Clear all violation records and evidence files |
| `GET` | `/api/videos/sources` | List available video sources (samples, uploads, webcam) |
| `POST`| `/api/videos/select` | Switch active video source |
| `POST`| `/api/videos/upload` | Upload video file (`.mp4`, `.avi`, `.mov`, `.mkv`) |
| `GET` | `/api/statistics/summary` | Aggregate violation and traffic density statistics |
| `GET` | `/api/statistics/timeline`| Historical vehicle count and density timeline |
