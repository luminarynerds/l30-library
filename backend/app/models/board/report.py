# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from enum import StrEnum
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String,
                        Text, Float)
from sqlalchemy.dialects.postgresql import JSONB, BYTEA
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...core.database import Base


class ReportStatus(StrEnum):
    DRAFT = "draft"
    GENERATED = "generated"
    SCHEDULED = "scheduled"
    SENT = "sent"
    ARCHIVED = "archived"


class ReportFormat(StrEnum):
    POWERPOINT = "powerpoint"
    PDF = "pdf"
    BOTH = "both"


class ReportFrequency(StrEnum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUALLY = "annually"
    ON_DEMAND = "on_demand"


class BoardReport(Base):
    __tablename__ = "board_reports"

    id = Column(Integer, primary_key=True, index=True)

    # Report metadata
    title = Column(String(500), nullable=False)
    description = Column(Text)
    report_period_start = Column(DateTime(timezone=True), nullable=False, index=True)
    report_period_end = Column(DateTime(timezone=True), nullable=False, index=True)
    comparison_period_start = Column(DateTime(timezone=True))
    comparison_period_end = Column(DateTime(timezone=True))

    # Configuration
    template_id = Column(Integer, ForeignKey("board_report_templates.id", ondelete="SET NULL"), nullable=True)
    status = Column(String(20), nullable=False, default="draft", index=True)
    frequency = Column(String(20), nullable=False, default="monthly")

    # Generated content
    file_powerpoint = Column(BYTEA)  # Stored PowerPoint file
    file_pdf = Column(BYTEA)  # Stored PDF file
    format_generated = Column(String(10), nullable=False, default="both")

    # Statistics snapshot
    stats_snapshot = Column(JSONB)  # JSON snapshot of all stats used in report

    # Narrative content
    executive_summary = Column(Text)  # Generated or manually added narrative
    key_metrics = Column(JSONB)  # Highlighted key metrics with trends
    narrative_prompts = Column(JSONB)  # Prompts for board members to add context

    # Email distribution
    recipient_emails = Column(JSONB)  # List of board member emails
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True))
    email_status = Column(String(50))  # "sent", "failed", "pending"
    email_error_message = Column(Text)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    generated_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Relationships
    template = relationship("BoardReportTemplate", back_populates="reports")

    # Audit
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    last_updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class BoardReportTemplate(Base):
    __tablename__ = "board_report_templates"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False, unique=True, index=True)
    description = Column(Text)
    is_default = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True, index=True)

    # Template configuration
    include_sections = Column(JSONB, nullable=False)  # {"circulation": true, "financial": true, ...}
    colors = Column(JSONB)  # Custom color scheme
    logo_url = Column(String(1000))  # Custom organization logo
    branding = Column(JSONB)  # Font, styling preferences

    # Custom content
    header_text = Column(Text)
    footer_text = Column(Text)
    custom_css = Column(Text)  # For PDF styling

    # Chart preferences
    chart_config = Column(JSONB)  # Chart types, size, placement

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    # Relationships
    reports = relationship("BoardReport", back_populates="template")


class BoardReportSchedule(Base):
    __tablename__ = "board_report_schedules"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, index=True)

    # Schedule configuration
    frequency = Column(String(20), nullable=False)  # "monthly", "quarterly", "annually"
    day_of_month = Column(Integer)  # 1-31 for monthly
    day_of_week = Column(Integer)  # 0-6 (Monday-Sunday)
    time_of_day = Column(String(5))  # "HH:MM" format, e.g., "09:00"

    # Template to use
    template_id = Column(Integer, ForeignKey("board_report_templates.id", ondelete="SET NULL"), nullable=True)

    # Recipients
    recipient_user_ids = Column(JSONB)  # List of user IDs to receive report
    recipient_emails = Column(JSONB)  # Additional email addresses

    # Report options
    report_format = Column(String(10), nullable=False, default="both")  # "powerpoint", "pdf", "both"
    include_comparison = Column(Boolean, default=True)

    # Last execution
    last_run_at = Column(DateTime(timezone=True))
    next_run_at = Column(DateTime(timezone=True), index=True)
    last_status = Column(String(50))  # "success", "failed", "pending"
    last_error = Column(Text)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
