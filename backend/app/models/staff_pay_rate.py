# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import (
    CheckConstraint, Column, Date, DateTime, ForeignKey, Integer,
    Numeric, Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class StaffPayRate(Base):
    __tablename__ = "staff_pay_rates"

    id = Column(Integer, primary_key=True, index=True)
    staff_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    hourly_rate = Column(Numeric(10, 4), nullable=False)
    effective_from = Column(Date, nullable=False)
    effective_to = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    staff = relationship("User", foreign_keys=[staff_id])
    created_by = relationship("User", foreign_keys=[created_by_id])

    __table_args__ = (
        CheckConstraint("hourly_rate > 0", name="ck_staff_pay_rates_positive"),
    )
