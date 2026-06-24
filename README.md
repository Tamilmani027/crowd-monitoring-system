# 🚦 AI-Based Crowd Monitoring System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white"/>
  <img src="https://img.shields.io/badge/YOLOv8-Ultralytics-00FFFF?style=for-the-badge"/>
  <img src="https://img.shields.io/badge/PyTorch-CSRNet-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white"/>
  <img src="https://img.shields.io/badge/OpenCV-Computer_Vision-5C3EE8?style=for-the-badge&logo=opencv&logoColor=white"/>
</p>

<p align="center">
  A real-time AI-powered crowd monitoring system that detects people, estimates crowd density, visualizes heatmaps, and triggers automated overcrowding alerts — all through a web-based dashboard.
</p>

---

## 📌 Overview

This project combines **YOLOv8** (for precise individual detection in low-to-medium density crowds) with **CSRNet** (a deep learning density estimator that activates in high-density scenarios) to deliver accurate crowd count data in any condition.

The system feeds live video from a webcam or IP camera into a **Flask web dashboard** where administrators can monitor counts in real time, review historical trends, inspect alert snapshots, and dynamically tune system parameters — all without restarting the service.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎯 **Dual-Model Detection** | YOLOv8 for individual tracking; CSRNet fallback for dense crowds |
| 🌡️ **Live Heatmaps** | Dynamic density maps showing high-traffic zones over configurable time windows |
| 🚨 **Overcrowding Alerts** | Visual warnings + automatic snapshot capture when thresholds are exceeded |
| 📊 **Analytics & History** | SQLite-backed time-series logging with summary metrics |
| 🖼️ **Alert Gallery** | Browse all captured alert snapshots from the dashboard |
| ⚙️ **Dynamic Configuration** | Change thresholds, cooldowns, camera source, and heatmap windows on-the-fly |
| 🔐 **Secure Auth** | Login-protected dashboard with configurable admin credentials via `.env` |
| 🏭 **Production-Ready** | Waitress WSGI server for robust, multi-threaded serving |

---

## 🛠️ Tech Stack

- **Backend**: Python 3.8+, Flask, Waitress
- **Computer Vision**: OpenCV, Ultralytics YOLOv8, PyTorch (CSRNet)
- **Data & Storage**: NumPy, SQLite
- **Configuration**: python-dotenv

---

## 📁 Project Structure

```
crowd-monitoring-system/
│
├── app.py                        # Flask routes and application factory
├── run.py                        # Entry point (production & dev modes)
├── camera.py                     # Core video processing, YOLO & heatmap logic
├── config.py                     # App configuration and constants
├── debug.py                      # Debug utilities
├── detect_video.py               # Standalone video detection script
├── download_csrnet_weights.py    # One-time script to fetch CSRNet weights
├── PartAmodel_best.pth.tar       # Pre-trained CSRNet model weights
├── requirements.txt
├── .env.example
│
├── services/
│   ├── csrnet.py                 # CSRNet dense crowd estimation service
│   ├── analytics.py              # Crowd count analytics and metrics
│   └── auth.py                  # Authentication service
│
├── database/
│   └── db.py                    # SQLite interactions and settings storage
│
└── templates/                   # HTML templates for the Flask dashboard
```

---

## ⚙️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Tamilmani027/crowd-monitoring-system.git
cd crowd-monitoring-system
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Open `.env` and set your admin credentials and secret key:

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password
SECRET_KEY=your_secret_key
```

### 5. Download CSRNet Weights (for Dense Crowd Support)

```bash
python download_csrnet_weights.py
```

> **Note:** The `PartAmodel_best.pth.tar` file is already included in the repo. This step is only needed if you've removed it or want a fresh download.

---

## 🚀 Running the Application

**Production mode** (Waitress WSGI — recommended):

```bash
python run.py
```

**Development mode** (Flask built-in server with hot-reload):

```bash
python run.py --dev
```

The app starts at **`http://127.0.0.1:8090/`** and will open your default browser automatically.

**Default login credentials** (change in `.env`):

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `123456` |

---

## 📱 Camera Source Configuration

Configure your camera source directly from the **Dashboard → Settings**.

### Local Webcam

Enter the camera index in the `Camera Source` field:
- `0` → Default built-in webcam
- `1` → External USB camera

### Mobile / IP Camera

1. Install an IP camera app on your phone — e.g., **IP Webcam** (Android) or **DroidCam**.
2. Connect both your phone and PC to the **same Wi-Fi network**.
3. Start the stream on your phone and copy the video URL (e.g., `http://192.168.1.50:8080/video`).
4. Paste the URL into the `Camera Source` field in the dashboard settings.

---

## 🔄 How It Works

```
Live Video Feed
      │
      ▼
 Frame Captured (camera.py)
      │
      ├──[Low/Medium Density]──► YOLOv8 Detection ──► Count persons via bounding boxes
      │
      └──[High Density]──────► CSRNet Estimation ──► Density map → count estimate
                                       │
                                       ▼
                              Heatmap Overlay Generation
                                       │
                                       ▼
                           Threshold Check → Alert if exceeded
                                       │
                                       ▼
                           SQLite DB log + Snapshot saved
                                       │
                                       ▼
                           Flask Dashboard (real-time stream)
```

---

## 📊 Dashboard Pages

| Page | What it shows |
|---|---|
| **Live Monitor** | Real-time video stream with count overlay and heatmap |
| **History** | Time-series crowd count graph and summary statistics |
| **Alert Gallery** | All captured alert snapshots with timestamps |
| **Settings** | Camera source, thresholds, cooldown, heatmap window controls |

---

## 📦 Dependencies

```
ultralytics       # YOLOv8 person detection
opencv-python     # Video capture & image processing
numpy             # Array operations & heatmap computation
flask             # Web framework & dashboard
python-dotenv     # Environment variable management
waitress          # Production WSGI server
torch             # PyTorch — CSRNet backbone
torchvision       # Pretrained model utilities
```

---

## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request for bug fixes, new features, or documentation improvements.

---

## 👤 Author

**Tamilmani C**  
MCA Final Year | SJB Institute of Technology, Bengaluru  
[GitHub](https://github.com/Tamilmani027)

---

## 📄 License

This project is open-source and available under the [MIT License](LICENSE).
