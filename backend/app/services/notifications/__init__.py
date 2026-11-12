# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Notification services package.

This package provides a unified interface for sending notifications across all domains
including patron circulation, makerspace, delivery, alerts, emergency, reviews, and payouts.

The package is organized into specialized modules:
- types.py: Notification type enums and shared data structures
- templates.py: Template provider and HTML email template rendering
- base.py: Core base class with shared notification infrastructure
- circulation.py: Library patron circulation notifications
- emergency.py: Emergency/panic alert notifications
- makerspace.py: Makerspace reservation/job/workshop notifications
- delivery.py: HomeDelivery delivery notifications
- alerts.py: Privacy/moderation alert notifications
- email_sender.py: Email delivery service
- preferences.py: User preference management
- batching.py: Batch sending logic
"""

# Types and data structures
from .types import (
    NotificationType,
    NotificationChannel,
    NotificationTemplate,
    NotificationContent,
    NotificationRecipient,
    NotificationResult,
    NotificationConfig,
    CirculationNotificationType,
    MakerspaceNotificationType,
    DeliveryNotificationType,
    AlertNotificationType,
    EmergencyNotificationType,
    PayoutNotificationType,
    ReviewNotificationType,
)

# Base class
from .base import BaseNotificationService

# Domain-specific services
from .circulation import CirculationNotificationService
from .emergency import EmergencyNotificationService
from .makerspace import MakerspaceNotificationService
from .delivery import DeliveryNotificationService
from .alerts import AlertNotificationService

# Template provider
from .templates import DomainTemplateProvider

# Infrastructure services
from .preferences import PreferencesManager
from .email_sender import EmailSenderService
from .batching import BatchNotificationService


# =============================================================================
# Unified Notification Service (Facade)
# =============================================================================


class UnifiedNotificationService(BaseNotificationService):

    def __init__(self):
        super().__init__()
        self._circulation = CirculationNotificationService()
        self._emergency = EmergencyNotificationService()
        self._makerspace = MakerspaceNotificationService()
        self._delivery = DeliveryNotificationService()
        self._alerts = AlertNotificationService()

    # =========================================================================
    # Circulation delegation
    # =========================================================================

    @staticmethod
    def render_checkout_receipt_email(user, item, checkout):
        return CirculationNotificationService.render_checkout_receipt_email(user, item, checkout)

    @staticmethod
    def render_due_date_reminder_email(user, item, checkout, days_until_due):
        return CirculationNotificationService.render_due_date_reminder_email(user, item, checkout, days_until_due)

    @staticmethod
    def render_overdue_notice_email(user, item, checkout, days_overdue, fine_amount=None):
        return CirculationNotificationService.render_overdue_notice_email(user, item, checkout, days_overdue, fine_amount)

    @staticmethod
    def render_hold_ready_email(user, item, hold):
        return CirculationNotificationService.render_hold_ready_email(user, item, hold)

    @staticmethod
    def render_hold_expiring_email(user, item, hold, days_until_expiry):
        return CirculationNotificationService.render_hold_expiring_email(user, item, hold, days_until_expiry)

    async def send_hold_ready_sms(self, user_id, item_title, expires_date, db):
        return await self._circulation.send_hold_ready_sms(user_id, item_title, expires_date, db)

    # =========================================================================
    # Alert delegation
    # =========================================================================

    async def notify_privacy_alert(self, alert, db):
        return await self._alerts.notify_privacy_alert(alert, db)

    async def notify_moderation_alert(self, alert, db):
        return await self._alerts.notify_moderation_alert(alert, db)

    async def send_daily_digest(self, db):
        return await self._alerts.send_daily_digest(db)

    # =========================================================================
    # Emergency delegation
    # =========================================================================

    async def notify_police_911(self, panic_alert, db, emergency_type="security_emergency", location_details=None):
        return await self._emergency.notify_police_911(panic_alert, db, emergency_type, location_details)

    async def notify_security_company(self, panic_alert, db, company_name="Building Security Company", phone=None):
        return await self._emergency.notify_security_company(panic_alert, db, company_name, phone)

    async def notify_building_staff(self, panic_alert, db):
        return await self._emergency.notify_building_staff(panic_alert, db)

    # =========================================================================
    # Makerspace delegation
    # =========================================================================

    @staticmethod
    async def notify_reservation_created(db, reservation):
        return await MakerspaceNotificationService.notify_reservation_created(db, reservation)

    @staticmethod
    async def notify_reservation_reminder(db, reservation):
        return await MakerspaceNotificationService.notify_reservation_reminder(db, reservation)

    @staticmethod
    async def notify_job_submitted(db, job):
        return await MakerspaceNotificationService.notify_job_submitted(db, job)

    @staticmethod
    async def notify_job_approved(db, job):
        return await MakerspaceNotificationService.notify_job_approved(db, job)

    @staticmethod
    async def notify_job_rejected(db, job):
        return await MakerspaceNotificationService.notify_job_rejected(db, job)

    @staticmethod
    async def notify_job_ready_pickup(db, job):
        return await MakerspaceNotificationService.notify_job_ready_pickup(db, job)

    @staticmethod
    async def notify_waitlist_joined(db, waitlist_entry):
        return await MakerspaceNotificationService.notify_waitlist_joined(db, waitlist_entry)

    @staticmethod
    async def notify_waitlist_slot_available(db, waitlist_entry, expires_in_hours=24):
        return await MakerspaceNotificationService.notify_waitlist_slot_available(db, waitlist_entry, expires_in_hours)

    @staticmethod
    async def notify_workshop_registration(db, registration, is_waitlisted=False):
        return await MakerspaceNotificationService.notify_workshop_registration(db, registration, is_waitlisted)

    @staticmethod
    async def notify_workshop_reminder(db, registration):
        return await MakerspaceNotificationService.notify_workshop_reminder(db, registration)

    @staticmethod
    async def notify_certification_expiring(db, certification, days_until_expiry):
        return await MakerspaceNotificationService.notify_certification_expiring(db, certification, days_until_expiry)

    @staticmethod
    async def notify_certification_completed(db, certification):
        return await MakerspaceNotificationService.notify_certification_completed(db, certification)

    @staticmethod
    async def send_reservation_reminders(db):
        return await MakerspaceNotificationService.send_reservation_reminders(db)

    @staticmethod
    async def send_workshop_reminders(db):
        return await MakerspaceNotificationService.send_workshop_reminders(db)

    @staticmethod
    async def send_certification_expiry_warnings(db, days_before=30):
        return await MakerspaceNotificationService.send_certification_expiry_warnings(db, days_before)

    # =========================================================================
    # Delivery delegation
    # =========================================================================

    async def send_delivery_notification_to_recipient(self, notification_type, recipient, context, channels=None):
        return await self._delivery.send_delivery_notification_to_recipient(notification_type, recipient, context, channels)

    async def send_delivery_reminders(self, db):
        return await self._delivery.send_delivery_reminders(db)

    async def send_feedback_requests(self, db, feedback_delay_hours=24):
        return await self._delivery.send_feedback_requests(db, feedback_delay_hours)

    # =========================================================================
    # Preferences delegation
    # =========================================================================

    @staticmethod
    async def get_or_create_preferences(user_id: int, db):
        return await PreferencesManager.get_or_create_preferences(user_id, db)

    @staticmethod
    async def update_preferences(user_id: int, preferences_data: dict, db):
        return await PreferencesManager.update_preferences(user_id, preferences_data, db)


# =============================================================================
# Factory (backward compat)
# =============================================================================


class NotificationFactory:

    _unified_service = None

    @classmethod
    def _get_service(cls):
        if cls._unified_service is None:
            cls._unified_service = UnifiedNotificationService()
        return cls._unified_service

    @classmethod
    def get_unified_service(cls):
        return cls._get_service()

    @classmethod
    async def send_patron_notification(cls, notification_type, recipient_email, subject, html_body, context_data, user_id=None, db=None):
        result = await cls._get_service().send_notification(
            notification_type=notification_type,
            recipient_email=recipient_email,
            subject=subject,
            html_body=html_body,
            context_data=context_data,
            user_id=user_id,
            db=db,
        )
        return result is not None

    @classmethod
    async def send_makerspace_notification(cls, notification_type, recipient_email, context_data, db=None):
        return await cls._get_service().send_templated(
            notification_type=notification_type,
            recipient_email=recipient_email,
            context_data=context_data,
            db=db,
        )

    @classmethod
    async def send_delivery_notification(cls, notification_type, recipient_email, context_data, db=None):
        return await cls._get_service().send_templated(
            notification_type=notification_type,
            recipient_email=recipient_email,
            context_data=context_data,
            db=db,
        )

    @classmethod
    async def send_alert_notification(cls, notification_type, recipient_email, subject, body, context_data, db=None):
        result = await cls._get_service().send_notification(
            notification_type=notification_type,
            recipient_email=recipient_email,
            subject=subject,
            html_body=body,
            context_data=context_data,
            db=db,
        )
        return result is not None

    @classmethod
    async def send_emergency_notification(cls, notification_type, recipient_email, message, context_data, db=None):
        result = await cls._get_service().send_notification(
            notification_type=notification_type,
            recipient_email=recipient_email,
            subject="EMERGENCY ALERT",
            html_body=message,
            context_data=context_data,
            db=db,
        )
        return result is not None


# =============================================================================
# Singleton instances
# =============================================================================

notification_service = UnifiedNotificationService()
notification_factory = NotificationFactory()

__all__ = [
    # Types
    "NotificationType",
    "NotificationChannel",
    "NotificationTemplate",
    "NotificationContent",
    "NotificationRecipient",
    "NotificationResult",
    "NotificationConfig",
    # Domain-specific type enums
    "CirculationNotificationType",
    "MakerspaceNotificationType",
    "DeliveryNotificationType",
    "AlertNotificationType",
    "EmergencyNotificationType",
    "PayoutNotificationType",
    "ReviewNotificationType",
    # Base class
    "BaseNotificationService",
    # Domain services
    "CirculationNotificationService",
    "EmergencyNotificationService",
    "MakerspaceNotificationService",
    "DeliveryNotificationService",
    "AlertNotificationService",
    # Template provider
    "DomainTemplateProvider",
    # Infrastructure services
    "PreferencesManager",
    "EmailSenderService",
    "BatchNotificationService",
    # Facade and factory (backward compatibility)
    "UnifiedNotificationService",
    "NotificationFactory",
    "notification_service",
    "notification_factory",
]
