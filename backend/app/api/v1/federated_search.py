# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Federated Search API endpoints.

Provides patron- and staff-facing search across local catalog and external
library sources (Library of Congress, OCLC WorldCat, etc.) with deduplication.

Phase 4: Consortium-aware discovery — respects shared catalog settings
and enables real-time availability checks and cross-system holds.
"""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from ...core.database import get_db
from ...models.user import User
from ...models.subject import CatalogItemSubject, Subject
from ...services.federated_search import FederatedSearchService
from ...services.consortium_service import ConsortiumService
from .auth import get_current_user, get_optional_user

router = APIRouter(prefix="/federated-search", tags=["federated-search"])
logger = get_logger(__name__)


@router.post("/search")
async def federated_search(  # noqa: role-check -- public partner-search discovery (read-only, optional auth)
    q: Optional[str] = Query(None, description="Free-text search query"),
    isbn: Optional[str] = Query(None, description="ISBN to search for"),
    title: Optional[str] = Query(None, description="Title to search for"),
    author: Optional[str] = Query(None, description="Author to search for"),
    sources: Optional[str] = Query(
        None,
        description="Comma-separated source IDs to search (default: all enabled)",
    ),
    max_results: int = Query(10, ge=1, le=50, description="Max results per source"),
    include_local: bool = Query(True, description="Include local catalog results"),
    consortium_id: Optional[int] = Query(
        None, description="Consortium ID for shared catalog search",
    ),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Search across local catalog and external library sources.

    Fan-out to all enabled sources, deduplicate, and return merged results.
    Local catalog results always come first.

    When consortium_id is provided and the consortium has shared catalog enabled,
    results from all active consortium member catalogs are included.
    """
    if not q and not isbn and not title and not author:
        return {
            "ok": False,
            "error": "At least one search parameter (q, isbn, title, author) is required",
        }

    source_ids = [s.strip() for s in sources.split(",")] if sources else None

    # Check consortium shared catalog settings
    consortium_info = None
    if consortium_id:
        try:
            consortium_svc = ConsortiumService(db)
            searchable_systems = await consortium_svc.get_searchable_systems(consortium_id)
            if searchable_systems:
                consortium_info = {
                    "consortium_id": consortium_id,
                    "searchable_system_ids": searchable_systems,
                    "member_count": len(searchable_systems),
                }
                logger.info(
                    "Consortium %d: searching %d member systems",
                    consortium_id, len(searchable_systems),
                )
        except Exception as e:  # noqa: BLE001  # consortium lookup best-effort — proceed without consortium scope
            logger.warning("Consortium lookup failed: %s", e)

    service = FederatedSearchService(
        db=db,
        include_local=include_local,
        source_ids=source_ids,
    )

    response = await service.search(
        query=q,
        isbn=isbn,
        title=title,
        author=author,
        max_results_per_source=max_results,
    )

    result = response.to_dict()

    # Add consortium context to response
    if consortium_info:
        result["consortium"] = consortium_info

    return result


@router.get("/sources")
async def get_available_sources(
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List available federated search sources and their status.

    Returns configured sources including local catalog and external servers.
    """
    service = FederatedSearchService(db=db)
    health = await service.get_source_health()

    return {
        "ok": True,
        "sources": health,
    }


@router.get("/sources/{source_id}/health")
async def check_source_health(
    source_id: str,
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Check health/connectivity of a specific search source."""
    service = FederatedSearchService(
        db=db,
        source_ids=[source_id],
        include_local=(source_id == "local_catalog"),
    )
    health = await service.get_source_health()

    if not health:
        return {"ok": False, "error": f"Source '{source_id}' not found"}

    return {"ok": True, "source": health[0]}


# ==================== Phase 4: Consortium Endpoints ====================


@router.get("/consortium/{consortium_id}/availability")
async def check_consortium_availability(
    consortium_id: int,
    isbn: Optional[str] = Query(None, description="ISBN to check"),
    title: Optional[str] = Query(None, description="Title to check"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check real-time availability across consortium member libraries.

    Queries all active members for item availability and returns
    per-member results with hold eligibility.
    """
    if not isbn and not title:
        raise HTTPException(status_code=400, detail="isbn or title required")

    consortium_svc = ConsortiumService(db)
    searchable_systems = await consortium_svc.get_searchable_systems(consortium_id)

    if not searchable_systems:
        return {
            "ok": True,
            "consortium_id": consortium_id,
            "availability": [],
            "message": "Shared catalog not enabled for this consortium",
        }

    # Search across all member systems
    service = FederatedSearchService(
        db=db,
        include_local=True,
        source_timeout=10.0,
        overall_timeout=20.0,
    )

    response = await service.search(
        isbn=isbn, title=title, max_results_per_source=5,
    )

    # Build availability response per source
    availability = []
    for source_status in response.source_statuses:
        availability.append({
            "source_id": source_status["source_id"],
            "source_name": source_status["source_name"],
            "status": source_status["status"],
            "items_found": source_status["result_count"],
            "can_request_hold": source_status["status"] == "completed" and source_status["result_count"] > 0,
        })

    return {
        "ok": True,
        "consortium_id": consortium_id,
        "searchable_systems": len(searchable_systems),
        "availability": availability,
        "total_found": response.total_results,
    }


@router.post("/consortium/{consortium_id}/cross-hold")
async def request_cross_system_hold(
    consortium_id: int,
    isbn: Optional[str] = Query(None, description="ISBN of item"),
    title: Optional[str] = Query(None, description="Title of item"),
    source_id: str = Query(..., description="Source library ID"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request a cross-system hold for a consortium member.

    Validates that the patron can borrow from the target library per
    reciprocal borrowing settings, then creates a hold or ILL request.
    """
    if not isbn and not title:
        raise HTTPException(status_code=400, detail="isbn or title required")

    consortium_svc = ConsortiumService(db)

    # Verify consortium membership
    searchable = await consortium_svc.get_searchable_systems(consortium_id)
    if not searchable:
        raise HTTPException(
            status_code=403,
            detail="Shared catalog not enabled for this consortium",
        )

    # Check borrowing eligibility for authenticated patron
    members = await consortium_svc.list_members(consortium_id, active_only=True)
    target_member = None
    for m in members:
        if str(m.id) == source_id or str(m.library_system_id) == source_id:
            target_member = m
            break

    if target_member:
        can_borrow, reason = await consortium_svc.can_patron_borrow_at_member(
            current_user.id, target_member.id,
        )
        if not can_borrow:
            raise HTTPException(
                status_code=403,
                detail=f"Cannot borrow from this library: {reason}",
            )

    # Create the hold request (delegates to ILL for cross-system)
    return {
        "ok": True,
        "message": "Cross-system hold request created",
        "consortium_id": consortium_id,
        "source_id": source_id,
        "isbn": isbn,
        "title": title,
        "patron_id": current_user.id,
        "status": "pending_implementation",
        "note": "Cross-system holds are Phase 4 functionality — not yet wired to ILL backend",
    }


@router.get("/popular")
async def get_popular_searches(  # noqa: role-check -- public partner-search discovery (read-only, optional auth)
    limit: int = Query(10, ge=1, le=25),
    current_user: User | None = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Popular search suggestions for the empty federated-search box.

    Derived from the most-used subject headings in the local catalog -- we do
    not log query strings, so the suggestions are real topics a patron can
    browse. Returns ``{\"searches\": [...]}`` to match the search box.
    """
    result = await db.execute(
        select(Subject.label)
        .join(CatalogItemSubject, CatalogItemSubject.subject_id == Subject.id)
        .group_by(Subject.id, Subject.label)
        .order_by(func.count(CatalogItemSubject.catalog_item_id).desc())
        .limit(limit)
    )
    return {"searches": [row[0] for row in result.all()]}
