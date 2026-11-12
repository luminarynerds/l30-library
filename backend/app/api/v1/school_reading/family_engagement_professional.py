# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Professional development, ambassador, and consultation routes."""

from datetime import datetime, timezone
from typing import List, Optional
from app.core.branding import branding
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from ....core.database import get_db
from ....core.rate_limit import limiter
from ....core.shortcuts import get_or_404
from ....models.outreach import OutreachPartner, OutreachPartnerStatus
from ....models.reading import (
    ConsultationAttendee,
    LibrarianConsultationSlot,
    ReadingAmbassadorCertification,
    TeacherTrainingModule,
    TrainingCompletion,
)
from ....models.user import User, UserRole
from ....schemas.reading import (
    LibrarianConsultationSlotCreate,
    LibrarianConsultationSlotResponse,
    ReadingAmbassadorCertificationCreate,
    ReadingAmbassadorCertificationListResponse,
    ReadingAmbassadorCertificationResponse,
    ReadingAmbassadorCertificationUpdate,
    TeacherTrainingModuleCreate,
    TeacherTrainingModuleResponse,
    TrainingCompletionResponse,
)
from ..auth import get_current_user
from ..dependencies import check_staff_access
from ..feature_guards import require_for_teachers_enabled
from ._notifications import _notify_librarian_of_teacher_action
from ._shared import assert_teacher_access_to_school, require_teacher_of_school

professional_router = APIRouter()


@professional_router.post(
    "/training-modules",
    response_model=TeacherTrainingModuleResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def create_training_module(
    request: Request,
    module_data: TeacherTrainingModuleCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a professional development training module. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    school_result = await db.execute(
        select(OutreachPartner).where(OutreachPartner.id == module_data.partner_id)
    )
    if not school_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    module = TeacherTrainingModule(
        partner_id=module_data.partner_id,
        title=module_data.title,
        description=module_data.description,
        content_url=module_data.content_url,
        duration_minutes=module_data.duration_minutes,
        category=module_data.category,
        level=module_data.level,
    )

    db.add(module)
    await db.commit()
    await db.refresh(module)

    return module


@professional_router.get(
    "/training-modules/{school_id}",
    response_model=List[TeacherTrainingModuleResponse],
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_training_modules(
    request: Request,
    school_id: int,
    category: Optional[str] = Query(None),
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List training modules for a school."""
    conditions = [
        TeacherTrainingModule.partner_id == school_id,
        TeacherTrainingModule.is_active == True,
    ]
    if category:
        conditions.append(TeacherTrainingModule.category == category)

    query = select(TeacherTrainingModule).where(*conditions)
    result = await db.execute(query)
    modules = result.scalars().all()

    return modules


@professional_router.post(
    "/training-modules/{module_id}/start",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def start_training_module(
    request: Request,
    module_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start a training module. Teacher enrollment."""
    # Verify module exists
    module_result = await db.execute(
        select(TeacherTrainingModule).where(TeacherTrainingModule.id == module_id)
    )
    if not module_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    # Create or update completion record
    completion_result = await db.execute(
        select(TrainingCompletion).where(
            and_(
                TrainingCompletion.module_id == module_id,
                TrainingCompletion.user_id == current_user.id,
            )
        )
    )
    completion = completion_result.scalar_one_or_none()

    if not completion:
        completion = TrainingCompletion(
            module_id=module_id,
            user_id=current_user.id,
            status="in_progress",
            started_at=datetime.now(timezone.utc),
        )
        db.add(completion)
    else:
        completion.status = "in_progress"
        completion.started_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(completion)

    return completion


@professional_router.get(
    "/training-modules/{school_id}/completions",
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_training_completions(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's training completions for modules belonging to a school."""
    result = await db.execute(
        select(TrainingCompletion)
        .options(selectinload(TrainingCompletion.module))
        .join(TeacherTrainingModule, TrainingCompletion.module_id == TeacherTrainingModule.id)
        .where(
            and_(
                TrainingCompletion.user_id == current_user.id,
                TeacherTrainingModule.partner_id == school_id,
            )
        )
    )
    completions = result.scalars().all()

    return {
        "completions": [
            {
                "module_id": c.module_id,
                "module_title": c.module.title if c.module else None,
                "status": c.status,
                "started_at": c.started_at,
                "completed_at": c.completed_at,
                "quiz_score": c.quiz_score,
                "passed_assessment": c.passed_assessment,
            }
            for c in completions
        ]
    }


@professional_router.get(
    "/training-modules/{school_id}/certificates",
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_training_certificates(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the current user's reading-ambassador certifications for a school."""
    result = await db.execute(
        select(ReadingAmbassadorCertification).where(
            and_(
                ReadingAmbassadorCertification.user_id == current_user.id,
                ReadingAmbassadorCertification.partner_id == school_id,
            )
        )
    )
    certifications = result.scalars().all()

    return {
        "certificates": [
            {
                "id": cert.id,
                "certification_name": cert.certification_name,
                "certification_level": cert.certification_level,
                "certification_number": cert.certification_number,
                "issued_at": cert.certified_at,
                "expires_at": cert.expires_at,
            }
            for cert in certifications
        ]
    }


class CompleteTrainingModuleRequest(BaseModel):
    partnerId: Optional[int] = None
    # Optional: training modules currently have no quiz content, so completion
    # without a score is attendance-based (passed, quiz_score null).
    assessmentScore: Optional[float] = None
    answers: Optional[List[str]] = None


@professional_router.post(
    "/training-modules/{module_id}/complete",
    response_model=TrainingCompletionResponse,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def complete_training_module(
    request: Request,
    module_id: int,
    body: CompleteTrainingModuleRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark a training module completed for the current user. Records quiz score and pass/fail."""
    module_result = await db.execute(
        select(TeacherTrainingModule).where(TeacherTrainingModule.id == module_id)
    )
    if not module_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Module not found")

    completion_result = await db.execute(
        select(TrainingCompletion).where(
            and_(
                TrainingCompletion.module_id == module_id,
                TrainingCompletion.user_id == current_user.id,
            )
        )
    )
    completion = completion_result.scalar_one_or_none()
    if not completion:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No in-progress completion found for this module; start the module first",
        )

    score = int(body.assessmentScore) if body.assessmentScore is not None else None
    completion.status = "completed"
    completion.completed_at = datetime.now(timezone.utc)
    completion.quiz_score = score
    completion.passed_assessment = True if score is None else body.assessmentScore >= 70

    await db.commit()
    await db.refresh(completion)

    # Librarian notification (best-effort; never 500s the caller).
    # Resolve school_id via the module's partner_id (lazy-fetched).
    module_partner_id = None
    try:
        m_result = await db.execute(
            select(TeacherTrainingModule).where(TeacherTrainingModule.id == module_id)
        )
        m_row = m_result.scalar_one_or_none()
        module_partner_id = getattr(m_row, "partner_id", None) if m_row else None
    except Exception:  # noqa: BLE001  # module lookup fallback — use request body partnerId
        module_partner_id = body.partnerId
    await _notify_librarian_of_teacher_action(
        db,
        teacher=current_user,
        school_id=module_partner_id or body.partnerId,
        action_type="training_module_complete",
        payload={
            "module_id": module_id,
            "quiz_score": score,
            "passed": completion.passed_assessment,
        },
    )

    return completion


@professional_router.post(
    "/ambassador-certifications",
    response_model=ReadingAmbassadorCertificationResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def create_ambassador_certification(
    request: Request,
    cert_data: ReadingAmbassadorCertificationCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a reading ambassador certification. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    school_result = await db.execute(
        select(OutreachPartner).where(OutreachPartner.id == cert_data.partner_id)
    )
    if not school_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    certification = ReadingAmbassadorCertification(
        user_id=cert_data.user_id,
        partner_id=cert_data.partner_id,
        certification_level=cert_data.certification_level,
        certification_name=cert_data.certification_name,
    )

    db.add(certification)
    await db.commit()
    await db.refresh(certification)

    # Generate certification number
    certification.certification_number = f"RA-{certification.partner_id:03d}-{certification.id:06d}"
    await db.commit()
    await db.refresh(certification)

    return certification


@professional_router.get(
    "/ambassador-certifications/{school_id}",
    response_model=ReadingAmbassadorCertificationListResponse,
)
@limiter.limit("120/minute")
async def list_ambassador_certifications(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List reading ambassador certifications for a school. Staff only."""
    check_staff_access(current_user)

    school_result = await db.execute(select(OutreachPartner).where(OutreachPartner.id == school_id))
    school = school_result.scalar_one_or_none()
    if not school:
        raise HTTPException(status_code=404, detail="School not found")

    query = (
        select(ReadingAmbassadorCertification)
        .options(
            selectinload(ReadingAmbassadorCertification.user),
            selectinload(ReadingAmbassadorCertification.partner),
        )
        .where(ReadingAmbassadorCertification.partner_id == school_id)
        .order_by(ReadingAmbassadorCertification.created_at.desc())
    )

    result = await db.execute(query)
    certs = result.scalars().all()

    now = datetime.now(timezone.utc)
    items = []
    for cert in certs:
        if cert.certified_at is None:
            computed_status = "pending"
        elif cert.expires_at and cert.expires_at < now:
            computed_status = "expired"
        elif cert.is_active:
            computed_status = "active"
        else:
            computed_status = "expired"

        cert_number = cert.certification_number
        if not cert_number:
            cert_number = f"RA-{cert.partner_id:03d}-{cert.id:06d}"

        user = cert.user
        teacher_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email

        items.append(
            {
                "id": cert.id,
                "teacher_name": teacher_name,
                "school_name": cert.partner.name if cert.partner else "Unknown",
                "certification_level": cert.certification_level,
                "certification_name": cert.certification_name,
                "certification_number": cert_number,
                "date_earned": cert.certified_at,
                "expires_at": cert.expires_at,
                "required_modules_completed": cert.required_modules_completed,
                "total_modules_required": cert.total_modules_required,
                "status": computed_status,
            }
        )

    return {"certifications": items}


@professional_router.get("/ambassador-certifications/{cert_id}/download")
@limiter.limit("30/minute")
async def download_ambassador_certificate(
    request: Request,
    cert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Download a reading ambassador certificate as PDF. Staff only."""
    import re
    from io import BytesIO

    from fastapi.responses import StreamingResponse
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    check_staff_access(current_user)

    cert_result = await db.execute(
        select(ReadingAmbassadorCertification)
        .options(
            selectinload(ReadingAmbassadorCertification.user),
            selectinload(ReadingAmbassadorCertification.partner),
        )
        .where(ReadingAmbassadorCertification.id == cert_id)
    )
    cert = cert_result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    user = cert.user
    teacher_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email
    school_name = cert.partner.name if cert.partner else "Unknown"
    cert_number = cert.certification_number or f"RA-{cert.partner_id:03d}-{cert.id:06d}"
    date_earned = cert.certified_at.strftime("%B %d, %Y") if cert.certified_at else "Pending"
    level = cert.certification_level.capitalize()

    teacher_name = re.sub(r"[^\w\s\-']", "", teacher_name)[:100]
    school_name = re.sub(r"[^\w\s\-&']", "", school_name)[:100]

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=1 * inch,
        leftMargin=1 * inch,
        rightMargin=1 * inch,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CertTitle",
        parent=styles["Heading1"],
        fontSize=32,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor("#2C1810"),
    )
    subtitle_style = ParagraphStyle(
        "CertSubtitle",
        parent=styles["Normal"],
        fontSize=16,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor("#5C4F3D"),
    )
    body_style = ParagraphStyle(
        "CertBody",
        parent=styles["Normal"],
        fontSize=14,
        spaceAfter=12,
        alignment=1,
        textColor=colors.HexColor("#333333"),
    )
    name_style = ParagraphStyle(
        "CertName",
        parent=styles["Heading2"],
        fontSize=24,
        spaceAfter=20,
        alignment=1,
        textColor=colors.HexColor("#2C1810"),
    )
    small_style = ParagraphStyle(
        "CertSmall",
        parent=styles["Normal"],
        fontSize=10,
        spaceAfter=6,
        alignment=1,
        textColor=colors.HexColor("#666666"),
    )

    elements = [
        Spacer(1, 0.5 * inch),
        Paragraph("Reading Ambassador Certificate", title_style),
        Paragraph(branding.library_name, subtitle_style),
        Spacer(1, 0.3 * inch),
        Paragraph("This certifies that", body_style),
        Paragraph(teacher_name, name_style),
        Paragraph("has achieved the status of", body_style),
        Paragraph(f"{level} Reading Ambassador", name_style),
        Spacer(1, 0.2 * inch),
        Paragraph(f"for exceptional service to reading programs at {school_name}", body_style),
        Spacer(1, 0.3 * inch),
        Paragraph(f"Date Earned: {date_earned}", body_style),
        Paragraph(f"Certificate Number: {cert_number}", small_style),
    ]

    doc.build(elements)
    buffer.seek(0)

    safe_name = re.sub(r"[^\w\-]", "_", teacher_name)
    filename = f"reading-ambassador-{safe_name}-{cert_number}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@professional_router.put(
    "/ambassador-certifications/{cert_id}", response_model=ReadingAmbassadorCertificationResponse
)
@limiter.limit("60/minute")
async def update_ambassador_certification(
    request: Request,
    cert_id: int,
    update_data: ReadingAmbassadorCertificationUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a reading ambassador certification. Staff only."""
    check_staff_access(current_user)

    cert_result = await db.execute(
        select(ReadingAmbassadorCertification).where(ReadingAmbassadorCertification.id == cert_id)
    )
    cert = cert_result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    update_fields = update_data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(cert, field, value)

    await db.commit()
    await db.refresh(cert)
    return cert


@professional_router.delete(
    "/ambassador-certifications/{cert_id}", status_code=status.HTTP_204_NO_CONTENT
)
@limiter.limit("30/minute")
async def revoke_ambassador_certification(
    request: Request,
    cert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke (soft-delete) a reading ambassador certification. Staff only."""
    check_staff_access(current_user)

    cert_result = await db.execute(
        select(ReadingAmbassadorCertification).where(ReadingAmbassadorCertification.id == cert_id)
    )
    cert = cert_result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    cert.is_active = False
    await db.commit()


@professional_router.post(
    "/ambassador-certifications/{cert_id}/renew",
    response_model=ReadingAmbassadorCertificationResponse,
)
@limiter.limit("30/minute")
async def renew_ambassador_certification(
    request: Request,
    cert_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Renew an expired reading ambassador certification. Staff only."""
    from datetime import timedelta

    check_staff_access(current_user)

    cert_result = await db.execute(
        select(ReadingAmbassadorCertification).where(ReadingAmbassadorCertification.id == cert_id)
    )
    cert = cert_result.scalar_one_or_none()
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")

    now = datetime.now(timezone.utc)
    cert.certified_at = now
    cert.expires_at = now + timedelta(days=365)
    cert.renewal_eligible_at = now + timedelta(days=270)
    cert.is_active = True
    await db.commit()
    await db.refresh(cert)
    return cert


@professional_router.get(
    "/consultation-slots/{school_id}",
    response_model=List[LibrarianConsultationSlotResponse],
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_consultation_slots(
    request: Request,
    school_id: int,
    current_user: User = Depends(require_teacher_of_school),
    db: AsyncSession = Depends(get_db),
):
    """List available librarian consultation slots for a school."""
    query = (
        select(LibrarianConsultationSlot)
        .where(
            and_(
                LibrarianConsultationSlot.partner_id == school_id,
                LibrarianConsultationSlot.is_completed == False,
            )
        )
        .order_by(LibrarianConsultationSlot.scheduled_date)
    )

    result = await db.execute(query)
    slots = result.scalars().all()

    return slots


@professional_router.post(
    "/consultation-slots",
    response_model=LibrarianConsultationSlotResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("60/minute")
async def create_consultation_slot(
    request: Request,
    slot_data: LibrarianConsultationSlotCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a librarian consultation slot. Staff only."""
    check_staff_access(current_user)

    # Verify school exists
    school_result = await db.execute(
        select(OutreachPartner).where(OutreachPartner.id == slot_data.partner_id)
    )
    if not school_result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="School not found")

    slot = LibrarianConsultationSlot(
        partner_id=slot_data.partner_id,
        librarian_id=slot_data.librarian_id,
        title=slot_data.title,
        description=slot_data.description,
        consultation_type=slot_data.consultation_type,
        scheduled_date=slot_data.scheduled_date,
        start_time=slot_data.start_time,
        end_time=slot_data.end_time,
        duration_minutes=slot_data.duration_minutes,
        max_participants=slot_data.max_participants,
    )

    db.add(slot)
    await db.commit()
    await db.refresh(slot)

    return slot


@professional_router.post(
    "/consultation-slots/{slot_id}/register",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def register_for_consultation(
    request: Request,
    slot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register for a librarian consultation slot. Teacher enrollment."""
    # Verify slot exists
    slot = await get_or_404(db, LibrarianConsultationSlot, slot_id, "Slot not found")

    # Per-teacher school scope: teachers may only register for slots at their school.
    assert_teacher_access_to_school(current_user, slot.partner_id)

    if slot.current_participants >= slot.max_participants:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot is full")

    # Check if already registered
    attendee_result = await db.execute(
        select(ConsultationAttendee).where(
            and_(
                ConsultationAttendee.slot_id == slot_id,
                ConsultationAttendee.user_id == current_user.id,
            )
        )
    )
    if attendee_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered for this slot"
        )

    # Create attendee record
    attendee = ConsultationAttendee(
        slot_id=slot_id,
        user_id=current_user.id,
    )

    slot.current_participants += 1
    slot.is_booked = True

    db.add(attendee)
    await db.commit()
    await db.refresh(attendee)

    # Librarian notification (best-effort; targets the slot's specific
    # librarian rather than broadcasting).
    await _notify_librarian_of_teacher_action(
        db,
        teacher=current_user,
        school_id=slot.partner_id,
        action_type="consultation_book",
        payload={
            "slot_id": slot.id,
            "title": slot.title,
            "scheduled_date": slot.scheduled_date.isoformat() if slot.scheduled_date else None,
            "start_time": slot.start_time,
        },
        target_user_id=slot.librarian_id,
    )

    return {"message": "Successfully registered for consultation", "attendee_id": attendee.id}


# ============================================================================
# Librarian Consultation - User-Facing Endpoints
# ============================================================================


@professional_router.get(
    "/schools",
    response_model=List[dict],
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def list_active_schools(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active school partners. Teachers see only their assigned school."""
    conditions = [
        OutreachPartner.partner_type == "school",
        OutreachPartner.status == OutreachPartnerStatus.ACTIVE.value,
    ]
    if current_user.role == UserRole.TEACHER:
        conditions.append(OutreachPartner.id == current_user.school_id)

    query = select(OutreachPartner).where(and_(*conditions)).order_by(OutreachPartner.name)

    result = await db.execute(query)
    schools = result.scalars().all()

    return [
        {
            "id": school.id,
            "name": school.name,
            "address": school.address_line1,
            "city": school.city,
            "state": school.state,
            "partnership_tier": school.partnership_tier,
        }
        for school in schools
    ]


@professional_router.get(
    "/consultation-slots/{school_id}/my-registrations",
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("120/minute")
async def get_user_consultation_registrations(
    request: Request,
    school_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user's consultation registrations for a specific school."""
    # Verify school exists
    await get_or_404(db, OutreachPartner, school_id, "School not found")

    # Get all slots for this school
    query = (
        select(LibrarianConsultationSlot)
        .where(
            and_(
                LibrarianConsultationSlot.partner_id == school_id,
                LibrarianConsultationSlot.is_completed == False,
            )
        )
        .order_by(LibrarianConsultationSlot.scheduled_date)
    )

    result = await db.execute(query)
    slots = result.scalars().all()

    # Find which slots current user is registered for
    slot_ids = [slot.id for slot in slots]
    if not slot_ids:
        return {"registrations": []}

    attendees_result = await db.execute(
        select(ConsultationAttendee, LibrarianConsultationSlot)
        .join(LibrarianConsultationSlot)
        .where(
            and_(
                ConsultationAttendee.user_id == current_user.id,
                ConsultationAttendee.slot_id.in_(slot_ids),
            )
        )
        .order_by(LibrarianConsultationSlot.scheduled_date)
    )
    attendee_records = attendees_result.all()

    registrations = []
    for attendee, slot in attendee_records:
        registrations.append(
            {
                "attendee_id": attendee.id,
                "slot_id": slot.id,
                "title": slot.title,
                "librarian_id": slot.librarian_id,
                "description": slot.description,
                "consultation_type": slot.consultation_type,
                "scheduled_date": slot.scheduled_date.isoformat() if slot.scheduled_date else None,
                "start_time": slot.start_time,
                "end_time": slot.end_time,
                "duration_minutes": slot.duration_minutes,
                "current_participants": slot.current_participants,
                "max_participants": slot.max_participants,
                "registered_at": attendee.registered_at.isoformat()
                if attendee.registered_at
                else None,
            }
        )

    return {"registrations": registrations}


@professional_router.delete(
    "/consultation-slots/{slot_id}/unregister",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_for_teachers_enabled)],
)
@limiter.limit("60/minute")
async def unregister_from_consultation(
    request: Request,
    slot_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Unregister (cancel) a consultation registration. User must be the attendee."""
    # Verify slot exists
    slot = await get_or_404(db, LibrarianConsultationSlot, slot_id, "Slot not found")

    # Find attendee record for current user
    attendee_result = await db.execute(
        select(ConsultationAttendee).where(
            and_(
                ConsultationAttendee.slot_id == slot_id,
                ConsultationAttendee.user_id == current_user.id,
            )
        )
    )
    attendee = attendee_result.scalar_one_or_none()

    if not attendee:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found for this user"
        )

    # Prevent cancellation if consultation already completed
    if slot.is_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot cancel a completed consultation"
        )

    # Capture cancel-grace inputs BEFORE we delete the attendee row.
    booked_at = getattr(attendee, "registered_at", None)
    slot_partner_id = slot.partner_id
    slot_librarian_id = slot.librarian_id
    slot_title = slot.title
    slot_id = slot.id

    # Delete attendee record and decrement participant count
    await db.delete(attendee)
    slot.current_participants = max(0, slot.current_participants - 1)

    # Reset is_booked if no more participants
    if slot.current_participants == 0:
        slot.is_booked = False

    await db.commit()

    # Librarian notification (skip-noise: <60s after book = silent cancel).
    await _notify_librarian_of_teacher_action(
        db,
        teacher=current_user,
        school_id=slot_partner_id,
        action_type="consultation_cancel",
        payload={"slot_id": slot_id, "title": slot_title},
        target_user_id=slot_librarian_id,
        booked_at=booked_at,
    )

    # No response body for 204 NO_CONTENT
