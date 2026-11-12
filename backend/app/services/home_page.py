# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from __future__ import annotations

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..core.cache import get_redis
from ..models.catalog import CatalogingStatus, CatalogItem, SensitivityLevel
from ..models.home import (
    HomeHeroPick,
    HomePageConfig,
    HomeShelf,
    HomeShelfQueryKind,
)
from ..models.staff_picks import StaffPicksItem, StaffPicksList
from ..schemas.home import (
    HeroPickRead,
    HomeItemCard,
    HomePageConfigRead,
    HomePageRead,
    ShelfRead,
)


logger = get_logger(__name__)

HOME_PAGE_CACHE_KEY = "home:page"
HOME_PAGE_CACHE_TTL = 60  # seconds


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------


async def _cache_get() -> Optional[HomePageRead]:
    try:
        redis = await get_redis()
    except Exception:  # noqa: BLE001 — fail-open: home page must render even if Redis bootstrap raises
        return None
    if redis is None:
        return None
    try:
        raw = await redis.get(HOME_PAGE_CACHE_KEY)
    except RedisError:
        return None
    if not raw:
        return None
    try:
        return HomePageRead.model_validate_json(raw)
    except (ValueError, TypeError):
        return None


async def _cache_set(payload: HomePageRead) -> None:
    try:
        redis = await get_redis()
    except Exception:  # noqa: BLE001 — fail-open: cache write must never break home page response
        return
    if redis is None:
        return
    try:
        await redis.set(
            HOME_PAGE_CACHE_KEY,
            payload.model_dump_json(),
            ex=HOME_PAGE_CACHE_TTL,
        )
    except RedisError:
        logger.debug("home page cache set failed", exc_info=True)


async def bust_home_page_cache() -> None:
    try:
        redis = await get_redis()
    except Exception:  # noqa: BLE001 — fail-open: cache bust is best-effort, must not raise to callers
        return
    if redis is None:
        return
    try:
        await redis.delete(HOME_PAGE_CACHE_KEY)
    except RedisError:
        logger.debug("home page cache delete failed", exc_info=True)


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def is_public_item(item: CatalogItem) -> bool:
    return (
        item.cataloging_status == CatalogingStatus.CATALOGED
        and item.sensitivity_level == SensitivityLevel.PUBLIC
    )


def _apply_public_filter(stmt):
    return stmt.where(
        CatalogItem.cataloging_status == CatalogingStatus.CATALOGED,
        CatalogItem.sensitivity_level == SensitivityLevel.PUBLIC,
    )


def _to_item_card(item: CatalogItem) -> HomeItemCard:
    return HomeItemCard(
        id=item.id,
        title=item.title,
        author=item.author,
        item_type=getattr(item.item_type, "value", None) if item.item_type else None,
    )


async def _resolve_hero(db: AsyncSession) -> Optional[HeroPickRead]:
    now = datetime.now(timezone.utc)
    stmt = (
        select(HomeHeroPick)
        .where(HomeHeroPick.active_from <= now)
        .where(
            (HomeHeroPick.active_to.is_(None)) | (HomeHeroPick.active_to >= now)
        )
        .order_by(HomeHeroPick.active_from.desc())
        .options(selectinload(HomeHeroPick.item))  # [[feedback_l30_async_property_landmine]]
        .limit(1)
    )
    res = await db.execute(stmt)
    pick = res.scalars().first()
    if pick is None or pick.item is None:
        return None
    if not is_public_item(pick.item):
        # Active hero references a non-public item (uncataloged or sensitive);
        # treat as "no hero" rather than render a card with a broken cover.
        return None
    return HeroPickRead(
        id=pick.id,
        item=_to_item_card(pick.item),
        annotation_md=pick.annotation_md,
        cta_label=pick.cta_label,
        cta_href=pick.cta_href,
        active_from=pick.active_from,
        active_to=pick.active_to,
    )


async def _resolve_shelf_items(
    db: AsyncSession, shelf: HomeShelf
) -> List[CatalogItem]:
    params = shelf.query_params or {}
    limit = max(1, min(shelf.max_items or 6, 24))
    # Restrict every shelf to anon-visible items (cataloged + public).
    # Without this, uncataloged/sensitive records leak into the public home
    # page and the cover proxy 404s their jackets while titles still render.
    base = _apply_public_filter(select(CatalogItem))

    kind = shelf.query_kind
    if isinstance(kind, str):
        kind = HomeShelfQueryKind(kind)

    if kind == HomeShelfQueryKind.new_arrivals:
        stmt = base.order_by(CatalogItem.created_at.desc()).limit(limit)
    elif kind == HomeShelfQueryKind.staff_picks:
        # Aggregate the staff-picks lists curated at /staff/picks (the same
        # data /picks renders), newest additions first. The legacy
        # CatalogItem.staff_pick flag is orphaned: no UI ever set it.
        stmt = (
            base.join(
                StaffPicksItem, StaffPicksItem.catalog_item_id == CatalogItem.id
            )
            .join(StaffPicksList, StaffPicksItem.list_id == StaffPicksList.id)
            .where(StaffPicksList.is_active.is_(True))
            .order_by(StaffPicksItem.added_at.desc())
            # Over-fetch (an item may sit in several active lists) so the
            # post-dedupe result can still fill the shelf; capped to `limit`
            # in the loop below. 200 is ample headroom for realistic list sizes.
            .limit(200)
        )
        res = await db.execute(stmt)
        seen: set[int] = set()
        items: List[CatalogItem] = []
        for item in res.scalars().all():
            if item.id in seen:
                continue
            seen.add(item.id)
            items.append(item)
            if len(items) >= limit:
                break
        return items
    elif kind == HomeShelfQueryKind.subject:
        subject = (params.get("subject") or "").strip()
        if not subject:
            return []
        # catalog_items.subjects is String(500) with mixed comma/semicolon
        # delimiters per [[feedback_l30_catalog_subjects_delimiters]]; v1
        # ships a substring match. A future migration can split into rows.
        stmt = (
            base.where(CatalogItem.subjects.ilike(f"%{subject}%"))
            .order_by(CatalogItem.created_at.desc())
            .limit(limit)
        )
    elif kind == HomeShelfQueryKind.format:
        # Catalog has no single "format" column; spec maps to media_format.
        media_format = (params.get("media_format") or params.get("format") or "").strip()
        if not media_format:
            return []
        stmt = (
            base.where(CatalogItem.media_format == media_format)
            .order_by(CatalogItem.created_at.desc())
            .limit(limit)
        )
    elif kind == HomeShelfQueryKind.circulation_top:
        # TODO: implement once a circulation_events / aggregated checkout
        # source is in place. Returning empty keeps the shelf hidden until
        # data exists.
        return []
    elif kind == HomeShelfQueryKind.manual_list:
        ids = params.get("item_ids") or []
        if not isinstance(ids, list) or not ids:
            return []
        # Preserve the admin-specified order.
        stmt = base.where(CatalogItem.id.in_(ids)).limit(limit)
        res = await db.execute(stmt)
        rows = {item.id: item for item in res.scalars().all()}
        return [rows[i] for i in ids if i in rows][:limit]
    else:  # pragma: no cover - defensive
        return []

    res = await db.execute(stmt)
    return list(res.scalars().all())


async def _resolve_config(db: AsyncSession) -> Optional[HomePageConfigRead]:
    res = await db.execute(select(HomePageConfig).where(HomePageConfig.id == 1))
    cfg = res.scalars().first()
    if cfg is None:
        return None
    return HomePageConfigRead.model_validate(cfg)


async def resolve_home_page(
    db: AsyncSession, *, use_cache: bool = True
) -> HomePageRead:

    if use_cache:
        cached = await _cache_get()
        if cached is not None:
            return cached

    config = await _resolve_config(db)
    hero = None
    if config is None or config.hero_visible:
        hero = await _resolve_hero(db)

    shelves_stmt = (
        select(HomeShelf)
        .where(HomeShelf.is_active.is_(True))
        .order_by(HomeShelf.sort_order.asc(), HomeShelf.id.asc())
    )
    res = await db.execute(shelves_stmt)
    shelf_rows = list(res.scalars().all())

    resolved: List[ShelfRead] = []
    for shelf in shelf_rows:
        items = await _resolve_shelf_items(db, shelf)
        if not items:
            # Drop empty shelves — they never appear with items:[] in the response.
            continue
        resolved.append(
            ShelfRead(
                id=shelf.id,
                slug=shelf.slug,
                heading=shelf.heading,
                description=shelf.description,
                view_all_href=shelf.view_all_href,
                items=[_to_item_card(it) for it in items],
            )
        )

    payload = HomePageRead(config=config, hero=hero, shelves=resolved)

    if use_cache:
        await _cache_set(payload)

    return payload
