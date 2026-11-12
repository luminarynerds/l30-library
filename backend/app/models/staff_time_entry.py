# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum

from sqlalchemy import Column, Date, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class TimeEntryType(StrEnum):
    CLOCK_IN = "clock_in"
    CLOCK_OUT = "clock_out"
    BREAK_START = "break_start"
    BREAK_END = "break_end"


class StaffTimeEntry(Base):
    __tablename__ = "staff_time_entries"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    entry_type = Column(
        SQLEnum(TimeEntryType, name="timeentrytype", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    recorded_at = Column(DateTime(timezone=True), nullable=False)
    shift_date = Column(Date, nullable=False, index=True)
    staff_shift_id = Column(Integer, ForeignKey("staff_shifts.id", ondelete="SET NULL"), nullable=True)
    duration_minutes = Column(Float, nullable=True)
    notes = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    staff = relationship("User", foreign_keys=[staff_id])

    __table_args__ = (
        Index("ix_time_entries_staff_date", "staff_id", "shift_date"),
    )
