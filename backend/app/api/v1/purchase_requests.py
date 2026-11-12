# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Purchase Request API Endpoints

Patron-facing:
- Submit a purchase request
- List my requests
- Get request status
- Cancel my request

Staff-facing:
- Review queue (list pending requests)
- Approve / decline individual requests
- Bulk approve / decline
- Link request to purchase order
- Mark request as received
- Fulfillment statistics
- Decline reason templates CRUD
"""

from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.catalog import CatalogItem
from ...models.acquisition import SelectionListItem
from ...models.purchase_request import (
    DeclineReasonTemplate,
    PatronPurchaseRequest,
    PurchaseRequestStatus,
)
from ...models.user import User
from ...schemas.purchase_request import (
    ApproveRequestBody,
    BulkActionResponse,
    BulkActionResult,
    BulkApproveRequest,
    BulkDeclineRequest,
    DeclineReasonTemplateCreate,
    DeclineReasonTemplateResponse,
    DeclineReasonTemplateUpdate,
    DeclineRequestBody,
    DuplicateCheckResult,
    FulfillmentStatsResponse,
    LinkToOrderRequest,
    PurchaseRequestCreate,
    PurchaseRequestListResponse,
    PurchaseRequestResponse,
    PurchaseRequestStaffListResponse,
    PurchaseRequestStaffResponse,
)
from ...services.purchase_request_service import (
    auto_check_review_sources,
    check_duplicate,
    check_existing_pending_request,
    get_fulfillment_stats,
    send_request_notification,
)
from ..v1.auth import get_current_user
from .dependencies import check_staff_access

logger = get_logger(__name__)

router = APIRouter(prefix="/purchase-requests", tags=["purchase-requests"])


# ============ Authorization Helpers ============


# ============ Patron Endpoints ============


@router.post("", response_model=PurchaseRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_purchase_request(
    body: PurchaseRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new purchase request as a patron."""
    # Check for duplicate pending request by the same patron
    existing = await check_existing_pending_request(
        db, current_user.id, body.title, body.author
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have an active request for this title (request #{existing.id})",
        )

    # Check if we already own this item
    dup_result = await check_duplicate(db, body.title, body.author, body.isbn)

    request = PatronPurchaseRequest(
        patron_id=current_user.id,
        title=body.title,
        author=body.author,
        isbn=body.isbn,
        material_type=body.material_type,
        publisher=body.publisher,
        publication_year=body.publication_year,
        patron_notes=body.patron_notes,
        status=PurchaseRequestStatus.PENDING,
    )

    # Record duplicate check result
    if dup_result.has_duplicate:
        request.duplicate_of_catalog_id = dup_result.catalog_item_id
    request.duplicate_check_done = True

    # Auto-check review sources (async but non-blocking)
    try:
        await auto_check_review_sources(request)
    except Exception:
        logger.exception("Review source check failed, continuing")

    db.add(request)
    await db.commit()
    await db.refresh(request)

    # Send confirmation notification
    request.patron = current_user  # attach for notification
    try:
        await send_request_notification(db, request, "submitted")
    except Exception:
        logger.exception("Failed to send submission notification")

    return request


@router.get("/mine", response_model=PurchaseRequestListResponse)
async def list_my_requests(
    status_filter: PurchaseRequestStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the current patron's purchase requests."""
    query = select(PatronPurchaseRequest).where(
        PatronPurchaseRequest.patron_id == current_user.id
    )
    count_query = select(func.count(PatronPurchaseRequest.id)).where(
        PatronPurchaseRequest.patron_id == current_user.id
    )

    if status_filter:
        query = query.where(PatronPurchaseRequest.status == status_filter)
        count_query = count_query.where(PatronPurchaseRequest.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(
        PatronPurchaseRequest.created_at.desc()
    )

    result = await db.execute(query)
    items = result.scalars().all()

    return PurchaseRequestListResponse(
        items=[PurchaseRequestResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/mine/{request_id}", response_model=PurchaseRequestResponse)
async def get_my_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get details of one of the patron's own requests."""
    req = await get_or_404(db, PatronPurchaseRequest, request_id, "Purchase request not found")
    if req.patron_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")
    return req


@router.post("/mine/{request_id}/cancel", response_model=PurchaseRequestResponse)
async def cancel_my_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a pending purchase request (patron only)."""
    req = await get_or_404(db, PatronPurchaseRequest, request_id, "Purchase request not found")
    if req.patron_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your request")
    if req.status not in [PurchaseRequestStatus.PENDING, PurchaseRequestStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel a request with status '{req.status}'",
        )
    req.status = PurchaseRequestStatus.CANCELLED
    await db.commit()
    await db.refresh(req)
    return req


@router.get("/check-duplicate", response_model=DuplicateCheckResult)
async def check_duplicate_endpoint(
    title: str = Query(..., max_length=500),
    author: str | None = Query(None, max_length=255),
    isbn: str | None = Query(None, max_length=20),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Check if the library already owns this item (useful before submitting)."""
    return await check_duplicate(db, title, author, isbn)


# ============ Staff Endpoints ============


@router.get("/queue", response_model=PurchaseRequestStaffListResponse)
async def staff_review_queue(
    status_filter: PurchaseRequestStatus | None = Query(None, alias="status"),
    has_duplicate: bool | None = Query(None, description="Filter to requests with catalog duplicates"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List purchase requests for staff review (review queue)."""
    check_staff_access(current_user)

    query = select(PatronPurchaseRequest).options(
        selectinload(PatronPurchaseRequest.patron),
        selectinload(PatronPurchaseRequest.reviewed_by),
        selectinload(PatronPurchaseRequest.duplicate_of_catalog),
    )
    count_query = select(func.count(PatronPurchaseRequest.id))

    if status_filter:
        query = query.where(PatronPurchaseRequest.status == status_filter)
        count_query = count_query.where(PatronPurchaseRequest.status == status_filter)
    else:
        # Default: show pending and under_review first
        query = query.order_by(
            # Pending first, then under_review, then others
            PatronPurchaseRequest.status.asc(),
        )

    if has_duplicate is True:
        query = query.where(PatronPurchaseRequest.duplicate_of_catalog_id.isnot(None))
        count_query = count_query.where(PatronPurchaseRequest.duplicate_of_catalog_id.isnot(None))
    elif has_duplicate is False:
        query = query.where(PatronPurchaseRequest.duplicate_of_catalog_id.is_(None))
        count_query = count_query.where(PatronPurchaseRequest.duplicate_of_catalog_id.is_(None))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(
        PatronPurchaseRequest.created_at.asc()
    )

    result = await db.execute(query)
    items = result.scalars().all()

    response_items = []
    for item in items:
        resp = PurchaseRequestStaffResponse.model_validate(item)
        resp.patron_name = item.patron.full_name if item.patron else None
        resp.reviewer_name = item.reviewed_by.full_name if item.reviewed_by else None
        if item.duplicate_of_catalog:
            resp.duplicate_title = item.duplicate_of_catalog.title
        response_items.append(resp)

    return PurchaseRequestStaffListResponse(
        items=response_items,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/queue/{request_id}", response_model=PurchaseRequestStaffResponse)
async def staff_get_request(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get full staff view of a purchase request."""
    check_staff_access(current_user)

    result = await db.execute(
        select(PatronPurchaseRequest)
        .options(
            selectinload(PatronPurchaseRequest.patron),
            selectinload(PatronPurchaseRequest.reviewed_by),
            selectinload(PatronPurchaseRequest.duplicate_of_catalog),
        )
        .where(PatronPurchaseRequest.id == request_id)
    )
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Purchase request not found")

    resp = PurchaseRequestStaffResponse.model_validate(req)
    resp.patron_name = req.patron.full_name if req.patron else None
    resp.reviewer_name = req.reviewed_by.full_name if req.reviewed_by else None
    if req.duplicate_of_catalog:
        resp.duplicate_title = req.duplicate_of_catalog.title
    return resp


@router.post("/queue/{request_id}/approve", response_model=PurchaseRequestStaffResponse)
async def staff_approve_request(
    request_id: int,
    body: ApproveRequestBody = ApproveRequestBody(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve a purchase request."""
    check_staff_access(current_user)

    req = await get_or_404(db, PatronPurchaseRequest, request_id, "Purchase request not found")
    if req.status not in [PurchaseRequestStatus.PENDING, PurchaseRequestStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve a request with status '{req.status}'",
        )

    req.status = PurchaseRequestStatus.APPROVED
    req.reviewed_by_id = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    if body.staff_notes:
        req.staff_notes = body.staff_notes

    await db.commit()
    await db.refresh(req, ["patron", "reviewed_by", "duplicate_of_catalog"])

    resp = PurchaseRequestStaffResponse.model_validate(req)
    resp.patron_name = req.patron.full_name if req.patron else None
    resp.reviewer_name = current_user.full_name
    return resp


@router.post("/queue/{request_id}/decline", response_model=PurchaseRequestStaffResponse)
async def staff_decline_request(
    request_id: int,
    body: DeclineRequestBody,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Decline a purchase request with a reason."""
    check_staff_access(current_user)

    req = await get_or_404(db, PatronPurchaseRequest, request_id, "Purchase request not found")
    if req.status not in [PurchaseRequestStatus.PENDING, PurchaseRequestStatus.UNDER_REVIEW]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot decline a request with status '{req.status}'",
        )

    req.status = PurchaseRequestStatus.DECLINED
    req.reviewed_by_id = current_user.id
    req.reviewed_at = datetime.now(timezone.utc)
    req.decline_reason = body.decline_reason
    if body.staff_notes:
        req.staff_notes = body.staff_notes

    await db.commit()
    await db.refresh(req, ["patron", "reviewed_by", "duplicate_of_catalog"])

    # Send decline notification
    try:
        await send_request_notification(db, req, "declined")
    except Exception:
        logger.exception("Failed to send decline notification")

    resp = PurchaseRequestStaffResponse.model_validate(req)
    resp.patron_name = req.patron.full_name if req.patron else None
    resp.reviewer_name = current_user.full_name
    return resp


@router.post("/queue/bulk-approve", response_model=BulkActionResponse)
async def staff_bulk_approve(
    body: BulkApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk approve multiple purchase requests."""
    check_staff_access(current_user)

    results = []
    succeeded = 0
    now = datetime.now(timezone.utc)

    for rid in body.request_ids:
        result = await db.execute(
            select(PatronPurchaseRequest).where(PatronPurchaseRequest.id == rid)
        )
        req = result.scalar_one_or_none()
        if not req:
            results.append(BulkActionResult(request_id=rid, success=False, error="Not found"))
            continue
        if req.status not in [PurchaseRequestStatus.PENDING, PurchaseRequestStatus.UNDER_REVIEW]:
            results.append(BulkActionResult(
                request_id=rid, success=False,
                error=f"Invalid status: {req.status}",
            ))
            continue

        req.status = PurchaseRequestStatus.APPROVED
        req.reviewed_by_id = current_user.id
        req.reviewed_at = now
        if body.staff_notes:
            req.staff_notes = body.staff_notes
        results.append(BulkActionResult(request_id=rid, success=True))
        succeeded += 1

    await db.commit()

    return BulkActionResponse(
        total_requested=len(body.request_ids),
        succeeded=succeeded,
        failed=len(body.request_ids) - succeeded,
        results=results,
    )


@router.post("/queue/bulk-decline", response_model=BulkActionResponse)
async def staff_bulk_decline(
    body: BulkDeclineRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk decline multiple purchase requests."""
    check_staff_access(current_user)

    results = []
    succeeded = 0
    now = datetime.now(timezone.utc)

    for rid in body.request_ids:
        result = await db.execute(
            select(PatronPurchaseRequest).where(PatronPurchaseRequest.id == rid)
        )
        req = result.scalar_one_or_none()
        if not req:
            results.append(BulkActionResult(request_id=rid, success=False, error="Not found"))
            continue
        if req.status not in [PurchaseRequestStatus.PENDING, PurchaseRequestStatus.UNDER_REVIEW]:
            results.append(BulkActionResult(
                request_id=rid, success=False,
                error=f"Invalid status: {req.status}",
            ))
            continue

        req.status = PurchaseRequestStatus.DECLINED
        req.reviewed_by_id = current_user.id
        req.reviewed_at = now
        req.decline_reason = body.decline_reason
        if body.staff_notes:
            req.staff_notes = body.staff_notes
        results.append(BulkActionResult(request_id=rid, success=True))
        succeeded += 1

        # Send notification for each declined request
        try:
            await db.refresh(req, ["patron"])
            await send_request_notification(db, req, "declined")
        except Exception:
            logger.exception(f"Failed to send decline notification for request {rid}")

    await db.commit()

    return BulkActionResponse(
        total_requested=len(body.request_ids),
        succeeded=succeeded,
        failed=len(body.request_ids) - succeeded,
        results=results,
    )


@router.post("/queue/{request_id}/link-order", response_model=PurchaseRequestStaffResponse)
async def staff_link_to_order(
    request_id: int,
    body: LinkToOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Link an approved request to a purchase order and mark as ordered."""
    check_staff_access(current_user)

    req = await get_or_404(db, PatronPurchaseRequest, request_id, "Purchase request not found")
    if req.status not in [PurchaseRequestStatus.APPROVED, PurchaseRequestStatus.ORDERED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only link orders for approved requests (current: {req.status})",
        )

    req.purchase_order_id = body.purchase_order_id
    req.status = PurchaseRequestStatus.ORDERED

    # Send "we ordered your request" notification
    if not req.ordered_notified:
        req.ordered_notified = True
        await db.commit()
        await db.refresh(req, ["patron"])
        try:
            await send_request_notification(db, req, "ordered")
        except Exception:
            logger.exception("Failed to send ordered notification")
    else:
        await db.commit()

    await db.refresh(req, ["patron", "reviewed_by", "duplicate_of_catalog"])
    resp = PurchaseRequestStaffResponse.model_validate(req)
    resp.patron_name = req.patron.full_name if req.patron else None
    resp.reviewer_name = req.reviewed_by.full_name if req.reviewed_by else None
    return resp


@router.post("/queue/{request_id}/mark-received", response_model=PurchaseRequestStaffResponse)
async def staff_mark_received(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a request as received (item arrived at library)."""
    check_staff_access(current_user)

    req = await get_or_404(db, PatronPurchaseRequest, request_id, "Purchase request not found")
    if req.status not in [PurchaseRequestStatus.ORDERED, PurchaseRequestStatus.APPROVED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Can only mark ordered/approved requests as received (current: {req.status})",
        )

    req.status = PurchaseRequestStatus.RECEIVED

    # Send "your request is ready" notification
    if not req.received_notified:
        req.received_notified = True
        await db.commit()
        await db.refresh(req, ["patron"])
        try:
            await send_request_notification(db, req, "received")
        except Exception:
            logger.exception("Failed to send received notification")
    else:
        await db.commit()

    await db.refresh(req, ["patron", "reviewed_by", "duplicate_of_catalog"])
    resp = PurchaseRequestStaffResponse.model_validate(req)
    resp.patron_name = req.patron.full_name if req.patron else None
    resp.reviewer_name = req.reviewed_by.full_name if req.reviewed_by else None
    return resp


@router.get("/stats", response_model=FulfillmentStatsResponse)
async def staff_fulfillment_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get purchase request fulfillment statistics."""
    check_staff_access(current_user)
    return await get_fulfillment_stats(db)


# ============ Decline Reason Templates ============


@router.get("/decline-templates", response_model=list[DeclineReasonTemplateResponse])
async def list_decline_templates(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all active decline reason templates."""
    check_staff_access(current_user)
    result = await db.execute(
        select(DeclineReasonTemplate)
        .where(DeclineReasonTemplate.is_active == True)
        .order_by(DeclineReasonTemplate.usage_count.desc())
    )
    return result.scalars().all()


@router.post("/decline-templates", response_model=DeclineReasonTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_decline_template(
    body: DeclineReasonTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new decline reason template."""
    check_staff_access(current_user)

    # Check for duplicate label
    existing = await db.execute(
        select(DeclineReasonTemplate).where(DeclineReasonTemplate.label == body.label)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A template with label '{body.label}' already exists",
        )

    template = DeclineReasonTemplate(
        label=body.label,
        message=body.message,
        created_by_id=current_user.id,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)
    return template


@router.put("/decline-templates/{template_id}", response_model=DeclineReasonTemplateResponse)
async def update_decline_template(
    template_id: int,
    body: DeclineReasonTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a decline reason template."""
    check_staff_access(current_user)
    template = await get_or_404(db, DeclineReasonTemplate, template_id, "Template not found")

    if body.label is not None:
        template.label = body.label
    if body.message is not None:
        template.message = body.message
    if body.is_active is not None:
        template.is_active = body.is_active

    await db.commit()
    await db.refresh(template)
    return template


@router.delete("/decline-templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_decline_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a decline reason template."""
    check_staff_access(current_user)
    template = await get_or_404(db, DeclineReasonTemplate, template_id, "Template not found")
    await db.delete(template)
    await db.commit()
    return None


@router.post("/queue/{request_id}/add-to-selection")
async def add_to_selection_list(
    request_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Convert an approved purchase request into a selection list item."""
    check_staff_access(current_user)

    result = await db.execute(
        select(PatronPurchaseRequest).where(PatronPurchaseRequest.id == request_id)
    )
    request_obj = result.scalars().first()
    if not request_obj:
        raise HTTPException(status_code=404, detail="Purchase request not found")

    if request_obj.status != PurchaseRequestStatus.APPROVED:
        raise HTTPException(status_code=400, detail="Only approved requests can be added to selection list")

    # Check for duplicates
    existing = await db.execute(
        select(SelectionListItem).where(SelectionListItem.purchase_request_id == request_id)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail="This request is already on the selection list")

    selection_item = SelectionListItem(
        title=request_obj.title,
        author=request_obj.author,
        isbn=request_obj.isbn,
        source="manual",
        priority="medium",
        requested_by_id=current_user.id,
        notes=f"From patron purchase request #{request_obj.id}",
        purchase_request_id=request_obj.id,
        status="pending",
    )
    db.add(selection_item)
    await db.commit()
    await db.refresh(selection_item)

    return {"id": selection_item.id, "message": "Added to selection list"}
