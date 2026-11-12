# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class TeacherApplicationStatus(StrEnum):
    pending = "pending"
    approved = "approved"
    denied = "denied"


class TeacherApplication(Base):

    __tablename__ = "teacher_applications"

    id = Column(Integer, primary_key=True, index=True)

    # The PATRON user submitting the application. Required: there is no
    # anonymous path -- the user account is created first, application is a
    # separate row referencing the user (per project_l30 patron-signup-approval
    # memory).
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Applicant-declared school. Optional at submit; librarian can set during
    # approval if the user didn't pick one (e.g. school not yet in
    # outreach_partners). Stored as FK to outreach_partners with
    # ondelete=SET NULL so partner deletion doesn't cascade-kill the
    # application history.
    school_id = Column(
        Integer,
        ForeignKey("outreach_partners.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Free-text school name when the user can't find their school in the
    # dropdown -- librarian uses this to create / link an outreach_partner.
    school_name_freetext = Column(String(255), nullable=True)

    # Teaching context
    grade_level = Column(String(100), nullable=True)  # free text: "K-2", "6th", "high school", etc
    subject = Column(String(255), nullable=True)      # "math", "reading", etc
    classroom_size = Column(Integer, nullable=True)

    # Applicant notes / pitch (why they want a teacher card, planned use)
    notes = Column(Text, nullable=True)

    # Status workflow
    status = Column(
        SQLEnum(
            TeacherApplicationStatus,
            name="teacherapplicationstatus",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        default=TeacherApplicationStatus.pending,
        nullable=False,
        index=True,
    )

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    review_notes = Column(Text, nullable=True)
    denial_reason = Column(Text, nullable=True)

    # Relationships
    user = relationship("User", foreign_keys=[user_id], backref="teacher_applications")
    reviewer = relationship("User", foreign_keys=[reviewed_by_id])
    school = relationship("OutreachPartner", foreign_keys=[school_id], lazy="select")

    __table_args__ = (
        Index("ix_teacher_applications_status_created", "status", "created_at"),
        Index("ix_teacher_applications_user_status", "user_id", "status"),
    )

    @property
    def is_pending(self) -> bool:
        return self.status == TeacherApplicationStatus.pending

    @property
    def is_approved(self) -> bool:
        return self.status == TeacherApplicationStatus.approved

    @property
    def is_denied(self) -> bool:
        return self.status == TeacherApplicationStatus.denied
