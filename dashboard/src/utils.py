from __future__ import annotations

from datetime import datetime, timezone


def parse_dt(value: str | None) -> datetime | None:
    if value is None or value == "":
        return None
    # ISO8601 expected
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def ago(dt: datetime | None, now: datetime | None = None) -> str:
    if dt is None:
        return "N/A"
    if now is None:
        now = datetime.now(timezone.utc)

    delta = now - dt
    seconds = int(delta.total_seconds())

    if seconds < 0:
        return "just now"

    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if seconds < 60:
        return "just now"
    if minutes < 60:
        return f"{minutes} min ago" if minutes == 1 else f"{minutes} mins ago"
    if hours < 24:
        return f"{hours} hr ago" if hours == 1 else f"{hours} hrs ago"
    return f"{days} day ago" if days == 1 else f"{days} days ago"
