# AI-Based Crowd Monitoring System Using YOLO 🚦

## 📌 Overview
This project implements an AI-based crowd monitoring system using Python and YOLOv8.
It detects people in video footage, counts the number of individuals, and triggers alerts
when crowd density exceeds a predefined threshold. The system is designed to support
crowd safety monitoring in public places using CCTV or recorded video feeds.

---

## ✨ Features
- **Person Detection**: Accurate people detection using YOLOv8
- **Crowd Counting**: Counts the total number of detected persons in each frame
- **Overcrowding Alerts**:
  - Visual warning displayed as **"OVER CROWDED"** (Red)
  - Console alert messages
  - Automatic image capture saved in the `alerts` folder
- **Visualization**:
  - Bounding boxes around detected people
  - Live count and status displayed on video feed

---

## 🛠️ Tech Stack
- Python
- OpenCV
- YOLOv8
- NumPy
- Ultralytics

---

## 📋 Prerequisites
- Python 3.8 or above
- Internet connection (for first-time YOLO model download)

---

## ⚙️ Installation
1. Clone or download the source code
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt

## 📱 Mobile Camera Setup
You can use a phone as the live camera source by running a stream app on the phone and pasting its URL into the dashboard.

Recommended phone apps:
- IP Webcam
- DroidCam
- Any RTSP or MJPEG camera app

Example URL formats:
- `http://192.168.1.50:8080/video`
- `rtsp://192.168.1.50:8554/video`

Steps:
1. Connect the phone and PC to the same Wi-Fi network.
2. Start the stream app on the phone.
3. Copy the stream URL shown by the app.
4. Open the dashboard and paste the URL into the `Camera Source` field.
5. Click `Set Mobile Camera`.
6. Click `Open Live Feed`.

If the stream is reachable, the dashboard will use the phone camera as the live feed source.
