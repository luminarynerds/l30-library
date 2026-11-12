# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import logging
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any, Optional

from app.core.logging import get_logger

# Get structured logger
logger = get_logger(__name__)


class PanicAlertLogEvent(StrEnum):

    ALERT_CREATED = "alert_created"
    ALERT_ACKNOWLEDGED = "alert_acknowledged"
    ALERT_RESOLVED = "alert_resolved"
    ALERT_CANCELLED = "alert_cancelled"
    EMAIL_SEND_ATTEMPT = "email_send_attempt"
    EMAIL_SEND_SUCCESS = "email_send_success"
    EMAIL_SEND_FAILURE = "email_send_failure"
    SMS_SEND_ATTEMPT = "sms_send_attempt"
    SMS_SEND_SUCCESS = "sms_send_success"
    SMS_SEND_FAILURE = "sms_send_failure"
    NOTIFICATION_SENT = "notification_sent"
    API_ERROR = "api_error"
    DATABASE_ERROR = "database_error"
    VALIDATION_ERROR = "validation_error"
    STATUS_TRANSITION = "status_transition"


class PanicAlertLogger:

    @staticmethod
    def log_alert_created(
        alert_id: int,
        user_id: int,
        branch_id: Optional[int],
        activation_source: str,
        location: str = "Unknown",
        has_notes: bool = False,
        metadata: Optional[dict] = None,
    ) -> None:
        logger.warning(
            f"Panic alert created: PA-{alert_id:06d}",
            extra={
                "event_type": PanicAlertLogEvent.ALERT_CREATED.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "user_id": user_id,
                "branch_id": branch_id,
                "activation_source": activation_source,
                "location": location,
                "has_notes": has_notes,
                "metadata": metadata or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_alert_acknowledged(
        alert_id: int,
        acknowledged_by_user_id: int,
        response_time_seconds: Optional[float] = None,
    ) -> None:
        logger.info(
            f"Panic alert acknowledged: PA-{alert_id:06d}",
            extra={
                "event_type": PanicAlertLogEvent.ALERT_ACKNOWLEDGED.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "acknowledged_by_user_id": acknowledged_by_user_id,
                "response_time_seconds": response_time_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_alert_resolved(
        alert_id: int,
        resolution_time_seconds: Optional[float] = None,
        has_notes: bool = False,
        false_alert: bool = False,
    ) -> None:
        logger.info(
            f"Panic alert resolved: PA-{alert_id:06d}",
            extra={
                "event_type": PanicAlertLogEvent.ALERT_RESOLVED.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "resolution_time_seconds": resolution_time_seconds,
                "has_notes": has_notes,
                "false_alert": false_alert,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_status_transition(
        alert_id: int,
        from_status: str,
        to_status: str,
        user_id: Optional[int] = None,
    ) -> None:
        logger.info(
            f"Alert status transition: PA-{alert_id:06d} {from_status} -> {to_status}",
            extra={
                "event_type": PanicAlertLogEvent.STATUS_TRANSITION.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "from_status": from_status,
                "to_status": to_status,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_email_send_attempt(
        alert_id: int,
        recipient_email: str,
        recipient_user_id: int,
        notification_type: str = "panic_alert",
    ) -> None:
        logger.info(
            f"Email send attempt for alert PA-{alert_id:06d}",
            extra={
                "event_type": PanicAlertLogEvent.EMAIL_SEND_ATTEMPT.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "recipient_email": recipient_email,
                "recipient_user_id": recipient_user_id,
                "notification_type": notification_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_email_send_success(
        alert_id: int,
        recipient_email: str,
        recipient_user_id: int,
        send_duration_seconds: Optional[float] = None,
    ) -> None:
        logger.info(
            f"Email sent successfully for alert PA-{alert_id:06d}",
            extra={
                "event_type": PanicAlertLogEvent.EMAIL_SEND_SUCCESS.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "recipient_email": recipient_email,
                "recipient_user_id": recipient_user_id,
                "send_duration_seconds": send_duration_seconds,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_email_send_failure(
        alert_id: int,
        recipient_email: str,
        recipient_user_id: int,
        error_message: str,
        error_type: str = "unknown",
        retry_count: int = 0,
    ) -> None:
        logger.error(
            f"Email send failed for alert PA-{alert_id:06d}: {error_message}",
            extra={
                "event_type": PanicAlertLogEvent.EMAIL_SEND_FAILURE.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "recipient_email": recipient_email,
                "recipient_user_id": recipient_user_id,
                "error_message": error_message,
                "error_type": error_type,
                "retry_count": retry_count,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_notification_sent(
        alert_id: int,
        recipient_count: int,
        notification_channels: list[str],
        location: str = "Unknown",
    ) -> None:
        logger.warning(
            f"Panic alert notifications sent: PA-{alert_id:06d} to {recipient_count} recipients",
            extra={
                "event_type": PanicAlertLogEvent.NOTIFICATION_SENT.value,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}",
                "recipient_count": recipient_count,
                "notification_channels": notification_channels,
                "location": location,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_api_error(
        endpoint: str,
        error_message: str,
        user_id: Optional[int] = None,
        alert_id: Optional[int] = None,
        status_code: int = 500,
        traceback: Optional[str] = None,
    ) -> None:
        logger.error(
            f"Panic alert API error at {endpoint}: {error_message}",
            extra={
                "event_type": PanicAlertLogEvent.API_ERROR.value,
                "endpoint": endpoint,
                "error_message": error_message,
                "user_id": user_id,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}" if alert_id else None,
                "status_code": status_code,
                "traceback": traceback,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_database_error(
        operation: str,
        error_message: str,
        alert_id: Optional[int] = None,
        user_id: Optional[int] = None,
    ) -> None:
        logger.error(
            f"Database error during {operation}: {error_message}",
            extra={
                "event_type": PanicAlertLogEvent.DATABASE_ERROR.value,
                "operation": operation,
                "error_message": error_message,
                "alert_id": alert_id,
                "alert_number": f"PA-{alert_id:06d}" if alert_id else None,
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def log_validation_error(
        field: str,
        error_message: str,
        user_id: Optional[int] = None,
        input_data: Optional[dict] = None,
    ) -> None:
        logger.warning(
            f"Validation error for field '{field}': {error_message}",
            extra={
                "event_type": PanicAlertLogEvent.VALIDATION_ERROR.value,
                "field": field,
                "error_message": error_message,
                "user_id": user_id,
                "input_data": input_data or {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )


# Convenience function for logging with context
def log_with_context(
    level: str,
    message: str,
    event_type: PanicAlertLogEvent,
    context: dict[str, Any],
) -> None:
    log_func = getattr(logger, level.lower(), logger.info)
    context["event_type"] = event_type.value
    context["timestamp"] = datetime.now(timezone.utc).isoformat()
    log_func(message, extra=context)
