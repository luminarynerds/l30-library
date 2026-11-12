# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Makerspace resource management API routes.

Public endpoints for patrons to:
- Browse available resources
- Make reservations
- Submit jobs to the queue
- View their certifications
"""

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination_config import PaginationDefaults
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.makerspace import (
    ResourceType, ResourceStatus, MakerspaceReservationStatus, JobStatus,
    CertificationStatus, PaymentStatus, MakerspaceWaitlistStatus, WorkshopStatus,
    MakerspaceRegistrationStatus, MakerspaceWaitlist, MakerspaceWorkshop, WorkshopRegistration,
    MakerspaceResource, MakerspaceCertificationType, MakerspaceCertification,
    MakerspaceJob
)
from ...models.user import User, UserRole
from ...schemas.common import PaginationInfo
from ...schemas.makerspace import (
    MakerspaceResourceResponse, MakerspaceResourceSummary,
    CertificationTypeResponse, CertificationResponse, CertificationWithDetails,
    QuizSubmission, QuizResult,
    ReservationCreate, ReservationResponse, ReservationWithDetails,
    AvailabilityResponse, TimeSlot,
    JobCreate, JobResponse, JobWithDetails,
    CostEstimate, CostCalculationRequest, ConsumableUsageCreate,
    PaginatedMakerspaceResourceSummaryResponse,
    PaginatedReservationWithDetailsResponse,
    PaginatedJobWithDetailsResponse,
    QueueJobItem, QueueStatusResponse,
    # New schemas for waitlist, workshops, and operating hours
    ResourceOperatingHours, DynamicAvailabilityResponse, DynamicTimeSlot,
    WaitlistCreate, WaitlistResponse, WaitlistWithDetails, WaitlistPositionResponse,
    WorkshopSummary, WorkshopResponse, WorkshopWithDetails,
    WorkshopRegistrationCreate, WorkshopRegistrationResponse, MyWorkshopRegistration,
    PaginatedWorkshopSummaryResponse,
    WorkshopStatus as WorkshopStatusSchema,
    WorkshopLevel,
)
from ...services.makerspace_service import (
    MakerspaceResourceService, CertificationService,
    ReservationService, JobQueueService, MakerspacePaymentService
)
from ...services.makerspace.certification_service import QUIZ_MAX_ATTEMPTS
from .auth import get_current_user, get_current_user_optional
from .dependencies import is_staff_or_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/makerspace", tags=["makerspace"])


# =============================================================================
# Resource Endpoints
# =============================================================================

@router.get("/resources", response_model=PaginatedMakerspaceResourceSummaryResponse)
@limiter.limit("60/minute")
async def list_resources(
    request: Request,
    resource_type: ResourceType | None = Query(None),
    status: ResourceStatus | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List all available makerspace resources."""
    resources, total = await MakerspaceResourceService.get_all(
        db,
        resource_type=resource_type,
        status=status,
        is_active=True,
        page=page,
        per_page=per_page
    )

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return PaginatedMakerspaceResourceSummaryResponse(
        data=[MakerspaceResourceSummary.model_validate(r) for r in resources],
        pagination=PaginationInfo(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    )


@router.get("/resources/{resource_id}", response_model=MakerspaceResourceResponse)
@limiter.limit("120/minute")
async def get_resource(
    request: Request,
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific resource."""
    resource = await MakerspaceResourceService.get_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    if not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    return MakerspaceResourceResponse.model_validate(resource)


@router.get("/resources/{resource_id}/availability", response_model=AvailabilityResponse)
@limiter.limit("120/minute")
async def get_resource_availability(
    request: Request,
    resource_id: int,
    target_date: date = Query(..., description="Date to check availability"),
    slot_duration_minutes: int = Query(60, ge=15, le=480),
    db: AsyncSession = Depends(get_db),
):
    """Get available time slots for a resource on a given date."""
    resource = await MakerspaceResourceService.get_by_id(db, resource_id)
    if not resource or not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    slots = await MakerspaceResourceService.get_availability(
        db, resource_id, target_date, slot_duration_minutes
    )

    return AvailabilityResponse(
        resource_id=resource_id,
        date=target_date,
        slots=[TimeSlot(**s) for s in slots]
    )


@router.get("/resource-types", response_model=list[dict])
@limiter.limit("60/minute")
async def list_resource_types(request: Request):
    """Get all available resource types."""
    return [
        {"value": t.value, "label": t.name.replace("_", " ").title()}
        for t in ResourceType
    ]


# =============================================================================
# Certification Endpoints
# =============================================================================

@router.get("/certifications/types", response_model=list[CertificationTypeResponse])
@limiter.limit("60/minute")
async def list_certification_types(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """List all available certification types."""
    cert_types = await CertificationService.get_certification_types(db)
    return [CertificationTypeResponse.model_validate(ct) for ct in cert_types]


@router.get("/certifications/types/{type_id}", response_model=CertificationTypeResponse)
@limiter.limit("120/minute")
async def get_certification_type(
    request: Request,
    type_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a certification type."""
    cert_type = await CertificationService.get_certification_type_by_id(db, type_id)
    if not cert_type or not cert_type.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification type not found")

    return CertificationTypeResponse.model_validate(cert_type)


@router.get("/my/certifications", response_model=list[CertificationWithDetails])
@limiter.limit("60/minute")
async def get_my_certifications(
    request: Request,
    status: CertificationStatus | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's certifications."""
    certifications = await CertificationService.get_user_certifications(
        db, current_user.id, status
    )

    results = []
    for cert in certifications:
        cert_dict = CertificationResponse.model_validate(cert).model_dump()
        cert_dict["certification_type_name"] = (
            cert.certification_type.name if cert.certification_type else None
        )
        cert_dict["user_name"] = current_user.full_name
        results.append(CertificationWithDetails(**cert_dict))

    return results


@router.post("/certifications/enroll/{type_id}", response_model=CertificationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def enroll_in_certification(
    request: Request,
    type_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enroll in a certification program."""
    cert_type = await CertificationService.get_certification_type_by_id(db, type_id)
    if not cert_type or not cert_type.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification type not found")

    try:
        certification = await CertificationService.start_certification(
            db, current_user.id, type_id
        )
        return CertificationResponse.model_validate(certification)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/certifications/{certification_id}/complete-training", response_model=CertificationResponse)
@limiter.limit("10/minute")
async def complete_training(
    request: Request,
    certification_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark training as completed (self-paced)."""
    certification = await CertificationService.get_certification(db, certification_id)
    if not certification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")

    if certification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if certification.status != CertificationStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certification is not pending")

    certification = await CertificationService.complete_training(db, certification)
    return CertificationResponse.model_validate(certification)


@router.post("/certifications/{certification_id}/submit-quiz", response_model=QuizResult)
@limiter.limit("10/minute")
async def submit_quiz(
    request: Request,
    certification_id: int,
    submission: QuizSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit quiz answers for certification."""
    certification = await CertificationService.get_certification(db, certification_id)
    if not certification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")

    if certification.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if certification.status != CertificationStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Certification is not pending")

    if not certification.training_completed_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Training must be completed first")

    # For demo purposes, calculate a score based on answers
    # In production, this would verify against actual quiz questions
    score = min(100, len(submission.answers) * 10)  # Placeholder

    certification, passed = await CertificationService.submit_quiz(db, certification, score)

    cert_type = await CertificationService.get_certification_type_by_id(
        db, certification.certification_type_id
    )
    passing_score = cert_type.passing_score if cert_type else 80

    if passed:
        feedback = {"message": "Congratulations! Certification complete."}
    elif certification.status == CertificationStatus.expired:
        feedback = {
            "message": "You have used all quiz attempts. Contact staff to re-enroll.",
            "attempts_remaining": 0,
        }
    else:
        attempts_remaining = max(0, QUIZ_MAX_ATTEMPTS - certification.quiz_attempts)
        feedback = {
            "message": f"Not quite — {attempts_remaining} attempt(s) remaining. Review the material and try again.",
            "attempts_remaining": attempts_remaining,
        }

    return QuizResult(
        score=score,
        passed=passed,
        passing_score=passing_score,
        feedback=feedback,
    )


# =============================================================================
# Reservation Endpoints
# =============================================================================

@router.get("/my/reservations", response_model=PaginatedReservationWithDetailsResponse)
@limiter.limit("60/minute")
async def get_my_reservations(
    request: Request,
    status: MakerspaceReservationStatus | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's reservations."""
    reservations, total = await ReservationService.get_reservations(
        db,
        user_id=current_user.id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page
    )

    items = []
    for r in reservations:
        r_dict = ReservationResponse.model_validate(r).model_dump()
        r_dict["user_name"] = current_user.full_name
        r_dict["user_email"] = current_user.email
        r_dict["resource_name"] = r.resource.name if r.resource else None
        r_dict["resource_type"] = r.resource.resource_type if r.resource else None
        items.append(ReservationWithDetails(**r_dict))

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return PaginatedReservationWithDetailsResponse(
        data=items,
        pagination=PaginationInfo(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    )


@router.post("/reservations", response_model=ReservationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def create_reservation(
    request: Request,
    reservation_data: ReservationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reservation."""
    try:
        reservation = await ReservationService.create(
            db,
            user_id=current_user.id,
            resource_id=reservation_data.resource_id,
            start_time=reservation_data.start_time,
            end_time=reservation_data.end_time,
            project_name=reservation_data.project_name,
            project_description=reservation_data.project_description,
            notes=reservation_data.notes
        )

        logger.info(f"Reservation created: {reservation.id} by user {current_user.id}")

        # Send reservation confirmation notification
        try:
            from ...services.makerspace_notification_service import MakerspaceNotificationService
            reservation.user = current_user
            await MakerspaceNotificationService.notify_reservation_created(db, reservation)
        except Exception as e:  # noqa: BLE001  # best-effort notification — reservation already created
            logger.warning(f"Failed to send reservation notification: {e}")

        return ReservationResponse.model_validate(reservation)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/reservations/{reservation_id}", response_model=ReservationWithDetails)
@limiter.limit("120/minute")
async def get_reservation(
    request: Request,
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific reservation."""
    reservation = await ReservationService.get_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    # Only allow user to see their own reservations (or staff)
    if reservation.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    r_dict = ReservationResponse.model_validate(reservation).model_dump()
    r_dict["user_name"] = reservation.user.full_name if reservation.user else None
    r_dict["user_email"] = reservation.user.email if reservation.user else None
    r_dict["resource_name"] = reservation.resource.name if reservation.resource else None
    r_dict["resource_type"] = (
        reservation.resource.resource_type if reservation.resource else None
    )

    return ReservationWithDetails(**r_dict)


@router.delete("/reservations/{reservation_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def cancel_reservation(
    request: Request,
    reservation_id: int,
    reason: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a reservation."""
    reservation = await ReservationService.get_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    if reservation.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    try:
        await ReservationService.cancel(db, reservation, current_user.id, reason)
        logger.info(f"Reservation {reservation_id} cancelled by user {current_user.id}")
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Job Queue Endpoints
# =============================================================================

@router.get("/my/jobs", response_model=PaginatedJobWithDetailsResponse)
@limiter.limit("60/minute")
async def get_my_jobs(
    request: Request,
    status: JobStatus | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's jobs."""
    jobs, total = await JobQueueService.get_jobs(
        db,
        user_id=current_user.id,
        status=status,
        page=page,
        per_page=per_page
    )

    items = []
    for job in jobs:
        j_dict = JobResponse.model_validate(job).model_dump()
        j_dict["user_name"] = current_user.full_name
        j_dict["user_email"] = current_user.email
        j_dict["resource_name"] = job.resource.name if job.resource else None
        items.append(JobWithDetails(**j_dict))

    total_pages = (total + per_page - 1) // per_page if per_page > 0 else 0
    return PaginatedJobWithDetailsResponse(
        data=items,
        pagination=PaginationInfo(
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
    )


@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def submit_job(
    request: Request,
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Submit a new job to the queue."""
    # Check certification if resource requires it
    if job_data.resource_id:
        resource = await MakerspaceResourceService.get_by_id(db, job_data.resource_id)
        if resource and resource.requires_certification and resource.certification_type_id:
            is_certified = await CertificationService.check_user_certified(
                db, current_user.id, resource.certification_type_id
            )
            if not is_certified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Certification required to use this equipment"
                )

    job = await JobQueueService.submit(
        db,
        user_id=current_user.id,
        data=job_data.model_dump(exclude_unset=True)
    )

    logger.info(f"Job {job.job_number} submitted by user {current_user.id}")

    # Send job submission notification
    try:
        from ...services.makerspace_notification_service import MakerspaceNotificationService
        job.user = current_user
        await MakerspaceNotificationService.notify_job_submitted(db, job)
    except Exception as e:  # noqa: BLE001  # best-effort notification — job already submitted
        logger.warning(f"Failed to send job submission notification: {e}")

    return JobResponse.model_validate(job)


@router.post("/jobs/upload")
@limiter.limit("5/minute")
async def upload_job_file(
    request: Request,
    job_id: int = Query(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a file for a job."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if job.status != JobStatus.submitted:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot upload file for this job")

    # Validate file type
    allowed_extensions = [".stl", ".obj", ".gcode", ".3mf", ".svg", ".dxf"]
    file_ext = "." + file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_extensions)}"
        )

    # Read and validate file size
    MAX_MAKERSPACE_UPLOAD_SIZE = 100 * 1024 * 1024  # 100 MB
    content = await file.read()
    if len(content) > MAX_MAKERSPACE_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size is {MAX_MAKERSPACE_UPLOAD_SIZE // (1024 * 1024)} MB",
        )
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    # SECURITY: Sanitize filename to prevent path traversal attacks.
    # file.filename is user-controlled and could contain ../../ sequences.
    from pathlib import Path as FilePath
    import os
    safe_filename = FilePath(file.filename).name  # strips directory components
    if not safe_filename or safe_filename.startswith('.'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    upload_dir = f"/tmp/makerspace_uploads/{job.job_number}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, safe_filename)

    # Verify resolved path stays within upload directory
    resolved = os.path.realpath(file_path)
    if not resolved.startswith(os.path.realpath(upload_dir) + os.sep):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid filename",
        )

    import aiofiles
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    # Update job with file info
    job.file_name = safe_filename
    job.file_path = file_path
    job.file_size_bytes = len(content)
    job.file_format = file_ext
    job.status = JobStatus.pending_review

    await db.commit()

    logger.info(
        "Upload audit: user_id=%s filename=%s size=%s format=%s job_id=%s timestamp=%s",
        current_user.id,
        safe_filename,
        len(content),
        file_ext,
        job.id,
        datetime.now(timezone.utc).isoformat(),
    )
    return {
        "message": "File uploaded successfully",
        "file_name": safe_filename,
        "file_size": len(content)
    }


@router.get("/jobs/{job_id}", response_model=JobWithDetails)
@limiter.limit("120/minute")
async def get_job(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific job."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    j_dict = JobResponse.model_validate(job).model_dump()
    j_dict["user_name"] = job.user.full_name if job.user else None
    j_dict["user_email"] = job.user.email if job.user else None
    j_dict["resource_name"] = job.resource.name if job.resource else None

    return JobWithDetails(**j_dict)


@router.get("/jobs/number/{job_number}", response_model=JobWithDetails)
@limiter.limit("120/minute")
async def get_job_by_number(
    request: Request,
    job_number: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a job by job number."""
    job = await JobQueueService.get_by_job_number(db, job_number)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.user_id != current_user.id and not is_staff_or_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    j_dict = JobResponse.model_validate(job).model_dump()
    j_dict["user_name"] = job.user.full_name if job.user else None
    j_dict["user_email"] = job.user.email if job.user else None
    j_dict["resource_name"] = job.resource.name if job.resource else None

    return JobWithDetails(**j_dict)


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def cancel_job(
    request: Request,
    job_id: int,
    reason: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a job."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if job.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    try:
        await JobQueueService.cancel_job(db, job, reason)
        logger.info(f"Job {job.job_number} cancelled by user {current_user.id}")
        return None
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Cost Calculation Endpoints
# =============================================================================

@router.post("/calculate-cost", response_model=CostEstimate)
@limiter.limit("60/minute")
async def calculate_cost(  # noqa: role-check -- public cost estimator, rate-limited
    request: Request,
    cost_request: CostCalculationRequest,
    db: AsyncSession = Depends(get_db),
):
    """Calculate the cost for using a resource."""
    try:
        consumables = None
        if cost_request.consumables:
            consumables = [c.model_dump() for c in cost_request.consumables]

        result = await MakerspacePaymentService.calculate_cost(
            db,
            resource_id=cost_request.resource_id,
            duration_hours=cost_request.duration_hours,
            consumables=consumables
        )
        return CostEstimate(**result)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Queue Status (Public)
# =============================================================================

@router.get("/queue", response_model=QueueStatusResponse)
@limiter.limit("60/minute")
async def get_queue_status(
    request: Request,
    resource_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Get the current job queue status (public view)."""
    jobs = await JobQueueService.get_queue(db, resource_id)

    # Return limited info for public view
    queue = []
    for i, job in enumerate(jobs):
        queue.append(QueueJobItem(
            position=i + 1,
            job_number=job.job_number,
            status=job.status.value,
            estimated_time_minutes=job.estimated_print_time_minutes,
            resource_name=job.resource.name if job.resource else None,
            submitted_at=job.created_at.isoformat() if job.created_at else None
        ))

    return QueueStatusResponse(
        queue=queue,
        total_jobs=len(queue)
    )


# =============================================================================
# Operating Hours & Dynamic Availability Endpoints
# =============================================================================

@router.get("/resources/{resource_id}/operating-hours", response_model=ResourceOperatingHours)
@limiter.limit("120/minute")
async def get_resource_operating_hours(
    request: Request,
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get the operating hours for a specific resource."""
    resource = await MakerspaceResourceService.get_by_id(db, resource_id)
    if not resource or not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    return ResourceOperatingHours(
        resource_id=resource.id,
        resource_name=resource.name,
        available_from=resource.available_from,
        available_until=resource.available_until,
        available_days=resource.available_days,
        buffer_minutes=resource.buffer_minutes,
        min_reservation_hours=resource.min_reservation_hours,
        max_reservation_hours=resource.max_reservation_hours
    )


@router.get("/resources/{resource_id}/dynamic-availability", response_model=DynamicAvailabilityResponse)
@limiter.limit("120/minute")
async def get_dynamic_availability(
    request: Request,
    resource_id: int,
    target_date: date = Query(..., description="Date to check availability"),
    slot_duration_minutes: int = Query(60, ge=15, le=480),
    db: AsyncSession = Depends(get_db),
):
    """
    Get dynamically generated time slots based on the resource's operating hours.

    This endpoint returns availability based on the actual operating hours
    configured for the resource, rather than fixed time slots.
    """
    from sqlalchemy import select, and_
    from ...models.makerspace import MakerspaceReservation

    resource = await MakerspaceResourceService.get_by_id(db, resource_id)
    if not resource or not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    # Check if the resource is available on this day of week
    day_of_week = target_date.weekday()  # Monday = 0, Sunday = 6
    if day_of_week not in resource.available_days:
        return DynamicAvailabilityResponse(
            resource_id=resource.id,
            resource_name=resource.name,
            date=target_date,
            operating_hours=ResourceOperatingHours(
                resource_id=resource.id,
                resource_name=resource.name,
                available_from=resource.available_from,
                available_until=resource.available_until,
                available_days=resource.available_days,
                buffer_minutes=resource.buffer_minutes,
                min_reservation_hours=resource.min_reservation_hours,
                max_reservation_hours=resource.max_reservation_hours
            ),
            slots=[],
            waitlist_count=0
        )

    # Parse operating hours
    from datetime import timedelta
    open_hour, open_minute = map(int, resource.available_from.split(":"))
    close_hour, close_minute = map(int, resource.available_until.split(":"))

    start_dt = datetime.combine(target_date, datetime.min.time().replace(
        hour=open_hour, minute=open_minute, tzinfo=timezone.utc
    ))
    end_dt = datetime.combine(target_date, datetime.min.time().replace(
        hour=close_hour, minute=close_minute, tzinfo=timezone.utc
    ))

    # Get existing reservations for this date
    result = await db.execute(
        select(MakerspaceReservation)
        .where(MakerspaceReservation.resource_id == resource_id)
        .where(MakerspaceReservation.status.in_([
            MakerspaceReservationStatus.pending,
            MakerspaceReservationStatus.confirmed,
            MakerspaceReservationStatus.checked_in
        ]))
        .where(MakerspaceReservation.start_time >= start_dt)
        .where(MakerspaceReservation.end_time <= end_dt)
    )
    reservations = result.scalars().all()

    # Build reservation lookup by time
    reserved_slots = {}
    for res in reservations:
        reserved_slots[(res.start_time, res.end_time)] = res.id

    # Generate time slots
    slots = []
    current_time = start_dt
    slot_duration = timedelta(minutes=slot_duration_minutes)
    buffer = timedelta(minutes=resource.buffer_minutes)
    now = datetime.now(timezone.utc)

    while current_time + slot_duration <= end_dt:
        slot_end = current_time + slot_duration
        is_past = current_time < now

        # Check if this slot overlaps with any reservation
        is_available = True
        reservation_id = None

        for (res_start, res_end), res_id in reserved_slots.items():
            # Check for overlap
            if not (slot_end <= res_start or current_time >= res_end):
                is_available = False
                reservation_id = res_id
                break

        slots.append(DynamicTimeSlot(
            start_time=current_time,
            end_time=slot_end,
            is_available=is_available and not is_past,
            is_past=is_past,
            reservation_id=reservation_id
        ))

        current_time = slot_end + buffer if buffer.total_seconds() > 0 else slot_end

    # Get waitlist count
    waitlist_result = await db.execute(
        select(MakerspaceWaitlist)
        .where(MakerspaceWaitlist.resource_id == resource_id)
        .where(MakerspaceWaitlist.preferred_date == target_date)
        .where(MakerspaceWaitlist.status == MakerspaceWaitlistStatus.waiting)
    )
    waitlist_count = len(waitlist_result.scalars().all())

    return DynamicAvailabilityResponse(
        resource_id=resource.id,
        resource_name=resource.name,
        date=target_date,
        operating_hours=ResourceOperatingHours(
            resource_id=resource.id,
            resource_name=resource.name,
            available_from=resource.available_from,
            available_until=resource.available_until,
            available_days=resource.available_days,
            buffer_minutes=resource.buffer_minutes,
            min_reservation_hours=resource.min_reservation_hours,
            max_reservation_hours=resource.max_reservation_hours
        ),
        slots=slots,
        waitlist_count=waitlist_count
    )


# =============================================================================
# Waitlist Endpoints
# =============================================================================

@router.get("/my/waitlist", response_model=list[WaitlistWithDetails])
@limiter.limit("60/minute")
async def get_my_waitlist_entries(
    request: Request,
    status_filter: MakerspaceWaitlistStatus | None = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's waitlist entries."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    query = select(MakerspaceWaitlist).options(
        selectinload(MakerspaceWaitlist.resource)
    ).where(MakerspaceWaitlist.user_id == current_user.id)

    if status_filter:
        query = query.where(MakerspaceWaitlist.status == status_filter)

    query = query.order_by(MakerspaceWaitlist.id.desc())

    result = await db.execute(query)
    entries = result.scalars().all()

    return [
        WaitlistWithDetails(
            **WaitlistResponse.model_validate(e).model_dump(),
            user_name=current_user.full_name,
            user_email=current_user.email,
            resource_name=e.resource.name if e.resource else None,
            resource_type=str(e.resource.resource_type) if e.resource else None
        )
        for e in entries
    ]


@router.post("/waitlist", response_model=WaitlistResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def join_waitlist(
    request: Request,
    waitlist_data: WaitlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Join the waitlist for a resource."""
    from sqlalchemy import select, func

    # Check resource exists
    resource = await MakerspaceResourceService.get_by_id(db, waitlist_data.resource_id)
    if not resource or not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    # Check if already on waitlist for this resource and date
    existing = await db.execute(
        select(MakerspaceWaitlist)
        .where(MakerspaceWaitlist.user_id == current_user.id)
        .where(MakerspaceWaitlist.resource_id == waitlist_data.resource_id)
        .where(MakerspaceWaitlist.preferred_date == waitlist_data.preferred_date)
        .where(MakerspaceWaitlist.status == MakerspaceWaitlistStatus.waiting)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already on waitlist for this resource and date"
        )

    # Get current position count
    position_result = await db.execute(
        select(func.count(MakerspaceWaitlist.id))
        .where(MakerspaceWaitlist.resource_id == waitlist_data.resource_id)
        .where(MakerspaceWaitlist.preferred_date == waitlist_data.preferred_date)
        .where(MakerspaceWaitlist.status == MakerspaceWaitlistStatus.waiting)
    )
    position = position_result.scalar() + 1

    # Create waitlist entry
    entry = MakerspaceWaitlist(
        user_id=current_user.id,
        resource_id=waitlist_data.resource_id,
        preferred_date=waitlist_data.preferred_date,
        preferred_start_time=waitlist_data.preferred_start_time,
        preferred_end_time=waitlist_data.preferred_end_time,
        flexible_dates=waitlist_data.flexible_dates,
        notify_email=waitlist_data.notify_email,
        notify_sms=waitlist_data.notify_sms,
        contact_phone=waitlist_data.contact_phone,
        notes=waitlist_data.notes,
        position=position,
        status=MakerspaceWaitlistStatus.waiting
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    # Send confirmation notification
    from ...services.makerspace_notification_service import MakerspaceNotificationService
    entry.user = current_user
    entry.resource = resource
    await MakerspaceNotificationService.notify_waitlist_joined(db, entry)

    logger.info(f"User {current_user.id} joined waitlist for resource {waitlist_data.resource_id}")
    return WaitlistResponse.model_validate(entry)


@router.get("/waitlist/{waitlist_id}/position", response_model=WaitlistPositionResponse)
@limiter.limit("120/minute")
async def get_waitlist_position(
    request: Request,
    waitlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current position in waitlist."""
    from sqlalchemy import select, func

    entry = await get_or_404(db, MakerspaceWaitlist, waitlist_id, "Waitlist entry not found")

    if entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    # Get total waiting for this resource and date
    total_result = await db.execute(
        select(func.count(MakerspaceWaitlist.id))
        .where(MakerspaceWaitlist.resource_id == entry.resource_id)
        .where(MakerspaceWaitlist.preferred_date == entry.preferred_date)
        .where(MakerspaceWaitlist.status == MakerspaceWaitlistStatus.waiting)
    )
    total = total_result.scalar()

    return WaitlistPositionResponse(
        waitlist_id=entry.id,
        position=entry.position or 1,
        total_waiting=total,
        estimated_wait=f"~{entry.position or 1}-{(entry.position or 1) + 2} days" if entry.position else None
    )


@router.delete("/waitlist/{waitlist_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def leave_waitlist(
    request: Request,
    waitlist_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Leave the waitlist."""
    from sqlalchemy import select

    entry = await get_or_404(db, MakerspaceWaitlist, waitlist_id, "Waitlist entry not found")

    if entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if entry.status not in [MakerspaceWaitlistStatus.waiting, MakerspaceWaitlistStatus.notified]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel this entry")

    entry.status = MakerspaceWaitlistStatus.cancelled
    await db.commit()

    logger.info(f"User {current_user.id} left waitlist entry {waitlist_id}")
    return None


# =============================================================================
# Workshop Endpoints
# =============================================================================

@router.get("/workshops", response_model=PaginatedWorkshopSummaryResponse)
@limiter.limit("60/minute")
async def list_workshops(
    request: Request,
    skill_level: WorkshopLevel | None = Query(None),
    is_certification_training: bool | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
):
    """List upcoming published workshops."""
    from sqlalchemy import select, func

    query = select(MakerspaceWorkshop).where(
        MakerspaceWorkshop.status == WorkshopStatus.published
    )

    if skill_level:
        query = query.where(MakerspaceWorkshop.skill_level == skill_level)

    if is_certification_training is not None:
        query = query.where(MakerspaceWorkshop.is_certification_training == is_certification_training)

    # Default to showing future workshops
    if start_date:
        query = query.where(MakerspaceWorkshop.start_time >= datetime.combine(
            start_date, datetime.min.time()
        ).replace(tzinfo=timezone.utc))
    else:
        query = query.where(MakerspaceWorkshop.start_time >= datetime.now(timezone.utc))

    if end_date:
        query = query.where(MakerspaceWorkshop.start_time <= datetime.combine(
            end_date, datetime.max.time()
        ).replace(tzinfo=timezone.utc))

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Add pagination and ordering
    query = query.order_by(MakerspaceWorkshop.start_time.asc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    workshops = result.scalars().all()

    items = []
    for w in workshops:
        spots_remaining = max(0, w.max_participants - w.current_participants)
        items.append(WorkshopSummary(
            id=w.id,
            title=w.title,
            short_description=w.short_description,
            start_time=w.start_time,
            end_time=w.end_time,
            location=w.location,
            is_virtual=w.is_virtual,
            skill_level=w.skill_level,
            fee=w.fee,
            max_participants=w.max_participants,
            current_participants=w.current_participants,
            spots_remaining=spots_remaining,
            is_full=spots_remaining == 0,
            has_waitlist=w.allow_waitlist and w.waitlist_count > 0,
            waitlist_count=w.waitlist_count,
            is_certification_training=w.is_certification_training,
            certification_type_id=w.certification_type_id,
            instructor_name=w.instructor_name,
            image_url=w.image_url,
            tags=w.tags,
            status=w.status
        ))

    return PaginatedWorkshopSummaryResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page
    )


@router.get("/workshops/{workshop_id}", response_model=WorkshopWithDetails)
@limiter.limit("120/minute")
async def get_workshop(
    request: Request,
    workshop_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific workshop."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    result = await db.execute(
        select(MakerspaceWorkshop)
        .options(
            selectinload(MakerspaceWorkshop.certification_type),
            selectinload(MakerspaceWorkshop.instructor),
            selectinload(MakerspaceWorkshop.room)
        )
        .where(MakerspaceWorkshop.id == workshop_id)
    )
    workshop = result.scalar_one_or_none()

    if not workshop:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop not found")

    if workshop.status == WorkshopStatus.draft:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workshop not found")

    spots_remaining = max(0, workshop.max_participants - workshop.current_participants)
    is_full = spots_remaining == 0

    # Check if registration is open
    now = datetime.now(timezone.utc)
    is_registration_open = (
        (workshop.registration_opens_at is None or workshop.registration_opens_at <= now) and
        (workshop.registration_closes_at is None or workshop.registration_closes_at > now) and
        workshop.start_time > now
    )

    response = WorkshopWithDetails(
        **WorkshopResponse.model_validate(workshop).model_dump(),
        certification_type_name=workshop.certification_type.name if workshop.certification_type else None,
        instructor_user_name=workshop.instructor.full_name if workshop.instructor else None,
        room_name=workshop.room.name if workshop.room else None,
        spots_remaining=spots_remaining,
        is_full=is_full,
        is_registration_open=is_registration_open
    )

    return response


@router.post("/workshops/{workshop_id}/register", response_model=WorkshopRegistrationResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/minute")
async def register_for_workshop(
    request: Request,
    workshop_id: int,
    registration_data: WorkshopRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register for a workshop."""
    from sqlalchemy import select, func

    # Get workshop
    workshop = await get_or_404(db, MakerspaceWorkshop, workshop_id, "Workshop not found")

    if workshop.status != WorkshopStatus.published:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workshop is not accepting registrations")

    # Check if registration is open
    now = datetime.now(timezone.utc)
    if workshop.registration_opens_at and workshop.registration_opens_at > now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration has not opened yet")

    if workshop.registration_closes_at and workshop.registration_closes_at < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Registration is closed")

    if workshop.start_time < now:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workshop has already started")

    # Check if already registered
    existing = await db.execute(
        select(WorkshopRegistration)
        .where(WorkshopRegistration.workshop_id == workshop_id)
        .where(WorkshopRegistration.user_id == current_user.id)
        .where(WorkshopRegistration.status.notin_([MakerspaceRegistrationStatus.cancelled]))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered for this workshop")

    # Check capacity
    is_full = workshop.current_participants >= workshop.max_participants
    is_waitlisted = False
    waitlist_position = None

    if is_full:
        if not workshop.allow_waitlist:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Workshop is full")
        is_waitlisted = True

        # Get waitlist position
        waitlist_count_result = await db.execute(
            select(func.count(WorkshopRegistration.id))
            .where(WorkshopRegistration.workshop_id == workshop_id)
            .where(WorkshopRegistration.status == MakerspaceRegistrationStatus.waitlisted)
        )
        waitlist_position = waitlist_count_result.scalar() + 1

    # Create registration
    registration = WorkshopRegistration(
        workshop_id=workshop_id,
        user_id=current_user.id,
        status=MakerspaceRegistrationStatus.waitlisted if is_waitlisted else MakerspaceRegistrationStatus.registered,
        waitlist_position=waitlist_position,
        contact_email=registration_data.contact_email or current_user.email,
        contact_phone=registration_data.contact_phone,
        notes=registration_data.notes,
        payment_status=PaymentStatus.pending if workshop.fee > 0 else PaymentStatus.waived
    )
    db.add(registration)

    # Update workshop counts
    if is_waitlisted:
        workshop.waitlist_count += 1
    else:
        workshop.current_participants += 1

    await db.commit()
    await db.refresh(registration)

    # Send confirmation notification
    from ...services.makerspace_notification_service import MakerspaceNotificationService
    registration.user = current_user
    registration.workshop = workshop
    await MakerspaceNotificationService.notify_workshop_registration(db, registration, is_waitlisted)

    logger.info(f"User {current_user.id} registered for workshop {workshop_id} (waitlisted: {is_waitlisted})")
    return WorkshopRegistrationResponse.model_validate(registration)


@router.get("/my/workshops", response_model=list[MyWorkshopRegistration])
@limiter.limit("60/minute")
async def get_my_workshop_registrations(
    request: Request,
    include_past: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's workshop registrations."""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    query = select(WorkshopRegistration).options(
        selectinload(WorkshopRegistration.workshop)
    ).where(WorkshopRegistration.user_id == current_user.id)

    if not include_past:
        query = query.join(MakerspaceWorkshop).where(
            MakerspaceWorkshop.start_time >= datetime.now(timezone.utc)
        )

    query = query.order_by(WorkshopRegistration.created_at.desc())

    result = await db.execute(query)
    registrations = result.scalars().all()

    return [
        MyWorkshopRegistration(
            registration_id=r.id,
            workshop_id=r.workshop_id,
            workshop_title=r.workshop.title if r.workshop else "Unknown",
            workshop_start_time=r.workshop.start_time if r.workshop else datetime.now(timezone.utc),
            workshop_end_time=r.workshop.end_time if r.workshop else datetime.now(timezone.utc),
            workshop_location=r.workshop.location if r.workshop else None,
            is_virtual=r.workshop.is_virtual if r.workshop else False,
            virtual_meeting_url=r.workshop.virtual_meeting_url if r.workshop else None,
            status=r.status,
            waitlist_position=r.waitlist_position,
            is_waitlisted=r.status == MakerspaceRegistrationStatus.waitlisted,
            confirmation_sent=r.confirmation_sent_at is not None,
            reminder_sent=r.reminder_sent_at is not None
        )
        for r in registrations
    ]


@router.delete("/workshops/{workshop_id}/registration", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def cancel_workshop_registration(
    request: Request,
    workshop_id: int,
    reason: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a workshop registration."""
    from sqlalchemy import select

    result = await db.execute(
        select(WorkshopRegistration)
        .where(WorkshopRegistration.workshop_id == workshop_id)
        .where(WorkshopRegistration.user_id == current_user.id)
        .where(WorkshopRegistration.status.notin_([MakerspaceRegistrationStatus.cancelled]))
    )
    registration = result.scalar_one_or_none()

    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    # Get workshop
    workshop_result = await db.execute(
        select(MakerspaceWorkshop).where(MakerspaceWorkshop.id == workshop_id)
    )
    workshop = workshop_result.scalar_one_or_none()

    was_waitlisted = registration.status == MakerspaceRegistrationStatus.waitlisted

    # Update registration
    registration.status = MakerspaceRegistrationStatus.cancelled
    registration.cancelled_at = datetime.now(timezone.utc)
    registration.cancellation_reason = reason

    # Update workshop counts
    if workshop:
        if was_waitlisted:
            workshop.waitlist_count = max(0, workshop.waitlist_count - 1)
        else:
            workshop.current_participants = max(0, workshop.current_participants - 1)

            # Promote from waitlist if someone is waiting
            if workshop.waitlist_count > 0:
                waitlist_result = await db.execute(
                    select(WorkshopRegistration)
                    .where(WorkshopRegistration.workshop_id == workshop_id)
                    .where(WorkshopRegistration.status == MakerspaceRegistrationStatus.waitlisted)
                    .order_by(WorkshopRegistration.waitlist_position)
                    .limit(1)
                )
                next_in_line = waitlist_result.scalar_one_or_none()

                if next_in_line:
                    next_in_line.status = MakerspaceRegistrationStatus.registered
                    next_in_line.waitlist_position = None
                    workshop.current_participants += 1
                    workshop.waitlist_count -= 1

                    # Notify the promoted user
                    from ...services.makerspace_notification_service import MakerspaceNotificationService
                    next_in_line.workshop = workshop
                    await MakerspaceNotificationService.notify_workshop_registration(db, next_in_line, False)

    await db.commit()

    logger.info(f"User {current_user.id} cancelled registration for workshop {workshop_id}")
    return None
