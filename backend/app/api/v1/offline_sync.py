# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.offline_sync import (
    DepartRequest,
    DepartResponse,
    PrepareRouteResponse,
    ReturnRequest,
    ReturnResponse,
    SyncRequest,
    SyncResponse,
)
from ...services.offline_sync_service import OfflineSyncService
from .dependencies import require_authenticated, require_staff

router = APIRouter(prefix="/offline", tags=["Offline Sync"])


@router.get("/prepare-route", response_model=PrepareRouteResponse)
async def prepare_route(
    branch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    return await OfflineSyncService.prepare_route(db, branch_id)


@router.post("/depart", response_model=DepartResponse)
async def depart(
    request: DepartRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = await OfflineSyncService.depart(
        db=db,
        branch_id=request.branch_id,
        staff_id=staff_user.id,
        items_cached=request.items_cached,
        patrons_cached=request.patrons_cached,
    )
    return DepartResponse(
        session_id=session.id,
        offline_session_token=session.offline_session_token,
        status=session.status,
    )


@router.post("/return", response_model=ReturnResponse)
async def mark_returned(
    request: ReturnRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    session = await OfflineSyncService.mark_returned(db, request.session_id)
    return ReturnResponse(session_id=session.id, status=session.status)


@router.post("/sync", response_model=SyncResponse)
async def sync_operations(
    request: SyncRequest,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
    x_offline_token: Optional[str] = Header(None, alias="X-Offline-Token"),
):
    if x_offline_token:
        session = await OfflineSyncService.validate_offline_token(db, x_offline_token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid offline session token")
        if session.id != request.session_id:
            raise HTTPException(status_code=403, detail="Token does not match session")
    else:
        raise HTTPException(status_code=401, detail="X-Offline-Token header required")

    results = await OfflineSyncService.sync_operations(db, request.session_id, request.operations)
    return SyncResponse(
        session_id=request.session_id,
        results=results,
        synced=sum(1 for r in results if r.status == "synced"),
        conflicts=sum(1 for r in results if r.status == "conflict"),
        failed=sum(1 for r in results if r.status == "failed"),
    )
