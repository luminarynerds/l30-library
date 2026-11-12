# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from app.models.mixins import TimestampMixin
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base
from .user import UserRole


class Permission(Base, TimestampMixin):

    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(50), nullable=False)

    # Timestamps, server_default=func.now())

    role_permissions = relationship("RolePermission", back_populates="permission")


class RolePermission(Base):

    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]), nullable=False, index=True)
    permission_id = Column(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    # Timestamps, server_default=func.now())

    permission = relationship("Permission", back_populates="role_permissions")


class RoleSettings(Base):

    __tablename__ = "role_settings"

    id = Column(Integer, primary_key=True, index=True)
    role = Column(SQLEnum(UserRole, values_callable=lambda x: [e.value for e in x]), unique=True, nullable=False, index=True)

    # Circulation limits
    max_checkouts = Column(Integer, default=10, nullable=False)
    max_holds = Column(Integer, default=5, nullable=False)
    max_renewals = Column(Integer, default=2, nullable=False)

    # Durations (in days)
    checkout_duration_days = Column(Integer, default=21, nullable=False)
    hold_duration_days = Column(Integer, default=7, nullable=False)

    # Fines
    max_fine_amount = Column(Integer, default=2500, nullable=False)  # in cents
    fine_exempt = Column(Boolean, default=False, nullable=False)

    # Reading minutes (for children - alternative to fines)
    use_reading_minutes = Column(Boolean, default=False, nullable=False)
    minutes_per_day_overdue = Column(Integer, default=10, nullable=False)
    max_reading_minutes_owed = Column(Integer, default=60, nullable=False)

    # Access flags
    can_use_digital_resources = Column(Boolean, default=True, nullable=False)
    can_access_adult_content = Column(Boolean, default=True, nullable=False)
    can_book_meeting_rooms = Column(Boolean, default=False, nullable=False)
    can_use_3d_printer = Column(Boolean, default=False, nullable=False)

    # Special settings
    requires_guardian = Column(Boolean, default=False, nullable=False)
    home_delivery_eligible = Column(Boolean, default=False, nullable=False)

    # Timestamps, server_default=func.now())
