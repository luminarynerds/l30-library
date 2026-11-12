# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from ..core.database import Base


class UnifiedReportSchedule(Base):
    __tablename__ = "unified_report_schedules"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    # What to generate
    report_type = Column(String(50), nullable=False, index=True)  # e.g. "circulation"
    output_format = Column(String(10), nullable=False, default="pdf")  # csv, excel, pdf

    # When to generate
    frequency = Column(String(20), nullable=False)  # daily, weekly, monthly
    day_of_week = Column(Integer)  # 0-6 (Mon-Sun) for weekly
    day_of_month = Column(Integer)  # 1-31 for monthly
    time_of_day = Column(String(5), nullable=False, default="08:00")  # HH:MM

    # Filters applied to the report
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)

    # Who gets it
    recipient_emails = Column(JSONB, nullable=False, default=list)

    # Execution tracking
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True), index=True)
    last_status = Column(String(50))  # success, failed
    last_error = Column(Text)

    # Audit
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
