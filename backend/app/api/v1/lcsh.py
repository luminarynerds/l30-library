# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
LCSH (Library of Congress Subject Headings) API endpoints
"""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...services.lcsh_service import lcsh_service
from .dependencies import require_staff

router = APIRouter(prefix="/cataloging/subjects", tags=["cataloging", "lcsh"])
logger = get_logger(__name__)


@router.get("/autocomplete")
async def autocomplete_subjects(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Autocomplete subject headings using Library of Congress Subject Headings (LCSH).

    Staff-only endpoint for cataloging assistance.

    Returns controlled vocabulary subject headings that match the query.
    """
    try:
        suggestions = lcsh_service.autocomplete(q, limit=limit)

        return {
            "ok": True,
            "query": q,
            "count": len(suggestions),
            "suggestions": suggestions,
        }

    except Exception as e:
        logger.error(f"LCSH autocomplete error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve subject headings",
        ) from e


@router.get("/validate")
async def validate_subject(
    subject: str = Query(..., min_length=1, description="Subject heading to validate"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Validate if a subject heading is a valid LCSH term.

    Staff-only endpoint for cataloging validation.

    Returns whether the subject heading is in the LCSH vocabulary.
    """
    try:
        is_valid = lcsh_service.validate(subject)

        result = {
            "ok": True,
            "subject": subject,
            "is_valid": is_valid,
        }

        # If not valid, suggest similar headings
        if not is_valid:
            similar = lcsh_service.get_similar(subject, limit=5)
            result["suggestions"] = similar

        return result

    except Exception as e:
        logger.error(f"LCSH validation error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to validate subject heading",
        ) from e


@router.get("/browse")
async def browse_subjects(
    prefix: str = Query(None, description="Browse subjects starting with prefix"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Browse subject headings by prefix.

    Staff-only endpoint for cataloging.

    Useful for exploring related subject headings by topic area.
    """
    try:
        if prefix:
            subjects = lcsh_service.get_all_starting_with(prefix, limit=limit)
        else:
            # Return first N subjects for general browsing
            subjects = lcsh_service.subjects[:limit]

        return {
            "ok": True,
            "prefix": prefix,
            "count": len(subjects),
            "subjects": subjects,
        }

    except Exception as e:
        logger.error(f"LCSH browse error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to browse subject headings",
        ) from e
