# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Migration wizard API endpoints.

POST   /api/v1/migration/upload          - upload file, start analyze
GET    /api/v1/migration/{job_id}/status - poll progress
GET    /api/v1/migration/{job_id}/preview - analysis report + field mapping
POST   /api/v1/migration/{job_id}/configure - save field mapping + options
POST   /api/v1/migration/{job_id}/dry-run - trigger dry run
POST   /api/v1/migration/{job_id}/execute - trigger real import
POST   /api/v1/migration/{job_id}/rollback - undo
GET    /api/v1/migration/history         - list past migrations
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.models.migration_job import MigrationJob, MigrationJobStatus, MigrationSourceSystem
from app.models.user import User
from app.schemas.migration_wizard import (
    FieldMappingRequest,
    MigrationJobResponse,
    MigrationOptionsRequest,
    MigrationProgressResponse,
    MigrationHistoryResponse,
    MigrationHistoryItem,
    AnalysisReport,
    DryRunReport,
)
from app.services.migration_wizard_service import MigrationWizardService
from .dependencies import require_admin

router = APIRouter(prefix="/migration", tags=["Migration"])

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


@router.post("/upload", response_model=MigrationJobResponse, status_code=201)
async def upload_migration_file(
    file: UploadFile = File(...),
    source_system: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Upload migration file and start analysis.

    Args:
        file: CSV or MARC file
        source_system: "sirsi" | "koha" | "csv"

    Returns:
        Created MigrationJob with initial analysis
    """
    # Validate source system
    try:
        source = MigrationSourceSystem(source_system)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid source_system. Must be one of: {', '.join([s.value for s in MigrationSourceSystem])}",
        ) from None

    # Validate file
    from pathlib import Path as _FilePath
    allowed_exts = {".csv", ".mrc", ".xml", ".tsv"}
    file_ext = _FilePath(file.filename or "").suffix.lower()
    if file_ext not in allowed_exts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type '{file_ext}' not allowed. Accepted: {', '.join(sorted(allowed_exts))}",
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

    job = await MigrationWizardService.upload(
        db=db,
        content=content,
        filename=file.filename or "migration_file",
        source_system=source_system,
        user_id=current_user.id,
    )

    return MigrationJobResponse.from_attributes(**{c.name: getattr(job, c.name) for c in job.__table__.columns})


@router.get("/{job_id}/status", response_model=MigrationProgressResponse)
async def get_migration_status(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Check migration job progress."""
    job = await MigrationWizardService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    return MigrationProgressResponse(
        job_id=job.id,
        status=job.status.value,
        total_rows=job.total_rows,
        processed_rows=job.processed_rows,
        failed_rows=job.failed_rows,
        progress_percent=job.progress_percent,
        started_at=job.started_at,
        completed_at=job.completed_at,
        is_complete=job.is_complete,
    )


@router.get("/{job_id}/preview", response_model=dict)
async def get_migration_preview(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get analysis report and suggested field mapping."""
    job = await MigrationWizardService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    return {
        "job_id": job.id,
        "status": job.status.value,
        "analysis_report": job.analysis_report or {},
    }


@router.post("/{job_id}/configure", response_model=MigrationJobResponse)
async def configure_migration(
    job_id: int,
    body: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Save field mapping and import options."""
    job = await MigrationWizardService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    field_mapping = body.get("field_mapping", {})
    options = body.get("options", {})

    job = await MigrationWizardService.configure(db, job, field_mapping, options)

    return MigrationJobResponse.from_attributes(**{c.name: getattr(job, c.name) for c in job.__table__.columns})


@router.post("/{job_id}/dry-run", response_model=dict)
async def run_dry_run(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Simulate import without writing to database."""
    job = await MigrationWizardService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    job = await MigrationWizardService.execute_dry_run(db, job)

    return {
        "job_id": job.id,
        "status": job.status.value,
        "dry_run_report": job.dry_run_report or {},
    }


@router.post("/{job_id}/execute", response_model=MigrationJobResponse)
async def execute_migration(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Execute actual import with database writes."""
    job = await MigrationWizardService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    job = await MigrationWizardService.execute(db, job)

    return MigrationJobResponse.from_attributes(**{c.name: getattr(job, c.name) for c in job.__table__.columns})


@router.post("/{job_id}/rollback", response_model=dict)
async def rollback_migration(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Undo completed migration."""
    job = await MigrationWizardService.get_job(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Migration job not found")

    job = await MigrationWizardService.rollback(db, job)

    return {
        "job_id": job.id,
        "status": job.status.value,
        "rolled_back": True,
    }


@router.get("/history", response_model=MigrationHistoryResponse)
async def get_migration_history(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List past migration jobs."""
    # Count total
    count_result = await db.execute(select(MigrationJob))
    total = len(count_result.scalars().all())

    # Get paginated results
    result = await db.execute(
        select(MigrationJob)
        .order_by(desc(MigrationJob.created_at))
        .limit(limit)
        .offset(offset)
    )
    jobs = result.scalars().all()

    items = [
        MigrationHistoryItem(
            id=job.id,
            source_system=job.source_system.value,
            original_filename=job.original_filename,
            status=job.status.value,
            total_rows=job.total_rows,
            processed_rows=job.processed_rows,
            failed_rows=job.failed_rows,
            created_at=job.created_at,
            completed_at=job.completed_at,
        )
        for job in jobs
    ]

    return MigrationHistoryResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )
