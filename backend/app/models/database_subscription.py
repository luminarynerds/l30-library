# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum as PyEnum

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ProxyType(PyEnum):
    EZPROXY = "ezproxy"
    OPENATHENS = "openathens"
    DIRECT = "direct"  # No proxy needed (IP-authenticated or open access)
    REFERRER = "referrer"  # Referrer URL authentication
    SHIBBOLETH = "shibboleth"


class SubscriptionStatus(PyEnum):
    ACTIVE = "active"
    EXPIRING_SOON = "expiring_soon"  # Within renewal window
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"  # Not yet started
    TRIAL = "trial"


class DatabaseCategory(PyEnum):
    GENERAL_REFERENCE = "general_reference"
    ACADEMIC = "academic"
    NEWSPAPERS = "newspapers"
    MAGAZINES = "magazines"
    EBOOKS = "ebooks"
    AUDIOBOOKS = "audiobooks"
    GENEALOGY = "genealogy"
    BUSINESS = "business"
    LEGAL = "legal"
    HEALTH = "health"
    CHILDREN = "children"
    TEEN = "teen"
    LANGUAGE_LEARNING = "language_learning"
    TEST_PREP = "test_prep"
    STREAMING_VIDEO = "streaming_video"
    STREAMING_MUSIC = "streaming_music"
    DIY_CRAFTS = "diy_crafts"
    AUTOMOTIVE = "automotive"
    OTHER = "other"


class ProxyConfiguration(Base):
    __tablename__ = "proxy_configurations"

    id = Column(Integer, primary_key=True, index=True)

    # Configuration name (e.g., "Primary EZproxy", "OpenAthens Production")
    name = Column(String(100), nullable=False)

    # Proxy type
    proxy_type = Column(String(20), nullable=False, default=ProxyType.EZPROXY.value)

    # EZproxy settings
    ezproxy_base_url = Column(String(500))  # e.g., "https://proxy.library.org"
    ezproxy_login_path = Column(String(100), default="/login")
    ezproxy_url_param = Column(String(50), default="url")  # ?url= or ?qurl=

    # OpenAthens settings
    openathens_org_id = Column(String(100))
    openathens_entity_id = Column(String(500))
    openathens_wayfless_url = Column(String(500))

    # Shibboleth settings
    shibboleth_entity_id = Column(String(500))
    shibboleth_discovery_url = Column(String(500))

    # IP ranges for on-site detection (JSONB array of CIDR ranges)
    # e.g., ["192.168.1.0/24", "10.0.0.0/8"]
    onsite_ip_ranges = Column(JSONB, default=[])

    # Authentication settings
    requires_library_card = Column(Boolean, default=True)
    allows_guest_access = Column(Boolean, default=False)

    # Active flag
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)

    # Metadata
    notes = Column(Text)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    created_by = relationship("User", foreign_keys=[created_by_id])
    databases = relationship("DatabaseSubscription", back_populates="proxy_config")

    def generate_proxy_url(self, target_url: str) -> str:
        if self.proxy_type == ProxyType.DIRECT.value:
            return target_url

        if self.proxy_type == ProxyType.EZPROXY.value:
            if self.ezproxy_base_url:
                # Standard EZproxy URL format
                return f"{self.ezproxy_base_url}{self.ezproxy_login_path}?{self.ezproxy_url_param}={target_url}"

        if self.proxy_type == ProxyType.OPENATHENS.value:
            if self.openathens_wayfless_url:
                return f"{self.openathens_wayfless_url}?TARGET={target_url}"

        # Fallback to direct URL
        return target_url


class DatabaseVendor(Base):
    __tablename__ = "database_vendors"

    id = Column(Integer, primary_key=True, index=True)

    # Vendor identification
    name = Column(String(200), nullable=False, unique=True)
    short_name = Column(String(50))  # e.g., "EBSCO", "ProQuest"

    # Contact information
    website = Column(String(500))
    support_url = Column(String(500))
    support_email = Column(String(255))
    support_phone = Column(String(50))

    # Account information
    account_number = Column(String(100))
    account_rep_name = Column(String(200))
    account_rep_email = Column(String(255))
    account_rep_phone = Column(String(50))

    # Admin portal
    admin_portal_url = Column(String(500))
    admin_username = Column(String(100))  # Store encrypted in production

    # Notes
    notes = Column(Text)

    # Metadata, server_default=func.now())

    # Relationships
    subscriptions = relationship("DatabaseSubscription", back_populates="vendor")
    sushi_credentials = relationship(
        "SUSHICredential", back_populates="vendor", cascade="all, delete-orphan"
    )


class SUSHICredential(Base):
    __tablename__ = "sushi_credentials"

    id = Column(Integer, primary_key=True, index=True)

    vendor_id = Column(
        Integer,
        ForeignKey("database_vendors.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Human label for staff (e.g., "EBSCO COUNTER R5", "ProQuest Platform A")
    label = Column(String(150), nullable=False)

    # SUSHI server endpoint (root of the COUNTER_SUSHI_API_5 service)
    base_url = Column(String(1000), nullable=False)

    # SUSHI auth parameters (COUNTER R5 spec)
    customer_id = Column(String(200), nullable=False)
    requestor_id = Column(String(200))
    platform = Column(String(200))  # Optional, required by some multi-platform vendors

    # Encrypted at rest via app.core.encryption.encrypt_token
    api_key = Column(Text)

    # Operational state
    is_active = Column(Boolean, default=True, nullable=False)
    last_harvest_at = Column(DateTime(timezone=True))
    last_harvest_status = Column(String(50))  # "success", "partial", "error", "pending"
    last_harvest_error = Column(Text)

    # Notes for staff
    notes = Column(Text)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    vendor = relationship("DatabaseVendor", back_populates="sushi_credentials")

    __table_args__ = (
        UniqueConstraint("vendor_id", "label", name="uq_sushi_credentials_vendor_label"),
        Index("ix_sushi_credentials_active", "is_active"),
    )


class DatabaseSubscription(Base):
    __tablename__ = "database_subscriptions"

    id = Column(Integer, primary_key=True, index=True)

    # Basic information
    name = Column(String(300), nullable=False)
    short_name = Column(String(100))  # For A-Z list display
    description = Column(Text)

    # Categorization
    category = Column(String(50), default=DatabaseCategory.GENERAL_REFERENCE.value)
    subjects = Column(JSONB, default=[])  # ["Science", "Technology"]
    keywords = Column(JSONB, default=[])  # For search

    # Vendor relationship
    vendor_id = Column(Integer, ForeignKey("database_vendors.id", ondelete="SET NULL"))

    # Access URLs
    access_url = Column(String(1000), nullable=False)  # Primary access URL
    mobile_url = Column(String(1000))  # Mobile-optimized URL if different
    admin_url = Column(String(1000))  # Admin/stats portal
    help_url = Column(String(1000))  # User help/guide

    # Proxy configuration
    proxy_config_id = Column(Integer, ForeignKey("proxy_configurations.id", ondelete="SET NULL"))
    proxy_type = Column(String(20), default=ProxyType.EZPROXY.value)
    custom_proxy_url = Column(String(1000))  # Override proxy URL for this database
    requires_proxy = Column(Boolean, default=True)

    # Authentication details
    auth_method = Column(String(50))  # "barcode", "username", "ip", "referrer"
    auth_notes = Column(Text)  # Special authentication instructions

    # Subscription dates
    subscription_start = Column(Date, nullable=False)
    subscription_end = Column(Date, nullable=False)
    trial_end = Column(Date)  # If on trial

    # Status tracking
    status = Column(String(20), default=SubscriptionStatus.ACTIVE.value, index=True)
    auto_renew = Column(Boolean, default=False)

    # Renewal management
    renewal_reminder_days = Column(Integer, default=60)
    last_renewal_reminder = Column(DateTime(timezone=True))
    renewal_contact_email = Column(String(255))  # Override vendor contact
    renewal_notes = Column(Text)

    # Cost tracking
    annual_cost = Column(Numeric(12, 2))
    cost_per_use = Column(Numeric(10, 4))  # For pay-per-use models
    payment_frequency = Column(String(20), default="annual")  # annual, monthly, multi-year

    # Contract details
    contract_number = Column(String(100))
    purchase_order = Column(String(100))
    invoice_number = Column(String(100))

    # Access restrictions
    simultaneous_users = Column(Integer)  # NULL = unlimited
    session_ttl_minutes = Column(Integer)  # NULL = use system default (30 min)
    patron_types_allowed = Column(JSONB, default=[])  # Empty = all types
    branch_restrictions = Column(JSONB, default=[])  # Empty = all branches

    # Display settings
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_featured = Column(Boolean, default=False, index=True)
    display_order = Column(Integer, default=0)
    logo_url = Column(String(500))

    # Usage tracking
    usage_stats_url = Column(String(500))  # COUNTER stats portal
    last_usage_sync = Column(DateTime(timezone=True))

    # Metadata
    notes = Column(Text)
    internal_notes = Column(Text)  # Staff-only notes, server_default=func.now())
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    vendor = relationship("DatabaseVendor", back_populates="subscriptions")
    proxy_config = relationship("ProxyConfiguration", back_populates="databases")
    created_by = relationship("User", foreign_keys=[created_by_id])
    usage_stats = relationship("DatabaseUsageStats", back_populates="subscription", cascade="all, delete-orphan")
    access_logs = relationship("DatabaseAccessLog", back_populates="subscription", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_database_subscriptions_dates", "subscription_start", "subscription_end"),
        Index("ix_database_subscriptions_category", "category", "is_active"),
        Index("ix_database_subscriptions_status_end", "status", "subscription_end"),
    )

    @property
    def is_expired(self) -> bool:
        return self.subscription_end < date.today()

    @property
    def is_expiring_soon(self) -> bool:
        if self.is_expired:
            return False
        if self.renewal_reminder_days is None:
            return False
        days_until_expiry = (self.subscription_end - date.today()).days
        return days_until_expiry <= self.renewal_reminder_days

    @property
    def days_until_expiry(self) -> int:
        return (self.subscription_end - date.today()).days

    def get_proxy_url(self) -> str:
        if self.custom_proxy_url:
            return self.custom_proxy_url

        if not self.requires_proxy:
            return self.access_url

        if self.proxy_config:
            return self.proxy_config.generate_proxy_url(self.access_url)

        return self.access_url


class DatabaseUsageStats(Base):
    __tablename__ = "database_usage_stats"

    id = Column(Integer, primary_key=True, index=True)

    subscription_id = Column(
        Integer,
        ForeignKey("database_subscriptions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Time period
    stat_year = Column(Integer, nullable=False)
    stat_month = Column(Integer, nullable=False)  # 1-12

    # COUNTER metrics (R5 compliant)
    total_item_requests = Column(Integer, default=0)  # Total content requests
    unique_item_requests = Column(Integer, default=0)  # Unique content items
    total_item_investigations = Column(Integer, default=0)  # Views/investigations
    unique_item_investigations = Column(Integer, default=0)

    # Search metrics
    searches_regular = Column(Integer, default=0)
    searches_federated = Column(Integer, default=0)
    searches_automated = Column(Integer, default=0)

    # Session metrics
    total_sessions = Column(Integer, default=0)
    unique_users = Column(Integer, default=0)

    # Turnaways (access denied)
    no_license = Column(Integer, default=0)  # Denied due to license limit

    # Access location
    onsite_sessions = Column(Integer, default=0)
    offsite_sessions = Column(Integer, default=0)

    # Source of data
    data_source = Column(String(50))  # "counter_sushi", "manual", "vendor_report"
    imported_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    subscription = relationship("DatabaseSubscription", back_populates="usage_stats")

    __table_args__ = (
        UniqueConstraint("subscription_id", "stat_year", "stat_month", name="uq_database_usage_period"),
        Index("ix_database_usage_stats_period", "stat_year", "stat_month"),
    )

    @property
    def cost_per_use(self) -> Decimal | None:
        if self.subscription and self.subscription.annual_cost and self.total_item_requests:
            monthly_cost = self.subscription.annual_cost / 12
            return monthly_cost / Decimal(self.total_item_requests)
        return None


class DatabaseAccessLog(Base):
    __tablename__ = "database_access_logs"

    id = Column(Integer, primary_key=True, index=True)

    subscription_id = Column(
        Integer,
        ForeignKey("database_subscriptions.id", ondelete="CASCADE"),
        nullable=False
    )

    # When
    accessed_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Who (anonymized)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    patron_type = Column(String(50))  # "adult", "teen", "child", "staff"
    user_role = Column(String(50))  # UserRole value

    # Where
    is_onsite = Column(Boolean, default=False)
    ip_hash = Column(String(64))  # Hashed IP for privacy
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100))  # deprecated; use branch_id

    # How
    access_method = Column(String(50))  # "web", "mobile_app", "discovery", "a-z_list"
    referrer_type = Column(String(50))  # "catalog", "website", "direct", "federated"

    # Outcome
    success = Column(Boolean, default=True)
    error_type = Column(String(50))  # "auth_failed", "license_limit", "expired"

    # Relationships
    subscription = relationship("DatabaseSubscription", back_populates="access_logs")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_database_access_logs_time", "accessed_at"),
        Index("ix_database_access_logs_subscription", "subscription_id", "accessed_at"),
    )


class DatabaseRenewalNotification(Base):
    __tablename__ = "database_renewal_notifications"

    id = Column(Integer, primary_key=True, index=True)

    subscription_id = Column(
        Integer,
        ForeignKey("database_subscriptions.id", ondelete="CASCADE"),
        nullable=False
    )

    # Notification details
    sent_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    notification_type = Column(String(50), nullable=False)  # "60_day", "30_day", "7_day", "expired"
    sent_to = Column(String(255), nullable=False)  # Email address

    # Status
    delivered = Column(Boolean, default=True)
    error_message = Column(Text)

    # Response tracking
    responded_at = Column(DateTime(timezone=True))
    response_action = Column(String(50))  # "renewed", "cancelled", "negotiating"

    # Relationships
    subscription = relationship("DatabaseSubscription")

    __table_args__ = (
        Index("ix_renewal_notifications_subscription", "subscription_id", "sent_at"),
    )
