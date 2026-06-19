import cv2
import datetime
import logging
import os
import threading
import time
from collections import deque

import numpy as np

from config import Config
from database import db_manager
from services.camera_source import is_stream_source
from services.detector import CrowdDetector
from services.notification_service import send_email_alert, send_webhook_alert


logger = logging.getLogger(__name__)


class VideoCamera:
    def __init__(self, source=None):
        self.BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        self.VIDEO_PATH = os.path.join(self.BASE_DIR, 'input_video (2).mp4')
        self.ALERT_FOLDER = os.path.join(self.BASE_DIR, 'alerts')
        self.source = Config.CAMERA_SOURCE if source is None else source

        self.THRESHOLD = int(db_manager.get_setting('crowd_threshold', str(Config.CROWD_THRESHOLD)) or Config.CROWD_THRESHOLD)
        self.ALERT_COOLDOWN_SECONDS = int(db_manager.get_setting('alert_cooldown', str(Config.ALERT_COOLDOWN)) or Config.ALERT_COOLDOWN)
        self.SHOW_HEATMAP = True
        self.HEATMAP_WINDOW_SECONDS = Config.HEATMAP_WINDOW_SECONDS
        self.HISTORY_RECORD_INTERVAL_SECONDS = Config.HISTORY_RECORD_INTERVAL_SECONDS
        self.USE_BYTETRACK = Config.USE_BYTETRACK
        self.frame_lock = threading.Lock()
        self.heatmap_points = deque()

        os.makedirs(self.ALERT_FOLDER, exist_ok=True)

        logger.info('Initializing YOLOv8 model')
        self.detector = CrowdDetector(use_bytetrack=self.USE_BYTETRACK)

        # Do not open the capture here; open lazily when a frame is requested.
        self.cap = None

        self.last_alert_epoch = 0.0
        self.last_history_epoch = 0.0
        self.person_count = 0
        self.last_count = 0
        self.trend = 'stable'
        self.last_alert_time = 'None'
        self.status = 'normal'

    def _open_capture(self, source):
        # Determine if source is a local camera index (int or digit string)
        is_local_camera = False
        camera_idx = None
        if isinstance(source, int):
            is_local_camera = True
            camera_idx = source
        elif isinstance(source, str) and source.strip().isdigit():
            is_local_camera = True
            camera_idx = int(source.strip())

        if is_local_camera:
            import platform
            if platform.system() == 'Windows':
                logger.info('Trying to open Windows camera index %s with CAP_DSHOW', camera_idx)
                cap = cv2.VideoCapture(camera_idx, cv2.CAP_DSHOW)
                if cap.isOpened():
                    return cap
                logger.warning('Failed to open camera index %s with CAP_DSHOW, trying default backend', camera_idx)
            
            cap = cv2.VideoCapture(camera_idx)
            if cap.isOpened():
                return cap
        else:
            cap = cv2.VideoCapture(source)
            if cap.isOpened():
                return cap

        if is_stream_source(source):
            logger.warning('Mobile or network camera stream could not be opened: %s', source)
            return None

        logger.warning('Configured camera source unavailable, trying file fallback')
        if os.path.exists(self.VIDEO_PATH):
            cap = cv2.VideoCapture(self.VIDEO_PATH)
            if cap.isOpened():
                return cap

        import glob

        video_files = glob.glob(os.path.join(self.BASE_DIR, '*.mp4'))
        if video_files:
            cap = cv2.VideoCapture(video_files[0])
            if cap.isOpened():
                return cap

        logger.warning('No video source found. Using placeholder frames')
        return None

    def __del__(self):
        self.release()

    def release(self):
        with self.frame_lock:
            if self.cap is not None:
                try:
                    if self.cap.isOpened():
                        self.cap.release()
                except Exception:
                    # Some capture objects may not implement isOpened() gracefully
                    try:
                        self.cap.release()
                    except Exception:
                        logger.exception('Failed while releasing capture')
                finally:
                    self.cap = None

    def _blank_frame(self, message):
        blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank_frame, message, (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        ret, jpeg = cv2.imencode('.jpg', blank_frame)
        return jpeg.tobytes()

    def _record_history(self, person_count, status, trend):
        now = time.time()
        if now - self.last_history_epoch < self.HISTORY_RECORD_INTERVAL_SECONDS:
            return

        try:
            db_manager.add_crowd_history(
                recorded_at=datetime.datetime.now().isoformat(timespec='seconds'),
                person_count=person_count,
                status=status,
                trend=trend,
                source=str(self.source),
            )
            self.last_history_epoch = now
        except Exception:
            logger.exception('Failed to record crowd history')

    def _send_notifications(self, person_count, image_path):
        subject = f'Crowd alert: {person_count} people detected'
        body = f'Crowding detected at {datetime.datetime.now().isoformat(timespec="seconds")} with count {person_count}.'
        email_status = send_email_alert(subject, body)
        webhook_status = send_webhook_alert(
            {
                'event': 'crowd_alert',
                'count': person_count,
                'threshold': self.THRESHOLD,
                'image_path': image_path,
                'source': str(self.source),
                'timestamp': datetime.datetime.now().isoformat(timespec='seconds'),
            }
        )
        return email_status, webhook_status

    def get_frame(self):
        with self.frame_lock:
            # Ensure the capture is opened lazily when a frame is requested.
            if self.cap is None:
                self.cap = self._open_capture(self.source)

            if self.cap is None or not self.cap.isOpened():
                return self._blank_frame('NO CAMERA SOURCE')

            success, frame = self.cap.read()
            if not success:
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                success, frame = self.cap.read()
                if not success:
                    self.status = 'camera_err'
                    return self._blank_frame('CAMERA SOURCE ERROR')

            # Read dynamic CSRNet settings
            use_csrnet = str(db_manager.get_setting('use_csrnet', str(Config.USE_CSRNET_FALLBACK))).lower() in ['true', '1', 'yes']
            csrnet_threshold = int(db_manager.get_setting('csrnet_threshold', str(Config.CSRNET_THRESHOLD)))

            detection = self.detector.detect_people(
                frame, 
                use_csrnet=use_csrnet, 
                csrnet_threshold=csrnet_threshold
            )
            boxes = detection.boxes
            person_count = detection.person_count

            if person_count > self.last_count:
                self.trend = 'up'
            elif person_count < self.last_count:
                self.trend = 'down'
            else:
                self.trend = 'stable'

            self.last_count = person_count
            self.person_count = person_count

            now = time.time()
            if person_count > self.THRESHOLD:
                display_status = 'OVER CROWDED'
                self.status = 'alert'
                color = (0, 0, 255)

                if now - self.last_alert_epoch > self.ALERT_COOLDOWN_SECONDS:
                    logger.warning('[ALERT] Count: %s', person_count)
                    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
                    self.last_alert_time = datetime.datetime.now().strftime('%I:%M:%S %p')

                    filename = os.path.join(self.ALERT_FOLDER, f'alert_{timestamp}_{person_count}_people.jpg')
                    cv2.imwrite(filename, frame)
                    email_status, webhook_status = self._send_notifications(person_count, filename)
                    db_manager.add_alert(
                        created_at=datetime.datetime.now().isoformat(timespec='seconds'),
                        person_count=person_count,
                        threshold=self.THRESHOLD,
                        status='alert',
                        image_path=filename,
                        source=str(self.source),
                        email_status=email_status,
                        webhook_status=webhook_status,
                    )
                    self.last_alert_epoch = now
            else:
                display_status = 'NORMAL'
                self.status = 'normal'
                color = (0, 255, 0)

            self._record_history(person_count, self.status, self.trend)

            if detection.is_csrnet and detection.density_map is not None:
                # If CSRNet fallback was used, overlay the density map
                density_map = detection.density_map
                # Normalize density map for visualization
                if np.max(density_map) > 0:
                    density_map = (density_map / np.max(density_map)) * 255.0
                density_map = density_map.astype(np.uint8)
                
                # Resize density map to match frame size if needed (usually 1/8 size of input)
                density_map_resized = cv2.resize(density_map, (frame.shape[1], frame.shape[0]))
                heatmap_color = cv2.applyColorMap(density_map_resized, cv2.COLORMAP_JET)
                
                # Create mask
                _, mask_thresh = cv2.threshold(density_map_resized, 10, 255, cv2.THRESH_BINARY)
                alpha = mask_thresh.astype(float) / 255.0 * 0.6
                alpha = cv2.merge([alpha, alpha, alpha])
                frame = (frame * (1.0 - alpha) + heatmap_color * alpha).astype(np.uint8)
                
            elif self.SHOW_HEATMAP:
                current_time = time.time()
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
                    self.heatmap_points.append((current_time, cx, cy))

                while self.heatmap_points and current_time - self.heatmap_points[0][0] > self.HEATMAP_WINDOW_SECONDS:
                    self.heatmap_points.popleft()

                if self.heatmap_points:
                    heatmap_matrix = np.zeros((frame.shape[0], frame.shape[1]), dtype=np.uint8)
                    for _, cx, cy in self.heatmap_points:
                        cv2.circle(heatmap_matrix, (cx, cy), radius=60, color=255, thickness=-1)

                    heatmap_blurred = cv2.GaussianBlur(heatmap_matrix, (121, 121), 0)
                    heatmap_color = cv2.applyColorMap(heatmap_blurred, cv2.COLORMAP_JET)
                    _, mask_thresh = cv2.threshold(heatmap_blurred, 10, 255, cv2.THRESH_BINARY)
                    alpha = mask_thresh.astype(float) / 255.0 * 0.5
                    alpha = cv2.merge([alpha, alpha, alpha])
                    frame = (frame * (1.0 - alpha) + heatmap_color * alpha).astype(np.uint8)

            # Only draw boxes if we didn't use CSRNet, or draw them anyway (we have some boxes)
            if not detection.is_csrnet:
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (600, 110), (0, 0, 0), -1)
            cv2.addWeighted(overlay, 0.6, frame, 0.4, 0, frame)

            cv2.putText(frame, f'Status: {display_status}', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
            if detection.is_csrnet:
                cv2.putText(frame, f'Count (Est): {person_count} (Thr: {self.THRESHOLD}) [CSRNet]', (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
            else:
                cv2.putText(frame, f'Count: {person_count} (Threshold: {self.THRESHOLD})', (20, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            ret, jpeg = cv2.imencode('.jpg', frame)
            return jpeg.tobytes()
