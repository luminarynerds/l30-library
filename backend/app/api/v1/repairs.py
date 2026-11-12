# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Binding/repair workflow API endpoints."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.repair import (
    RepairRecordCreate, RepairRecordUpdate, RepairStatusUpdate,
    RepairRecordResponse, RepairRecordListResponse, RepairDashboardResponse,
)
from ...services.repair_service import RepairService
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/repairs", tags=["repairs"])


def _get_service(db: AsyncSession = Depends(get_db)) -> RepairService:
    return RepairService(db)


@router.get("/dashboard", response_model=RepairDashboardResponse)
async def get_dashboard(
    current_user: User = Depends(require_staff),
    service: RepairService = Depends(_get_service),
):
    return await service.get_dashboard()


@router.get("", response_model=RepairRecordListResponse)
async def list_repairs(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
    repair_type: str | None = Query(None),
    current_user: User = Depends(require_staff),
    service: RepairService = Depends(_get_service),
):
    rows, total = await service.list_repairs(
        page=page, per_page=per_page,
        status=status_filter, repair_type=repair_type,
    )
    items = []
    for row in rows:
        record = row[0]
        resp = RepairRecordResponse.model_validate(record)
        resp.item_title = row.item_title
        resp.item_barcode = row.item_barcode
        resp.vendor_name = row.vendor_name
        items.append(resp)
    return RepairRecordListResponse(
        items=items, total=total, page=page, per_page=per_page,
    )


@router.post("", response_model=RepairRecordResponse, status_code=201)
async def create_repair(
    data: RepairRecordCreate,
    current_user: User = Depends(require_staff),
    service: RepairService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    record = await service.create_repair(
        reported_by_id=current_user.id,
        **data.model_dump(exclude_unset=True),
    )
    await db.commit()
    return RepairRecordResponse.model_validate(record)


@router.get("/{repair_id}", response_model=RepairRecordResponse)
async def get_repair(
    repair_id: int,
    current_user: User = Depends(require_staff),
    service: RepairService = Depends(_get_service),
):
    record = await service.get_repair(repair_id)
    if not record:
        raise HTTPException(status_code=404, detail="Repair record not found")
    return RepairRecordResponse.model_validate(record)


@router.patch("/{repair_id}", response_model=RepairRecordResponse)
async def update_repair(
    repair_id: int,
    data: RepairRecordUpdate,
    current_user: User = Depends(require_staff),
    service: RepairService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    record = await service.update_repair(repair_id, data.model_dump(exclude_unset=True))
    if not record:
        raise HTTPException(status_code=404, detail="Repair record not found")
    await db.commit()
    return RepairRecordResponse.model_validate(record)


@router.patch("/{repair_id}/status", response_model=RepairRecordResponse)
async def update_repair_status(
    repair_id: int,
    data: RepairStatusUpdate,
    current_user: User = Depends(require_staff),
    service: RepairService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    try:
        record = await service.update_status(
            repair_id, data.status, current_user.id,
            notes=data.notes, sent_date=data.sent_date,
            returned_date=data.returned_date, actual_cost=data.actual_cost,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    if not record:
        raise HTTPException(status_code=404, detail="Repair record not found")
    await db.commit()
    return RepairRecordResponse.model_validate(record)
