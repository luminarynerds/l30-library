# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Comic & Graphic Novel Cataloging API Endpoints

Provides comprehensive endpoints for managing comic and graphic novel metadata:
- Comic series management
- Issue tracking with variant covers
- Story arc grouping and crossover event management
- Creator role tracking
- Content advisory and warning management
- Complex reading order for crossover events
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.comic_cataloging import (
    ComicContentAdvisory,
    ComicContentWarning,
    ComicFormat,
    ComicIssue,
    ComicIssueCreator,
    ComicPublisherImprint,
    ComicSeries,
    ReadingOrderEvent,
    ReadingOrderEventIssue,
    StoryArc,
    VariantCover,
    VariantCoverType,
    story_arc_issues,
)
from ...models.user import User
from ...schemas.comic_cataloging import (
    ComicContentAdvisoryCreate,
    ComicContentAdvisoryResponse,
    ComicIssueCreate,
    ComicIssueCreatorCreate,
    ComicIssueCreatorResponse,
    ComicIssueDetailResponse,
    ComicIssueResponse,
    ComicIssueUpdate,
    ComicSeriesCreate,
    ComicSeriesDetailResponse,
    ComicSeriesResponse,
    ComicSeriesUpdate,
    QuickAddComicIssueRequest,
    ReadingOrderEventCreate,
    ReadingOrderEventResponse,
    StoryArcCreate,
    StoryArcResponse,
    StoryArcUpdate,
    VariantCoverCreate,
    VariantCoverResponse,
)
from .dependencies import require_staff

router = APIRouter(prefix="/comic-cataloging", tags=["comic-cataloging"])


# ============================================================================
# Comic Series Endpoints
# ============================================================================


@router.get(
    "/series",
    response_model=list[ComicSeriesResponse],
)
async def list_comic_series(
    publisher: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List comic series with optional filtering by publisher"""
    query = select(ComicSeries)

    if publisher:
        safe_publisher = publisher.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(ComicSeries.publisher.ilike(f"%{safe_publisher}%"))

    query = query.order_by(ComicSeries.sort_title or ComicSeries.title).offset(skip).limit(limit)

    result = await db.execute(query)
    series = result.scalars().all()
    return series


@router.get(
    "/series/{series_id}",
    response_model=ComicSeriesDetailResponse,
)
async def get_comic_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific comic series with issue and story arc counts"""
    result = await db.execute(
        select(ComicSeries)
        .where(ComicSeries.id == series_id)
        .options(
            selectinload(ComicSeries.issues),
            selectinload(ComicSeries.story_arcs),
        )
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic series not found",
        )

    response = ComicSeriesDetailResponse.model_validate(series)
    response.issue_count = len(series.issues) if series.issues else 0
    response.story_arc_count = len(series.story_arcs) if series.story_arcs else 0
    return response


@router.post(
    "/series",
    response_model=ComicSeriesResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comic_series(
    series_in: ComicSeriesCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new comic series"""
    # Check for duplicates
    existing = await db.execute(
        select(ComicSeries).where(ComicSeries.title == series_in.title)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Comic series with this title already exists",
        )

    series = ComicSeries(**series_in.model_dump(exclude_unset=True))
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


@router.put(
    "/series/{series_id}",
    response_model=ComicSeriesResponse,
)
async def update_comic_series(
    series_id: int,
    series_in: ComicSeriesUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a comic series"""
    result = await db.execute(
        select(ComicSeries).where(ComicSeries.id == series_id)
    )
    series = result.scalar_one_or_none()
    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic series not found",
        )

    for key, value in series_in.model_dump(exclude_unset=True).items():
        setattr(series, key, value)

    await db.commit()
    await db.refresh(series)
    return series


# ============================================================================
# Comic Issue Endpoints
# ============================================================================


@router.get(
    "/issues",
    response_model=list[ComicIssueResponse],
)
async def list_comic_issues(
    series_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List comic issues with optional filtering by series"""
    query = select(ComicIssue)

    if series_id:
        query = query.where(ComicIssue.series_id == series_id)

    query = query.order_by(
        ComicIssue.series_id,
        ComicIssue.issue_number,
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    issues = result.scalars().all()
    return issues


@router.get(
    "/issues/{issue_id}",
    response_model=ComicIssueDetailResponse,
)
async def get_comic_issue(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific comic issue with all related data"""
    result = await db.execute(
        select(ComicIssue)
        .where(ComicIssue.id == issue_id)
        .options(
            selectinload(ComicIssue.variant_covers),
            selectinload(ComicIssue.creators),
        )
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic issue not found",
        )

    # Fetch content advisories separately
    advisories_result = await db.execute(
        select(ComicContentAdvisory).where(
            ComicContentAdvisory.issue_id == issue_id
        )
    )
    advisories = advisories_result.scalars().all()

    response = ComicIssueDetailResponse.model_validate(issue)
    response.content_advisories = [
        ComicContentAdvisoryResponse.model_validate(a) for a in advisories
    ]
    return response


@router.post(
    "/issues",
    response_model=ComicIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comic_issue(
    issue_in: ComicIssueCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new comic issue"""
    # Verify series exists
    series_result = await db.execute(
        select(ComicSeries).where(ComicSeries.id == issue_in.series_id)
    )
    if not series_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic series not found",
        )

    # Check for duplicate issue number in same series
    existing = await db.execute(
        select(ComicIssue).where(
            (ComicIssue.series_id == issue_in.series_id) &
            (ComicIssue.issue_number == issue_in.issue_number)
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This issue number already exists for this series",
        )

    issue = ComicIssue(**issue_in.model_dump(exclude_unset=True))
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


@router.post(
    "/issues/quick-add",
    response_model=ComicIssueResponse,
    status_code=status.HTTP_201_CREATED,
)
async def quick_add_comic_issue(
    issue_in: QuickAddComicIssueRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Quick add a comic issue with minimal required fields"""
    # Verify series exists
    series_result = await db.execute(
        select(ComicSeries).where(ComicSeries.id == issue_in.series_id)
    )
    if not series_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic series not found",
        )

    # Create issue with provided fields
    issue_data = {
        "series_id": issue_in.series_id,
        "catalog_item_id": issue_in.catalog_item_id,
        "issue_number": issue_in.issue_number,
    }

    if issue_in.issue_title:
        issue_data["issue_title"] = issue_in.issue_title
    if issue_in.publication_date:
        issue_data["publication_date"] = issue_in.publication_date
    if issue_in.isbn:
        issue_data["isbn"] = issue_in.isbn
    if issue_in.page_count:
        issue_data["page_count"] = issue_in.page_count

    issue = ComicIssue(**issue_data)
    db.add(issue)
    await db.commit()
    await db.refresh(issue)
    return issue


@router.put(
    "/issues/{issue_id}",
    response_model=ComicIssueResponse,
)
async def update_comic_issue(
    issue_id: int,
    issue_in: ComicIssueUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a comic issue"""
    result = await db.execute(
        select(ComicIssue).where(ComicIssue.id == issue_id)
    )
    issue = result.scalar_one_or_none()
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic issue not found",
        )

    for key, value in issue_in.model_dump(exclude_unset=True).items():
        setattr(issue, key, value)

    await db.commit()
    await db.refresh(issue)
    return issue


# ============================================================================
# Variant Cover Endpoints
# ============================================================================


@router.get(
    "/issues/{issue_id}/variants",
    response_model=list[VariantCoverResponse],
)
async def list_variant_covers(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all variant covers for an issue"""
    result = await db.execute(
        select(VariantCover).where(VariantCover.issue_id == issue_id)
    )
    covers = result.scalars().all()
    return covers


@router.post(
    "/issues/{issue_id}/variants",
    response_model=VariantCoverResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_variant_cover(
    issue_id: int,
    cover_in: VariantCoverCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a variant cover for an issue"""
    # Verify issue exists
    issue_result = await db.execute(
        select(ComicIssue).where(ComicIssue.id == issue_id)
    )
    if not issue_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic issue not found",
        )

    cover_data = cover_in.model_dump(exclude_unset=True)
    cover_data["issue_id"] = issue_id

    cover = VariantCover(**cover_data)
    db.add(cover)
    await db.commit()
    await db.refresh(cover)
    return cover


# ============================================================================
# Creator Endpoints
# ============================================================================


@router.get(
    "/issues/{issue_id}/creators",
    response_model=list[ComicIssueCreatorResponse],
)
async def list_issue_creators(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List all creators for an issue"""
    result = await db.execute(
        select(ComicIssueCreator)
        .where(ComicIssueCreator.issue_id == issue_id)
        .order_by(ComicIssueCreator.display_order)
    )
    creators = result.scalars().all()
    return creators


@router.post(
    "/issues/{issue_id}/creators",
    response_model=ComicIssueCreatorResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_issue_creator(
    issue_id: int,
    creator_in: ComicIssueCreatorCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add a creator to an issue"""
    # Verify issue exists
    issue_result = await db.execute(
        select(ComicIssue).where(ComicIssue.id == issue_id)
    )
    if not issue_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic issue not found",
        )

    creator_data = creator_in.model_dump(exclude_unset=True)
    creator_data["issue_id"] = issue_id

    creator = ComicIssueCreator(**creator_data)
    db.add(creator)
    await db.commit()
    await db.refresh(creator)
    return creator


# ============================================================================
# Story Arc Endpoints
# ============================================================================


@router.get(
    "/series/{series_id}/story-arcs",
    response_model=list[StoryArcResponse],
)
async def list_story_arcs(
    series_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List story arcs for a series"""
    query = (
        select(StoryArc)
        .where(StoryArc.series_id == series_id)
        .order_by(StoryArc.sequence_number)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    arcs = result.scalars().all()
    return arcs


@router.post(
    "/story-arcs",
    response_model=StoryArcResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_story_arc(
    arc_in: StoryArcCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new story arc"""
    # Verify series exists
    series_result = await db.execute(
        select(ComicSeries).where(ComicSeries.id == arc_in.series_id)
    )
    if not series_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic series not found",
        )

    arc = StoryArc(**arc_in.model_dump(exclude_unset=True))
    db.add(arc)
    await db.commit()
    await db.refresh(arc)
    return arc


@router.put(
    "/story-arcs/{arc_id}",
    response_model=StoryArcResponse,
)
async def update_story_arc(
    arc_id: int,
    arc_in: StoryArcUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a story arc"""
    result = await db.execute(
        select(StoryArc).where(StoryArc.id == arc_id)
    )
    arc = result.scalar_one_or_none()
    if not arc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story arc not found",
        )

    for key, value in arc_in.model_dump(exclude_unset=True).items():
        setattr(arc, key, value)

    await db.commit()
    await db.refresh(arc)
    return arc


# ============================================================================
# Content Advisory Endpoints
# ============================================================================


@router.get(
    "/issues/{issue_id}/advisories",
    response_model=list[ComicContentAdvisoryResponse],
)
async def list_content_advisories(
    issue_id: int,
    db: AsyncSession = Depends(get_db),
):
    """List content advisories for an issue"""
    result = await db.execute(
        select(ComicContentAdvisory).where(
            ComicContentAdvisory.issue_id == issue_id
        )
    )
    advisories = result.scalars().all()
    return advisories


@router.post(
    "/issues/{issue_id}/advisories",
    response_model=ComicContentAdvisoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_content_advisory(
    issue_id: int,
    advisory_in: ComicContentAdvisoryCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a content advisory for an issue"""
    # Verify issue exists
    issue_result = await db.execute(
        select(ComicIssue).where(ComicIssue.id == issue_id)
    )
    if not issue_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comic issue not found",
        )

    advisory_data = advisory_in.model_dump(exclude_unset=True)
    advisory_data["issue_id"] = issue_id
    advisory_data["added_by_id"] = staff_user.id

    advisory = ComicContentAdvisory(**advisory_data)
    db.add(advisory)
    await db.commit()
    await db.refresh(advisory)
    return advisory


# ============================================================================
# Reading Order Event Endpoints
# ============================================================================


@router.get(
    "/reading-order-events",
    response_model=list[ReadingOrderEventResponse],
)
async def list_reading_order_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List all reading order events"""
    query = (
        select(ReadingOrderEvent)
        .order_by(ReadingOrderEvent.event_name)
        .offset(skip)
        .limit(limit)
    )

    result = await db.execute(query)
    events = result.scalars().all()
    return events


@router.post(
    "/reading-order-events",
    response_model=ReadingOrderEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reading_order_event(
    event_in: ReadingOrderEventCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new reading order event"""
    event = ReadingOrderEvent(**event_in.model_dump(exclude_unset=True))
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event
