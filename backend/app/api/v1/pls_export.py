# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public Libraries Survey (PLS) statistics export API endpoints."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.pls_export import (
    PLSPreviewResponse, PLSOverrideRequest,
)
from ...services.pls_export_service import PLSExportService
from .auth import get_current_user
from .dependencies import require_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/pls-export", tags=["pls-export"])


def _get_service(db: AsyncSession = Depends(get_db)) -> PLSExportService:
    return PLSExportService(db)


@router.get("/preview", response_model=PLSPreviewResponse)
async def preview_pls(
    fiscal_year: int = Query(..., ge=2000, le=2100),
    current_user: User = Depends(require_admin),
    service: PLSExportService = Depends(_get_service),
):
    result = await service.generate_preview(fiscal_year)
    return result


@router.post("/generate")
async def generate_pls_csv(
    fiscal_year: int = Query(..., ge=2000, le=2100),
    overrides: PLSOverrideRequest | None = None,
    current_user: User = Depends(require_admin),
    service: PLSExportService = Depends(_get_service),
):
    override_dict = overrides.overrides if overrides else {}
    csv_content = await service.generate_csv(fiscal_year, override_dict)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=pls_export_{fiscal_year}.csv"},
    )
