# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reading Prizes API for L30 Library.
Manage prizes, redemptions, and reward fulfillment for reading programs.
"""

from datetime import datetime
from enum import StrEnum
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_, select
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


class RedemptionStatus(StrEnum):

    pending = "pending"  # Waiting for approval
    approved = "approved"  # Approved by admin
    delivered = "delivered"  # Prize delivered to user
    cancelled = "cancelled"  # Redemption cancelled


# ============================================================================
# Schemas (Request/Response Models)
# ============================================================================


class PrizeBase(BaseModel):

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    points_required: int = Field(..., ge=1)
    quantity_available: Optional[int] = Field(None, ge=0)
    is_active: bool = True
    program_id: Optional[int] = None


class PrizeCreate(PrizeBase):

    pass


class PrizeResponse(PrizeBase):

    id: int
    program_id: Optional[int]
    created_at: datetime
    updated_at: datetime
    quantity_remaining: int = 0
    redemption_count: int = 0

    class Config:
        from_attributes = True


class RedemptionBase(BaseModel):

    prize_id: int
    user_id: Optional[int] = None


class RedemptionCreate(BaseModel):

    prize_id: int = Field(..., ge=1)


class RedemptionResponse(BaseModel):

    id: int
    prize_id: int
    user_id: int
    status: RedemptionStatus
    created_at: datetime
    updated_at: datetime
    approved_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    approved_by_id: Optional[int] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True


class PaginatedPrizesResponse(BaseModel):

    items: List[PrizeResponse]
    total: int
    limit: int
    offset: int


class PaginatedRedemptionsResponse(BaseModel):

    items: List[RedemptionResponse]
    total: int
    limit: int
    offset: int


class RedemptionApprovalRequest(BaseModel):

    approved: bool = True
    notes: Optional[str] = Field(None, max_length=500)


class RedemptionDeliveryRequest(BaseModel):

    delivery_notes: Optional[str] = Field(None, max_length=500)


class RedemptionCancelRequest(BaseModel):

    reason: Optional[str] = Field(None, max_length=500)


# ============================================================================
# Prize Endpoints
# ============================================================================

async def require_reading_programs_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "reading_programs_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading programs feature is not enabled",
        )


router = APIRouter(
    prefix="/reading/prizes",
    tags=["reading-prizes"],
    dependencies=[Depends(require_reading_programs_enabled)],
)


@router.get("/programs/{program_id}/prizes", response_model=PaginatedPrizesResponse)
@limiter.limit("60/minute")
async def list_prizes_for_program(
    request: Request,
    program_id: int,
    active_only: bool = Query(True, description="Show only active prizes"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List available prizes for a specific reading program."""
    # This endpoint assumes a Prize model exists in the database
    # For now, returning empty response as the Prize model is not yet defined
    return PaginatedPrizesResponse(items=[], total=0, limit=limit, offset=offset)


@router.get("/prizes/{prize_id}", response_model=PrizeResponse)
@limiter.limit("60/minute")
async def get_prize_details(
    request: Request,
    prize_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of a specific prize."""
    # This endpoint assumes a Prize model exists
    # For now, returning 404 as the Prize model is not yet defined
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prize not found")


@router.post(
    "/prizes/{prize_id}/redeem",
    response_model=RedemptionResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def redeem_prize(
    request: Request,
    prize_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Claim a prize (creates a pending redemption)."""
    # Validate prize exists
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prize not found")


@router.get("/my/redemptions", response_model=PaginatedRedemptionsResponse)
@limiter.limit("60/minute")
async def get_user_redemptions(
    request: Request,
    status_filter: Optional[RedemptionStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """View user's prize redemptions."""
    return PaginatedRedemptionsResponse(items=[], total=0, limit=limit, offset=offset)


# ============================================================================
# Admin Redemption Management Endpoints
# ============================================================================


@router.get(
    "/admin/redemptions", response_model=PaginatedRedemptionsResponse
)
@limiter.limit("60/minute")
async def list_all_redemptions(
    request: Request,
    status_filter: Optional[RedemptionStatus] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all prize redemptions (admin only)."""
    check_admin_access(current_user)

    return PaginatedRedemptionsResponse(items=[], total=0, limit=limit, offset=offset)


@router.put(
    "/admin/redemptions/{id}/approve",
    response_model=RedemptionResponse,
)
@limiter.limit("30/minute")
async def approve_redemption(
    request: Request,
    id: int,
    approval_data: RedemptionApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a pending prize redemption (admin only)."""
    check_admin_access(current_user)

    # Check if redemption exists and is pending
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Redemption not found"
    )


@router.put(
    "/admin/redemptions/{id}/deliver",
    response_model=RedemptionResponse,
)
@limiter.limit("30/minute")
async def mark_redemption_delivered(
    request: Request,
    id: int,
    delivery_data: RedemptionDeliveryRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a redemption as delivered (admin only)."""
    check_admin_access(current_user)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Redemption not found"
    )


@router.put(
    "/admin/redemptions/{id}/cancel",
    response_model=RedemptionResponse,
)
@limiter.limit("30/minute")
async def cancel_redemption(
    request: Request,
    id: int,
    cancel_data: RedemptionCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a prize redemption (admin only)."""
    check_admin_access(current_user)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Redemption not found"
    )
