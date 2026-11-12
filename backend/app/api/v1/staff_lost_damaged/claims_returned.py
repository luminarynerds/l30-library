# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Claims Returned Endpoints

Handles filing claims returned disputes, reviewing, searching,
resolving, listing, patron history, and related info endpoints.
"""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.lost_damaged import ClaimDisputeStatus
from ....models.user import User
from ....schemas.lost_damaged import (
    FileClaimRequest,
    ClaimsReturnedWorkflowResponse,
    ClaimsReturnedDisputeResponse,
    StartReviewRequest,
    StartSearchRequest,
    ResolveClaimRequest,
    ClaimResolutionResponse,
    PatronClaimsHistoryResponse,
    ClaimsListResponse,
)
from ....services.claims_returned_service import ClaimsReturnedService
from ..auth import get_current_user
from ..dependencies import require_staff
from .utils import convert_dispute, handle_enum_validation, handle_service_error

logger = get_logger(__name__)

router = APIRouter()


# ============================================================================
# Claims Returned Endpoints
# ============================================================================

@router.post("/claims-returned/file", response_model=ClaimsReturnedWorkflowResponse, status_code=status.HTTP_201_CREATED)
async def file_claims_returned_claim(
    request: FileClaimRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    File a claims returned dispute on behalf of a patron.

    Creates the dispute record and notifies staff for review.
    """
    service = ClaimsReturnedService(db)
    result = await service.file_claim(
        checkout_id=request.checkout_id,
        patron_statement=request.patron_statement,
        claimed_return_date=request.claimed_return_date,
        claimed_return_location=request.claimed_return_location,
        filed_by=staff_user,
        send_notification=request.send_notification,
    )

    handle_service_error(result)

    dispute_response = None
    if result.dispute:
        dispute_response = convert_dispute(result.dispute)

    return ClaimsReturnedWorkflowResponse(
        success=True,
        message=result.message,
        dispute=dispute_response,
        notification_sent=result.notification_sent,
    )


@router.post("/claims-returned/{dispute_id}/start-review", response_model=ClaimsReturnedWorkflowResponse)
async def start_review(
    dispute_id: int,
    request: StartReviewRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Start reviewing a claims returned dispute."""
    service = ClaimsReturnedService(db)
    result = await service.start_review(
        dispute_id=dispute_id,
        reviewed_by=staff_user,
        initial_notes=request.initial_notes,
    )

    handle_service_error(result)

    dispute_response = None
    if result.dispute:
        dispute_response = convert_dispute(result.dispute)

    return ClaimsReturnedWorkflowResponse(
        success=True,
        message=result.message,
        dispute=dispute_response,
    )


@router.post("/claims-returned/{dispute_id}/start-search", response_model=ClaimsReturnedWorkflowResponse)
async def start_search(
    dispute_id: int,
    request: StartSearchRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Start searching for a claimed returned item."""
    service = ClaimsReturnedService(db)
    result = await service.start_search(
        dispute_id=dispute_id,
        search_locations=request.search_locations,
        search_notes=request.search_notes,
    )

    handle_service_error(result)

    dispute_response = None
    if result.dispute:
        dispute_response = convert_dispute(result.dispute)

    return ClaimsReturnedWorkflowResponse(
        success=True,
        message=result.message,
        dispute=dispute_response,
    )


@router.post("/claims-returned/{dispute_id}/resolve", response_model=ClaimResolutionResponse)
async def resolve_claim(
    dispute_id: int,
    request: ResolveClaimRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve a claims returned dispute.

    Can approve, deny, or mark as item found.
    """
    service = ClaimsReturnedService(db)
    result = await service.resolve_claim(
        dispute_id=dispute_id,
        resolved_by=staff_user,
        approved=request.approved,
        resolution_reason=request.resolution_reason,
        item_found=request.item_found,
        credit_amount=request.credit_amount,
        send_notification=request.send_notification,
    )

    handle_service_error(result)

    dispute_response = None
    if result.dispute:
        dispute_response = convert_dispute(result.dispute)

    return ClaimResolutionResponse(
        success=True,
        message=result.message,
        dispute=dispute_response,
        credit_amount=result.credit_amount,
        item_found=result.item_found,
        notification_sent=result.notification_sent,
    )


@router.get("/claims-returned", response_model=ClaimsListResponse)
async def list_claims(
    status: Optional[str] = Query(None, description="Filter by status"),
    patron_id: Optional[int] = Query(None, description="Filter by patron"),
    days_ago: Optional[int] = Query(None, ge=1, description="Claims filed within X days"),
    unresolved_only: bool = Query(False, description="Show only unresolved claims"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List claims returned disputes with filtering."""
    status_enum = None
    if status:
        status_enum = handle_enum_validation(ClaimDisputeStatus, status, "status")

    service = ClaimsReturnedService(db)
    items, total = await service.get_disputes(
        status=status_enum,
        patron_id=patron_id,
        days_ago=days_ago,
        unresolved_only=unresolved_only,
        limit=limit,
        offset=offset,
    )

    return ClaimsListResponse(
        items=[convert_dispute(item) for item in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/claims-returned/patron/{patron_id}/history", response_model=PatronClaimsHistoryResponse)
async def get_patron_claims_history(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a patron's claims returned history."""
    service = ClaimsReturnedService(db)
    history = await service.get_patron_claims_history(patron_id)

    return PatronClaimsHistoryResponse(
        patron_id=history.patron_id,
        total_claims=history.total_claims,
        claims_this_year=history.claims_this_year,
        approved_claims=history.approved_claims,
        denied_claims=history.denied_claims,
        pending_claims=history.pending_claims,
        items_later_found=history.items_later_found,
        is_at_risk=history.is_at_risk,
        max_claims_allowed=history.max_claims_allowed,
    )


@router.get("/claims-returned/overdue")
async def get_overdue_disputes(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get disputes that have exceeded the review period."""
    service = ClaimsReturnedService(db)
    disputes = await service.get_overdue_disputes()

    return {
        "count": len(disputes),
        "items": [convert_dispute(d) for d in disputes],
    }


# ============================================================================
# Info Endpoints
# ============================================================================

@router.get("/claims-returned/file")
async def get_claims_returned_file_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about filing claims returned disputes.

    Returns endpoint metadata and guidance.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/claims-returned/file",
        "description": "File a claims returned dispute on behalf of a patron",
        "method": "POST",
        "required_fields": ["checkout_id", "patron_statement"],
        "optional_fields": [
            "claimed_return_date",
            "claimed_return_location",
            "send_notification",
        ],
        "workflow": [
            "1. Patron claims they returned an item",
            "2. Staff files dispute with patron's statement",
            "3. Dispute enters review queue",
            "4. Staff investigates and searches for item",
            "5. Dispute is resolved (approved/denied)",
        ],
        "notes": [
            "Used when patron disputes that item is still checked out",
            "Creates formal dispute record for investigation",
            "Patron can provide details about when/where they returned item",
        ],
    }


@router.get("/claims-returned/resolve")
async def get_claims_returned_resolve_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about resolving claims returned disputes.

    Returns endpoint metadata and resolution options.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/claims-returned/resolve",
        "description": "Resolve a claims returned dispute",
        "method": "POST",
        "required_fields": ["dispute_id", "approved", "resolution_reason"],
        "optional_fields": ["item_found", "credit_amount", "send_notification"],
        "resolution_options": {
            "approved": "Patron's claim is valid - remove charges",
            "denied": "Item not returned - charges stand",
            "item_found": "Item was located during search",
        },
        "notes": [
            "Approved claims result in charge removal/credit",
            "Denied claims maintain patron responsibility",
            "If item_found=true, item is checked in automatically",
            "Resolution reason is required for documentation",
            "Patron receives notification of decision if send_notification=true",
        ],
    }


@router.get("/claims-returned/start-review")
async def get_claims_returned_start_review_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about starting review of claims returned disputes.

    Returns endpoint metadata.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/claims-returned/start-review",
        "description": "Start reviewing a claims returned dispute",
        "method": "POST",
        "required_fields": ["dispute_id"],
        "optional_fields": ["initial_notes"],
        "notes": [
            "Marks dispute as under review",
            "Assigns reviewer to current staff member",
            "Sets reviewed_at timestamp",
            "Initial notes can document first impressions",
            "Next step is typically to start search",
        ],
    }


@router.get("/claims-returned/start-search")
async def get_claims_returned_start_search_info(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get information about starting search for claimed returned items.

    Returns endpoint metadata and search guidance.
    """
    return {
        "endpoint": "POST /staff/lost-damaged/claims-returned/start-search",
        "description": "Start searching for a claimed returned item",
        "method": "POST",
        "required_fields": ["dispute_id"],
        "optional_fields": ["search_locations", "search_notes"],
        "search_locations_examples": [
            "Returns cart",
            "Book drop",
            "Shelving area",
            "Holds shelf",
            "Staff processing area",
            "Claimed return location (if specified by patron)",
        ],
        "notes": [
            "Updates dispute status to 'searching'",
            "Documents where search will be conducted",
            "Search notes can track progress",
            "Complete search before resolving dispute",
        ],
    }
