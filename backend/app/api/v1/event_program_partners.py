# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Event program partners: basic CRUD.

Public reads (list, get) so the EventForm presenter picker can fetch them
without admin auth. Mutations are admin-gated. DELETE is soft (is_active=false)
unless ?force=true.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination import PaginationParams, calculate_total_pages
from ...models.event_program_partner import EventProgramPartner
from ...models.user import User
from ...schemas.common import PaginatedResponse, PaginationInfo
from ...schemas.event_program_partner import (
    EventProgramPartnerCreate,
    EventProgramPartnerResponse,
    EventProgramPartnerUpdate,
    slugify,
)
from .dependencies import require_admin

router = APIRouter(prefix="/program-partners", tags=["program-partners"])


async def _unique_slug(db: AsyncSession, base: str, exclude_id: Optional[int] = None) -> str:
    slug = base
    suffix = 2
    while True:
        q = select(EventProgramPartner).where(EventProgramPartner.slug == slug)
        if exclude_id is not None:
            q = q.where(EventProgramPartner.id != exclude_id)
        existing = (await db.execute(q)).scalar_one_or_none()
        if existing is None:
            return slug
        slug = f"{base}_{suffix}"
        suffix += 1


@router.get("", response_model=PaginatedResponse[EventProgramPartnerResponse])
async def list_program_partners(
    pagination: PaginationParams = Depends(),
    include_inactive: bool = Query(
        False, description="Include soft-deleted (is_active=false) partners."
    ),
    search: Optional[str] = Query(None, max_length=200, description="Substring search on name."),
    db: AsyncSession = Depends(get_db),
):
    """List event program partners.

    Default behavior: active only. Pass include_inactive=true to surface soft-deleted rows.
    """
    base_q = select(EventProgramPartner)
    if not include_inactive:
        base_q = base_q.where(EventProgramPartner.is_active.is_(True))
    if search:
        like = f"%{search.lower()}%"
        base_q = base_q.where(func.lower(EventProgramPartner.name).like(like))

    count_q = select(func.count()).select_from(base_q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    rows = (
        await db.execute(
            base_q.order_by(EventProgramPartner.name)
            .offset(pagination.offset)
            .limit(pagination.page_size)
        )
    ).scalars().all()

    return PaginatedResponse[EventProgramPartnerResponse](
        data=[EventProgramPartnerResponse.model_validate(r) for r in rows],
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=calculate_total_pages(total, pagination.page_size),
            has_next=pagination.page * pagination.page_size < total,
            has_previous=pagination.page > 1,
        ),
    )


@router.post(
    "",
    response_model=EventProgramPartnerResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_program_partner(
    payload: EventProgramPartnerCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    slug = await _unique_slug(db, slugify(payload.name))
    partner = EventProgramPartner(
        name=payload.name,
        slug=slug,
        website=payload.website,
        contact_email=payload.contact_email,
        contact_phone=payload.contact_phone,
        notes=payload.notes,
        is_active=payload.is_active,
    )
    db.add(partner)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Program partner with that name already exists.",
        ) from None
    await db.refresh(partner)
    return EventProgramPartnerResponse.model_validate(partner)


@router.get("/{partner_id}", response_model=EventProgramPartnerResponse)
async def get_program_partner(
    partner_id: int,
    db: AsyncSession = Depends(get_db),
):
    partner = (
        await db.execute(
            select(EventProgramPartner).where(EventProgramPartner.id == partner_id)
        )
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Program partner not found."
        )
    return EventProgramPartnerResponse.model_validate(partner)


@router.patch("/{partner_id}", response_model=EventProgramPartnerResponse)
async def update_program_partner(
    partner_id: int,
    payload: EventProgramPartnerUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    partner = (
        await db.execute(
            select(EventProgramPartner).where(EventProgramPartner.id == partner_id)
        )
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Program partner not found."
        )

    data = payload.model_dump(exclude_unset=True)
    # Slug only changes if explicitly provided in the update payload.
    if "slug" in data and data["slug"]:
        data["slug"] = await _unique_slug(db, data["slug"], exclude_id=partner_id)
    for field, value in data.items():
        setattr(partner, field, value)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Program partner with that name already exists.",
        ) from None
    await db.refresh(partner)
    return EventProgramPartnerResponse.model_validate(partner)


@router.delete("/{partner_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program_partner(
    partner_id: int,
    force: bool = Query(
        False, description="If true, hard-delete the row instead of marking is_active=false."
    ),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    partner = (
        await db.execute(
            select(EventProgramPartner).where(EventProgramPartner.id == partner_id)
        )
    ).scalar_one_or_none()
    if partner is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Program partner not found."
        )
    if force:
        await db.delete(partner)
    else:
        partner.is_active = False
    await db.commit()
