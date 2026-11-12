# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from .base import BaseNotificationService
from .types import NotificationType
from .templates import (
    render_checkout_receipt_email,
    render_due_date_reminder_email,
    render_overdue_notice_email,
    render_hold_ready_email,
    render_hold_expiring_email,
)

settings = get_settings()
logger = get_logger(__name__)


class CirculationNotificationService(BaseNotificationService):

    # =========================================================================
    # Patron circulation email rendering
    # =========================================================================

    @staticmethod
    def render_checkout_receipt_email(user, item, checkout) -> tuple:
        return render_checkout_receipt_email(user, item, checkout)

    @staticmethod
    def render_due_date_reminder_email(user, item, checkout, days_until_due: int) -> tuple:
        return render_due_date_reminder_email(user, item, checkout, days_until_due)

    @staticmethod
    def render_overdue_notice_email(
        user, item, checkout, days_overdue: int, fine_amount: Optional[float] = None
    ) -> tuple:
        return render_overdue_notice_email(user, item, checkout, days_overdue, fine_amount)

    @staticmethod
    def render_hold_ready_email(user, item, hold) -> tuple:
        return render_hold_ready_email(user, item, hold)

    @staticmethod
    def render_hold_expiring_email(user, item, hold, days_until_expiry: int) -> tuple:
        return render_hold_expiring_email(user, item, hold, days_until_expiry)

    async def send_hold_ready_sms(
        self,
        user_id: int,
        item_title: str,
        expires_date: str,
        db: AsyncSession,
    ) -> bool:
        from ..sms_service import sms_service, SMSNotificationType, DEFAULT_TEMPLATES

        if not settings.sms_enabled:
            return False

        prefs = await self.get_or_create_preferences(user_id, db)

        if not prefs.sms_notifications_enabled or not prefs.sms_phone_verified:
            return False

        if not prefs.sms_hold_ready:
            return False

        if len(item_title) > 30:
            item_title = item_title[:27] + "..."

        template = DEFAULT_TEMPLATES.get(SMSNotificationType.HOLD_READY, "")
        message = sms_service.render_template(template, {
            "title": item_title,
            "expires_date": expires_date,
            "phone": "",
        })

        try:
            await sms_service.queue_sms(
                user_id=user_id,
                phone_number=prefs.sms_phone_number,
                notification_type=SMSNotificationType.HOLD_READY,
                message=message,
                context_data={"item_title": item_title},
                db=db,
            )
            return True
        except Exception as e:  # noqa: BLE001  # SMS dispatch boundary - failure must not break hold-ready flow
            logger.warning(f"Failed to queue hold ready SMS: {e}")
            return False
