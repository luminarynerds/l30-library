# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from ..core.logging import get_logger

logger = get_logger(__name__)

# In-memory counters for Prometheus-style metrics (scraped by /metrics endpoint).
# These are process-local and reset on restart; the DB tables provide durable history.
_counters: dict[str, int] = {}


def _increment(metric: str, labels: dict[str, str], count: int = 1) -> None:
    key = f"{metric}|" + "|".join(f"{k}={v}" for k, v in sorted(labels.items()))
    _counters[key] = _counters.get(key, 0) + count


def get_metrics_snapshot() -> dict[str, int]:
    return dict(_counters)


def _hash_recipient(recipient: str) -> str:
    return hashlib.sha256(recipient.lower().strip().encode()).hexdigest()


def _hint_recipient(recipient: str, channel: str) -> str:
    if channel == "email" and "@" in recipient:
        _, domain = recipient.rsplit("@", 1)
        return f"***@{domain}"
    if channel == "sms" and len(recipient) >= 4:
        return f"***{recipient[-4:]}"
    return "***"


async def track_notification(
    channel: str,
    template_name: str,
    recipient: str,
    *,
    success: bool,
    error: Optional[str] = None,
    error_type: Optional[str] = None,
    http_status_code: Optional[int] = None,
    subject: Optional[str] = None,
) -> None:
    status_label = "success" if success else "failure"
    _increment("notification_send_total", {"channel": channel, "template": template_name, "status": status_label})

    if error_type == "timeout":
        _increment("notification_send_total", {"channel": channel, "template": template_name, "status": "timeout"})

    if success:
        return

    # --- Failure path: write to dead letter queue ---
    try:
        from ..core.database import AsyncSessionLocal
        from ..models.notification_failure import (
            FailedNotificationRecord,
            NotificationChannel,
            NotificationFailureStatus,
        )

        channel_enum = NotificationChannel.EMAIL if channel == "email" else NotificationChannel.SMS
        now = datetime.now(timezone.utc)

        record = FailedNotificationRecord(
            channel=channel_enum,
            template_name=template_name,
            recipient_hash=_hash_recipient(recipient),
            recipient_hint=_hint_recipient(recipient, channel),
            subject=subject[:500] if subject else None,
            error_message=error or "Unknown error",
            error_type=error_type,
            http_status_code=http_status_code,
            status=NotificationFailureStatus.PENDING,
            retry_count=0,
            max_retries=3,
            next_retry_at=now + timedelta(seconds=30),
        )

        async with AsyncSessionLocal() as db:
            db.add(record)
            await db.commit()

        logger.warning(
            "Notification delivery failed, queued for retry",
            extra={
                "channel": channel,
                "template": template_name,
                "recipient_hint": _hint_recipient(recipient, channel),
                "error": error,
                "error_type": error_type,
            },
        )

    except Exception as exc:
        # Tracking must never break the caller
        logger.error(
            f"Failed to record notification failure in DLQ: {exc}",
            extra={"channel": channel, "template": template_name},
            exc_info=True,
        )
