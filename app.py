import atexit
import logging
import os
import time
from collections import defaultdict
from datetime import timedelta
from logging.handlers import RotatingFileHandler

from flask import Flask, Response, flash, jsonify, redirect, render_template, request, session, url_for

from config import Config
from database import db_manager
from services.analytics_service import get_dashboard_summary, get_history_series, list_alert_gallery, list_history
from services.auth_service import authenticate_user, ensure_default_admin_user
from services.camera_manager import camera_manager
from services.camera_source import normalize_camera_source

# winsound is Windows-only; make import conditional for cross-platform support
try:
    import winsound
except ImportError:
    winsound = None

app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(seconds=Config.SESSION_LIFETIME_SECONDS)

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

if not logger.handlers:
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, 'app.log'),
        maxBytes=2 * 1024 * 1024,
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [%(name)s] %(message)s'
    ))
    logger.addHandler(file_handler)


# ---------------------------------------------------------------------------
# Rate Limiter for login endpoint
# ---------------------------------------------------------------------------
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes
_login_attempts: dict[str, list[float]] = defaultdict(list)


def _is_rate_limited(ip: str) -> bool:
    """Return True if *ip* has exceeded the allowed login attempts."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SECONDS
    # Prune old entries
    _login_attempts[ip] = [t for t in _login_attempts[ip] if t > cutoff]
    return len(_login_attempts[ip]) >= RATE_LIMIT_MAX_ATTEMPTS


def _record_failed_attempt(ip: str) -> None:
    _login_attempts[ip].append(time.time())


def _clear_attempts(ip: str) -> None:
    _login_attempts.pop(ip, None)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_active_camera_source():
    raw_source = db_manager.get_setting('camera_source', str(Config.CAMERA_SOURCE))
    return normalize_camera_source(raw_source)


def get_camera():
    return camera_manager.get_camera(get_active_camera_source())


def release_camera():
    logger.info('Releasing all camera instances')
    camera_manager.release_all()


atexit.register(release_camera)
ensure_default_admin_user()
if db_manager.get_setting('camera_source') is None:
    db_manager.set_setting('camera_source', str(Config.CAMERA_SOURCE))

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        client_ip = request.remote_addr or '127.0.0.1'

        # Rate limiting check
        if _is_rate_limited(client_ip):
            logger.warning("Rate-limited login attempt from IP '%s'", client_ip)
            flash('Too many failed login attempts. Please try again later.', 'error')
            return jsonify({'error': 'Too many login attempts. Try again in 5 minutes.'}), 429

        username = request.form.get('username')
        password = request.form.get('password')

        if authenticate_user(username, password):
            session['user'] = username
            session.permanent = True
            _clear_attempts(client_ip)
            logger.info("Successful login for user '%s'", username)
            return redirect(url_for('dashboard'))
        else:
            _record_failed_attempt(client_ip)
            logger.warning("Failed login attempt for user '%s' from IP '%s'", username, client_ip)
            try:
                if winsound is not None:
                    winsound.Beep(1000, 200)
                    winsound.Beep(800, 200)
                    winsound.Beep(1000, 200)
            except Exception:
                logger.exception('Failed to play warning beep')

            flash('SYSTEM BREACH DETECTED: Invalid Credentials', 'error')
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html')


@app.route('/history')
def history():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('history.html')


@app.route('/gallery')
def gallery():
    if 'user' not in session:
        return redirect(url_for('login'))
    return render_template('gallery.html')

@app.route('/logout')
def logout():
    session.pop('user', None)
    logger.info('User logged out')
    return redirect(url_for('login'))

def gen(camera):
    while True:
        frame = camera.get_frame()
        if frame is None:
            continue
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed')
def video_feed():
    if 'user' not in session:
        return redirect(url_for('login'))
    # Optional ephemeral source override (does not persist unless saved via /api/settings)
    source_param = request.args.get('source')
    if source_param:
        try:
            source = normalize_camera_source(source_param)
            camera = camera_manager.get_camera(source)
        except Exception:
            logger.exception('Failed to get camera for source %s', source_param)
            return ('', 400)
    else:
        camera = get_camera()

    return Response(gen(camera),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/data')
def api_data():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    camera = get_camera()
    return jsonify({
        'count': camera.person_count,
        'status': camera.status,
        'threshold': camera.THRESHOLD,
        'trend': camera.trend,
        'last_alert': camera.last_alert_time,
        'alert_cooldown': camera.ALERT_COOLDOWN_SECONDS,
        'heatmap': camera.SHOW_HEATMAP,
        'camera_source': get_active_camera_source(),
    })


@app.route('/api/history')
def api_history():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    limit = request.args.get('limit', default=200, type=int)
    return jsonify(list_history(limit=limit))


@app.route('/api/analytics/summary')
def api_analytics_summary():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    return jsonify({
        'summary': get_dashboard_summary(),
        'series': get_history_series(),
    })


@app.route('/api/settings', methods=['GET', 'POST'])
def api_settings():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    payload = request.get_json(silent=True) or request.form.to_dict()
    needs_camera = request.method == 'GET' or any(
        key in payload and payload[key] != ''
        for key in ('threshold', 'cooldown', 'heatmap_window')
    )
    camera = get_camera() if needs_camera else None

    if request.method == 'POST':
        # --- Server-side input validation ---
        errors = []

        if 'threshold' in payload and payload['threshold'] != '':
            try:
                val = int(payload['threshold'])
                if not (1 <= val <= 500):
                    errors.append('Threshold must be between 1 and 500.')
                else:
                    camera.THRESHOLD = val
                    db_manager.set_setting('crowd_threshold', str(camera.THRESHOLD))
            except (ValueError, TypeError):
                errors.append('Threshold must be an integer.')

        if 'cooldown' in payload and payload['cooldown'] != '':
            try:
                val = int(payload['cooldown'])
                if not (5 <= val <= 3600):
                    errors.append('Cooldown must be between 5 and 3600 seconds.')
                else:
                    camera.ALERT_COOLDOWN_SECONDS = val
                    db_manager.set_setting('alert_cooldown', str(camera.ALERT_COOLDOWN_SECONDS))
            except (ValueError, TypeError):
                errors.append('Cooldown must be an integer.')

        if 'heatmap_window' in payload and payload['heatmap_window'] != '':
            try:
                val = int(payload['heatmap_window'])
                if not (2 <= val <= 120):
                    errors.append('Heatmap window must be between 2 and 120 seconds.')
                else:
                    camera.HEATMAP_WINDOW_SECONDS = val
                    db_manager.set_setting('heatmap_window_seconds', str(camera.HEATMAP_WINDOW_SECONDS))
            except (ValueError, TypeError):
                errors.append('Heatmap window must be an integer.')

        if 'camera_source' in payload and payload['camera_source'] != '':
            raw = payload['camera_source']
            new_source = normalize_camera_source(raw)
            # Validate: numeric 0-10 or valid stream URL
            if isinstance(new_source, int):
                if not (0 <= new_source <= 10):
                    errors.append('Camera index must be between 0 and 10.')
                else:
                    db_manager.set_setting('camera_source', str(new_source))
                    camera_manager.release_all()
            elif isinstance(new_source, str):
                lowered = new_source.strip().lower()
                if not lowered.startswith(('http://', 'https://', 'rtsp://')):
                    errors.append('Camera URL must start with http://, https://, or rtsp://.')
                else:
                    db_manager.set_setting('camera_source', str(new_source))
                    camera_manager.release_all()

        if 'use_csrnet' in payload:
            val = str(payload['use_csrnet']).lower() in ['true', '1', 'yes']
            db_manager.set_setting('use_csrnet', str(val))

        if 'csrnet_threshold' in payload and payload['csrnet_threshold'] != '':
            try:
                val = int(payload['csrnet_threshold'])
                if not (1 <= val <= 1000):
                    errors.append('CSRNet threshold must be between 1 and 1000.')
                else:
                    db_manager.set_setting('csrnet_threshold', str(val))
            except (ValueError, TypeError):
                errors.append('CSRNet threshold must be an integer.')

        if errors:
            return jsonify({'error': '; '.join(errors)}), 400

        return jsonify({
            'threshold': camera.THRESHOLD if camera is not None else int(db_manager.get_setting('crowd_threshold', str(Config.CROWD_THRESHOLD))),
            'cooldown': camera.ALERT_COOLDOWN_SECONDS if camera is not None else int(db_manager.get_setting('alert_cooldown', str(Config.ALERT_COOLDOWN))),
            'heatmap_window': camera.HEATMAP_WINDOW_SECONDS if camera is not None else int(db_manager.get_setting('heatmap_window_seconds', str(Config.HEATMAP_WINDOW_SECONDS))),
            'camera_source': get_active_camera_source(),
            'use_csrnet': str(db_manager.get_setting('use_csrnet', str(Config.USE_CSRNET_FALLBACK))).lower() in ['true', '1', 'yes'],
            'csrnet_threshold': int(db_manager.get_setting('csrnet_threshold', str(Config.CSRNET_THRESHOLD))),
        })

    return jsonify({
        'threshold': camera.THRESHOLD if camera is not None else int(db_manager.get_setting('crowd_threshold', str(Config.CROWD_THRESHOLD))),
        'cooldown': camera.ALERT_COOLDOWN_SECONDS if camera is not None else int(db_manager.get_setting('alert_cooldown', str(Config.ALERT_COOLDOWN))),
        'heatmap_window': camera.HEATMAP_WINDOW_SECONDS if camera is not None else int(db_manager.get_setting('heatmap_window_seconds', str(Config.HEATMAP_WINDOW_SECONDS))),
        'camera_source': get_active_camera_source(),
        'use_csrnet': str(db_manager.get_setting('use_csrnet', str(Config.USE_CSRNET_FALLBACK))).lower() in ['true', '1', 'yes'],
        'csrnet_threshold': int(db_manager.get_setting('csrnet_threshold', str(Config.CSRNET_THRESHOLD))),
    })

@app.route('/toggle_heatmap')
def toggle_heatmap():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401
    
    camera = get_camera()
    camera.SHOW_HEATMAP = not camera.SHOW_HEATMAP
    return jsonify({'heatmap': camera.SHOW_HEATMAP})


@app.route('/release_camera', methods=['POST', 'GET'])
def release_camera_route():
    if 'user' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    source_param = request.args.get('source')
    try:
        if source_param:
            # release specific camera instance if provided
            camera_manager.release_camera(source=normalize_camera_source(source_param))
        else:
            # release all camera instances
            camera_manager.release_all()
    except Exception:
        logger.exception('Failed to release camera(s)')
        return jsonify({'released': False}), 500

    return jsonify({'released': True})

if __name__ == '__main__':
    # When run directly, use dev mode for backward compatibility.
    import webbrowser
    from threading import Timer

    def open_browser():
        if not os.environ.get("WERKZEUG_RUN_MAIN"):
            webbrowser.open_new('http://127.0.0.1:8090/')

    Timer(1, open_browser).start()
    logger.info('Starting Flask dev server on http://0.0.0.0:8090')
    app.run(host='0.0.0.0', port=8090, debug=True, use_reloader=False)
