# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Work Relationships API Endpoints

Manages cross-format adaptations and links between works:
- Create, read, update, delete work relationships
- Find related works in different formats
- Get format suggestions (if you liked X, try Y)
- Cross-format discovery queries

Example scenarios:
- Link manga to anime adaptation
- Link light novel to manga adaptation
- Link film to novelization
- Link soundtrack CD to series
- Link art book to main series
"""

from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .auth import get_current_user
from ...core.rate_limit import limiter
from ...models.user import User, UserRole
from ...models.work_relationships import (
    WorkRelationship, RelationshipType, RelationshipDirection,
    FormatSuggestion, CrossFormatDiscovery
)
from ...schemas.work_relationships import (
    WorkRelationshipCreate,
    WorkRelationshipResponse,
    WorkRelationshipUpdate,
    FormatSuggestionCreate,
    FormatSuggestionResponse,
    CrossFormatDiscoveryResponse,
    RelatedWorksResponse
)
from ...services.work_relationship_service import WorkRelationshipService

router = APIRouter(prefix="/work-relationships", tags=["Work Relationships"])

# Mirrors require_staff in app/api/v1/dependencies.py; User has no is_staff attribute.
_STAFF_ROLES = (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL)


@router.post(
    "/",
    response_model=WorkRelationshipResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create work relationship",
    description="Create a new relationship between two works (e.g., manga-to-anime)"
)
@limiter.limit("10/minute")
async def create_relationship(
    request: WorkRelationshipCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new work relationship."""
    # Verify user is staff/librarian
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can create work relationships"
        )

    relationship = await WorkRelationshipService.create_relationship(
        db,
        source_work_id=request.source_work_id,
        target_work_id=request.target_work_id,
        relationship_type=request.relationship_type,
        direction=request.direction or RelationshipDirection.forward,
        title=request.title,
        description=request.description,
        is_official=request.is_official if request.is_official is not None else True,
        adaptation_fidelity=request.adaptation_fidelity,
        created_by_id=current_user.id,
        **request.dict(exclude={
            'source_work_id', 'target_work_id', 'relationship_type',
            'direction', 'title', 'description', 'is_official', 'adaptation_fidelity'
        }, exclude_none=True)
    )

    await db.commit()
    return relationship


@router.get(
    "/{relationship_id}",
    response_model=WorkRelationshipResponse,
    summary="Get work relationship",
    description="Retrieve a specific work relationship"
)
@limiter.limit("30/minute")
async def get_relationship(
    request: Request,
    relationship_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get a specific work relationship."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(WorkRelationship)
        .where(WorkRelationship.id == relationship_id)
        .options(selectinload(WorkRelationship.source_work))
        .options(selectinload(WorkRelationship.target_work))
    )
    relationship = result.scalar_one_or_none()

    if not relationship:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found"
        )

    return relationship


@router.get(
    "/work/{work_id}/related",
    response_model=RelatedWorksResponse,
    summary="Get related works",
    description="Get all works related to a specific work in different formats"
)
@limiter.limit("30/minute")
async def get_related_works(
    request: Request,
    work_id: int,
    relationship_types: Optional[str] = Query(
        None,
        description="Comma-separated list of relationship types to filter by"
    ),
    include_backreferences: bool = Query(
        True,
        description="Include works that link TO this work (not just FROM it)"
    ),
    db: AsyncSession = Depends(get_db)
):
    """Get all works related to a specific work."""
    # Parse relationship types if provided
    rel_types = None
    if relationship_types:
        rel_types = [
            RelationshipType(rt.strip())
            for rt in relationship_types.split(",")
        ]

    if include_backreferences:
        result = await WorkRelationshipService.find_related_works_bidirectional(
            db, work_id, rel_types
        )
    else:
        forward = await WorkRelationshipService.find_related_works(
            db, work_id, rel_types
        )
        result = {
            "as_source": forward,
            "as_target": []
        }

    return RelatedWorksResponse(
        work_id=work_id,
        related_as_source=[
            {
                "work_id": item.get("target_work_id", item.get("work_id")),
                "title": (item.get("target_work") or item.get("work")).title,
                "work_type": (item.get("target_work") or item.get("work")).work_type,
                "relationship_type": item["relationship_type"],
                "relationship_id": item["relationship"].id
            }
            for item in result["as_source"]
        ],
        related_as_target=[
            {
                "work_id": item.get("work_id", item.get("source_work_id")),
                "title": (item.get("work") or item.get("source_work")).title,
                "work_type": (item.get("work") or item.get("source_work")).work_type,
                "relationship_type": item["relationship_type"],
                "relationship_id": item["relationship"].id
            }
            for item in result["as_target"]
        ]
    )


@router.get(
    "/work/{work_id}/all-formats",
    response_model=dict,
    summary="Get all formats of work",
    description="Get all available formats (manga, anime, light novel, etc.) of a work"
)
@limiter.limit("30/minute")
async def get_all_formats(
    request: Request,
    work_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get all available formats of a work."""
    formats = await WorkRelationshipService.get_all_formats(db, work_id)

    return {
        "work_id": work_id,
        "formats": {
            # relationship_type comes back from the DB as a plain str in some
            # driver/enum configurations (RelationshipType is a StrEnum), not
            # always the enum member -- normalize instead of assuming .value.
            getattr(rel_type, "value", rel_type): [
                {
                    "id": work.id,
                    "title": work.title,
                    "work_type": str(work.work_type)
                }
                for work in works
            ]
            for rel_type, works in formats.items()
        }
    }


@router.post(
    "/suggestions",
    response_model=FormatSuggestionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create format suggestion",
    description="Create 'If you liked X, try Y' format suggestion"
)
@limiter.limit("10/minute")
async def create_suggestion(
    request: FormatSuggestionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a format suggestion."""
    # Verify user is staff/librarian
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can create suggestions"
        )

    suggestion = await WorkRelationshipService.create_format_suggestion(
        db,
        source_work_id=request.source_work_id,
        target_work_id=request.target_work_id,
        suggestion_text=request.suggestion_text,
        confidence_score=request.confidence_score or 50,
        is_global=request.is_global if request.is_global is not None else True,
        created_by_id=current_user.id,
        **request.dict(
            exclude={'source_work_id', 'target_work_id', 'suggestion_text',
                    'confidence_score', 'is_global'},
            exclude_none=True
        )
    )

    await db.commit()
    return suggestion


@router.get(
    "/work/{work_id}/suggestions",
    response_model=List[FormatSuggestionResponse],
    summary="Get format suggestions",
    description="Get 'If you liked this, try...' suggestions for a work"
)
@limiter.limit("30/minute")
async def get_suggestions(
    request: Request,
    work_id: int,
    global_only: bool = Query(True, description="Only show global suggestions"),
    db: AsyncSession = Depends(get_db)
):
    """Get format suggestions for a work."""
    suggestions = await WorkRelationshipService.get_suggestions_for_work(
        db, work_id, is_global=global_only
    )
    return suggestions


@router.get(
    "/discovery/{series_name}",
    response_model=CrossFormatDiscoveryResponse,
    summary="Cross-format discovery",
    description="Search for all formats of a series by name"
)
@limiter.limit("30/minute")
async def search_discovery(
    request: Request,
    series_name: str,
    db: AsyncSession = Depends(get_db)
):
    """Search cross-format discovery by series name."""
    discovery = await WorkRelationshipService.search_by_format(db, series_name)

    if not discovery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No cross-format discovery data found for this series"
        )

    return discovery


@router.put(
    "/{relationship_id}",
    response_model=WorkRelationshipResponse,
    summary="Update work relationship",
    description="Update a work relationship"
)
@limiter.limit("10/minute")
async def update_relationship(
    relationship_id: int,
    request: WorkRelationshipUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a work relationship."""
    from sqlalchemy import select

    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can update relationships"
        )

    relationship = await get_or_404(db, WorkRelationship, relationship_id, "Relationship not found")

    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(relationship, field, value)

    await db.commit()
    await db.refresh(relationship)
    return relationship


@router.delete(
    "/{relationship_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete work relationship",
    description="Delete a work relationship"
)
@limiter.limit("10/minute")
async def delete_relationship(
    request: Request,
    relationship_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a work relationship."""
    if current_user.role not in _STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff can delete relationships"
        )

    success = await WorkRelationshipService.delete_relationship(db, relationship_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Relationship not found"
        )

    await db.commit()
