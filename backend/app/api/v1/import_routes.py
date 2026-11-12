# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Bulk import API endpoints.

POST /api/v1/import/upload          - upload file, start validation
GET  /api/v1/import/{job_id}/status - check progress
GET  /api/v1/import/{job_id}/preview - see validated rows
POST /api/v1/import/{job_id}/column-mapping - set column mapping
POST /api/v1/import/{job_id}/dry-run - simulate
POST /api/v1/import/{job_id}/execute - run for real
POST /api/v1/import/{job_id}/rollback - undo
GET  /api/v1/import/history         - list past imports
GET  /api/v1/import/templates       - list available CSV templates
GET  /api/v1/import/templates/{job_type} - download a template
"""

import io
import csv as csv_mod
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.import_job import (
    DuplicateAction,
    ImportJobStatus,
    ImportJobType,
    ImportRecordStatus,
)
from ...models.user import User
from ...schemas.import_schemas import (
    ColumnMappingRequest,
    DryRunResult,
    ImportExecuteRequest,
    ImportHistoryResponse,
    ImportHistoryItem,
    ImportJobResponse,
    ImportPreviewResponse,
    ImportProgressResponse,
    PreviewRow,
    RollbackResponse,
    TemplateInfo,
    ValidationReport,
    ValidationError as ValErr,
)
from ...services.import_service import ImportService, TEMPLATES, TARGET_FIELDS
from .dependencies import require_staff

router = APIRouter(prefix="/import", tags=["Import"])

MAX_UPLOAD_SIZE = 200 * 1024 * 1024  # 200 MB


# ── Upload ────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=ImportJobResponse, status_code=201)
async def upload_import_file(
    file: UploadFile = File(...),
    job_type: ImportJobType = Form(...),
    duplicate_action: DuplicateAction = Form(DuplicateAction.SKIP),
    error_threshold: float = Form(10.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Upload a file and start validation.

    Accepts CSV, MARC21 (.mrc), MARCXML (.xml), or JSON files.
    After upload the file is automatically validated.
    """
    # Validate file type before reading content
    ALLOWED_IMPORT_EXTENSIONS = {".csv", ".mrc", ".xml", ".json", ".tsv"}
    from pathlib import Path as _FilePath
    _file_ext = _FilePath(file.filename or "").suffix.lower()
    if _file_ext not in ALLOWED_IMPORT_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{_file_ext}' not allowed. Accepted: {', '.join(sorted(ALLOWED_IMPORT_EXTENSIONS))}",
        )

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_UPLOAD_SIZE // (1024*1024)} MB",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    job = await ImportService.upload(
        db=db,
        file_content=content,
        filename=file.filename or "import_file",
        job_type=job_type,
        duplicate_action=duplicate_action,
        error_threshold=error_threshold,
        created_by_id=current_user.id,
    )

    # Auto-validate after upload
    job = await ImportService.validate(db, job)

    return ImportJobResponse.model_validate(job)


# ── Status ────────────────────────────────────────────────────────────────

@router.get("/{job_id}/status", response_model=ImportProgressResponse)
async def get_import_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Check import job progress."""
    job = await ImportService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    return ImportProgressResponse(
        job_id=job.id,
        status=job.status,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        created_rows=job.created_rows,
        updated_rows=job.updated_rows,
        skipped_rows=job.skipped_rows,
        error_rows=job.error_rows,
        progress_percent=job.progress_percent,
        started_at=job.started_at,
        completed_at=job.completed_at,
    )


# ── Preview ───────────────────────────────────────────────────────────────

@router.get("/{job_id}/preview", response_model=ImportPreviewResponse)
async def get_import_preview(
    job_id: int,
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Preview validated rows (first N rows with status)."""
    job = await ImportService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status not in (ImportJobStatus.VALIDATED, ImportJobStatus.DRY_RUN):
        raise HTTPException(
            status_code=400,
            detail=f"Job must be validated first (current status: {job.status})",
        )

    records = await ImportService.preview(db, job, limit=limit)

    preview_rows = [
        PreviewRow(
            row_number=r.row_number,
            status=r.status,
            data=r.source_data or {},
            errors=r.errors,
            warnings=r.warnings,
            is_duplicate=r.is_duplicate,
            duplicate_of_id=r.duplicate_of_id,
            duplicate_score=r.duplicate_score,
        )
        for r in records
    ]

    # Detect source columns from first record
    detected = []
    if records and records[0].source_data:
        detected = list(records[0].source_data.keys())

    target_fields = sorted(TARGET_FIELDS.get(job.job_type, set()))

    return ImportPreviewResponse(
        job_id=job.id,
        total_rows=job.total_rows,
        preview_rows=preview_rows,
        detected_columns=detected,
        target_fields=target_fields,
        column_mapping=job.column_mapping,
    )


# ── Column Mapping ────────────────────────────────────────────────────────

@router.post("/{job_id}/column-mapping", response_model=ImportJobResponse)
async def set_column_mapping(
    job_id: int,
    body: ColumnMappingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Set column mapping and re-validate."""
    job = await ImportService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status not in (ImportJobStatus.VALIDATED, ImportJobStatus.PENDING):
        raise HTTPException(status_code=400, detail="Job must be in validated or pending state")

    job = await ImportService.set_column_mapping(db, job, body.mapping)
    return ImportJobResponse.model_validate(job)


# ── Dry Run ───────────────────────────────────────────────────────────────

@router.post("/{job_id}/dry-run", response_model=DryRunResult)
async def run_dry_run(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Simulate the import - shows what would be created, updated, or skipped."""
    job = await ImportService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status != ImportJobStatus.VALIDATED:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be validated before dry run (current: {job.status})",
        )

    report = await ImportService.dry_run(db, job)
    return DryRunResult(job_id=job.id, **report)


# ── Execute ───────────────────────────────────────────────────────────────

@router.post("/{job_id}/execute", response_model=ImportJobResponse)
async def execute_import(
    job_id: int,
    body: Optional[ImportExecuteRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Execute the import for real - creates records in batches."""
    job = await ImportService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status != ImportJobStatus.VALIDATED:
        raise HTTPException(
            status_code=400,
            detail=f"Job must be validated before executing (current: {job.status})",
        )

    batch_size = 100
    if body:
        batch_size = body.batch_size
        if body.duplicate_action is not None:
            job.duplicate_action = body.duplicate_action

    job = await ImportService.execute(db, job, batch_size=batch_size)
    return ImportJobResponse.model_validate(job)


# ── Rollback ──────────────────────────────────────────────────────────────

@router.post("/{job_id}/rollback", response_model=RollbackResponse)
async def rollback_import(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Undo all records created by this import job."""
    job = await ImportService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Import job not found")
    if job.status not in (ImportJobStatus.COMPLETED, ImportJobStatus.FAILED, ImportJobStatus.IMPORTING):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot rollback job with status '{job.status}'",
        )

    job, created_count, updated_count = await ImportService.rollback(
        db, job, rolled_back_by_id=current_user.id, reason="Staff-initiated rollback"
    )
    warning = None
    if updated_count > 0:
        warning = (
            f"{updated_count} record(s) were marked as rolled back but their data was not "
            f"restored — full undo of updates requires storing previous field values "
            f"(not implemented). Only {created_count} newly-created record(s) were actually deleted."
        )
    return RollbackResponse(
        job_id=job.id,
        status=job.status,
        records_rolled_back=created_count + updated_count,
        records_actually_deleted=created_count,
        records_marked_only=updated_count,
        warning=warning,
        rolled_back_at=job.rolled_back_at,
    )


# ── History ───────────────────────────────────────────────────────────────

@router.get("/history", response_model=ImportHistoryResponse)
async def get_import_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    job_type: Optional[ImportJobType] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List past import jobs."""
    jobs, total = await ImportService.list_jobs(
        db, limit=limit, offset=offset, job_type=job_type
    )
    return ImportHistoryResponse(
        items=[ImportHistoryItem.model_validate(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


# ── Templates ─────────────────────────────────────────────────────────────

@router.get("/templates", response_model=list[TemplateInfo])
async def list_templates(
    current_user: User = Depends(require_staff),
):
    """List available CSV import templates."""
    return [
        TemplateInfo(
            job_type=jt,
            filename=info["filename"],
            description=info["description"],
            columns=info["columns"],
            sample_row=info["sample_row"],
        )
        for jt, info in TEMPLATES.items()
    ]
