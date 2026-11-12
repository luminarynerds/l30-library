# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import uuid

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..core.database import Base


class ParentOnboardingExportLog(Base):

    __tablename__ = "parent_onboarding_export_log"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Requester. SET NULL on user delete so the audit row survives.
    exported_by_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    exported_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    format = Column(String(8), nullable=False)  # 'csv' | 'pdf'
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    # Scope, not requester: which coordinator's activity was in the report.
    # NULL means whole-team report.
    coordinator_id = Column(Integer, nullable=True)
    row_count = Column(Integer, nullable=False)

    exported_by = relationship("User", foreign_keys=[exported_by_id])

    __table_args__ = (
        CheckConstraint(
            "format IN ('csv', 'pdf')",
            name="ck_parent_onboarding_export_log_format",
        ),
        Index(
            "ix_parent_onboarding_export_log_exported_at",
            "exported_at",
        ),
    )
