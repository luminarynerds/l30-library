# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Publisher and Manga Data API routes.
Handles publisher management, imprint hierarchy, manga serialization, and collection development.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.publisher_data import (
    ContentRatingSystem,
    MangaMagazine,
    MangaMetadata,
    MangaSerialization,
    Publisher,
    PublisherRegion,
    PublisherSeries,
    PublisherType,
)
from ...models.bibframe import BibframeInstance, BibframeWork
from ...models.release_tracker import TrackerBook
from ...models.user import User, UserRole
from ...schemas.publisher_data import (
    CollectionDevelopmentQuery,
    CollectionDevelopmentResponse,
    MangaMagazineCreate,
    MangaMagazineResponse,
    MangaMetadataCreate,
    MangaMetadataResponse,
    MangaSerializationCreate,
    MangaSerializationResponse,
    PublisherCreate,
    PublisherResponse,
    PublisherSeriesCreate,
    PublisherSeriesResponse,
    PublisherUpdate,
    PublisherWithImprintsResponse,
)
from .auth import get_current_user
from .dependencies import require_admin, require_staff

router = APIRouter(prefix="/publishers", tags=["publishers"])


# ============================================================================
# Publisher Management
# ============================================================================


@router.get("", response_model=List[PublisherResponse])
async def list_publishers(
    active_only: bool = Query(True),
    publisher_type: Optional[PublisherType] = None,
    region: Optional[PublisherRegion] = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List all publishers and imprints.
    Easy filtering by type (publisher/imprint/independent) and region.
    """
    query = select(Publisher)

    if active_only:
        query = query.where(Publisher.is_active == True)

    if publisher_type:
        query = query.where(Publisher.publisher_type == publisher_type)

    if region:
        query = query.where(Publisher.primary_region == region)

    query = query.order_by(Publisher.name)

    result = await db.execute(query)
    publishers = result.scalars().all()
    return publishers


@router.get("/{publisher_id}", response_model=PublisherWithImprintsResponse)
async def get_publisher(publisher_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get publisher with hierarchy and imprints.
    Shows all sub-imprints if this is a parent publisher.
    """
    result = await db.execute(
        select(Publisher)
        .where(Publisher.id == publisher_id)
        .options(selectinload(Publisher.imprints))
    )
    publisher = result.scalar_one_or_none()

    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")

    return publisher


@router.post("", response_model=PublisherResponse)
async def create_publisher(
    publisher: PublisherCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new publisher or imprint.
    Requires staff access.
    """
    await require_staff(current_user)

    # Check if parent exists
    if publisher.parent_publisher_id:
        parent_result = await db.execute(
            select(Publisher).where(Publisher.id == publisher.parent_publisher_id)
        )
        if not parent_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Parent publisher not found")

    db_publisher = Publisher(
        name=publisher.name,
        name_sort=publisher.name_sort or publisher.name.lower(),
        display_name=publisher.display_name or publisher.name,
        publisher_type=publisher.publisher_type,
        parent_publisher_id=publisher.parent_publisher_id,
        description=publisher.description,
        history=publisher.history,
        headquarters_location=publisher.headquarters_location,
        primary_region=publisher.primary_region,
        regions_served=publisher.regions_served,
        website_url=publisher.website_url,
        email=publisher.email,
        phone=publisher.phone,
        default_rating_system=publisher.default_rating_system,
        content_ratings_info=publisher.content_ratings_info,
        viaf_id=publisher.viaf_id,
        wikidata_id=publisher.wikidata_id,
        isni=publisher.isni,
        is_active=True,
    )

    db.add(db_publisher)
    await db.commit()
    await db.refresh(db_publisher)
    return db_publisher


@router.patch("/{publisher_id}", response_model=PublisherResponse)
async def update_publisher(
    publisher_id: int,
    publisher: PublisherUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update publisher details.
    Requires staff access.
    """
    await require_staff(current_user)

    db_publisher = await get_or_404(db, Publisher, publisher_id, "Publisher not found")

    update_data = publisher.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_publisher, field, value)

    await db.commit()
    await db.refresh(db_publisher)
    return db_publisher


# ============================================================================
# Manga Magazines
# ============================================================================


@router.get("/magazines", response_model=List[MangaMagazineResponse])
async def list_magazines(
    publisher_id: Optional[int] = None,
    ongoing_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    List manga magazines.
    Filter by publisher and ongoing status.
    """
    query = select(MangaMagazine)

    if publisher_id:
        query = query.where(MangaMagazine.publisher_id == publisher_id)

    if ongoing_only:
        query = query.where(MangaMagazine.is_ongoing == True)

    query = query.order_by(MangaMagazine.name)

    result = await db.execute(query)
    magazines = result.scalars().all()
    return magazines


@router.post("/magazines", response_model=MangaMagazineResponse)
async def create_magazine(
    magazine: MangaMagazineCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a manga magazine.
    Requires staff access.
    """
    await require_staff(current_user)

    # Verify publisher exists
    result = await db.execute(
        select(Publisher).where(Publisher.id == magazine.publisher_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Publisher not found")

    db_magazine = MangaMagazine(
        name=magazine.name,
        english_name=magazine.english_name,
        publisher_id=magazine.publisher_id,
        publication_frequency=magazine.publication_frequency,
        first_published=magazine.first_published,
        last_published=magazine.last_published,
        is_ongoing=magazine.is_ongoing,
        description=magazine.description,
        target_demographic=magazine.target_demographic,
        issn=magazine.issn,
        wikidata_id=magazine.wikidata_id,
    )

    db.add(db_magazine)
    await db.commit()
    await db.refresh(db_magazine)
    return db_magazine


# ============================================================================
# Manga Serialization Tracking
# ============================================================================


@router.post("/serializations", response_model=MangaSerializationResponse)
async def create_serialization(
    serialization: MangaSerializationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record manga serialization (e.g., "Weekly Shonen Jump, 2019-2023").
    Requires staff access.
    """
    await require_staff(current_user)

    # Verify work and magazine exist
    work_result = await db.execute(
        select(BibframeWork).where(BibframeWork.id == serialization.bibframe_work_id)
    )
    if not work_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Work not found")

    magazine_result = await db.execute(
        select(MangaMagazine).where(MangaMagazine.id == serialization.magazine_id)
    )
    if not magazine_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Magazine not found")

    db_serialization = MangaSerialization(
        bibframe_work_id=serialization.bibframe_work_id,
        magazine_id=serialization.magazine_id,
        start_date=serialization.start_date,
        end_date=serialization.end_date,
        is_ongoing=serialization.is_ongoing,
        start_chapter=serialization.start_chapter,
        end_chapter=serialization.end_chapter,
        notes=serialization.notes,
    )

    db.add(db_serialization)
    await db.commit()
    await db.refresh(db_serialization)
    return db_serialization


@router.get("/works/{work_id}/serializations", response_model=List[MangaSerializationResponse])
async def get_work_serializations(
    work_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all magazine serializations for a manga work.
    Shows where this manga was originally published.
    """
    result = await db.execute(
        select(MangaSerialization)
        .where(MangaSerialization.bibframe_work_id == work_id)
        .options(selectinload(MangaSerialization.magazine))
    )
    serializations = result.scalars().all()
    return serializations


# ============================================================================
# Publisher Series Tracking (for collection development)
# ============================================================================


@router.get("/series", response_model=List[PublisherSeriesResponse])
async def list_publisher_series(
    publisher_id: Optional[int] = None,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """
    List series by publisher for collection development.
    Shows which series each publisher offers and how many are in the library.
    """
    query = select(PublisherSeries)

    if publisher_id:
        query = query.where(PublisherSeries.publisher_id == publisher_id)

    if featured_only:
        query = query.where(PublisherSeries.is_featured == True)

    query = query.order_by(PublisherSeries.series_title)

    result = await db.execute(query)
    series = result.scalars().all()
    return series


@router.post("/series", response_model=PublisherSeriesResponse)
async def create_publisher_series(
    series: PublisherSeriesCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add series to publisher tracking (e.g., "Viz Media" > "Shonen Jump" series).
    Requires staff access.
    """
    await require_staff(current_user)

    # Verify publisher exists
    result = await db.execute(
        select(Publisher).where(Publisher.id == series.publisher_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Publisher not found")

    db_series = PublisherSeries(
        publisher_id=series.publisher_id,
        series_title=series.series_title,
        series_description=series.series_description,
        publisher_series_number=series.publisher_series_number,
        is_featured=series.is_featured,
        total_published_books=series.total_published_books,
        books_in_library=0,
    )

    db.add(db_series)
    await db.commit()
    await db.refresh(db_series)
    return db_series


# ============================================================================
# Manga Metadata
# ============================================================================


@router.post("/metadata", response_model=MangaMetadataResponse)
async def create_manga_metadata(
    metadata: MangaMetadataCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Add manga-specific metadata (translator, original title, etc.).
    Requires staff access.
    """
    await require_staff(current_user)

    # Verify work exists
    result = await db.execute(
        select(BibframeWork).where(BibframeWork.id == metadata.bibframe_work_id)
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Work not found")

    # Check if metadata already exists
    existing = await db.execute(
        select(MangaMetadata).where(
            MangaMetadata.bibframe_work_id == metadata.bibframe_work_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400, detail="Metadata already exists for this work"
        )

    db_metadata = MangaMetadata(
        bibframe_work_id=metadata.bibframe_work_id,
        original_japanese_title=metadata.original_japanese_title,
        romaji_title=metadata.romaji_title,
        translator_name=metadata.translator_name,
        translator_notes=metadata.translator_notes,
        original_publication_country=metadata.original_publication_country,
        is_volume_collection=metadata.is_volume_collection,
        volume_number=metadata.volume_number,
        total_chapters_in_work=metadata.total_chapters_in_work,
        chapter_range=metadata.chapter_range,
        reading_direction=metadata.reading_direction,
        original_publication_date=metadata.original_publication_date,
        english_publication_date=metadata.english_publication_date,
    )

    db.add(db_metadata)
    await db.commit()
    await db.refresh(db_metadata)
    return db_metadata


@router.get("/metadata/{work_id}", response_model=MangaMetadataResponse)
async def get_manga_metadata(work_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get manga metadata for a work (translator, original title, etc.).
    """
    metadata = await get_or_404(db, MangaMetadata, work_id, "Manga metadata not found")

    return metadata


# ============================================================================
# Collection Development Helper
# ============================================================================


@router.get(
    "/collection-development/{publisher_id}",
    response_model=CollectionDevelopmentResponse,
)
async def get_collection_development_info(
    publisher_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get collection development summary for a publisher.
    Shows series count, titles in library, out-of-print titles, and featured series.
    EASY way to track what you should acquire from each publisher/imprint.
    """
    # Get publisher
    pub_result = await db.execute(
        select(Publisher)
        .where(Publisher.id == publisher_id)
        .options(selectinload(Publisher.series))
    )
    publisher = pub_result.scalar_one_or_none()

    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")

    # Count series
    series_result = await db.execute(
        select(func.count(PublisherSeries.id)).where(
            PublisherSeries.publisher_id == publisher_id
        )
    )
    series_count = series_result.scalar() or 0

    # Count total titles linked to publisher
    titles_result = await db.execute(
        select(func.count(BibframeInstance.id)).where(
            BibframeInstance.publisher == publisher.name
        )
    )
    total_titles = titles_result.scalar() or 0

    # out_of_print_status column does not exist on BibframeInstance
    out_of_print_titles = 0

    # Get featured series
    featured_result = await db.execute(
        select(PublisherSeries)
        .where(
            and_(
                PublisherSeries.publisher_id == publisher_id,
                PublisherSeries.is_featured == True,
            )
        )
        .limit(5)
    )
    featured_series = featured_result.scalars().all()

    return {
        "publisher": publisher,
        "series_count": series_count,
        "total_titles": total_titles,
        "titles_in_library": total_titles,  # In real scenario, would filter by library holdings
        "out_of_print_titles": out_of_print_titles,
        "featured_series": featured_series,
        "recent_releases": [],  # Would populate from TrackerBook
    }


# ============================================================================
# Publisher Feeds for Collection Development
# ============================================================================


@router.get("/new-releases/{publisher_id}")
async def get_publisher_new_releases(
    publisher_id: int,
    days_ahead: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """
    Get new releases by a publisher for collection development.
    Shows upcoming releases so librarians can plan acquisitions.
    """
    # Get publisher
    pub_result = await db.execute(
        select(Publisher).where(Publisher.id == publisher_id)
    )
    publisher = pub_result.scalar_one_or_none()
    if not publisher:
        raise HTTPException(status_code=404, detail="Publisher not found")

    # Get tracked books for this publisher
    result = await db.execute(
        select(TrackerBook)
        .options(selectinload(TrackerBook.author))
        .where(TrackerBook.publisher == publisher.name)
        .order_by(TrackerBook.release_date.desc())
        .limit(50)
    )
    books = result.scalars().all()

    return {
        "publisher_id": publisher_id,
        "book_count": len(books),
        "books": [
            {
                "title": book.title,
                "author": book.author_name,
                "release_date": book.release_date,
                "status": str(book.status),
                "age_rating": str(book.age_rating),
                "isbn_13": book.isbn_13,
                "publisher": book.publisher,
            }
            for book in books
        ],
    }
