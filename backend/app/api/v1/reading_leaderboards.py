# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reading Leaderboards API for L30 Library.
Manage reading competition leaderboards and ranking systems.
"""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.user import User
from ...services.organization_features_service import OrganizationFeaturesService
from .auth import get_current_user
from .dependencies import check_admin_access


# ============================================================================
# Enums
# ============================================================================


class LeaderboardType(StrEnum):

    minutes_read = "minutes_read"  # Most minutes read
    books_completed = "books_completed"  # Most books read
    pages_read = "pages_read"  # Most pages read
    consistency = "consistency"  # Best reading streak
    points = "points"  # Gamification points


class LeaderboardStatus(StrEnum):

    draft = "draft"  # Not yet active
    active = "active"  # Currently running
    completed = "completed"  # Finished
    archived = "archived"  # Historical


# ============================================================================
# Schemas (Request/Response Models)
# ============================================================================


class LeaderboardEntryBase(BaseModel):

    user_id: int
    rank: int = Field(..., ge=1)
    score: int = Field(..., ge=0)
    display_name: Optional[str] = Field(None, max_length=255)


class LeaderboardEntryResponse(LeaderboardEntryBase):

    id: int
    leaderboard_id: int
    updated_at: datetime

    class Config:
        from_attributes = True


class LeaderboardBase(BaseModel):

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    leaderboard_type: LeaderboardType
    program_id: Optional[int] = None
    age_group: Optional[str] = Field(None, max_length=50)
    status: LeaderboardStatus = LeaderboardStatus.draft
    start_date: datetime
    end_date: Optional[datetime] = None
    is_public: bool = True


class LeaderboardCreate(LeaderboardBase):

    pass


class LeaderboardUpdate(BaseModel):

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    status: Optional[LeaderboardStatus] = None
    end_date: Optional[datetime] = None
    is_public: Optional[bool] = None


class LeaderboardResponse(LeaderboardBase):

    id: int
    created_at: datetime
    updated_at: datetime
    participant_count: int = 0
    total_entries: int = 0

    class Config:
        from_attributes = True


class PaginatedLeaderboardsResponse(BaseModel):

    items: List[LeaderboardResponse]
    total: int
    limit: int
    offset: int


class LeaderboardWithEntriesResponse(LeaderboardResponse):

    entries: List[LeaderboardEntryResponse] = []


class UserRankResponse(BaseModel):

    rank: int
    score: int
    percentile: float
    total_participants: int
    is_top_10: bool


class TopEntriesResponse(BaseModel):

    leaderboard_id: int
    entries: List[LeaderboardEntryResponse]
    limit: int


# ============================================================================
# Leaderboard Endpoints
# ============================================================================

async def require_gamification_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "gamification_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gamification feature is not enabled",
        )


router = APIRouter(
    prefix="/reading/leaderboards",
    tags=["reading-leaderboards"],
    dependencies=[Depends(require_gamification_enabled)],
)


@router.get(
    "/",
    response_model=PaginatedLeaderboardsResponse,
)
@limiter.limit("60/minute")
async def list_active_leaderboards(
    request: Request,
    leaderboard_type: Optional[LeaderboardType] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List active leaderboards."""
    return PaginatedLeaderboardsResponse(items=[], total=0, limit=limit, offset=offset)


@router.get(
    "/{leaderboard_id}",
    response_model=LeaderboardWithEntriesResponse,
)
@limiter.limit("60/minute")
async def get_leaderboard_entries(
    request: Request,
    leaderboard_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get leaderboard entries with ranking."""
    # This endpoint assumes Leaderboard and LeaderboardEntry models exist
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Leaderboard not found"
    )


@router.get(
    "/{leaderboard_id}/my-rank",
    response_model=UserRankResponse,
)
@limiter.limit("60/minute")
async def get_user_rank(
    request: Request,
    leaderboard_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's rank on a leaderboard."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Leaderboard not found or user not ranked",
    )


@router.get(
    "/{leaderboard_id}/top",
    response_model=TopEntriesResponse,
)
@limiter.limit("120/minute")
async def get_top_entries(
    request: Request,
    leaderboard_id: int,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get top N entries on a leaderboard."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Leaderboard not found"
    )


@router.get(
    "/programs/{program_id}/leaderboards",
    response_model=PaginatedLeaderboardsResponse,
)
@limiter.limit("60/minute")
async def get_program_leaderboards(
    request: Request,
    program_id: int,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get all leaderboards for a specific program."""
    return PaginatedLeaderboardsResponse(items=[], total=0, limit=limit, offset=offset)


# ============================================================================
# Admin Leaderboard Management
# ============================================================================


@router.post(
    "/admin/create",
    response_model=LeaderboardResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def create_leaderboard(
    request: Request,
    leaderboard_data: LeaderboardCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new leaderboard (admin only)."""
    check_admin_access(current_user)

    # Validate dates
    if (
        leaderboard_data.end_date
        and leaderboard_data.end_date <= leaderboard_data.start_date
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be after start date",
        )

    # Create leaderboard in database
    # This assumes Leaderboard model exists
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Leaderboard model not implemented",
    )


@router.put(
    "/admin/{id}",
    response_model=LeaderboardResponse,
)
@limiter.limit("30/minute")
async def update_leaderboard(
    request: Request,
    id: int,
    update_data: LeaderboardUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a leaderboard (admin only)."""
    check_admin_access(current_user)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Leaderboard not found"
    )


@router.post(
    "/admin/{id}/recalculate",
    response_model=LeaderboardResponse,
)
@limiter.limit("10/minute")
async def recalculate_rankings(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Recalculate rankings for a leaderboard (admin only)."""
    check_admin_access(current_user)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Leaderboard not found"
    )
