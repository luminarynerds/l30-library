# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer,
                        String, Text)
from sqlalchemy.sql import func
from app.models.mixins import TimestampMixin

from ..core.database import Base


class StaffBio(Base, TimestampMixin):

    __tablename__ = "staff_bios"

    id = Column(Integer, primary_key=True, index=True)
    staff_name = Column(String(100), nullable=False)
    role = Column(String(100), nullable=False)
    bio = Column(Text, nullable=False)

    # Optional fields
    photo_url = Column(String(500), nullable=True)
    fun_fact = Column(String(500), nullable=True)
    favorite_book = Column(String(200), nullable=True)
    years_of_service = Column(Integer, nullable=True)

    # Display
    is_visible = Column(Boolean, default=True, nullable=False)
    sort_order = Column(Integer, default=0, nullable=False)

    # Link to user account (optional)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<StaffBio(staff_name='{self.staff_name}', role='{self.role}')>"

