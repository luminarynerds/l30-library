# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public community resource links endpoint."""

from collections import defaultdict

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...schemas.community_resource import (
    PublicCategoryResponse,
    PublicCommunityResourcesResponse,
    PublicLinkResponse,
)
from ...services import community_resource_service as svc

router = APIRouter(prefix="/community-resources", tags=["community-resources"])


@router.get("", response_model=PublicCommunityResourcesResponse)
async def get_community_resources(
    page_context: str = Query(..., description="Page context filter"),
    db: AsyncSession = Depends(get_db),
):
    links = await svc.get_public_resources(db, page_context)

    grouped = defaultdict(list)
    category_meta = {}
    for link in links:
        grouped[link.category].append(
            PublicLinkResponse(name=link.name, url=link.url, description=link.description)
        )
        if link.category not in category_meta:
            category_meta[link.category] = {
                "title": link.category_label,
                "icon_hint": link.icon_hint,
            }

    categories = [
        PublicCategoryResponse(
            category=cat,
            title=category_meta[cat]["title"],
            icon_hint=category_meta[cat]["icon_hint"],
            links=grouped[cat],
        )
        for cat in grouped
    ]

    return PublicCommunityResourcesResponse(categories=categories)
