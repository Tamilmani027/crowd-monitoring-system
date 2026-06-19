import os
import sqlite3
import threading
from contextlib import contextmanager

from config import Config


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_DIR = os.path.join(BASE_DIR, 'database')
DATABASE_PATH = os.path.join(DATABASE_DIR, 'crowd_monitor.db')

_db_lock = threading.Lock()


def _ensure_database_dir() -> None:
    os.makedirs(DATABASE_DIR, exist_ok=True)


@contextmanager
def get_connection():
    _ensure_database_dir()
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def init_db() -> None:
    with _db_lock:
        with get_connection() as connection:
            cursor = connection.cursor()
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'admin',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                '''
            )
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    person_count INTEGER NOT NULL,
                    threshold INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    image_path TEXT NOT NULL,
                    source TEXT NOT NULL,
                    email_status TEXT NOT NULL DEFAULT 'not_sent',
                    webhook_status TEXT NOT NULL DEFAULT 'not_sent'
                )
                '''
            )
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS crowd_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    person_count INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    trend TEXT NOT NULL,
                    source TEXT NOT NULL
                )
                '''
            )
            cursor.execute(
                '''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                '''
            )

            # Enable WAL mode for better concurrent read/write performance
            cursor.execute('PRAGMA journal_mode=WAL')
            # Set busy timeout to 5 seconds so concurrent writers wait instead of failing
            cursor.execute('PRAGMA busy_timeout=5000')


def seed_setting(key: str, value: str) -> None:
    with _db_lock:
        with get_connection() as connection:
            connection.execute(
                'INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value',
                (key, value),
            )


def get_setting(key: str, default: str | None = None) -> str | None:
    with get_connection() as connection:
        row = connection.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    return row['value'] if row else default


def set_setting(key: str, value: str) -> None:
    seed_setting(key, value)


def get_all_settings() -> dict[str, str]:
    with get_connection() as connection:
        rows = connection.execute('SELECT key, value FROM settings').fetchall()
    return {row['key']: row['value'] for row in rows}


def create_user(username: str, password_hash: str, role: str = 'admin') -> None:
    with _db_lock:
        with get_connection() as connection:
            connection.execute(
                'INSERT OR IGNORE INTO users(username, password_hash, role) VALUES (?, ?, ?)',
                (username, password_hash, role),
            )


def update_user_password(username: str, password_hash: str) -> None:
    with _db_lock:
        with get_connection() as connection:
            connection.execute(
                'UPDATE users SET password_hash = ? WHERE username = ?',
                (password_hash, username),
            )


def get_user_by_username(username: str):
    with get_connection() as connection:
        return connection.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()


def list_users() -> list[sqlite3.Row]:
    with get_connection() as connection:
        rows = connection.execute('SELECT * FROM users ORDER BY username ASC').fetchall()
    return rows


def add_alert(*, created_at: str, person_count: int, threshold: int, status: str, image_path: str, source: str, email_status: str = 'not_sent', webhook_status: str = 'not_sent') -> int:
    with _db_lock:
        with get_connection() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO alerts(created_at, person_count, threshold, status, image_path, source, email_status, webhook_status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (created_at, person_count, threshold, status, image_path, source, email_status, webhook_status),
            )
            return int(cursor.lastrowid)


def list_alerts(limit: int = 50, offset: int = 0):
    with get_connection() as connection:
        rows = connection.execute(
            'SELECT * FROM alerts ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?',
            (limit, offset),
        ).fetchall()
    return rows


def get_alerts_count() -> int:
    with get_connection() as connection:
        row = connection.execute('SELECT COUNT(*) AS count FROM alerts').fetchone()
    return int(row['count']) if row else 0


def add_crowd_history(*, recorded_at: str, person_count: int, status: str, trend: str, source: str) -> int:
    with _db_lock:
        with get_connection() as connection:
            cursor = connection.execute(
                '''
                INSERT INTO crowd_history(recorded_at, person_count, status, trend, source)
                VALUES (?, ?, ?, ?, ?)
                ''',
                (recorded_at, person_count, status, trend, source),
            )
            return int(cursor.lastrowid)


def list_crowd_history(limit: int = 200, offset: int = 0):
    with get_connection() as connection:
        rows = connection.execute(
            'SELECT * FROM crowd_history ORDER BY recorded_at DESC, id DESC LIMIT ? OFFSET ?',
            (limit, offset),
        ).fetchall()
    return rows


def get_crowd_history_since(since_iso: str):
    with get_connection() as connection:
        rows = connection.execute(
            'SELECT * FROM crowd_history WHERE recorded_at >= ? ORDER BY recorded_at ASC, id ASC',
            (since_iso,),
        ).fetchall()
    return rows


def get_crowd_history_summary(limit: int = 100):
    with get_connection() as connection:
        rows = connection.execute(
            'SELECT * FROM crowd_history ORDER BY recorded_at DESC, id DESC LIMIT ?',
            (limit,),
        ).fetchall()
    return rows


init_db()
