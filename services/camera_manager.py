import threading

from config import Config
from camera import VideoCamera


class CameraManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._cameras = {}

    def get_camera(self, source=None):
        camera_source = Config.CAMERA_SOURCE if source is None else source
        key = str(camera_source)
        with self._lock:
            if key not in self._cameras:
                self._cameras[key] = VideoCamera(source=camera_source)
            return self._cameras[key]

    def release_camera(self, source=None):
        camera_source = Config.CAMERA_SOURCE if source is None else source
        key = str(camera_source)
        with self._lock:
            camera = self._cameras.pop(key, None)
        if camera is not None:
            camera.release()

    def release_all(self):
        with self._lock:
            cameras = list(self._cameras.values())
            self._cameras.clear()
        for camera in cameras:
            camera.release()


camera_manager = CameraManager()
