# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from enum import StrEnum
from typing import Optional

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text, UniqueConstraint)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class TagColor(StrEnum):
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"
    PURPLE = "purple"
    PINK = "pink"
    TEAL = "teal"
    GRAY = "gray"


class Tag(Base):
    __tablename__ = "patron_tags_definitions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True)
    color = Column(String(20), nullable=False, default=TagColor.BLUE.value)
    description = Column(String(255), nullable=True)
    is_custom = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    patron_tags = relationship("PatronTag", back_populates="tag", cascade="all, delete-orphan")


class PatronTag(Base):
    __tablename__ = "patron_tags"

    id = Column(Integer, primary_key=True, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    tag_id = Column(Integer, ForeignKey("patron_tags_definitions.id", ondelete="CASCADE"), nullable=False, index=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    notes = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("patron_id", "tag_id", name="uq_patron_tag"),
    )

    # Relationships
    tag = relationship("Tag", back_populates="patron_tags")
    patron = relationship("User", foreign_keys=[patron_id])
    assigned_by = relationship("User", foreign_keys=[assigned_by_id])


class PatronGroup(Base):
    __tablename__ = "patron_groups"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Group settings
    allow_self_join = Column(Boolean, default=False, nullable=False)
    max_members = Column(Integer, nullable=True)  # NULL = unlimited

    # Relationships
    members = relationship("PatronGroupMember", back_populates="group", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_id])


class PatronGroupMember(Base):
    __tablename__ = "patron_group_members"

    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("patron_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    patron_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    joined_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    added_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    role = Column(String(50), nullable=True)  # e.g., "leader", "member"
    notes = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("group_id", "patron_id", name="uq_group_patron"),
    )

    # Relationships
    group = relationship("PatronGroup", back_populates="members")
    patron = relationship("User", foreign_keys=[patron_id])
    added_by = relationship("User", foreign_keys=[added_by_id])


# Pre-defined system tags that should be seeded
SYSTEM_TAGS = [
    {"name": "Senior", "color": TagColor.PURPLE.value, "description": "Senior citizen patron (65+)", "is_custom": False},
    {"name": "Student", "color": TagColor.BLUE.value, "description": "Student patron", "is_custom": False},
    {"name": "Staff", "color": TagColor.GREEN.value, "description": "Library staff member", "is_custom": False},
    {"name": "Teacher", "color": TagColor.TEAL.value, "description": "Teacher or educator", "is_custom": False},
    {"name": "Volunteer", "color": TagColor.ORANGE.value, "description": "Library volunteer", "is_custom": False},
    {"name": "VIP", "color": TagColor.YELLOW.value, "description": "VIP patron", "is_custom": False},
    {"name": "New Member", "color": TagColor.PINK.value, "description": "Recently joined patron", "is_custom": False},
]
