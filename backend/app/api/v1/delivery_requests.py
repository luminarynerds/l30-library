# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Delivery Request API Endpoints

Endpoints for:
- One-click delivery requests from patrons
- Request management (view, approve, decline)
- Delivery history and tracking
"""
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models import (
    DeliveryRequest,
    DeliveryRequestStatus,
    CatalogItem,
    User,
    UserRole,
)
from ...models.home_delivery import DeliveryFrequency
from ...schemas.delivery_request import (
    DeliveryRequestCreate,
    DeliveryRequestResponse,
    DeliveryRequestListResponse,
    DeliveryRequestApprove,
    DeliveryRequestDecline,
)
from .dependencies import require_patron, require_staff

router = APIRouter(prefix="/delivery-requests", tags=["delivery-requests"])
logger = get_logger(__name__)


# =============================================================================
# Patron Endpoints: Create and View Requests
# =============================================================================


@router.post("", response_model=DeliveryRequestResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_delivery_request(
    request: Request,
    req: DeliveryRequestCreate,
    patron: User = Depends(require_patron),
    db: AsyncSession = Depends(get_db),
) -> DeliveryRequestResponse:
    """
    Create a new delivery request for an item.

    Patrons can request one-click home delivery for items with options for:
    - Single delivery (once)
    - Recurring delivery (weekly/biweekly/monthly)
    """
    # Verify item exists
    await get_or_404(db, CatalogItem, req.item_id, "Item not found")

    # Check if patron already has an active request for this item
    stmt = select(DeliveryRequest).where(
        and_(
            DeliveryRequest.user_id == patron.id,
            DeliveryRequest.item_id == req.item_id,
            DeliveryRequest.status.in_(
                [
                    DeliveryRequestStatus.pending,
                    DeliveryRequestStatus.approved,
                ]
            ),
        )
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Active delivery request already exists for this item",
        )

    # Create delivery request
    delivery_request = DeliveryRequest(
        user_id=patron.id,
        item_id=req.item_id,
        frequency=req.frequency,
        delivery_address=req.delivery_address,
        delivery_notes=req.delivery_notes,
        preferred_window=req.preferred_window,
        requested_by_date=req.requested_by_date,
        status=DeliveryRequestStatus.pending,
    )

    db.add(delivery_request)
    await db.commit()
    await db.refresh(delivery_request)

    # Enrich response
    return _enrich_delivery_request(delivery_request)


@router.get("/me", response_model=list[DeliveryRequestResponse])
@limiter.limit("30/minute")
async def get_my_delivery_requests(
    request: Request,
    patron: User = Depends(require_patron),
    status_filter: Optional[DeliveryRequestStatus] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> list[DeliveryRequestResponse]:
    """
    Get all delivery requests for the current patron.

    Optional filters:
    - status: Filter by request status (pending, approved, declined, etc.)
    """
    stmt = select(DeliveryRequest).where(DeliveryRequest.user_id == patron.id)

    if status_filter:
        stmt = stmt.where(DeliveryRequest.status == status_filter)

    stmt = stmt.order_by(DeliveryRequest.created_at.desc())
    results = (await db.execute(stmt)).scalars().all()

    return [_enrich_delivery_request(dr) for dr in results]


@router.get("/{request_id}", response_model=DeliveryRequestResponse)
@limiter.limit("30/minute")
async def get_delivery_request(
    request_id: int,
    request: Request,
    patron: User = Depends(require_patron),
    db: AsyncSession = Depends(get_db),
) -> DeliveryRequestResponse:
    """
    Get details of a specific delivery request.

    Patrons can only view their own requests.
    """
    dr = await get_or_404(db, DeliveryRequest, request_id, "Request not found")

    # Verify ownership
    if dr.user_id != patron.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot access other patrons' delivery requests",
        )

    return _enrich_delivery_request(dr)


@router.patch("/{request_id}/cancel")
@limiter.limit("10/minute")
async def cancel_delivery_request(
    request_id: int,
    request: Request,
    patron: User = Depends(require_patron),
    db: AsyncSession = Depends(get_db),
) -> DeliveryRequestResponse:
    """
    Cancel a pending or approved delivery request.

    Patrons can only cancel their own requests that are not yet in delivery.
    """
    dr = await get_or_404(db, DeliveryRequest, request_id, "Request not found")

    # Verify ownership
    if dr.user_id != patron.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel other patrons' delivery requests",
        )

    # Can only cancel if pending or approved
    if dr.status not in [DeliveryRequestStatus.pending, DeliveryRequestStatus.approved]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel request with status '{dr.status}'",
        )

    dr.status = DeliveryRequestStatus.cancelled
    dr.cancelled_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(dr)

    return _enrich_delivery_request(dr)


# =============================================================================
# Staff Endpoints: Manage Requests
# =============================================================================


@router.get("", response_model=list[DeliveryRequestListResponse])
@limiter.limit("30/minute")
async def list_delivery_requests(
    request: Request,
    staff_user: User = Depends(require_staff),
    status_filter: Optional[DeliveryRequestStatus] = Query(None, alias="status"),
    frequency_filter: Optional[DeliveryFrequency] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[DeliveryRequestListResponse]:
    """
    List all delivery requests (staff view).

    Staff can filter by:
    - status: pending, approved, declined, in_delivery, completed, cancelled
    - frequency: once, weekly, biweekly, monthly
    """
    stmt = select(DeliveryRequest)

    if status_filter:
        stmt = stmt.where(DeliveryRequest.status == status_filter)

    if frequency_filter:
        stmt = stmt.where(DeliveryRequest.frequency == frequency_filter)

    # Order by created_at descending, prioritizing pending requests
    stmt = stmt.order_by(
        DeliveryRequest.status == DeliveryRequestStatus.pending,
        DeliveryRequest.created_at.desc(),
    ).limit(limit).offset(offset)

    results = (await db.execute(stmt)).scalars().all()

    return [_enrich_list_response(dr) for dr in results]


@router.patch("/{request_id}/approve", response_model=DeliveryRequestResponse)
@limiter.limit("10/minute")
async def approve_delivery_request(
    request_id: int,
    request: Request,
    approval: DeliveryRequestApprove,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> DeliveryRequestResponse:
    """
    Approve a pending delivery request.

    Staff can add notes when approving. Request transitions to 'approved' status.
    """
    dr = await get_or_404(db, DeliveryRequest, request_id, "Request not found")

    if dr.status != DeliveryRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only approve pending requests (current status: {dr.status})",
        )

    dr.status = DeliveryRequestStatus.approved
    dr.approved_at = datetime.now(timezone.utc)
    dr.approved_by_id = staff_user.id
    if approval.notes:
        dr.delivery_notes = approval.notes

    await db.commit()
    await db.refresh(dr)

    logger.info(
        f"Delivery request {request_id} approved by staff {staff_user.id}",
        extra={"user_id": staff_user.id, "request_id": request_id},
    )

    return _enrich_delivery_request(dr)


@router.patch("/{request_id}/decline", response_model=DeliveryRequestResponse)
@limiter.limit("10/minute")
async def decline_delivery_request(
    request_id: int,
    request: Request,
    decline: DeliveryRequestDecline,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> DeliveryRequestResponse:
    """
    Decline a pending delivery request.

    Staff must provide a reason. Request transitions to 'declined' status.
    """
    dr = await get_or_404(db, DeliveryRequest, request_id, "Request not found")

    if dr.status != DeliveryRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only decline pending requests (current status: {dr.status})",
        )

    dr.status = DeliveryRequestStatus.declined
    dr.declined_at = datetime.now(timezone.utc)
    dr.decline_reason = decline.reason
    dr.approved_by_id = staff_user.id

    await db.commit()
    await db.refresh(dr)

    logger.info(
        f"Delivery request {request_id} declined by staff {staff_user.id}",
        extra={"user_id": staff_user.id, "request_id": request_id},
    )

    return _enrich_delivery_request(dr)


@router.patch("/{request_id}/mark-in-delivery")
@limiter.limit("10/minute")
async def mark_in_delivery(
    request_id: int,
    request: Request,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> DeliveryRequestResponse:
    """
    Mark a delivery request as in_delivery.

    Staff updates when item is picked up for delivery.
    """
    dr = await get_or_404(db, DeliveryRequest, request_id, "Request not found")

    if dr.status != DeliveryRequestStatus.approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only mark approved requests as in delivery (current status: {dr.status})",
        )

    dr.status = DeliveryRequestStatus.in_delivery
    await db.commit()
    await db.refresh(dr)

    return _enrich_delivery_request(dr)


@router.patch("/{request_id}/mark-delivered")
@limiter.limit("10/minute")
async def mark_delivered(
    request_id: int,
    request: Request,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
) -> DeliveryRequestResponse:
    """
    Mark a delivery request as completed.

    Staff updates when item is delivered to patron.
    """
    dr = await get_or_404(db, DeliveryRequest, request_id, "Request not found")

    if dr.status != DeliveryRequestStatus.in_delivery:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only mark in-delivery requests as delivered (current status: {dr.status})",
        )

    dr.status = DeliveryRequestStatus.completed
    dr.delivered_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(dr)

    return _enrich_delivery_request(dr)


# =============================================================================
# Helper Functions
# =============================================================================


def _enrich_delivery_request(dr: DeliveryRequest) -> DeliveryRequestResponse:
    return DeliveryRequestResponse(
        id=dr.id,
        user_id=dr.user_id,
        item_id=dr.item_id,
        status=dr.status,
        frequency=dr.frequency,
        delivery_address=dr.delivery_address,
        delivery_notes=dr.delivery_notes,
        preferred_window=dr.preferred_window,
        created_at=dr.created_at,
        updated_at=dr.updated_at,
        approved_at=dr.approved_at,
        declined_at=dr.declined_at,
        decline_reason=dr.decline_reason,
        delivered_at=dr.delivered_at,
        cancelled_at=dr.cancelled_at,
        requested_by_date=dr.requested_by_date,
        next_delivery_date=dr.next_delivery_date,
        approved_by_id=dr.approved_by_id,
        item_title=dr.item.title if dr.item else None,
        item_author=dr.item.author if dr.item else None,
        patron_name=dr.user.full_name if dr.user else None,
    )


def _enrich_list_response(dr: DeliveryRequest) -> DeliveryRequestListResponse:
    return DeliveryRequestListResponse(
        id=dr.id,
        user_id=dr.user_id,
        patron_name=dr.user.full_name if dr.user else None,
        item_id=dr.item_id,
        item_title=dr.item.title if dr.item else None,
        status=dr.status,
        frequency=dr.frequency,
        created_at=dr.created_at,
        requested_by_date=dr.requested_by_date,
        next_delivery_date=dr.next_delivery_date,
        approved_by_id=dr.approved_by_id,
    )
