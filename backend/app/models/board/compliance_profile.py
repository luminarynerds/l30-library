# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from ..mixins import TimestampMixin
from ...core.database import Base


class BoardStateComplianceProfile(Base, TimestampMixin):
    __tablename__ = "board_state_compliance_profiles"

    id = Column(Integer, primary_key=True, index=True)
    state_code = Column(String(2), nullable=False, unique=True, index=True)
    state_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, default=False, index=True)

    # Open meeting law
    notice_lead_hours = Column(Integer, nullable=False)
    emergency_notice_rule = Column(String(500))
    open_meeting_law_citation = Column(String(500))
    permitted_exec_session_reasons = Column(JSONB, default=list)

    # Public records law
    public_records_law_name = Column(String(200))
    public_records_response_days = Column(Integer)
    public_records_law_citation = Column(String(500))

    # Retention defaults
    minutes_retention = Column(String(50), default="permanent")
    resolution_retention = Column(String(50), default="permanent")

    # Configuration audit
    configured_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    configured_at = Column(DateTime(timezone=True), server_default=func.now())

    configured_by = relationship("User", foreign_keys=[configured_by_id])
