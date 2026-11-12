# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Print Notice Management API Endpoints

This module provides endpoints for:
- Print notice queue management
- Batch creation and processing
- PDF generation
- Cost tracking and reporting
- Returned mail handling
- Notice history
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...utils.range_response import create_range_response
from ...models.print_notice import (
    PrintNotice, PrintNoticeBatch, PrintNoticeBatchStatus,
    PrintNoticeCostConfig, PrintNoticeHistory, PrintNoticeStatus, PrintNoticeType
)
from ...models.user import AddressStatus, NoticePreference, User, UserRole
from ...schemas.print_notice import (
    AddressValidationRequest, AddressValidationResponse,
    BatchMergeResult, BatchPDFGenerationResult,
    CostConfigResponse, CostConfigUpdate, CostSummaryResponse,
    PatronAddressStatusUpdate, PatronNoticePreferenceUpdate,
    PrintNoticeBatchAddNotices, PrintNoticeBatchCreate,
    PrintNoticeBatchDetailResponse, PrintNoticeBatchListResponse, PrintNoticeBatchResponse,
    PrintNoticeAccountExpiringCreate, PrintNoticeFineCreate,
    PrintNoticeHoldReadyCreate, PrintNoticeListResponse,
    PrintNoticeOverdueCreate, PrintNoticeResponse,
    PrintNoticeHistoryListResponse, PrintNoticeHistoryResponse,
    ReturnedMailBulkRequest, ReturnedMailRequest
)
from ...services.address_service import validate_address
from ...services.print_notice_service import PrintNoticeService
from .dependencies import require_staff

router = APIRouter(prefix="/staff/print-notices", tags=["staff-print-notices"])


# =============================================================================
# Address Validation Endpoints
# =============================================================================

@router.post("/validate-address", response_model=AddressValidationResponse)
async def validate_patron_address(
    address_data: AddressValidationRequest,
    staff_user: User = Depends(require_staff),
):
    """
    Validate and normalize an address to USPS standards.

    Returns validation status, any errors/warnings, and the normalized address.
    """
    result = validate_address(
        address_data.address_line1,
        address_data.address_line2,
        address_data.city,
        address_data.state,
        address_data.zip_code,
        address_data.country,
    )

    normalized = None
    if result.normalized_address:
        from ...schemas.print_notice import AddressBase
        normalized = AddressBase(
            address_line1=result.normalized_address.line1,
            address_line2=result.normalized_address.line2,
            city=result.normalized_address.city,
            state=result.normalized_address.state,
            zip_code=result.normalized_address.zip_code if not result.normalized_address.zip_plus4
                else f"{result.normalized_address.zip_code}-{result.normalized_address.zip_plus4}",
            country=result.normalized_address.country,
        )

    return AddressValidationResponse(
        is_valid=result.is_valid,
        errors=result.errors,
        warnings=result.warnings,
        normalized_address=normalized,
    )


# =============================================================================
# Patron Notice Preference Endpoints
# =============================================================================

@router.put("/patrons/{patron_id}/notice-preference")
async def update_patron_notice_preference(
    patron_id: int,
    preference_data: PatronNoticePreferenceUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a patron's notice delivery preference.

    If setting to 'print', address fields should be provided.
    """
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    patron.notice_preference = preference_data.notice_preference

    # Update address if provided
    if preference_data.address_line1:
        patron.address_line1 = preference_data.address_line1
    if preference_data.address_line2 is not None:
        patron.address_line2 = preference_data.address_line2
    if preference_data.city:
        patron.city = preference_data.city
    if preference_data.state:
        patron.state = preference_data.state
    if preference_data.zip_code:
        patron.zip_code = preference_data.zip_code

    # If setting to print, validate address
    if preference_data.notice_preference == NoticePreference.PRINT:
        if not all([patron.address_line1, patron.city, patron.state, patron.zip_code]):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Complete mailing address required for print notices"
            )

        validation = validate_address(
            patron.address_line1,
            patron.address_line2,
            patron.city,
            patron.state,
            patron.zip_code,
            patron.country or "USA"
        )

        if not validation.is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid address: {', '.join(validation.errors)}"
            )

        # Mark as unverified until mail is successfully delivered
        patron.address_status = AddressStatus.UNVERIFIED

    await db.commit()

    return {"message": "Notice preference updated successfully"}


@router.put("/patrons/{patron_id}/address-status")
async def update_patron_address_status(
    patron_id: int,
    status_data: PatronAddressStatusUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a patron's address verification status.

    Used after mail delivery confirmation or returned mail.
    """
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    patron.address_status = status_data.address_status

    if status_data.address_status == AddressStatus.VALID:
        patron.address_verified_at = datetime.now(timezone.utc)
    elif status_data.address_status == AddressStatus.RETURNED_MAIL:
        patron.address_returned_mail_count += 1
        patron.address_last_returned_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Address status updated successfully"}


# =============================================================================
# Print Notice Queue Endpoints
# =============================================================================

@router.post("/notices/overdue", response_model=PrintNoticeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_overdue_notice(
    request: Request,
    notice_data: PrintNoticeOverdueCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create an overdue notice for a patron."""
    service = PrintNoticeService(db)

    try:
        notice = await service.queue_overdue_notice(
            patron_id=notice_data.patron_id,
            checkout_ids=notice_data.checkout_ids,
            created_by_id=staff_user.id,
        )
        return PrintNoticeResponse.model_validate(notice)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/notices/fine", response_model=PrintNoticeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_fine_notice(
    request: Request,
    notice_data: PrintNoticeFineCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a fine notice for a patron."""
    service = PrintNoticeService(db)

    try:
        notice = await service.queue_fine_notice(
            patron_id=notice_data.patron_id,
            fine_ids=notice_data.fine_ids,
            created_by_id=staff_user.id,
        )
        return PrintNoticeResponse.model_validate(notice)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/notices/hold-ready", response_model=PrintNoticeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_hold_ready_notice(
    request: Request,
    notice_data: PrintNoticeHoldReadyCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a hold ready notice for a patron."""
    service = PrintNoticeService(db)

    try:
        notice = await service.queue_hold_ready_notice(
            patron_id=notice_data.patron_id,
            hold_id=notice_data.hold_id,
            created_by_id=staff_user.id,
        )
        return PrintNoticeResponse.model_validate(notice)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/notices/account-expiring", response_model=PrintNoticeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_account_expiring_notice(
    request: Request,
    notice_data: PrintNoticeAccountExpiringCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create an account expiring notice for a patron."""
    service = PrintNoticeService(db)

    try:
        notice = await service.queue_account_expiring_notice(
            patron_id=notice_data.patron_id,
            expiration_date=notice_data.expiration_date,
            created_by_id=staff_user.id,
        )
        return PrintNoticeResponse.model_validate(notice)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/notices", response_model=PrintNoticeListResponse)
async def list_notices(
    patron_id: Optional[int] = Query(None),
    status: Optional[PrintNoticeStatus] = Query(None),
    notice_type: Optional[PrintNoticeType] = Query(None),
    batch_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List print notices with optional filtering."""
    service = PrintNoticeService(db)

    notices = await service.list_notices(
        patron_id=patron_id,
        status=status,
        notice_type=notice_type,
        batch_id=batch_id,
        limit=limit,
        offset=offset,
    )

    # Get total count
    count_query = select(func.count(PrintNotice.id))
    if patron_id:
        count_query = count_query.where(PrintNotice.patron_id == patron_id)
    if status:
        count_query = count_query.where(PrintNotice.status == status)
    if notice_type:
        count_query = count_query.where(PrintNotice.notice_type == notice_type)
    if batch_id:
        count_query = count_query.where(PrintNotice.batch_id == batch_id)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    return PrintNoticeListResponse(
        items=[PrintNoticeResponse.model_validate(n) for n in notices],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/notices/{notice_id}", response_model=PrintNoticeResponse)
async def get_notice(
    notice_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific print notice."""
    service = PrintNoticeService(db)
    notice = await service.get_notice(notice_id)

    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")

    return PrintNoticeResponse.model_validate(notice)


@router.get("/notices/{notice_id}/pdf")
async def get_notice_pdf(
    notice_id: int,
    request: Request,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Download the PDF for a specific notice.

    Supports HTTP 206 Partial Content for resumable downloads:
    - Use Range header to request specific byte ranges
    - Example: Range: bytes=0-1023 (first 1KB)
    - Example: Range: bytes=1024- (from 1KB to end)

    Returns:
    - 200 OK: Full file content (no Range header)
    - 206 Partial Content: Requested byte range(s)
    - 304 Not Modified: If ETag matches (cache hit)
    - 416 Range Not Satisfiable: Invalid range requested
    """
    service = PrintNoticeService(db)
    notice = await service.get_notice(notice_id)

    if not notice:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notice not found")

    if not notice.pdf_file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="PDF not yet generated")

    # Return range-aware response with streaming support
    return await create_range_response(
        request=request,
        file_path=notice.pdf_file_path,
        media_type="application/pdf",
        filename=f"notice_{notice_id}.pdf",
        include_etag=True
    )


# =============================================================================
# Batch Management Endpoints
# =============================================================================

@router.post("/batches", response_model=PrintNoticeBatchResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_batch(
    request: Request,
    batch_data: PrintNoticeBatchCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new print notice batch."""
    service = PrintNoticeService(db)

    batch = await service.create_batch(
        name=batch_data.name,
        notice_types=batch_data.notice_types,
        created_by_id=staff_user.id,
        auto_close_hours=batch_data.auto_close_hours,
    )

    return PrintNoticeBatchResponse.model_validate(batch)


@router.get("/batches", response_model=PrintNoticeBatchListResponse)
async def list_batches(
    status: Optional[PrintNoticeBatchStatus] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List print notice batches."""
    service = PrintNoticeService(db)

    batches = await service.list_batches(
        status=status,
        limit=limit,
        offset=offset,
    )

    # Get total count
    count_query = select(func.count(PrintNoticeBatch.id))
    if status:
        count_query = count_query.where(PrintNoticeBatch.status == status)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    return PrintNoticeBatchListResponse(
        items=[PrintNoticeBatchResponse.model_validate(b) for b in batches],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/batches/{batch_id}", response_model=PrintNoticeBatchDetailResponse)
async def get_batch(
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific batch with its notices."""
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)

    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    return PrintNoticeBatchDetailResponse(
        **PrintNoticeBatchResponse.model_validate(batch).model_dump(),
        notices=[PrintNoticeResponse.model_validate(n) for n in batch.notices],
    )


@router.get("/batches/{batch_id}/add-notices", response_model=PrintNoticeBatchResponse)
@limiter.limit("30/minute")
async def check_batch_can_add_notices(
    batch_id: int,
    request: Request,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check if notices can be added to a batch."""
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return PrintNoticeBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/add-notices", response_model=PrintNoticeBatchResponse)
@limiter.limit("30/minute")
async def add_notices_to_batch(
    request: Request,
    batch_id: int,
    add_data: PrintNoticeBatchAddNotices,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add notices to an existing batch."""
    service = PrintNoticeService(db)

    try:
        batch = await service.add_notices_to_batch(batch_id, add_data.notice_ids)
        return PrintNoticeBatchResponse.model_validate(batch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/batches/{batch_id}/add-pending")
@limiter.limit("10/minute")
async def check_pending_notices(
    batch_id: int,
    request: Request,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check pending notices available to add."""
    service = PrintNoticeService(db)
    pending = await service.get_pending_notices()
    return {"pending_count": len(pending), "batch_id": batch_id}


@router.post("/batches/{batch_id}/add-pending")
@limiter.limit("10/minute")
async def add_all_pending_to_batch(
    request: Request,
    batch_id: int,
    notice_types: Optional[str] = Query(None, description="Comma-separated notice types"),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Add all pending notices to a batch."""
    service = PrintNoticeService(db)

    # Parse notice types
    types = None
    if notice_types:
        types = [PrintNoticeType(t.strip()) for t in notice_types.split(",")]

    pending = await service.get_pending_notices(notice_types=types)

    if not pending:
        return {"message": "No pending notices to add", "added_count": 0}

    try:
        batch = await service.add_notices_to_batch(
            batch_id, [n.id for n in pending]
        )
        return {
            "message": f"Added {len(pending)} notices to batch",
            "added_count": len(pending),
            "batch": PrintNoticeBatchResponse.model_validate(batch),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/batches/{batch_id}/merge")
@limiter.limit("10/minute")
async def check_batch_merge_status(
    batch_id: int,
    request: Request,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check if batch notices can be merged."""
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"batch_id": batch_id, "notice_count": len(batch.notices)}


@router.post("/batches/{batch_id}/merge", response_model=BatchMergeResult)
@limiter.limit("10/minute")
async def merge_batch_notices(
    request: Request,
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Merge multiple notices for the same patron into a single mailing.

    This reduces postage costs by combining notices addressed to the same patron.
    """
    service = PrintNoticeService(db)

    try:
        result = await service.merge_notices_for_batch(batch_id)
        return BatchMergeResult(
            merged_count=result["merged_count"],
            total_savings=result["total_savings"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/batches/{batch_id}/close", response_model=PrintNoticeBatchResponse)
async def check_batch_closeable(
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check if a batch can be closed."""
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return PrintNoticeBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/close", response_model=PrintNoticeBatchResponse)
@limiter.limit("10/minute")
async def close_batch(
    request: Request,
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Close a batch (no more notices can be added)."""
    service = PrintNoticeService(db)

    try:
        batch = await service.close_batch(batch_id, closed_by_id=staff_user.id)
        return PrintNoticeBatchResponse.model_validate(batch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/batches/{batch_id}/generate-pdfs")
async def check_batch_pdf_status(
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check the PDF generation status for a batch."""
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"batch_id": batch_id, "status": batch.status, "notice_count": len(batch.notices)}


@router.post("/batches/{batch_id}/generate-pdfs", response_model=BatchPDFGenerationResult)
@limiter.limit("5/minute")
async def generate_batch_pdfs(
    request: Request,
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate PDFs for all notices in a batch.

    This should be called after the batch is closed and before printing.
    """
    service = PrintNoticeService(db)

    try:
        result = await service.generate_batch_pdfs(batch_id)
        return BatchPDFGenerationResult(
            generated_count=result["generated_count"],
            total_pages=result["total_pages"],
            manifest_path=result["manifest_path"],
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/batches/{batch_id}/manifest")
async def get_batch_manifest(
    batch_id: int,
    request: Request,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Download the manifest PDF for a batch.

    Supports HTTP 206 Partial Content for resumable downloads:
    - Use Range header to request specific byte ranges
    - Example: Range: bytes=0-1023 (first 1KB)
    - Example: Range: bytes=1024- (from 1KB to end)

    Returns:
    - 200 OK: Full file content (no Range header)
    - 206 Partial Content: Requested byte range(s)
    - 304 Not Modified: If ETag matches (cache hit)
    - 416 Range Not Satisfiable: Invalid range requested
    """
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)

    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")

    if not batch.manifest_pdf_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Manifest not yet generated")

    # Return range-aware response with streaming support
    return await create_range_response(
        request=request,
        file_path=batch.manifest_pdf_path,
        media_type="application/pdf",
        filename=f"manifest_{batch.batch_number}.pdf",
        include_etag=True
    )


@router.get("/batches/{batch_id}/mark-printed", response_model=PrintNoticeBatchResponse)
async def check_batch_print_status(
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check if a batch can be marked as printed."""
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return PrintNoticeBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/mark-printed", response_model=PrintNoticeBatchResponse)
@limiter.limit("10/minute")
async def mark_batch_printed(
    request: Request,
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a batch as printed."""
    service = PrintNoticeService(db)

    try:
        batch = await service.mark_batch_printed(batch_id, printed_by_id=staff_user.id)
        return PrintNoticeBatchResponse.model_validate(batch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/batches/{batch_id}/mark-mailed", response_model=PrintNoticeBatchResponse)
async def check_batch_mail_status(
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Check if a batch can be marked as mailed."""
    service = PrintNoticeService(db)
    batch = await service.get_batch(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    return PrintNoticeBatchResponse.model_validate(batch)


@router.post("/batches/{batch_id}/mark-mailed", response_model=PrintNoticeBatchResponse)
@limiter.limit("10/minute")
async def mark_batch_mailed(
    request: Request,
    batch_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a batch as mailed.

    This creates historical records for all notices in the batch.
    """
    service = PrintNoticeService(db)

    try:
        batch = await service.mark_batch_mailed(batch_id, mailed_by_id=staff_user.id)
        return PrintNoticeBatchResponse.model_validate(batch)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Returned Mail Handling
# =============================================================================

@router.post("/notices/{notice_id}/returned", response_model=PrintNoticeResponse)
@limiter.limit("30/minute")
async def mark_notice_returned(
    request: Request,
    notice_id: int,
    return_data: ReturnedMailRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a notice as returned mail.

    Optionally updates the patron's address status to indicate bad address.
    """
    service = PrintNoticeService(db)

    try:
        notice = await service.mark_notice_returned(
            notice_id,
            return_reason=return_data.return_reason,
            update_patron_address=return_data.update_patron_address,
        )
        return PrintNoticeResponse.model_validate(notice)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/notices/bulk-returned")
@limiter.limit("10/minute")
async def mark_notices_bulk_returned(
    request: Request,
    return_data: ReturnedMailBulkRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark multiple notices as returned mail."""
    service = PrintNoticeService(db)

    processed = 0
    failed = []

    for notice_id in return_data.notice_ids:
        try:
            await service.mark_notice_returned(
                notice_id,
                return_reason=return_data.return_reason,
                update_patron_address=return_data.update_patron_addresses,
            )
            processed += 1
        except Exception as e:  # noqa: BLE001  # per-notice — record failure and continue
            failed.append({"notice_id": notice_id, "error": str(e)})

    return {
        "processed_count": processed,
        "failed_count": len(failed),
        "failed": failed,
    }


# =============================================================================
# Cost Configuration and Tracking
# =============================================================================

@router.get("/cost-config", response_model=CostConfigResponse)
async def get_cost_config(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get the current cost configuration."""
    service = PrintNoticeService(db)
    config = await service.get_cost_config()

    return CostConfigResponse(
        id=config.id if config.id else 0,
        cost_per_page=config.cost_per_page,
        first_class_letter=config.first_class_letter,
        first_class_large_envelope=config.first_class_large_envelope,
        presort_standard=config.presort_standard,
        large_envelope_page_threshold=config.large_envelope_page_threshold,
        # An unsaved default config object HAS these attrs but they're None
        # (Python-side column defaults only apply on flush), so hasattr passed
        # None through and 500'd the required bool/datetime fields. Guard on the
        # value, not attribute existence.
        is_active=config.is_active if getattr(config, 'is_active', None) is not None else True,
        effective_from=config.effective_from if getattr(config, 'effective_from', None) is not None else datetime.now(timezone.utc),
        effective_to=getattr(config, 'effective_to', None),
        notes=getattr(config, 'notes', None),
        created_at=config.created_at if getattr(config, 'created_at', None) is not None else datetime.now(timezone.utc),
        updated_at=getattr(config, 'updated_at', None),
    )


@router.post("/cost-config", response_model=CostConfigResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
async def update_cost_config(
    request: Request,
    config_data: CostConfigUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update cost configuration.

    Creates a new configuration record (old one remains for historical reference).
    """
    # Deactivate current config
    result = await db.execute(
        select(PrintNoticeCostConfig).where(PrintNoticeCostConfig.is_active == True)
    )
    current_config = result.scalar_one_or_none()

    if current_config:
        current_config.is_active = False
        current_config.effective_to = datetime.now(timezone.utc)

    # Create new config
    new_config = PrintNoticeCostConfig(
        cost_per_page=config_data.cost_per_page or (current_config.cost_per_page if current_config else Decimal("0.05")),
        first_class_letter=config_data.first_class_letter or (current_config.first_class_letter if current_config else Decimal("0.68")),
        first_class_large_envelope=config_data.first_class_large_envelope or (current_config.first_class_large_envelope if current_config else Decimal("1.50")),
        presort_standard=config_data.presort_standard or (current_config.presort_standard if current_config else Decimal("0.45")),
        large_envelope_page_threshold=config_data.large_envelope_page_threshold or (current_config.large_envelope_page_threshold if current_config else 6),
        notes=config_data.notes,
        is_active=True,
        created_by_id=staff_user.id,
    )

    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)

    return CostConfigResponse.model_validate(new_config)


@router.get("/cost-summary", response_model=CostSummaryResponse)
async def get_cost_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get cost summary for print notices."""
    service = PrintNoticeService(db)

    summary = await service.get_cost_summary(
        start_date=start_date,
        end_date=end_date,
    )

    return CostSummaryResponse(
        total_notices=summary["total_notices"],
        total_cost=summary["total_cost"],
        returned_count=summary["returned_count"],
        return_rate=summary["return_rate"],
        period_start=start_date,
        period_end=end_date,
    )


# =============================================================================
# Notice History
# =============================================================================

@router.get("/history", response_model=PrintNoticeHistoryListResponse)
async def get_notice_history(
    patron_id: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get notice history for a patron or all patrons."""
    service = PrintNoticeService(db)

    history = await service.get_notice_history(
        patron_id=patron_id,
        limit=limit,
        offset=offset,
    )

    # Get total count
    count_query = select(func.count(PrintNoticeHistory.id))
    if patron_id:
        count_query = count_query.where(PrintNoticeHistory.patron_id == patron_id)

    result = await db.execute(count_query)
    total = result.scalar() or 0

    return PrintNoticeHistoryListResponse(
        items=[PrintNoticeHistoryResponse.model_validate(h) for h in history],
        total=total,
        limit=limit,
        offset=offset,
    )


# =============================================================================
# Patrons Requiring Print Notices
# =============================================================================

@router.get("/patrons-requiring-print")
async def get_patrons_requiring_print_notices(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a list of patrons who require print notices.

    These are patrons with notice_preference set to 'print' or
    who have no email address.
    """
    service = PrintNoticeService(db)
    patrons = await service.get_patrons_needing_print_notices()

    return {
        "patrons": [
            {
                "id": p.id,
                "name": p.full_name,
                "library_card": p.library_card,
                "notice_preference": str(p.notice_preference),
                "address_status": str(p.address_status),
                "has_valid_address": bool(
                    p.address_line1 and p.city and p.state and p.zip_code
                ),
            }
            for p in patrons
        ],
        "total": len(patrons),
    }


# =============================================================================
# Dashboard Statistics
# =============================================================================

@router.get("/dashboard-stats")
async def get_print_notice_dashboard_stats(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard statistics for print notices."""
    # Pending notices count
    pending_result = await db.execute(
        select(func.count(PrintNotice.id)).where(
            PrintNotice.status == PrintNoticeStatus.PENDING
        )
    )
    pending_count = pending_result.scalar() or 0

    # Open batches count
    open_batches_result = await db.execute(
        select(func.count(PrintNoticeBatch.id)).where(
            PrintNoticeBatch.status == PrintNoticeBatchStatus.OPEN
        )
    )
    open_batches = open_batches_result.scalar() or 0

    # Notices ready for mailing (printed but not mailed)
    ready_to_mail_result = await db.execute(
        select(func.count(PrintNotice.id)).where(
            PrintNotice.status == PrintNoticeStatus.PRINTED
        )
    )
    ready_to_mail = ready_to_mail_result.scalar() or 0

    # Returned mail this month
    from datetime import timedelta
    month_ago = datetime.now(timezone.utc) - timedelta(days=30)
    returned_result = await db.execute(
        select(func.count(PrintNotice.id)).where(
            PrintNotice.status == PrintNoticeStatus.RETURNED,
            PrintNotice.returned_at >= month_ago,
        )
    )
    returned_this_month = returned_result.scalar() or 0

    # Total cost this month
    cost_result = await db.execute(
        select(func.sum(PrintNoticeHistory.total_cost)).where(
            PrintNoticeHistory.mailed_at >= month_ago
        )
    )
    total_cost_this_month = cost_result.scalar() or Decimal("0.00")

    # Patrons needing print notices
    print_patrons_result = await db.execute(
        select(func.count(User.id)).where(
            User.notice_preference == NoticePreference.PRINT,
            User.role == UserRole.PATRON,
        )
    )
    print_patrons = print_patrons_result.scalar() or 0

    return {
        "pending_notices": pending_count,
        "open_batches": open_batches,
        "ready_to_mail": ready_to_mail,
        "returned_this_month": returned_this_month,
        "total_cost_this_month": float(total_cost_this_month),
        "patrons_requiring_print": print_patrons,
    }
