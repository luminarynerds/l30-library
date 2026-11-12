# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text,
    Enum as SQLEnum, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class ImportJobType(StrEnum):
    PATRONS = "patrons"
    CATALOG_ITEMS = "catalog_items"
    HOLDINGS = "holdings"
    MARC_RECORDS = "marc_records"
    CIRCULATION_HISTORY = "circulation_history"
    FINES = "fines"
    HOLDS = "holds"
    POLICIES = "policies"


class ImportJobStatus(StrEnum):
    PENDING = "pending"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DRY_RUN = "dry_run"
    IMPORTING = "importing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"


class ImportFileFormat(StrEnum):
    CSV = "csv"
    MARC21 = "marc21"
    MARCXML = "marcxml"
    JSON = "json"


class DuplicateAction(StrEnum):
    SKIP = "skip"
    MERGE = "merge"
    CREATE_NEW = "create_new"


class ImportJob(Base, TimestampMixin):

    __tablename__ = "import_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Job configuration
    job_type = Column(
        SQLEnum(ImportJobType, name="importjobtype", create_type=False, values_callable=lambda x: [e.value for e in x]),
    )
    file_format = Column(
        SQLEnum(ImportFileFormat, name="importfileformat", create_type=False, values_callable=lambda x: [e.value for e in x]),
    )
    status = Column(
        SQLEnum(ImportJobStatus, name="importjobstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ImportJobStatus.PENDING,
    )

    # File info
    source_filename = Column(String(500), nullable=False)
    source_file_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)

    # Progress tracking
    total_rows = Column(Integer, default=0, nullable=False)
    processed_rows = Column(Integer, default=0, nullable=False)
    created_rows = Column(Integer, default=0, nullable=False)
    updated_rows = Column(Integer, default=0, nullable=False)
    skipped_rows = Column(Integer, default=0, nullable=False)
    error_rows = Column(Integer, default=0, nullable=False)

    # Validation report: {errors: [{row, field, message}], warnings: [{row, field, message}]}
    validation_report = Column(JSON, nullable=True)

    # Dry run results: {would_create, would_update, would_skip, sample_records}
    dry_run_report = Column(JSON, nullable=True)

    # Column mapping: {source_column: target_field, ...}
    column_mapping = Column(JSON, nullable=True)

    # Duplicate handling preference
    duplicate_action = Column(
        SQLEnum(DuplicateAction, name="duplicateaction", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=DuplicateAction.SKIP,
    )

    # Error threshold: percentage of errors that triggers auto-rollback (0-100)
    error_threshold = Column(Float, default=10.0, nullable=False)

    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Rollback tracking
    rolled_back_at = Column(DateTime(timezone=True), nullable=True)
    rolled_back_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    rollback_reason = Column(String(500), nullable=True)

    # Relationships
    created_by = relationship(
        "User", foreign_keys=[created_by_id], backref="import_jobs"
    )
    rolled_back_by = relationship(
        "User", foreign_keys=[rolled_back_by_id]
    )
    records = relationship(
        "ImportRecord", back_populates="import_job", cascade="all, delete-orphan"
    )

    @property
    def progress_percent(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round((self.processed_rows / self.total_rows) * 100, 1)

    @property
    def error_percent(self) -> float:
        if self.total_rows == 0:
            return 0.0
        return round((self.error_rows / self.total_rows) * 100, 1)

    @property
    def is_complete(self) -> bool:
        return self.status in (
            ImportJobStatus.COMPLETED,
            ImportJobStatus.FAILED,
            ImportJobStatus.ROLLED_BACK,
            ImportJobStatus.CANCELLED,
        )


class ImportRecordStatus(StrEnum):
    PENDING = "pending"
    VALID = "valid"
    WARNING = "warning"
    INVALID = "invalid"
    CREATED = "created"
    UPDATED = "updated"
    SKIPPED = "skipped"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class ImportRecord(Base, TimestampMixin):

    __tablename__ = "import_records"

    id = Column(Integer, primary_key=True, index=True)

    import_job_id = Column(
        Integer, ForeignKey("import_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    row_number = Column(Integer, nullable=False)

    status = Column(
        SQLEnum(ImportRecordStatus, name="importrecordstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=ImportRecordStatus.PENDING,
    )

    # Source data from the file (JSON)
    source_data = Column(JSON, nullable=True)

    # What was created - for rollback
    target_table = Column(String(100), nullable=True)
    target_id = Column(Integer, nullable=True)

    # Validation / error details
    errors = Column(JSON, nullable=True)  # [{field, message, severity}]
    warnings = Column(JSON, nullable=True)

    # Duplicate detection
    is_duplicate = Column(Boolean, default=False, nullable=False)
    duplicate_of_id = Column(Integer, nullable=True)
    duplicate_score = Column(Float, nullable=True)

    # Relationships
    import_job = relationship("ImportJob", back_populates="records")
