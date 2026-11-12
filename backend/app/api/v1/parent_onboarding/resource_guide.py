# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Parent Onboarding — Resource Guide API endpoints (Component 3).

Pure move from _legacy.py; no behaviour change.
"""
import logging as _logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....models.parent_onboarding import (
    ParentResourceGuideFlag,
    ParentResourceGuideItem, ParentResourceGuideSection,
    ResourceGuideFlagReason, ResourceGuideFlagStatus,
)
from ....models.user import User
from ....schemas.parent_onboarding import (
    ResourceGuideFlagCreate, ResourceGuideFlagItemSnapshot,
    ResourceGuideFlagResponse, ResourceGuideFlagUpdate,
    ResourceGuideItemCreate, ResourceGuideItemResponse, ResourceGuideItemUpdate,
    ResourceGuideSectionCreate, ResourceGuideSectionResponse,
    ResourceGuideSectionUpdate,
)
from ....services.parent_onboarding import ResourceGuideService
from ..auth import get_current_user
from ..dependencies import require_authenticated, require_staff

router = APIRouter()


# ============================================================================
# Helpers
# ============================================================================

def _build_item_response(
    item: ParentResourceGuideItem,
    *,
    stale_after_months: int,
    lang: Optional[str] = None,
) -> ResourceGuideItemResponse:
    verified_by_name: Optional[str] = None
    if item.verified_by is not None:
        full = getattr(item.verified_by, "full_name", None)
        if full and str(full).strip():
            verified_by_name = str(full)
        else:
            email = getattr(item.verified_by, "email", None) or ""
            verified_by_name = email.split("@", 1)[0] if email else f"#{item.verified_by_id}"

    translations_raw: dict = dict(item.translations or {})
    title_out: str = item.title
    description_out: Optional[str] = item.description
    if lang:
        entry = translations_raw.get(lang) or {}
        if isinstance(entry, dict):
            t_title = entry.get("title")
            if isinstance(t_title, str) and t_title.strip():
                title_out = t_title
            t_desc = entry.get("description")
            if isinstance(t_desc, str) and t_desc.strip():
                description_out = t_desc

    return ResourceGuideItemResponse(
        id=item.id,
        section_id=item.section_id,
        title=title_out,
        description=description_out,
        contact_info=item.contact_info,
        url=item.url,
        languages=list(item.languages or []),
        translations=translations_raw,
        display_order=item.display_order,
        last_verified_at=item.last_verified_at,
        verified_by_id=item.verified_by_id,
        verified_by_name=verified_by_name,
        stale=ResourceGuideService.is_item_stale(item, stale_after_months),
        open_flag_count=ResourceGuideService.count_open_flags(item),
    )


def _build_section_response(
    section: ParentResourceGuideSection,
    *,
    stale_after_months: int,
    lang: Optional[str] = None,
) -> ResourceGuideSectionResponse:
    return ResourceGuideSectionResponse(
        id=section.id,
        title_key=section.title_key,
        icon=section.icon,
        display_order=section.display_order,
        is_active=section.is_active,
        branch_id=section.branch_id,
        items=[
            _build_item_response(it, stale_after_months=stale_after_months, lang=lang)
            for it in section.items
        ],
        created_at=getattr(section, "created_at", None),
    )


def _build_flag_response(flag: ParentResourceGuideFlag) -> ResourceGuideFlagResponse:
    flagged_by_name: Optional[str] = None
    if flag.flagged_by is not None:
        full = getattr(flag.flagged_by, "full_name", None)
        flagged_by_name = (
            str(full)
            if full and str(full).strip()
            else (getattr(flag.flagged_by, "email", "") or "").split("@", 1)[0] or None
        )
    resolved_by_name: Optional[str] = None
    if flag.resolved_by is not None:
        full = getattr(flag.resolved_by, "full_name", None)
        resolved_by_name = (
            str(full)
            if full and str(full).strip()
            else (getattr(flag.resolved_by, "email", "") or "").split("@", 1)[0] or None
        )
    snapshot: Optional[ResourceGuideFlagItemSnapshot] = None
    if flag.item is not None:
        snapshot = ResourceGuideFlagItemSnapshot(
            id=flag.item.id,
            section_id=flag.item.section_id,
            title=flag.item.title,
            contact_info=flag.item.contact_info,
            url=flag.item.url,
        )
    return ResourceGuideFlagResponse(
        id=flag.id,
        item_id=flag.item_id,
        flagged_by_id=flag.flagged_by_id,
        flagged_by_name=flagged_by_name,
        reason_code=flag.reason_code,
        comment=flag.comment,
        status=flag.status,
        resolution=flag.resolution,
        resolution_notes=flag.resolution_notes,
        resolved_by_id=flag.resolved_by_id,
        resolved_by_name=resolved_by_name,
        resolved_at=flag.resolved_at,
        created_at=flag.created_at,
        updated_at=flag.updated_at,
        item=snapshot,
    )


# ============================================================================
# Routes
# ============================================================================

@router.get("/resource-guide/sections", response_model=list[ResourceGuideSectionResponse])
async def list_resource_guide_sections(
    branch_id: Optional[int] = None,
    lang: Optional[str] = Query(
        None,
        max_length=10,
        pattern=r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})?$",
        description=(
            "Optional ISO 639-1 code (lowercase, with optional region tag) "
            "to substitute title/description with that language's "
            "translation when present."
        ),
    ),
    db: AsyncSession = Depends(get_db),
):
    """List resource guide sections with items (public).

    Multilingual: when `lang` is provided, items whose `translations[lang]`
    has a non-empty `title`/`description` get those substituted at the
    top level. Items lacking that language are still returned -- the
    client decides whether to mark them with a fallback marker. The
    `translations` map is always present in each item for the staff edit
    surface.
    """
    from ....core.config import get_settings
    stale_months = get_settings().parent_resource_stale_after_months
    sections = await ResourceGuideService.list_sections(db, branch_id=branch_id)
    return [
        _build_section_response(s, stale_after_months=stale_months, lang=lang)
        for s in sections
    ]


@router.post("/resource-guide/sections", response_model=ResourceGuideSectionResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_guide_section(
    data: ResourceGuideSectionCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a resource guide section (staff-only)."""
    section = await ResourceGuideService.create_section(db, data.model_dump())
    return ResourceGuideSectionResponse.model_validate(section)


@router.patch("/resource-guide/sections/{section_id}", response_model=ResourceGuideSectionResponse)
async def update_resource_guide_section(
    section_id: int,
    data: ResourceGuideSectionUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a resource guide section (staff-only)."""
    result = await db.execute(
        select(ParentResourceGuideSection).where(ParentResourceGuideSection.id == section_id)
    )
    section = result.scalar_one_or_none()
    if not section:
        raise HTTPException(status_code=404, detail="Section not found")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(section, key, value)
    await db.flush()
    await db.refresh(section)
    return ResourceGuideSectionResponse.model_validate(section)


@router.post("/resource-guide/sections/{section_id}/items", response_model=ResourceGuideItemResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_guide_item(
    section_id: int,
    data: ResourceGuideItemCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add an item to a resource guide section (staff-only)."""
    item = await ResourceGuideService.create_item(db, section_id, data.model_dump())
    return ResourceGuideItemResponse.model_validate(item)


@router.patch("/resource-guide/items/{item_id}", response_model=ResourceGuideItemResponse)
async def update_resource_guide_item(
    item_id: int,
    data: ResourceGuideItemUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a resource guide item (staff-only).

    `translations` is diff-merged: each key in the incoming map either
    sets (or replaces) a single language's entry, or -- when the value
    is null -- removes that language. Languages not mentioned in the
    payload are preserved untouched. Omitting `translations` from the
    payload leaves the whole map alone (the common case for non-i18n
    edits).
    """
    result = await db.execute(
        select(ParentResourceGuideItem).where(ParentResourceGuideItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    payload = data.model_dump(exclude_unset=True)
    incoming_translations = payload.pop("translations", None)
    for key, value in payload.items():
        setattr(item, key, value)

    if incoming_translations is not None:
        merged: dict = dict(item.translations or {})
        for lang_code, entry in incoming_translations.items():
            if entry is None:
                merged.pop(lang_code, None)
            else:
                merged[lang_code] = entry
        item.translations = merged

    await db.flush()
    await db.refresh(item)
    return ResourceGuideItemResponse.model_validate(item)


@router.delete("/resource-guide/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource_guide_item(
    item_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a resource guide item (staff-only)."""
    result = await db.execute(
        select(ParentResourceGuideItem).where(ParentResourceGuideItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    await db.delete(item)


@router.post(
    "/resource-guide/items/{item_id}/verify",
    response_model=ResourceGuideItemResponse,
)
async def verify_resource_guide_item(
    item_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a resource guide item as freshly verified (staff-only).

    Sets `last_verified_at = now()`, `verified_by_id = current_user.id`,
    auto-resolves any open flags on the item with `verified_current`.
    Idempotent: re-verifying just advances the timestamp.
    """
    item = await ResourceGuideService.verify_item(db, item_id, current_user)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    from ....core.config import get_settings
    return _build_item_response(
        item, stale_after_months=get_settings().parent_resource_stale_after_months
    )


@router.post(
    "/resource-guide/items/{item_id}/flags",
    response_model=ResourceGuideFlagResponse,
    status_code=status.HTTP_201_CREATED,
)
async def flag_resource_guide_item(
    item_id: int,
    data: ResourceGuideFlagCreate,
    current_user: User = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db),
):
    """File a flag against a resource guide item.

    Any authenticated user may flag (the staff page is the only entry today,
    but the endpoint is intentionally open so a future patron-facing
    resources page can reuse it). The route is fail-secure: an unknown
    `reason_code` 422s at the schema layer (StrictInputSchema + enum
    validation). On success the last verifier / editor is notified
    out-of-band; route returns the new flag immediately.
    """
    flag = await ResourceGuideService.flag_item(
        db,
        item_id=item_id,
        flagged_by=current_user,
        reason_code=data.reason_code,
        comment=data.comment,
    )
    if flag is None:
        raise HTTPException(status_code=404, detail="Item not found")

    try:
        from ...services.parent_resource_flag_notify import notify_flag_filed
        await notify_flag_filed(db, flag, flagged_by=current_user)
    except Exception:  # pragma: no cover -- notification failures are out-of-band
        _logging.getLogger(__name__).exception(
            "parent_resource_flag notification failed; flag still created",
            extra={"flag_id": flag.id, "item_id": flag.item_id},
        )

    flag_full = (
        await db.execute(
            select(ParentResourceGuideFlag)
            .options(
                selectinload(ParentResourceGuideFlag.item),
                selectinload(ParentResourceGuideFlag.flagged_by),
                selectinload(ParentResourceGuideFlag.resolved_by),
            )
            .where(ParentResourceGuideFlag.id == flag.id)
        )
    ).scalar_one()
    return _build_flag_response(flag_full)


@router.get(
    "/resource-guide/flags",
    response_model=list[ResourceGuideFlagResponse],
)
async def list_resource_guide_flags(
    status_filter: Optional[ResourceGuideFlagStatus] = Query(
        None, alias="status",
        description="Filter by status; omit to return all statuses.",
    ),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff queue: list flags ordered oldest first (FIFO triage)."""
    flags = await ResourceGuideService.list_flags(db, status=status_filter)
    return [_build_flag_response(f) for f in flags]


@router.patch(
    "/resource-guide/flags/{flag_id}",
    response_model=ResourceGuideFlagResponse,
)
async def patch_resource_guide_flag(
    flag_id: int,
    data: ResourceGuideFlagUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Patch a flag's status / resolution (staff-only).

    The convenience verb is `POST /items/{id}/verify`, which auto-resolves
    all flags on the item; this endpoint exists for the queue UI to triage
    a single flag without forcing a verify-or-edit (e.g., dismissing an
    invalid flag).
    """
    flag = await ResourceGuideService.resolve_flag(
        db,
        flag_id=flag_id,
        user=current_user,
        new_status=data.status,
        resolution=data.resolution,
        resolution_notes=data.resolution_notes,
    )
    if flag is None:
        raise HTTPException(status_code=404, detail="Flag not found")
    return _build_flag_response(flag)
