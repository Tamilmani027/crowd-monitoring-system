import logging
import os

from dotenv import load_dotenv

load_dotenv()

_config_logger = logging.getLogger(__name__)


class Config:
    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "123456")

    _raw_secret = os.getenv("SECRET_KEY", "change-this-secret-key")
    if _raw_secret == "change-this-secret-key":
        SECRET_KEY = os.urandom(32).hex()
        _config_logger.warning(
            "SECRET_KEY is not set — using a random key. "
            "Sessions will NOT persist across server restarts. "
            "Set SECRET_KEY in your .env file for production."
        )
    else:
        SECRET_KEY = _raw_secret

    SESSION_LIFETIME_SECONDS = int(os.getenv("SESSION_LIFETIME_SECONDS", "3600"))

    CROWD_THRESHOLD = int(os.getenv("CROWD_THRESHOLD", "10"))
    ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "30"))
    _camera_source = os.getenv("CAMERA_SOURCE", "0")
    CAMERA_SOURCE = int(_camera_source) if _camera_source.isdigit() else _camera_source
    SMTP_HOST = os.getenv("SMTP_HOST", "")
    SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")
    ALERT_EMAIL_FROM = os.getenv("ALERT_EMAIL_FROM", "")
    WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
    USE_BYTETRACK = os.getenv("USE_BYTETRACK", "false").strip().lower() in {"1", "true", "yes", "on"}
    HEATMAP_WINDOW_SECONDS = int(os.getenv("HEATMAP_WINDOW_SECONDS", "10"))
    HISTORY_RECORD_INTERVAL_SECONDS = int(os.getenv("HISTORY_RECORD_INTERVAL_SECONDS", "5"))

    USE_CSRNET_FALLBACK = os.getenv("USE_CSRNET_FALLBACK", "false").strip().lower() in {"1", "true", "yes", "on"}
    CSRNET_THRESHOLD = int(os.getenv("CSRNET_THRESHOLD", "30"))
    CSRNET_MODEL_PATH = os.getenv("CSRNET_MODEL_PATH", "PartAmodel_best.pth.tar")
