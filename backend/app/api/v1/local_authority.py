# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""HTTP routes for LocalAuthority CRUD + linking."""

from typing import Optional

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.local_authority import LocalAuthorityStatus, LocalAuthorityType
from ...models.user import User
from ...schemas.bibframe import AuthorityLinkResponse
from ...schemas.local_authority import (
    LocalAuthorityCreate,
    LocalAuthorityLinkRequest,
    LocalAuthorityListResponse,
    LocalAuthorityResponse,
    LocalAuthorityUpdate,
)
from ...services.local_authority_service import local_authority_service
from .auth import get_current_user
from .dependencies import require_staff

router = APIRouter(prefix="/local-authorities", tags=["Local Authorities"])


@router.get("", response_model=LocalAuthorityListResponse)
@limiter.limit("60/minute")
async def list_local_authorities(
    request: Request,
    q: Optional[str] = Query(None, description="Search label (case-insensitive)"),
    authority_type: Optional[LocalAuthorityType] = None,
    status_filter: Optional[LocalAuthorityStatus] = Query(None, alias="status"),
    library_system_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocalAuthorityListResponse:
    total, rows = await local_authority_service.search(
        db,
        q=q,
        authority_type=authority_type,
        status_filter=status_filter,
        library_system_id=library_system_id,
        limit=limit,
        offset=offset,
    )
    return LocalAuthorityListResponse(
        total=total,
        items=[LocalAuthorityResponse.model_validate(r) for r in rows],
    )


@router.get("/{authority_id}", response_model=LocalAuthorityResponse)
@limiter.limit("120/minute")
async def get_local_authority(
    request: Request,
    authority_id: int,
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> LocalAuthorityResponse:
    record = await local_authority_service.get(db, authority_id)
    return LocalAuthorityResponse.model_validate(record)


@router.post("", response_model=LocalAuthorityResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_local_authority(
    request: Request,
    data: LocalAuthorityCreate,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> LocalAuthorityResponse:
    record = await local_authority_service.create(db, data, user_id=user.id)
    return LocalAuthorityResponse.model_validate(record)


@router.patch("/{authority_id}", response_model=LocalAuthorityResponse)
@limiter.limit("60/minute")
async def update_local_authority(
    request: Request,
    authority_id: int,
    data: LocalAuthorityUpdate,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> LocalAuthorityResponse:
    record = await local_authority_service.update(db, authority_id, data, user_id=user.id)
    return LocalAuthorityResponse.model_validate(record)


@router.delete("/{authority_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("30/minute")
async def delete_local_authority(
    request: Request,
    authority_id: int,
    _user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> None:
    await local_authority_service.delete(db, authority_id)


@router.post(
    "/{authority_id}/links",
    response_model=AuthorityLinkResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def link_local_authority_to_entity(
    request: Request,
    authority_id: int,
    payload: LocalAuthorityLinkRequest,
    user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> AuthorityLinkResponse:
    link = await local_authority_service.link_to_entity(
        db, authority_id, payload, user_id=user.id
    )
    return AuthorityLinkResponse.model_validate(link)
