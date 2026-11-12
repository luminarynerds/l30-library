# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import secrets
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    JSON,
    UniqueConstraint,
)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


# =============================================================================
# Enums
# =============================================================================


class NewsletterFrequency(StrEnum):
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    UNSUBSCRIBED = "unsubscribed"
    BOUNCED = "bounced"
    COMPLAINED = "complained"


class UnsubscribeReason(StrEnum):
    TOO_FREQUENT = "too_frequent"
    NOT_RELEVANT = "not_relevant"
    NEVER_SIGNED_UP = "never_signed_up"
    PRIVACY_CONCERNS = "privacy_concerns"
    OTHER = "other"
    ONE_CLICK = "one_click"  # CAN-SPAM one-click unsubscribe


class MarketingConsentSource(StrEnum):
    REGISTRATION = "registration"
    ACCOUNT_SETTINGS = "account_settings"
    NEWSLETTER_FORM = "newsletter_form"
    EVENT_REGISTRATION = "event_registration"
    STAFF_ASSISTED = "staff_assisted"
    IMPORTED = "imported"


class MailchimpSyncStatus(StrEnum):
    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


# =============================================================================
# Newsletter Subscription Model
# =============================================================================


class NewsletterSubscription(Base):
    __tablename__ = "newsletter_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Can be linked to patron account (optional for guest subscribers)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # Email is required (either from user or provided directly)
    email = Column(String(255), nullable=False, index=True)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)

    # Subscription status
    status = Column(
        SQLEnum(SubscriptionStatus, name="subscriptionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SubscriptionStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Frequency preference
    frequency = Column(
        SQLEnum(NewsletterFrequency, name="newsletterfrequency", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NewsletterFrequency.WEEKLY,
        nullable=False,
    )

    # Consent tracking (GDPR)
    consent_given = Column(Boolean, default=False, nullable=False)
    consent_date = Column(DateTime(timezone=True), nullable=True)
    consent_source = Column(
        SQLEnum(MarketingConsentSource, name="marketingconsentsource", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    consent_ip_address = Column(String(45), nullable=True)  # IPv6 compatible

    # Double opt-in (best practice)
    double_optin_token = Column(String(64), nullable=True, unique=True, index=True)
    double_optin_sent_at = Column(DateTime(timezone=True), nullable=True)
    double_optin_confirmed_at = Column(DateTime(timezone=True), nullable=True)

    # Unsubscribe management
    unsubscribe_token = Column(String(64), nullable=False, unique=True, index=True)
    unsubscribed_at = Column(DateTime(timezone=True), nullable=True)
    unsubscribe_reason = Column(
        SQLEnum(UnsubscribeReason, name="unsubscribereason", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    unsubscribe_feedback = Column(Text, nullable=True)

    # Mailchimp integration
    mailchimp_member_id = Column(String(100), nullable=True, index=True)
    mailchimp_sync_status = Column(
        SQLEnum(MailchimpSyncStatus, name="mailchimpsyncstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MailchimpSyncStatus.PENDING,
        nullable=False,
    )
    mailchimp_last_synced = Column(DateTime(timezone=True), nullable=True)
    mailchimp_error = Column(Text, nullable=True)

    # Tracking, server_default=func.now())

    # Relationships
    user = relationship("User")
    interests = relationship(
        "SubscriberInterest",
        back_populates="subscription",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("email", name="uq_newsletter_email"),
        Index("ix_newsletter_status_email", "status", "email"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.unsubscribe_token:
            self.unsubscribe_token = secrets.token_urlsafe(32)

    @property
    def is_active(self) -> bool:
        return self.status == SubscriptionStatus.ACTIVE

    @property
    def is_confirmed(self) -> bool:
        return self.double_optin_confirmed_at is not None


# =============================================================================
# Interest Categories for Mailing Lists
# =============================================================================


class InterestCategory(Base):
    __tablename__ = "interest_categories"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(100), nullable=False, unique=True)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Visual
    icon = Column(String(50), nullable=True)  # Icon name for UI
    color = Column(String(7), nullable=True)  # Hex color

    # Categorization
    parent_id = Column(
        Integer,
        ForeignKey("interest_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Mapping to catalog
    dewey_range_start = Column(String(10), nullable=True)
    dewey_range_end = Column(String(10), nullable=True)
    bisac_codes = Column(JSON, nullable=True)  # List of BISAC codes

    # Mailchimp integration
    mailchimp_interest_id = Column(String(100), nullable=True)

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    display_order = Column(Integer, default=0, nullable=False)

    # Relationships
    parent = relationship("InterestCategory", remote_side=[id])
    subscribers = relationship("SubscriberInterest", back_populates="category")


class SubscriberInterest(Base):
    __tablename__ = "subscriber_interests"

    id = Column(Integer, primary_key=True, index=True)

    subscription_id = Column(
        Integer,
        ForeignKey("newsletter_subscriptions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category_id = Column(
        Integer,
        ForeignKey("interest_categories.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # When they subscribed to this interest
    subscribed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    subscription = relationship("NewsletterSubscription", back_populates="interests")
    category = relationship("InterestCategory", back_populates="subscribers")

    __table_args__ = (
        UniqueConstraint("subscription_id", "category_id", name="uq_subscriber_interest"),
    )


# =============================================================================
# New Arrival Alerts
# =============================================================================


class NewArrivalAlert(Base):
    __tablename__ = "new_arrival_alerts"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What to alert on
    category_id = Column(
        Integer,
        ForeignKey("interest_categories.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # OR specific search criteria
    search_query = Column(String(500), nullable=True)
    author_name = Column(String(255), nullable=True)
    series_name = Column(String(255), nullable=True)

    # Delivery preferences
    delivery_method = Column(String(20), default="email", nullable=False)  # email, sms, both
    frequency = Column(
        SQLEnum(NewsletterFrequency, name="newsletterfrequency", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=NewsletterFrequency.WEEKLY,
        nullable=False,
    )

    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Tracking
    last_alert_sent = Column(DateTime(timezone=True), nullable=True)
    items_alerted_ids = Column(JSON, nullable=True)  # Track which items already alerted

    # Unsubscribe token for this specific alert
    unsubscribe_token = Column(String(64), nullable=False, unique=True, index=True)

    # Relationships
    user = relationship("User")
    category = relationship("InterestCategory")

    __table_args__ = (
        Index("ix_arrival_alerts_user_active", "user_id", "is_active"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.unsubscribe_token:
            self.unsubscribe_token = secrets.token_urlsafe(32)


# =============================================================================
# Email Unsubscribe Token (Universal)
# =============================================================================


class EmailUnsubscribeToken(Base):
    __tablename__ = "email_unsubscribe_tokens"

    id = Column(Integer, primary_key=True, index=True)

    # Token for URL
    token = Column(String(64), nullable=False, unique=True, index=True)

    # Who this is for
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    email = Column(String(255), nullable=False, index=True)

    # What type of email this token was generated for
    email_type = Column(String(50), nullable=False)  # newsletter, alert, notification
    email_category = Column(String(100), nullable=True)  # Specific category if applicable

    # Tracking, server_default=func.now())
    used_at = Column(DateTime(timezone=True), nullable=True)

    # Expiry (optional - tokens can be long-lived for CAN-SPAM)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.token:
            self.token = secrets.token_urlsafe(32)

    @property
    def is_valid(self) -> bool:
        if self.used_at:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


# =============================================================================
# Marketing Campaign Tracking
# =============================================================================


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(200), nullable=False)
    slug = Column(String(200), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)

    # Campaign type
    campaign_type = Column(String(50), nullable=False)  # newsletter, new_arrivals, event, custom

    # Targeting
    target_interests = Column(JSON, nullable=True)  # List of interest category IDs
    target_all_subscribers = Column(Boolean, default=False, nullable=False)

    # Content
    subject = Column(String(200), nullable=True)
    preview_text = Column(String(200), nullable=True)
    html_content = Column(Text, nullable=True)

    # Scheduling
    scheduled_for = Column(DateTime(timezone=True), nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    # Status
    status = Column(String(20), default="draft", nullable=False)  # draft, scheduled, sending, sent, cancelled

    # Mailchimp integration
    mailchimp_campaign_id = Column(String(100), nullable=True)

    # Statistics
    recipients_count = Column(Integer, default=0)
    opens_count = Column(Integer, default=0)
    clicks_count = Column(Integer, default=0)
    unsubscribes_count = Column(Integer, default=0)
    bounces_count = Column(Integer, default=0)

    # Audit
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    created_by = relationship("User")


class CampaignRecipient(Base):
    __tablename__ = "campaign_recipients"

    id = Column(Integer, primary_key=True, index=True)

    campaign_id = Column(
        Integer,
        ForeignKey("marketing_campaigns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    subscription_id = Column(
        Integer,
        ForeignKey("newsletter_subscriptions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    email = Column(String(255), nullable=False)

    # Status
    status = Column(String(20), default="pending", nullable=False)  # pending, sent, delivered, opened, clicked, bounced, unsubscribed

    # Tracking
    sent_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=True)
    clicked_at = Column(DateTime(timezone=True), nullable=True)

    # Unsubscribe token for this specific send
    unsubscribe_token = Column(String(64), nullable=False, index=True)

    __table_args__ = (
        UniqueConstraint("campaign_id", "email", name="uq_campaign_recipient"),
        Index("ix_campaign_recipients_status", "campaign_id", "status"),
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self.unsubscribe_token:
            self.unsubscribe_token = secrets.token_urlsafe(32)
