# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum
from enum import Enum, StrEnum
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Integer, String, Text,
    Enum as SQLEnum, ForeignKey, JSON,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MigrationSourceSystem(StrEnum):
    SIRSI = "sirsi"
    KOHA = "koha"
    GENERIC_CSV = "csv"


class MigrationJobStatus(StrEnum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    READY = "ready"
    MAPPING = "mapping"
    DRY_RUN = "dry_run"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationJob(Base, TimestampMixin):

    __tablename__ = "migration_jobs"

    id = Column(Integer, primary_key=True, index=True)

    # Job configuration
    status = Column(
        SQLEnum(MigrationJobStatus, name="migrationjobstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MigrationJobStatus.PENDING,
        index=True,
    )
    source_system = Column(
        SQLEnum(MigrationSourceSystem, name="migrationsourcesystem", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )

    # File info
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(Integer, nullable=True)

    # Progress tracking
    total_rows = Column(Integer, default=0, nullable=False)
    processed_rows = Column(Integer, default=0, nullable=False)
    failed_rows = Column(Integer, default=0, nullable=False)

    # User's field mapping: {source_column: lsc_field, ...}
    field_mapping = Column(JSON, nullable=True)

    # Migration options: {migrate_patrons, migrate_catalog, migrate_checkouts, migrate_fines, ...}
    options = Column(JSON, nullable=True)

    # Analysis report from file inspection
    analysis_report = Column(JSON, nullable=True)

    # Dry-run results: {would_create, would_update, would_skip, sample_records, ...}
    dry_run_report = Column(JSON, nullable=True)

    # Per-row errors: [{row, field, message}, ...]
    error_log = Column(JSON, nullable=True)

    # Audit trail
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    rollback_available_until = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    created_by = relationship(
        "User", foreign_keys=[created_by_id], backref="migration_jobs"
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
        return round((self.failed_rows / self.total_rows) * 100, 1)

    @property
    def is_complete(self) -> bool:
        return self.status in (
            MigrationJobStatus.COMPLETED,
            MigrationJobStatus.FAILED,
            MigrationJobStatus.ROLLED_BACK,
        )
