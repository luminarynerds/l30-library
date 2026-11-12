# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Public Catalog Recommendations Endpoint

Returns curated + algorithmic recommendations for a catalog item.
Pins appear first, suppressed items are filtered, then semantic similar items fill remaining slots.

Visibility: every returned item is gated by the same predicate as
``GET /catalog/items/{id}`` -- anonymous callers only see PUBLIC + CATALOGED
items; patrons cannot see CONFIDENTIAL; staff (any tier) see all states.
Without this gate the surface leaked title/author/cover for items the caller
could not fetch directly.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.catalog import CatalogItem, CatalogingStatus, SensitivityLevel
from ...models.curated_recommendations import CuratedRecommendation
from ...models.user import User, UserRole
from .auth import get_optional_user
from .dependencies import is_staff_or_admin

router = APIRouter(prefix="/catalog", tags=["catalog-recommendations"])


def _is_visible_to(item: CatalogItem, user: User | None) -> bool:
    if item.cataloging_status != CatalogingStatus.CATALOGED and not (
        user is not None and is_staff_or_admin(user)
    ):
        return False
    if user is None:
        return item.sensitivity_level == SensitivityLevel.PUBLIC
    if user.role == UserRole.PATRON:
        return item.sensitivity_level != SensitivityLevel.CONFIDENTIAL
    return True


class RecommendationItem(BaseModel):
    id: int
    title: str
    author: Optional[str] = None
    is_pinned: bool = False
    cover_image: Optional[str] = None
    available: bool = False


class RecommendationsResponse(BaseModel):
    items: list[RecommendationItem]
    total_pinned: int
    algorithm_used: str


@router.get("/{item_id}/recommendations", response_model=RecommendationsResponse)
async def get_recommendations(
    item_id: int,
    limit: int = Query(6, ge=1, le=20),
    db: AsyncSession = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Get curated and algorithmic recommendations for a catalog item.

    Every item -- pinned or algorithmic -- is passed through the same
    visibility predicate as the item-detail endpoint before it can appear
    in the response.
    """

    # 1. Pinned recommendations (visible curated items ordered by display_order)
    pins_stmt = (
        select(CuratedRecommendation)
        .where(
            CuratedRecommendation.source_item_id == item_id,
            CuratedRecommendation.is_hidden == False,
        )
        .order_by(CuratedRecommendation.display_order)
    )
    pins_result = await db.execute(pins_stmt)
    pins = pins_result.scalars().all()

    # 2. Suppressed item IDs (to exclude from algorithmic results)
    hides_stmt = (
        select(CuratedRecommendation.target_item_id)
        .where(
            CuratedRecommendation.source_item_id == item_id,
            CuratedRecommendation.is_hidden == True,
        )
    )
    hides_result = await db.execute(hides_stmt)
    suppressed_ids = set(hides_result.scalars().all())

    # Enrich pinned items with catalog data and visibility-gate them.
    pinned_items: list[RecommendationItem] = []
    pinned_ids: set[int] = set()
    for pin in pins:
        item_stmt = select(CatalogItem).where(CatalogItem.id == pin.target_item_id)
        item_result = await db.execute(item_stmt)
        catalog_item = item_result.scalar_one_or_none()
        if catalog_item and _is_visible_to(catalog_item, current_user):
            pinned_items.append(RecommendationItem(
                id=catalog_item.id,
                title=catalog_item.title,
                author=catalog_item.author,
                is_pinned=True,
                cover_image=catalog_item.cover_url,
                available=str(catalog_item.status) == "available" if catalog_item.status else False,
            ))
            pinned_ids.add(catalog_item.id)

    # 3. Fill remaining slots with semantic similar items.
    #
    # We over-fetch from the semantic ranker, batch-load the candidates,
    # then drop anything the caller is not allowed to see. Without the
    # batch-load + per-item visibility check, the response leaked title +
    # author + cover_url for CONFIDENTIAL or non-cataloged items.
    skip_ids = suppressed_ids | pinned_ids | {item_id}
    remaining_slots = limit - len(pinned_items)
    algorithm_used = "fallback"
    algorithmic_items: list[RecommendationItem] = []

    if remaining_slots > 0:
        try:
            from ...services.semantic_search_service import SemanticSearchService
            svc = SemanticSearchService(db)
            # Over-fetch to absorb visibility-filtered drops.
            result = await svc.find_similar_items(
                item_id,
                limit=remaining_slots + len(skip_ids) + 20,
            )
            algorithm_used = "semantic"

            candidate_ids: list[int] = []
            for sim in result.get("similar_items", []):
                sim_id = int(sim.get("source_id", 0)) if sim.get("source") == "local" else 0
                if sim_id and sim_id not in skip_ids and sim_id not in candidate_ids:
                    candidate_ids.append(sim_id)

            if candidate_ids:
                items_stmt = select(CatalogItem).where(CatalogItem.id.in_(candidate_ids))
                items_result = await db.execute(items_stmt)
                items_by_id = {it.id: it for it in items_result.scalars().all()}
                # Preserve semantic-ranker order.
                for sim_id in candidate_ids:
                    it = items_by_id.get(sim_id)
                    if it is None or not _is_visible_to(it, current_user):
                        continue
                    algorithmic_items.append(RecommendationItem(
                        id=it.id,
                        title=it.title,
                        author=it.author,
                        is_pinned=False,
                        cover_image=it.cover_url,
                        available=str(it.status) == "available" if it.status else False,
                    ))
                    if len(algorithmic_items) >= remaining_slots:
                        break
        except Exception:  # noqa: BLE001  # recommendation algorithm fallback — use fallback list
            algorithm_used = "fallback"

    # 4. Merge: pins first, then algorithmic.
    all_items = pinned_items + algorithmic_items
    return RecommendationsResponse(
        items=all_items[:limit],
        total_pinned=len(pinned_items),
        algorithm_used=algorithm_used,
    )
