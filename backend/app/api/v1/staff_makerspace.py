# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff makerspace management API routes.

Staff endpoints for:
- Managing resources
- Managing certifications
- Queue management
- Consumables inventory
- Safety incidents
- Maintenance scheduling
- Reports
"""

from app.core.logging import get_logger
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination_config import PaginationDefaults
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.makerspace import (
    ResourceType,
    ResourceStatus,
    MakerspaceReservationStatus,
    JobStatus,
    JobPriority,
    CertificationStatus,
    MakerspaceIncidentSeverity,
    MaintenanceType,
    MaintenanceStatus,
    PaymentStatus,
)
from ...models.user import User
from ...schemas.makerspace import (
    MakerspaceResourceCreate,
    MakerspaceResourceUpdate,
    MakerspaceResourceResponse,
    CertificationTypeCreate,
    CertificationTypeUpdate,
    CertificationTypeResponse,
    CertificationCreate,
    CertificationUpdate,
    CertificationResponse,
    CertificationWithDetails,
    ReservationResponse,
    ReservationWithDetails,
    ReservationCheckIn,
    ReservationCheckOut,
    JobResponse,
    JobWithDetails,
    JobReview,
    JobStatusUpdate,
    JobComplete,
    JobPickup,
    ConsumableCreate,
    ConsumableUpdate,
    ConsumableResponse,
    ConsumableStockAdjustment,
    ConsumableUsageResponse,
    ConsumableUsageWithDetails,
    SafetyIncidentCreate,
    SafetyIncidentUpdate,
    SafetyIncidentResponse,
    SafetyIncidentWithDetails,
    SafetyIncidentResolve,
    MaintenanceCreate,
    MaintenanceUpdate,
    MaintenanceResponse,
    MaintenanceWithDetails,
    MaintenanceComplete,
    PaymentCreate,
    PaymentResponse,
    PaymentRefund,
    ResourceUtilizationReport,
    RevenueReport,
    PopularEquipmentReport,
    IncidentSummaryReport,
    # Staff list response schemas
    StaffResourceListResponse,
    StaffCertificationListResponse,
    StaffCertificationListItem,
    StaffReservationListResponse,
    StaffJobListResponse,
    StaffConsumableListResponse,
    StaffIncidentListResponse,
    StaffIncidentListItem,
    StaffMaintenanceListResponse,
    StaffMaintenanceListItem,
    StaffRevenueReportResponse,
    StaffIncidentSummaryReportResponse,
)
from ...services.makerspace_service import (
    MakerspaceResourceService,
    CertificationService,
    ReservationService,
    JobQueueService,
    ConsumableService,
    SafetyIncidentService,
    MaintenanceService,
    MakerspacePaymentService,
    MakerspaceReportsService,
)
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/makerspace", tags=["staff-makerspace"])


# =============================================================================
# Resource Management
# =============================================================================


@router.get("/resources", response_model=StaffResourceListResponse)
@limiter.limit("60/minute")
async def list_all_resources(
    request: Request,
    resource_type: ResourceType | None = Query(None),
    status: ResourceStatus | None = Query(None),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(
        PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffResourceListResponse:
    """List all resources (including inactive)."""
    resources, total = await MakerspaceResourceService.get_all(
        db,
        resource_type=resource_type,
        status=status,
        is_active=is_active,
        page=page,
        per_page=per_page,
    )

    return StaffResourceListResponse(
        items=[MakerspaceResourceResponse.model_validate(r) for r in resources],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post(
    "/resources", response_model=MakerspaceResourceResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("10/minute")
async def create_resource(
    request: Request,
    resource_data: MakerspaceResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new resource."""
    resource = await MakerspaceResourceService.create(
        db, data=resource_data.model_dump(), created_by_id=current_user.id
    )
    logger.info(f"Resource created: {resource.name} by user {current_user.id}")
    return MakerspaceResourceResponse.model_validate(resource)


@router.put("/resources/{resource_id}", response_model=MakerspaceResourceResponse)
@limiter.limit("30/minute")
async def update_resource(
    request: Request,
    resource_id: int,
    resource_data: MakerspaceResourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a resource."""
    resource = await MakerspaceResourceService.get_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    resource = await MakerspaceResourceService.update(
        db, resource, data=resource_data.model_dump(exclude_unset=True)
    )
    logger.info(f"Resource updated: {resource.name} by user {current_user.id}")
    return MakerspaceResourceResponse.model_validate(resource)


@router.patch("/resources/{resource_id}/status", response_model=MakerspaceResourceResponse)
@limiter.limit("30/minute")
async def update_resource_status(
    request: Request,
    resource_id: int,
    status: ResourceStatus = Query(...),
    notes: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update resource status."""
    resource = await MakerspaceResourceService.get_by_id(db, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    resource = await MakerspaceResourceService.update_status(db, resource, status, notes)
    logger.info(f"Resource {resource.name} status changed to {status} by user {current_user.id}")
    return MakerspaceResourceResponse.model_validate(resource)


# =============================================================================
# Certification Type Management
# =============================================================================


@router.post(
    "/certification-types",
    response_model=CertificationTypeResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("10/minute")
async def create_certification_type(
    request: Request,
    cert_data: CertificationTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new certification type."""
    cert_type = await CertificationService.create_certification_type(
        db, data=cert_data.model_dump()
    )
    logger.info(f"Certification type created: {cert_type.name} by user {current_user.id}")
    return CertificationTypeResponse.model_validate(cert_type)


@router.put("/certification-types/{type_id}", response_model=CertificationTypeResponse)
@limiter.limit("30/minute")
async def update_certification_type(
    request: Request,
    type_id: int,
    cert_data: CertificationTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a certification type."""
    cert_type = await CertificationService.get_certification_type_by_id(db, type_id)
    if not cert_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Certification type not found"
        )

    for key, value in cert_data.model_dump(exclude_unset=True).items():
        if value is not None:
            setattr(cert_type, key, value)

    await db.commit()
    await db.refresh(cert_type)
    return CertificationTypeResponse.model_validate(cert_type)


# =============================================================================
# Patron Certification Management
# =============================================================================


@router.get("/certifications", response_model=StaffCertificationListResponse)
@limiter.limit("60/minute")
async def list_certifications(
    request: Request,
    user_id: int | None = Query(None),
    certification_type_id: int | None = Query(None),
    status: CertificationStatus | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(
        PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffCertificationListResponse:
    """List all certifications with filtering."""
    from sqlalchemy import select, func
    from ...models.makerspace import MakerspaceCertification
    from sqlalchemy.orm import selectinload

    query = select(MakerspaceCertification)
    count_query = select(func.count(MakerspaceCertification.id))

    if user_id:
        query = query.where(MakerspaceCertification.user_id == user_id)
        count_query = count_query.where(MakerspaceCertification.user_id == user_id)

    if certification_type_id:
        query = query.where(MakerspaceCertification.certification_type_id == certification_type_id)
        count_query = count_query.where(
            MakerspaceCertification.certification_type_id == certification_type_id
        )

    if status:
        query = query.where(MakerspaceCertification.status == status)
        count_query = count_query.where(MakerspaceCertification.status == status)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        query.options(
            selectinload(MakerspaceCertification.user),
            selectinload(MakerspaceCertification.certification_type),
        )
        .offset(offset)
        .limit(per_page)
        .order_by(MakerspaceCertification.created_at.desc())
    )

    result = await db.execute(query)
    certifications = result.scalars().all()

    items = []
    for cert in certifications:
        cert_data = CertificationResponse.model_validate(cert).model_dump()
        cert_data["certification_type_name"] = (
            cert.certification_type.name if cert.certification_type else None
        )
        cert_data["user_name"] = cert.user.full_name if cert.user else None
        items.append(StaffCertificationListItem(**cert_data))

    return StaffCertificationListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/certifications/{user_id}/certify", response_model=CertificationResponse)
@limiter.limit("30/minute")
async def certify_user(
    request: Request,
    user_id: int,
    certification_type_id: int = Query(...),
    notes: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Manually certify a user (staff action)."""
    # Check if user already has this certification
    existing_certs = await CertificationService.get_user_certifications(db, user_id)
    cert_to_update = None

    for cert in existing_certs:
        if cert.certification_type_id == certification_type_id:
            if cert.status == CertificationStatus.active:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="User is already certified"
                )
            cert_to_update = cert
            break

    if not cert_to_update:
        # Create new certification
        cert_to_update = await CertificationService.start_certification(
            db, user_id, certification_type_id
        )

    certification = await CertificationService.certify_user(
        db, cert_to_update, current_user.id, notes
    )

    logger.info(
        f"User {user_id} certified for type {certification_type_id} by staff {current_user.id}"
    )
    return CertificationResponse.model_validate(certification)


@router.post("/certifications/{certification_id}/suspend")
@limiter.limit("30/minute")
async def suspend_certification(
    request: Request,
    certification_id: int,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Suspend a certification."""
    certification = await CertificationService.get_certification(db, certification_id)
    if not certification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")

    await CertificationService.suspend_certification(db, certification, current_user.id, reason)

    logger.info(f"Certification {certification_id} suspended by user {current_user.id}")
    return {"message": "Certification suspended"}


@router.post("/certifications/{certification_id}/reinstate")
@limiter.limit("30/minute")
async def reinstate_certification(
    request: Request,
    certification_id: int,
    notes: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Reinstate a suspended certification."""
    certification = await CertificationService.get_certification(db, certification_id)
    if not certification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Certification not found")

    await CertificationService.reinstate_certification(db, certification, notes)

    logger.info(f"Certification {certification_id} reinstated by user {current_user.id}")
    return {"message": "Certification reinstated"}


@router.get("/certifications/expiring", response_model=list[CertificationWithDetails])
@limiter.limit("60/minute")
async def get_expiring_certifications(
    request: Request,
    days: int = Query(30, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get certifications expiring within N days."""
    certifications = await CertificationService.check_expiring_certifications(db, days)

    results = []
    for cert in certifications:
        c_dict = CertificationResponse.model_validate(cert).model_dump()
        c_dict["certification_type_name"] = (
            cert.certification_type.name if cert.certification_type else None
        )
        c_dict["user_name"] = cert.user.full_name if cert.user else None
        results.append(CertificationWithDetails(**c_dict))

    return results


# =============================================================================
# Reservation Management
# =============================================================================


@router.get("/reservations", response_model=StaffReservationListResponse)
@limiter.limit("60/minute")
async def list_reservations(
    request: Request,
    user_id: int | None = Query(None),
    resource_id: int | None = Query(None),
    status: MakerspaceReservationStatus | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(
        PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffReservationListResponse:
    """List all reservations with filtering."""
    reservations, total = await ReservationService.get_reservations(
        db,
        user_id=user_id,
        resource_id=resource_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page,
    )

    items = []
    for r in reservations:
        r_data = ReservationResponse.model_validate(r).model_dump()
        r_data["user_name"] = r.user.full_name if r.user else None
        r_data["user_email"] = r.user.email if r.user else None
        r_data["resource_name"] = r.resource.name if r.resource else None
        r_data["resource_type"] = r.resource.resource_type if r.resource else None
        items.append(ReservationWithDetails(**r_data))

    return StaffReservationListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post("/reservations/{reservation_id}/approve", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def approve_reservation(
    request: Request,
    reservation_id: int,
    notes: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Approve a pending reservation."""
    reservation = await ReservationService.get_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    try:
        reservation = await ReservationService.approve(db, reservation, current_user.id, notes)
        logger.info(f"Reservation {reservation_id} approved by user {current_user.id}")
        return ReservationResponse.model_validate(reservation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/reservations/{reservation_id}/check-in", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def check_in_reservation(
    request: Request,
    reservation_id: int,
    check_in_data: ReservationCheckIn,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Check in a patron for their reservation."""
    reservation = await ReservationService.get_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    try:
        reservation = await ReservationService.check_in(db, reservation, check_in_data.notes)
        logger.info(f"Reservation {reservation_id} checked in by user {current_user.id}")
        return ReservationResponse.model_validate(reservation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/reservations/{reservation_id}/check-out", response_model=ReservationResponse)
@limiter.limit("30/minute")
async def check_out_reservation(
    request: Request,
    reservation_id: int,
    check_out_data: ReservationCheckOut,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Check out a patron from their reservation."""
    reservation = await ReservationService.get_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    consumables = None
    if check_out_data.consumable_usage:
        consumables = [c.model_dump() for c in check_out_data.consumable_usage]

    try:
        reservation = await ReservationService.check_out(
            db, reservation, check_out_data.notes, consumables
        )
        logger.info(f"Reservation {reservation_id} checked out by user {current_user.id}")
        return ReservationResponse.model_validate(reservation)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/reservations/{reservation_id}/no-show")
@limiter.limit("30/minute")
async def mark_no_show(
    request: Request,
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a reservation as no-show."""
    reservation = await ReservationService.get_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Reservation not found")

    try:
        await ReservationService.mark_no_show(db, reservation)
        logger.info(f"Reservation {reservation_id} marked as no-show by user {current_user.id}")
        return {"message": "Reservation marked as no-show"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Job Queue Management
# =============================================================================


@router.get("/jobs", response_model=StaffJobListResponse)
@limiter.limit("60/minute")
async def list_jobs(
    request: Request,
    user_id: int | None = Query(None),
    resource_id: int | None = Query(None),
    status: JobStatus | None = Query(None),
    priority: JobPriority | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(
        PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffJobListResponse:
    """List all jobs with filtering."""
    jobs, total = await JobQueueService.get_jobs(
        db,
        user_id=user_id,
        resource_id=resource_id,
        status=status,
        priority=priority,
        page=page,
        per_page=per_page,
    )

    items = []
    for job in jobs:
        j_data = JobResponse.model_validate(job).model_dump()
        j_data["user_name"] = job.user.full_name if job.user else None
        j_data["user_email"] = job.user.email if job.user else None
        j_data["resource_name"] = job.resource.name if job.resource else None
        items.append(JobWithDetails(**j_data))

    return StaffJobListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/jobs/queue", response_model=list[JobWithDetails])
@limiter.limit("60/minute")
async def get_job_queue(
    request: Request,
    resource_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get the current job queue."""
    jobs = await JobQueueService.get_queue(db, resource_id)

    results = []
    for job in jobs:
        j_dict = JobResponse.model_validate(job).model_dump()
        j_dict["user_name"] = job.user.full_name if job.user else None
        j_dict["user_email"] = job.user.email if job.user else None
        j_dict["resource_name"] = job.resource.name if job.resource else None
        results.append(JobWithDetails(**j_dict))

    return results


@router.post("/jobs/{job_id}/review", response_model=JobResponse)
@limiter.limit("30/minute")
async def review_job(
    request: Request,
    job_id: int,
    review: JobReview,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Review a submitted job."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    estimates = None
    if review.approved:
        estimates = {
            "print_time_minutes": review.estimated_print_time_minutes,
            "material_grams": review.estimated_material_grams,
            "cost": review.estimated_cost,
        }

    try:
        job = await JobQueueService.review(
            db,
            job,
            reviewed_by_id=current_user.id,
            approved=review.approved,
            notes=review.notes,
            rejection_reason=review.rejection_reason,
            estimates=estimates,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    logger.info(
        f"Job {job.job_number} {'approved' if review.approved else 'rejected'} "
        f"by user {current_user.id}"
    )

    # Serialize before notifying: the notification commits, which expires `job`, and
    # serializing an expired instance lazy-loads outside the greenlet context.
    response = JobResponse.model_validate(job)

    # Send approval/rejection notification
    try:
        from ...services.makerspace_notification_service import MakerspaceNotificationService

        if review.approved:
            await MakerspaceNotificationService.notify_job_approved(db, job)
        else:
            await MakerspaceNotificationService.notify_job_rejected(db, job)
    except Exception as e:  # noqa: BLE001  # best-effort job review notification
        logger.warning(f"Failed to send job review notification: {e}")

    return response


@router.post("/jobs/{job_id}/start", response_model=JobResponse)
@limiter.limit("30/minute")
async def start_job(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Start processing a job."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        job = await JobQueueService.start_job(db, job)
        logger.info(f"Job {job.job_number} started by user {current_user.id}")
        return JobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/jobs/{job_id}/complete", response_model=JobResponse)
@limiter.limit("30/minute")
async def complete_job(
    request: Request,
    job_id: int,
    completion: JobComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a job as completed."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    consumables = None
    if completion.consumable_usage:
        consumables = [c.model_dump() for c in completion.consumable_usage]

    try:
        job = await JobQueueService.complete_job(
            db,
            job,
            actual_time_minutes=completion.actual_print_time_minutes,
            actual_material_grams=completion.actual_material_grams,
            consumables_used=consumables,
            notes=completion.notes,
        )
        logger.info(f"Job {job.job_number} completed by user {current_user.id}")
        return JobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/jobs/{job_id}/ready-pickup", response_model=JobResponse)
@limiter.limit("30/minute")
async def mark_ready_pickup(
    request: Request,
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a job as ready for pickup."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        job = await JobQueueService.mark_ready_for_pickup(db, job)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    logger.info(f"Job {job.job_number} marked ready for pickup by user {current_user.id}")

    # Serialize before notifying: the notification commits, which expires `job`, and
    # serializing an expired instance lazy-loads outside the greenlet context.
    response = JobResponse.model_validate(job)

    # Send ready-for-pickup notification
    try:
        from ...services.makerspace_notification_service import MakerspaceNotificationService

        await MakerspaceNotificationService.notify_job_ready_pickup(db, job)
    except Exception as e:  # noqa: BLE001  # best-effort pickup notification
        logger.warning(f"Failed to send ready-for-pickup notification: {e}")

    return response


@router.post("/jobs/{job_id}/pickup", response_model=JobResponse)
@limiter.limit("30/minute")
async def mark_picked_up(
    request: Request,
    job_id: int,
    pickup: JobPickup,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a job as picked up."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        job = await JobQueueService.mark_picked_up(db, job, job.user_id)
        logger.info(f"Job {job.job_number} marked as picked up by user {current_user.id}")
        return JobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/jobs/{job_id}/fail")
@limiter.limit("30/minute")
async def fail_job(
    request: Request,
    job_id: int,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Mark a job as failed."""
    job = await JobQueueService.get_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    try:
        await JobQueueService.fail_job(db, job, reason)
        logger.info(f"Job {job.job_number} marked as failed by user {current_user.id}")
        return {"message": "Job marked as failed"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/jobs/reorder", response_model=list[JobResponse])
@limiter.limit("10/minute")
async def reorder_queue(
    request: Request,
    job_ids: list[int],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Reorder the job queue."""
    jobs = await JobQueueService.reorder_queue(db, job_ids)
    logger.info(f"Queue reordered by user {current_user.id}")
    return [JobResponse.model_validate(job) for job in jobs]


# =============================================================================
# Consumables Inventory
# =============================================================================


@router.get("/consumables", response_model=StaffConsumableListResponse)
@limiter.limit("60/minute")
async def list_consumables(
    request: Request,
    category: str | None = Query(None),
    material_type: str | None = Query(None),
    low_stock_only: bool = Query(False),
    is_active: bool | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(
        PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffConsumableListResponse:
    """List all consumables."""
    consumables, total = await ConsumableService.get_all(
        db,
        category=category,
        material_type=material_type,
        is_active=is_active,
        low_stock_only=low_stock_only,
        page=page,
        per_page=per_page,
    )

    return StaffConsumableListResponse(
        items=[ConsumableResponse.model_validate(c) for c in consumables],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/consumables/low-stock", response_model=list[ConsumableResponse])
@limiter.limit("60/minute")
async def get_low_stock(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get all consumables at or below reorder threshold."""
    consumables = await ConsumableService.get_low_stock_items(db)
    return [ConsumableResponse.model_validate(c) for c in consumables]


@router.post("/consumables", response_model=ConsumableResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_consumable(
    request: Request,
    consumable_data: ConsumableCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new consumable item."""
    consumable = await ConsumableService.create(db, data=consumable_data.model_dump())
    logger.info(f"Consumable created: {consumable.name} by user {current_user.id}")
    return ConsumableResponse.model_validate(consumable)


@router.put("/consumables/{consumable_id}", response_model=ConsumableResponse)
@limiter.limit("30/minute")
async def update_consumable(
    request: Request,
    consumable_id: int,
    consumable_data: ConsumableUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a consumable item."""
    consumable = await ConsumableService.get_by_id(db, consumable_id)
    if not consumable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consumable not found")

    consumable = await ConsumableService.update(
        db, consumable, data=consumable_data.model_dump(exclude_unset=True)
    )
    logger.info(f"Consumable updated: {consumable.name} by user {current_user.id}")
    return ConsumableResponse.model_validate(consumable)


@router.post("/consumables/{consumable_id}/adjust-stock", response_model=ConsumableResponse)
@limiter.limit("30/minute")
async def adjust_consumable_stock(
    request: Request,
    consumable_id: int,
    adjustment: ConsumableStockAdjustment,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Adjust consumable stock level."""
    consumable = await ConsumableService.get_by_id(db, consumable_id)
    if not consumable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consumable not found")

    try:
        consumable = await ConsumableService.adjust_stock(
            db, consumable, adjustment.quantity, adjustment.reason
        )
        logger.info(
            f"Stock adjusted for {consumable.name}: {adjustment.quantity} by user {current_user.id}"
        )
        return ConsumableResponse.model_validate(consumable)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Safety Incidents
# =============================================================================


@router.get("/incidents", response_model=StaffIncidentListResponse)
@limiter.limit("60/minute")
async def list_incidents(
    request: Request,
    resource_id: int | None = Query(None),
    severity: MakerspaceIncidentSeverity | None = Query(None),
    is_resolved: bool | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(
        PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffIncidentListResponse:
    """List safety incidents."""
    incidents, total = await SafetyIncidentService.get_incidents(
        db,
        resource_id=resource_id,
        severity=severity,
        is_resolved=is_resolved,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page,
    )

    items = []
    for incident in incidents:
        i_data = SafetyIncidentResponse.model_validate(incident).model_dump()
        i_data["resource_name"] = incident.resource.name if incident.resource else None
        items.append(StaffIncidentListItem(**i_data))

    return StaffIncidentListResponse(items=items, total=total, page=page, per_page=per_page)


@router.post(
    "/incidents", response_model=SafetyIncidentResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("30/minute")
async def create_incident(
    request: Request,
    incident_data: SafetyIncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Report a safety incident."""
    incident = await SafetyIncidentService.create(
        db, reported_by_id=current_user.id, data=incident_data.model_dump()
    )
    logger.warning(f"Safety incident {incident.incident_number} reported by user {current_user.id}")
    return SafetyIncidentResponse.model_validate(incident)


@router.put("/incidents/{incident_id}", response_model=SafetyIncidentResponse)
@limiter.limit("30/minute")
async def update_incident(
    request: Request,
    incident_id: int,
    incident_data: SafetyIncidentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a safety incident."""
    incident = await SafetyIncidentService.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident = await SafetyIncidentService.update(
        db, incident, data=incident_data.model_dump(exclude_unset=True)
    )
    return SafetyIncidentResponse.model_validate(incident)


@router.post("/incidents/{incident_id}/resolve")
@limiter.limit("30/minute")
async def resolve_incident(
    request: Request,
    incident_id: int,
    resolution: SafetyIncidentResolve,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Resolve a safety incident."""
    incident = await SafetyIncidentService.get_by_id(db, incident_id)
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    await SafetyIncidentService.resolve(db, incident, current_user.id, resolution.resolution_notes)
    logger.info(f"Incident {incident.incident_number} resolved by user {current_user.id}")
    return {"message": "Incident resolved"}


# =============================================================================
# Maintenance
# =============================================================================


@router.get("/maintenance", response_model=StaffMaintenanceListResponse)
@limiter.limit("60/minute")
async def list_maintenance(
    request: Request,
    resource_id: int | None = Query(None),
    maintenance_type: MaintenanceType | None = Query(None),
    status: MaintenanceStatus | None = Query(None),
    start_date: date | None = Query(None),
    end_date: date | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(
        PaginationDefaults.DEFAULT_PAGE_SIZE, ge=1, le=PaginationDefaults.MAX_PAGE_SIZE
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffMaintenanceListResponse:
    """List maintenance records."""
    records, total = await MaintenanceService.get_maintenance_records(
        db,
        resource_id=resource_id,
        maintenance_type=maintenance_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        page=page,
        per_page=per_page,
    )

    items = []
    for m in records:
        m_data = MaintenanceResponse.model_validate(m).model_dump()
        m_data["resource_name"] = m.resource.name if m.resource else None
        items.append(StaffMaintenanceListItem(**m_data))

    return StaffMaintenanceListResponse(items=items, total=total, page=page, per_page=per_page)


@router.get("/maintenance/overdue", response_model=list[MaintenanceWithDetails])
@limiter.limit("60/minute")
async def get_overdue_maintenance(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get all overdue maintenance tasks."""
    records = await MaintenanceService.get_overdue(db)

    results = []
    for m in records:
        m_dict = MaintenanceResponse.model_validate(m).model_dump()
        m_dict["resource_name"] = m.resource.name if m.resource else None
        results.append(MaintenanceWithDetails(**m_dict))

    return results


@router.get("/maintenance/upcoming", response_model=list[MaintenanceWithDetails])
@limiter.limit("60/minute")
async def get_upcoming_maintenance(
    request: Request,
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get maintenance tasks scheduled within N days."""
    records = await MaintenanceService.get_upcoming(db, days)

    results = []
    for m in records:
        m_dict = MaintenanceResponse.model_validate(m).model_dump()
        m_dict["resource_name"] = m.resource.name if m.resource else None
        results.append(MaintenanceWithDetails(**m_dict))

    return results


@router.post(
    "/maintenance", response_model=MaintenanceResponse, status_code=status.HTTP_201_CREATED
)
@limiter.limit("30/minute")
async def schedule_maintenance(
    request: Request,
    maintenance_data: MaintenanceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Schedule a maintenance task."""
    maintenance = await MaintenanceService.schedule(
        db, scheduled_by_id=current_user.id, data=maintenance_data.model_dump()
    )
    logger.info(
        f"Maintenance scheduled for resource {maintenance.resource_id} by user {current_user.id}"
    )
    return MaintenanceResponse.model_validate(maintenance)


@router.post("/maintenance/{maintenance_id}/start", response_model=MaintenanceResponse)
@limiter.limit("30/minute")
async def start_maintenance(
    request: Request,
    maintenance_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Start a maintenance task."""
    maintenance = await MaintenanceService.get_by_id(db, maintenance_id)
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found"
        )

    try:
        maintenance = await MaintenanceService.start(db, maintenance, current_user.id)
        logger.info(f"Maintenance {maintenance_id} started by user {current_user.id}")
        return MaintenanceResponse.model_validate(maintenance)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/maintenance/{maintenance_id}/complete", response_model=MaintenanceResponse)
@limiter.limit("30/minute")
async def complete_maintenance(
    request: Request,
    maintenance_id: int,
    completion: MaintenanceComplete,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Complete a maintenance task."""
    maintenance = await MaintenanceService.get_by_id(db, maintenance_id)
    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Maintenance record not found"
        )

    try:
        maintenance = await MaintenanceService.complete(
            db,
            maintenance,
            findings=completion.findings,
            parts_replaced=completion.parts_replaced,
            parts_cost=completion.parts_cost,
            labor_hours=completion.labor_hours,
            next_maintenance_date=completion.next_maintenance_date,
            notes=completion.notes,
        )
        logger.info(f"Maintenance {maintenance_id} completed by user {current_user.id}")
        return MaintenanceResponse.model_validate(maintenance)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Payments
# =============================================================================


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def create_payment(
    request: Request,
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Record a payment."""
    payment = await MakerspacePaymentService.create_payment(
        db,
        user_id=payment_data.user_id,
        amount=payment_data.amount,
        payment_method=payment_data.payment_method,
        processed_by_id=current_user.id,
        reservation_id=payment_data.reservation_id,
        job_id=payment_data.job_id,
        notes=payment_data.notes,
    )
    logger.info(f"Payment {payment.receipt_number} recorded by user {current_user.id}")
    return PaymentResponse.model_validate(payment)


@router.post("/payments/{payment_id}/refund", response_model=PaymentResponse)
@limiter.limit("10/minute")
async def refund_payment(
    request: Request,
    payment_id: int,
    refund_data: PaymentRefund,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Process a refund."""
    from sqlalchemy import select
    from ...models.makerspace import MakerspacePayment

    payment = await get_or_404(db, MakerspacePayment, payment_id, "Payment not found")

    try:
        payment = await MakerspacePaymentService.refund(
            db, payment, refund_data.amount, refund_data.reason, current_user.id
        )
        logger.info(
            f"Refund of ${refund_data.amount} for payment {payment_id} by user {current_user.id}"
        )
        return PaymentResponse.model_validate(payment)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


# =============================================================================
# Reports
# =============================================================================


@router.get("/reports/utilization", response_model=list[dict])
@limiter.limit("30/minute")
async def get_utilization_report(
    request: Request,
    start_date: date = Query(...),
    end_date: date = Query(...),
    resource_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get resource utilization report."""
    return await MakerspaceReportsService.get_resource_utilization(
        db, start_date, end_date, resource_id
    )


@router.get("/reports/revenue", response_model=StaffRevenueReportResponse)
@limiter.limit("30/minute")
async def get_revenue_report(
    request: Request,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffRevenueReportResponse:
    """Get revenue report."""
    report_data = await MakerspaceReportsService.get_revenue_report(db, start_date, end_date)
    return StaffRevenueReportResponse(**report_data)


@router.get("/reports/popular-equipment", response_model=list[dict])
@limiter.limit("30/minute")
async def get_popular_equipment_report(
    request: Request,
    start_date: date = Query(...),
    end_date: date = Query(...),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Get popular equipment report."""
    return await MakerspaceReportsService.get_popular_equipment(db, start_date, end_date, limit)


@router.get("/reports/incidents", response_model=StaffIncidentSummaryReportResponse)
@limiter.limit("30/minute")
async def get_incident_report(
    request: Request,
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> StaffIncidentSummaryReportResponse:
    """Get incident summary report."""
    report_data = await MakerspaceReportsService.get_incident_summary(db, start_date, end_date)
    return StaffIncidentSummaryReportResponse(**report_data)
