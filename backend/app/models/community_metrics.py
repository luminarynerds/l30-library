# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class CommunityMetricsSnapshot(Base):

    __tablename__ = "community_metrics_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    period_type = Column(String(20), nullable=False)
    category = Column(String(50), nullable=False)
    metrics = Column(JSONB, nullable=False, default=dict)
    computed_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    branch_id = Column(Integer, ForeignKey("branches.id", ondelete="SET NULL"), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "period_start", "period_end", "period_type", "category", "branch_id",
            name="uq_cms_period_category_branch",
        ),
        Index("ix_cms_period", "period_type", "period_start", "period_end"),
        Index("ix_cms_category", "category"),
        Index("ix_cms_branch", "branch_id"),
    )
