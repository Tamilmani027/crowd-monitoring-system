import cv2
import os
import sys

print("Python executable:", sys.executable)
print("Current working dir:", os.getcwd())

# Get the absolute path of the current script's directory
script_dir = os.path.dirname(os.path.abspath(__file__))

# Define potential video files to look for
video_files = ['input_video.mp4', 'input_video1.mp4']
video_path = None

for fname in video_files:
    potential_path = os.path.join(script_dir, fname)
    if os.path.exists(potential_path):
        video_path = potential_path
        break

if video_path:
    print(f"Video file found: {video_path}")
    print(f"File size: {os.path.getsize(video_path)} bytes")
else:
    print(f"ERROR: No video file found in {script_dir}")
    print(f"       Checked for: {video_files}")
    sys.exit(1)

try:
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("ERROR: cv2.VideoCapture could not open the file.")
    else:
        ret, frame = cap.read()
        if ret:
            print(f"Success: Video opened. Frame shape: {frame.shape}")
        else:
            print("ERROR: Video opened but could not read first frame.")
    cap.release()
except Exception as e:
    print(f"Exception opening video: {e}")

try:
    import ultralytics
    print(f"Ultralytics version: {ultralytics.__version__}")
    from ultralytics import YOLO
    model = YOLO('yolov8n.pt')
    print("Success: YOLO model loaded.")
except Exception as e:
    print(f"Exception loading YOLO: {e}")
