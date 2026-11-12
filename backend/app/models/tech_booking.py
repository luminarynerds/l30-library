# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text, Float, JSON)
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class TechTopic(StrEnum):
    email = "email"
    smartphone = "smartphone"
    tablet = "tablet"
    computer_basics = "computer_basics"
    internet_browsing = "internet_browsing"
    social_media = "social_media"
    password_management = "password_management"
    online_safety = "online_safety"
    resume_building = "resume_building"
    job_search_online = "job_search_online"
    cloud_storage = "cloud_storage"
    video_conferencing = "video_conferencing"
    library_website = "library_website"
    digital_resources = "digital_resources"
    accessibility_features = "accessibility_features"
    other = "other"


class SkillLevel(StrEnum):
    beginner = "beginner"
    intermediate = "intermediate"
    advanced = "advanced"


class BookingStatus(StrEnum):
    pending = "pending"  # Awaiting staff assignment/confirmation
    confirmed = "confirmed"  # Confirmed with staff member
    in_progress = "in_progress"  # Session is happening
    completed = "completed"  # Session finished normally
    cancelled = "cancelled"  # Cancelled by patron or staff
    no_show = "no_show"  # Patron didn't attend
    rescheduled = "rescheduled"  # Moved to different time


class TechFollowUpStatus(StrEnum):
    not_needed = "not_needed"
    pending = "pending"
    scheduled = "scheduled"
    completed = "completed"
    declined = "declined"


class TechAssistanceStaff(Base):
    __tablename__ = "tech_assistance_staff"

    id = Column(Integer, primary_key=True, index=True)

    # Staff reference
    staff_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    # Topics they can teach (stored as JSON array)
    expertise_topics = Column(ARRAY(String(50)), nullable=False, default=list)
    # Example: ["email", "smartphone", "resume_building"]

    # Maximum concurrent sessions
    max_concurrent_sessions = Column(Integer, default=3)

    # Bio/description for matching
    bio = Column(Text, nullable=True)

    # Languages spoken (e.g., for accessibility)
    languages = Column(ARRAY(String(50)), nullable=True, default=list)

    # Availability (stored as JSON for flexibility)
    # Example: {"monday": {"start": "09:00", "end": "17:00"}, ...}
    availability = Column(JSON, nullable=True)

    # Whether this staff member is available for volunteer tutor coordination
    is_volunteer_coordinator = Column(Boolean, default=False)

    # Status
    is_active = Column(Boolean, default=True)

    # Timestamps, server_default=func.now())

    # Relationships
    staff_user = relationship("User", foreign_keys=[staff_id], backref="tech_expertise")
    bookings = relationship("TechAssistanceBooking", back_populates="assigned_staff")

    __table_args__ = (
        Index("ix_tech_staff_active_topics", "is_active"),
    )


class TechAssistanceBooking(Base):
    __tablename__ = "tech_assistance_bookings"

    id = Column(Integer, primary_key=True, index=True)

    # Patron reference
    patron_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Appointment timing
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)

    # Topic and skill level
    topic = Column(
        SQLEnum(TechTopic, name="techtopic", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False
    )
    skill_level = Column(
        SQLEnum(SkillLevel, name="skilllevel", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=SkillLevel.beginner,
        nullable=False
    )

    # Contact information (for non-logged-in users)
    contact_name = Column(String(255), nullable=True)
    contact_email = Column(String(255), nullable=True, index=True)
    contact_phone = Column(String(50), nullable=True)

    # Booking details
    description = Column(Text, nullable=True)  # What patron wants to learn
    preferred_staff_id = Column(Integer, nullable=True)  # Preferred tutor preference

    # Status
    status = Column(
        SQLEnum(BookingStatus, name="bookingstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=BookingStatus.pending,
        nullable=False
    )

    # Staff assignment and session details
    assigned_staff_id = Column(
        Integer,
        ForeignKey("tech_assistance_staff.id", ondelete="SET NULL"),
        nullable=True
    )

    # Session tracking
    checked_in_at = Column(DateTime(timezone=True), nullable=True)
    session_start_actual = Column(DateTime(timezone=True), nullable=True)
    session_end_actual = Column(DateTime(timezone=True), nullable=True)

    # Cancellation tracking
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancelled_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    cancellation_reason = Column(String(500), nullable=True)

    # Notification tracking
    confirmation_sent_at = Column(DateTime(timezone=True), nullable=True)
    reminder_sent_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    patron = relationship("User", foreign_keys=[patron_id], backref="tech_bookings")
    assigned_staff = relationship("TechAssistanceStaff", back_populates="bookings")
    canceller = relationship("User", foreign_keys=[cancelled_by])
    session_notes = relationship("TechSessionNote", back_populates="booking", cascade="all, delete-orphan")
    resources = relationship("TechResourceHandout", back_populates="booking")
    follow_ups = relationship("TechFollowUpBooking", foreign_keys="[TechFollowUpBooking.original_booking_id]", back_populates="original_booking")
    impact_tracking = relationship("TechSkillImpact", back_populates="booking", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_tech_bookings_patron_status", "patron_id", "status"),
        Index("ix_tech_bookings_staff_status", "assigned_staff_id", "status"),
        Index("ix_tech_bookings_start_time", "start_time"),
        Index("ix_tech_bookings_topic_status", "topic", "status"),
    )


class TechSessionNote(Base):
    __tablename__ = "tech_session_notes"

    id = Column(Integer, primary_key=True, index=True)

    # Booking reference
    booking_id = Column(
        Integer,
        ForeignKey("tech_assistance_bookings.id", ondelete="CASCADE"),
        nullable=False
    )

    # Notes content
    content = Column(Text, nullable=False)

    # What was covered
    topics_covered = Column(ARRAY(String(255)), nullable=True, default=list)

    # Skills/concepts taught
    concepts_taught = Column(ARRAY(String(255)), nullable=True, default=list)

    # Patron understanding level (1-5)
    patron_comprehension_level = Column(Integer, nullable=True)  # 1=minimal, 5=excellent

    # Recommendations for next session
    recommendations = Column(Text, nullable=True)

    # Challenges encountered
    challenges = Column(Text, nullable=True)

    # Staff who took notes
    created_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )

    # Timestamps, server_default=func.now())

    # Relationships
    booking = relationship("TechAssistanceBooking", back_populates="session_notes")
    creator = relationship("User", foreign_keys=[created_by])


class TechFollowUpBooking(Base):
    __tablename__ = "tech_follow_up_bookings"

    id = Column(Integer, primary_key=True, index=True)

    # Reference to original booking
    original_booking_id = Column(
        Integer,
        ForeignKey("tech_assistance_bookings.id", ondelete="CASCADE"),
        nullable=False
    )

    # Reference to follow-up booking (if created)
    follow_up_booking_id = Column(
        Integer,
        ForeignKey("tech_assistance_bookings.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status of follow-up planning
    status = Column(
        SQLEnum(TechFollowUpStatus, name="followupstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=TechFollowUpStatus.not_needed,
        nullable=False
    )

    # Suggested follow-up topics
    suggested_topics = Column(ARRAY(String(255)), nullable=True, default=list)

    # Notes on why follow-up is needed
    reason = Column(Text, nullable=True)

    # Suggested timing for follow-up (e.g., "1 week", "2 weeks")
    suggested_timing = Column(String(100), nullable=True)

    # Patron acceptance of follow-up
    patron_agreed = Column(Boolean, default=False)
    patron_agreed_at = Column(DateTime(timezone=True), nullable=True)

    # Created/updated timestamps, server_default=func.now())

    # Relationships
    original_booking = relationship(
        "TechAssistanceBooking",
        foreign_keys=[original_booking_id],
        back_populates="follow_ups"
    )
    follow_up_booking = relationship(
        "TechAssistanceBooking",
        foreign_keys=[follow_up_booking_id]
    )


class TechResourceHandout(Base):
    __tablename__ = "tech_resource_handouts"

    id = Column(Integer, primary_key=True, index=True)

    # Booking reference
    booking_id = Column(
        Integer,
        ForeignKey("tech_assistance_bookings.id", ondelete="CASCADE"),
        nullable=False
    )

    # Resource details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # Resource location/link
    resource_url = Column(String(500), nullable=True)
    file_path = Column(String(500), nullable=True)  # For locally stored PDFs/handouts

    # Resource type
    resource_type = Column(String(100), nullable=True)  # e.g., "PDF guide", "video link", "website"

    # Topic(s) it covers
    topics = Column(ARRAY(String(100)), nullable=True, default=list)

    # Whether it was sent to patron
    sent_to_patron = Column(Boolean, default=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    sent_method = Column(String(50), nullable=True)  # e.g., "email", "printed"

    # Timestamps, server_default=func.now())

    # Relationships
    booking = relationship("TechAssistanceBooking", back_populates="resources")


class TechSkillImpact(Base):
    __tablename__ = "tech_skill_impact"

    id = Column(Integer, primary_key=True, index=True)

    # Booking reference (one-to-one)
    booking_id = Column(
        Integer,
        ForeignKey("tech_assistance_bookings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Skills learned/improved
    skills_learned = Column(ARRAY(String(255)), nullable=True, default=list)

    # Confidence level pre/post session (1-5)
    confidence_before = Column(Integer, nullable=True)
    confidence_after = Column(Integer, nullable=True)

    # Independence level (1-5, how much patron can do independently)
    independence_level = Column(Integer, nullable=True)

    # Primary goal achieved?
    goal_achieved = Column(Boolean, default=False)

    # Patron-reported satisfaction (1-5)
    satisfaction_rating = Column(Integer, nullable=True)

    # Patron feedback
    patron_feedback = Column(Text, nullable=True)

    # Would patron like to book again?
    interested_in_future_sessions = Column(Boolean, default=False)

    # Follow-up recommendation from staff
    staff_recommendation = Column(Text, nullable=True)

    # Timestamps, server_default=func.now())

    # Relationships
    booking = relationship("TechAssistanceBooking", back_populates="impact_tracking")


class TechVolunteerTutor(Base):
    __tablename__ = "tech_volunteer_tutors"

    id = Column(Integer, primary_key=True, index=True)

    # Volunteer reference
    volunteer_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True
    )

    # Topics they can help with
    expertise_topics = Column(ARRAY(String(50)), nullable=False, default=list)

    # Availability (JSON format)
    availability = Column(JSON, nullable=True)

    # Contact information
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)

    # Background/qualifications
    background = Column(Text, nullable=True)

    # Coordinator relationship
    assigned_coordinator_id = Column(
        Integer,
        ForeignKey("tech_assistance_staff.id", ondelete="SET NULL"),
        nullable=True
    )

    # Status
    is_active = Column(Boolean, default=True)
    approval_status = Column(String(50), default="pending")  # pending, approved, rejected
    approved_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    # Training/certification
    has_background_check = Column(Boolean, default=False)
    training_completed = Column(Boolean, default=False)

    # Statistics
    total_sessions = Column(Integer, default=0)
    average_rating = Column(Float, default=0.0)

    # Timestamps, server_default=func.now())

    # Relationships
    volunteer_user = relationship("User", foreign_keys=[volunteer_id], backref="tech_volunteer_profile")
    coordinator = relationship("TechAssistanceStaff", foreign_keys=[assigned_coordinator_id])
    approver = relationship("User", foreign_keys=[approved_by])
