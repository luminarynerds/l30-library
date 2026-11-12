# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Migration project API — multi-phase library migration with sequential gating.

POST   /api/v1/migration-project/                         - create project
GET    /api/v1/migration-project/                         - list projects
GET    /api/v1/migration-project/{id}                     - project status
POST   /api/v1/migration-project/{id}/phases/{phase}/upload   - upload for phase
POST   /api/v1/migration-project/{id}/phases/{phase}/dry-run  - simulate phase
POST   /api/v1/migration-project/{id}/phases/{phase}/execute  - run phase
POST   /api/v1/migration-project/{id}/phases/{phase}/rollback - undo phase
GET    /api/v1/migration-project/{id}/report              - final summary
"""

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.services.migration_project_service import MigrationProjectService
from .dependencies import require_admin

router = APIRouter(prefix="/migration-project", tags=["Migration Project"])

MAX_UPLOAD_SIZE = 500 * 1024 * 1024  # 500 MB


# ── Schemas ────────────────────────────────────────────────────────────────

class CreateProjectRequest(BaseModel):
    name: str = Field(..., max_length=255)
    source_system_name: Optional[str] = None
    source_system_type: Optional[str] = None
    cutover_strategy: Optional[str] = None
    estimated_catalog_size: Optional[int] = None
    estimated_patron_count: Optional[int] = None
    notes: Optional[str] = None


class PhaseResponse(BaseModel):
    phase: str
    status: str
    import_job_id: Optional[int] = None
    total_records: int = 0
    created_records: int = 0
    error_records: int = 0
    skipped_records: int = 0
    progress_percent: float = 0.0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProjectResponse(BaseModel):
    id: int
    name: str
    status: str
    cutover_strategy: Optional[str] = None
    source_system_name: Optional[str] = None
    source_system_type: Optional[str] = None
    estimated_catalog_size: Optional[int] = None
    estimated_patron_count: Optional[int] = None
    assessment_report: Optional[dict] = None
    phases: list[PhaseResponse] = []
    created_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


class ProjectListResponse(BaseModel):
    items: list[ProjectResponse]
    total: int
    limit: int
    offset: int


# ── Helpers ────────────────────────────────────────────────────────────────

def _project_to_response(project) -> ProjectResponse:
    phases = []
    for p in (project.phases or []):
        phases.append(PhaseResponse(
            phase=p.phase.value,
            status=p.status.value,
            import_job_id=p.import_job_id,
            total_records=p.total_records,
            created_records=p.created_records,
            error_records=p.error_records,
            skipped_records=p.skipped_records,
            progress_percent=p.progress_percent,
            started_at=p.started_at.isoformat() if p.started_at else None,
            completed_at=p.completed_at.isoformat() if p.completed_at else None,
        ))
    return ProjectResponse(
        id=project.id,
        name=project.name,
        status=project.status.value,
        cutover_strategy=project.cutover_strategy.value if project.cutover_strategy else None,
        source_system_name=project.source_system_name,
        source_system_type=project.source_system_type,
        estimated_catalog_size=project.estimated_catalog_size,
        estimated_patron_count=project.estimated_patron_count,
        assessment_report=project.assessment_report,
        phases=phases,
        created_at=project.created_at.isoformat() if project.created_at else None,
        started_at=project.started_at.isoformat() if project.started_at else None,
        completed_at=project.completed_at.isoformat() if project.completed_at else None,
    )


# ── Routes ─────────────────────────────────────────────────────────────────

@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(
    body: CreateProjectRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create a new multi-phase migration project."""
    project = await MigrationProjectService.create_project(
        db=db,
        name=body.name,
        created_by_id=current_user.id,
        source_system_name=body.source_system_name,
        source_system_type=body.source_system_type,
        cutover_strategy=body.cutover_strategy,
        estimated_catalog_size=body.estimated_catalog_size,
        estimated_patron_count=body.estimated_patron_count,
        notes=body.notes,
    )
    await db.commit()
    # Reload with phases eagerly loaded
    project = await MigrationProjectService.get_project_with_phases(db, project.id)
    return _project_to_response(project)


@router.get("/", response_model=ProjectListResponse)
async def list_projects(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List migration projects."""
    projects, total = await MigrationProjectService.list_projects(db, limit, offset)
    return ProjectListResponse(
        items=[_project_to_response(p) for p in projects],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get migration project with all phase statuses."""
    project = await MigrationProjectService.get_project_with_phases(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Migration project not found")
    return _project_to_response(project)


@router.post("/{project_id}/phases/{phase}/upload")
async def upload_phase_file(
    project_id: int,
    phase: str,
    file: UploadFile = File(...),
    duplicate_action: str = Form("skip"),
    error_threshold: float = Form(10.0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Upload a file for a migration phase. Triggers validation automatically."""
    # Validate file
    from pathlib import Path as _P
    allowed = {".csv", ".tsv", ".mrc", ".xml", ".marcxml", ".json"}
    ext = _P(file.filename or "").suffix.lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type '{ext}' not allowed. Accepted: {', '.join(sorted(allowed))}")

    content = await file.read()
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(413, f"File too large. Max {MAX_UPLOAD_SIZE // (1024*1024)} MB")
    if not content:
        raise HTTPException(400, "File is empty")

    try:
        result = await MigrationProjectService.upload_phase_file(
            db=db,
            project_id=project_id,
            phase_name=phase,
            file_content=content,
            filename=file.filename or "upload",
            created_by_id=current_user.id,
            duplicate_action=duplicate_action,
            error_threshold=error_threshold,
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{project_id}/phases/{phase}/dry-run")
async def dry_run_phase(
    project_id: int,
    phase: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Run a dry-run simulation for a phase."""
    try:
        result = await MigrationProjectService.dry_run_phase(db, project_id, phase)
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{project_id}/phases/{phase}/execute")
async def execute_phase(
    project_id: int,
    phase: str,
    batch_size: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Execute a validated phase — creates records in the database."""
    try:
        result = await MigrationProjectService.execute_phase(
            db, project_id, phase, batch_size=batch_size
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.post("/{project_id}/phases/{phase}/rollback")
async def rollback_phase(
    project_id: int,
    phase: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Rollback a completed or failed phase. Re-locks subsequent phases."""
    try:
        result = await MigrationProjectService.rollback_phase(
            db, project_id, phase, rolled_back_by_id=current_user.id
        )
        await db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/{project_id}/report")
async def get_migration_report(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get the final migration summary report."""
    try:
        return await MigrationProjectService.get_report(db, project_id)
    except ValueError as e:
        raise HTTPException(404, str(e)) from e
