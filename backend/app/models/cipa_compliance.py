# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta, timezone
from enum import StrEnum

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class PolicyType(StrEnum):
    INTERNET_USE = "internet_use"
    COMPUTER_LAB = "computer_lab"
    WIFI_ACCESS = "wifi_access"
    MINOR_INTERNET = "minor_internet"  # Additional restrictions for minors


class BypassReason(StrEnum):
    BONA_FIDE_RESEARCH = "bona_fide_research"
    MEDICAL_INFORMATION = "medical_information"
    LEGAL_RESEARCH = "legal_research"
    EDUCATIONAL_PURPOSE = "educational_purpose"
    OTHER_LAWFUL = "other_lawful"


class BypassStatus(StrEnum):
    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    COMPLETED = "completed"


class ComputerSessionStatus(StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    TIMED_OUT = "timed_out"
    TERMINATED = "terminated"  # Staff-terminated


class InternetPolicyAcceptance(Base):
    __tablename__ = "internet_policy_acceptances"

    id = Column(Integer, primary_key=True, index=True)

    # Patron who accepted (nullable for guest users)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Session identifier for guest/anonymous tracking
    session_id = Column(String(255), nullable=False, index=True)

    # Policy details
    policy_type = Column(
        SQLEnum(PolicyType, name="policytype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False, index=True
    )
    policy_version = Column(String(50), nullable=False)

    # Patron classification at time of acceptance
    is_minor = Column(Boolean, nullable=False, default=False)
    patron_type = Column(String(50), nullable=True)  # adult, teen, child

    # Acceptance details
    accepted_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    # Location/device
    workstation_id = Column(String(100), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # For WiFi acceptance - device identifier
    device_mac_hash = Column(String(64), nullable=True)  # Hashed for privacy

    # Relationships
    patron = relationship("User", backref="policy_acceptances")

    __table_args__ = (
        Index("ix_policy_acceptance_patron_type", "patron_id", "policy_type"),
        Index("ix_policy_acceptance_date_branch", "accepted_at", "branch_location"),
        Index("ix_policy_acceptance_minor", "is_minor", "accepted_at"),
    )

    @property
    def is_valid(self) -> bool:
        if self.accepted_at is None:
            return False
        expiry = self.accepted_at + timedelta(hours=24)
        return datetime.now(timezone.utc) < expiry


class FilterBypassRequest(Base):
    __tablename__ = "filter_bypass_requests"

    id = Column(Integer, primary_key=True, index=True)

    # Patron requesting bypass (must be adult)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False, index=True
    )

    # Staff member who approved
    approved_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=False, index=True
    )

    # Bypass details
    reason = Column(
        SQLEnum(BypassReason, name="bypassreason", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    reason_details = Column(String(500), nullable=True)  # Additional context

    # Status tracking
    status = Column(
        SQLEnum(BypassStatus, name="bypassstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=BypassStatus.ACTIVE,
        nullable=False, index=True
    )

    # Location
    workstation_id = Column(String(100), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Time window
    bypass_start = Column(DateTime(timezone=True), nullable=False)
    bypass_end = Column(DateTime(timezone=True), nullable=False)

    # Patron acknowledgments
    patron_acknowledged_aup = Column(Boolean, default=True, nullable=False)
    patron_acknowledged_monitoring = Column(Boolean, default=True, nullable=False)

    # Revocation (if applicable)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    revocation_reason = Column(String(255), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="bypass_requests")
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    revoked_by = relationship("User", foreign_keys=[revoked_by_id])

    __table_args__ = (
        Index("ix_bypass_request_patron_status", "patron_id", "status"),
        Index("ix_bypass_request_workstation", "workstation_id", "status"),
        Index("ix_bypass_request_date", "bypass_start", "bypass_end"),
    )

    @property
    def is_active(self) -> bool:
        if self.status != BypassStatus.ACTIVE:
            return False
        now = datetime.now(timezone.utc)
        return self.bypass_start <= now <= self.bypass_end

    @property
    def duration_minutes(self) -> int:
        if self.bypass_start and self.bypass_end:
            delta = self.bypass_end - self.bypass_start
            return int(delta.total_seconds() / 60)
        return 0


class ComputerSession(Base):
    __tablename__ = "computer_sessions"

    id = Column(Integer, primary_key=True, index=True)

    # Patron (nullable for guest sessions)
    patron_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True, index=True
    )

    # Session identification
    session_token = Column(String(255), unique=True, nullable=True, index=True)

    # Status
    status = Column(
        SQLEnum(ComputerSessionStatus, name="computersessionstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ComputerSessionStatus.ACTIVE,
        nullable=False, index=True
    )

    # Patron classification
    is_minor = Column(Boolean, nullable=False, default=False)
    patron_type = Column(String(50), nullable=True)

    # Location/device
    workstation_id = Column(String(100), nullable=True, index=True)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # deprecated; use branch_id

    # Policy acceptance reference
    policy_acceptance_id = Column(
        Integer, ForeignKey("internet_policy_acceptances.id", ondelete="SET NULL"),
        nullable=True
    )

    # Filter bypass reference (if applicable)
    active_bypass_id = Column(
        Integer, ForeignKey("filter_bypass_requests.id", ondelete="SET NULL"),
        nullable=True
    )

    # Filtering status
    content_filtering_enabled = Column(Boolean, default=True, nullable=False)
    minor_filtering_enabled = Column(Boolean, default=False, nullable=False)

    # Session timing
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    scheduled_end = Column(DateTime(timezone=True), nullable=True)  # Time limit
    ended_at = Column(DateTime(timezone=True), nullable=True)

    # Session limits
    max_duration_minutes = Column(Integer, default=120, nullable=False)  # 2 hours default
    extension_count = Column(Integer, default=0, nullable=False)

    # Termination details
    terminated_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    termination_reason = Column(String(255), nullable=True)

    # Network info (hashed for privacy)
    ip_address = Column(String(45), nullable=True)

    # ── Booking-system columns ──────────────────────────────────────
    reservation_id = Column(
        Integer, ForeignKey("computer_reservations.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    computer_id = Column(
        Integer, ForeignKey("computers.id", ondelete="SET NULL"),
        nullable=True, index=True
    )
    session_start_time = Column(DateTime(timezone=True), nullable=True)
    session_end_time = Column(DateTime(timezone=True), nullable=True)
    actual_end_time = Column(DateTime(timezone=True), nullable=True)
    auto_logout_at = Column(DateTime(timezone=True), nullable=True)
    auto_logout_executed = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    was_extended = Column(Boolean, default=False, nullable=False)
    warning_sent_at = Column(DateTime(timezone=True), nullable=True)
    user_initiated_logout = Column(Boolean, default=False, nullable=False)
    logoff_reason = Column(String(255), nullable=True)
    print_jobs_count = Column(Integer, default=0, nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="computer_sessions")
    policy_acceptance = relationship("InternetPolicyAcceptance")
    active_bypass = relationship("FilterBypassRequest")
    terminated_by = relationship("User", foreign_keys=[terminated_by_id])

    __table_args__ = (
        Index("ix_computer_session_workstation_status", "workstation_id", "status"),
        Index("ix_computer_session_patron", "patron_id", "started_at"),
        Index("ix_computer_session_active", "status", "started_at"),
        Index("ix_computer_session_computer_id", "computer_id"),
        Index("ix_computer_session_reservation", "reservation_id"),
        Index("ix_computer_session_is_active", "is_active"),
    )

    @property
    def duration_minutes(self) -> int:
        end_time = self.ended_at or datetime.now(timezone.utc)
        if self.started_at:
            delta = end_time - self.started_at
            return int(delta.total_seconds() / 60)
        return 0

    @property
    def is_overtime(self) -> bool:
        if self.status != ComputerSessionStatus.ACTIVE:
            return False
        return self.duration_minutes > self.max_duration_minutes


class CIPAComplianceReport(Base):
    __tablename__ = "cipa_compliance_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Report period
    report_period_start = Column(DateTime(timezone=True), nullable=False)
    report_period_end = Column(DateTime(timezone=True), nullable=False)
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True, index=True)
    branch_location = Column(String(100), nullable=True)  # NULL = all branches

    # Statistics
    total_sessions = Column(Integer, default=0, nullable=False)
    minor_sessions = Column(Integer, default=0, nullable=False)
    adult_sessions = Column(Integer, default=0, nullable=False)
    guest_sessions = Column(Integer, default=0, nullable=False)

    # Policy acceptance stats
    policy_acceptances = Column(Integer, default=0, nullable=False)
    minor_policy_acceptances = Column(Integer, default=0, nullable=False)

    # Filter bypass stats
    bypass_requests_total = Column(Integer, default=0, nullable=False)
    bypass_requests_approved = Column(Integer, default=0, nullable=False)
    bypass_requests_revoked = Column(Integer, default=0, nullable=False)

    # Filtering stats (if available from external system)
    filter_blocks_total = Column(Integer, nullable=True)
    filter_blocks_minors = Column(Integer, nullable=True)

    # Report metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    generated_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # File storage
    report_file_path = Column(String(500), nullable=True)

    # Notes
    notes = Column(Text, nullable=True)

    # Relationships
    generated_by = relationship("User")

    __table_args__ = (
        Index("ix_cipa_report_period", "report_period_start", "report_period_end"),
    )
