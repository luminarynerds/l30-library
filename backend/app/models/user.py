# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import re
from enum import StrEnum

from app.models.mixins import TimestampMixin
from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, Index, JSON
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text, event
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from ..core.encryption import EncryptedPIIField, EncryptedString, EncryptedDate


# COPPA age threshold - users under this age require parental consent
COPPA_AGE_THRESHOLD = 13

# Teen threshold - users between COPPA_AGE_THRESHOLD and this age have
# developing privacy interests (ALA guidance). Full parental visibility
# ends at 13; title-level detail is redacted from household views.
TEEN_AGE_THRESHOLD = 18


class UserRole(StrEnum):
    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    DIRECTOR = "director"  # Library Director - access to sensitive operations
    LEGAL = "legal"  # Legal counsel - access to law enforcement requests
    LIBRARY_ADMIN = (
        "library_admin"  # Library-scoped admin (e.g., connection groups, childcare session mgmt)
    )
    STAFF = "staff"
    PATRON = "patron"
    TEACHER = "teacher"
    CHILD = "child"
    BOOKMOBILE = "bookmobile"
    HOMEBOND = "homebond"


class NoticePreference(StrEnum):
    EMAIL = "email"
    SMS = "sms"
    PRINT = "print"
    NONE = "none"


class AddressStatus(StrEnum):
    VALID = "valid"
    UNVERIFIED = "unverified"
    RETURNED_MAIL = "returned_mail"
    INVALID = "invalid"


class PatronStatus(StrEnum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    BLOCKED = "blocked"
    DECEASED = "deceased"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Encrypted at rest. Uniqueness + lookup move to email_hash (a blind index
    # over the normalized lowercased email); a unique index on ciphertext would
    # be meaningless.
    email = Column(EncryptedString(500), nullable=False)
    email_hash = Column(String(64), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=True)

    first_name = Column(EncryptedString(500), nullable=False)
    last_name = Column(EncryptedString(500), nullable=False)
    # Blind indexes for exact / prefix name lookup. first_name_hash and
    # last_name_hash are HMACs of the normalized full value; last_name_prefix_hash
    # holds HMACs of each 1..N-char lowercased prefix of the last name so staff
    # last-name PREFIX search ("joh" -> "Johnson") works without exposing
    # plaintext. Substring-anywhere matching is intentionally dropped.
    first_name_hash = Column(String(64), nullable=True, index=True)
    last_name_hash = Column(String(64), nullable=True, index=True)
    last_name_prefix_hash = Column(JSONB, nullable=True)

    role = Column(
        SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]),
        default=UserRole.PATRON,
        nullable=False,
        index=True,
    )
    staff_role = Column(
        String(50), nullable=True
    )  # 'front_desk', 'cataloger', 'youth_services', 'manager'
    # Holds an ALA-accredited MLS/MLIS — drives PLS MLS-librarian FTE split.
    has_mls = Column(Boolean, default=False, nullable=False, server_default="false")
    dashboard_functions = Column(JSON, nullable=True)  # e.g. ["front_desk", "board_ops"]
    dashboard_tone = Column(
        String(20), nullable=False, server_default="standard"
    )  # calm, standard, full
    is_active = Column(Boolean, default=True, nullable=False, index=True)

    # Patron status for lifecycle management (keeps is_active for backwards compatibility)
    patron_status = Column(
        SQLEnum(
            PatronStatus,
            name="patronstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=PatronStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Suspension tracking (for temporary automatic suspensions)
    suspension_reason = Column(String(500), nullable=True)  # Why the patron was suspended
    suspended_until = Column(DateTime(timezone=True), nullable=True)  # Auto-lift date
    suspended_at = Column(DateTime(timezone=True), nullable=True)  # When suspension started
    suspended_by_id = Column(Integer, nullable=True)  # Staff ID who suspended (null for auto)

    # Block tracking (for administrative blocks)
    block_reason = Column(String(500), nullable=True)  # Why the patron was blocked
    blocked_at = Column(DateTime(timezone=True), nullable=True)  # When block was applied
    blocked_by_id = Column(Integer, nullable=True)  # Staff ID who blocked

    # Deceased patron handling
    date_of_death = Column(Date, nullable=True)
    deceased_marked_at = Column(DateTime(timezone=True), nullable=True)
    deceased_marked_by_id = Column(Integer, nullable=True)  # Staff ID who marked deceased

    # Estate contact information for deceased patrons
    estate_contact_name = Column(String(200), nullable=True)
    estate_contact_email = Column(String(255), nullable=True)
    _estate_contact_phone = Column("estate_contact_phone", String(500), nullable=True)
    estate_contact_phone = EncryptedPIIField("_estate_contact_phone")

    # Flag for estate follow-up on outstanding items/fines
    estate_followup_required = Column(Boolean, default=False, nullable=False)
    estate_followup_notes = Column(Text, nullable=True)

    # Library card for patrons
    library_card = Column(String(50), unique=True, index=True, nullable=True)

    # Card type and trial tracking
    card_type = Column(String(20), default="full", nullable=False)  # "temporary" or "full"
    card_trial_expires_at = Column(DateTime(timezone=True), nullable=True)
    card_upgraded_at = Column(DateTime(timezone=True), nullable=True)
    card_upgraded_by_id = Column(Integer, nullable=True)

    # Patron contact info
    _phone = Column("phone", String(500), nullable=True)
    phone_hash = Column(String(64), nullable=True, index=True)
    phone_last4 = Column(String(4), nullable=True)
    phone = EncryptedPIIField("_phone")
    _address = Column("address", Text, nullable=True)
    address = EncryptedPIIField("_address")

    # Notice delivery preference
    notice_preference = Column(
        SQLEnum(
            NoticePreference,
            name="noticepreference",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=NoticePreference.EMAIL,
        nullable=False,
    )

    # Structured mailing address (USPS standards)
    _address_line1 = Column("address_line1", String(500), nullable=True)
    address_line1 = EncryptedPIIField("_address_line1")
    _address_line2 = Column("address_line2", String(500), nullable=True)
    address_line2 = EncryptedPIIField("_address_line2")
    city = Column(String(100), nullable=True)
    state = Column(String(2), nullable=True)  # 2-letter state code
    zip_code = Column(String(10), nullable=True)  # ZIP or ZIP+4
    country = Column(String(50), default="USA", nullable=True)

    # Address verification status
    address_status = Column(
        SQLEnum(
            AddressStatus,
            name="addressstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=AddressStatus.UNVERIFIED,
        nullable=False,
    )
    address_verified_at = Column(DateTime(timezone=True), nullable=True)
    address_returned_mail_count = Column(Integer, default=0, nullable=False)
    address_last_returned_at = Column(DateTime(timezone=True), nullable=True)

    # Enhanced patron fields
    emergency_contact_name = Column(String(200), nullable=True)
    _emergency_contact_phone = Column("emergency_contact_phone", String(500), nullable=True)
    emergency_contact_phone = EncryptedPIIField("_emergency_contact_phone")
    preferred_contact_method = Column(String(20), nullable=True)  # email, phone, mail
    language_preference = Column(String(50), nullable=True)
    accessibility_needs = Column(Text, nullable=True)
    pronouns = Column(String(50), nullable=True)
    patron_type = Column(String(20), nullable=True)  # adult, teen, child
    custom_fields = Column(Text, nullable=True)  # JSON string for key-value pairs
    # Teacher card: when role==TEACHER, this links the user to a school
    # OutreachPartner row. NULL for non-teachers.
    school_id = Column(
        Integer,
        ForeignKey(
            "outreach_partners.id",
            ondelete="SET NULL",
            use_alter=True,
            name="users_school_id_fkey",
        ),
        nullable=True,
        index=True,
    )
    photo_url = Column(Text, nullable=True)  # Base64 or URL to photo

    # UI Mode preference
    ui_mode = Column(String(50), default="full", nullable=False)  # 'essentials' or 'full'

    # COPPA Compliance - Age verification and parental consent
    # date_of_birth is encrypted at rest; SQL date comparisons are impossible,
    # so under_18 is a maintained boolean for age-gate queries. NOTE: under_18
    # is computed at write/backfill time. Recompute cadence and the exact
    # 18th-birthday boundary semantics are PENDING a maintainer decision (test_08); no
    # recompute job is built here.
    date_of_birth = Column(EncryptedDate, nullable=True)
    under_18 = Column(Boolean, nullable=True, index=True)
    parent_guardian_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    parental_consent_given = Column(Boolean, default=False, nullable=False)
    parental_consent_date = Column(DateTime(timezone=True), nullable=True)
    parental_consent_method = Column(
        String(50), nullable=True
    )  # "email_verification", "in_person", "phone"
    _parental_consent_email = Column("parental_consent_email", String(500), nullable=True)
    parental_consent_email = EncryptedPIIField("_parental_consent_email")
    parent_guardian_name = Column(String(200), nullable=True)
    parental_consent_token = Column(String(255), nullable=True, index=True)
    parental_consent_token_expires = Column(DateTime(timezone=True), nullable=True)

    # GDPR - Data deletion request tracking
    deletion_requested_at = Column(DateTime(timezone=True), nullable=True)
    deletion_scheduled_for = Column(DateTime(timezone=True), nullable=True)

    # Reading minutes (for children)
    reading_minutes_owed = Column(Integer, default=0, nullable=False)
    reading_minutes_logged = Column(Integer, default=0, nullable=False)

    # Account lockout (added in 009)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime(timezone=True), nullable=True)

    # Password reset (added in 009)
    reset_token = Column(String(255), nullable=True, index=True)
    reset_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Email verification (added in 009)
    email_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255), nullable=True)
    verification_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Staff email invite
    invite_token = Column(String(255), nullable=True, index=True)
    invite_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Magic link passwordless login
    magic_link_token = Column(String(255), nullable=True, index=True)
    magic_link_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Privacy settings
    track_reading_history = Column(Boolean, default=False, nullable=False)
    # Receipt privacy: if True, printed receipts/notices omit item titles for sensitive privacy
    discreet_receipts = Column(Boolean, default=True, nullable=False)
    # Staff access: if False, patron opts out of staff viewing checkout history
    allow_staff_access_to_history = Column(Boolean, default=False, nullable=False)
    # Aggregate recommendations: if True, patron's checkouts/returns are excluded
    # from /discover trending aggregates. Per-patron control; system-level
    # kill-switch is the aggregate_trending_enabled feature flag.
    aggregate_recommendations_opt_out = Column(Boolean, default=False, nullable=False)
    # Notification frequency: 'instant', 'daily', 'weekly', 'never'
    notification_frequency = Column(String(20), default="instant", nullable=False)

    # Two-Factor Authentication (TOTP)
    totp_secret = Column(Text, nullable=True)  # AES-256 encrypted TOTP secret
    totp_enabled = Column(Boolean, default=False, nullable=False)
    totp_confirmed_at = Column(DateTime(timezone=True), nullable=True)
    recovery_codes = Column(Text, nullable=True)  # JSON array of bcrypt-hashed codes
    totp_setup_dismissals = Column(
        Integer, default=0, server_default="0", nullable=False
    )  # 2FA setup prompt dismissal count

    # Recovery email
    _recovery_email = Column("recovery_email", String(500), nullable=True)
    recovery_email = EncryptedPIIField("_recovery_email")
    recovery_email_verified = Column(Boolean, default=False, nullable=False)
    recovery_email_token = Column(String(255), nullable=True)
    recovery_email_token_expires = Column(DateTime(timezone=True), nullable=True)

    # Security alert preferences
    security_alert_new_login = Column(Boolean, default=True, nullable=False)
    security_alert_changes = Column(Boolean, default=True, nullable=False)

    # Onboarding tracking
    onboarding_completed_at = Column(DateTime(timezone=True), nullable=True)
    onboarding_version = Column(String(20), nullable=True, default="1.0")
    onboarding_skipped = Column(Boolean, default=False, nullable=False)
    show_tooltips = Column(Boolean, default=True, nullable=False)
    show_feature_highlights = Column(Boolean, default=True, nullable=False)
    first_login_at = Column(DateTime(timezone=True), nullable=True)
    getting_started_progress = Column(Text, nullable=True)  # JSON for checklist state

    # Login tracking
    last_login = Column(DateTime(timezone=True), nullable=True)

    # Materialized engagement signal — bumped by triggers on checkouts,
    # holds, and patron_messages. Used by outreach lapsed_days criteria.
    last_activity_at = Column(DateTime(timezone=True), nullable=True, index=True)

    # Library card expiration
    card_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Multi-branch support
    # NOTE: Foreign keys commented out - branches and library_systems tables don't exist yet
    # They will be created by bootstrap seeding
    home_branch_id = Column(Integer, nullable=True, index=True)
    home_library_system_id = Column(Integer, nullable=True, index=True)
    # For staff: which branch they primarily work at
    work_branch_id = Column(Integer, nullable=True, index=True)

    # Patron differentiation axis (Koha categorycode equivalent). Nullable;
    # staff users typically leave this NULL. See models/patron_category.py.
    patron_category_id = Column(
        Integer,
        ForeignKey("patron_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Family Account Linking - Groups accounts into households for unified views
    # When a child's link is approved, they get the same household_id as parent
    # This allows unified holds/checkouts/fines views
    household_id = Column(Integer, nullable=True, index=True)

    # Residency
    is_resident = Column(
        Boolean,
        nullable=True,
        default=None,
        doc="Auto-detected from zip code. null=unknown, True=in-service-area, False=out-of-area",
    )
    residency_override = Column(
        Boolean,
        nullable=True,
        default=None,
        doc="Admin manual override. When set, takes precedence over auto-detection",
    )
    residency_verified_at = Column(DateTime(timezone=True), nullable=True)

    # Room reservation no-show tracking
    room_reservation_no_show_count = Column(
        Integer, default=0, nullable=False
    )  # Track no-show count for room reservations

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "suspended_until IS NULL OR suspended_at IS NULL OR suspended_until > suspended_at",
            name="ck_user_suspended_until_after_suspended_at",
        ),
        CheckConstraint(
            "reading_minutes_owed >= 0",
            name="ck_user_reading_minutes_owed_non_negative",
        ),
        CheckConstraint(
            "reading_minutes_logged >= 0",
            name="ck_user_reading_minutes_logged_non_negative",
        ),
        CheckConstraint(
            "failed_login_attempts >= 0",
            name="ck_user_failed_login_attempts_non_negative",
        ),
        CheckConstraint(
            "room_reservation_no_show_count >= 0",
            name="ck_user_room_no_show_count_non_negative",
        ),
        Index(
            "ix_users_last_name_prefix_hash",
            "last_name_prefix_hash",
            postgresql_using="gin",
        ),
    )

    # Relationships
    # NOTE: Using lazy="select" on relationships that could form circular reference chains
    # to prevent garbage collection issues. This ensures related objects are only loaded
    # when explicitly accessed, rather than eagerly loaded.
    refresh_tokens = relationship(
        "RefreshToken", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    favorites = relationship(
        "Favorite", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    hub_favorites = relationship(
        "UserHubFavorite",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    hub_visits = relationship(
        "UserHubVisit",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
    )
    reading_statuses = relationship(
        "ReadingStatus", back_populates="user", cascade="all, delete-orphan"
    )
    reviews = relationship("Review", back_populates="user", cascade="all, delete-orphan")
    # NOTE: Commented out - ReadingList model doesn't exist
    reading_lists = relationship(
        "ReadingList", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    password_history = relationship(
        "PasswordHistory", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    # COPPA - Parent/guardian relationship (self-referential with lazy loading)
    parent_guardian = relationship(
        "User",
        remote_side="User.id",
        foreign_keys=[parent_guardian_id],
        back_populates="children",
        lazy="select",
    )
    children = relationship(
        "User",
        foreign_keys="User.parent_guardian_id",
        back_populates="parent_guardian",
        lazy="select",
    )
    # Multi-branch relationships
    # NOTE: Commented out - Branch and LibrarySystem models don't exist
    # # DISABLED: # DISABLED: home_branch relationship
    # home_library_system = relationship("LibrarySystem", foreign_keys=[home_library_system_id])
    # work_branch = relationship("Branch", foreign_keys=[work_branch_id])
    # Circulation relationships
    checkouts = relationship("Checkout", back_populates="user", lazy="select")
    holds = relationship("Hold", back_populates="user", lazy="select")
    # Teacher card school link (no back_populates to avoid touching OutreachPartner)
    school = relationship("OutreachPartner", foreign_keys=[school_id], lazy="select")
    # Marketing/Newsletter relationship
    # NOTE: Commented out - NewsletterSubscription model doesn't exist
    # newsletter_subscription = relationship(
    #     "NewsletterSubscription",
    #     back_populates="user",
    #     uselist=False,
    #     cascade="all, delete-orphan",
    #     lazy="select"
    # )
    # Privacy monitoring alerts
    # NOTE: Commented out - PrivacyAlert model doesn't exist
    # privacy_alerts = relationship(
    #     "PrivacyAlert",
    #     back_populates="user",
    #     foreign_keys="PrivacyAlert.user_id",
    #     cascade="all, delete-orphan",
    #     lazy="select"
    # )
    # Threat response relationships
    # NOTE: Commented out - ThreatAlert and StaffCheckIn models don't exist
    # threat_alerts_created = relationship(
    #     "ThreatAlert",
    #     back_populates="created_by",
    #     foreign_keys="ThreatAlert.created_by_id",
    #     lazy="select"
    # )
    # threat_checkins = relationship(
    #     "StaffCheckIn",
    #     back_populates="user",
    #     foreign_keys="StaffCheckIn.user_id",
    #     cascade="all, delete-orphan",
    #     lazy="select"
    # )
    # Print management relationships
    print_jobs = relationship(
        "PrintJob", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    print_quota = relationship(
        "PrintQuota",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="select",
    )
    print_refunds = relationship(
        "PrintRefund",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="select",
        foreign_keys="PrintRefund.user_id",
    )
    scan_to_emails = relationship(
        "ScanToEmail", back_populates="user", cascade="all, delete-orphan", lazy="select"
    )
    # Family account linking relationships
    household_link_requests = relationship(
        "HouseholdLink",
        foreign_keys="HouseholdLink.requester_id",
        back_populates="requester",
        lazy="select",
    )
    household_link_targets = relationship(
        "HouseholdLink",
        foreign_keys="HouseholdLink.target_parent_id",
        back_populates="target_parent",
        lazy="select",
    )

    # Notification preferences relationship
    notification_preferences = relationship(
        "UserNotificationPreference", back_populates="user", uselist=False, lazy="select"
    )

    def set_phone(self, value: str | None) -> None:
        self.phone = value  # EncryptedPIIField handles encryption
        if value:
            from ..core.encryption import hash_pii

            stripped = re.sub(r"\D", "", value)
            self.phone_hash = hash_pii(stripped, field="phone")
            self.phone_last4 = stripped[-4:] if len(stripped) >= 4 else stripped
        else:
            self.phone_hash = None
            self.phone_last4 = None

    def set_name(self, first_name: str | None, last_name: str | None) -> None:
        """Set name + maintain blind indexes. Construction sites can keep using
        the first_name=/last_name= kwargs; the before_insert/before_update event
        below recomputes these hashes on every flush regardless."""
        self.first_name = first_name
        self.last_name = last_name
        _recompute_name_hashes(self)

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def reading_minutes_balance(self) -> int:
        return max(0, self.reading_minutes_owed - self.reading_minutes_logged)

    @property
    def age(self) -> int | None:
        if self.date_of_birth is None:
            return None
        from datetime import date

        today = date.today()
        return (
            today.year
            - self.date_of_birth.year
            - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))
        )

    @property
    def is_minor(self) -> bool:
        age = self.age
        if age is None:
            return False  # If no DOB, assume not a minor
        return age < COPPA_AGE_THRESHOLD

    @property
    def is_teen(self) -> bool:
        age = self.age
        if age is None:
            return False
        return COPPA_AGE_THRESHOLD <= age < TEEN_AGE_THRESHOLD

    @property
    def is_youth(self) -> bool:
        return self.is_minor or self.is_teen

    @property
    def requires_parental_consent(self) -> bool:
        return self.is_minor and not self.parental_consent_given

    def is_card_expired(self, grace_period_days: int = 0) -> bool:
        if self.card_expires_at is None:
            return False
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        grace_period = timedelta(days=grace_period_days)
        return now > (self.card_expires_at + grace_period)

    def days_until_card_expires(self) -> int | None:
        if self.card_expires_at is None:
            return None
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        delta = self.card_expires_at - now
        return delta.days

    @property
    def is_deceased(self) -> bool:
        return self.patron_status == PatronStatus.DECEASED

    @property
    def is_suspended(self) -> bool:
        return self.patron_status == PatronStatus.SUSPENDED

    @property
    def is_blocked(self) -> bool:
        return self.patron_status == PatronStatus.BLOCKED

    def should_lift_suspension(self) -> bool:
        if self.patron_status != PatronStatus.SUSPENDED:
            return False
        if self.suspended_until is None:
            return False
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        return now >= self.suspended_until

    @property
    def can_access_account(self) -> bool:
        if not self.is_active:
            return False
        if self.is_deceased:
            return False
        if self.is_locked():
            return False
        if self.requires_parental_consent:
            return False
        return True

    @property
    def can_circulate(self) -> bool:
        if not self.is_active:
            return False
        if self.is_deceased:
            return False
        if self.patron_status in [PatronStatus.BLOCKED, PatronStatus.SUSPENDED]:
            return False
        return True

    def is_locked(self) -> bool:
        from datetime import datetime, timezone

        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token = Column(String(255), unique=True, nullable=False, index=True)
    device_info = Column(String(255), nullable=True)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    last_active_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def is_valid(self) -> bool:
        from datetime import datetime, timezone

        if self.revoked_at is not None:
            return False
        return datetime.now(timezone.utc) < self.expires_at


class PasswordHistory(Base):
    __tablename__ = "password_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="password_history")


class DeletedEmail(Base):
    __tablename__ = "deleted_emails"

    id = Column(Integer, primary_key=True, index=True)

    # Hashed email for privacy - we only need to check if an email matches
    email_hash = Column(String(255), unique=True, nullable=False, index=True)

    # When the account was deleted
    deleted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # When the re-registration block expires (90 days after deletion)
    block_expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    # Deletion type for audit purposes
    deletion_type = Column(
        String(50), nullable=False
    )  # 'self_service', 'staff_initiated', 'scheduled'

    # Optional: Staff member who processed the deletion (null for self-service)
    processed_by_staff_id = Column(Integer, nullable=True)


# Max prefix length stored for last-name prefix blind index. 12 covers
# essentially all surnames staff would prefix-search; longer names still get
# an exact-match hash via last_name_hash.
_LAST_NAME_PREFIX_MAX = 12


def name_blind_hash(value: str) -> str:
    from ..core.encryption import hash_pii

    return hash_pii(value, field="name")


def email_blind_hash(value: str) -> str:
    from ..core.encryption import hash_pii

    return hash_pii(value, field="email")


def email_match_clause(value: str):
    """Exact-match clause for an email via the blind index. Replaces both
    ``User.email == x`` and substring ``User.email.ilike('%x%')`` lookups
    (email is encrypted; substring search on ciphertext is impossible, so
    email search is now exact-match). Returns None for an empty value."""
    normalized = (value or "").strip().lower()
    if not normalized:
        return None
    return User.email_hash == email_blind_hash(normalized)


def _norm_name(value) -> str:
    return (value or "").strip().lower()


def last_name_prefix_hashes(last_name) -> list[str]:
    """HMACs of each 1..N-char lowercased prefix of the last name."""
    normalized = _norm_name(last_name)
    if not normalized:
        return []
    upper = min(len(normalized), _LAST_NAME_PREFIX_MAX)
    return [name_blind_hash(normalized[:i]) for i in range(1, upper + 1)]


def name_search_clause(search: str):
    """Blind-index search clause for a name query. Matches:
      - the whole query as an exact first OR last name,
      - the whole query as a last-name PREFIX,
      - for multi-token queries ("First Last"), exact first AND last name.
    Substring-anywhere is intentionally not supported (maintainer decision).
    Returns None when the query is empty."""
    from sqlalchemy import and_, or_

    normalized = _norm_name(search)
    if not normalized:
        return None
    whole = name_blind_hash(normalized)
    clauses = [
        User.first_name_hash == whole,
        User.last_name_hash == whole,
        User.last_name_prefix_hash.op("?")(whole),
    ]
    tokens = normalized.split()
    if len(tokens) >= 2:
        # Treat first token as first name and the remainder as last name.
        first_h = name_blind_hash(tokens[0])
        last_h = name_blind_hash(" ".join(tokens[1:]))
        clauses.append(
            and_(
                User.first_name_hash == first_h,
                User.last_name_hash == last_h,
            )
        )
    return or_(*clauses)


def name_or_email_clause(search: str):
    """Blind-index clause matching a patron by name (exact/last-prefix) OR by
    exact email. Convenience for the many staff search sites that ilike'd both
    encrypted columns. Returns None when the query is empty."""
    from sqlalchemy import or_

    parts = [c for c in (name_search_clause(search), email_match_clause(search)) if c is not None]
    if not parts:
        return None
    return or_(*parts)


def _recompute_name_hashes(user: "User") -> None:
    first = _norm_name(user.first_name)
    last = _norm_name(user.last_name)
    user.first_name_hash = name_blind_hash(first) if first else None
    user.last_name_hash = name_blind_hash(last) if last else None
    user.last_name_prefix_hash = last_name_prefix_hashes(last) or None


def _recompute_email_hash(user: "User") -> None:
    normalized = (user.email or "").strip().lower()
    user.email_hash = email_blind_hash(normalized) if normalized else None


def _recompute_under_18(user: "User") -> None:
    # date_of_birth is encrypted; precompute the age gate. Computed at write
    # time only -- see the date_of_birth column note re: recompute cadence.
    age = user.age
    user.under_18 = (age < TEEN_AGE_THRESHOLD) if age is not None else None


def _recompute_phone_hash(user: "User") -> None:
    # Mirror set_phone() so a phone supplied via constructor kwarg or attribute
    # assignment still gets a searchable blind index / last4. Without this, any
    # User built without calling set_phone() has an unsearchable phone.
    value = user.phone
    if value:
        from ..core.encryption import hash_pii

        stripped = re.sub(r"\D", "", value)
        user.phone_hash = hash_pii(stripped, field="phone") if stripped else None
        user.phone_last4 = (stripped[-4:] if len(stripped) >= 4 else stripped) or None
    else:
        user.phone_hash = None
        user.phone_last4 = None


@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def _user_before_write(mapper, connection, target: "User") -> None:
    # Keep blind indexes in sync no matter how first_name/last_name/phone were
    # set (constructor kwargs, attribute assignment, or set_name/set_phone).
    # Reading the encrypted attrs here is greenlet-safe: values are already
    # loaded, no DB I/O.
    _recompute_name_hashes(target)
    _recompute_email_hash(target)
    _recompute_phone_hash(target)
    _recompute_under_18(target)
