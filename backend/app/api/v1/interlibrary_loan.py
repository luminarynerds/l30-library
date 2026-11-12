# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Interlibrary Loan (ILL) API endpoints.

Provides:
- Patron: request items from other libraries, track status, view updates
- Staff: manage partner libraries, process requests, cost tracking, reporting
- Dashboard: reciprocal lending statistics, fill rates
"""

from app.core.logging import get_logger
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.interlibrary_loan import (
    ILLCostCategory,
    ILLRequestStatus,
    ILLRequestType,
    PartnerLibraryStatus,
)
from ...models.user import User, UserRole
from ...schemas.interlibrary_loan import (
    DueDateReminderConfig,
    ILLCostRecordCreate,
    ILLCostRecordResponse,
    ILLCostSummary,
    ILLFillRateReport,
    ILLRequestCreate,
    ILLRequestPatronView,
    ILLRequestResponse,
    ILLRequestStaffCreate,
    ILLRequestUpdate,
    ILLTrackingUpdateCreate,
    ILLTrackingUpdateResponse,
    PartnerLibraryCreate,
    PartnerLibraryResponse,
    PartnerLibraryUpdate,
    PartnerSearchResult,
    ReciprocallLendingDashboard,
    ReciprocallLendingStats,
)
from ...services.interlibrary_loan_service import (
    InterlibraryLoanService,
    STATUS_LABELS,
)
from .auth import get_current_user
from .dependencies import require_staff
from fastapi import Depends

logger = get_logger(__name__)

router = APIRouter(prefix="/ill", tags=["interlibrary-loan"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_service(db: AsyncSession = Depends(get_db)) -> InterlibraryLoanService:
    return InterlibraryLoanService(db)


def _require_staff_or_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (
        UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR
    ):
        raise HTTPException(status_code=403, detail="Staff access required")
    return current_user


# ===========================================================================
# PATRON ENDPOINTS
# ===========================================================================

@router.post("/requests", response_model=ILLRequestResponse, status_code=201)
async def create_ill_request(
    data: ILLRequestCreate,
    current_user: User = Depends(get_current_user),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    """Patron submits a new ILL request — 'We don't have it, want us to get it?'"""
    ill_request = await service.create_request(
        patron_id=current_user.id,
        request_type=ILLRequestType.borrow,
        title=data.title,
        author=data.author,
        isbn=data.isbn,
        issn=data.issn,
        publication_year=data.publication_year,
        edition=data.edition,
        volume=data.volume,
        material_type=data.material_type,
        patron_notes=data.patron_notes,
        needed_by=data.needed_by,
        pickup_branch_id=data.pickup_branch_id,
    )
    await db.commit()
    refreshed = await service.get_request(ill_request.id)
    return _to_response(refreshed)


@router.get("/requests/my", response_model=list[ILLRequestPatronView])
async def get_my_ill_requests(
    active_only: bool = Query(False),
    current_user: User = Depends(get_current_user),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Patron views their ILL requests with tracking updates."""
    requests = await service.list_requests(
        patron_id=current_user.id, active_only=active_only
    )
    result = []
    for req in requests:
        tracking = await service.get_patron_tracking(req.id)
        result.append(_to_patron_view(req, tracking))
    return result


@router.get("/requests/{request_id}/tracking", response_model=list[ILLTrackingUpdateResponse])
async def get_request_tracking(
    request_id: int,
    current_user: User = Depends(get_current_user),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Get patron-visible tracking updates for a request."""
    ill_request = await service.get_request(request_id)
    if not ill_request:
        raise HTTPException(status_code=404, detail="ILL request not found")
    # Patrons can only see their own requests
    if ill_request.patron_id != current_user.id and current_user.role == UserRole.PATRON:
        raise HTTPException(status_code=403, detail="Access denied")
    return await service.get_patron_tracking(request_id)


@router.post("/requests/{request_id}/cancel", response_model=ILLRequestResponse)
async def cancel_ill_request(
    request_id: int,
    current_user: User = Depends(get_current_user),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
):
    """Patron cancels their ILL request."""
    ill_request = await service.get_request(request_id)
    if not ill_request:
        raise HTTPException(status_code=404, detail="ILL request not found")
    if ill_request.patron_id != current_user.id and current_user.role == UserRole.PATRON:
        raise HTTPException(status_code=403, detail="Access denied")

    result = await service.cancel_request(request_id, current_user.id)
    if not result:
        raise HTTPException(status_code=400, detail="Request cannot be cancelled in its current state")
    await db.commit()
    refreshed = await service.get_request(result.id)
    return _to_response(refreshed)


# ===========================================================================
# PARTNER SEARCH (available to patrons and staff)
# ===========================================================================

@router.get("/search-partners", response_model=list[PartnerSearchResult])
async def search_partner_catalogs(
    title: str = Query(..., min_length=1),
    author: str | None = Query(None),
    isbn: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Search partner library catalogs for a title. Auto-search for availability."""
    results = await service.search_partner_catalogs(title=title, author=author, isbn=isbn)
    return [PartnerSearchResult(**r) for r in results]


# ===========================================================================
# STAFF ENDPOINTS
# ===========================================================================

@router.post("/staff/requests", response_model=ILLRequestResponse, status_code=201)
async def staff_create_ill_request(
    data: ILLRequestStaffCreate,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Staff creates an ILL request on behalf of patron."""
    ill_request = await service.create_request(
        patron_id=data.patron_id,
        staff_id=current_user.id,
        request_type=data.request_type,
        partner_library_id=data.partner_library_id,
        catalog_item_id=data.catalog_item_id,
        title=data.title,
        author=data.author,
        isbn=data.isbn,
        issn=data.issn,
        publication_year=data.publication_year,
        edition=data.edition,
        volume=data.volume,
        material_type=data.material_type,
        notes=data.notes,
        patron_notes=data.patron_notes,
        needed_by=data.needed_by,
        pickup_branch_id=data.pickup_branch_id,
        shipping_method=data.shipping_method,
        estimated_cost=data.estimated_cost,
    )
    await db.commit()
    refreshed = await service.get_request(ill_request.id)
    return _to_response(refreshed)


@router.get("/staff/requests", response_model=list[ILLRequestResponse])
async def staff_list_ill_requests(
    patron_id: int | None = Query(None),
    partner_library_id: int | None = Query(None),
    request_type: ILLRequestType | None = Query(None),
    status_filter: ILLRequestStatus | None = Query(None, alias="status"),
    active_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Staff lists all ILL requests with filters."""
    requests = await service.list_requests(
        patron_id=patron_id,
        partner_library_id=partner_library_id,
        request_type=request_type,
        status=status_filter,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )
    return [_to_response(r) for r in requests]


@router.get("/staff/requests/{request_id}", response_model=ILLRequestResponse)
async def staff_get_ill_request(
    request_id: int,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Staff views a single ILL request with full details."""
    ill_request = await service.get_request(request_id)
    if not ill_request:
        raise HTTPException(status_code=404, detail="ILL request not found")
    return _to_response(ill_request)


@router.patch("/staff/requests/{request_id}", response_model=ILLRequestResponse)
async def staff_update_ill_request(
    request_id: int,
    data: ILLRequestUpdate,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Staff updates an ILL request (status, tracking, costs)."""
    updates = data.model_dump(exclude_unset=True)
    result = await service.update_request(request_id, current_user.id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="ILL request not found")
    await db.commit()
    refreshed = await service.get_request(result.id)
    return _to_response(refreshed)


@router.post("/staff/requests/{request_id}/auto-search", response_model=ILLRequestResponse)
async def staff_auto_search_and_submit(
    request_id: int,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Auto-search partner libraries and submit to best match."""
    result = await service.auto_search_and_submit(request_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="ILL request not found")
    await db.commit()
    refreshed = await service.get_request(result.id)
    return _to_response(refreshed)


@router.post("/staff/requests/{request_id}/renew", response_model=ILLRequestResponse)
async def staff_renew_ill_request(
    request_id: int,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Renew an ILL checkout (extend due date)."""
    result = await service.renew_request(request_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=400,
            detail="Cannot renew: request not checked out or max renewals reached",
        )
    await db.commit()
    refreshed = await service.get_request(result.id)
    return _to_response(refreshed)


@router.post(
    "/staff/requests/{request_id}/tracking",
    response_model=ILLTrackingUpdateResponse,
    status_code=201,
)
async def staff_add_tracking_update(
    request_id: int,
    data: ILLTrackingUpdateCreate,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Staff adds a tracking update visible to patron."""
    ill_request = await service.get_request(request_id)
    if not ill_request:
        raise HTTPException(status_code=404, detail="ILL request not found")

    tracking = await service.add_tracking_update(
        request_id=request_id,
        status=ill_request.status,
        message=data.message,
        created_by_id=current_user.id,
        is_patron_visible=data.is_patron_visible,
    )
    await db.commit()
    return tracking


# ===========================================================================
# RETURN SHIPPING LABEL
# ===========================================================================

@router.get("/staff/requests/{request_id}/shipping-label")
async def get_return_shipping_label(
    request_id: int,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Generate return shipping label data for an ILL item."""
    label = await service.generate_return_shipping_label(request_id)
    if not label:
        raise HTTPException(status_code=404, detail="Request or partner library not found")
    return label


# ===========================================================================
# COST TRACKING
# ===========================================================================

@router.post(
    "/staff/requests/{request_id}/costs",
    response_model=ILLCostRecordResponse,
    status_code=201,
)
async def add_cost_record(
    request_id: int,
    data: ILLCostRecordCreate,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Add a cost record to an ILL request."""
    cost = await service.add_cost_record(
        request_id=request_id,
        category=data.category,
        amount=data.amount,
        description=data.description,
        created_by_id=current_user.id,
    )
    await db.commit()
    return cost


@router.get("/staff/requests/{request_id}/costs", response_model=list[ILLCostRecordResponse])
async def get_cost_records(
    request_id: int,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Get cost records for an ILL request."""
    return await service.get_cost_records(request_id)


# ===========================================================================
# DUE DATE REMINDERS
# ===========================================================================

@router.get("/staff/due-reminders")
async def get_due_date_reminders(
    days_ahead: int = Query(7, ge=1, le=30),
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Get ILL items with approaching due dates for reminder processing."""
    upcoming = await service.get_upcoming_due_requests(days_ahead)
    overdue = await service.get_overdue_requests()
    return {
        "upcoming": [_to_response(r) for r in upcoming],
        "overdue": [_to_response(r) for r in overdue],
        "upcoming_count": len(upcoming),
        "overdue_count": len(overdue),
    }


# ===========================================================================
# REPORTING
# ===========================================================================

@router.get("/staff/reports/fill-rate", response_model=ILLFillRateReport)
async def get_fill_rate_report(
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Get fill rate report for ILL requests."""
    if not period_start:
        period_start = date.today() - timedelta(days=365)
    if not period_end:
        period_end = date.today()
    return await service.get_fill_rate_report(period_start, period_end)


@router.get("/staff/reports/costs", response_model=ILLCostSummary)
async def get_cost_summary_report(
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Get cost tracking summary for ILL operations."""
    if not period_start:
        period_start = date.today() - timedelta(days=365)
    if not period_end:
        period_end = date.today()
    return await service.get_cost_summary(period_start, period_end)


@router.get("/staff/reports/reciprocal-dashboard", response_model=ReciprocallLendingDashboard)
async def get_reciprocal_lending_dashboard(
    period_start: date = Query(default=None),
    period_end: date = Query(default=None),
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Get reciprocal lending dashboard with per-partner statistics."""
    if not period_start:
        period_start = date.today() - timedelta(days=365)
    if not period_end:
        period_end = date.today()
    return await service.get_reciprocal_lending_dashboard(period_start, period_end)


# ===========================================================================
# PARTNER LIBRARY MANAGEMENT (Staff)
# ===========================================================================

@router.post("/staff/partners", response_model=PartnerLibraryResponse, status_code=201)
async def create_partner_library(
    data: PartnerLibraryCreate,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Add a new partner library."""
    partner = await service.create_partner_library(**data.model_dump())
    await db.commit()
    return partner


@router.get("/staff/partners", response_model=list[PartnerLibraryResponse])
async def list_partner_libraries(
    status_filter: PartnerLibraryStatus | None = Query(None, alias="status"),
    search: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """List partner libraries with optional filters."""
    return await service.list_partner_libraries(
        status=status_filter, search=search, skip=skip, limit=limit
    )


@router.get("/staff/partners/{partner_id}", response_model=PartnerLibraryResponse)
async def get_partner_library(
    partner_id: int,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
):
    """Get a partner library by ID."""
    partner = await service.get_partner_library(partner_id)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner library not found")
    return partner


@router.patch("/staff/partners/{partner_id}", response_model=PartnerLibraryResponse)
async def update_partner_library(
    partner_id: int,
    data: PartnerLibraryUpdate,
    current_user: User = Depends(_require_staff_or_admin),
    service: InterlibraryLoanService = Depends(_get_service),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Update a partner library."""
    updates = data.model_dump(exclude_unset=True)
    partner = await service.update_partner_library(partner_id, updates)
    if not partner:
        raise HTTPException(status_code=404, detail="Partner library not found")
    await db.commit()
    return partner


# ===========================================================================
# Response Builders
# ===========================================================================

def _to_response(ill_request) -> dict:
    partner_name = None
    if ill_request.partner_library:
        partner_name = ill_request.partner_library.name
    return {
        "id": ill_request.id,
        "patron_id": ill_request.patron_id,
        "staff_id": ill_request.staff_id,
        "request_type": ill_request.request_type,
        "partner_library_id": ill_request.partner_library_id,
        "partner_library_name": partner_name,
        "catalog_item_id": ill_request.catalog_item_id,
        "title": ill_request.title,
        "author": ill_request.author,
        "isbn": ill_request.isbn,
        "issn": ill_request.issn,
        "publication_year": ill_request.publication_year,
        "edition": ill_request.edition,
        "volume": ill_request.volume,
        "material_type": ill_request.material_type,
        "notes": ill_request.notes,
        "patron_notes": ill_request.patron_notes,
        "status": ill_request.status,
        "pickup_branch_id": ill_request.pickup_branch_id,
        "needed_by": ill_request.needed_by,
        "due_date": ill_request.due_date,
        "shipped_at": ill_request.shipped_at,
        "received_at": ill_request.received_at,
        "checked_out_at": ill_request.checked_out_at,
        "returned_at": ill_request.returned_at,
        "completed_at": ill_request.completed_at,
        "shipping_method": ill_request.shipping_method,
        "outbound_tracking": ill_request.outbound_tracking,
        "return_tracking": ill_request.return_tracking,
        "estimated_cost": ill_request.estimated_cost,
        "actual_cost": ill_request.actual_cost,
        "renewal_count": ill_request.renewal_count,
        "max_renewals": ill_request.max_renewals,
        "created_at": ill_request.created_at,
        "updated_at": ill_request.updated_at,
    }


def _to_patron_view(ill_request, tracking_updates) -> dict:
    return {
        "id": ill_request.id,
        "title": ill_request.title,
        "author": ill_request.author,
        "status": ill_request.status,
        "status_label": STATUS_LABELS.get(ill_request.status, str(ill_request.status)),
        "due_date": ill_request.due_date,
        "needed_by": ill_request.needed_by,
        "pickup_branch_id": ill_request.pickup_branch_id,
        "renewal_count": ill_request.renewal_count,
        "max_renewals": ill_request.max_renewals,
        "tracking_updates": tracking_updates,
        "created_at": ill_request.created_at,
    }
