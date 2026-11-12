# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Checkout, checkin, return, history, and fines endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.authorization import check_fine_block
from ....core.cache import invalidate_catalog_cache
from ....core.database import get_db
from ....core.pagination import PaginationParams, calculate_total_pages
from ....core.service_error_handler import handle_service_errors
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout, CheckoutStatus
from ....models.ebook_checkout_log import EbookCheckoutLog
from ....models.fine import Fine, FineStatus
from ....models.user import User, UserRole
from ....schemas.circulation import CheckoutCreate, CheckoutResponse
from ....schemas.common import PaginatedResponse, PaginationInfo
from ....schemas.fine import FineResponse, FineSummary, PatronFineResponse
from ....services.checkout_service import create_checkout, return_checkout, renew_checkout, send_pending_hold_notification
from ....services.fine_service import check_and_create_overdue_fine, get_user_fines_summary
from ..auth import get_current_user
from ..lifecycle import create_lifecycle_event
from app.core.logging import get_logger

router = APIRouter()


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def checkout_item(
    checkout_in: CheckoutCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Checkout an item from the library."""
    # Check fine balance
    can_proceed, balance = await check_fine_block(current_user, db)
    if not can_proceed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Your account has ${balance:.2f} in unpaid fines, which needs to be resolved before checking out. Please visit the front desk or pay online.",
        )

    # Delegate to service layer
    checkout_result = await create_checkout(current_user, checkout_in.item_id, db)
    checkout = checkout_result.checkout

    # Get item for response
    result = await db.execute(select(CatalogItem).where(CatalogItem.id == checkout.item_id))
    item = result.scalar_one_or_none()

    await db.commit()

    # Release the distributed lock AFTER commit so no concurrent checkout
    # can sneak in before the data is durable.
    await checkout_result.release_lock()

    await db.refresh(checkout)

    # Invalidate catalog cache since item status changed
    await invalidate_catalog_cache()

    return CheckoutResponse(
        id=checkout.id,
        user_id=checkout.user_id,
        item_id=checkout.item_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        item_title=item.title if item else None,
        item_author=item.author if item else None,
    )


@router.post("/checkin", response_model=CheckoutResponse)
async def checkin_item(
    checkout_id: int = Query(..., description="ID of the checkout to return"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a checked out item using checkout ID.

    This is an alternative endpoint to POST /return/{checkout_id} for checkins.
    Staff roles (ADMIN, DIRECTOR, STAFF, SUPER_ADMIN) can checkin any checkout.
    Patrons can only checkin their own checkouts.
    """
    # Build query - staff can checkin any item, patrons only their own
    staff_roles = {UserRole.ADMIN, UserRole.DIRECTOR, UserRole.STAFF, UserRole.SUPER_ADMIN}
    query = select(Checkout).where(Checkout.id == checkout_id).with_for_update()

    if current_user.role not in staff_roles:
        query = query.where(Checkout.user_id == current_user.id)

    result = await db.execute(query)
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="We couldn't find that checkout. It may have already been returned.")

    is_staff = current_user.role in staff_roles

    if is_staff:
        allowed_statuses = [
            CheckoutStatus.active, CheckoutStatus.overdue,
            CheckoutStatus.lost, CheckoutStatus.lost_by_patron,
            CheckoutStatus.claims_returned, CheckoutStatus.damaged,
        ]
    else:
        allowed_statuses = [CheckoutStatus.active, CheckoutStatus.overdue]

    previous_status = checkout.status

    if checkout.status not in allowed_statuses:
        raise HTTPException(status_code=400, detail="This item has already been returned or is no longer checked out.")

    # For staff-driven checkin, the loan owner is whoever the checkout was
    # issued to -- not current_user. Pass the loan owner as `user` (so audit,
    # reading-shelf, suspension lift, and lifecycle events attribute to the
    # patron) and current_user as `staff` (audit staff_id). For patron self-
    # checkin, current_user IS the loan owner; staff is None.
    if is_staff:
        loan_owner = await db.get(User, checkout.user_id)
        if loan_owner is None:
            raise HTTPException(status_code=404, detail="We couldn't find the patron this checkout belongs to.")
        staff_actor: Optional[User] = current_user
    else:
        loan_owner = current_user
        staff_actor = None

    # Delegate to service layer
    result = await return_checkout(
        checkout, db, loan_owner, create_lifecycle_event, staff=staff_actor,
    )

    await db.commit()
    await db.refresh(checkout)

    # Send hold-ready notification AFTER commit so we never notify for
    # a hold promotion that gets rolled back.
    await send_pending_hold_notification(result.pending_notification)

    if is_staff and previous_status in [
        CheckoutStatus.lost, CheckoutStatus.lost_by_patron,
        CheckoutStatus.claims_returned, CheckoutStatus.damaged,
    ]:
        import logging
        get_logger(__name__).info(
            "Previously %s item (checkout %d) returned via staff checkin",
            previous_status.value, checkout.id,
        )

    # Invalidate catalog cache
    await invalidate_catalog_cache()

    item = result.item
    return CheckoutResponse(
        id=checkout.id,
        user_id=checkout.user_id,
        item_id=checkout.item_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        item_title=item.title if item else None,
        item_author=item.author if item else None,
    )


@router.post("/return/{checkout_id}", response_model=CheckoutResponse)
async def return_item(
    checkout_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return a checked out item."""
    # Use FOR UPDATE to lock checkout
    result = await db.execute(
        select(Checkout)
        .where(Checkout.id == checkout_id, Checkout.user_id == current_user.id)
        .with_for_update()
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(status_code=404, detail="We couldn't find that checkout. It may have already been returned.")

    if checkout.status not in [CheckoutStatus.active, CheckoutStatus.overdue]:
        raise HTTPException(status_code=400, detail="This item has already been returned or is no longer checked out.")

    # Delegate to service layer
    ret = await return_checkout(checkout, db, current_user, create_lifecycle_event)

    await db.commit()
    await db.refresh(checkout)

    # Send hold-ready notification AFTER commit so we never notify for
    # a hold promotion that gets rolled back.
    await send_pending_hold_notification(ret.pending_notification)

    # Invalidate catalog cache since item status changed
    await invalidate_catalog_cache()

    item = ret.item
    return CheckoutResponse(
        id=checkout.id,
        user_id=checkout.user_id,
        item_id=checkout.item_id,
        status=checkout.status,
        checked_out_at=checkout.checked_out_at,
        due_date=checkout.due_date,
        returned_at=checkout.returned_at,
        renewal_count=checkout.renewal_count,
        item_title=item.title if item else None,
        item_author=item.author if item else None,
    )


@router.get("/checkouts/active", response_model=PaginatedResponse[CheckoutResponse])
@handle_service_errors("Failed to retrieve active checkouts")
async def get_active_checkouts(
    pagination: PaginationParams = Depends(),
    status: str | None = Query(None, description="Filter by status (active, overdue, returned)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's active checkouts with pagination.

    This endpoint returns only active and overdue items by default.
    Pass ?status= to filter by a specific status.
    """
    if status is not None:
        try:
            parsed_status = CheckoutStatus(status)
        except ValueError:
            valid = [s.value for s in CheckoutStatus]
            raise HTTPException(
                status_code=400,
                detail=f"'{status}' is not a recognized status. Try one of: {valid}",
            ) from None
        status_filter = Checkout.status == parsed_status
    else:
        status_filter = Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue])

    base_filters = [
        Checkout.user_id == current_user.id,
        status_filter,
    ]

    # Count query
    count_result = await db.execute(
        select(func.count(Checkout.id)).where(*base_filters)
    )
    total = count_result.scalar() or 0

    # Data query
    result = await db.execute(
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(*base_filters)
        .order_by(Checkout.due_date)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.all()

    for checkout, _ in rows:
        await check_and_create_overdue_fine(checkout, db, user=current_user)

    await db.commit()

    items = [
        CheckoutResponse(
            id=checkout.id,
            user_id=checkout.user_id,
            item_id=checkout.item_id,
            status=checkout.status,
            checked_out_at=checkout.checked_out_at,
            due_date=checkout.due_date,
            returned_at=checkout.returned_at,
            renewal_count=checkout.renewal_count,
            item_title=item.title,
            item_author=item.author,
        )
        for checkout, item in rows
    ]

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.get("/checkouts", response_model=PaginatedResponse[CheckoutResponse])
@handle_service_errors("Failed to retrieve checkouts")
async def get_user_checkouts(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current user's active checkouts with pagination."""
    base_filters = [
        Checkout.user_id == current_user.id,
        Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
    ]

    # Count query
    count_result = await db.execute(
        select(func.count(Checkout.id)).where(*base_filters)
    )
    total = count_result.scalar() or 0

    # Data query
    result = await db.execute(
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(*base_filters)
        .order_by(Checkout.due_date)
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    rows = result.all()

    for checkout, _ in rows:
        await check_and_create_overdue_fine(checkout, db, user=current_user)

    await db.commit()

    items = [
        CheckoutResponse(
            id=checkout.id,
            user_id=checkout.user_id,
            item_id=checkout.item_id,
            status=checkout.status,
            checked_out_at=checkout.checked_out_at,
            due_date=checkout.due_date,
            returned_at=checkout.returned_at,
            renewal_count=checkout.renewal_count,
            item_title=item.title,
            item_author=item.author,
        )
        for checkout, item in rows
    ]

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.get("/history", response_model=PaginatedResponse[CheckoutResponse])
async def get_checkout_history(
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's checkout history (all past checkouts). Returns empty result if user has disabled history tracking."""
    # If user has disabled history tracking, return empty paginated response
    if not current_user.track_reading_history:
        return PaginatedResponse(
            data=[],
            pagination=PaginationInfo(
                page=pagination.page,
                per_page=pagination.page_size,
                total=0,
                total_pages=0,
                has_next=False,
                has_previous=False,
            ),
        )

    # Count physical checkouts at DB level
    phys_count_result = await db.execute(
        select(func.count(Checkout.id)).where(Checkout.user_id == current_user.id)
    )
    phys_total = phys_count_result.scalar() or 0

    # Count ebook borrow events at DB level (each borrow = one history entry)
    ebook_count_result = await db.execute(
        select(func.count(EbookCheckoutLog.id)).where(
            EbookCheckoutLog.user_id == current_user.id,
            EbookCheckoutLog.action == "borrow",
        )
    )
    ebook_total = ebook_count_result.scalar() or 0
    total = phys_total + ebook_total

    # Paginate physical checkouts at DB level.
    # Ordering note: physical checkouts are sorted newest-first; ebook events
    # are appended after. The two sources are not interleaved by date in this
    # interim implementation (true cross-source merge sort requires a UNION
    # or application-level re-sort across both result sets).
    phys_result = await db.execute(
        select(Checkout, CatalogItem)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Checkout.user_id == current_user.id)
        .order_by(Checkout.checked_out_at.desc())
        .offset(pagination.offset)
        .limit(pagination.limit)
    )
    phys_rows = phys_result.all()

    paginated_items: list[CheckoutResponse] = [
        CheckoutResponse(
            id=checkout.id,
            user_id=checkout.user_id,
            item_id=checkout.item_id,
            status=checkout.status,
            checked_out_at=checkout.checked_out_at,
            due_date=checkout.due_date,
            returned_at=checkout.returned_at,
            renewal_count=checkout.renewal_count,
            item_title=item.title if item else None,
            item_author=item.author if item else None,
        )
        for checkout, item in phys_rows
    ]

    # Ebook borrow events: fetch the page slice, then look up matching returns.
    # Only append ebook items if this page has room after physical checkouts.
    ebook_page_start = max(0, pagination.offset - phys_total)
    ebook_page_limit = pagination.limit - len(paginated_items)
    if ebook_page_limit > 0 and ebook_page_start >= 0:
        borrow_result = await db.execute(
            select(EbookCheckoutLog)
            .where(
                EbookCheckoutLog.user_id == current_user.id,
                EbookCheckoutLog.action == "borrow",
            )
            .order_by(EbookCheckoutLog.recorded_at.desc())
            .offset(ebook_page_start)
            .limit(ebook_page_limit)
        )
        borrow_events = borrow_result.scalars().all()

        for borrow in borrow_events:
            # Find the matching return event (first return after this borrow)
            ret_result = await db.execute(
                select(EbookCheckoutLog)
                .where(
                    EbookCheckoutLog.user_id == current_user.id,
                    EbookCheckoutLog.action == "return",
                    EbookCheckoutLog.recorded_at > borrow.recorded_at,
                )
                .order_by(EbookCheckoutLog.recorded_at)
                .limit(1)
            )
            matched_return = ret_result.scalar_one_or_none()
            title = borrow.ebook_title or (matched_return.ebook_title if matched_return else None)
            paginated_items.append(
                CheckoutResponse(
                    id=-borrow.id,
                    user_id=current_user.id,
                    item_id=0,
                    status=CheckoutStatus.returned if matched_return else CheckoutStatus.active,
                    checked_out_at=borrow.recorded_at,
                    due_date=borrow.recorded_at,
                    returned_at=matched_return.recorded_at if matched_return else None,
                    renewal_count=0,
                    item_title="[eBook] " + title if title else "[eBook]",
                    item_author=borrow.ebook_author or None,
                )
            )

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=paginated_items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.get("/fines", response_model=PaginatedResponse[PatronFineResponse])
@handle_service_errors("Failed to retrieve fines")
async def get_user_fines(
    include_paid: bool = True,
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's fines (unpaid and optionally paid) with pagination."""
    # First check active checkouts for overdue fines
    active_checkouts = await db.execute(
        select(Checkout).where(
            Checkout.user_id == current_user.id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )
    for checkout in active_checkouts.scalars().all():
        await check_and_create_overdue_fine(checkout, db, user=current_user)

    await db.commit()

    # Build count query
    count_query = select(func.count(Fine.id)).where(Fine.user_id == current_user.id)
    if not include_paid:
        count_query = count_query.where(Fine.status == FineStatus.unpaid)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Build data query
    query = (
        select(Fine, Checkout, CatalogItem)
        .outerjoin(Checkout, Fine.checkout_id == Checkout.id)
        .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(Fine.user_id == current_user.id)
    )

    if not include_paid:
        query = query.where(Fine.status == FineStatus.unpaid)

    query = query.order_by(Fine.created_at.desc()).offset(pagination.offset).limit(pagination.limit)

    result = await db.execute(query)
    rows = result.all()

    items = [
        PatronFineResponse(
            id=fine.id,
            fine_type=fine.fine_type,
            status=fine.status,
            amount=fine.amount,
            amount_paid=fine.amount_paid,
            balance=fine.balance,
            description=fine.description,
            created_at=fine.created_at,
            paid_at=fine.paid_at,
            waived=fine.waived_at is not None,
            waived_at=fine.waived_at,
            item_title=item.title if item else None,
            item_author=item.author if item else None,
        )
        for fine, checkout, item in rows
    ]

    total_pages = calculate_total_pages(total, pagination.page_size)
    return PaginatedResponse(
        data=items,
        pagination=PaginationInfo(
            page=pagination.page,
            per_page=pagination.page_size,
            total=total,
            total_pages=total_pages,
            has_next=pagination.page < total_pages,
            has_previous=pagination.page > 1,
        ),
    )


@router.get("/fines/summary", response_model=FineSummary)
async def get_fines_summary(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get summary of user's fines."""
    # Delegate to service layer
    summary_data = await get_user_fines_summary(current_user.id, db)

    return FineSummary(
        total_outstanding=summary_data["total_outstanding"],
        total_paid=summary_data["total_paid"],
        outstanding_count=summary_data["outstanding_count"],
        paid_count=summary_data["paid_count"],
    )
