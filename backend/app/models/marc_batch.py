# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from enum import StrEnum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MarcBatchJobType(StrEnum):
    import_job = "import"
    export_job = "export"


class MarcBatchJobStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class MarcBatchJob(Base, TimestampMixin):
    __tablename__ = "marc_batch_jobs"

    id = Column(Integer, primary_key=True, index=True)
    job_type = Column(
        String(50),
        nullable=False,
    )
    status = Column(
        String(50),
        nullable=False, default=MarcBatchJobStatus.pending,
    )
    file_name = Column(String(500), nullable=True)
    file_format = Column(String(20), nullable=True)  # "marc21", "marcxml"
    total_records = Column(Integer, default=0)
    processed = Column(Integer, default=0)
    created_count = Column(Integer, default=0)
    updated_count = Column(Integer, default=0)
    skipped = Column(Integer, default=0)
    errors = Column(JSONB, default=[])  # [{record_index, error_message}]
    filter_criteria = Column(JSONB, nullable=True)  # For exports: {item_type, date_from, date_to}
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    created_by = relationship("User", foreign_keys=[created_by_id])
