# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""MARC batch import/export API endpoints."""

from app.core.logging import get_logger
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.marc_batch import (
    MarcImportPreviewResponse, MarcImportExecuteRequest,
    MarcExportRequest, MarcBatchJobResponse, MarcBatchJobListResponse,
)
from ...services.marc_batch_service import MarcBatchService
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/marc-batch", tags=["marc-batch"])


def _get_service(db: AsyncSession = Depends(get_db)) -> MarcBatchService:
    return MarcBatchService(db)


@router.post("/import/upload", response_model=MarcImportPreviewResponse, status_code=201)
async def upload_marc_file(
    file: UploadFile = File(...),
    file_format: str = Query("marc21", pattern="^(marc21|marcxml)$"),
    current_user: User = Depends(require_staff),
    service: MarcBatchService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    job, records = await service.parse_upload(content, file.filename, file_format, current_user.id)
    await db.commit()

    return MarcImportPreviewResponse(
        job_id=job.id,
        file_name=job.file_name,
        total_records=len(records),
        records=records,
        duplicate_count=sum(1 for r in records if r["match_found"]),
    )


@router.post("/import/{job_id}/execute", response_model=MarcBatchJobResponse)
async def execute_import(
    job_id: int,
    data: MarcImportExecuteRequest,
    current_user: User = Depends(require_staff),
    service: MarcBatchService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    job = await service.execute_import(job_id, [d.model_dump() for d in data.decisions])
    await db.commit()
    return MarcBatchJobResponse.model_validate(job)


@router.post("/export", response_model=MarcBatchJobResponse)
async def create_export(
    data: MarcExportRequest,
    current_user: User = Depends(require_staff),
    service: MarcBatchService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    job, file_bytes = await service.generate_export(
        file_format=data.format, user_id=current_user.id,
        item_type=data.item_type, date_from=data.date_from,
        date_to=data.date_to, incremental_since=data.incremental_since,
        catalog_item_id=data.catalog_item_id,
        catalog_item_ids=data.catalog_item_ids,
    )
    await db.commit()
    return MarcBatchJobResponse.model_validate(job)


@router.get("/export/now")
async def export_now(
    format: str = Query("marc21", pattern="^(marc21|marcxml)$"),
    item_type: str | None = Query(None),
    incremental_since: datetime | None = Query(None),
    catalog_item_id: int | None = Query(None),
    current_user: User = Depends(require_staff),
    service: MarcBatchService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    """One-shot synchronous export: create job, return the file in the response."""
    job, file_bytes = await service.generate_export(
        file_format=format, user_id=current_user.id,
        item_type=item_type, incremental_since=incremental_since,
        catalog_item_id=catalog_item_id,
    )
    await db.commit()
    media = "application/marc" if format == "marc21" else "application/marcxml+xml"
    return StreamingResponse(
        iter([file_bytes]),
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename={job.file_name}"},
    )


@router.get("/export/{job_id}/download")
async def download_export(
    job_id: int,
    current_user: User = Depends(require_staff),
    service: MarcBatchService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    from app.models.marc_batch import MarcBatchJob, MarcBatchJobType
    from sqlalchemy import select
    result = await db.execute(select(MarcBatchJob).where(MarcBatchJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job or job.job_type != MarcBatchJobType.export_job:
        raise HTTPException(status_code=404, detail="Export job not found")

    # Re-generate the export (or retrieve from storage)
    _, file_bytes = await service.generate_export(
        file_format=job.file_format, user_id=current_user.id,
        **(job.filter_criteria or {}),
    )
    media = "application/marc" if job.file_format == "marc21" else "application/marcxml+xml"
    return StreamingResponse(
        iter([file_bytes]),
        media_type=media,
        headers={"Content-Disposition": f"attachment; filename={job.file_name}"},
    )


@router.get("/jobs", response_model=MarcBatchJobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    job_type: str | None = Query(None),
    current_user: User = Depends(require_staff),
    service: MarcBatchService = Depends(_get_service),
):
    items, total = await service.list_jobs(page=page, per_page=per_page, job_type=job_type)
    return MarcBatchJobListResponse(
        items=[MarcBatchJobResponse.model_validate(j) for j in items],
        total=total, page=page, per_page=per_page,
    )
