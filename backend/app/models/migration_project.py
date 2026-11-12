# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import enum

from enum import Enum, StrEnum
from sqlalchemy import (
    Column, DateTime, Integer, String, Text,
    Enum as SQLEnum, ForeignKey, JSON, UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.models.mixins import TimestampMixin


class MigrationPhase(StrEnum):
    ASSESSMENT = "assessment"
    CATALOG = "catalog"
    HOLDINGS = "holdings"
    PATRONS = "patrons"
    ACTIVE_CIRCULATION = "active_circulation"
    HISTORICAL_DATA = "historical_data"


class MigrationPhaseStatus(StrEnum):
    LOCKED = "locked"
    READY = "ready"
    UPLOADING = "uploading"
    VALIDATING = "validating"
    VALIDATED = "validated"
    DRY_RUN = "dry_run"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class MigrationProjectStatus(StrEnum):
    CREATED = "created"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CutoverStrategy(StrEnum):
    BIG_BANG = "big_bang"
    PARALLEL_RUN = "parallel_run"


class MigrationProject(Base, TimestampMixin):

    __tablename__ = "migration_projects"

    id = Column(Integer, primary_key=True, index=True)

    # Project metadata
    name = Column(String(255), nullable=False)
    status = Column(
        SQLEnum(MigrationProjectStatus, name="migrationprojectstatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MigrationProjectStatus.CREATED,
        index=True,
    )
    cutover_strategy = Column(
        SQLEnum(CutoverStrategy, name="cutoverstrategy", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )

    # Source system info
    source_system_name = Column(String(255), nullable=True)
    source_system_type = Column(String(50), nullable=True)

    # Size estimates
    estimated_catalog_size = Column(Integer, nullable=True)
    estimated_patron_count = Column(Integer, nullable=True)

    # Notes and reports
    notes = Column(Text, nullable=True)
    assessment_report = Column(JSON, nullable=True)
    final_report = Column(JSON, nullable=True)

    # Audit
    created_by_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    created_by = relationship(
        "User", foreign_keys=[created_by_id], backref="migration_projects"
    )
    phases = relationship(
        "MigrationProjectPhase", back_populates="project", cascade="all, delete-orphan",
        order_by="MigrationProjectPhase.id",
    )


class MigrationProjectPhase(Base, TimestampMixin):

    __tablename__ = "migration_project_phases"
    __table_args__ = (
        UniqueConstraint("project_id", "phase", name="uq_project_phase"),
    )

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer, ForeignKey("migration_projects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    phase = Column(
        SQLEnum(MigrationPhase, name="migrationphase", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    status = Column(
        SQLEnum(MigrationPhaseStatus, name="migrationphasestatus", create_type=False, values_callable=lambda x: [e.value for e in x]),
        default=MigrationPhaseStatus.LOCKED,
    )

    # Link to the ImportJob that handles actual data processing
    import_job_id = Column(
        Integer, ForeignKey("import_jobs.id", ondelete="SET NULL"), nullable=True
    )

    # Progress counters
    total_records = Column(Integer, default=0, nullable=False)
    created_records = Column(Integer, default=0, nullable=False)
    error_records = Column(Integer, default=0, nullable=False)
    skipped_records = Column(Integer, default=0, nullable=False)

    # Error details
    error_log = Column(JSON, nullable=True)

    # Timing
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    project = relationship("MigrationProject", back_populates="phases")
    import_job = relationship("ImportJob", foreign_keys=[import_job_id])

    @property
    def progress_percent(self) -> float:
        if self.total_records == 0:
            return 0.0
        return round((self.created_records / self.total_records) * 100, 1)

    @property
    def is_complete(self) -> bool:
        return self.status in (
            MigrationPhaseStatus.COMPLETED,
            MigrationPhaseStatus.FAILED,
            MigrationPhaseStatus.ROLLED_BACK,
        )
