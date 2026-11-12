# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timezone

from .config import get_settings
from .email_safeguard_config import (
    get_alert_threshold,
    get_daily_send_cap,
    get_dedup_window_hours,
)

logger = get_logger(__name__)


async def _get_redis_client():
    try:
        from .cache import get_redis
        return await get_redis()
    except Exception as e:  # noqa: BLE001  # fail-open boundary — Redis outage must not block email
        logger.warning(
            "Email safeguards: Redis unavailable, failing open",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return None


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _current_hour_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d-%H")


def _dedup_window_key(dedup_window_hours: int) -> str:
    now = datetime.now(timezone.utc)

    # For 24+ hour windows, use daily granularity
    if dedup_window_hours >= 24:
        return now.strftime("%Y-%m-%d")

    # For sub-day windows, use hour-bucketed granularity
    # Calculate which bucket of the day we're in
    window = max(1, dedup_window_hours)
    hour_bucket = (now.hour // window) * window
    return now.strftime("%Y-%m-%d") + f"-{hour_bucket:02d}h"


async def check_daily_cap() -> bool:
    try:
        client = await _get_redis_client()
        if client is None:
            return True  # fail-open

        cap = await get_daily_send_cap()
        key = f"email:daily_count:{_today_key()}"
        count = await client.get(key)
        current_count = int(count) if count is not None else 0

        if current_count >= cap:
            logger.critical(
                "EMAIL DAILY CAP REACHED: %d/%d emails sent today. "
                "All further emails will be blocked until midnight UTC.",
                current_count,
                cap,
                extra={
                    "daily_count": current_count,
                    "daily_cap": cap,
                    "date": _today_key(),
                },
            )
            return False

        return True
    except Exception as e:  # noqa: BLE001  # fail-open boundary — daily-cap check must not block email on Redis errors
        logger.warning(
            "Email safeguards: check_daily_cap failed, failing open",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return True  # fail-open


async def increment_daily_count() -> int:
    try:
        client = await _get_redis_client()
        if client is None:
            return -1

        daily_key = f"email:daily_count:{_today_key()}"
        hourly_key = f"email:hourly_count:{_current_hour_key()}"

        # Increment daily counter with 48-hour TTL for auto-cleanup
        new_daily_count = await client.incr(daily_key)
        if new_daily_count == 1:
            await client.expire(daily_key, 48 * 3600)  # 48 hours TTL

        # Increment hourly counter with 2-hour TTL
        new_hourly_count = await client.incr(hourly_key)
        if new_hourly_count == 1:
            await client.expire(hourly_key, 2 * 3600)  # 2 hours TTL

        # Check hourly alert threshold
        alert_threshold = await get_alert_threshold()
        if new_hourly_count == alert_threshold:
            logger.warning(
                "EMAIL RATE ALERT: %d emails sent in the current hour "
                "(threshold: %d). Possible notification storm.",
                new_hourly_count,
                alert_threshold,
                extra={
                    "hourly_count": new_hourly_count,
                    "alert_threshold": alert_threshold,
                    "hour": _current_hour_key(),
                    "daily_count": new_daily_count,
                },
            )

        return new_daily_count
    except Exception as e:  # noqa: BLE001  # fail-open boundary — counter failures must not block email
        logger.warning(
            "Email safeguards: increment_daily_count failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return -1


async def increment_cap_skipped() -> int:
    try:
        client = await _get_redis_client()
        if client is None:
            return -1

        key = f"email:cap_skipped:{_today_key()}"
        new_count = await client.incr(key)
        if new_count == 1:
            await client.expire(key, 48 * 3600)  # 48-hour TTL for auto-cleanup
        return new_count
    except Exception as e:  # noqa: BLE001  # fail-open boundary — skip-counter failures must not block email
        logger.warning(
            "Email safeguards: increment_cap_skipped failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return -1


async def get_cap_skipped_today() -> int:
    try:
        client = await _get_redis_client()
        if client is None:
            return 0
        key = f"email:cap_skipped:{_today_key()}"
        raw = await client.get(key)
        return int(raw) if raw is not None else 0
    except Exception:  # noqa: BLE001  # fail-open boundary — stats lookup, default to 0 on any error
        return 0


async def check_dedup(patron_id: int, notification_type: str) -> bool:
    try:
        client = await _get_redis_client()
        if client is None:
            return True  # fail-open

        window_hours = await get_dedup_window_hours()
        time_key = _dedup_window_key(window_hours)
        key = f"email:dedup:{patron_id}:{notification_type}:{time_key}"
        exists = await client.exists(key)
        if exists:
            logger.info(
                "Email dedup: skipping duplicate %s notification for patron %d",
                notification_type,
                patron_id,
                extra={
                    "patron_id": patron_id,
                    "notification_type": notification_type,
                    "dedup_key": key,
                },
            )
            return False

        return True
    except Exception as e:  # noqa: BLE001  # fail-open boundary — dedup check must not block email
        logger.warning(
            "Email safeguards: check_dedup failed, failing open",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "patron_id": patron_id,
                "notification_type": notification_type,
            },
        )
        return True  # fail-open


async def mark_sent(patron_id: int, notification_type: str) -> None:
    try:
        client = await _get_redis_client()
        if client is None:
            return

        window_hours = await get_dedup_window_hours()
        time_key = _dedup_window_key(window_hours)
        key = f"email:dedup:{patron_id}:{notification_type}:{time_key}"
        ttl_seconds = window_hours * 3600
        await client.setex(key, ttl_seconds, "1")
    except Exception as e:  # noqa: BLE001  # fail-open boundary — dedup mark failures must not block email
        logger.warning(
            "Email safeguards: mark_sent failed",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "patron_id": patron_id,
                "notification_type": notification_type,
            },
        )


async def get_email_stats() -> dict:
    try:
        client = await _get_redis_client()
        if client is None:
            return {
                "daily_count": -1,
                "daily_cap": await get_daily_send_cap(),
                "hourly_count": -1,
                "cap_skipped_today": -1,
                "status": "unknown",
                "message": "Redis unavailable - safeguards failing open",
            }

        daily_key = f"email:daily_count:{_today_key()}"
        hourly_key = f"email:hourly_count:{_current_hour_key()}"
        cap_skipped_key = f"email:cap_skipped:{_today_key()}"

        daily_count_raw = await client.get(daily_key)
        hourly_count_raw = await client.get(hourly_key)
        cap_skipped_raw = await client.get(cap_skipped_key)
        daily_count = int(daily_count_raw) if daily_count_raw is not None else 0
        hourly_count = int(hourly_count_raw) if hourly_count_raw is not None else 0
        cap_skipped_today = int(cap_skipped_raw) if cap_skipped_raw is not None else 0

        cap = await get_daily_send_cap()
        alert_threshold = await get_alert_threshold()
        usage_pct = (daily_count / cap * 100) if cap > 0 else 0

        if usage_pct >= 100:
            email_status = "critical"
        elif usage_pct >= 80:
            email_status = "warning"
        else:
            email_status = "ok"

        return {
            "daily_count": daily_count,
            "daily_cap": cap,
            "usage_percent": round(usage_pct, 1),
            "hourly_count": hourly_count,
            "alert_threshold": alert_threshold,
            "cap_skipped_today": cap_skipped_today,
            "status": email_status,
        }
    except Exception as e:  # noqa: BLE001  # fail-open boundary — stats endpoint must not raise; return sentinel dict
        logger.warning(
            "Email safeguards: get_email_stats failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        try:
            fallback_cap = await get_daily_send_cap()
        except Exception:  # noqa: BLE001  # fallback cap lookup — must always yield a value
            fallback_cap = get_settings().email_daily_send_cap
        return {
            "daily_count": -1,
            "daily_cap": fallback_cap,
            "hourly_count": -1,
            "cap_skipped_today": -1,
            "status": "unknown",
            "message": f"Error retrieving stats: {str(e)}",
        }


async def email_cap_remaining() -> int:
    try:
        stats = await get_email_stats()
        cap = int(stats.get("daily_cap") or 0)
        count = stats.get("daily_count")
        # -1 is the Redis-unavailable sentinel in get_email_stats(); treat
        # as "no enforcement possible" and fail open to the full cap.
        if count is None or int(count) < 0:
            return cap
        return max(0, cap - int(count))
    except Exception as e:  # noqa: BLE001  # fail-open boundary — remaining-cap lookup, return full cap on any error
        logger.warning(
            "Email safeguards: email_cap_remaining failed, failing open",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        try:
            return await get_daily_send_cap()
        except Exception:  # noqa: BLE001  # fallback cap lookup — must always yield a value
            return get_settings().email_daily_send_cap
