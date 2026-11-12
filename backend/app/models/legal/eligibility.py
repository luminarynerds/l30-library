# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ...core.database import Base


class LegalEligibilityThreshold(Base):
    __tablename__ = "legal_eligibility_thresholds"

    id = Column(Integer, primary_key=True, index=True)
    provider_id = Column(
        Integer, ForeignKey("legal_service_providers.id", ondelete="CASCADE"),
        nullable=False, index=True
    )
    household_size = Column(Integer, nullable=False)  # 1-8, where 8 = "8+"
    income_limit = Column(Integer, nullable=False)  # Annual dollar amount
    percentage_of_fpl = Column(Integer, nullable=False)  # e.g. 125, 200
    effective_date = Column(Date, nullable=False)
    expires_date = Column(Date, nullable=True)  # NULL = current
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    provider = relationship("LegalServiceProvider")
    created_by = relationship("User", foreign_keys=[created_by_id])
