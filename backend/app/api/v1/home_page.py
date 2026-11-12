# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""HTTP routes for the data-driven home page.

Public:
- ``GET /api/v1/home/page`` — composite payload built from `home_*` tables.

Admin (require ADMIN or SUPER_ADMIN role):
- ``GET/POST/PATCH/DELETE /api/v1/home/admin/hero-picks``
- ``GET/POST/PATCH/DELETE /api/v1/home/admin/shelves``
- ``GET/PATCH /api/v1/home/admin/config``

All admin writes invalidate the Redis cache for the public payload.

Router-shadowing note: register literal-path routes (``/page``) before any
``/{id}`` patterns per [[feedback_l30_fastapi_router_shadowing]] — done here
by putting the public router and admin sub-resources in separate sub-routers
with distinct prefixes.
"""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.authorization import require_role
from ...core.database import get_db
from ...models.catalog import CatalogItem
from ...models.home import HomeHeroPick, HomePageConfig, HomeShelf
from ...models.user import User, UserRole
from ...schemas.home import (
    HeroPickCreate,
    HeroPickRead,
    HeroPickUpdate,
    HomeItemCard,
    HomePageConfigRead,
    HomePageConfigUpdate,
    HomePageRead,
    ShelfAdminRead,
    ShelfCreate,
    ShelfUpdate,
)
from ...services.home_page import (
    bust_home_page_cache,
    is_public_item,
    resolve_home_page,
)


router = APIRouter(prefix="/home", tags=["home"])

admin_router = APIRouter(
    prefix="/home/admin",
    tags=["home-admin"],
    dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN))],
)


# ---------------------------------------------------------------------------
# Public endpoint
# ---------------------------------------------------------------------------


@router.get("/page", response_model=HomePageRead)
async def get_home_page(db: AsyncSession = Depends(get_db)) -> HomePageRead:
    """Return the resolved home page payload (cached 60s in Redis)."""
    return await resolve_home_page(db)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_hero_with_item(
    db: AsyncSession, hero_id: int
) -> HomeHeroPick:
    from sqlalchemy.orm import selectinload

    stmt = (
        select(HomeHeroPick)
        .where(HomeHeroPick.id == hero_id)
        .options(selectinload(HomeHeroPick.item))
    )
    res = await db.execute(stmt)
    pick = res.scalars().first()
    if pick is None:
        raise HTTPException(status_code=404, detail="Hero pick not found")
    return pick


# _resolve_hero drops heroes whose item is not cataloged + public, so
# accepting such an item here would save a hero that never renders,
# with no feedback anywhere.
async def _require_featurable_item(db: AsyncSession, item_id: int) -> None:
    item = await db.get(CatalogItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Catalog item not found")
    if not is_public_item(item):
        raise HTTPException(
            status_code=422,
            detail=(
                "This item can't be featured yet. Hero picks only display "
                "items that are fully cataloged and publicly visible; this "
                f"one is currently '{item.cataloging_status.value}' with "
                f"'{item.sensitivity_level.value}' sensitivity."
            ),
        )


def _hero_to_read(pick: HomeHeroPick) -> HeroPickRead:
    return HeroPickRead(
        id=pick.id,
        item=HomeItemCard(
            id=pick.item.id,
            title=pick.item.title,
            author=pick.item.author,
            item_type=getattr(pick.item.item_type, "value", None)
            if pick.item and pick.item.item_type
            else None,
        ),
        annotation_md=pick.annotation_md,
        cta_label=pick.cta_label,
        cta_href=pick.cta_href,
        active_from=pick.active_from,
        active_to=pick.active_to,
    )


# ---------------------------------------------------------------------------
# Admin: hero picks
# ---------------------------------------------------------------------------


@admin_router.get("/hero-picks", response_model=List[HeroPickRead])
async def list_hero_picks(db: AsyncSession = Depends(get_db)) -> List[HeroPickRead]:
    from sqlalchemy.orm import selectinload

    stmt = (
        select(HomeHeroPick)
        .options(selectinload(HomeHeroPick.item))
        .order_by(HomeHeroPick.active_from.desc())
    )
    res = await db.execute(stmt)
    return [_hero_to_read(p) for p in res.scalars().all()]


@admin_router.post(
    "/hero-picks", response_model=HeroPickRead, status_code=status.HTTP_201_CREATED
)
async def create_hero_pick(
    payload: HeroPickCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    ),
) -> HeroPickRead:
    await _require_featurable_item(db, payload.item_id)
    pick = HomeHeroPick(
        item_id=payload.item_id,
        annotation_md=payload.annotation_md,
        cta_label=payload.cta_label,
        cta_href=payload.cta_href,
        active_from=payload.active_from,
        active_to=payload.active_to,
        created_by=current_user.id,
    )
    db.add(pick)
    await db.commit()
    await db.refresh(pick)
    await bust_home_page_cache()
    pick = await _load_hero_with_item(db, pick.id)
    return _hero_to_read(pick)


@admin_router.patch("/hero-picks/{hero_id}", response_model=HeroPickRead)
async def update_hero_pick(
    hero_id: int,
    payload: HeroPickUpdate,
    db: AsyncSession = Depends(get_db),
) -> HeroPickRead:
    pick = await _load_hero_with_item(db, hero_id)
    updates = payload.model_dump(exclude_unset=True)
    if updates.get("item_id") is not None:
        await _require_featurable_item(db, updates["item_id"])
    for field, value in updates.items():
        setattr(pick, field, value)
    await db.commit()
    await db.refresh(pick)
    await bust_home_page_cache()
    pick = await _load_hero_with_item(db, pick.id)
    return _hero_to_read(pick)


@admin_router.delete("/hero-picks/{hero_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hero_pick(
    hero_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    pick = await db.get(HomeHeroPick, hero_id)
    if pick is None:
        raise HTTPException(status_code=404, detail="Hero pick not found")
    await db.delete(pick)
    await db.commit()
    await bust_home_page_cache()


# ---------------------------------------------------------------------------
# Admin: shelves
# ---------------------------------------------------------------------------


@admin_router.get("/shelves", response_model=List[ShelfAdminRead])
async def list_shelves(db: AsyncSession = Depends(get_db)) -> List[ShelfAdminRead]:
    res = await db.execute(
        select(HomeShelf).order_by(HomeShelf.sort_order.asc(), HomeShelf.id.asc())
    )
    return [ShelfAdminRead.model_validate(s) for s in res.scalars().all()]


@admin_router.post(
    "/shelves", response_model=ShelfAdminRead, status_code=status.HTTP_201_CREATED
)
async def create_shelf(
    payload: ShelfCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    ),
) -> ShelfAdminRead:
    shelf = HomeShelf(
        slug=payload.slug,
        heading=payload.heading,
        description=payload.description,
        query_kind=payload.query_kind.value,
        query_params=payload.query_params,
        sort_order=payload.sort_order,
        is_active=payload.is_active,
        max_items=payload.max_items,
        view_all_href=payload.view_all_href,
        created_by=current_user.id,
    )
    db.add(shelf)
    await db.commit()
    await db.refresh(shelf)
    await bust_home_page_cache()
    return ShelfAdminRead.model_validate(shelf)


@admin_router.patch("/shelves/{shelf_id}", response_model=ShelfAdminRead)
async def update_shelf(
    shelf_id: int,
    payload: ShelfUpdate,
    db: AsyncSession = Depends(get_db),
) -> ShelfAdminRead:
    shelf = await db.get(HomeShelf, shelf_id)
    if shelf is None:
        raise HTTPException(status_code=404, detail="Shelf not found")
    data = payload.model_dump(exclude_unset=True)
    if "query_kind" in data and data["query_kind"] is not None:
        data["query_kind"] = data["query_kind"].value
    for field, value in data.items():
        setattr(shelf, field, value)
    await db.commit()
    await db.refresh(shelf)
    await bust_home_page_cache()
    return ShelfAdminRead.model_validate(shelf)


@admin_router.delete("/shelves/{shelf_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shelf(
    shelf_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    shelf = await db.get(HomeShelf, shelf_id)
    if shelf is None:
        raise HTTPException(status_code=404, detail="Shelf not found")
    await db.delete(shelf)
    await db.commit()
    await bust_home_page_cache()


# ---------------------------------------------------------------------------
# Admin: page config (singleton)
# ---------------------------------------------------------------------------


async def _get_or_create_config(db: AsyncSession) -> HomePageConfig:
    res = await db.execute(select(HomePageConfig).where(HomePageConfig.id == 1))
    cfg = res.scalars().first()
    if cfg is None:
        cfg = HomePageConfig(id=1)
        db.add(cfg)
        await db.commit()
        await db.refresh(cfg)
    return cfg


@admin_router.get("/config", response_model=HomePageConfigRead)
async def get_config(db: AsyncSession = Depends(get_db)) -> HomePageConfigRead:
    cfg = await _get_or_create_config(db)
    return HomePageConfigRead.model_validate(cfg)


@admin_router.patch("/config", response_model=HomePageConfigRead)
async def update_config(
    payload: HomePageConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.SUPER_ADMIN)
    ),
) -> HomePageConfigRead:
    cfg = await _get_or_create_config(db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(cfg, field, value)
    cfg.updated_by = current_user.id
    await db.commit()
    await db.refresh(cfg)
    await bust_home_page_cache()
    return HomePageConfigRead.model_validate(cfg)
