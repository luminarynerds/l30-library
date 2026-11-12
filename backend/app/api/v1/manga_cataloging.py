# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Manga Cataloging API Endpoints

Provides endpoints for efficient manga series cataloging:
- Template management
- Quick volume addition
- Copy and increment
- Batch volume creation
- Cover image auto-fetching
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.manga_cataloging import MangaCatalogingTemplate, MangaVolumeRecord
from ...models.user import User
from ...schemas.manga_cataloging import (
    BatchCreateMangaVolumesRequest,
    CopyAndIncrementVolumeRequest,
    ISBNLookupResponse,
    MangaCatalogingStats,
    MangaCatalogingTemplateCreate,
    MangaCatalogingTemplateResponse,
    MangaCatalogingTemplateUpdate,
    MangaVolumeRecordCreate,
    MangaVolumeRecordResponse,
    MangaVolumeRecordUpdate,
    QuickAddMangaVolumeRequest,
    SeriesInfoResponse,
)
from ...services.manga_cataloging_service import MangaCatalogingService
from .dependencies import require_staff

router = APIRouter(prefix="/manga-cataloging", tags=["manga-cataloging"])


# ============================================================================
# Template Management Endpoints
# ============================================================================


@router.get(
    "/templates",
    response_model=list[MangaCatalogingTemplateResponse],
)
async def list_manga_templates(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all available manga cataloging templates"""
    result = await db.execute(
        select(MangaCatalogingTemplate).order_by(MangaCatalogingTemplate.name)
    )
    templates = result.scalars().all()
    return templates


@router.get(
    "/templates/{template_id}",
    response_model=MangaCatalogingTemplateResponse,
)
async def get_manga_template(
    template_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific manga cataloging template"""
    result = await db.execute(
        select(MangaCatalogingTemplate).where(
            MangaCatalogingTemplate.id == template_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )
    return template


@router.post(
    "/templates",
    response_model=MangaCatalogingTemplateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manga_template(
    template_in: MangaCatalogingTemplateCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new manga cataloging template"""
    template = MangaCatalogingTemplate(
        **template_in.model_dump(exclude_unset=True),
        created_by_id=staff_user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put(
    "/templates/{template_id}",
    response_model=MangaCatalogingTemplateResponse,
)
async def update_manga_template(
    template_id: int,
    template_in: MangaCatalogingTemplateUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a manga cataloging template"""
    result = await db.execute(
        select(MangaCatalogingTemplate).where(
            MangaCatalogingTemplate.id == template_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    update_data = template_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(template, field, value)

    await db.commit()
    await db.refresh(template)
    return template


@router.delete(
    "/templates/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_manga_template(
    template_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a manga cataloging template"""
    result = await db.execute(
        select(MangaCatalogingTemplate).where(
            MangaCatalogingTemplate.id == template_id
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template not found",
        )

    await db.delete(template)
    await db.commit()


# ============================================================================
# Volume Management Endpoints
# ============================================================================


@router.get(
    "/volumes",
    response_model=list[MangaVolumeRecordResponse],
)
async def list_manga_volumes(
    series_title: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List manga volume records with optional series filter"""
    query = select(MangaVolumeRecord)

    if series_title:
        safe_title = series_title.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            MangaVolumeRecord.series_title.ilike(f"%{safe_title}%")
        )

    query = query.order_by(
        MangaVolumeRecord.series_title,
        MangaVolumeRecord.volume_number,
    )

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    volumes = result.scalars().all()
    return volumes


@router.get(
    "/volumes/{volume_id}",
    response_model=MangaVolumeRecordResponse,
)
async def get_manga_volume(
    volume_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific manga volume record"""
    result = await db.execute(
        select(MangaVolumeRecord).where(MangaVolumeRecord.id == volume_id)
    )
    volume = result.scalar_one_or_none()
    if not volume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volume not found",
        )
    return volume


@router.post(
    "/volumes",
    response_model=MangaVolumeRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_manga_volume(
    volume_in: MangaVolumeRecordCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new manga volume record"""
    volume = MangaVolumeRecord(**volume_in.model_dump())
    db.add(volume)
    await db.commit()
    await db.refresh(volume)
    return volume


@router.put(
    "/volumes/{volume_id}",
    response_model=MangaVolumeRecordResponse,
)
async def update_manga_volume(
    volume_id: int,
    volume_in: MangaVolumeRecordUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a manga volume record"""
    result = await db.execute(
        select(MangaVolumeRecord).where(MangaVolumeRecord.id == volume_id)
    )
    volume = result.scalar_one_or_none()
    if not volume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volume not found",
        )

    update_data = volume_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(volume, field, value)

    await db.commit()
    await db.refresh(volume)
    return volume


@router.delete(
    "/volumes/{volume_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_manga_volume(
    volume_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Delete a manga volume record"""
    result = await db.execute(
        select(MangaVolumeRecord).where(MangaVolumeRecord.id == volume_id)
    )
    volume = result.scalar_one_or_none()
    if not volume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Volume not found",
        )

    await db.delete(volume)
    await db.commit()


# ============================================================================
# Efficiency Feature Endpoints
# ============================================================================


@router.post(
    "/quick-add-volume",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def quick_add_manga_volume(
    request: QuickAddMangaVolumeRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Quick-add a new manga volume with auto-populated fields.

    Features:
    - Auto-populate series info from previous volumes
    - Optional copy from existing volume
    - Auto-fetch cover image from ISBN
    - Create reading order entry
    """
    result = await MangaCatalogingService.quick_add_manga_volume(
        db, request, staff_user.id
    )
    return result


@router.post(
    "/copy-and-increment",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def copy_and_increment_volume(
    request: CopyAndIncrementVolumeRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Copy a volume record and increment the volume number.

    This reduces data entry by cloning fields from a previous volume
    and updating the volume number and optionally ISBN.
    """
    try:
        result = await MangaCatalogingService.copy_and_increment_volume(
            db,
            request.source_volume_id,
            request.new_volume_number,
            request.isbn,
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.post(
    "/batch-create-volumes",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
)
async def batch_create_manga_volumes(
    request: BatchCreateMangaVolumesRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Batch create multiple manga volumes for a series.

    Useful for processing multi-volume purchases or completing
    series retroactively. Auto-fetches covers and uses template
    defaults to minimize data entry.
    """
    result = await MangaCatalogingService.batch_create_manga_volumes(
        db,
        request.series_title,
        request.volumes,
        request.template_id,
    )
    return result


@router.get(
    "/isbn/{isbn}/cover",
    response_model=dict,
)
async def fetch_cover_from_isbn(
    isbn: str,
    staff_user: User = Depends(require_staff),
):
    """
    Fetch cover image URL from ISBN.

    Queries Open Library and Google Books APIs to find cover images.
    Useful for quick lookup without creating a full record.
    """
    cover_url = await MangaCatalogingService.fetch_cover_from_isbn(isbn)
    return {
        "isbn": isbn,
        "cover_url": cover_url,
        "source": "open_library" if cover_url else None,
    }


@router.get(
    "/isbn/{isbn}/lookup",
    response_model=ISBNLookupResponse,
)
async def isbn_lookup_autofill(
    isbn: str,
    staff_user: User = Depends(require_staff),
):
    """
    Lookup full book metadata from ISBN for auto-fill.

    Queries Open Library and Google Books APIs to return title, author,
    publisher, publication date, page count, cover URL, and description.
    Use this to auto-fill catalog fields when adding a new volume by ISBN.
    """
    metadata = await MangaCatalogingService.lookup_isbn_metadata(isbn)
    return ISBNLookupResponse(**metadata)


@router.get(
    "/series/{series_title}/info",
    response_model=SeriesInfoResponse,
)
async def get_series_info(
    series_title: str,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get auto-populated series info from previous volumes.

    Returns common fields (publisher, language, format) that can
    be used as defaults for new volumes in the series.
    Includes the next suggested volume number for the series.
    """
    series_info = (
        await MangaCatalogingService.get_series_info_from_previous_volumes(
            db, series_title
        )
    )

    # Get volume count
    result = await db.execute(
        select(func.count(MangaVolumeRecord.id)).where(
            MangaVolumeRecord.series_title == series_title
        )
    )
    volume_count = result.scalar() or 0

    # Get next volume number
    next_volume = await MangaCatalogingService.get_next_volume_number(
        db, series_title
    )

    return SeriesInfoResponse(
        series_title=series_title,
        total_volumes=volume_count,
        next_volume_number=next_volume,
        auto_populate_info=series_info,
    )


@router.get(
    "/stats",
    response_model=MangaCatalogingStats,
)
async def get_manga_cataloging_stats(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get statistics on manga cataloging usage"""

    # Total templates
    result = await db.execute(
        select(func.count(MangaCatalogingTemplate.id))
    )
    total_templates = result.scalar() or 0

    # Total volumes
    result = await db.execute(select(func.count(MangaVolumeRecord.id)))
    total_volumes = result.scalar() or 0

    # Total unique series
    result = await db.execute(
        select(func.count(func.distinct(MangaVolumeRecord.series_title)))
    )
    total_series = result.scalar() or 0

    # Average volumes per series
    avg_volumes = (
        total_volumes / total_series if total_series > 0 else 0
    )

    # Templates with auto-cover fetch enabled
    result = await db.execute(
        select(func.count(MangaCatalogingTemplate.id)).where(
            MangaCatalogingTemplate.auto_fetch_cover == True
        )
    )
    templates_with_auto_cover = result.scalar() or 0

    return MangaCatalogingStats(
        total_templates=total_templates,
        total_volumes=total_volumes,
        total_series=total_series,
        avg_volumes_per_series=round(avg_volumes, 2),
        templates_with_auto_cover=templates_with_auto_cover,
    )
