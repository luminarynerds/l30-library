# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Knowledge Base API - Staff-curated information for patrons"""

from datetime import datetime
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.sanitization import _sanitize_html
from ...models.knowledge_base import DecisionTree, KnowledgeEntry
from ...models.user import User
from ...services.organization_features_service import OrganizationFeaturesService
from .auth import get_current_user, get_optional_user
from .dependencies import require_admin, require_staff

router = APIRouter(prefix="/knowledge", tags=["knowledge-base"])

# KB categories that should be hidden when their corresponding feature flag is off
CATEGORY_FEATURE_FLAGS: dict[str, str] = {
    "indie": "indie_platform_enabled",
    "programs": "events_enabled",
    "makerspace": "makerspace_enabled",
    "community": "community_features_enabled",
    "youth_services": "community_features_enabled",
}

# Entry types served on public (unauthenticated) endpoints. Non-public types
# (e.g. captured patron_chat) must never be reachable by id or via mark-helpful.
PUBLIC_ENTRY_TYPES = ("faq", "guide", "policy", "how-to", "read-alike")


async def _get_hidden_categories(db: AsyncSession) -> list[str]:
    hidden = []
    for category, flag in CATEGORY_FEATURE_FLAGS.items():
        if not await OrganizationFeaturesService.is_feature_enabled(db, flag):
            hidden.append(category)
    return hidden


async def _resolve_catalog_match(
    db: AsyncSession, title: Optional[str], author: Optional[str]
) -> tuple[Optional[int], Optional[str]]:
    if not title or not author:
        return None, None
    from ...models.catalog import CatalogItem

    q = (
        select(CatalogItem.id, CatalogItem.cover_url)
        .where(
            func.lower(CatalogItem.title) == title.strip().lower(),
            func.lower(CatalogItem.author) == author.strip().lower(),
        )
        .limit(2)
    )
    rows = (await db.execute(q)).all()
    if len(rows) == 1:
        return rows[0][0], rows[0][1]
    return None, None


# ============================================================================
# Schemas
# ============================================================================


class KnowledgeEntryResponse(BaseModel):

    id: int
    category: str
    entry_type: Optional[str] = None
    title: str
    summary: Optional[str] = None
    content: str
    tags: Optional[str] = None
    is_featured: bool
    view_count: int
    helpful_count: int
    added_by_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ReadAlikeResponse(BaseModel):

    id: int
    if_you_liked: str
    if_you_liked_author: Optional[str] = None
    then_try: str
    then_try_author: Optional[str] = None
    reason: str
    added_by_name: Optional[str] = None
    created_at: datetime
    then_try_catalog_id: Optional[int] = None
    then_try_cover_url: Optional[str] = None

    class Config:
        from_attributes = True




class DecisionTreePublicResponse(BaseModel):
    id: int
    title: str
    description: str | None = None
    category: str
    tree_data: Any
    view_count: int
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class KnowledgeEntryCreate(BaseModel):

    category: str = Field(..., min_length=1, max_length=50)
    entry_type: Optional[str] = Field(default=None, max_length=30)
    title: str = Field(..., min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=500)
    content: str = Field(..., min_length=1)
    tags: Optional[str] = Field(default=None, max_length=500)
    is_featured: bool = False

    # For read-alikes
    if_you_liked: Optional[str] = Field(default=None, max_length=200)
    if_you_liked_author: Optional[str] = Field(default=None, max_length=200)
    then_try: Optional[str] = Field(default=None, max_length=200)
    then_try_author: Optional[str] = Field(default=None, max_length=200)
    reason: Optional[str] = None

    # content is authored as rich-text HTML and served unauthenticated to
    # patrons, so sanitize it the same way blog bodies are sanitized.
    @field_validator("content", mode="before")
    @classmethod
    def _sanitize_content(cls, value):
        return _sanitize_html(value)


class KnowledgeEntryUpdate(BaseModel):

    category: Optional[str] = Field(default=None, min_length=1, max_length=50)
    entry_type: Optional[str] = Field(default=None, max_length=30)
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    summary: Optional[str] = Field(default=None, max_length=500)
    content: Optional[str] = Field(default=None, min_length=1)
    tags: Optional[str] = Field(default=None, max_length=500)
    is_featured: Optional[bool] = None

    # For read-alikes
    if_you_liked: Optional[str] = Field(default=None, max_length=200)
    if_you_liked_author: Optional[str] = Field(default=None, max_length=200)
    then_try: Optional[str] = Field(default=None, max_length=200)
    then_try_author: Optional[str] = Field(default=None, max_length=200)
    reason: Optional[str] = None

    @field_validator("content", mode="before")
    @classmethod
    def _sanitize_content(cls, value):
        return _sanitize_html(value)


# ============================================================================
# Public Endpoints
# ============================================================================


@router.get("", response_model=List[KnowledgeEntryResponse])
async def search_knowledge_base(
    category: Optional[str] = Query(
        default=None,
        description="Filter by topic category (Account & Membership, Borrowing & Returns, etc.)",
    ),
    entry_type: Optional[str] = Query(
        default=None,
        description="Filter by entry type (faq, guide, policy, how-to, read-alike)",
    ),
    search: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Search in title and content",
    ),
    q: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Alias for search",
    ),
    featured_only: bool = Query(
        default=False, description="Only return featured entries"
    ),
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[KnowledgeEntryResponse]:
    """Search the knowledge base."""
    search_term = q or search
    query = select(KnowledgeEntry)

    # Exclude categories whose feature flag is disabled
    hidden = await _get_hidden_categories(db)
    if hidden:
        query = query.where(KnowledgeEntry.category.notin_(hidden))

    # Only show patron-facing entry types on public endpoint
    query = query.where(KnowledgeEntry.entry_type.in_(PUBLIC_ENTRY_TYPES))

    if category:
        query = query.where(KnowledgeEntry.category == category)

    if entry_type:
        query = query.where(KnowledgeEntry.entry_type == entry_type)

    if search_term:
        search_pattern = f"%{search_term}%"
        query = query.where(
            or_(
                KnowledgeEntry.title.ilike(search_pattern),
                KnowledgeEntry.content.ilike(search_pattern),
                KnowledgeEntry.tags.ilike(search_pattern),
            )
        )

    if featured_only:
        query = query.where(KnowledgeEntry.is_featured == True)

    query = query.order_by(
        KnowledgeEntry.is_featured.desc(),
        KnowledgeEntry.helpful_count.desc(),
        KnowledgeEntry.created_at.desc(),
    ).offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/read-alikes", response_model=List[ReadAlikeResponse])
async def get_read_alikes(
    search: Optional[str] = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Search by title, author, or genre/theme",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[ReadAlikeResponse]:
    """
    Get read-alike book recommendations from Patty's expertise.

    - **search**: Search by title, author, or genre/theme
    - **limit**: Maximum number of recommendations
    """
    query = select(KnowledgeEntry).where(KnowledgeEntry.entry_type == "read-alike")

    # Exclude categories whose feature flag is disabled
    hidden = await _get_hidden_categories(db)
    if hidden:
        query = query.where(KnowledgeEntry.category.notin_(hidden))

    # Search in book titles, authors, and recommendation reasons
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                KnowledgeEntry.if_you_liked.ilike(search_pattern),
                KnowledgeEntry.if_you_liked_author.ilike(search_pattern),
                KnowledgeEntry.then_try.ilike(search_pattern),
                KnowledgeEntry.then_try_author.ilike(search_pattern),
                KnowledgeEntry.reason.ilike(search_pattern),
            )
        )

    query = query.order_by(
        KnowledgeEntry.is_featured.desc(), KnowledgeEntry.helpful_count.desc()
    ).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()
    responses: List[ReadAlikeResponse] = []
    for e in entries:
        cid, cover = await _resolve_catalog_match(db, e.then_try, e.then_try_author)
        responses.append(
            ReadAlikeResponse(
                id=e.id,
                if_you_liked=e.if_you_liked,
                if_you_liked_author=e.if_you_liked_author,
                then_try=e.then_try,
                then_try_author=e.then_try_author,
                reason=e.reason,
                added_by_name=e.added_by_name,
                created_at=e.created_at,
                then_try_catalog_id=cid,
                then_try_cover_url=cover,
            )
        )
    return responses


@router.get("/categories/counts")
async def get_category_counts(
    db: AsyncSession = Depends(get_db),
) -> dict[str, dict[str, int]]:
    """Return article counts per category and per entry_type.

    Used by the frontend to hide categories/types with zero articles from
    filter dropdowns. Honors feature-flag-hidden categories (returns 0 for them).
    """
    hidden = await _get_hidden_categories(db)

    cat_q = select(KnowledgeEntry.category, func.count(KnowledgeEntry.id)).group_by(
        KnowledgeEntry.category
    )
    type_q = (
        select(KnowledgeEntry.entry_type, func.count(KnowledgeEntry.id))
        .where(KnowledgeEntry.entry_type.is_not(None))
        .group_by(KnowledgeEntry.entry_type)
    )
    if hidden:
        cat_q = cat_q.where(KnowledgeEntry.category.notin_(hidden))
        type_q = type_q.where(KnowledgeEntry.category.notin_(hidden))

    cat_rows = (await db.execute(cat_q)).all()
    type_rows = (await db.execute(type_q)).all()
    return {
        "categories": {row[0]: row[1] for row in cat_rows},
        "types": {row[0]: row[1] for row in type_rows},
    }


@router.get("/faqs", response_model=List[KnowledgeEntryResponse])
async def get_faqs(
    category: Optional[str] = Query(default=None, description="Filter by topic category"),
    search: Optional[str] = Query(default=None, min_length=1, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> List[KnowledgeEntryResponse]:
    """Get frequently asked questions."""
    query = select(KnowledgeEntry).where(KnowledgeEntry.entry_type == "faq")

    # Exclude categories whose feature flag is disabled
    hidden = await _get_hidden_categories(db)
    if hidden:
        query = query.where(KnowledgeEntry.category.notin_(hidden))

    # Only show patron-facing entry types on public endpoint
    query = query.where(KnowledgeEntry.entry_type.in_(PUBLIC_ENTRY_TYPES))

    if category:
        query = query.where(KnowledgeEntry.category == category)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            or_(
                KnowledgeEntry.title.ilike(search_pattern),
                KnowledgeEntry.content.ilike(search_pattern),
            )
        )

    query = query.order_by(
        KnowledgeEntry.is_featured.desc(), KnowledgeEntry.view_count.desc()
    )

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/decision-trees", response_model=List[DecisionTreePublicResponse])
async def get_public_decision_trees(
    category: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> List[DecisionTreePublicResponse]:
    query = select(DecisionTree).where(DecisionTree.is_published == True)

    if category:
        query = query.where(DecisionTree.category == category)

    query = query.order_by(DecisionTree.view_count.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/decision-trees/{tree_id}", response_model=DecisionTreePublicResponse)
async def get_public_decision_tree(
    tree_id: int, db: AsyncSession = Depends(get_db)
) -> DecisionTreePublicResponse:
    result = await db.execute(
        select(DecisionTree).where(
            DecisionTree.id == tree_id,
            DecisionTree.is_published == True,
        )
    )
    tree = result.scalar_one_or_none()

    if not tree:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision tree not found",
        )

    tree.view_count += 1
    await db.commit()

    return tree


@router.get("/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_knowledge_entry(
    entry_id: int, db: AsyncSession = Depends(get_db)
) -> KnowledgeEntryResponse:
    """Get a single knowledge base entry by ID"""
    result = await db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.id == entry_id,
            KnowledgeEntry.entry_type.in_(PUBLIC_ENTRY_TYPES),
            KnowledgeEntry.review_status == "approved",
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found"
        )

    # Increment view count
    entry.view_count += 1
    await db.commit()

    return entry


@router.post("/{entry_id}/helpful", status_code=status.HTTP_204_NO_CONTENT)
async def mark_entry_helpful(entry_id: int, db: AsyncSession = Depends(get_db)) -> None:  # noqa: role-check -- public mark-helpful counter
    """Mark a knowledge entry as helpful"""
    result = await db.execute(
        select(KnowledgeEntry).where(
            KnowledgeEntry.id == entry_id,
            KnowledgeEntry.entry_type.in_(PUBLIC_ENTRY_TYPES),
            KnowledgeEntry.review_status == "approved",
        )
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found"
        )

    entry.helpful_count += 1
    await db.commit()


# ============================================================================
# Admin/Staff Endpoints
# ============================================================================


@router.post(
    "/admin/entries",
    response_model=KnowledgeEntryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_entry(
    entry_data: KnowledgeEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeEntryResponse:
    """
    Create a new knowledge base entry (staff/admin only).

    Staff can share their expertise with patrons through the knowledge base.
    """
    await require_staff(current_user)

    # Create entry
    entry = KnowledgeEntry(
        **entry_data.model_dump(),
        added_by_id=current_user.id,
        added_by_name=f"{current_user.first_name} {current_user.last_name}",
    )

    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return entry


@router.get("/admin/entries/stats/summary")
async def get_knowledge_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    """Get knowledge base statistics (staff/admin only)"""
    await require_staff(current_user)

    # Count by category
    result = await db.execute(
        select(KnowledgeEntry.category, func.count(KnowledgeEntry.id)).group_by(
            KnowledgeEntry.category
        )
    )
    category_counts = dict(result.all())

    # Total stats
    result = await db.execute(select(KnowledgeEntry))
    entries = result.scalars().all()

    total_views = sum(e.view_count for e in entries)
    total_helpful = sum(e.helpful_count for e in entries)
    featured_count = sum(1 for e in entries if e.is_featured)

    # Most viewed entries
    most_viewed = sorted(entries, key=lambda x: x.view_count, reverse=True)[:5]
    most_viewed_list = [
        {
            "id": e.id,
            "title": e.title,
            "category": e.category,
            "view_count": e.view_count,
        }
        for e in most_viewed
    ]

    return {
        "total_entries": len(entries),
        "by_category": category_counts,
        "featured_entries": featured_count,
        "total_views": total_views,
        "total_helpful_marks": total_helpful,
        "most_viewed": most_viewed_list,
    }


@router.get("/admin/entries/{entry_id}", response_model=KnowledgeEntryResponse)
async def get_admin_knowledge_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeEntryResponse:
    """Get a knowledge base entry (staff/admin only)"""
    await require_staff(current_user)

    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found"
        )

    return entry


@router.put("/admin/entries/{entry_id}", response_model=KnowledgeEntryResponse)
async def update_knowledge_entry(
    entry_id: int,
    update_data: KnowledgeEntryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeEntryResponse:
    """Update a knowledge base entry (staff/admin only)"""
    await require_staff(current_user)

    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found"
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(entry, field, value)

    await db.commit()
    await db.refresh(entry)

    return entry


@router.delete("/admin/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_knowledge_entry(
    entry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a knowledge base entry (admin only)"""
    await require_admin(current_user)

    result = await db.execute(
        select(KnowledgeEntry).where(KnowledgeEntry.id == entry_id)
    )
    entry = result.scalar_one_or_none()

    if not entry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Knowledge entry not found"
        )

    await db.delete(entry)
    await db.commit()


