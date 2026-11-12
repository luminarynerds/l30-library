# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import UTC, datetime, timedelta

logger = get_logger(__name__)

# Standard timezone for all system operations.
UTC = UTC


def utc_now() -> datetime:
    return datetime.now(UTC)


def ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None

    if dt.tzinfo is None:
        # Naive datetime - assume it's already UTC and add timezone info
        logger.warning("Converting naive datetime to UTC: %s", dt)
        return dt.replace(tzinfo=UTC)
    elif dt.tzinfo != UTC:
        # Convert to UTC
        return dt.astimezone(UTC)
    else:
        # Already UTC
        return dt


def datetime_to_iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None

    # Ensure UTC timezone
    utc_dt = ensure_utc(dt)
    return utc_dt.isoformat()


def iso_to_datetime(iso_string: str | None) -> datetime | None:
    if not iso_string:
        return None

    try:
        # Parse ISO string
        if iso_string.endswith("Z"):
            # Replace Z with explicit UTC timezone
            iso_string = iso_string[:-1] + "+00:00"

        dt = datetime.fromisoformat(iso_string)
        return ensure_utc(dt)
    except (ValueError, TypeError) as e:
        logger.error("Failed to parse ISO datetime string %s: %s", iso_string, e)
        return None


def utc_timestamp() -> int:
    return int(utc_now().timestamp())


def utc_from_timestamp(timestamp: int | float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=UTC)


def time_ago_utc(
    hours: int = 0, days: int = 0, minutes: int = 0, seconds: int = 0
) -> datetime:
    delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return utc_now() - delta


def time_from_now_utc(
    hours: int = 0, days: int = 0, minutes: int = 0, seconds: int = 0
) -> datetime:
    delta = timedelta(days=days, hours=hours, minutes=minutes, seconds=seconds)
    return utc_now() + delta


def is_timezone_aware(dt: datetime) -> bool:
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def datetime_age_hours(dt: datetime | None) -> float:
    if dt is None:
        return float("inf")

    utc_dt = ensure_utc(dt)
    age_delta = utc_now() - utc_dt
    return age_delta.total_seconds() / 3600


def datetime_age_days(dt: datetime | None) -> float:
    return datetime_age_hours(dt) / 24


def is_recent(dt: datetime | None, hours: int = 24) -> bool:
    if dt is None:
        return False

    age_hours = datetime_age_hours(dt)
    return 0 <= age_hours <= hours


def is_stale(dt: datetime | None, hours: int = 24) -> bool:
    if dt is None:
        return True

    age_hours = datetime_age_hours(dt)
    return age_hours > hours


def format_time_ago(dt: datetime | None) -> str:
    if dt is None:
        return "Never"

    age_hours = datetime_age_hours(dt)

    if age_hours < 0:
        return "In the future"
    elif age_hours < 1:
        minutes = int(age_hours * 60)
        return f"{minutes} minutes ago" if minutes != 1 else "1 minute ago"
    elif age_hours < 24:
        hours = int(age_hours)
        return f"{hours} hours ago" if hours != 1 else "1 hour ago"
    else:
        days = int(age_hours / 24)
        return f"{days} days ago" if days != 1 else "1 day ago"


def validate_datetime_range(
    start_dt: datetime | None, end_dt: datetime | None
) -> tuple[datetime | None, datetime | None]:
    start_utc = ensure_utc(start_dt) if start_dt else None
    end_utc = ensure_utc(end_dt) if end_dt else None

    if start_utc and end_utc and end_utc < start_utc:
        raise ValueError(
            f"End datetime {end_utc} cannot be before start datetime {start_utc}"
        )

    return start_utc, end_utc


def get_time_window_utc(
    hours_back: int = 24, hours_forward: int = 0
) -> tuple[datetime, datetime]:
    now = utc_now()
    start_utc = now - timedelta(hours=hours_back)
    end_utc = now + timedelta(hours=hours_forward)

    return start_utc, end_utc


# Database query helpers
def utc_filter_recent(column, hours: int = 24):
    cutoff = time_ago_utc(hours=hours)
    return column >= cutoff


def utc_filter_older_than(column, hours: int = 24):
    cutoff = time_ago_utc(hours=hours)
    return column < cutoff


def utc_filter_between(column, start_hours_ago: int, end_hours_ago: int = 0):
    start_time = time_ago_utc(hours=start_hours_ago)
    end_time = time_ago_utc(hours=end_hours_ago)

    from sqlalchemy import and_

    return and_(column >= start_time, column <= end_time)
