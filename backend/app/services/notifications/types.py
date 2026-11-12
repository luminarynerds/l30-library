# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Dict, List, Optional, Tuple

logger = get_logger(__name__)


# =============================================================================
# Unified Notification Type Enum
# =============================================================================


class NotificationType(StrEnum):

    # Library Patron Circulation
    CHECKOUT_RECEIPT = "checkout_receipt"
    DUE_DATE_REMINDER = "due_date_reminder"
    OVERDUE_NOTICE = "overdue_notice"
    HOLD_READY = "hold_ready"
    HOLD_EXPIRING = "hold_expiring"
    CLAIMS_RETURNED = "claims_returned"

    # Makerspace Reservations
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_REMINDER = "reservation_reminder"
    RESERVATION_CANCELLED = "reservation_cancelled"

    # Makerspace Jobs
    JOB_SUBMITTED = "job_submitted"
    JOB_APPROVED = "job_approved"
    JOB_REJECTED = "job_rejected"
    JOB_READY_PICKUP = "job_ready_pickup"

    # Makerspace Waitlist & Workshops
    WAITLIST_JOINED = "waitlist_joined"
    WAITLIST_SLOT_AVAILABLE = "waitlist_slot_available"
    WORKSHOP_REGISTERED = "workshop_registered"
    WORKSHOP_REMINDER = "workshop_reminder"

    # Makerspace Certifications
    CERTIFICATION_EXPIRING = "certification_expiring"
    CERTIFICATION_COMPLETED = "certification_completed"

    # HomeDelivery Delivery
    DELIVERY_REMINDER = "delivery_reminder"
    DELIVERY_SCHEDULED = "delivery_scheduled"
    DELIVERY_RESCHEDULED = "delivery_rescheduled"
    DELIVERY_OUT_FOR_DELIVERY = "delivery_out_for_delivery"
    DELIVERY_COMPLETED = "delivery_completed"
    DELIVERY_FAILED = "delivery_failed"
    FEEDBACK_REQUEST = "feedback_request"
    VOLUNTEER_ASSIGNED = "volunteer_assigned"
    ENROLLMENT_APPROVED = "enrollment_approved"
    ENROLLMENT_PAUSED = "enrollment_paused"

    # Alerts
    PRIVACY_ALERT = "privacy_alert"
    MODERATION_ALERT = "moderation_alert"
    DAILY_DIGEST = "daily_digest"

    # Emergency
    POLICE_911 = "police_911"
    SECURITY_ALERT = "security_alert"
    BUILDING_STAFF_ALERT = "building_staff_alert"
    FIRE_ALERT = "fire_alert"
    MEDICAL_ALERT = "medical_alert"
    PANIC_ALERT = "panic_alert"

    # Review Responses
    REVIEW_RESPONSE = "review_response"

    # Payouts
    PAYOUT_SENT = "payout_sent"
    EARNINGS_SUMMARY = "earnings_summary"
    PAYOUT_FAILED = "payout_failed"

    # PTO & Time Off Promotion
    PTO_BALANCE_REMINDER = "pto_balance_reminder"
    PTO_PLANNING_ENCOURAGEMENT = "pto_planning_encouragement"
    PTO_COVERAGE_MESSAGEABLE = "pto_coverage_manageable"
    PTO_NO_GUILT = "pto_no_guilt"
    PTO_TIME_OFF_STRENGTH = "pto_time_off_strength"
    PTO_APPROVED_CELEBRATION = "pto_approved_celebration"
    PTO_WELCOME_BACK = "pto_welcome_back"
    PTO_VACATION_EXPIRY_WARNING = "pto_vacation_expiry_warning"

    # Patron Purchase Requests
    PURCHASE_REQUEST_SUBMITTED = "purchase_request_submitted"
    PURCHASE_REQUEST_ORDERED = "purchase_request_ordered"
    PURCHASE_REQUEST_RECEIVED = "purchase_request_received"
    PURCHASE_REQUEST_DECLINED = "purchase_request_declined"

    # Account Lifecycle
    WELCOME_EMAIL = "welcome_email"
    FINE_ASSESSMENT_NOTICE = "fine_assessment_notice"
    FINE_PAYMENT_CONFIRMATION = "fine_payment_confirmation"
    EVENT_REGISTRATION_CONFIRMATION = "event_registration_confirmation"
    EVENT_REGISTRATION_CANCELLED = "event_registration_cancelled"
    EVENT_WAITLIST_PROMOTED = "event_waitlist_promoted"
    EVENT_WAITLIST_JOINED = "event_waitlist_joined"
    EVENT_WAITLIST_SPOT_AVAILABLE = "event_waitlist_spot_available"
    EVENT_REMINDER = "event_reminder"
    EVENT_CANCELLED = "event_cancelled"

    # Reference chat
    REFERENCE_CHAT_REPLY = "reference_chat_reply"


# =============================================================================
# Domain-Specific Notification Type Enums
# =============================================================================


class CirculationNotificationType(StrEnum):
    CHECKOUT_RECEIPT = "checkout_receipt"
    DUE_DATE_REMINDER = "due_date_reminder"
    OVERDUE_NOTICE = "overdue_notice"
    HOLD_READY = "hold_ready"
    HOLD_EXPIRING = "hold_expiring"


class MakerspaceNotificationType(StrEnum):
    RESERVATION_CREATED = "reservation_created"
    RESERVATION_REMINDER = "reservation_reminder"
    RESERVATION_CANCELLED = "reservation_cancelled"
    JOB_SUBMITTED = "job_submitted"
    JOB_APPROVED = "job_approved"
    JOB_REJECTED = "job_rejected"
    JOB_READY_PICKUP = "job_ready_pickup"
    WAITLIST_JOINED = "waitlist_joined"
    WAITLIST_SLOT_AVAILABLE = "waitlist_slot_available"
    WORKSHOP_REGISTERED = "workshop_registered"
    WORKSHOP_REMINDER = "workshop_reminder"
    CERTIFICATION_EXPIRING = "certification_expiring"
    CERTIFICATION_COMPLETED = "certification_completed"


class DeliveryNotificationType(StrEnum):
    DELIVERY_REMINDER = "delivery_reminder"
    DELIVERY_SCHEDULED = "delivery_scheduled"
    DELIVERY_RESCHEDULED = "delivery_rescheduled"
    DELIVERY_OUT_FOR_DELIVERY = "delivery_out_for_delivery"
    DELIVERY_COMPLETED = "delivery_completed"
    DELIVERY_FAILED = "delivery_failed"
    FEEDBACK_REQUEST = "feedback_request"
    VOLUNTEER_ASSIGNED = "volunteer_assigned"
    ENROLLMENT_APPROVED = "enrollment_approved"
    ENROLLMENT_PAUSED = "enrollment_paused"


class AlertNotificationType(StrEnum):
    PRIVACY_ALERT = "privacy_alert"
    MODERATION_ALERT = "moderation_alert"
    DAILY_DIGEST = "daily_digest"


class EmergencyNotificationType(StrEnum):
    POLICE_911 = "police_911"
    SECURITY_ALERT = "security_alert"
    BUILDING_STAFF_ALERT = "building_staff_alert"
    FIRE_ALERT = "fire_alert"
    MEDICAL_ALERT = "medical_alert"
    PANIC_ALERT = "panic_alert"


class PayoutNotificationType(StrEnum):
    PAYOUT_SENT = "payout_sent"
    EARNINGS_SUMMARY = "earnings_summary"
    PAYOUT_FAILED = "payout_failed"


class ReviewNotificationType(StrEnum):
    REVIEW_RESPONSE = "review_response"


class PTONotificationType(StrEnum):
    PTO_BALANCE_REMINDER = "pto_balance_reminder"
    PTO_PLANNING_ENCOURAGEMENT = "pto_planning_encouragement"
    PTO_COVERAGE_MANAGEABLE = "pto_coverage_manageable"
    PTO_NO_GUILT = "pto_no_guilt"
    PTO_TIME_OFF_STRENGTH = "pto_time_off_strength"
    PTO_APPROVED_CELEBRATION = "pto_approved_celebration"
    PTO_WELCOME_BACK = "pto_welcome_back"
    PTO_VACATION_EXPIRY_WARNING = "pto_vacation_expiry_warning"


# =============================================================================
# Notification Channel
# =============================================================================


class NotificationChannel(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    IN_APP = "in_app"
    PUSH = "push"


# =============================================================================
# Shared Data Classes
# =============================================================================


@dataclass
class NotificationTemplate:
    subject: str
    body: str
    html_body: Optional[str] = None
    sms_body: Optional[str] = None

    def render(self, context: Dict) -> Tuple[str, str, Optional[str], Optional[str]]:
        try:
            subject = self.subject.format(**context)
            body = self.body.format(**context)
            html = self.html_body.format(**context) if self.html_body else None
            sms = self.sms_body.format(**context) if self.sms_body else None
            return subject, body, html, sms
        except KeyError as e:
            logger.warning(f"Missing template variable: {e}")
            return self.subject, self.body, self.html_body, self.sms_body


@dataclass
class NotificationContent:
    user_id: Optional[int] = None
    recipient_email: Optional[str] = None
    recipient_phone: Optional[str] = None
    subject: str = ""
    body: str = ""
    html_body: Optional[str] = None
    sms_body: Optional[str] = None
    context_data: Dict = None
    channels: List[str] = None
    scheduled_for: Optional[datetime] = None

    def __post_init__(self):
        if self.context_data is None:
            self.context_data = {}
        if self.channels is None:
            self.channels = ["email"]


@dataclass
class NotificationRecipient:
    user_id: int
    email: Optional[str]
    phone: Optional[str]
    name: str
    preferred_channel: NotificationChannel = NotificationChannel.EMAIL


@dataclass
class NotificationResult:
    success: bool
    channel: NotificationChannel
    recipient_id: int
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None


@dataclass
class NotificationConfig:
    email_enabled: bool = True
    sms_enabled: bool = False
    push_enabled: bool = False
    email_from: str = "library@example.com"
    email_from_name: str = "Library HomeDelivery Services"
    sms_provider: Optional[str] = None
    sms_from_number: Optional[str] = None
    reminder_days_before: int = 1
    feedback_delay_hours: int = 24
