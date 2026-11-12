# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Enum as SQLEnum, ForeignKey, Integer, JSON, String, Text, Index, func
from sqlalchemy.orm import relationship

from app.models.mixins import TimestampMixin
from ..core.database import Base


class BoundaryType(StrEnum):
    CIRCULATION_SUSPENSION = "circulation_suspension"
    LOCATION_RESTRICTION = "location_restriction"
    BEHAVIOR_CONTRACT = "behavior_contract"
    STAFF_INTERACTION_LIMIT = "staff_interaction_limit"
    SERVICE_RESTRICTION = "service_restriction"
    COMMUNICATION_PROTOCOL = "communication_protocol"
    TIME_LIMIT = "time_limit"
    PROGRAM_EXCLUSION = "program_exclusion"
    RESOURCE_LIMIT = "resource_limit"
    SUPERVISED_ACCESS_ONLY = "supervised_access_only"


class BoundaryStatus(StrEnum):
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    UNDER_REVIEW = "under_review"
    APPEALED = "appealed"
    EXPIRED = "expired"
    LIFTED = "lifted"
    ESCALATED = "escalated"


class AppealStatus(StrEnum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    DENIED = "denied"
    WITHDRAWN = "withdrawn"


class EscalationLevel(StrEnum):
    STAFF = "staff"
    MANAGER = "manager"
    DIRECTOR = "director"
    LEGAL = "legal"


class PatronBoundary(TimestampMixin, Base):
    __tablename__ = "patron_boundaries"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Boundary details
    boundary_type = Column(SQLEnum(BoundaryType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    specific_restrictions = Column(JSON, nullable=True)  # Detailed restrictions

    # Status tracking
    status = Column(SQLEnum(BoundaryStatus, values_callable=lambda x: [e.value for e in x]), nullable=False, default=BoundaryStatus.PENDING_APPROVAL, index=True)
    requires_approval = Column(Boolean, default=True)
    approved_by_director = Column(Boolean, default=False)

    # Duration
    start_date = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    end_date = Column(DateTime, nullable=True)
    is_permanent = Column(Boolean, default=False)

    # Incident tracking
    incident_count = Column(Integer, default=1)
    incident_dates = Column(JSON, nullable=True)  # Array of incident datetimes
    supporting_evidence = Column(JSON, nullable=True)  # Evidence links, descriptions

    # Rehabilitation
    rehabilitation_conditions = Column(JSON, nullable=True)
    rehabilitation_progress = Column(Text, nullable=True)
    can_appeal = Column(Boolean, default=True)

    # Staff tracking
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Audit trail, server_default=func.now(), nullable=False, index=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
    patron = relationship("User", foreign_keys=[patron_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    out_of_scope_requests = relationship("OutOfScopeRequest", back_populates="boundary", cascade="all, delete-orphan")
    escalations = relationship("BoundaryEscalation", back_populates="boundary", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_patron_boundary_patron_status", "patron_id", "status"),
        Index("idx_patron_boundary_org_date", "organization_id", "created_at"),
    )


class OutOfScopeRequest(Base):
    __tablename__ = "out_of_scope_requests"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    boundary_id = Column(Integer, ForeignKey("patron_boundaries.id", ondelete="CASCADE"), nullable=True)

    # Request details
    request_description = Column(Text, nullable=False)
    request_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    staff_member_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Categorization
    request_category = Column(String(100), nullable=True)  # IT support, personal errands, etc.
    why_out_of_scope = Column(Text, nullable=False)
    policy_reference = Column(String(255), nullable=True)

    # Response tracking
    how_declined = Column(Text, nullable=True)
    patron_reaction = Column(Text, nullable=True)
    required_escalation = Column(Boolean, default=False)

    # Pattern detection
    is_repeat_request = Column(Boolean, default=False)
    related_request_count = Column(Integer, default=0)

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
    patron = relationship("User", foreign_keys=[patron_id])
    staff_member = relationship("User", foreign_keys=[staff_member_id])
    boundary = relationship("PatronBoundary", back_populates="out_of_scope_requests")


class BoundaryTemplate(Base):
    __tablename__ = "boundary_templates"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Template details
    name = Column(String(255), nullable=False)
    boundary_type = Column(SQLEnum(BoundaryType, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    script_content = Column(Text, nullable=False)

    # Usage guidance
    when_to_use = Column(Text, nullable=True)
    tone_guidance = Column(String(100), nullable=True)  # firm, empathetic, formal
    follow_up_actions = Column(JSON, nullable=True)

    # Audit, server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    usage_count = Column(Integer, default=0)

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
    created_by = relationship("User")


class BoundaryPolicy(Base):
    __tablename__ = "boundary_policies"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Policy details
    policy_name = Column(String(255), nullable=False)
    policy_code = Column(String(50), nullable=True, unique=True, index=True)
    policy_text = Column(Text, nullable=False)

    # Application
    applies_to_boundary_types = Column(JSON, nullable=True)  # Array of boundary types
    escalation_procedure = Column(Text, nullable=True)
    appeal_procedure = Column(Text, nullable=True)

    # Authority levels
    requires_director_approval = Column(Boolean, default=False)
    requires_board_approval = Column(Boolean, default=False)

    # Audit
    effective_date = Column(DateTime, nullable=False)
    last_reviewed_date = Column(DateTime, nullable=True)

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet


class UnreasonableDemandLog(Base):
    __tablename__ = "unreasonable_demand_logs"

    id = Column(Integer, primary_key=True, index=True)
    organization_id = Column(Integer, nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # Incident details
    demand_description = Column(Text, nullable=False)
    incident_date = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    staff_member_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Why unreasonable
    unreasonable_reasons = Column(JSON, nullable=True)  # Array of reasons
    evidence_links = Column(JSON, nullable=True)
    witness_ids = Column(JSON, nullable=True)  # Array of staff user IDs

    # Impact assessment
    emotional_impact_level = Column(Integer, nullable=True)  # 1-5 scale
    time_wasted_minutes = Column(Integer, nullable=True)
    required_manager_intervention = Column(Boolean, default=False)

    # Relationships
    # Note: organization_id FK exists but no Organization model defined yet
    patron = relationship("User", foreign_keys=[patron_id])
    staff_member = relationship("User", foreign_keys=[staff_member_id])


class BoundaryEscalation(Base):
    __tablename__ = "boundary_escalations"

    id = Column(Integer, primary_key=True, index=True)
    boundary_id = Column(Integer, ForeignKey("patron_boundaries.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(Integer, nullable=False, index=True)

    # Escalation details
    from_level = Column(SQLEnum(EscalationLevel, values_callable=lambda x: [e.value for e in x]), nullable=False)
    to_level = Column(SQLEnum(EscalationLevel, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    reason = Column(Text, nullable=False)

    # Decision tracking
    escalated_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    escalated_to_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    decision = Column(Text, nullable=True)
    decision_date = Column(DateTime, nullable=True)

    # Status
    is_resolved = Column(Boolean, default=False, index=True)
    requires_further_escalation = Column(Boolean, default=False)

    # Timestamps, server_default=func.now(), nullable=False)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    boundary = relationship("PatronBoundary", back_populates="escalations")
    # Note: organization_id FK exists but no Organization model defined yet
    escalated_by = relationship("User", foreign_keys=[escalated_by_id])
    escalated_to = relationship("User", foreign_keys=[escalated_to_id])
