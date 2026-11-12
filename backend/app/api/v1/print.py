# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Print Management API Routes

Endpoints for print job submission, release, payment processing, quota management,
and staff printer management.
"""
import os
import uuid
from decimal import Decimal
from typing import Optional, List

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

from ...core.database import get_db
from ...core.exceptions import InternalServerError
from ...core.error_codes import ErrorCode
from ...core.file_validation import validate_file_type, validate_file_size, extract_page_count
from .dependencies import require_staff, require_admin, get_current_user
from ...models.user import User

logger = get_logger(__name__)
from ...models.print import (
    PrintJob, Printer, PrintQuota, PrintRefund, PrinterAlert,
    PrintJobStatus, ColorMode, PrintReleaseStation, ScanToEmail
)
from ...services.print_service import PrintService
from ...services.printer_management_service import PrinterManagementService
from ...services.print_cost_service import calculate_cost
from ...services import print_release_service
from ...schemas.printing import (
    PrintJobCreateRequest, PrintJobUpdateRequest,
    PrintJobResponse as NewPrintJobResponse, PrintJobListResponse,
    PrintCostEstimate, PrintReleaseRequest as NewPrintReleaseRequest,
    PrinterResponse as NewPrinterResponse, PrinterListResponse,
    PrintPreviewResponse,
)
from pydantic import BaseModel
from datetime import datetime
from .dependencies import is_staff_or_admin

router = APIRouter(prefix="/print", tags=["print"])


# ============================================================================
# Schemas
# ============================================================================

class PrintJobSubmitRequest(BaseModel):
    job_name: str
    pages: int
    copies: int = 1
    color_mode: str = "blackwhite"
    double_sided: bool = True
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    device_type: Optional[str] = None


class PrintJobResponse(BaseModel):
    id: int
    job_name: str
    job_uid: str
    status: str
    pages: int
    copies: int
    color_mode: str
    cost: float
    cost_breakdown: dict
    submitted_at: datetime
    payment_processed: bool
    release_code: Optional[str] = None

    class Config:
        from_attributes = True


class PrintPaymentRequest(BaseModel):
    job_id: int
    payment_method: str  # 'card', 'cash', 'account_balance'
    payment_reference: Optional[str] = None
    account_balance_used: float = 0.0


class PrintReleaseRequest(BaseModel):
    job_id: int
    release_station_id: int
    card_number_last_4: Optional[str] = None


class PrintRefundRequest(BaseModel):
    job_id: int
    reason: str
    refund_method: str = "account_credit"  # 'card', 'cash', 'account_credit'
    description: Optional[str] = None


class PrintQuotaResponse(BaseModel):
    user_id: int
    monthly_pages_limit: int
    monthly_dollar_limit: float
    pages_used_this_month: int
    cost_incurred_this_month: float
    pages_remaining: int
    budget_remaining: float

    class Config:
        from_attributes = True


class PrinterResponse(BaseModel):
    id: int
    name: str
    location: str
    printer_type: str
    status: str
    is_enabled: bool
    black_toner_level: Optional[float]
    paper_level: Optional[float]

    class Config:
        from_attributes = True


class PrinterAlertResponse(BaseModel):
    id: int
    printer_id: int
    printer_name: str
    printer_location: str
    alert_type: str
    severity: str
    message: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Print Job Submission
# ============================================================================

@router.post("/submit", response_model=PrintJobResponse)
async def submit_print_job(
    request: PrintJobSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a new print job"""
    service = PrintService(db)

    try:
        job = await service.submit_print_job(
            user_id=current_user.id,
            job_name=request.job_name,
            pages=request.pages,
            copies=request.copies,
            color_mode=ColorMode(request.color_mode),
            double_sided=request.double_sided,
            device_id=request.device_id,
            device_name=request.device_name,
            device_type=request.device_type,
        )

        # Generate release code
        release_code = await service.generate_release_code(job.id)
        job.release_code = release_code

        return PrintJobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Error submitting print job")
        raise InternalServerError(code=ErrorCode.INTERNAL_ERROR) from None


@router.get("/jobs/{job_id}", response_model=PrintJobResponse)
async def get_print_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific print job"""
    service = PrintService(db)
    job = await service.get_print_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")

    # Verify ownership
    if job.user_id and job.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    return PrintJobResponse.model_validate(job)


@router.get("/my-jobs", response_model=List[PrintJobResponse])
async def get_my_print_jobs(
    status: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's print jobs"""
    service = PrintService(db)

    job_status = PrintJobStatus(status) if status else None
    jobs, _ = await service.get_user_print_jobs(
        user_id=current_user.id,
        status=job_status,
        limit=limit,
        offset=offset,
    )

    return [PrintJobResponse.model_validate(job) for job in jobs]


# ============================================================================
# Print Queue & Release
# ============================================================================

@router.get("/queue")
async def get_print_queue(
    printer_id: Optional[int] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get the current print queue"""
    service = PrintService(db)
    jobs = await service.get_print_queue(printer_id=printer_id)

    return {
        "queue_size": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "job_name": job.job_name,
                "pages": job.pages,
                "copies": job.copies,
                "color_mode": str(job.color_mode),
                "submitted_at": job.submitted_at.isoformat(),
            }
            for job in jobs
        ],
    }


@router.post("/release")
async def release_print_job(
    request: PrintReleaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Release a held print job at a release station"""
    service = PrintService(db)

    try:
        job = await service.release_print_job(
            job_id=request.job_id,
            release_station_id=request.release_station_id,
            card_number_last_4=request.card_number_last_4,
        )

        return {
            "success": True,
            "message": "Print job released",
            "job_id": job.id,
            "released_at": job.released_at.isoformat(),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/release-station/{station_id}")
async def get_release_station(
    station_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get release station information (public endpoint)"""
    from sqlalchemy import select
    result = await db.execute(
        select(PrintReleaseStation).filter(PrintReleaseStation.id == station_id)
    )
    station = result.scalar_one_or_none()

    if not station or not station.is_active:
        raise HTTPException(status_code=404, detail="Release station not found")

    return {
        "id": station.id,
        "name": station.name,
        "location": station.location,
        "card_reader_type": station.card_reader_type,
        "has_display": station.has_display,
        "has_cash_payment": station.has_cash_payment,
        "has_card_payment": station.has_card_payment,
        "use_pin_code": station.use_pin_code,
    }


@router.post("/release-station/{station_id}/heartbeat")
async def release_station_heartbeat(  # noqa: role-check -- public release-station heartbeat (station_id only)
    station_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Record heartbeat from a release station"""
    service = PrinterManagementService(db)

    try:
        station = await service.heartbeat_release_station(station_id)
        return {"success": True, "is_online": station.is_online}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============================================================================
# Payment
# ============================================================================

@router.post("/pay")
async def process_print_payment(
    request: PrintPaymentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Process payment for a print job"""
    service = PrintService(db)

    try:
        job = await service.get_print_job(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Print job not found")

        # Verify ownership
        if job.user_id != current_user.id and not is_staff_or_admin(current_user):
            raise HTTPException(status_code=403, detail="Access denied")

        # Process payment
        job = await service.process_payment(
            job_id=request.job_id,
            payment_method=request.payment_method,
            payment_reference=request.payment_reference,
            account_balance_used=Decimal(str(request.account_balance_used)),
        )

        return {
            "success": True,
            "message": "Payment processed",
            "job_id": job.id,
            "amount_charged": float(job.payment_amount_charged),
            "payment_method": job.payment_method,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Quota Management
# ============================================================================

@router.get("/quota", response_model=PrintQuotaResponse)
async def get_print_quota(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's print quota"""
    service = PrintService(db)
    quota = await service.get_user_quota(current_user.id)

    return PrintQuotaResponse.model_validate(quota)


@router.post("/quota/reset")
async def reset_monthly_quotas(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Reset all monthly print quotas (admin only)"""
    service = PrintService(db)
    count = await service.reset_monthly_quotas()

    return {
        "success": True,
        "message": f"Reset quotas for {count} users",
        "reset_count": count,
    }


# ============================================================================
# Refunds
# ============================================================================

@router.post("/refund")
async def request_print_refund(
    request: PrintRefundRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request a refund for a failed print"""
    service = PrintService(db)

    try:
        job = await service.get_print_job(request.job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Print job not found")

        # Verify ownership
        if job.user_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied")

        refund = await service.create_refund_request(
            job_id=request.job_id,
            reason=request.reason,
            refund_method=request.refund_method,
            description=request.description,
        )

        return {
            "success": True,
            "message": "Refund request created",
            "refund_id": refund.id,
            "refund_amount": float(refund.refund_amount),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# ============================================================================
# Printer Management (Staff)
# ============================================================================

@router.get("/printers", response_model=List[PrinterResponse])
async def list_printers(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all available printers"""
    service = PrinterManagementService(db)
    printers = await service.get_all_printers(only_enabled=True)

    return [PrinterResponse.model_validate(p) for p in printers]


@router.post("/printers")
async def register_printer(
    name: str = Form(...),
    printer_type: str = Form(...),
    location: str = Form(...),
    model: Optional[str] = Form(None),
    ipp_endpoint: Optional[str] = Form(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Register a new printer (staff only)"""
    service = PrinterManagementService(db)

    try:
        printer = await service.register_printer(
            name=name,
            printer_type=printer_type,
            location=location,
            model=model,
            ipp_endpoint=ipp_endpoint,
        )

        return PrinterResponse.model_validate(printer)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/printers/{printer_id}/stats")
async def get_printer_statistics(
    printer_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get printer usage statistics (staff only)"""
    service = PrinterManagementService(db)

    try:
        stats = await service.get_printer_statistics(printer_id)
        return stats
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============================================================================
# Printer Alerts (Staff)
# ============================================================================

@router.get("/alerts", response_model=List[PrinterAlertResponse])
async def get_printer_alerts(
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get all unresolved printer alerts (staff only)"""
    service = PrinterManagementService(db)
    alerts = await service.get_alerts_for_staff()

    return alerts


@router.post("/alerts/{alert_id}/resolve")
async def resolve_printer_alert(
    alert_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Mark a printer alert as resolved (staff only)"""
    service = PrinterManagementService(db)

    try:
        alert = await service.resolve_alert(
            alert_id=alert_id,
            resolved_by_id=current_user.id,
        )

        return {
            "success": True,
            "message": "Alert resolved",
            "alert_id": alert.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ============================================================================
# Enhanced Endpoints (using proper schemas and services)
# ============================================================================

MAX_PAGES_PER_JOB = 500
UPLOAD_DIR = "/app/uploads/print_jobs"


@router.post("/jobs", response_model=NewPrintJobResponse, status_code=201)
async def create_print_job(
    file: UploadFile = File(...),
    job_name: str = Form(..., min_length=1, max_length=255),
    copies: int = Form(1, ge=1, le=100),
    color_mode: str = Form("blackwhite"),
    paper_size: str = Form("letter"),
    double_sided: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file and create a new print job."""
    service = PrintService(db)

    try:
        # Read file content
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")

        # Validate file type by magic bytes
        mime_type = validate_file_type(content[:16], file.filename or "upload")
        if not mime_type:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file type. Allowed: PDF, PNG, JPG, GIF, WebP"
            )

        # Validate file size
        if not validate_file_size(len(content), 'print'):
            raise HTTPException(status_code=400, detail="File exceeds 25MB limit")

        # Extract page count
        pages = extract_page_count(content, mime_type)
        if pages is None:
            raise HTTPException(
                status_code=400,
                detail="Could not determine page count from file"
            )

        if pages > MAX_PAGES_PER_JOB:
            raise HTTPException(
                status_code=400,
                detail=f"File has {pages} pages, maximum is {MAX_PAGES_PER_JOB}"
            )

        # Save file to disk
        ext = os.path.splitext(file.filename or "upload")[1].lower() or ".bin"
        job_uid = str(uuid.uuid4())
        user_dir = os.path.join(UPLOAD_DIR, str(current_user.id))
        os.makedirs(user_dir, exist_ok=True)
        file_path = os.path.join(user_dir, f"{job_uid}{ext}")

        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)

        # Create print job
        job = await service.submit_print_job(
            user_id=current_user.id,
            job_name=job_name,
            pages=pages,
            copies=copies,
            color_mode=ColorMode(color_mode),
            double_sided=double_sided,
            file_path=file_path,
            file_mime_type=mime_type,
        )

        # Store file size on the job
        job.file_size_bytes = len(content)
        await db.commit()
        await db.refresh(job)

        # Generate release code
        release_code = await service.generate_release_code(job.id)
        job.release_code = release_code

        return NewPrintJobResponse.model_validate(job)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception:
        logger.exception("Error creating print job")
        raise InternalServerError(code=ErrorCode.INTERNAL_ERROR) from None


@router.get("/jobs", response_model=PrintJobListResponse)
async def list_print_jobs(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List patron's print jobs with pagination"""
    service = PrintService(db)

    job_status = PrintJobStatus(status) if status else None
    offset = (page - 1) * per_page
    jobs, total = await service.get_user_print_jobs(
        user_id=current_user.id,
        status=job_status,
        limit=per_page,
        offset=offset,
    )

    return PrintJobListResponse(
        items=[NewPrintJobResponse.model_validate(job) for job in jobs],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.delete("/jobs/{job_id}")
async def cancel_print_job(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a print job"""
    service = PrintService(db)
    job = await service.get_print_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")

    # Verify ownership
    if job.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        job = await service.cancel_job(job_id)
        return {
            "success": True,
            "message": "Print job cancelled",
            "job_id": job.id,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.patch("/jobs/{job_id}", response_model=NewPrintJobResponse)
async def update_print_job(
    job_id: int,
    request: PrintJobUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update print job settings before release"""
    service = PrintService(db)
    job = await service.get_print_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")

    # Verify ownership
    if job.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    # Only allow updates on jobs that haven't started printing
    if job.status not in (PrintJobStatus.submitted, PrintJobStatus.held, PrintJobStatus.queued):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot update job with status '{job.status}'"
        )

    # Apply updates
    update_data = request.model_dump(exclude_unset=True)
    if "copies" in update_data:
        job.copies = update_data["copies"]
    if "color_mode" in update_data:
        job.color_mode = ColorMode(update_data["color_mode"])
    if "paper_size" in update_data:
        from ...models.print import PaperSize
        job.paper_size = PaperSize(update_data["paper_size"])
    if "double_sided" in update_data:
        job.double_sided = update_data["double_sided"]

    # Recalculate cost with updated settings
    cost_result = await calculate_cost(
        db,
        pages=job.pages,
        copies=job.copies,
        color_mode=job.color_mode.value if hasattr(job.color_mode, 'value') else job.color_mode,
        double_sided=job.double_sided,
        device_type=job.device_type,
    )
    job.cost = cost_result["total"]
    job.cost_breakdown = cost_result

    await db.commit()
    await db.refresh(job)

    return NewPrintJobResponse.model_validate(job)


@router.get("/jobs/{job_id}/preview", response_model=PrintPreviewResponse)
async def get_print_job_preview(
    job_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get preview for a print job"""
    service = PrintService(db)
    job = await service.get_print_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Print job not found")

    # Verify ownership
    if job.user_id and job.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Access denied")

    return PrintPreviewResponse(
        job_id=job.id,
        preview_url=job.preview_image_path,
        page_count=job.pages,
        file_type=job.file_mime_type,
    )


@router.post("/release/{job_id}", response_model=NewPrintJobResponse)
async def release_job_to_printer(
    job_id: int,
    request: NewPrintReleaseRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Release a print job to the printer after payment"""
    try:
        job = await print_release_service.release_job(
            db=db,
            job_id=job_id,
            patron_id=current_user.id,
            payment_method=request.payment_method,
        )
        return NewPrintJobResponse.model_validate(job)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error releasing print job")
        raise InternalServerError(code=ErrorCode.INTERNAL_ERROR) from None


@router.post("/cost-estimate", response_model=PrintCostEstimate)
async def estimate_print_cost(
    pages: int = Query(..., gt=0),
    copies: int = Query(1, ge=1, le=100),
    color_mode: str = Query("blackwhite", pattern="^(blackwhite|color)$"),
    double_sided: bool = Query(True),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculate cost estimate for a print job"""
    result = await calculate_cost(
        db=db,
        pages=pages,
        copies=copies,
        color_mode=color_mode,
        double_sided=double_sided,
    )

    return PrintCostEstimate(**result)
