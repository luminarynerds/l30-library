# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
EDI (Electronic Data Interchange) API Endpoints

Provides endpoints for:
- Vendor EDI profile management
- Sending purchase orders via EDI
- Processing inbound EDI messages
- Transaction tracking and retries
- Invoice reconciliation
- Connection testing
"""

import json
from app.core.logging import get_logger
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.pagination_config import PaginationDefaults
from ...core.shortcuts import get_or_404
from ...models.acquisition import PurchaseOrder, Vendor
from ...models.edi import (
    EDIInvoice,
    EDIInvoiceStatus,
    EDIMessageType,
    EDIOrderResponse,
    EDIShipmentNotice,
    EDITransaction,
    EDITransactionStatus,
    VendorEDIProfile,
)
from ...models.user import User
from ...schemas.edi import (
    BatchReconciliationRequest,
    BatchReconciliationResponse,
    EDIInvoiceDetail,
    EDIInvoiceListResponse,
    EDIInvoiceResponse,
    EDIOrderResponseDetail,
    EDIOrderResponseListResponse,
    EDIOrderResponseResponse,
    EDIShipmentNoticeDetail,
    EDIShipmentNoticeListResponse,
    EDIShipmentNoticeResponse,
    EDIStatistics,
    EDITransactionDetail,
    EDITransactionListResponse,
    EDITransactionResponse,
    InvoiceApprovalRequest,
    InvoiceDisputeRequest,
    ProcessInboundRequest,
    ProcessInboundResponse,
    ReconciliationResult,
    RetryTransactionRequest,
    RetryTransactionResponse,
    SendEDIOrderRequest,
    SendEDIOrderResponse,
    TestConnectionRequest,
    TestConnectionResponse,
    VendorEDIProfileCreate,
    VendorEDIProfileResponse,
    VendorEDIProfileUpdate,
)
from ...services.edi import EDIProcessor, EDIReconciliation, EDITransport
from .auth import get_current_user
from .dependencies import check_staff_access, check_admin_access

logger = get_logger(__name__)

router = APIRouter(prefix="/edi", tags=["edi"])




# ============ Vendor EDI Profile Management ============


@router.get("/profiles", response_model=list[VendorEDIProfileResponse])
async def list_edi_profiles(
    vendor_id: int | None = Query(None),
    enabled_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List vendor EDI profiles"""
    check_staff_access(current_user)

    query = select(VendorEDIProfile).options(selectinload(VendorEDIProfile.vendor))

    if vendor_id:
        query = query.where(VendorEDIProfile.vendor_id == vendor_id)

    if enabled_only:
        query = query.where(VendorEDIProfile.is_enabled == True)

    result = await db.execute(query)
    profiles = result.scalars().all()

    return [
        _profile_to_response(profile)
        for profile in profiles
    ]


@router.get("/profiles/{profile_id}", response_model=VendorEDIProfileResponse)
async def get_edi_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific vendor EDI profile"""
    check_staff_access(current_user)

    result = await db.execute(
        select(VendorEDIProfile)
        .where(VendorEDIProfile.id == profile_id)
        .options(selectinload(VendorEDIProfile.vendor))
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EDI profile not found")

    return _profile_to_response(profile)


@router.get("/profiles/vendor/{vendor_id}", response_model=VendorEDIProfileResponse | None)
async def get_vendor_edi_profile(
    vendor_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get EDI profile for a vendor"""
    check_staff_access(current_user)

    result = await db.execute(
        select(VendorEDIProfile)
        .where(VendorEDIProfile.vendor_id == vendor_id)
        .options(selectinload(VendorEDIProfile.vendor))
    )
    profile = result.scalar_one_or_none()

    if not profile:
        return None

    return _profile_to_response(profile)


@router.post("/profiles", response_model=VendorEDIProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_edi_profile(
    profile_in: VendorEDIProfileCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new vendor EDI profile"""
    check_admin_access(current_user)

    # Check vendor exists
    await get_or_404(db, Vendor, profile_in.vendor_id, "Vendor not found")

    # Check if profile already exists
    existing = await db.execute(
        select(VendorEDIProfile)
        .where(VendorEDIProfile.vendor_id == profile_in.vendor_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="EDI profile already exists for this vendor"
        )

    # Create profile
    profile_data = profile_in.model_dump(exclude_unset=True)

    # Handle vendor_settings
    if profile_data.get("vendor_settings"):
        profile_data["vendor_settings"] = json.dumps(profile_data["vendor_settings"])

    profile = VendorEDIProfile(**profile_data)
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    # Reload with vendor
    result = await db.execute(
        select(VendorEDIProfile)
        .where(VendorEDIProfile.id == profile.id)
        .options(selectinload(VendorEDIProfile.vendor))
    )
    profile = result.scalar_one()

    return _profile_to_response(profile)


@router.patch("/profiles/{profile_id}", response_model=VendorEDIProfileResponse)
async def update_edi_profile(
    profile_id: int,
    profile_in: VendorEDIProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a vendor EDI profile"""
    check_admin_access(current_user)

    result = await db.execute(
        select(VendorEDIProfile)
        .where(VendorEDIProfile.id == profile_id)
        .options(selectinload(VendorEDIProfile.vendor))
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EDI profile not found")

    update_data = profile_in.model_dump(exclude_unset=True)

    # Handle vendor_settings
    if "vendor_settings" in update_data and update_data["vendor_settings"]:
        update_data["vendor_settings"] = json.dumps(update_data["vendor_settings"])

    for field, value in update_data.items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)

    return _profile_to_response(profile)


@router.delete("/profiles/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edi_profile(
    profile_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a vendor EDI profile"""
    check_admin_access(current_user)

    profile = await get_or_404(db, VendorEDIProfile, profile_id, "EDI profile not found")

    await db.delete(profile)
    await db.commit()

    return None


def _profile_to_response(profile: VendorEDIProfile) -> VendorEDIProfileResponse:
    vendor_settings = None
    if profile.vendor_settings:
        try:
            vendor_settings = json.loads(profile.vendor_settings)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse vendor_settings JSON for EDI profile %s",
                profile.id,
            )

    return VendorEDIProfileResponse(
        id=profile.id,
        vendor_id=profile.vendor_id,
        vendor_name=profile.vendor.name if profile.vendor else None,
        is_enabled=profile.is_enabled,
        edi_standard=profile.edi_standard,
        sender_id=profile.sender_id,
        sender_qualifier=profile.sender_qualifier,
        receiver_id=profile.receiver_id,
        receiver_qualifier=profile.receiver_qualifier,
        transport_protocol=profile.transport_protocol,
        transport_host=profile.transport_host,
        transport_port=profile.transport_port,
        transport_username=profile.transport_username,
        transport_directory_outbound=profile.transport_directory_outbound,
        transport_directory_inbound=profile.transport_directory_inbound,
        supports_orders=profile.supports_orders,
        supports_ordrsp=profile.supports_ordrsp,
        supports_desadv=profile.supports_desadv,
        supports_invoic=profile.supports_invoic,
        max_retries=profile.max_retries,
        retry_interval_minutes=profile.retry_interval_minutes,
        auto_send_orders=profile.auto_send_orders,
        auto_process_responses=profile.auto_process_responses,
        auto_approve_invoices=profile.auto_approve_invoices,
        invoice_tolerance_percent=profile.invoice_tolerance_percent,
        is_test_mode=profile.is_test_mode,
        has_password=bool(profile.transport_password),
        has_ssh_key=bool(profile.ssh_private_key),
        vendor_settings=vendor_settings,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        last_transmission_at=profile.last_transmission_at,
        last_successful_transmission_at=profile.last_successful_transmission_at,
    )


# ============ Connection Testing ============


@router.post("/test-connection", response_model=TestConnectionResponse)
async def test_connection(
    request: TestConnectionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Test EDI connection for a vendor"""
    check_admin_access(current_user)

    result = await db.execute(
        select(VendorEDIProfile)
        .where(VendorEDIProfile.vendor_id == request.vendor_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="EDI profile not found")

    transport = EDITransport(profile)
    test_result = await transport.test_connection()

    connectivity_status = "connected" if test_result.success else "disconnected"
    authentication_result = test_result.auth_status if test_result.success else None

    return TestConnectionResponse(
        success=test_result.success,
        message=test_result.message,
        connectivity_status=connectivity_status,
        latency_ms=test_result.latency_ms,
        authentication_result=authentication_result,
        details={
            "host": profile.transport_host,
            "port": profile.transport_port,
            "protocol": str(profile.transport_protocol),
            "error": test_result.error
        } if not test_result.success else None
    )


# ============ Send Orders ============


@router.post("/send-order", response_model=SendEDIOrderResponse)
async def send_edi_order(
    request: SendEDIOrderRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send a purchase order via EDI"""
    check_staff_access(current_user)

    processor = EDIProcessor(db)
    success, transaction, message = await processor.send_purchase_order(
        request.purchase_order_id
    )

    return SendEDIOrderResponse(
        success=success,
        transaction_id=transaction.id if transaction else None,
        interchange_control_number=transaction.interchange_control_number if transaction else None,
        message=message,
        error=message if not success else None
    )


# ============ Transaction Management ============


@router.get("/transactions", response_model=EDITransactionListResponse)
async def list_transactions(
    vendor_id: int | None = Query(None),
    purchase_order_id: int | None = Query(None),
    message_type: EDIMessageType | None = Query(None),
    status: EDITransactionStatus | None = Query(None),
    direction: str | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List EDI transactions with filters"""
    check_staff_access(current_user)

    query = (
        select(EDITransaction)
        .options(
            selectinload(EDITransaction.vendor_edi_profile).selectinload(VendorEDIProfile.vendor),
            selectinload(EDITransaction.purchase_order)
        )
        .order_by(EDITransaction.created_at.desc())
    )

    if vendor_id:
        query = query.join(VendorEDIProfile).where(VendorEDIProfile.vendor_id == vendor_id)

    if purchase_order_id:
        query = query.where(EDITransaction.purchase_order_id == purchase_order_id)

    if message_type:
        query = query.where(EDITransaction.message_type == message_type)

    if status:
        query = query.where(EDITransaction.status == status)

    if direction:
        query = query.where(EDITransaction.direction == direction)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    transactions = result.scalars().all()

    items = []
    for t in transactions:
        vendor_name = None
        if t.vendor_edi_profile and t.vendor_edi_profile.vendor:
            vendor_name = t.vendor_edi_profile.vendor.name

        items.append(EDITransactionResponse(
            id=t.id,
            vendor_edi_profile_id=t.vendor_edi_profile_id,
            purchase_order_id=t.purchase_order_id,
            message_type=t.message_type,
            direction=t.direction,
            interchange_control_number=t.interchange_control_number,
            message_reference_number=t.message_reference_number,
            status=t.status,
            filename=t.filename,
            retry_count=t.retry_count,
            next_retry_at=t.next_retry_at,
            last_error=t.last_error,
            created_at=t.created_at,
            sent_at=t.sent_at,
            received_at=t.received_at,
            processed_at=t.processed_at,
            vendor_name=vendor_name,
            po_number=t.purchase_order.po_number if t.purchase_order else None
        ))

    return EDITransactionListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/transactions/{transaction_id}", response_model=EDITransactionDetail)
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get transaction details including raw message"""
    check_staff_access(current_user)

    result = await db.execute(
        select(EDITransaction)
        .where(EDITransaction.id == transaction_id)
        .options(
            selectinload(EDITransaction.vendor_edi_profile).selectinload(VendorEDIProfile.vendor),
            selectinload(EDITransaction.purchase_order)
        )
    )
    t = result.scalar_one_or_none()

    if not t:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    parsed_data = None
    if t.parsed_data:
        try:
            parsed_data = json.loads(t.parsed_data)
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse parsed_data JSON for EDI transaction %s",
                t.id,
            )

    vendor_name = None
    if t.vendor_edi_profile and t.vendor_edi_profile.vendor:
        vendor_name = t.vendor_edi_profile.vendor.name

    return EDITransactionDetail(
        id=t.id,
        vendor_edi_profile_id=t.vendor_edi_profile_id,
        purchase_order_id=t.purchase_order_id,
        message_type=t.message_type,
        direction=t.direction,
        interchange_control_number=t.interchange_control_number,
        message_reference_number=t.message_reference_number,
        status=t.status,
        filename=t.filename,
        retry_count=t.retry_count,
        next_retry_at=t.next_retry_at,
        last_error=t.last_error,
        created_at=t.created_at,
        sent_at=t.sent_at,
        received_at=t.received_at,
        processed_at=t.processed_at,
        vendor_name=vendor_name,
        po_number=t.purchase_order.po_number if t.purchase_order else None,
        raw_message=t.raw_message,
        parsed_data=parsed_data
    )


@router.post("/transactions/{transaction_id}/retry", response_model=RetryTransactionResponse)
async def retry_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retry a failed transaction"""
    check_staff_access(current_user)

    processor = EDIProcessor(db)
    success, message = await processor.retry_failed_transaction(transaction_id)

    # Get updated transaction
    result = await db.execute(
        select(EDITransaction).where(EDITransaction.id == transaction_id)
    )
    t = result.scalar_one_or_none()

    return RetryTransactionResponse(
        success=success,
        transaction_id=transaction_id,
        new_status=t.status if t else EDITransactionStatus.FAILED,
        message=message,
        error=message if not success else None
    )


# ============ Process Inbound Messages ============


@router.post("/process-inbound", response_model=ProcessInboundResponse)
async def process_inbound_messages(
    request: ProcessInboundRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Process inbound EDI messages from vendors"""
    check_staff_access(current_user)

    processor = EDIProcessor(db)
    results = await processor.process_inbound_messages(request.vendor_id)

    return ProcessInboundResponse(
        vendors_processed=results["vendors_processed"],
        files_processed=results["files_processed"],
        transactions_created=results["transactions_created"],
        errors=results["errors"]
    )


# ============ Invoice Management ============


@router.get("/invoices", response_model=EDIInvoiceListResponse)
async def list_invoices(
    vendor_id: int | None = Query(None),
    purchase_order_id: int | None = Query(None),
    status: EDIInvoiceStatus | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List EDI invoices with filters"""
    check_staff_access(current_user)

    query = (
        select(EDIInvoice)
        .options(
            selectinload(EDIInvoice.vendor),
            selectinload(EDIInvoice.purchase_order),
            selectinload(EDIInvoice.approved_by)
        )
        .order_by(EDIInvoice.created_at.desc())
    )

    if vendor_id:
        query = query.where(EDIInvoice.vendor_id == vendor_id)

    if purchase_order_id:
        query = query.where(EDIInvoice.purchase_order_id == purchase_order_id)

    if status:
        query = query.where(EDIInvoice.status == status)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    invoices = result.scalars().all()

    items = [_invoice_to_response(inv) for inv in invoices]

    return EDIInvoiceListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/invoices/{invoice_id}", response_model=EDIInvoiceDetail)
async def get_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get invoice details including line items"""
    check_staff_access(current_user)

    result = await db.execute(
        select(EDIInvoice)
        .where(EDIInvoice.id == invoice_id)
        .options(
            selectinload(EDIInvoice.vendor),
            selectinload(EDIInvoice.purchase_order),
            selectinload(EDIInvoice.approved_by)
        )
    )
    inv = result.scalar_one_or_none()

    if not inv:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invoice not found")

    return _invoice_to_detail(inv)


@router.post("/invoices/{invoice_id}/reconcile", response_model=ReconciliationResult)
async def reconcile_invoice(
    invoice_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reconcile invoice against purchase order"""
    check_staff_access(current_user)

    reconciliation = EDIReconciliation(db)
    result = await reconciliation.reconcile_invoice(invoice_id)

    return ReconciliationResult(
        invoice_id=result.invoice_id,
        purchase_order_id=result.purchase_order_id,
        status=result.status,
        matched_items=result.matched_items,
        total_items=result.total_items,
        po_total=result.po_total,
        invoice_total=result.invoice_total,
        variance_amount=result.variance_amount,
        variance_percent=result.variance_percent,
        discrepancies=result.discrepancies,
        recommendations=result.recommendations
    )


@router.post("/invoices/batch-reconcile", response_model=BatchReconciliationResponse)
async def batch_reconcile(
    request: BatchReconciliationRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Reconcile multiple invoices"""
    check_staff_access(current_user)

    reconciliation = EDIReconciliation(db)
    results = await reconciliation.batch_reconcile(
        request.invoice_ids if request.invoice_ids else None
    )

    return BatchReconciliationResponse(
        total_processed=results["total_processed"],
        matched=results["matched"],
        partial_match=results["partial_match"],
        disputed=results["disputed"],
        errors=results["errors"],
        results=[
            ReconciliationResult(
                invoice_id=r["invoice_id"],
                purchase_order_id=r["purchase_order_id"],
                status=r["status"],
                matched_items=r["matched_items"],
                total_items=r["total_items"],
                po_total=None,
                invoice_total=None,
                variance_amount=Decimal(r["variance_amount"]) if r["variance_amount"] else None,
                variance_percent=None,
                discrepancies=[],
                recommendations=[]
            )
            for r in results["results"]
        ]
    )


@router.post("/invoices/{invoice_id}/approve")
async def approve_invoice(
    invoice_id: int,
    request: InvoiceApprovalRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Approve an invoice for payment"""
    check_admin_access(current_user)

    reconciliation = EDIReconciliation(db)
    success, message = await reconciliation.approve_invoice(
        invoice_id, current_user, request.notes
    )

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message}


@router.post("/invoices/{invoice_id}/dispute")
async def dispute_invoice(
    invoice_id: int,
    request: InvoiceDisputeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark an invoice as disputed"""
    check_staff_access(current_user)

    reconciliation = EDIReconciliation(db)
    success, message = await reconciliation.dispute_invoice(invoice_id, request.reason)

    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    return {"message": message}


@router.post("/invoices/auto-approve")
async def auto_approve_invoices(
    vendor_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Auto-approve invoices within tolerance"""
    check_admin_access(current_user)

    reconciliation = EDIReconciliation(db)
    results = await reconciliation.auto_approve_invoices(vendor_id)

    return results


def _invoice_to_response(inv: EDIInvoice) -> EDIInvoiceResponse:
    return EDIInvoiceResponse(
        id=inv.id,
        edi_transaction_id=inv.edi_transaction_id,
        purchase_order_id=inv.purchase_order_id,
        vendor_id=inv.vendor_id,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        subtotal=inv.subtotal,
        tax_amount=inv.tax_amount,
        shipping_amount=inv.shipping_amount,
        discount_amount=inv.discount_amount,
        total_amount=inv.total_amount,
        currency_code=inv.currency_code,
        status=inv.status,
        po_total=inv.po_total,
        variance_amount=inv.variance_amount,
        variance_reason=inv.variance_reason,
        matched_line_items=inv.matched_line_items,
        total_line_items=inv.total_line_items,
        approved_by_id=inv.approved_by_id,
        approved_at=inv.approved_at,
        rejection_reason=inv.rejection_reason,
        notes=inv.notes,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        vendor_name=inv.vendor.name if inv.vendor else None,
        po_number=inv.purchase_order.po_number if inv.purchase_order else None,
        approved_by_name=inv.approved_by.full_name if inv.approved_by else None
    )


def _invoice_to_detail(inv: EDIInvoice) -> EDIInvoiceDetail:
    from ...schemas.edi import EDIInvoiceLineItem

    line_items = []
    if inv.line_items:
        try:
            items_data = json.loads(inv.line_items)
            for item in items_data:
                line_items.append(EDIInvoiceLineItem(
                    line_number=item.get("line_number", 0),
                    isbn=item.get("isbn"),
                    title=item.get("title"),
                    quantity=item.get("quantity", 0),
                    unit_price=Decimal(str(item.get("unit_price", 0))) if item.get("unit_price") else Decimal("0"),
                    line_total=Decimal(str(item.get("line_total", 0))) if item.get("line_total") else Decimal("0"),
                    po_item_id=item.get("po_item_id"),
                    match_status=item.get("match_status")
                ))
        except json.JSONDecodeError:
            logger.warning(
                "Failed to parse line_items JSON for EDI invoice %s",
                inv.id,
            )

    return EDIInvoiceDetail(
        id=inv.id,
        edi_transaction_id=inv.edi_transaction_id,
        purchase_order_id=inv.purchase_order_id,
        vendor_id=inv.vendor_id,
        invoice_number=inv.invoice_number,
        invoice_date=inv.invoice_date,
        due_date=inv.due_date,
        subtotal=inv.subtotal,
        tax_amount=inv.tax_amount,
        shipping_amount=inv.shipping_amount,
        discount_amount=inv.discount_amount,
        total_amount=inv.total_amount,
        currency_code=inv.currency_code,
        status=inv.status,
        po_total=inv.po_total,
        variance_amount=inv.variance_amount,
        variance_reason=inv.variance_reason,
        matched_line_items=inv.matched_line_items,
        total_line_items=inv.total_line_items,
        approved_by_id=inv.approved_by_id,
        approved_at=inv.approved_at,
        rejection_reason=inv.rejection_reason,
        notes=inv.notes,
        created_at=inv.created_at,
        updated_at=inv.updated_at,
        vendor_name=inv.vendor.name if inv.vendor else None,
        po_number=inv.purchase_order.po_number if inv.purchase_order else None,
        approved_by_name=inv.approved_by.full_name if inv.approved_by else None,
        line_items=line_items
    )


# ============ Order Responses ============


@router.get("/order-responses", response_model=EDIOrderResponseListResponse)
async def list_order_responses(
    vendor_id: int | None = Query(None),
    purchase_order_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List order responses (ORDRSP)"""
    check_staff_access(current_user)

    query = (
        select(EDIOrderResponse)
        .options(
            selectinload(EDIOrderResponse.vendor),
            selectinload(EDIOrderResponse.purchase_order)
        )
        .order_by(EDIOrderResponse.created_at.desc())
    )

    if vendor_id:
        query = query.where(EDIOrderResponse.vendor_id == vendor_id)

    if purchase_order_id:
        query = query.where(EDIOrderResponse.purchase_order_id == purchase_order_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    responses = result.scalars().all()

    items = [
        EDIOrderResponseResponse(
            id=r.id,
            edi_transaction_id=r.edi_transaction_id,
            purchase_order_id=r.purchase_order_id,
            vendor_id=r.vendor_id,
            vendor_order_number=r.vendor_order_number,
            response_date=r.response_date,
            response_code=r.response_code,
            response_description=r.response_description,
            items_accepted=r.items_accepted,
            items_rejected=r.items_rejected,
            items_backordered=r.items_backordered,
            items_substituted=r.items_substituted,
            expected_ship_date=r.expected_ship_date,
            expected_delivery_date=r.expected_delivery_date,
            is_processed=r.is_processed,
            processed_at=r.processed_at,
            created_at=r.created_at,
            vendor_name=r.vendor.name if r.vendor else None,
            po_number=r.purchase_order.po_number if r.purchase_order else None
        )
        for r in responses
    ]

    return EDIOrderResponseListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


# ============ Shipment Notices ============


@router.get("/shipment-notices", response_model=EDIShipmentNoticeListResponse)
async def list_shipment_notices(
    vendor_id: int | None = Query(None),
    purchase_order_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List shipment notices (DESADV)"""
    check_staff_access(current_user)

    query = (
        select(EDIShipmentNotice)
        .options(
            selectinload(EDIShipmentNotice.vendor),
            selectinload(EDIShipmentNotice.purchase_order)
        )
        .order_by(EDIShipmentNotice.created_at.desc())
    )

    if vendor_id:
        query = query.where(EDIShipmentNotice.vendor_id == vendor_id)

    if purchase_order_id:
        query = query.where(EDIShipmentNotice.purchase_order_id == purchase_order_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page)

    result = await db.execute(query)
    notices = result.scalars().all()

    items = [
        EDIShipmentNoticeResponse(
            id=n.id,
            edi_transaction_id=n.edi_transaction_id,
            purchase_order_id=n.purchase_order_id,
            vendor_id=n.vendor_id,
            shipment_number=n.shipment_number,
            ship_date=n.ship_date,
            expected_delivery_date=n.expected_delivery_date,
            carrier_name=n.carrier_name,
            carrier_code=n.carrier_code,
            tracking_number=n.tracking_number,
            package_count=n.package_count,
            total_weight=n.total_weight,
            weight_unit=n.weight_unit,
            total_items_shipped=n.total_items_shipped,
            is_processed=n.is_processed,
            processed_at=n.processed_at,
            created_at=n.created_at,
            vendor_name=n.vendor.name if n.vendor else None,
            po_number=n.purchase_order.po_number if n.purchase_order else None
        )
        for n in notices
    ]

    return EDIShipmentNoticeListResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


# ============ Statistics ============


@router.get("/statistics", response_model=EDIStatistics)
async def get_statistics(
    vendor_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get EDI statistics"""
    check_staff_access(current_user)

    processor = EDIProcessor(db)
    stats = await processor.get_statistics(vendor_id)

    return EDIStatistics(
        total_transactions=stats["total_transactions"],
        pending_transactions=stats["pending_transactions"],
        failed_transactions=stats["failed_transactions"],
        successful_transactions=stats["successful_transactions"],
        pending_invoices=stats["pending_invoices"],
        disputed_invoices=stats["disputed_invoices"],
        total_invoice_amount=Decimal(stats["total_invoice_amount"]),
        last_24h_transactions=stats["last_24h_transactions"],
        by_message_type=stats["by_message_type"]
    )


@router.get("/invoices/batch-reconcile")
async def get_invoices_batch_reconcile_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of /invoices/batch-reconcile operation."""
    return {"status": "pending", "processed": 0, "total": 0}




