# AI-Based Crowd Monitoring System 🚦

## 📌 Overview
This project implements a robust, AI-based crowd monitoring system using Python, YOLOv8, and CSRNet. It is designed to detect people in video footage, accurately estimate crowd density, and trigger real-time alerts when overcrowding thresholds are exceeded. 

The system features a complete web-based dashboard powered by Flask, offering real-time monitoring, historical analytics, alert galleries, and dynamic configuration of camera sources and thresholds.

---

## ✨ Key Features
- **Accurate Person Detection**: Uses YOLOv8 for precise individual tracking in low-to-medium density crowds.
- **Dense Crowd Estimation**: Integrates CSRNet as a fallback for high-density situations where individual detection is challenging.
- **Web-Based Dashboard**: A full Flask web interface for live monitoring with secure authentication.
- **Interactive Heatmaps**: Generates dynamic heatmaps to visualize high-traffic areas and crowd density zones over time.
- **Overcrowding Alerts**:
  - Visual warnings on the live feed
  - Automatic snapshot capture stored in the database and accessible via the **Gallery**.
  - Configurable alert cooldowns to prevent spam.
- **Analytics & History**: Logs crowd counts to a SQLite database, providing time-series data and summary metrics via the **History** tab.
- **Dynamic Configuration**: Change detection thresholds, alert cooldowns, heatmap windows, and camera sources on-the-fly directly from the dashboard.
- **Production-Ready**: Includes a `run.py` entry point that uses Waitress for robust production serving, alongside a standard development mode.

---

## 🛠️ Tech Stack
- **Backend Framework**: Python, Flask, Waitress
- **Computer Vision**: OpenCV, Ultralytics (YOLOv8), PyTorch (CSRNet)
- **Data & Storage**: NumPy, SQLite
- **Environment**: python-dotenv

---

## 📋 Prerequisites
- Python 3.8 or above
- Internet connection (for the initial download of YOLOv8 and CSRNet weights)

---

## ⚙️ Installation

1. **Clone or download the source code.**

2. **Set up a virtual environment (Optional but recommended):**
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Linux/macOS:
   source .venv/bin/activate
   ```

3. **Install required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration:**
   Copy `.env.example` to `.env` and configure your settings (e.g., admin credentials, secrets).
   ```bash
   cp .env.example .env
   ```

5. **Download CSRNet Weights (Optional for Dense Crowds):**
   ```bash
   python download_csrnet_weights.py
   ```

---

## 🚀 Usage

Start the system using the provided entry script.

**For Production (Waitress):**
```bash
python run.py
```

**For Development (Flask built-in server with hot-reloading):**
```bash
python run.py --dev
```

Once started, the application will automatically open your default browser to `http://127.0.0.1:8090/`. 
*Default login credentials (unless changed in `.env`):*
- **Username**: admin
- **Password**: 123456

---

## 📱 Camera Source Setup

You can configure the camera source directly from the Dashboard settings. The system supports local webcams and IP streams (like from a mobile phone).

**Using a Mobile Camera:**
1. Install an IP camera app on your phone (e.g., IP Webcam, DroidCam).
2. Connect your phone and PC to the same Wi-Fi network.
3. Start the stream on your phone and copy the provided URL (e.g., `http://192.168.1.50:8080/video`).
4. In the Crowd Monitor dashboard, enter the URL in the `Camera Source` settings.

**Using a Local Webcam:**
Simply enter the camera index (e.g., `0` for the default webcam, `1` for an external USB camera) in the `Camera Source` settings.

---

## 📁 Project Structure Highlights
- `app.py` & `run.py`: Web server and application entry points.
- `camera.py`: Core video processing, YOLOv8 integration, and heatmap generation logic.
- `services/`: Contains modular services including `csrnet.py` for dense crowds, analytics, and authentication.
- `database/`: Manages SQLite database interactions and settings storage.
- `templates/` & `static/`: Frontend HTML, CSS, and JS for the dashboard.
