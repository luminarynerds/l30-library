# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from app.models.mixins import TimestampMixin
from sqlalchemy import Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class CohortMemberRole(StrEnum):
    MEMBER = "member"
    LEAD = "lead"
    ADMIN = "admin"


class CohortMemberStatus(StrEnum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    PENDING = "pending"


class Cohort(Base, TimestampMixin):
    __tablename__ = "cohorts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    tags = Column(JSONB, default=list, nullable=False)
    created_by = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    members = relationship(
        "CohortMember", back_populates="cohort", cascade="all, delete-orphan"
    )
    trainings = relationship(
        "CohortTraining", back_populates="cohort", cascade="all, delete-orphan"
    )


class CohortMember(Base):
    __tablename__ = "cohort_members"

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(
        Integer, ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(
        SQLEnum(CohortMemberRole, values_callable=lambda x: [e.value for e in x]), default=CohortMemberRole.MEMBER, nullable=False
    )
    status = Column(
        SQLEnum(CohortMemberStatus, values_callable=lambda x: [e.value for e in x]), default=CohortMemberStatus.ACTIVE, nullable=False
    )
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    cohort = relationship("Cohort", back_populates="members")
    user = relationship("User")


class CohortTraining(Base):
    __tablename__ = "cohort_trainings"

    id = Column(Integer, primary_key=True, index=True)
    cohort_id = Column(
        Integer, ForeignKey("cohorts.id", ondelete="CASCADE"), nullable=False
    )
    course_id = Column(
        Integer, ForeignKey("courses.id", ondelete="CASCADE"), nullable=False
    )
    due_date = Column(DateTime(timezone=True), nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    cohort = relationship("Cohort", back_populates="trainings")
    course = relationship("Course")
