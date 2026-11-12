# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""MARC macro CRUD + run endpoints."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.marc_macro import (
    SUPPORTED_TARGETS,
    MarcMacroCreate,
    MarcMacroListResponse,
    MarcMacroResponse,
    MarcMacroRunRequest,
    MarcMacroRunResponse,
    MarcMacroUpdate,
)
from ...services.marc_macro_service import (
    MarcMacroError,
    MarcMacroForbidden,
    MarcMacroNotFound,
    MarcMacroService,
)
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/marc-macros", tags=["marc-macros"])


def _service(db: AsyncSession = Depends(get_db)) -> MarcMacroService:
    return MarcMacroService(db)


def _to_http(exc: MarcMacroError) -> HTTPException:
    if isinstance(exc, MarcMacroNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, MarcMacroForbidden):
        return HTTPException(status_code=403, detail=str(exc))
    return HTTPException(status_code=400, detail=str(exc))


@router.get("/targets", response_model=dict[str, str])
async def list_targets(_: User = Depends(require_staff)) -> dict[str, str]:
    """Return the MARC tag/subfield -> catalog column mapping macros may target."""
    return SUPPORTED_TARGETS


@router.get("", response_model=MarcMacroListResponse)
async def list_macros(
    user: User = Depends(require_staff),
    service: MarcMacroService = Depends(_service),
) -> MarcMacroListResponse:
    items, total = await service.list_macros(user=user)
    return MarcMacroListResponse(
        items=[MarcMacroResponse.model_validate(m) for m in items],
        total=total,
    )


@router.post("", response_model=MarcMacroResponse, status_code=status.HTTP_201_CREATED)
async def create_macro(
    data: MarcMacroCreate,
    user: User = Depends(require_staff),
    service: MarcMacroService = Depends(_service),
) -> MarcMacroResponse:
    try:
        macro = await service.create_macro(data, user=user)
    except MarcMacroError as exc:
        raise _to_http(exc) from exc
    return MarcMacroResponse.model_validate(macro)


@router.get("/{macro_id}", response_model=MarcMacroResponse)
async def get_macro(
    macro_id: int,
    user: User = Depends(require_staff),
    service: MarcMacroService = Depends(_service),
) -> MarcMacroResponse:
    try:
        macro = await service.get_macro(macro_id, user=user)
    except MarcMacroError as exc:
        raise _to_http(exc) from exc
    return MarcMacroResponse.model_validate(macro)


@router.patch("/{macro_id}", response_model=MarcMacroResponse)
async def update_macro(
    macro_id: int,
    data: MarcMacroUpdate,
    user: User = Depends(require_staff),
    service: MarcMacroService = Depends(_service),
) -> MarcMacroResponse:
    try:
        macro = await service.update_macro(macro_id, data, user=user)
    except MarcMacroError as exc:
        raise _to_http(exc) from exc
    return MarcMacroResponse.model_validate(macro)


@router.delete("/{macro_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_macro(
    macro_id: int,
    user: User = Depends(require_staff),
    service: MarcMacroService = Depends(_service),
) -> None:
    try:
        await service.delete_macro(macro_id, user=user)
    except MarcMacroError as exc:
        raise _to_http(exc) from exc


@router.post("/{macro_id}/run", response_model=MarcMacroRunResponse)
async def run_macro(
    macro_id: int,
    data: MarcMacroRunRequest,
    user: User = Depends(require_staff),
    service: MarcMacroService = Depends(_service),
) -> MarcMacroRunResponse:
    try:
        results = await service.run_macro(macro_id, data.catalog_item_ids, user=user)
    except MarcMacroError as exc:
        raise _to_http(exc) from exc
    succeeded = sum(1 for r in results if r["error"] is None)
    return MarcMacroRunResponse(
        macro_id=macro_id,
        total=len(results),
        succeeded=succeeded,
        failed=len(results) - succeeded,
        results=results,
    )
