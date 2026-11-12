# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Index, Integer,
                        String, Text)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...core.database import Base


class CommitteeType(StrEnum):
    STANDING = "standing"  # Permanent committees (e.g., Finance, Policy)
    AD_HOC = "ad_hoc"  # Temporary committees for specific purposes
    ADVISORY = "advisory"  # Advisory committees
    SUBCOMMITTEE = "subcommittee"  # Subcommittee of another committee


class CommitteeStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    DISSOLVED = "dissolved"


class CommitteeMemberRole(StrEnum):
    CHAIR = "chair"
    VICE_CHAIR = "vice_chair"
    SECRETARY = "secretary"
    MEMBER = "member"


class Committee(Base):
    __tablename__ = "board_committees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    committee_type = Column(String(30), nullable=False, default="standing", index=True)
    status = Column(String(30), nullable=False, default="active", index=True)

    description = Column(Text)
    purpose = Column(Text)  # Charter/mission statement
    responsibilities = Column(Text)  # Key responsibilities

    # For subcommittees - link to parent committee
    parent_committee_id = Column(Integer, ForeignKey("board_committees.id", ondelete="SET NULL"), nullable=True)

    # Meeting schedule
    meeting_schedule = Column(String(500))  # e.g., "First Monday of each month at 3:00 PM"
    default_meeting_location = Column(String(500))

    # Governance
    min_members = Column(Integer, default=3)
    max_members = Column(Integer)
    quorum_requirement = Column(Integer, default=2)  # Minimum members for quorum

    # Term limits
    chair_term_months = Column(Integer, default=12)
    member_term_months = Column(Integer, default=24)

    # For ad-hoc committees
    established_date = Column(DateTime(timezone=True))
    dissolution_date = Column(DateTime(timezone=True))
    dissolution_reason = Column(Text)

    # Public visibility
    is_public = Column(Boolean, default=True)
    public_description = Column(Text)  # Public-facing description

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    # Self-referential relationship with lazy loading to prevent circular reference GC issues
    parent_committee = relationship(
        "Committee",
        remote_side=[id],
        back_populates="subcommittees",
        lazy="select"
    )
    subcommittees = relationship(
        "Committee",
        back_populates="parent_committee",
        lazy="select"
    )
    members = relationship("CommitteeMember", back_populates="committee", cascade="all, delete-orphan")
    meetings = relationship("BoardMeeting", back_populates="committee")
    documents = relationship("BoardDocument", back_populates="committee")
    created_by = relationship("User", foreign_keys=[created_by_id])


class CommitteeMember(Base):
    __tablename__ = "board_committee_members"

    id = Column(Integer, primary_key=True, index=True)
    committee_id = Column(
        Integer,
        ForeignKey("board_committees.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    board_member_id = Column(
        Integer,
        ForeignKey("board_members.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    role = Column(String(30), nullable=False, default="member")

    # Term tracking
    appointed_date = Column(DateTime(timezone=True), nullable=False)
    term_end_date = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, index=True)

    # Removal tracking
    removed_date = Column(DateTime(timezone=True))
    removal_reason = Column(Text)
    removed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Notes
    appointment_notes = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Composite index for active member queries per committee
    __table_args__ = (
        Index("ix_committee_members_committee_active", "committee_id", "is_active"),
    )

    # Relationships
    committee = relationship("Committee", back_populates="members")
    board_member = relationship("BoardMember")
    created_by = relationship("User", foreign_keys=[created_by_id])
    removed_by = relationship("User", foreign_keys=[removed_by_id])
