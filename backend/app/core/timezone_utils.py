# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)


def get_available_timezones() -> list[str]:
    return sorted(available_timezones())


def validate_timezone(timezone_str: str) -> bool:
    try:
        ZoneInfo(timezone_str)
        return True
    except (ZoneInfoNotFoundError, ValueError):
        return False


def utc_to_local(utc_dt: datetime, timezone_str: str) -> datetime:
    if not utc_dt:
        return None

    try:
        # Ensure datetime is timezone-aware
        if utc_dt.tzinfo is None:
            utc_dt = utc_dt.replace(tzinfo=UTC)

        # Convert to target timezone
        local_tz = ZoneInfo(timezone_str)
        return utc_dt.astimezone(local_tz)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as e:
        logger.error("Timezone conversion error: %s", e)
        return utc_dt


def local_to_utc(local_dt: datetime, timezone_str: str) -> datetime:
    if not local_dt:
        return None

    try:
        local_tz = ZoneInfo(timezone_str)

        # Attach local timezone if naive
        if local_dt.tzinfo is None:
            local_dt = local_dt.replace(tzinfo=local_tz)

        # Convert to UTC
        return local_dt.astimezone(UTC)
    except (ZoneInfoNotFoundError, ValueError, TypeError) as e:
        logger.error("Timezone conversion error: %s", e)
        return local_dt


def format_datetime_local(
    utc_dt: datetime, timezone_str: str, format_str: str = "%Y-%m-%d %I:%M %p %Z"
) -> str:
    if not utc_dt:
        return ""

    local_dt = utc_to_local(utc_dt, timezone_str)
    return local_dt.strftime(format_str)


def get_timezone_offset(timezone_str: str) -> str:
    try:
        now = datetime.now(ZoneInfo(timezone_str))
        offset = now.strftime("%z")
        # Format as +HH:MM or -HH:MM
        return f"{offset[:3]}:{offset[3:]}"
    except (ZoneInfoNotFoundError, ValueError):
        return "+00:00"


async def get_branch_timezone(db: AsyncSession, branch_id: int) -> str | None:
    from sqlalchemy.orm import joinedload

    from app.models.multi_branch import Branch

    result = await db.execute(
        select(Branch).options(joinedload(Branch.library_system)).filter(Branch.id == branch_id)
    )
    branch = result.scalar_one_or_none()
    return branch.library_system.timezone if branch and branch.library_system else None


# Common US timezones for quick reference
US_TIMEZONES = {
    "America/New_York": "Eastern (ET)",
    "America/Chicago": "Central (CT)",
    "America/Denver": "Mountain (MT)",
    "America/Phoenix": "Arizona (MST - no DST)",
    "America/Los_Angeles": "Pacific (PT)",
    "America/Anchorage": "Alaska (AKT)",
    "Pacific/Honolulu": "Hawaii (HST)",
}


def get_common_timezones() -> dict[str, str]:
    return US_TIMEZONES
