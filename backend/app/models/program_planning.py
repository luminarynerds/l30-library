# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import date, datetime, time
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    Boolean, Column, Date, DateTime, Enum as SQLEnum, Float, ForeignKey,
    Integer, Numeric, String, Text, Time, Index, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


# ============================================================================
# Enums
# ============================================================================

class TemplateCategory(StrEnum):
    SUMMER_READING = "summer_reading"
    STORYTIME = "storytime"
    WORKSHOP = "workshop"
    BOOK_CLUB = "book_club"
    STEM = "stem"
    ARTS_CRAFTS = "arts_crafts"
    TECHNOLOGY = "technology"
    OUTREACH = "outreach"
    LECTURE = "lecture"
    PERFORMANCE = "performance"
    HOLIDAY = "holiday"
    COMMUNITY = "community"
    OTHER = "other"


class BudgetItemCategory(StrEnum):
    SUPPLIES = "supplies"
    FOOD_BEVERAGE = "food_beverage"
    SPEAKER_FEES = "speaker_fees"
    EQUIPMENT_RENTAL = "equipment_rental"
    MARKETING = "marketing"
    PRINTING = "printing"
    VENUE = "venue"
    LICENSES = "licenses"
    TRANSPORTATION = "transportation"
    DECORATIONS = "decorations"
    PRIZES = "prizes"
    MISCELLANEOUS = "miscellaneous"


class SupplyItemStatus(StrEnum):
    NEEDED = "needed"
    ORDERED = "ordered"
    RECEIVED = "received"
    ON_HAND = "on_hand"
    UNAVAILABLE = "unavailable"


class VenueBookingStatus(StrEnum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


class MarketingMilestoneType(StrEnum):
    SOCIAL_MEDIA_POST = "social_media_post"
    FLYER_DESIGN = "flyer_design"
    FLYER_DISTRIBUTION = "flyer_distribution"
    EMAIL_BLAST = "email_blast"
    NEWSLETTER_INCLUSION = "newsletter_inclusion"
    WEBSITE_LISTING = "website_listing"
    PRESS_RELEASE = "press_release"
    SIGNAGE_UPDATE = "signage_update"
    PARTNER_OUTREACH = "partner_outreach"
    REGISTRATION_OPEN = "registration_open"
    REMINDER_SEND = "reminder_send"
    OTHER = "other"


class VolunteerAssignmentStatus(StrEnum):
    REQUESTED = "requested"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class EvaluationRating(StrEnum):
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    NOT_APPLICABLE = "not_applicable"


# ============================================================================
# Program Template Library
# ============================================================================

class ProgramTemplate(Base, TimestampMixin):
    __tablename__ = "program_templates"

    id = Column(Integer, primary_key=True, index=True)

    # Template identification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(
        String(50),
        nullable=False,
        index=True
    )

    # Target audience and type (mirrors Program model fields)
    target_audience = Column(String(50), nullable=False)  # children, teen, adult, etc.
    program_type = Column(String(50), nullable=False)  # storytime, workshop, etc.

    # Scheduling defaults
    default_duration_minutes = Column(Integer, default=60, nullable=False)
    recommended_capacity = Column(Integer, nullable=True)
    registration_required = Column(Boolean, default=False, nullable=False)

    # Room/equipment needs
    room_type_needed = Column(String(50), nullable=True)  # study_room, meeting_room, event_space
    equipment_needed = Column(JSON, nullable=True, default=list)
    # e.g., ["projector", "microphone", "whiteboard"]

    # Budget estimate
    estimated_budget = Column(Numeric(10, 2), nullable=True)

    # Marketing lead time (days before program to start marketing)
    marketing_lead_days = Column(Integer, default=14, nullable=True)

    # Volunteer needs
    volunteers_needed = Column(Integer, default=0, nullable=False)
    volunteer_roles_needed = Column(JSON, nullable=True, default=list)
    # e.g., ["setup", "registration_desk", "cleanup"]

    # Success criteria
    target_attendance = Column(Integer, nullable=True)
    success_metrics = Column(JSON, nullable=True, default=dict)
    # e.g., {"min_attendance": 15, "satisfaction_target": 4.0}

    # Template metadata
    is_active = Column(Boolean, default=True, nullable=False)
    times_used = Column(Integer, default=0, nullable=False)
    source_program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True
    )

    # Audit
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    source_program = relationship("Program", foreign_keys=[source_program_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    template_budget_items = relationship(
        "TemplateBudgetItem",
        back_populates="template",
        cascade="all, delete-orphan"
    )
    template_supply_items = relationship(
        "TemplateSupplyItem",
        back_populates="template",
        cascade="all, delete-orphan"
    )
    template_marketing_milestones = relationship(
        "TemplateMarketingMilestone",
        back_populates="template",
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_program_templates_category", "category"),
        Index("ix_program_templates_active", "is_active"),
    )


class TemplateBudgetItem(Base):
    __tablename__ = "template_budget_items"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("program_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    description = Column(String(255), nullable=False)
    category = Column(
        String(50),
        nullable=False
    )
    estimated_amount = Column(Numeric(10, 2), nullable=False)
    notes = Column(Text, nullable=True)

    template = relationship("ProgramTemplate", back_populates="template_budget_items")


class TemplateSupplyItem(Base):
    __tablename__ = "template_supply_items"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("program_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    item_name = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit = Column(String(50), nullable=True)  # e.g., "packs", "rolls", "each"
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    vendor_suggestion = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    template = relationship("ProgramTemplate", back_populates="template_supply_items")


class TemplateMarketingMilestone(Base):
    __tablename__ = "template_marketing_milestones"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(
        Integer,
        ForeignKey("program_templates.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    milestone_type = Column(
        String(50),
        nullable=False
    )
    description = Column(String(500), nullable=False)
    days_before_program = Column(Integer, nullable=False)  # e.g., 14 = two weeks before
    notes = Column(Text, nullable=True)

    template = relationship("ProgramTemplate", back_populates="template_marketing_milestones")


# ============================================================================
# Program Planning Instance (links a plan to an actual Program)
# ============================================================================

class ProgramPlan(Base, TimestampMixin):
    __tablename__ = "program_plans"

    id = Column(Integer, primary_key=True, index=True)

    # Link to actual program
    program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Template used (if any)
    template_id = Column(
        Integer,
        ForeignKey("program_templates.id", ondelete="SET NULL"),
        nullable=True
    )

    # Copied from a previous program (if any)
    copied_from_program_id = Column(
        Integer,
        ForeignKey("programs.id", ondelete="SET NULL"),
        nullable=True
    )

    # Planning status
    planning_notes = Column(Text, nullable=True)
    planning_complete = Column(Boolean, default=False, nullable=False)
    planning_completed_at = Column(DateTime(timezone=True), nullable=True)

    # Budget summary (denormalized from line items)
    total_budget = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)
    total_spent = Column(Numeric(10, 2), default=Decimal("0.00"), nullable=False)

    # Audit
    created_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Relationships
    program = relationship("Program", foreign_keys=[program_id], backref="plan")
    template = relationship("ProgramTemplate", foreign_keys=[template_id])
    copied_from_program = relationship("Program", foreign_keys=[copied_from_program_id])
    created_by = relationship("User", foreign_keys=[created_by_id])
    budget_items = relationship(
        "ProgramBudgetItem",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    supply_items = relationship(
        "ProgramSupplyItem",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    room_bookings = relationship(
        "ProgramRoomBooking",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    equipment_bookings = relationship(
        "ProgramEquipmentBooking",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    marketing_milestones = relationship(
        "ProgramMarketingMilestone",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    volunteer_assignments = relationship(
        "ProgramVolunteerAssignment",
        back_populates="plan",
        cascade="all, delete-orphan"
    )
    evaluation = relationship(
        "ProgramEvaluation",
        back_populates="plan",
        uselist=False,
        cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_program_plans_program", "program_id"),
    )


# ============================================================================
# Budget Tracking
# ============================================================================

class ProgramBudgetItem(Base, TimestampMixin):
    __tablename__ = "program_budget_items"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("program_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    description = Column(String(255), nullable=False)
    category = Column(
        String(50),
        nullable=False
    )
    estimated_amount = Column(Numeric(10, 2), nullable=False, default=Decimal("0.00"))
    actual_amount = Column(Numeric(10, 2), nullable=True)
    is_paid = Column(Boolean, default=False, nullable=False)
    paid_date = Column(Date, nullable=True)
    receipt_reference = Column(String(255), nullable=True)
    vendor = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)

    plan = relationship("ProgramPlan", back_populates="budget_items")

    __table_args__ = (
        Index("ix_program_budget_items_plan_category", "plan_id", "category"),
    )


# ============================================================================
# Supply Checklist
# ============================================================================

class ProgramSupplyItem(Base, TimestampMixin):
    __tablename__ = "program_supply_items"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("program_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    item_name = Column(String(255), nullable=False)
    quantity_needed = Column(Integer, default=1, nullable=False)
    quantity_on_hand = Column(Integer, default=0, nullable=False)
    unit = Column(String(50), nullable=True)
    estimated_cost = Column(Numeric(10, 2), nullable=True)
    actual_cost = Column(Numeric(10, 2), nullable=True)

    status = Column(
        String(50),
        default=SupplyItemStatus.NEEDED,
        nullable=False
    )

    vendor = Column(String(255), nullable=True)
    order_date = Column(Date, nullable=True)
    expected_delivery = Column(Date, nullable=True)
    assigned_to_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    notes = Column(Text, nullable=True)

    plan = relationship("ProgramPlan", back_populates="supply_items")
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])

    __table_args__ = (
        Index("ix_program_supply_items_plan_status", "plan_id", "status"),
    )


# ============================================================================
# Room & Equipment Auto-Booking
# ============================================================================

class ProgramRoomBooking(Base, TimestampMixin):
    __tablename__ = "program_room_bookings"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("program_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    room_id = Column(
        Integer,
        ForeignKey("rooms.id", ondelete="SET NULL"),
        nullable=True
    )
    reservation_id = Column(
        Integer,
        ForeignKey("room_reservations.id", ondelete="SET NULL"),
        nullable=True
    )

    status = Column(
        String(50),
        default=VenueBookingStatus.PENDING,
        nullable=False
    )
    setup_notes = Column(Text, nullable=True)
    setup_time_minutes = Column(Integer, default=15, nullable=True)
    teardown_time_minutes = Column(Integer, default=15, nullable=True)

    plan = relationship("ProgramPlan", back_populates="room_bookings")
    room = relationship("Room")

    __table_args__ = (
        Index("ix_program_room_bookings_plan", "plan_id"),
    )


class ProgramEquipmentBooking(Base, TimestampMixin):
    __tablename__ = "program_equipment_bookings"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("program_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    equipment_id = Column(
        Integer,
        ForeignKey("equipment.id", ondelete="SET NULL"),
        nullable=True
    )

    equipment_type_requested = Column(String(100), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    status = Column(
        String(50),
        default=VenueBookingStatus.PENDING,
        nullable=False
    )
    notes = Column(Text, nullable=True)

    plan = relationship("ProgramPlan", back_populates="equipment_bookings")
    equipment = relationship("Equipment")

    __table_args__ = (
        Index("ix_program_equipment_bookings_plan", "plan_id"),
    )


# ============================================================================
# Marketing Timeline Reminders
# ============================================================================

class ProgramMarketingMilestone(Base, TimestampMixin):
    __tablename__ = "program_marketing_milestones"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("program_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    milestone_type = Column(
        String(50),
        nullable=False
    )
    description = Column(String(500), nullable=False)
    due_date = Column(Date, nullable=False, index=True)
    completed = Column(Boolean, default=False, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    completed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    assigned_to_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    notes = Column(Text, nullable=True)

    plan = relationship("ProgramPlan", back_populates="marketing_milestones")
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_id])

    __table_args__ = (
        Index("ix_program_marketing_milestones_due", "due_date", "completed"),
        Index("ix_program_marketing_milestones_plan", "plan_id"),
    )


# ============================================================================
# Volunteer Assignment
# ============================================================================

class ProgramVolunteerAssignment(Base, TimestampMixin):
    __tablename__ = "program_volunteer_assignments"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("program_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    volunteer_id = Column(
        Integer,
        ForeignKey("volunteers.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    role = Column(String(100), nullable=False)  # e.g., "setup", "registration", "cleanup"
    status = Column(
        String(50),
        default=VolunteerAssignmentStatus.REQUESTED,
        nullable=False
    )
    confirmed_at = Column(DateTime(timezone=True), nullable=True)
    hours_worked = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)

    plan = relationship("ProgramPlan", back_populates="volunteer_assignments")
    volunteer = relationship("Volunteer")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_program_volunteer_assignments_plan", "plan_id"),
        Index("ix_program_volunteer_assignments_volunteer", "volunteer_id"),
    )


# ============================================================================
# Post-Program Evaluation
# ============================================================================

class ProgramEvaluation(Base, TimestampMixin):
    __tablename__ = "program_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(
        Integer,
        ForeignKey("program_plans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True
    )

    # Overall ratings
    overall_rating = Column(
        String(50),
        nullable=True
    )
    content_quality_rating = Column(
        String(50),
        nullable=True
    )
    logistics_rating = Column(
        String(50),
        nullable=True
    )
    engagement_rating = Column(
        String(50),
        nullable=True
    )

    # Attendance metrics
    expected_attendance = Column(Integer, nullable=True)
    actual_attendance = Column(Integer, nullable=True)
    new_patron_count = Column(Integer, default=0, nullable=True)
    repeat_attendee_count = Column(Integer, default=0, nullable=True)

    # Financial metrics
    budget_variance = Column(Numeric(10, 2), nullable=True)  # actual - estimated
    cost_per_attendee = Column(Numeric(10, 2), nullable=True)

    # Qualitative feedback
    staff_notes = Column(Text, nullable=True)
    what_went_well = Column(Text, nullable=True)
    what_to_improve = Column(Text, nullable=True)
    attendee_feedback_summary = Column(Text, nullable=True)

    # Recommendation
    recommend_repeat = Column(Boolean, nullable=True)
    recommended_changes = Column(Text, nullable=True)

    # Comparison data (JSON for flexibility)
    # e.g., {"last_year_attendance": 25, "attendance_change_pct": 20.0}
    comparison_metrics = Column(JSON, nullable=True, default=dict)

    # Evaluator
    evaluated_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    evaluated_at = Column(DateTime(timezone=True), nullable=True)

    plan = relationship("ProgramPlan", back_populates="evaluation")
    evaluated_by = relationship("User", foreign_keys=[evaluated_by_id])

    __table_args__ = (
        Index("ix_program_evaluations_plan", "plan_id"),
    )
