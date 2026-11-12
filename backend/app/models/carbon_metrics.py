# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Column, Integer, String, DateTime, Numeric, BigInteger, Index
from sqlalchemy.sql import func

from app.core.database import Base


class CarbonMetric(Base):

    __tablename__ = "carbon_metrics"

    id = Column(Integer, primary_key=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    period_type = Column(String(20), nullable=False)
    section = Column(String(50), nullable=False)

    total_bytes = Column(BigInteger, nullable=False, default=0)
    request_count = Column(Integer, nullable=False, default=0)
    estimated_co2_grams = Column(Numeric(12, 4), nullable=False, default=0)
    avg_bytes_per_request = Column(Numeric(12, 2), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_carbon_metrics_period", "period_start", "period_end"),
        Index("ix_carbon_metrics_section_period", "section", "period_start"),
        Index("ix_carbon_metrics_type_period", "period_type", "period_start"),
    )
