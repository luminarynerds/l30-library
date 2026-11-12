# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ReportGenerationLog(Base):

    __tablename__ = "report_generation_log"

    __table_args__ = (
        Index("ix_rpt_gen_log_generated_at", "generated_at"),
        Index("ix_rpt_gen_log_type_at", "report_type", "generated_at"),
        Index("ix_rpt_gen_log_user_at", "generated_by_id", "generated_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(80), nullable=False)
    format = Column(String(20), nullable=False)
    date_range_start = Column(DateTime(timezone=True), nullable=True)
    date_range_end = Column(DateTime(timezone=True), nullable=True)
    generated_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    generated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    duration_ms = Column(Integer, nullable=True)
    record_count = Column(Integer, nullable=True)
    cache_hit = Column(Boolean, nullable=False, default=False)

    generated_by = relationship("User", foreign_keys=[generated_by_id])

    def __repr__(self) -> str:
        return (
            f"<ReportGenerationLog(id={self.id}, type={self.report_type}, "
            f"by={self.generated_by_id}, at={self.generated_at})>"
        )
