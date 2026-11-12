# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Boolean, Column, Date, DateTime, ForeignKey, Integer, SmallInteger,
    String, Time, CheckConstraint,
)
from sqlalchemy.sql import func

from ..core.database import Base


class HomepageQuickLink(Base):

    __tablename__ = "homepage_quick_links"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String(100), nullable=False)
    icon = Column(String(50), nullable=False, default="link")
    url = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False, default=0)
    is_active = Column(Boolean, nullable=False, default=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class LibraryHours(Base):

    __tablename__ = "library_hours"

    id = Column(Integer, primary_key=True, index=True)
    day_of_week = Column(SmallInteger, nullable=False, unique=True)
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)
    is_closed = Column(Boolean, nullable=False, default=False)
    label = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        CheckConstraint("day_of_week BETWEEN 0 AND 6", name="ck_library_hours_day"),
    )


class LibraryHoursOverride(Base):

    __tablename__ = "library_hours_overrides"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    open_time = Column(Time, nullable=True)
    close_time = Column(Time, nullable=True)
    is_closed = Column(Boolean, nullable=False, default=False)
    reason = Column(String(200), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
