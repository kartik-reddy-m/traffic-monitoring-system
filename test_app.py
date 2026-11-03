import sys
import os
import time
import threading
import urllib.request
import json
from pathlib import Path

# Set paths
base_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(base_dir))

os.environ["YOLO_CONFIG_DIR"] = str(base_dir / "temp_yolo")
os.environ["MPLCONFIGDIR"] = str(base_dir / "temp_mpl")

import uvicorn
from app.main import app

class ServerThread(threading.Thread):
    def __init__(self):
        super().__init__()
        self.config = uvicorn.Config(app, host="127.0.0.1", port=8000, log_level="warning")
        self.server = uvicorn.Server(self.config)
        self.daemon = True

    def run(self):
        self.server.run()

    def stop(self):
        self.server.should_exit = True

def run_tests():
    print("[TEST] Starting FastAPI server on http://127.0.0.1:8000 in background thread...")
    server_thread = ServerThread()
    server_thread.start()

    time.sleep(3.5) # Wait for startup

    test_results = []

    def check(name, url, method="GET", data=None, headers=None):
        try:
            req = urllib.request.Request(url, method=method)
            if headers:
                for k, v in headers.items():
                    req.add_header(k, v)
            if data:
                req.data = json.dumps(data).encode("utf-8")
                req.add_header("Content-Type", "application/json")

            with urllib.request.urlopen(req, timeout=10) as resp:
                status = resp.status
                body = resp.read()
                print(f"  [+] {name}: Status {status} (Length: {len(body)})")
                test_results.append((name, True, status))
                return body
        except Exception as e:
            print(f"  [-] {name} FAILED: {e}")
            test_results.append((name, False, str(e)))
            return None

    print("\n--- Running Endpoint Tests ---")
    check("Health Check", "http://127.0.0.1:8000/health")
    check("Frontend Webpage", "http://127.0.0.1:8000/")
    
    stats_body = check("Live Stats API", "http://127.0.0.1:8000/api/monitoring/stats")
    if stats_body:
        stats = json.loads(stats_body.decode("utf-8"))
        print(f"      Stats content: total={stats.get('total_vehicles_counted')}, active={stats.get('active_vehicles_count')}, density={stats.get('density_level')}, signal={stats.get('signal_state')}")

    check("Violations API", "http://127.0.0.1:8000/api/violations")
    check("Video Sources API", "http://127.0.0.1:8000/api/videos/sources")
    check("Statistics Summary API", "http://127.0.0.1:8000/api/statistics/summary")

    # Test settings update
    check("Update Settings API", "http://127.0.0.1:8000/api/monitoring/settings", method="POST", data={
        "traffic_light_mode": "manual_red",
        "stop_line_y": 0.65,
        "allowed_direction": "down"
    })

    # Test stream packet read
    print("\n--- Testing Live Video Stream (reading MJPEG frame chunk) ---")
    try:
        req = urllib.request.Request("http://127.0.0.1:8000/api/monitoring/stream")
        with urllib.request.urlopen(req, timeout=12) as stream_resp:
            # Read first 10,000 bytes
            chunk = stream_resp.read(10000)
            if b"--frame" in chunk or b"Content-Type: image/jpeg" in chunk:
                print(f"  [+] Video Stream: Received valid MJPEG JPEG frame chunk ({len(chunk)} bytes)!")
                test_results.append(("Video Stream MJPEG", True, "Stream Active"))
            else:
                print(f"  [-] Video Stream: Received unexpected data ({len(chunk)} bytes)")
                test_results.append(("Video Stream MJPEG", False, "Missing JPEG headers"))
    except Exception as e:
        print(f"  [-] Video Stream Error: {e}")
        test_results.append(("Video Stream MJPEG", False, str(e)))

    # Shutdown
    print("\n[TEST] Stopping background test server...")
    server_thread.stop()
    time.sleep(1.0)

    # Summary
    print("\n" + "=" * 50)
    print("           TEST EXECUTION SUMMARY")
    print("=" * 50)
    all_passed = True
    for name, passed, info in test_results:
        status_str = "PASS" if passed else "FAIL"
        print(f" {status_str.ljust(6)} | {name.ljust(25)} | {info}")
        if not passed:
            all_passed = False
    print("=" * 50)

    if all_passed:
        print("[SUCCESS] All system verification tests PASSED flawlessly!")
        sys.exit(0)
    else:
        print("[ERROR] One or more tests failed.")
        sys.exit(1)

if __name__ == "__main__":
    run_tests()
