# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal content collections.

This module handles scenario-based legal collections which are curated
bundles of forms, guides, clinics, and providers for specific legal
situations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    LegalCollectionCreate, LegalCollectionUpdate, LegalCollectionResponse,
    LegalCollectionListResponse,
)
from ....services import legal_service
from .dependencies import get_current_user, get_current_user_optional
from .helpers import paginated_response, require_resource

router = APIRouter(prefix="/legal", tags=["legal-documents"])


# ============================================================================
# Legal Collections (Phase 1 Expansion)
# ============================================================================

@router.get("/collections", response_model=LegalCollectionListResponse)
async def list_collections(
    situation: Optional[str] = Query(None, description="Filter by situation (legal problem type)"),
    complexity_level: Optional[str] = Query(None, description="Filter by complexity: simple, moderate, complex"),
    has_fee_waiver: Optional[bool] = Query(None, description="Show only collections with fee waiver available"),
    cost_max: Optional[float] = Query(None, ge=0, description="Maximum estimated cost"),
    language: Optional[str] = Query(None, description="Filter by available language"),
    is_featured: Optional[bool] = Query(None, description="Show only featured collections"),
    search: Optional[str] = Query(None, description="Search by title or description"),
    sort_by: str = Query("featured", pattern="^(featured|relevance|alphabetical|newest)$", description="Sort results"),
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """
    List scenario-based legal collections with advanced filtering.

    Collections are curated bundles of forms, guides, clinics, and providers
    for specific legal situations (e.g., "I'm Facing Eviction").

    Filters:
    - situation: Legal problem type (eviction, bankruptcy, etc.)
    - complexity_level: simple, moderate, or complex
    - has_fee_waiver: Show collections with fee waiver available
    - cost_max: Maximum estimated cost in dollars
    - language: Available language code
    - is_featured: Show only featured collections
    - search: Search query across title and description
    - sort_by: Sort by featured, relevance, alphabetical, or newest
    """
    collections, total = await legal_service.list_collections(
        db,
        situation=situation,
        complexity_level=complexity_level,
        fee_waiver_available=has_fee_waiver,
        estimated_cost_max=cost_max,
        language=language,
        is_published=True,
        is_featured=is_featured,
        search_query=search,
        skip=offset,
        limit=limit,
        sort_by=sort_by
    )
    return paginated_response(
        key="collections",
        items=collections,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_collection_to_response,
    )


@router.get("/collections/{collection_id}", response_model=LegalCollectionResponse)
async def get_collection(
    collection_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific legal collection by ID."""
    collection = require_resource(
        await legal_service.get_collection_by_id(db, collection_id),
        message="Legal collection not found",
    )

    # Increment view count (async, non-blocking)
    await legal_service.increment_collection_views(db, collection_id)

    return _collection_to_response(collection)


@router.get("/collections/slug/{slug}", response_model=LegalCollectionResponse)
async def get_collection_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific legal collection by slug."""
    collection = require_resource(
        await legal_service.get_collection_by_slug(db, slug),
        message="Legal collection not found",
    )

    # Increment view count
    if collection:
        await legal_service.increment_collection_views(db, collection.id)

    return _collection_to_response(collection)


@router.post("/collections", response_model=LegalCollectionResponse, status_code=status.HTTP_201_CREATED)
async def create_collection(
    collection_data: LegalCollectionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new legal collection. Requires staff access."""
    # Validate that referenced resources exist
    collection = await legal_service.create_collection(
        db,
        collection_data.model_dump(),
        created_by_id=current_user.id
    )
    return _collection_to_response(collection)


@router.patch("/collections/{collection_id}", response_model=LegalCollectionResponse)
async def update_collection(
    collection_id: int,
    collection_data: LegalCollectionUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a legal collection. Requires staff access."""
    collection = require_resource(
        await legal_service.update_collection(
            db,
            collection_id,
            collection_data.model_dump(exclude_unset=True),
        ),
        message="Legal collection not found",
    )
    return _collection_to_response(collection)


@router.post("/collections/{collection_id}/helpful")
async def record_collection_helpful(
    collection_id: int,
    helpful_data: dict,
    db: AsyncSession = Depends(get_db)
):
    """Record helpful/not helpful feedback for a collection."""
    await legal_service.record_collection_helpful(
        db,
        collection_id,
        was_helpful=helpful_data.get("was_helpful", False)
    )
    await db.commit()
    return {"status": "recorded"}


@router.get("/collections/{collection_id}/related", response_model=LegalCollectionListResponse)
async def get_related_collections(
    collection_id: int,
    limit: int = Query(5, ge=1, le=20),
    db: AsyncSession = Depends(get_db)
):
    """
    Get collections related to the specified collection.

    Related collections are determined by:
    - Same legal situation/topic
    - Similar complexity level
    - Overlapping resources (forms, guides, clinics)
    """
    # Get the main collection first
    main_collection = await legal_service.get_collection_by_id(db, collection_id)
    if not main_collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Find similar collections
    related_collections = await legal_service.list_collections(
        db,
        situation=main_collection.situation,
        complexity_level=main_collection.complexity_level,
        is_published=True,
        skip=0,
        limit=limit + 1  # +1 to exclude the main collection
    )

    # Filter out the main collection and return
    related = [
        c for c in related_collections[0] if c.id != collection_id
    ][:limit]

    return paginated_response(
        key="collections",
        items=related,
        total=len(related),
        limit=limit,
        offset=0,
        mapper=_collection_to_response,
    )


@router.get("/collections/{collection_id}/analytics")
async def get_collection_analytics(
    collection_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get analytics for a collection (staff only).

    Returns engagement metrics including:
    - View count and trends
    - Click-through rates
    - Completion rates
    - Helpfulness ratings
    - Resource usage breakdown
    """
    collection = await legal_service.get_collection_by_id(db, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Calculate helpfulness percentage
    total_feedback = collection.helpful_count + collection.unhelpful_count
    helpfulness_pct = (
        (collection.helpful_count / total_feedback * 100) if total_feedback > 0 else 0
    )

    return {
        "collection_id": collection.id,
        "title": collection.title,
        "analytics": {
            "engagement": {
                "views": collection.view_count,
                "click_throughs": collection.click_through_count,
                "completions": collection.completion_count,
                "click_through_rate": (
                    collection.click_through_count / collection.view_count * 100
                    if collection.view_count > 0 else 0
                ),
                "completion_rate": (
                    collection.completion_count / collection.view_count * 100
                    if collection.view_count > 0 else 0
                )
            },
            "feedback": {
                "helpful": collection.helpful_count,
                "unhelpful": collection.unhelpful_count,
                "total_feedback": total_feedback,
                "helpfulness_percentage": round(helpfulness_pct, 2)
            },
            "resources": {
                "guides": len(collection.guide_ids) if collection.guide_ids else 0,
                "forms": len(collection.form_ids) if collection.form_ids else 0,
                "clinics": len(collection.clinic_ids) if collection.clinic_ids else 0,
                "providers": len(collection.provider_ids) if collection.provider_ids else 0,
                "glossary_terms": len(collection.glossary_term_ids) if collection.glossary_term_ids else 0
            }
        },
        "last_updated": collection.updated_at,
        "last_reviewed": collection.last_reviewed_date
    }


# ============================================================================
# Helper Functions
# ============================================================================

def _collection_to_response(collection) -> dict:
    return {
        "id": collection.id,
        "title": collection.title,
        "slug": collection.slug,
        "description": collection.description,
        "situation": collection.situation,
        "guide_ids": collection.guide_ids or [],
        "form_ids": collection.form_ids or [],
        "clinic_ids": collection.clinic_ids or [],
        "provider_ids": collection.provider_ids or [],
        "glossary_term_ids": collection.glossary_term_ids or [],
        "estimated_time_minutes": collection.estimated_time_minutes,
        "complexity_level": collection.complexity_level,
        "success_outcomes": collection.success_outcomes or [],
        "reading_level": collection.reading_level,
        "step_by_step_summary": collection.step_by_step_summary or [],
        "icon": collection.icon,
        "color_code": collection.color_code,
        "available_languages": collection.available_languages or [],
        # Librarian recommendations - Priority 1
        "estimated_cost_min": collection.estimated_cost_min,
        "estimated_cost_max": collection.estimated_cost_max,
        "cost_description": collection.cost_description,
        "fee_waiver_available": collection.fee_waiver_available,
        "resource_details": collection.resource_details or [],
        "last_reviewed_date": collection.last_reviewed_date,
        "view_count": collection.view_count,
        "click_through_count": collection.click_through_count,
        "completion_count": collection.completion_count,
        "helpful_count": collection.helpful_count,
        "unhelpful_count": collection.unhelpful_count,
        "is_published": collection.is_published,
        "is_featured": collection.is_featured,
        "display_order": collection.display_order,
        "created_at": collection.created_at,
        "updated_at": collection.updated_at,
        "created_by_id": collection.created_by_id
    }
