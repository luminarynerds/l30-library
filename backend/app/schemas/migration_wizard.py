# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


class FieldMappingRequest(StrictInputSchema):
    mapping: dict[str, str] = Field(..., description="Source column -> L30 field name mapping")


class MigrationOptionsRequest(StrictInputSchema):
    migrate_patrons: bool = True
    migrate_catalog: bool = True
    migrate_checkouts: bool = False
    migrate_fines: bool = False


class AnalysisReport(BaseModel):
    detected_columns: list[str] = Field(default_factory=list, description="Columns found in file")
    total_rows: int
    sample_rows: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggested_mapping: dict[str, str] = Field(default_factory=dict, description="Recommended field mapping")
    source_system_detected: str = Field(description="Detected source system (sirsi/koha/csv)")


class DryRunReport(BaseModel):
    would_create: int
    would_update: int
    would_skip: int
    sample_records: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validation_errors: list[dict[str, Any]] = Field(default_factory=list)


class MigrationJobResponse(BaseModel):
    id: int
    status: str
    source_system: str
    original_filename: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    progress_percent: float
    error_percent: float
    field_mapping: Optional[dict[str, str]] = None
    options: Optional[dict[str, Any]] = None
    analysis_report: Optional[dict[str, Any]] = None
    dry_run_report: Optional[dict[str, Any]] = None
    error_log: Optional[dict[str, Any]] = None
    created_by_id: Optional[int] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MigrationProgressResponse(BaseModel):
    job_id: int
    status: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    progress_percent: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    is_complete: bool = False


class MigrationHistoryItem(BaseModel):
    id: int
    source_system: str
    original_filename: str
    status: str
    total_rows: int
    processed_rows: int
    failed_rows: int
    created_at: datetime | None = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MigrationHistoryResponse(BaseModel):
    items: list[MigrationHistoryItem]
    total: int
    limit: int
    offset: int
