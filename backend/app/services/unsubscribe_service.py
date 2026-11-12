# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.frontend_routes import routes
from ..core.logging import get_logger
from ..models.marketing import (
    EmailUnsubscribeToken,
    NewsletterSubscription,
    NewArrivalAlert,
    SubscriptionStatus,
    UnsubscribeReason,
)
from ..models.notification import NotificationPreferences, NotificationType

settings = get_settings()
logger = get_logger(__name__)


class UnsubscribeService:

    # Mapping of notification types to preference fields
    NOTIFICATION_PREFERENCE_MAP = {
        NotificationType.CHECKOUT_RECEIPT: "email_checkout_receipt",
        NotificationType.DUE_DATE_REMINDER: "email_due_date_reminder",
        NotificationType.OVERDUE_NOTICE: "email_overdue_notice",
        NotificationType.HOLD_READY: "email_hold_ready",
        NotificationType.HOLD_EXPIRING: "email_hold_expiring",
        NotificationType.HOLD_CANCELLED: "email_hold_cancelled",
        NotificationType.FINE_NOTICE: "email_fine_notice",
        NotificationType.TRAINING_NEW_COURSE: "email_training_new_course",
        NotificationType.TRAINING_COURSE_COMPLETED: "email_training_course_completed",
        NotificationType.TRAINING_MILESTONE_REACHED: "email_training_milestone",
        NotificationType.TRAINING_CERTIFICATE_EARNED: "email_training_certificate",
        NotificationType.TRAINING_STREAK_REMINDER: "email_training_streak_reminder",
        NotificationType.TRAINING_NEW_CONTENT: "email_training_new_content",
        NotificationType.TRAINING_SKILL_ASSESSMENT_DUE: "email_training_skill_assessment",
        NotificationType.TRAINING_WEEKLY_DIGEST: "email_training_weekly_digest",
    }

    async def generate_unsubscribe_token(
        self,
        db: AsyncSession,
        email: str,
        email_type: str,
        user_id: Optional[int] = None,
        email_category: Optional[str] = None,
    ) -> str:
        token = secrets.token_urlsafe(32)

        unsubscribe_token = EmailUnsubscribeToken(
            token=token,
            email=email.lower(),
            user_id=user_id,
            email_type=email_type,
            email_category=email_category,
        )

        db.add(unsubscribe_token)
        await db.commit()

        return token

    def generate_unsubscribe_url(self, token: str) -> str:
        return f"{routes.url(settings.frontend_url, routes.unsubscribe)}?token={token}"

    def generate_preferences_url(self, token: str) -> str:
        return f"{routes.url(settings.frontend_url, routes.email_preferences)}?token={token}"

    def generate_list_unsubscribe_header(self, token: str) -> dict:
        unsubscribe_url = self.generate_unsubscribe_url(token)

        # settings has no standalone `email_domain` field; derive it from
        # FROM_EMAIL the same way app/seeds/bootstrap_library_system.py does.
        email_domain = settings.from_email.split("@")[-1]
        return {
            "List-Unsubscribe": f"<{unsubscribe_url}>, <mailto:unsubscribe@{email_domain}?subject=unsubscribe-{token}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }

    async def process_unsubscribe(
        self,
        db: AsyncSession,
        token: str,
        reason: Optional[UnsubscribeReason] = None,
        feedback: Optional[str] = None,
    ) -> dict:
        # Find the token
        result = await db.execute(
            select(EmailUnsubscribeToken).where(
                EmailUnsubscribeToken.token == token
            )
        )
        unsubscribe_token = result.scalar_one_or_none()

        if not unsubscribe_token:
            return {"success": False, "error": "Invalid or expired token"}

        if unsubscribe_token.used_at:
            return {"success": False, "error": "Token already used"}

        # Mark token as used
        unsubscribe_token.used_at = datetime.now(timezone.utc)

        email = unsubscribe_token.email
        email_type = unsubscribe_token.email_type
        email_category = unsubscribe_token.email_category
        user_id = unsubscribe_token.user_id

        # Process based on email type
        if email_type == "newsletter":
            await self._unsubscribe_newsletter(db, email, reason, feedback)
            message = "You have been unsubscribed from our newsletter"

        elif email_type == "alert":
            await self._unsubscribe_alert(db, email, email_category, user_id)
            message = "You have been unsubscribed from this alert"

        elif email_type == "notification" and email_category:
            await self._unsubscribe_notification(db, user_id, email_category)
            message = f"You have been unsubscribed from {email_category.replace('_', ' ')} notifications"

        elif email_type == "all":
            await self._unsubscribe_all(db, email, user_id, reason, feedback)
            message = "You have been unsubscribed from all marketing emails"

        else:
            return {"success": False, "error": "Unknown email type"}

        await db.commit()

        logger.info(
            "Unsubscribe processed",
            extra={
                "email_type": email_type,
                "email_category": email_category,
                "reason": reason.value if reason else None,
            }
        )

        return {
            "success": True,
            "message": message,
            "email_type": email_type,
            "email_category": email_category,
        }

    async def _unsubscribe_newsletter(
        self,
        db: AsyncSession,
        email: str,
        reason: Optional[UnsubscribeReason],
        feedback: Optional[str],
    ) -> None:
        result = await db.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == email.lower()
            )
        )
        subscription = result.scalar_one_or_none()

        if subscription:
            subscription.status = SubscriptionStatus.UNSUBSCRIBED
            subscription.unsubscribed_at = datetime.now(timezone.utc)
            subscription.unsubscribe_reason = reason or UnsubscribeReason.ONE_CLICK
            subscription.unsubscribe_feedback = feedback

    async def _unsubscribe_alert(
        self,
        db: AsyncSession,
        email: str,
        alert_type: Optional[str],
        user_id: Optional[int],
    ) -> None:
        if user_id:
            # Deactivate matching alerts
            result = await db.execute(
                select(NewArrivalAlert).where(
                    NewArrivalAlert.user_id == user_id,
                    NewArrivalAlert.is_active == True,
                )
            )
            alerts = result.scalars().all()
            for alert in alerts:
                alert.is_active = False

    async def _unsubscribe_notification(
        self,
        db: AsyncSession,
        user_id: Optional[int],
        notification_type: str,
    ) -> None:
        if not user_id:
            return

        result = await db.execute(
            select(NotificationPreferences).where(
                NotificationPreferences.user_id == user_id
            )
        )
        prefs = result.scalar_one_or_none()

        if prefs:
            # Map notification type to preference field
            try:
                notif_type = NotificationType(notification_type)
                field_name = self.NOTIFICATION_PREFERENCE_MAP.get(notif_type)
                if field_name and hasattr(prefs, field_name):
                    setattr(prefs, field_name, False)
            except ValueError:
                pass  # Unknown notification type

    async def _unsubscribe_all(
        self,
        db: AsyncSession,
        email: str,
        user_id: Optional[int],
        reason: Optional[UnsubscribeReason],
        feedback: Optional[str],
    ) -> None:
        # Unsubscribe newsletter
        await self._unsubscribe_newsletter(db, email, reason, feedback)

        # Deactivate all alerts
        if user_id:
            result = await db.execute(
                select(NewArrivalAlert).where(
                    NewArrivalAlert.user_id == user_id,
                    NewArrivalAlert.is_active == True,
                )
            )
            alerts = result.scalars().all()
            for alert in alerts:
                alert.is_active = False

    async def get_subscription_status(
        self,
        db: AsyncSession,
        token: str,
    ) -> Optional[dict]:
        result = await db.execute(
            select(EmailUnsubscribeToken).where(
                EmailUnsubscribeToken.token == token
            )
        )
        unsubscribe_token = result.scalar_one_or_none()

        if not unsubscribe_token:
            return None

        email = unsubscribe_token.email
        user_id = unsubscribe_token.user_id

        # Get newsletter subscription
        newsletter_result = await db.execute(
            select(NewsletterSubscription).where(
                NewsletterSubscription.email == email.lower()
            )
        )
        newsletter = newsletter_result.scalar_one_or_none()

        # Get notification preferences
        notification_prefs = None
        if user_id:
            prefs_result = await db.execute(
                select(NotificationPreferences).where(
                    NotificationPreferences.user_id == user_id
                )
            )
            notification_prefs = prefs_result.scalar_one_or_none()

        # Get active alerts
        alerts = []
        if user_id:
            alerts_result = await db.execute(
                select(NewArrivalAlert).where(
                    NewArrivalAlert.user_id == user_id,
                    NewArrivalAlert.is_active == True,
                )
            )
            alerts = [
                {
                    "id": a.id,
                    "category_id": a.category_id,
                    "search_query": a.search_query,
                    "author_name": a.author_name,
                }
                for a in alerts_result.scalars().all()
            ]

        return {
            "email": email,
            "newsletter": {
                "subscribed": newsletter is not None and newsletter.is_active,
                "frequency": str(newsletter.frequency) if newsletter else None,
            } if newsletter else None,
            "notifications": {
                "checkout_receipt": notification_prefs.email_checkout_receipt if notification_prefs else True,
                "due_date_reminder": notification_prefs.email_due_date_reminder if notification_prefs else True,
                "overdue_notice": notification_prefs.email_overdue_notice if notification_prefs else True,
                "hold_ready": notification_prefs.email_hold_ready if notification_prefs else True,
                "hold_expiring": notification_prefs.email_hold_expiring if notification_prefs else True,
                "fine_notice": notification_prefs.email_fine_notice if notification_prefs else True,
            } if notification_prefs else None,
            "alerts": alerts,
        }


# Singleton instance
unsubscribe_service = UnsubscribeService()
