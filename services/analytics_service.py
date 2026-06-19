from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from database import db_manager


def get_dashboard_summary() -> dict:
    alerts = db_manager.list_alerts(limit=10)
    history = db_manager.list_crowd_history(limit=50)

    latest = history[0] if history else None
    peak_count = max((row['person_count'] for row in history), default=0)
    alert_count = db_manager.get_alerts_count()

    return {
        'latest_count': latest['person_count'] if latest else 0,
        'latest_status': latest['status'] if latest else 'normal',
        'latest_trend': latest['trend'] if latest else 'stable',
        'peak_count': peak_count,
        'alert_count': alert_count,
        'recent_alerts': [dict(row) for row in alerts],
    }


def get_history_series(hours: int = 24) -> dict:
    since = datetime.now() - timedelta(hours=hours)
    rows = db_manager.get_crowd_history_since(since.isoformat(timespec='seconds'))

    labels = []
    counts = []
    statuses = []

    for row in rows:
        labels.append(row['recorded_at'])
        counts.append(row['person_count'])
        statuses.append(row['status'])

    return {
        'labels': labels,
        'counts': counts,
        'statuses': statuses,
    }


def list_alert_gallery(limit: int = 100) -> list[dict]:
    rows = db_manager.list_alerts(limit=limit)
    return [dict(row) for row in rows]


def list_history(limit: int = 200) -> list[dict]:
    rows = db_manager.list_crowd_history(limit=limit)
    return [dict(row) for row in rows]
