# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Learning - Certificate API Endpoints

Provides endpoints for:
- Certificate generation
- Certificate listing
- Certificate verification
- PDF download
"""
import re
import uuid
from datetime import datetime, timezone
from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.config import get_settings
from ...core.branding import branding
from ...models.learning import Certificate, Enrollment, Lesson, LessonProgress, Module
from ...models.user import User
from ...schemas.learning import CertificateResponse, CertificateVerify
from ...services.certificate_service import CertificateService
from .auth import get_current_user

router = APIRouter(prefix="/learning", tags=["learning-certificates"])
settings = get_settings()


@router.post("/courses/{course_id}/certificate", response_model=CertificateResponse)
async def generate_certificate(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate certificate for completed course."""
    enrollment_result = await db.execute(
        select(Enrollment)
        .options(selectinload(Enrollment.course))
        .where(Enrollment.user_id == current_user.id, Enrollment.course_id == course_id)
    )
    enrollment = enrollment_result.scalar_one_or_none()

    if not enrollment:
        raise HTTPException(status_code=404, detail="Not enrolled in this course")

    existing = await db.execute(
        select(Certificate).where(
            Certificate.user_id == current_user.id, Certificate.course_id == course_id
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Certificate already issued")

    total_result = await db.execute(
        select(func.count(Lesson.id)).join(Module).where(Module.course_id == course_id)
    )
    total_lessons = total_result.scalar() or 0

    completed_result = await db.execute(
        select(func.count(LessonProgress.id))
        .join(Lesson)
        .join(Module)
        .where(
            Module.course_id == course_id,
            LessonProgress.user_id == current_user.id,
            LessonProgress.status == "completed",
        )
    )
    completed_lessons = completed_result.scalar() or 0

    if completed_lessons < total_lessons:
        raise HTTPException(
            status_code=400,
            detail=f"Please complete all lessons first ({completed_lessons}/{total_lessons} done)",
        )

    cert_number = f"{branding.CARD_PREFIX}-{uuid.uuid4().hex[:8].upper()}"
    certificate = Certificate(
        user_id=current_user.id, course_id=course_id, certificate_number=cert_number
    )
    db.add(certificate)

    enrollment.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(certificate)

    return CertificateResponse(
        id=certificate.id,
        user_id=certificate.user_id,
        course_id=certificate.course_id,
        certificate_number=certificate.certificate_number,
        issued_at=certificate.issued_at,
        course_title=enrollment.course.title,
    )


@router.get("/certificates", response_model=list[CertificateResponse])
async def list_certificates(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """List user's certificates."""
    result = await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.course))
        .where(Certificate.user_id == current_user.id)
        .order_by(Certificate.issued_at.desc())
    )
    certificates = result.scalars().all()

    return [
        CertificateResponse(
            id=cert.id,
            user_id=cert.user_id,
            course_id=cert.course_id,
            certificate_number=cert.certificate_number,
            issued_at=cert.issued_at,
            course_title=cert.course.title,
        )
        for cert in certificates
    ]


@router.get("/certificates/{cert_number}/verify", response_model=CertificateVerify)
async def verify_certificate(cert_number: str, db: AsyncSession = Depends(get_db)):
    """Verify a certificate (public endpoint)."""
    result = await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.course))
        .where(Certificate.certificate_number == cert_number)
    )
    certificate = result.scalar_one_or_none()

    if not certificate:
        raise HTTPException(status_code=404, detail="Certificate not found")

    user_result = await db.execute(select(User).where(User.id == certificate.user_id))
    user = user_result.scalar_one()

    first_name = (user.first_name or "").strip()
    if not first_name:
        full = (user.full_name or "").strip()
        first_name = full.split()[0] if full else ""

    return CertificateVerify(
        certificate_number=certificate.certificate_number,
        user_name=user.full_name,
        recipient_first_name=first_name,
        course_title=certificate.course.title,
        issued_at=certificate.issued_at,
        is_valid=True,
    )


@router.get("/certificates/{course_id}/download")
async def download_certificate_pdf(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate and download a PDF certificate for a completed course."""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib.utils import ImageReader
    from reportlab.platypus import (
        Image as RLImage,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    cert_result = await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.course))
        .where(
            Certificate.user_id == current_user.id, Certificate.course_id == course_id
        )
    )
    certificate = cert_result.scalar_one_or_none()

    if not certificate:
        raise HTTPException(
            status_code=404,
            detail="Certificate not found. Please complete the course first.",
        )

    course = certificate.course

    safe_first_name = str(current_user.first_name or "").strip()[:50]
    safe_last_name = str(current_user.last_name or "").strip()[:50]
    safe_course_title = str(course.title or "").strip()[:100]

    safe_first_name = re.sub(r"[^\w\s\-]", "", safe_first_name)
    safe_last_name = re.sub(r"[^\w\s\-]", "", safe_last_name)
    safe_course_title = re.sub(r"[^\w\s\-&]", "", safe_course_title)

    if not safe_first_name:
        safe_first_name = current_user.email.split("@")[0]
    if not safe_last_name:
        safe_last_name = ""

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CertificateTitle",
        parent=styles["Heading1"],
        fontSize=36,
        spaceAfter=30,
        alignment=1,
        textColor=colors.HexColor("#2C1810"),
    )

    subtitle_style = ParagraphStyle(
        "CertificateSubtitle",
        parent=styles["Normal"],
        fontSize=18,
        spaceAfter=40,
        alignment=1,
        textColor=colors.HexColor("#5C4F3D"),
    )

    body_style = ParagraphStyle(
        "CertificateBody",
        parent=styles["Normal"],
        fontSize=14,
        spaceAfter=20,
        alignment=1,
    )

    name_style = ParagraphStyle(
        "Name",
        parent=styles["Heading2"],
        fontSize=24,
        alignment=1,
        textColor=colors.HexColor("#8B7B6A"),
        spaceAfter=20,
    )

    course_title_style = ParagraphStyle(
        "CourseTitle",
        parent=styles["Heading2"],
        fontSize=20,
        alignment=1,
        textColor=colors.HexColor("#2C1810"),
        spaceAfter=30,
    )

    signature_style = ParagraphStyle(
        "Signature", parent=styles["Normal"], fontSize=12, alignment=1
    )

    footer_style = ParagraphStyle(
        "Footer",
        parent=styles["Normal"],
        fontSize=10,
        alignment=1,
        textColor=colors.gray,
    )

    content = []

    content.append(Paragraph("Certificate of Completion", title_style))
    content.append(Spacer(1, 20))
    content.append(Paragraph(settings.library_name, subtitle_style))
    content.append(Paragraph("This is to certify that", body_style))
    content.append(Spacer(1, 10))

    full_name = f"{safe_first_name} {safe_last_name}".strip()
    content.append(Paragraph(full_name, name_style))

    content.append(
        Paragraph("has successfully completed the training course", body_style)
    )
    content.append(Spacer(1, 10))

    content.append(Paragraph(f"{safe_course_title}", course_title_style))

    completion_date = certificate.issued_at
    date_str = completion_date.strftime("%B %d, %Y")
    content.append(Paragraph(f"Completed on: {date_str}", body_style))
    content.append(Spacer(1, 30))

    difficulty = course.difficulty.title() if course.difficulty else "General"
    stats_data = [
        ["Difficulty Level:", difficulty],
        ["Estimated Duration:", f"{course.estimated_minutes or 0} minutes"],
    ]

    stats_table = Table(stats_data, colWidths=[2 * inch, 4 * inch])
    stats_table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 12),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    content.append(stats_table)
    content.append(Spacer(1, 40))

    content.append(Paragraph("_______________________________", signature_style))
    content.append(Paragraph("Library Director", signature_style))
    content.append(Paragraph(settings.library_name, signature_style))

    content.append(Spacer(1, 60))

    # Build QR code pointing at the public verification page so anyone who
    # receives the PDF (LinkedIn share, printout, etc.) can validate the
    # certificate without typing the cert number by hand.
    frontend_base = (settings.frontend_url or "").rstrip("/")
    verify_url = f"{frontend_base}/verify/{certificate.certificate_number}"
    qr_flowable = None
    try:
        import qrcode

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=2,
        )
        qr.add_data(verify_url)
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_buf = BytesIO()
        qr_img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        qr_flowable = RLImage(ImageReader(qr_buf), width=1.1 * inch, height=1.1 * inch)
    except Exception:  # noqa: BLE001  # QR is optional; printed verify URL is fallback
        # QR is optional; the printed verify URL is sufficient fallback.
        qr_flowable = None

    footer_left = [
        Paragraph(
            f"Certificate ID: {certificate.certificate_number}", footer_style
        ),
        Paragraph(f"Verify at: {verify_url}", footer_style),
    ]
    if qr_flowable is not None:
        footer_table = Table(
            [[footer_left, qr_flowable]],
            colWidths=[5.0 * inch, 1.5 * inch],
        )
        footer_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )
        content.append(footer_table)
    else:
        for flow in footer_left:
            content.append(flow)

    doc.build(content)
    buffer.seek(0)

    filename = (
        f"certificate_{safe_course_title.replace(' ', '_')}_{safe_first_name}.pdf"
    )

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



@router.get("/courses/{course_id}/certificate/pdf")
async def download_certificate_pdf_alias(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Alias for certificate PDF download (frontend compatibility)."""
    return await download_certificate_pdf(course_id, db=db, current_user=current_user)

@router.get("/courses/{course_id}/certificate", response_model=CertificateResponse)
async def get_courses__course_id__certificate(
    course_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get certificate info for a completed course."""
    result = await db.execute(
        select(Certificate)
        .options(selectinload(Certificate.course))
        .where(Certificate.user_id == current_user.id, Certificate.course_id == course_id)
    )
    certificate = result.scalar_one_or_none()

    if not certificate:
        raise HTTPException(status_code=404, detail="No certificate earned for this course")

    return CertificateResponse(
        id=certificate.id,
        user_id=certificate.user_id,
        course_id=certificate.course_id,
        certificate_number=certificate.certificate_number,
        issued_at=certificate.issued_at,
        course_title=certificate.course.title,
    )
