# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Admin Audiobooks API - CRUD endpoints for audiobook management

Note: The IndieAudiobook model has not been created yet. All endpoints
return empty results until the model and related infrastructure
are built. See the indie audiobook system docs for the planned schema.
"""

from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional

from app.api.v1.auth import get_current_user
from app.models.user import User

logger = get_logger(__name__)

router = APIRouter(prefix="/audiobooks", tags=["audiobooks"])

_NOT_IMPLEMENTED_DETAIL = (
    "Audiobook management is not yet available. "
    "The IndieAudiobook data model has not been created."
)


@router.get("/stats")
async def get_audiobooks_stats(
    current_user: User = Depends(get_current_user),
):
    """Get audiobook statistics for admin dashboard."""
    return {
        "total": 0,
        "active": 0,
        "inactive": 0,
        "total_listens": 0,
        "note": "Audiobook module not yet implemented",
    }


@router.get("/")
async def list_audiobooks(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    filter_status: Optional[str] = Query(None, alias="status"),
    sort: Optional[str] = Query("created_at"),
    current_user: User = Depends(get_current_user),
):
    """List all audiobooks with pagination and filtering."""
    return {
        "items": [],
        "total": 0,
        "skip": skip,
        "limit": limit,
        "note": "Audiobook module not yet implemented",
    }


@router.get("/{audiobook_id}")
async def get_audiobook(
    audiobook_id: int,
    current_user: User = Depends(get_current_user),
):
    """Get detailed information about a specific audiobook."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Audiobook not found",
    )


@router.post("/", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def create_audiobook(
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """Create a new audiobook."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_NOT_IMPLEMENTED_DETAIL,
    )


@router.put("/{audiobook_id}")
async def update_audiobook(
    audiobook_id: int,
    data: dict,
    current_user: User = Depends(get_current_user),
):
    """Update an existing audiobook."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_NOT_IMPLEMENTED_DETAIL,
    )


@router.delete("/{audiobook_id}")
async def delete_audiobook(
    audiobook_id: int,
    current_user: User = Depends(get_current_user),
):
    """Delete an audiobook."""
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=_NOT_IMPLEMENTED_DETAIL,
    )
