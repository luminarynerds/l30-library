# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin endpoints for managing community resource links."""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...schemas.community_resource import (
    CommunityResourceLinkCreate,
    CommunityResourceLinkResponse,
    CommunityResourceLinkUpdate,
    DiscoveryResponse,
    DiscoverySuggestion,
)
from ...services import community_resource_service as svc
from .auth.helpers import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/community-resources", tags=["admin-community-resources"])


@router.get("", response_model=list[CommunityResourceLinkResponse])
async def list_resources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.get_all_resources(db)


@router.post("", response_model=CommunityResourceLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_resource(
    data: CommunityResourceLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await svc.create_resource(db, data)


@router.patch("/{link_id}", response_model=CommunityResourceLinkResponse)
async def update_resource(
    link_id: int,
    data: CommunityResourceLinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    link = await svc.update_resource(db, link_id, data)
    if not link:
        raise HTTPException(status_code=404, detail="Resource link not found")
    return link


@router.delete("/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_resource(
    link_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    deleted = await svc.delete_resource(db, link_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Resource link not found")


@router.post("/discover", response_model=DiscoveryResponse)
async def discover_resources(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from ...models.multi_branch import LibrarySystem
    result = await db.execute(select(LibrarySystem).limit(1))
    library = result.scalar_one_or_none()
    if not library or not library.zip_code:
        raise HTTPException(
            status_code=400,
            detail="Library zip code not configured. Set it in Site Settings first.",
        )

    try:
        suggestions = await svc.discover_resources(
            db, library.city or "", library.state or "", library.zip_code
        )
    except RuntimeError as e:
        logger.warning(f"Discovery service unavailable: {e}")
        suggestions = []

    return DiscoveryResponse(
        suggestions=suggestions,
        zip_code=library.zip_code,
        city=library.city or "",
        state=library.state or "",
    )


@router.post("/discover/save", response_model=list[CommunityResourceLinkResponse])
async def save_discovered_resources(
    suggestions: list[DiscoverySuggestion],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    page_context_map = {
        "food_nutrition": ["community", "life_situations"],
        "health_wellness": ["community", "life_situations"],
        "housing": ["community", "life_situations"],
        "jobs_employment": ["community", "life_situations"],
        "family_services": ["community", "life_situations"],
    }
    saved = []
    for s in suggestions:
        contexts = page_context_map.get(s.category, ["community"])
        links = await svc.save_discovery_suggestions(db, [s], contexts)
        saved.extend(links)
    return saved
