# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import (
    Boolean, Column, ForeignKey, Index, Integer, String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class AgeRange(StrEnum):
    age_0_5 = "0-5"
    age_6_8 = "6-8"
    age_9_12 = "9-12"
    age_13_17 = "13-17"


class ProgramFamilyGroup(Base, TimestampMixin):
    __tablename__ = "program_family_groups"

    id = Column(Integer, primary_key=True, index=True)
    parent_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name = Column(String(200), nullable=False)

    # Relationships
    parent = relationship("User", foreign_keys=[parent_user_id], backref="family_groups")
    members = relationship(
        "ProgramFamilyMember",
        back_populates="family_group",
        cascade="all, delete-orphan",
        lazy="select",
    )

    __table_args__ = (
        UniqueConstraint("parent_user_id", name="uq_family_group_parent"),
    )


class ProgramFamilyMember(Base, TimestampMixin):
    __tablename__ = "program_family_members"

    id = Column(Integer, primary_key=True, index=True)
    family_group_id = Column(
        Integer,
        ForeignKey("program_family_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    first_name = Column(String(100), nullable=False)
    age_range = Column(String(10), nullable=False)
    is_parent = Column(Boolean, default=False, nullable=False)
    participant_id = Column(
        Integer,
        ForeignKey("reading_registrations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    family_group = relationship("ProgramFamilyGroup", back_populates="members")
    participant = relationship("ReadingRegistration", foreign_keys=[participant_id])

    __table_args__ = (
        Index("ix_family_members_group", "family_group_id"),
    )
