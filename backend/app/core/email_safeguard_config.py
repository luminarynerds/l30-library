# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional

from sqlalchemy import select

from .config import get_settings
from .database import get_async_session
from ..models.organization_features import OrganizationFeatures


DEFAULTS = {
    "email_daily_send_cap": 500,
    "email_alert_threshold": 100,
    "email_dedup_window_hours": 24,
}


async def _get_db_value(field: str) -> Optional[int]:
    async with get_async_session() as db:
        result = await db.execute(select(OrganizationFeatures).limit(1))
        row = result.scalar_one_or_none()
        if row is None or not isinstance(row.configuration, dict):
            return None
        em = row.configuration.get("email_marketing")
        if not isinstance(em, dict):
            return None
        val = em.get(field)
        if val is None or val == 0:
            return None
        try:
            return int(val)
        except (TypeError, ValueError):
            return None


async def _resolve(field: str, env_value: int) -> int:
    if env_value and env_value != DEFAULTS[field]:
        return env_value
    db_val = await _get_db_value(field)
    return db_val if db_val is not None else env_value


async def get_daily_send_cap() -> int:
    return await _resolve("email_daily_send_cap", get_settings().email_daily_send_cap)


async def get_alert_threshold() -> int:
    return await _resolve("email_alert_threshold", get_settings().email_alert_threshold)


async def get_dedup_window_hours() -> int:
    return await _resolve("email_dedup_window_hours", get_settings().email_dedup_window_hours)
