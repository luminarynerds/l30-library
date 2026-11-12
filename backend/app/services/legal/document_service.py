# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.error_codes import ErrorCode
from ...core.exceptions import ResourceNotFoundError

from ...models.legal import (
    LegalForm, FormStatus, LegalFormPacket, LegalFormPacketItem,
    LegalGuide
)

logger = get_logger(__name__)


# ============================================================================
# Legal Form Services
# ============================================================================

async def get_form_by_id(
    db: AsyncSession,
    form_id: int
) -> Optional[LegalForm]:
    result = await db.execute(
        select(LegalForm)
        .options(selectinload(LegalForm.topic))
        .where(LegalForm.id == form_id)
    )
    return result.scalar_one_or_none()


async def list_forms(
    db: AsyncSession,
    topic_id: Optional[int] = None,
    jurisdiction: Optional[str] = None,
    court_type: Optional[str] = None,
    difficulty_level: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[FormStatus] = FormStatus.active,
    query: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalForm], int]:
    base_query = select(LegalForm).options(selectinload(LegalForm.topic))
    count_query = select(func.count(LegalForm.id))

    filters = []
    if topic_id is not None:
        filters.append(LegalForm.topic_id == topic_id)
    if jurisdiction is not None:
        filters.append(LegalForm.jurisdiction == jurisdiction)
    if court_type is not None:
        filters.append(LegalForm.court_type == court_type)
    if difficulty_level is not None:
        filters.append(LegalForm.difficulty_level == difficulty_level)
    if language is not None:
        filters.append(LegalForm.languages_available.any(language))
    if status is not None:
        filters.append(LegalForm.status == status)
    if query:
        safe_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_filter = or_(
            LegalForm.title.ilike(f"%{safe_query}%"),
            LegalForm.plain_language_title.ilike(f"%{safe_query}%"),
            LegalForm.form_number.ilike(f"%{safe_query}%"),
            LegalForm.description.ilike(f"%{safe_query}%")
        )
        filters.append(search_filter)

    if filters:
        base_query = base_query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get paginated results
    base_query = base_query.order_by(LegalForm.title)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    forms = result.scalars().all()

    return forms, total


async def search_forms(
    db: AsyncSession,
    query: str,
    filters: Optional[dict] = None,
    skip: int = 0,
    limit: int = 20
) -> tuple[list[LegalForm], int]:
    from ._utils import log_search

    # Log search for analytics
    await log_search(db, query, "forms", filters or {})

    # Build search query
    base_query = select(LegalForm).options(selectinload(LegalForm.topic))

    safe_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    search_filter = or_(
        LegalForm.title.ilike(f"%{safe_query}%"),
        LegalForm.plain_language_title.ilike(f"%{safe_query}%"),
        LegalForm.form_number.ilike(f"%{safe_query}%"),
        LegalForm.description.ilike(f"%{safe_query}%"),
        LegalForm.when_to_use.ilike(f"%{safe_query}%")
    )

    conditions = [search_filter, LegalForm.status == FormStatus.active]

    if filters:
        if filters.get("jurisdiction"):
            conditions.append(LegalForm.jurisdiction == filters["jurisdiction"])
        if filters.get("court_type"):
            conditions.append(LegalForm.court_type == filters["court_type"])
        if filters.get("difficulty_level"):
            conditions.append(LegalForm.difficulty_level == filters["difficulty_level"])
        if filters.get("language"):
            conditions.append(LegalForm.languages_available.any(filters["language"]))

    base_query = base_query.where(and_(*conditions))
    count_query = select(func.count(LegalForm.id)).where(and_(*conditions))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    forms = result.scalars().all()

    return forms, total


async def create_form(
    db: AsyncSession,
    form_data: dict,
    created_by_id: Optional[int] = None
) -> LegalForm:
    from ._utils import log_content_change

    form = LegalForm(**form_data, created_by_id=created_by_id)
    db.add(form)
    await db.commit()
    await db.refresh(form)

    # Log creation
    await log_content_change(db, "form", form.id, "create", None, created_by_id)

    return form


async def update_form(
    db: AsyncSession,
    form_id: int,
    form_data: dict,
    updated_by_id: Optional[int] = None
) -> LegalForm:
    from ._utils import log_content_change

    form = await get_form_by_id(db, form_id)
    if not form:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Legal form not found"
        )

    # Capture old values for audit
    old_values = {key: getattr(form, key) for key in form_data.keys() if hasattr(form, key)}

    for key, value in form_data.items():
        if value is not None:
            setattr(form, key, value)

    await db.commit()
    await db.refresh(form)

    # Log update
    await log_content_change(
        db, "form", form.id, "update",
        {"old": old_values, "new": form_data},
        updated_by_id
    )

    return form


async def increment_form_views(
    db: AsyncSession,
    form_id: int
) -> None:
    form = await get_form_by_id(db, form_id)
    if form:
        form.view_count = (form.view_count or 0) + 1
        await db.commit()


async def increment_form_downloads(
    db: AsyncSession,
    form_id: int
) -> None:
    form = await get_form_by_id(db, form_id)
    if form:
        form.download_count = (form.download_count or 0) + 1
        await db.commit()


# ============================================================================
# Legal Form Packet Services
# ============================================================================

async def get_packet_by_id(
    db: AsyncSession,
    packet_id: int
) -> Optional[LegalFormPacket]:
    result = await db.execute(
        select(LegalFormPacket)
        .options(
            selectinload(LegalFormPacket.forms).selectinload(LegalFormPacketItem.form),
            selectinload(LegalFormPacket.topic)
        )
        .where(LegalFormPacket.id == packet_id)
    )
    return result.scalar_one_or_none()


async def get_packet_by_slug(
    db: AsyncSession,
    slug: str
) -> Optional[LegalFormPacket]:
    result = await db.execute(
        select(LegalFormPacket)
        .options(
            selectinload(LegalFormPacket.forms).selectinload(LegalFormPacketItem.form),
            selectinload(LegalFormPacket.topic)
        )
        .where(LegalFormPacket.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_packets(
    db: AsyncSession,
    topic_id: Optional[int] = None,
    jurisdiction: Optional[str] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalFormPacket], int]:
    base_query = select(LegalFormPacket).options(
        selectinload(LegalFormPacket.forms),
        selectinload(LegalFormPacket.topic)
    )
    count_query = select(func.count(LegalFormPacket.id))

    filters = [LegalFormPacket.is_active == is_active]
    if topic_id is not None:
        filters.append(LegalFormPacket.topic_id == topic_id)
    if jurisdiction is not None:
        filters.append(LegalFormPacket.jurisdiction == jurisdiction)

    base_query = base_query.where(and_(*filters))
    count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(LegalFormPacket.name)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    packets = result.scalars().all()

    return packets, total


async def create_packet(
    db: AsyncSession,
    packet_data: dict,
    forms_data: list[dict],
    created_by_id: Optional[int] = None
) -> LegalFormPacket:
    packet = LegalFormPacket(**packet_data, created_by_id=created_by_id)
    db.add(packet)
    await db.flush()

    # Add forms
    for form_item in forms_data:
        item = LegalFormPacketItem(packet_id=packet.id, **form_item)
        db.add(item)

    await db.commit()
    await db.refresh(packet)
    return packet


async def update_packet(
    db: AsyncSession,
    packet_id: int,
    packet_data: dict
) -> LegalFormPacket:
    packet = await get_packet_by_id(db, packet_id)
    if not packet:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Form packet not found"
        )

    for key, value in packet_data.items():
        if value is not None:
            setattr(packet, key, value)

    await db.commit()
    await db.refresh(packet)
    return packet


async def add_form_to_packet(
    db: AsyncSession,
    packet_id: int,
    form_data: dict
) -> LegalFormPacketItem:
    packet = await get_packet_by_id(db, packet_id)
    if not packet:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Form packet not found"
        )

    item = LegalFormPacketItem(packet_id=packet_id, **form_data)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def remove_form_from_packet(
    db: AsyncSession,
    packet_id: int,
    form_id: int
) -> None:
    result = await db.execute(
        select(LegalFormPacketItem)
        .where(
            LegalFormPacketItem.packet_id == packet_id,
            LegalFormPacketItem.form_id == form_id
        )
    )
    item = result.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.commit()


# ============================================================================
# Legal Guide Services
# ============================================================================

async def get_guide_by_id(
    db: AsyncSession,
    guide_id: int
) -> Optional[LegalGuide]:
    result = await db.execute(
        select(LegalGuide)
        .options(selectinload(LegalGuide.topic))
        .where(LegalGuide.id == guide_id)
    )
    return result.scalar_one_or_none()


async def get_guide_by_slug(
    db: AsyncSession,
    slug: str
) -> Optional[LegalGuide]:
    result = await db.execute(
        select(LegalGuide)
        .options(selectinload(LegalGuide.topic))
        .where(LegalGuide.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_guides(
    db: AsyncSession,
    topic_id: Optional[int] = None,
    is_published: bool = True,
    is_featured: Optional[bool] = None,
    reading_level: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalGuide], int]:
    base_query = select(LegalGuide).options(selectinload(LegalGuide.topic))
    count_query = select(func.count(LegalGuide.id))

    filters = [LegalGuide.is_published == is_published]
    if topic_id is not None:
        filters.append(LegalGuide.topic_id == topic_id)
    if is_featured is not None:
        filters.append(LegalGuide.is_featured == is_featured)
    if reading_level is not None:
        filters.append(LegalGuide.reading_level == reading_level)

    base_query = base_query.where(and_(*filters))
    count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(LegalGuide.title)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    guides = result.scalars().all()

    return guides, total


async def create_guide(
    db: AsyncSession,
    guide_data: dict,
    created_by_id: Optional[int] = None
) -> LegalGuide:
    from ._utils import log_content_change

    guide = LegalGuide(**guide_data, created_by_id=created_by_id)
    db.add(guide)
    await db.commit()
    await db.refresh(guide)

    # Log creation
    await log_content_change(db, "guide", guide.id, "create", None, created_by_id)

    return guide


async def update_guide(
    db: AsyncSession,
    guide_id: int,
    guide_data: dict,
    updated_by_id: Optional[int] = None
) -> LegalGuide:
    from ._utils import log_content_change

    guide = await get_guide_by_id(db, guide_id)
    if not guide:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Legal guide not found"
        )

    for key, value in guide_data.items():
        if value is not None:
            setattr(guide, key, value)

    await db.commit()
    await db.refresh(guide)

    # Log update
    await log_content_change(db, "guide", guide.id, "update", guide_data, updated_by_id)

    return guide


async def publish_guide(
    db: AsyncSession,
    guide_id: int,
    published_by_id: Optional[int] = None
) -> LegalGuide:
    from datetime import datetime, timezone
    from ._utils import log_content_change

    guide = await get_guide_by_id(db, guide_id)
    if not guide:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Legal guide not found"
        )

    guide.is_published = True
    guide.published_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(guide)

    # Log publish
    await log_content_change(db, "guide", guide.id, "publish", None, published_by_id)

    return guide


async def record_guide_helpful(
    db: AsyncSession,
    guide_id: int,
    was_helpful: bool
) -> None:
    guide = await get_guide_by_id(db, guide_id)
    if guide:
        if was_helpful:
            guide.helpful_count = (guide.helpful_count or 0) + 1
        else:
            guide.not_helpful_count = (guide.not_helpful_count or 0) + 1
        await db.commit()
