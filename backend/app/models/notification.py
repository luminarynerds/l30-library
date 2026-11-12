# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, Index, Integer, String, Text, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class NotificationType(StrEnum):

    # Circulation notifications
    CHECKOUT_RECEIPT = "checkout_receipt"
    DUE_DATE_REMINDER = "due_date_reminder"
    OVERDUE_NOTICE = "overdue_notice"
    HOLD_READY = "hold_ready"
    HOLD_EXPIRING = "hold_expiring"
    HOLD_CANCELLED = "hold_cancelled"
    FINE_NOTICE = "fine_notice"
    ACCOUNT_LOCKED = "account_locked"

    # Account lifecycle notifications
    ACCOUNT_TRANSITIONED = "account_transitioned"  # Child to adult account transition

    # Event notifications
    EVENT_REMINDER = "event_reminder"
    EVENT_CANCELLED = "event_cancelled"
    EVENT_UPDATED = "event_updated"
    EVENT_REGISTRATION_CANCELLED = "event_registration_cancelled"

    # Training/Learning notifications
    TRAINING_NEW_COURSE = "training_new_course"
    TRAINING_COURSE_COMPLETED = "training_course_completed"
    TRAINING_MILESTONE_REACHED = "training_milestone_reached"
    TRAINING_CERTIFICATE_EARNED = "training_certificate_earned"
    TRAINING_STREAK_REMINDER = "training_streak_reminder"
    TRAINING_NEW_CONTENT = "training_new_content"
    TRAINING_SKILL_ASSESSMENT_DUE = "training_skill_assessment_due"
    TRAINING_WEEKLY_DIGEST = "training_weekly_digest"

    # Board governance notifications
    BOARD_MEETING_SCHEDULED = "board_meeting_scheduled"
    BOARD_AGENDA_PUBLISHED = "board_agenda_published"

    # Emergency/Safety notifications
    PANIC_ALERT = "panic_alert"

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

    # Reading programs (added in rp_notification_types_001)
    READING_PROGRAM_PROGRESS_NUDGE = "reading_program_progress_nudge"
    READING_PROGRAM_STREAK_ALERT = "reading_program_streak_alert"
    READING_PROGRAM_PRIZE_UNLOCKED = "reading_program_prize_unlocked"

    # Staff operational alerts
    STAFF_DAILY_ALERT = "staff_daily_alert"
    STAFF_HELP_REQUESTED = "staff_help_requested"

    # Shift swap notifications (shared with shift_swap module)
    NEW_MATCH = "new_match"
    MATCH_ACCEPTED = "match_accepted"
    MATCH_REJECTED = "match_rejected"
    SWAP_CLAIMED = "swap_claimed"
    SWAP_EXPIRING = "swap_expiring"
    CLAIM_APPROVED = "claim_approved"
    CLAIM_REJECTED = "claim_rejected"


class NotificationStatus(StrEnum):

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PatronNotificationCategory(StrEnum):

    # Hold-related
    HOLD_AVAILABLE = "hold_available"
    HOLD_EXPIRING = "hold_expiring"
    HOLD_CANCELLED = "hold_cancelled"

    # Checkout/Due date
    CHECKOUT_RECEIPT = "checkout_receipt"
    DUE_DATE_REMINDER = "due_date_reminder"
    OVERDUE_NOTICE = "overdue_notice"

    # Fines
    FINE_ASSESSED = "fine_assessed"
    FINE_PAID = "fine_paid"

    # Account
    ACCOUNT_BLOCKED = "account_blocked"
    ACCOUNT_UNBLOCKED = "account_unblocked"

    # Reference chat
    REFERENCE_CHAT_REPLY = "reference_chat_reply"

    # Catalog saved-search new-arrival alerts (PR #611 backend + this PR notifier)
    CATALOG_SAVED_SEARCH_MATCH = "catalog_saved_search_match"


class Notification(Base):

    __tablename__ = "notifications"
    __table_args__ = (
        Index("ix_notifications_user_status_created", "user_id", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    notification_type = Column(
        SQLEnum(NotificationType, name="notificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    status = Column(
        SQLEnum(NotificationStatus, name="notificationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Notification content
    subject = Column(String(500), nullable=True)
    message = Column(Text, nullable=True)

    # Context data
    context_data = Column(JSON, nullable=True)

    # Tracking
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    user = relationship("User")


class PatronNotification(Base):

    __tablename__ = "patron_notifications"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    category = Column(
        SQLEnum(PatronNotificationCategory, name="patronnotificationcategory", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )

    # Notification content
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)

    # Source tracking for idempotency
    source_event_type = Column(String(100), nullable=False)  # E.g., "HoldReady", "LoanBecameOverdue"
    source_event_id = Column(String(255), nullable=False, unique=True, index=True)  # Unique constraint for idempotency

    # Related resource IDs (optional - for linking back to source entities)
    related_hold_id = Column(String(255), nullable=True)
    related_loan_id = Column(String(255), nullable=True)
    related_fine_id = Column(String(255), nullable=True)
    related_item_title = Column(String(500), nullable=True)

    # Action/CTA
    action_url = Column(String(500), nullable=True)
    action_label = Column(String(100), nullable=True)

    # Read status
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)

    # Dismissed/soft-delete status
    is_dismissed = Column(Boolean, default=False, nullable=False, index=True)
    dismissed_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id])


class NotificationPreferences(Base):

    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    # Email notification preferences (default all enabled)
    email_checkout_receipt = Column(Boolean, default=True, nullable=False)
    email_due_date_reminder = Column(Boolean, default=True, nullable=False)
    email_overdue_notice = Column(Boolean, default=True, nullable=False)
    email_hold_ready = Column(Boolean, default=True, nullable=False)
    email_hold_expiring = Column(Boolean, default=True, nullable=False)
    email_hold_cancelled = Column(Boolean, default=False, nullable=False)
    email_fine_notice = Column(Boolean, default=True, nullable=False)

    # Reminder timing (days before due date)
    due_date_reminder_days = Column(Integer, default=2, nullable=False)
    hold_expiring_reminder_days = Column(Integer, default=2, nullable=False)

    # Overdue notice escalation (send notices at these day intervals)
    overdue_notice_intervals = Column(
        JSON, default=[1, 7, 14], nullable=False
    )  # Days after due date

    # Training/Learning notification preferences
    email_training_new_course = Column(Boolean, default=True, nullable=False)
    email_training_course_completed = Column(Boolean, default=True, nullable=False)
    email_training_milestone = Column(Boolean, default=True, nullable=False)
    email_training_certificate = Column(Boolean, default=True, nullable=False)
    email_training_streak_reminder = Column(Boolean, default=False, nullable=False)
    email_training_new_content = Column(Boolean, default=True, nullable=False)
    email_training_skill_assessment = Column(Boolean, default=True, nullable=False)
    email_training_weekly_digest = Column(Boolean, default=False, nullable=False)

    # Training notification timing
    streak_reminder_days = Column(Integer, default=3, nullable=False)  # Days before losing streak

    # SMS notification preferences
    sms_notifications_enabled = Column(Boolean, default=False, nullable=False)
    sms_phone_number = Column(String(20), nullable=True)  # E.164 format
    sms_phone_verified = Column(Boolean, default=False, nullable=False)
    sms_phone_verified_at = Column(DateTime(timezone=True), nullable=True)

    # SMS notification types (default all disabled until opted in)
    sms_checkout_receipt = Column(Boolean, default=False, nullable=False)
    sms_due_date_reminder = Column(Boolean, default=True, nullable=False)
    sms_overdue_notice = Column(Boolean, default=True, nullable=False)
    sms_hold_ready = Column(Boolean, default=True, nullable=False)
    sms_hold_expiring = Column(Boolean, default=False, nullable=False)
    sms_hold_cancelled = Column(Boolean, default=False, nullable=False)
    sms_fine_notice = Column(Boolean, default=False, nullable=False)
    sms_event_reminder = Column(Boolean, default=True, nullable=False)

    # SMS timing preferences
    sms_due_date_reminder_days = Column(Integer, default=1, nullable=False)  # Days before due
    sms_event_reminder_hours = Column(Integer, default=24, nullable=False)   # Hours before event

    # Review response notification preferences
    email_review_response = Column(Boolean, default=True, nullable=False)

    # Board governance notification preferences
    email_board_meeting_scheduled = Column(Boolean, default=True, nullable=False)
    email_board_agenda_published = Column(Boolean, default=True, nullable=False)
    email_board_vote_reminder = Column(Boolean, default=True, nullable=False)
    email_board_motion_updates = Column(Boolean, default=True, nullable=False)
    email_board_resolution_adopted = Column(Boolean, default=True, nullable=False)
    email_board_action_item_due = Column(Boolean, default=True, nullable=False)
    email_board_action_item_assigned = Column(Boolean, default=True, nullable=False)
    email_board_document_published = Column(Boolean, default=True, nullable=False)
    email_board_public_comment_received = Column(Boolean, default=False, nullable=False)  # Admin only
    email_board_comment_period_alerts = Column(Boolean, default=True, nullable=False)
    email_board_committee_appointment = Column(Boolean, default=True, nullable=False)
    email_board_committee_meeting = Column(Boolean, default=True, nullable=False)

    # Board notification timing
    board_meeting_reminder_days = Column(Integer, default=7, nullable=False)  # Days before meeting
    board_vote_reminder_hours = Column(Integer, default=24, nullable=False)  # Hours before vote deadline
    board_action_item_reminder_days = Column(Integer, default=3, nullable=False)  # Days before due

    # Staff daily alert preferences (for morning dashboard notifications)
    email_staff_daily_alert = Column(Boolean, default=True, nullable=False)
    staff_daily_alert_time = Column(String(5), default="07:00", nullable=False)  # HH:MM format, default 7 AM
    staff_daily_alert_days = Column(JSON, default=["monday", "tuesday", "wednesday", "thursday", "friday"], nullable=False)  # Days of week to send

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")


class NotificationQueue(Base):

    __tablename__ = "notification_queue"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    notification_type = Column(
        SQLEnum(NotificationType, name="notificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        index=True,
    )

    status = Column(
        SQLEnum(NotificationStatus, name="notificationstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NotificationStatus.PENDING,
        nullable=False,
        index=True,
    )

    # Email details
    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    html_body = Column(Text, nullable=False)

    # Context data (JSON for flexibility)
    context_data = Column(JSON, nullable=True)

    # Tracking
    scheduled_for = Column(
        DateTime(timezone=True), nullable=False, index=True
    )  # When to send
    sent_at = Column(DateTime(timezone=True), nullable=True)
    failed_at = Column(DateTime(timezone=True), nullable=True)
    failure_reason = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)

    # Relationships
    user = relationship("User")


class NotificationHistory(Base):

    __tablename__ = "notification_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    notification_type = Column(
        SQLEnum(NotificationType, name="notificationtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        index=True,
    )

    recipient_email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    context_data = Column(JSON, nullable=True)

    sent_at = Column(DateTime(timezone=True), nullable=False, index=True)
    success = Column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User")


class NotificationDigestQueue(Base):

    __tablename__ = "notification_digest_queue"
    __table_args__ = (
        # Idempotency: the nightly sweep can run more than once a day on
        # retry. dedup_key carries the source entity id (checkout/hold) so a
        # re-run does not list the same item twice in one digest.
        UniqueConstraint(
            "user_id",
            "notification_type",
            "dedup_key",
            name="uq_notification_digest_queue_dedup",
        ),
        Index("ix_notification_digest_queue_user", "user_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Stored as a plain string (not the SQLEnum) because the preference gate
    # works in notification-type strings, and digest-eligible types are a
    # patron-facing subset that need not be schema-coupled to NotificationType.
    notification_type = Column(String(64), nullable=False)

    # Short human-readable line shown in the digest email (e.g.
    # "3 items due in 3 days"). Not full HTML -- the digest job renders the
    # summary email itself.
    summary = Column(String(500), nullable=False)
    context_data = Column(JSON, nullable=True)

    # Per-patron-per-type dedup token. Empty string when the caller has no
    # natural key (the unique constraint still collapses repeat enqueues of
    # the same type for the same patron before a digest is sent).
    dedup_key = Column(String(128), nullable=False, default="")

    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    user = relationship("User")


class TrainingAnnouncementType(StrEnum):

    NEW_COURSE = "new_course"
    NEW_FEATURE = "new_feature"
    CONTENT_UPDATE = "content_update"
    TIP = "tip"
    ANNOUNCEMENT = "announcement"


class TrainingAnnouncement(Base):

    __tablename__ = "training_announcements"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    announcement_type = Column(
        String(50),
        default="announcement",
        index=True,
    )

    # Optional link to related content
    link_url = Column(String(500), nullable=True)
    link_text = Column(String(100), nullable=True)

    # Related course if this is a course announcement
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Targeting
    target_audience = Column(String(20), default="all", nullable=False)  # all, patron, staff, admin

    # Visibility
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    start_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Priority for ordering (higher = more important)
    priority = Column(Integer, default=0, nullable=False)


class TrainingAnnouncementDismissal(Base):

    __tablename__ = "training_announcement_dismissals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    announcement_id = Column(
        Integer, ForeignKey("training_announcements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    dismissed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User")
    announcement = relationship("TrainingAnnouncement")
