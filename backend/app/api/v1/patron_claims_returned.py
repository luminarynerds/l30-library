# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron - Claims Returned API Endpoints

Allows patrons to:
- File claims returned disputes for items they believe they've returned
- View their dispute history and status
- View claims returned policies
"""

from app.core.logging import get_logger
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.circulation import Checkout, CheckoutStatus
from ...models.lost_damaged import (
    ClaimsReturnedDispute, ClaimDisputeStatus,
    LostItemRecord, LostItemStatus
)
from ...models.user import User
from ...services.claims_returned_service import ClaimsReturnedService
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/patron/claims-returned", tags=["patron-claims-returned"])


# ============================================================================
# Request/Response Schemas
# ============================================================================

class PatronFileClaimRequest(BaseModel):
    checkout_id: int = Field(..., description="ID of the checkout to dispute")
    statement: str = Field(
        ...,
        min_length=20,
        max_length=2000,
        description="Detailed explanation of when and where you returned the item"
    )
    return_date: Optional[date] = Field(None, description="Approximate date you returned the item")
    return_location: Optional[str] = Field(None, max_length=100, description="Where you returned the item")


class PatronClaimResponse(BaseModel):
    id: int
    checkout_id: int
    item_title: str
    item_author: Optional[str]
    status: str
    status_display: str
    patron_statement: str
    claimed_return_date: Optional[date]
    claimed_return_location: Optional[str]
    filed_at: datetime
    resolution: Optional[str]
    resolution_reason: Optional[str]
    credit_amount: Optional[Decimal]


class PatronClaimsListResponse(BaseModel):
    claims: List[PatronClaimResponse]
    total: int


class ClaimsReturnedPolicyResponse(BaseModel):
    max_claims_per_year: int
    review_period_days: int
    claims_this_year: int
    claims_remaining: int
    is_eligible_to_file: bool
    message: str


# ============================================================================
# Endpoints
# ============================================================================

@router.get("/policy", response_model=ClaimsReturnedPolicyResponse)
async def get_claims_policy(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get claims returned policy and patron's current eligibility.

    Returns information about:
    - Maximum claims allowed per year
    - How many claims the patron has filed this year
    - Whether they can file additional claims
    """
    service = ClaimsReturnedService(db)
    history = await service.get_patron_claims_history(current_user.id)
    settings = await service.get_settings()

    is_eligible = history.claims_this_year < history.max_claims_allowed
    claims_remaining = max(0, history.max_claims_allowed - history.claims_this_year)

    if is_eligible:
        message = f"You can file up to {claims_remaining} more claim(s) this year."
    else:
        message = "You have reached the maximum number of claims for this year. Please contact the library if you have questions."

    return ClaimsReturnedPolicyResponse(
        max_claims_per_year=history.max_claims_allowed,
        review_period_days=settings.claims_returned_review_days,
        claims_this_year=history.claims_this_year,
        claims_remaining=claims_remaining,
        is_eligible_to_file=is_eligible,
        message=message,
    )


@router.post("/file", response_model=PatronClaimResponse)
async def file_claim(
    request: PatronFileClaimRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    File a claims returned dispute for a checkout.

    Use this when you believe you've returned an item but it still shows
    as checked out on your account. Provide as much detail as possible
    about when and where you returned the item.

    The library will investigate your claim and contact you with the resolution.
    """
    # Verify the checkout belongs to this patron
    checkout_result = await db.execute(
        select(Checkout)
        .options(selectinload(Checkout.item))
        .where(Checkout.id == request.checkout_id)
    )
    checkout = checkout_result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="Checkout not found")

    if checkout.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only file claims for your own checkouts")

    # Check if checkout is eligible for claims returned
    if checkout.status not in [CheckoutStatus.active, CheckoutStatus.overdue,
                               CheckoutStatus.lost, CheckoutStatus.lost_by_patron]:
        raise HTTPException(
            status_code=400,
            detail="This checkout is not eligible for a claims returned dispute. "
                   "Only active, overdue, or lost items can have claims filed."
        )

    # Check if there's already an active dispute
    existing_dispute_result = await db.execute(
        select(ClaimsReturnedDispute).where(
            ClaimsReturnedDispute.checkout_id == request.checkout_id,
            ClaimsReturnedDispute.status.in_([
                ClaimDisputeStatus.PENDING,
                ClaimDisputeStatus.UNDER_REVIEW,
                ClaimDisputeStatus.SEARCH_IN_PROGRESS
            ])
        )
    )
    existing_dispute = existing_dispute_result.scalar_one_or_none()

    if existing_dispute:
        raise HTTPException(
            status_code=400,
            detail="There is already an active dispute for this checkout. "
                   "Please wait for the current dispute to be resolved."
        )

    # File the claim
    service = ClaimsReturnedService(db)
    result = await service.file_claim(
        checkout_id=request.checkout_id,
        patron_statement=request.statement,
        claimed_return_date=request.return_date,
        claimed_return_location=request.return_location,
        filed_by=current_user,
        send_notification=True,
    )

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)

    dispute = result.dispute

    return PatronClaimResponse(
        id=dispute.id,
        checkout_id=dispute.checkout_id,
        item_title=checkout.item.title if checkout.item else "Unknown",
        item_author=checkout.item.author if checkout.item else None,
        status=dispute.status,
        status_display=_get_status_display(dispute.status),
        patron_statement=dispute.patron_statement,
        claimed_return_date=dispute.claimed_return_date,
        claimed_return_location=dispute.claimed_return_location,
        filed_at=dispute.filed_at,
        resolution=dispute.resolution,
        resolution_reason=dispute.resolution_reason,
        credit_amount=dispute.credit_amount,
    )


@router.get("/", response_model=PatronClaimsListResponse)
async def list_my_claims(
    include_resolved: bool = Query(False, description="Include resolved claims"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List all claims returned disputes filed by the current patron.

    By default, only shows active (unresolved) claims. Set include_resolved=true
    to see all claims including those that have been approved, denied, or resolved.
    """
    query = select(ClaimsReturnedDispute).options(
        selectinload(ClaimsReturnedDispute.checkout).selectinload(Checkout.item)
    ).where(
        ClaimsReturnedDispute.patron_id == current_user.id
    )

    if not include_resolved:
        query = query.where(
            ClaimsReturnedDispute.status.in_([
                ClaimDisputeStatus.PENDING,
                ClaimDisputeStatus.UNDER_REVIEW,
                ClaimDisputeStatus.SEARCH_IN_PROGRESS
            ])
        )

    # Get total count
    from sqlalchemy import func
    count_query = select(func.count(ClaimsReturnedDispute.id)).where(
        ClaimsReturnedDispute.patron_id == current_user.id
    )
    if not include_resolved:
        count_query = count_query.where(
            ClaimsReturnedDispute.status.in_([
                ClaimDisputeStatus.PENDING,
                ClaimDisputeStatus.UNDER_REVIEW,
                ClaimDisputeStatus.SEARCH_IN_PROGRESS
            ])
        )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get claims
    query = query.order_by(ClaimsReturnedDispute.filed_at.desc())
    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    disputes = result.scalars().all()

    claims = []
    for dispute in disputes:
        item_title = "Unknown"
        item_author = None
        if dispute.checkout and dispute.checkout.item:
            item_title = dispute.checkout.item.title
            item_author = dispute.checkout.item.author

        claims.append(PatronClaimResponse(
            id=dispute.id,
            checkout_id=dispute.checkout_id,
            item_title=item_title,
            item_author=item_author,
            status=dispute.status,
            status_display=_get_status_display(dispute.status),
            patron_statement=dispute.patron_statement,
            claimed_return_date=dispute.claimed_return_date,
            claimed_return_location=dispute.claimed_return_location,
            filed_at=dispute.filed_at,
            resolution=dispute.resolution,
            resolution_reason=dispute.resolution_reason,
            credit_amount=dispute.credit_amount,
        ))

    return PatronClaimsListResponse(claims=claims, total=total)


@router.get("/eligible-checkouts", response_model=List[dict])
async def get_eligible_checkouts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get checkouts that are eligible for claims returned disputes.

    Returns checkouts that are active, overdue, or lost, and don't already
    have an active dispute.
    """
    # Get checkouts that could have claims filed
    result = await db.execute(
        select(Checkout)
        .options(selectinload(Checkout.item))
        .where(
            Checkout.user_id == current_user.id,
            Checkout.status.in_([
                CheckoutStatus.active,
                CheckoutStatus.overdue,
                CheckoutStatus.lost,
                CheckoutStatus.lost_by_patron
            ])
        )
        .order_by(Checkout.due_date.desc())
    )
    checkouts = result.scalars().all()

    # Get checkouts with active disputes
    active_disputes_result = await db.execute(
        select(ClaimsReturnedDispute.checkout_id).where(
            ClaimsReturnedDispute.patron_id == current_user.id,
            ClaimsReturnedDispute.status.in_([
                ClaimDisputeStatus.PENDING,
                ClaimDisputeStatus.UNDER_REVIEW,
                ClaimDisputeStatus.SEARCH_IN_PROGRESS
            ])
        )
    )
    disputed_checkout_ids = set(active_disputes_result.scalars().all())

    eligible = []
    for checkout in checkouts:
        if checkout.id not in disputed_checkout_ids:
            eligible.append({
                "checkout_id": checkout.id,
                "item_title": checkout.item.title if checkout.item else "Unknown",
                "item_author": checkout.item.author if checkout.item else None,
                "due_date": checkout.due_date,
                "status": str(checkout.status),
                "has_active_dispute": False,
            })

    return eligible


@router.get("/{claim_id}", response_model=PatronClaimResponse)
async def get_claim_details(
    claim_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get details of a specific claims returned dispute.

    Only shows claims that belong to the current patron.
    """
    result = await db.execute(
        select(ClaimsReturnedDispute)
        .options(
            selectinload(ClaimsReturnedDispute.checkout).selectinload(Checkout.item)
        )
        .where(ClaimsReturnedDispute.id == claim_id)
    )
    dispute = result.scalar_one_or_none()

    if not dispute:
        raise HTTPException(status_code=404, detail="Claim not found")

    if dispute.patron_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only view your own claims")

    item_title = "Unknown"
    item_author = None
    if dispute.checkout and dispute.checkout.item:
        item_title = dispute.checkout.item.title
        item_author = dispute.checkout.item.author

    return PatronClaimResponse(
        id=dispute.id,
        checkout_id=dispute.checkout_id,
        item_title=item_title,
        item_author=item_author,
        status=dispute.status,
        status_display=_get_status_display(dispute.status),
        patron_statement=dispute.patron_statement,
        claimed_return_date=dispute.claimed_return_date,
        claimed_return_location=dispute.claimed_return_location,
        filed_at=dispute.filed_at,
        resolution=dispute.resolution,
        resolution_reason=dispute.resolution_reason,
        credit_amount=dispute.credit_amount,
    )


def _get_status_display(status: ClaimDisputeStatus) -> str:
    display_map = {
        ClaimDisputeStatus.PENDING: "Pending Review",
        ClaimDisputeStatus.UNDER_REVIEW: "Under Review",
        ClaimDisputeStatus.SEARCH_IN_PROGRESS: "Search in Progress",
        ClaimDisputeStatus.APPROVED: "Approved",
        ClaimDisputeStatus.DENIED: "Denied",
        ClaimDisputeStatus.ITEM_FOUND: "Item Found",
    }
    return display_map.get(status, str(status))



