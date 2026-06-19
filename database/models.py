from dataclasses import dataclass


@dataclass(frozen=True)
class UserRecord:
    id: int | None
    username: str
    password_hash: str
    role: str


@dataclass(frozen=True)
class AlertRecord:
    id: int | None
    created_at: str
    person_count: int
    threshold: int
    status: str
    image_path: str
    source: str


@dataclass(frozen=True)
class CrowdHistoryRecord:
    id: int | None
    recorded_at: str
    person_count: int
    status: str
    trend: str
    source: str
