import cv2
import numpy as np
from pathlib import Path

def generate_traffic_demo(output_path: str = "sample_data/traffic_violations_demo.mp4", num_frames: int = 150):
    width, height = 720, 480
    fps = 20
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    print(f"Generating synthetic traffic benchmark video at: {output_path} ({num_frames} frames)...")

    for f in range(num_frames):
        # Create road scene
        frame = np.full((height, width, 3), (60, 60, 60), dtype=np.uint8)

        # Sidewalks
        frame[:, :60] = (140, 140, 140)
        frame[:, width-60:] = (140, 140, 140)

        # Lane dividers (dashed yellow)
        center_x = width // 2
        lane_w = (width - 120) // 2
        for y in range(0, height, 40):
            if (y // 40) % 2 == 0:
                cv2.line(frame, (center_x, y), (center_x, y + 25), (0, 215, 255), 3)

        # Stop line (white)
        stop_y = int(height * 0.65)
        cv2.line(frame, (60, stop_y), (width - 60, stop_y), (255, 255, 255), 4)

        # Moving Vehicle 1: Car moving down (Lane 1)
        v1_y = int(20 + (f * 4.5)) % (height + 100) - 80
        v1_x = 160
        # Car body
        cv2.rectangle(frame, (v1_x, v1_y), (v1_x + 90, v1_y + 140), (40, 40, 200), -1)
        # Windshield
        cv2.rectangle(frame, (v1_x + 10, v1_y + 25), (v1_x + 80, v1_y + 55), (180, 220, 240), -1)
        # Roof
        cv2.rectangle(frame, (v1_x + 15, v1_y + 55), (v1_x + 75, v1_y + 95), (20, 20, 150), -1)
        # Rear window
        cv2.rectangle(frame, (v1_x + 10, v1_y + 95), (v1_x + 80, v1_y + 115), (180, 220, 240), -1)

        # Moving Vehicle 2: Car moving UP (WRONG WAY in Lane 1!)
        if f > 30:
            v2_y = height - int((f - 30) * 4)
            v2_x = 260
            if -80 < v2_y < height + 50:
                cv2.rectangle(frame, (v2_x, v2_y), (v2_x + 85, v2_y + 130), (220, 100, 30), -1)
                cv2.rectangle(frame, (v2_x + 10, v2_y + 75), (v2_x + 75, v2_y + 105), (180, 220, 240), -1)
                cv2.rectangle(frame, (v2_x + 15, v2_y + 35), (v2_x + 70, v2_y + 75), (180, 70, 20), -1)

        # Moving Vehicle 3: Motorcycle with riders in Lane 2
        v3_y = int(50 + (f * 3.8)) % (height + 80) - 60
        v3_x = 480
        # Motorcycle chassis
        cv2.rectangle(frame, (v3_x + 20, v3_y), (v3_x + 40, v3_y + 100), (30, 30, 30), -1)
        # Wheels
        cv2.circle(frame, (v3_x + 30, v3_y + 15), 14, (10, 10, 10), -1)
        cv2.circle(frame, (v3_x + 30, v3_y + 85), 14, (10, 10, 10), -1)
        # Rider 1 (Helmeted)
        cv2.circle(frame, (v3_x + 30, v3_y + 40), 12, (20, 20, 20), -1) # Dark helmet
        # Rider 2 (Unhelmeted bare head)
        cv2.circle(frame, (v3_x + 30, v3_y + 65), 11, (160, 200, 230), -1) # Skin tone / hair

        out.write(frame)

    out.release()
    print("Demo video generation complete.")

if __name__ == "__main__":
    generate_traffic_demo()
