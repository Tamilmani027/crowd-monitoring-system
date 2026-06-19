import cv2
from ultralytics import YOLO
import datetime
import os
import sys
import winsound

# ==========================================
# CONFIGURATION
# ==========================================
# Get the absolute path of the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Target video filename
# We will try to find this specific file first.
VIDEO_FILENAME = 'input_video (2).mp4' 

# Construct the full path
VIDEO_PATH = os.path.join(BASE_DIR, VIDEO_FILENAME)

# Crowd threshold to trigger alert
THRESHOLD = 15

# Folder to save alert images
ALERT_FOLDER = os.path.join(BASE_DIR, 'alerts')

# Toggle display (set to False if running on a server without display)
SHOW_DISPLAY = True

# ==========================================
# INITIALIZATION
# ==========================================

# Create alert folder if it doesn't exist
if not os.path.exists(ALERT_FOLDER):
    os.makedirs(ALERT_FOLDER)

# ROBUST VIDEO LOADING
if not os.path.exists(VIDEO_PATH):
    print(f"Warning: Configured video '{VIDEO_FILENAME}' not found in {BASE_DIR}")
    print("Searching for other video files in the directory...")
    
    # Find any .mp4 file in the directory
    import glob
    video_files = glob.glob(os.path.join(BASE_DIR, "*.mp4"))
    
    if video_files:
        VIDEO_PATH = video_files[0]
        print(f"resolution: Found alternative video file: {os.path.basename(VIDEO_PATH)}")
        print("Using this video instead.")
    else:
        print("Error: No video files (.mp4) found in the script directory.")
        print(f"Please place 'input_video (2).mp4' or any other .mp4 file in: {BASE_DIR}")
        input("Press Enter to exit...")
        sys.exit(1)

# Initialize YOLOv8 model (using nano version for speed)
# It will automatically download 'yolov8n.pt' on the first run.
print("Initializing YOLOv8 model...")
model = YOLO('yolov8n.pt')

# Open video file
cap = cv2.VideoCapture(VIDEO_PATH)

if not cap.isOpened():
    print(f"Error: Could not open video source at '{VIDEO_PATH}'.")
    # Try one more fallback: 0 for webcam? No, user wants video.
    print("Codecs might be missing or file is corrupt.")
    input("Press Enter to exit...")
    sys.exit(1)

print(f"Processing video: {VIDEO_PATH}")
print(f"Crowd Threshold: {THRESHOLD}")
print("Press 'q' to quit.")

# ==========================================
# MAIN LOOP
# ==========================================
frame_count = 0
alert_cooldown = 0 # Simple cooldown to avoid saving too many images per second

while True:
    ret, frame = cap.read()
    if not ret:
        print("End of video stream.")
        break

    frame_count += 1
    
    # Run YOLOv8 inference on the frame
    # classes=0 filters for 'person' class only
    results = model(frame, classes=[0], verbose=False)
    
    # Analyze results
    result = results[0]
    boxes = result.boxes
    person_count = len(boxes)
    
    # Determine Status
    if person_count > THRESHOLD:
        status = "OVER CROWDED"
        color = (0, 0, 255) # Red
        
        # Taking action: Console Alert
        print(f"[ALERT] Overcrowding detected! Count: {person_count} > {THRESHOLD}")
        
        # Taking action: Save Alert Image (with cooldown of approx 30 frames/1 sec)
        if alert_cooldown == 0:
            # Play beep sound (frequency=1000Hz, duration=500ms)
            try:
                winsound.Beep(1000, 500)
            except Exception as e:
                print(f"        [Warning] Could not play sound: {e}")

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{ALERT_FOLDER}/alert_{timestamp}_{person_count}_people.jpg"
            cv2.imwrite(filename, frame)
            print(f"        Saved alert image: {filename}")
            alert_cooldown = 30 
    else:
        status = "NORMAL"
        color = (0, 255, 0) # Green
    
    if alert_cooldown > 0:
        alert_cooldown -= 1

    # Annotate Frame
    # Draw detections
    for box in boxes:
        # Bounding Box
        x1, y1, x2, y2 = map(int, box.xyxy[0])
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Optional: Label (can clutter if too many people)
        # cv2.putText(frame, 'Person', (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    # Draw Status Overlay
    # Add a semi-transparent background for text legibility
    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (400, 100), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

    # Text Info
    cv2.putText(frame, f"Status: {status}", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
    cv2.putText(frame, f"Count: {person_count} (Threshold: {THRESHOLD})", (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    
    # Display Frame
    if SHOW_DISPLAY:
        cv2.imshow("Crowd Monitoring System", frame)
    
        # Exit on 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

# Cleanup
cap.release()
if SHOW_DISPLAY:
    print("Video ended. Press any key in the window to exit.")
    cv2.waitKey(0) # Wait for a key press to close the window
    cv2.destroyAllWindows()
print("Execution finished.")
