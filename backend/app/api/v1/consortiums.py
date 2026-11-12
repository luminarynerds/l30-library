# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API routes for consortium management.

Provides endpoints for:
- Consortium management
- Member management
- Reciprocal borrowing
- Patron linking (cross-authentication)
- Billing and cost sharing
- White-labeling
- Invoice export and automation
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.authorization import require_role
from .dependencies import require_admin, require_authenticated, require_staff
from ...models.user import User, UserRole
from ...models.multi_branch import (
    BillingStatus,
    ConsortiumMemberStatus,
    ConsortiumMemberType,
)
from ...schemas.multi_branch import (
    # Consortium
    ConsortiumCreate,
    ConsortiumUpdate,
    ConsortiumResponse,
    ConsortiumDetailResponse,
    ConsortiumSettingsUpdate,
    ConsortiumSettingsResponse,
    # Member
    ConsortiumMemberCreate,
    ConsortiumMemberUpdate,
    ConsortiumMemberResponse,
    ConsortiumMemberDetailResponse,
    # Reciprocal
    ReciprocalBorrowingSettingsUpdate,
    ReciprocalBorrowingSettingsResponse,
    # Billing
    ConsortiumBillingResponse,
    MemberBalanceResponse,
    # White Label
    ConsortiumWhiteLabelUpdate,
    ConsortiumWhiteLabelResponse,
    # Patron Link
    ConsortiumPatronLinkCreate,
    ConsortiumPatronLinkResponse,
)
from ...services.consortium_service import ConsortiumService
from ...services.consortium_billing_service import ConsortiumBillingService
from ...services.consortium_invoice_export_service import ConsortiumInvoiceExportService


router = APIRouter(prefix="/consortiums", tags=["consortiums"])


# =============================================================================
# DEPENDENCIES
# =============================================================================

async def get_consortium_service(db: AsyncSession = Depends(get_db)) -> ConsortiumService:
    return ConsortiumService(db)


async def get_billing_service(db: AsyncSession = Depends(get_db)) -> ConsortiumBillingService:
    return ConsortiumBillingService(db)


async def get_invoice_export_service(db: AsyncSession = Depends(get_db)) -> ConsortiumInvoiceExportService:
    return ConsortiumInvoiceExportService(db)


# =============================================================================
# CONSORTIUM ENDPOINTS
# =============================================================================

@router.post("", response_model=ConsortiumResponse, status_code=status.HTTP_201_CREATED)
async def create_consortium(
    data: ConsortiumCreate,
    current_user: User = Depends(require_role(UserRole.SUPER_ADMIN)),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Create a new consortium. Requires SUPER_ADMIN role."""
    # Check if code already exists
    existing = await service.get_consortium_by_code(data.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Consortium with code '{data.code}' already exists"
        )

    return await service.create_consortium(**data.model_dump())


@router.get("", response_model=list[ConsortiumResponse])
async def list_consortiums(
    active_only: bool = Query(True, description="Only return active consortiums"),
    current_user: User = Depends(require_authenticated),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """List all consortiums."""
    return await service.list_consortiums(active_only=active_only)


@router.get("/{consortium_id}", response_model=ConsortiumDetailResponse)
async def get_consortium(
    consortium_id: int,
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get a consortium by ID with members and settings."""
    consortium = await service.get_consortium(consortium_id)
    if not consortium:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consortium not found"
        )
    return consortium


@router.patch("/{consortium_id}", response_model=ConsortiumResponse)
async def update_consortium(
    consortium_id: int,
    data: ConsortiumUpdate,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Update a consortium. Requires ADMIN role."""
    consortium = await service.update_consortium(
        consortium_id,
        **data.model_dump(exclude_unset=True)
    )
    if not consortium:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consortium not found"
        )
    return consortium


@router.get("/{consortium_id}/settings", response_model=ConsortiumSettingsResponse)
async def get_consortium_settings(
    consortium_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get consortium settings."""
    consortium = await service.get_consortium(consortium_id)
    if not consortium:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consortium not found"
        )
    return consortium.settings


@router.patch("/{consortium_id}/settings", response_model=ConsortiumSettingsResponse)
async def update_consortium_settings(
    consortium_id: int,
    data: ConsortiumSettingsUpdate,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Update consortium settings. Requires ADMIN role."""
    settings = await service.update_consortium_settings(
        consortium_id,
        **data.model_dump(exclude_unset=True)
    )
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consortium not found"
        )
    return settings


# =============================================================================
# MEMBER ENDPOINTS
# =============================================================================

@router.post("/{consortium_id}/members", response_model=ConsortiumMemberResponse, status_code=status.HTTP_201_CREATED)
async def add_member(
    consortium_id: int,
    data: ConsortiumMemberCreate,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Add a library system as a consortium member. Requires ADMIN role."""
    # Check if already a member
    existing = await service.get_member_by_system(consortium_id, data.library_system_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Library system is already a member of this consortium"
        )

    return await service.add_member(
        consortium_id=consortium_id,
        **data.model_dump(exclude={"consortium_id"})
    )


@router.get("/{consortium_id}/members", response_model=list[ConsortiumMemberResponse])
async def list_members(
    consortium_id: int,
    status: ConsortiumMemberStatus | None = Query(None),
    active_only: bool = Query(True),
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """List consortium members."""
    return await service.list_members(
        consortium_id,
        status=status,
        active_only=active_only,
    )


@router.get("/members/{member_id}", response_model=ConsortiumMemberDetailResponse)
async def get_member(
    member_id: int,
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get a consortium member by ID."""
    member = await service.get_member(member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member


@router.patch("/members/{member_id}", response_model=ConsortiumMemberResponse)
async def update_member(
    member_id: int,
    data: ConsortiumMemberUpdate,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Update a consortium member. Requires ADMIN role."""
    member = await service.update_member(
        member_id,
        **data.model_dump(exclude_unset=True)
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member


@router.post("/members/{member_id}/suspend", response_model=ConsortiumMemberResponse)
async def suspend_member(
    member_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Suspend a consortium member. Requires ADMIN role."""
    member = await service.update_member_status(
        member_id, ConsortiumMemberStatus.SUSPENDED
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member


@router.post("/members/{member_id}/activate", response_model=ConsortiumMemberResponse)
async def activate_member(
    member_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Activate a consortium member. Requires ADMIN role."""
    member = await service.update_member_status(
        member_id, ConsortiumMemberStatus.ACTIVE
    )
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member


# =============================================================================
# RECIPROCAL BORROWING ENDPOINTS
# =============================================================================

@router.get("/members/{member_id}/reciprocal-settings", response_model=ReciprocalBorrowingSettingsResponse)
async def get_reciprocal_settings(
    member_id: int,
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get reciprocal borrowing settings for a member."""
    member = await service.get_member(member_id)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return member.reciprocal_settings


@router.patch("/members/{member_id}/reciprocal-settings", response_model=ReciprocalBorrowingSettingsResponse)
async def update_reciprocal_settings(
    member_id: int,
    data: ReciprocalBorrowingSettingsUpdate,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Update reciprocal borrowing settings. Requires ADMIN role."""
    settings = await service.update_reciprocal_settings(
        member_id,
        **data.model_dump(exclude_unset=True)
    )
    if not settings:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )
    return settings


@router.get("/members/{member_id}/can-borrow")
async def check_can_borrow(
    member_id: int,
    patron_id: int,
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Check if a patron can borrow at a consortium member."""
    can_borrow, reason = await service.can_patron_borrow_at_member(
        patron_id, member_id
    )
    limits = await service.get_patron_checkout_limits_at_member(
        patron_id, member_id
    )

    return {
        "patron_id": patron_id,
        "member_id": member_id,
        "can_borrow": can_borrow,
        "reason": reason,
        "checkout_limit": limits["checkout_limit"] if can_borrow else 0,
        "hold_limit": limits["hold_limit"] if can_borrow else 0,
    }


# =============================================================================
# PATRON LINK ENDPOINTS (Cross-authentication)
# =============================================================================

@router.post("/patron-links", response_model=ConsortiumPatronLinkResponse, status_code=status.HTTP_201_CREATED)
async def create_patron_link(
    data: ConsortiumPatronLinkCreate,
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Create a patron link for reciprocal borrowing. Requires STAFF role."""
    # Check if already linked
    existing = await service.get_patron_link(data.home_user_id, data.linked_member_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patron is already linked to this member"
        )

    return await service.create_patron_link(**data.model_dump())


@router.get("/patron-links", response_model=list[ConsortiumPatronLinkResponse])
async def list_patron_links(
    patron_id: int,
    active_only: bool = Query(True),
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get all consortium links for a patron."""
    return await service.get_patron_links(patron_id, active_only=active_only)


@router.get("/patron-links/{link_id}", response_model=ConsortiumPatronLinkResponse)
async def get_patron_link(
    link_id: int,
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get a patron link by ID."""
    link = await service.get_patron_link_by_id(link_id)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patron link not found"
        )
    return link


@router.post("/patron-links/{user_id}/{member_id}/block")
async def block_patron_at_member(
    user_id: int,
    member_id: int,
    reason: str,
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Block a patron from borrowing at a consortium member. Requires STAFF role."""
    link = await service.block_patron_at_member(user_id, member_id, reason)
    if not link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patron link not found"
        )
    return {"status": "blocked", "reason": reason}


# =============================================================================
# BILLING ENDPOINTS
# =============================================================================

@router.post("/{consortium_id}/billing/generate")
async def generate_billing(
    consortium_id: int,
    period_start: date,
    period_end: date,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Generate billing for a period. Requires ADMIN role."""
    records = await service.generate_billing_for_period(
        consortium_id, period_start, period_end
    )
    return {
        "records_created": len(records),
        "period": {"start": period_start, "end": period_end},
    }


@router.get("/{consortium_id}/billing", response_model=list[ConsortiumBillingResponse])
async def list_billing_records(
    consortium_id: int,
    member_id: int | None = Query(None),
    status: BillingStatus | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """List billing records."""
    return await service.list_billing_records(
        consortium_id,
        member_id=member_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )


@router.get("/billing/{billing_id}", response_model=ConsortiumBillingResponse)
async def get_billing_record(
    billing_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Get a billing record by ID."""
    record = await service.get_billing_record(billing_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )
    return record


@router.get("/billing/create-invoice", response_model=dict)
async def get_create_invoice_info(
    current_user: User = Depends(require_admin),
):
    """Get information about creating invoices."""
    return {
        "description": "Create an invoice for billing records",
        "min_due_days": 7,
        "max_due_days": 90,
        "default_due_days": 30,
        "requires_billing_ids": True,
    }


@router.post("/billing/create-invoice")
async def create_invoice(
    billing_ids: list[int],
    due_days: int = Query(30, ge=7, le=90),
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Create an invoice for billing records. Requires ADMIN role."""
    records = await service.create_invoice(billing_ids, due_days)
    if not records:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing records found"
        )
    return {
        "invoice_number": records[0].invoice_number,
        "records_count": len(records),
        "due_date": records[0].due_date,
    }


@router.get("/billing/{billing_id}/pay", response_model=dict)
async def get_payment_info(
    billing_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Get information about recording payment for a billing record."""
    record = await service.get_billing_record(billing_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )
    return {
        "billing_id": record.id,
        "amount": record.amount,
        "status": record.status,
        "requires_payment_reference": False,
        "can_record_payment": record.status in ["pending", "overdue"],
    }


@router.post("/billing/{billing_id}/pay", response_model=ConsortiumBillingResponse)
async def record_payment(
    billing_id: int,
    payment_reference: str | None = Query(None),
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Record payment for a billing record. Requires ADMIN role."""
    record = await service.record_payment(billing_id, payment_reference)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )
    return record


@router.get("/billing/{billing_id}/dispute", response_model=dict)
async def get_dispute_info(
    billing_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Get information about disputing a billing record."""
    record = await service.get_billing_record(billing_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )
    return {
        "billing_id": record.id,
        "status": record.status,
        "can_dispute": record.status not in ["paid", "disputed"],
        "dispute_reasons": ["incorrect_amount", "duplicate_charge", "service_not_received", "other"],
    }


@router.post("/billing/{billing_id}/dispute", response_model=ConsortiumBillingResponse)
async def dispute_billing(
    billing_id: int,
    reason: str,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Dispute a billing record. Requires ADMIN role."""
    record = await service.dispute_billing(billing_id, reason)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )
    return record


@router.get("/{consortium_id}/members/{member_id}/balance", response_model=MemberBalanceResponse)
async def get_member_balance(
    consortium_id: int,
    member_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Get the current balance for a member."""
    return await service.get_member_balance(consortium_id, member_id)


@router.get("/{consortium_id}/financial-summary")
async def get_financial_summary(
    consortium_id: int,
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
):
    """Get financial summary for the consortium."""
    return await service.get_consortium_financial_summary(
        consortium_id, from_date, to_date
    )


# =============================================================================
# WHITE LABEL ENDPOINTS
# =============================================================================

@router.get("/members/{member_id}/white-label", response_model=ConsortiumWhiteLabelResponse | None)
async def get_white_label(
    member_id: int,
    current_user: User = Depends(require_authenticated),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get white label configuration for a member."""
    return await service.get_white_label_config(member_id)


@router.put("/members/{member_id}/white-label", response_model=ConsortiumWhiteLabelResponse)
async def update_white_label(
    member_id: int,
    data: ConsortiumWhiteLabelUpdate,
    current_user: User = Depends(require_admin),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Update white label configuration. Requires ADMIN role."""
    return await service.update_white_label(
        member_id,
        **data.model_dump(exclude_unset=True)
    )


@router.get("/white-label/by-domain")
async def get_white_label_by_domain(
    domain: str,
    current_user: User = Depends(require_authenticated),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get white label configuration by domain (for frontend routing)."""
    config = await service.get_white_label_by_domain(domain)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No white label configuration found for this domain"
        )
    return config


# =============================================================================
# SEARCHABLE SYSTEMS ENDPOINT
# =============================================================================

@router.get("/{consortium_id}/searchable-systems")
async def get_searchable_systems(
    consortium_id: int,
    requesting_system_id: int | None = Query(None),
    current_user: User = Depends(require_staff),
    service: ConsortiumService = Depends(get_consortium_service),
):
    """Get list of library systems to include in catalog search."""
    system_ids = await service.get_searchable_systems(
        consortium_id, requesting_system_id
    )
    return {"library_system_ids": system_ids}


# =============================================================================
# INVOICE EXPORT ENDPOINTS
# =============================================================================

@router.get("/billing/{billing_id}/export/pdf")
async def export_invoice_pdf(
    billing_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
    export_service: ConsortiumInvoiceExportService = Depends(get_invoice_export_service),
):
    """Export a single billing record as PDF invoice."""
    record = await service.get_billing_record(billing_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )

    # Generate PDF
    pdf_bytes = await export_service.generate_pdf_invoice(record)

    # Return as downloadable file
    filename = f"invoice_{record.invoice_number or billing_id}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/billing/{billing_id}/export/csv")
async def export_invoice_csv(
    billing_id: int,
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
    export_service: ConsortiumInvoiceExportService = Depends(get_invoice_export_service),
):
    """Export a single billing record as CSV."""
    record = await service.get_billing_record(billing_id)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Billing record not found"
        )

    # Generate CSV
    csv_string = export_service.generate_csv_invoice([record])

    # Return as downloadable file
    filename = f"invoice_{record.invoice_number or billing_id}.csv"
    return StreamingResponse(
        iter([csv_string]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.post("/billing/export/bulk-pdf")
async def export_invoices_bulk_pdf(
    billing_ids: list[int],
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
    export_service: ConsortiumInvoiceExportService = Depends(get_invoice_export_service),
):
    """Export multiple billing records as separate PDF files (returns zip).

    Note: For production, this should be optimized to return a zip file
    containing all PDFs. Current implementation returns a JSON response
    with download URLs.
    """
    records = []
    for billing_id in billing_ids:
        record = await service.get_billing_record(billing_id)
        if record:
            records.append(record)

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing records found"
        )

    return {
        "message": "Invoice export ready",
        "count": len(records),
        "records": [
            {
                "billing_id": r.id,
                "invoice_number": r.invoice_number,
                "download_pdf": f"/consortiums/billing/{r.id}/export/pdf",
                "download_csv": f"/consortiums/billing/{r.id}/export/csv",
            }
            for r in records
        ],
    }


@router.post("/{consortium_id}/billing/export/csv-summary")
async def export_consortium_billing_csv(
    consortium_id: int,
    member_id: int | None = Query(None),
    status: BillingStatus | None = Query(None),
    from_date: date | None = Query(None),
    to_date: date | None = Query(None),
    current_user: User = Depends(require_admin),
    service: ConsortiumBillingService = Depends(get_billing_service),
    export_service: ConsortiumInvoiceExportService = Depends(get_invoice_export_service),
):
    """Export all billing records for a period as CSV (for accounting software)."""
    records = await service.list_billing_records(
        consortium_id,
        member_id=member_id,
        status=status,
        from_date=from_date,
        to_date=to_date,
        limit=10000,  # Get all records
    )

    if not records:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No billing records found for the specified criteria"
        )

    # Generate CSV
    csv_string = export_service.generate_csv_invoice(records)

    # Return as downloadable file
    filename = f"consortium_{consortium_id}_billing_{from_date}_{to_date}.csv"
    return StreamingResponse(
        iter([csv_string]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
