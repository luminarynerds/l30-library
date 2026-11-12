# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# ── Enums re-exported for schema use ──────────────────────────────────────
from app.models.import_job import (
    ImportJobType,
    ImportJobStatus,
    ImportFileFormat,
    DuplicateAction,
    ImportRecordStatus,
)
from ._base import StrictInputSchema


# ── Request schemas ───────────────────────────────────────────────────────

class ImportUploadRequest(StrictInputSchema):
    job_type: ImportJobType
    duplicate_action: DuplicateAction = DuplicateAction.SKIP
    error_threshold: float = Field(
        default=10.0, ge=0, le=100,
        description="Error % that triggers auto-rollback",
    )


class ColumnMappingRequest(StrictInputSchema):
    mapping: dict[str, str] = Field(
        ...,
        description="Map of source column name → target field name",
    )


class ImportExecuteRequest(StrictInputSchema):
    batch_size: int = Field(default=100, ge=1, le=1000)
    duplicate_action: Optional[DuplicateAction] = None


# ── Response schemas ──────────────────────────────────────────────────────

class ImportJobResponse(BaseModel):
    id: int
    job_type: ImportJobType
    file_format: ImportFileFormat
    status: ImportJobStatus
    source_filename: str
    file_size_bytes: Optional[int] = None
    total_rows: int
    processed_rows: int
    created_rows: int
    updated_rows: int
    skipped_rows: int
    error_rows: int
    progress_percent: float
    error_threshold: float
    duplicate_action: DuplicateAction
    column_mapping: Optional[dict[str, str]] = None
    created_by_id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ValidationError(BaseModel):
    row: int
    field: str
    message: str
    severity: str = "error"  # error | warning


class ValidationReport(BaseModel):
    job_id: int
    status: ImportJobStatus
    total_rows: int
    valid_rows: int
    warning_rows: int
    error_rows: int
    errors: list[ValidationError]
    warnings: list[ValidationError]


class PreviewRow(BaseModel):
    row_number: int
    status: ImportRecordStatus
    data: dict[str, Any]
    errors: Optional[list[dict[str, str]]] = None
    warnings: Optional[list[dict[str, str]]] = None
    is_duplicate: bool = False
    duplicate_of_id: Optional[int] = None
    duplicate_score: Optional[float] = None


class ImportPreviewResponse(BaseModel):
    job_id: int
    total_rows: int
    preview_rows: list[PreviewRow]
    detected_columns: list[str]
    target_fields: list[str]
    column_mapping: Optional[dict[str, str]] = None


class DryRunResult(BaseModel):
    job_id: int
    would_create: int
    would_update: int
    would_skip: int
    duplicate_candidates: int
    sample_records: list[dict[str, Any]]


class ImportProgressResponse(BaseModel):
    job_id: int
    status: ImportJobStatus
    total_rows: int
    processed_rows: int
    created_rows: int
    updated_rows: int
    skipped_rows: int
    error_rows: int
    progress_percent: float
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ImportHistoryItem(BaseModel):
    id: int
    job_type: ImportJobType
    status: ImportJobStatus
    source_filename: str
    total_rows: int
    created_rows: int
    error_rows: int
    created_by_id: Optional[int] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ImportHistoryResponse(BaseModel):
    items: list[ImportHistoryItem]
    total: int
    limit: int
    offset: int


class RollbackResponse(BaseModel):
    job_id: int
    status: ImportJobStatus
    records_rolled_back: int
    records_actually_deleted: int = 0
    records_marked_only: int = 0
    warning: Optional[str] = None
    rolled_back_at: Optional[datetime] = None


class TemplateInfo(BaseModel):
    job_type: ImportJobType
    filename: str
    description: str
    columns: list[str]
    sample_row: dict[str, str]
