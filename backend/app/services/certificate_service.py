# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
import uuid
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.learning import Certificate, Course, Enrollment
from app.models.user import User
from app.models import (
    CompletionCertificate,
    CertificateTemplate,
    ReadingProgram,
    ReadingRegistration,
)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.platypus import PageBreak
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class CertificateService:

    @staticmethod
    def generate_certificate_number() -> str:
        return f"CERT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

    @staticmethod
    async def get_or_create_certificate(
        db: AsyncSession,
        user_id: int,
        course_id: int
    ) -> Tuple[Certificate, bool]:
        # Check if certificate already exists
        result = await db.execute(
            select(Certificate)
            .where(
                and_(
                    Certificate.user_id == user_id,
                    Certificate.course_id == course_id
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            return existing, False

        # Create new certificate
        certificate_number = CertificateService.generate_certificate_number()

        certificate = Certificate(
            user_id=user_id,
            course_id=course_id,
            certificate_number=certificate_number,
            issued_at=datetime.now(timezone.utc)
        )

        db.add(certificate)
        return certificate, True

    @staticmethod
    async def get_certificate(
        db: AsyncSession,
        certificate_id: int
    ) -> Optional[Certificate]:
        result = await db.execute(
            select(Certificate)
            .options(
                selectinload(Certificate.course)
            )
            .where(Certificate.id == certificate_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_certificates(
        db: AsyncSession,
        user_id: int
    ) -> list:
        result = await db.execute(
            select(Certificate)
            .options(
                selectinload(Certificate.course)
            )
            .where(Certificate.user_id == user_id)
            .order_by(Certificate.issued_at.desc())
        )
        return result.scalars().all()

    @staticmethod
    async def verify_certificate(
        db: AsyncSession,
        certificate_number: str
    ) -> Optional[dict]:
        result = await db.execute(
            select(Certificate)
            .options(
                selectinload(Certificate.course)
            )
            .where(Certificate.certificate_number == certificate_number)
        )
        certificate = result.scalar_one_or_none()

        if not certificate:
            return None

        return {
            "certificate_number": certificate.certificate_number,
            "course_title": certificate.course.title,
            "issued_at": certificate.issued_at.isoformat(),
            "is_valid": True
        }

    @staticmethod
    def generate_pdf_certificate(
        user_name: str,
        course_title: str,
        certificate_number: str,
        issued_date: datetime,
        instructor_name: str = "Learning Center"
    ) -> BytesIO:
        if not REPORTLAB_AVAILABLE:
            return CertificateService._generate_simple_pdf(
                user_name, course_title, certificate_number, issued_date, instructor_name
            )

        return CertificateService._generate_reportlab_pdf(
            user_name, course_title, certificate_number, issued_date, instructor_name
        )

    @staticmethod
    def _generate_simple_pdf(
        user_name: str,
        course_title: str,
        certificate_number: str,
        issued_date: datetime,
        instructor_name: str
    ) -> BytesIO:
        output = BytesIO()

        # Create canvas directly (reportlab should be available for basic functionality)
        try:
            c = canvas.Canvas(output, pagesize=letter)

            # Set up dimensions
            width, height = letter
            center_x = width / 2

            # Background
            c.setFillColor(colors.HexColor("#f5f5f5"))
            c.rect(0.2 * inch, 0.2 * inch, width - 0.4 * inch, height - 0.4 * inch, fill=1)

            # Title
            c.setFont("Helvetica-Bold", 36)
            c.drawCentredString(center_x, height - 1 * inch, "Certificate of Completion")

            # Decorative line
            c.setLineWidth(2)
            c.setStrokeColor(colors.HexColor("#2563eb"))
            c.line(1.5 * inch, height - 1.5 * inch, width - 1.5 * inch, height - 1.5 * inch)

            # Body text
            c.setFont("Helvetica", 14)
            c.drawCentredString(center_x, height - 2.2 * inch, "This certifies that")

            c.setFont("Helvetica-Bold", 28)
            c.drawCentredString(center_x, height - 2.8 * inch, user_name)

            c.setFont("Helvetica", 14)
            c.drawCentredString(center_x, height - 3.4 * inch, "has successfully completed the course")

            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(center_x, height - 4 * inch, course_title)

            # Footer details
            c.setFont("Helvetica", 11)
            issued_str = issued_date.strftime("%B %d, %Y")
            c.drawString(1 * inch, 1.5 * inch, f"Certificate Number: {certificate_number}")
            c.drawString(1 * inch, 1 * inch, f"Issued: {issued_str}")
            c.drawString(1 * inch, 0.5 * inch, f"Issued by: {instructor_name}")

            c.save()
            output.seek(0)
            return output

        except Exception:  # noqa: BLE001 -- PDF render fallback boundary: any reportlab failure degrades to plain-text certificate
            # Fallback to text-based PDF
            return BytesIO(f"Certificate of Completion\n{user_name}\n{course_title}\n{certificate_number}".encode())

    @staticmethod
    def _generate_reportlab_pdf(
        user_name: str,
        course_title: str,
        certificate_number: str,
        issued_date: datetime,
        instructor_name: str
    ) -> BytesIO:
        output = BytesIO()

        try:
            # Create PDF document
            doc = SimpleDocTemplate(output, pagesize=letter)
            story = []

            # Get styles
            styles = getSampleStyleSheet()

            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=42,
                textColor=colors.HexColor("#1e40af"),
                spaceAfter=30,
                alignment=1,  # center
            )

            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Heading2'],
                fontSize=24,
                textColor=colors.HexColor("#1e40af"),
                spaceAfter=20,
                alignment=1,
            )

            body_style = ParagraphStyle(
                'CustomBody',
                parent=styles['Normal'],
                fontSize=14,
                alignment=1,
                spaceAfter=12,
            )

            # Add spacing from top
            story.append(Spacer(1, 0.5 * inch))

            # Title
            story.append(Paragraph("Certificate of Completion", title_style))

            # Decorative line
            story.append(Spacer(1, 0.2 * inch))

            # Content
            story.append(Paragraph("This certifies that", body_style))
            story.append(Spacer(1, 0.2 * inch))

            story.append(Paragraph(f"<b>{user_name}</b>", subtitle_style))

            story.append(Spacer(1, 0.2 * inch))
            story.append(Paragraph("has successfully completed the course", body_style))

            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(f"<b>{course_title}</b>", subtitle_style))

            story.append(Spacer(1, 0.5 * inch))

            # Certificate details
            issued_str = issued_date.strftime("%B %d, %Y")
            details_style = ParagraphStyle(
                'Details',
                parent=styles['Normal'],
                fontSize=11,
                leftIndent=1 * inch,
            )

            story.append(Paragraph(f"Certificate Number: {certificate_number}", details_style))
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(f"Issued: {issued_str}", details_style))
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph(f"Issued by: {instructor_name}", details_style))

            # Build PDF
            doc.build(story)
            output.seek(0)
            return output

        except Exception:  # noqa: BLE001 -- PDF render fallback boundary: any reportlab failure degrades to plain-text certificate
            # If reportlab fails, return simple text
            output = BytesIO()
            output.write(
                f"Certificate of Completion\n{user_name}\n{course_title}\n{certificate_number}".encode()
            )
            output.seek(0)
            return output

    @staticmethod
    async def delete_certificate(
        db: AsyncSession,
        certificate_id: int
    ) -> bool:
        result = await db.execute(
            select(Certificate).where(Certificate.id == certificate_id)
        )
        certificate = result.scalar_one_or_none()

        if certificate:
            await db.delete(certificate)
            return True

        return False


# ============================================================================
# Reading Program Certificate Service
# ============================================================================


class ReadingCertificateService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_certificate(
        self,
        user_id: int,
        program_id: int,
        registration_id: Optional[int] = None,
        completion_date: Optional[datetime] = None,
        reading_goal_achieved: int = 0,
        reading_goal_target: int = 0,
        template_id: Optional[int] = None,
        notes: Optional[str] = None,
    ) -> CompletionCertificate:
        # Verify user exists
        user = await self.db.get(User, user_id)
        if not user:
            raise ValueError(f"User with ID {user_id} not found")

        # Verify program exists
        program = await self.db.get(ReadingProgram, program_id)
        if not program:
            raise ValueError(f"Reading program with ID {program_id} not found")

        # Generate unique certificate code
        certificate_code = self._generate_certificate_code()

        # Use provided date or today
        if completion_date is None:
            completion_date = datetime.now(timezone.utc).date()

        # Get default template if not specified
        if template_id is None:
            template_id = await self._get_default_template_id(program_id)

        # Create new certificate
        certificate = CompletionCertificate(
            certificate_code=certificate_code,
            user_id=user_id,
            program_id=program_id,
            registration_id=registration_id,
            template_id=template_id,
            completion_date=completion_date,
            reading_goal_achieved=reading_goal_achieved,
            reading_goal_target=reading_goal_target,
            issued_at=datetime.now(timezone.utc),
            notes=notes,
        )

        self.db.add(certificate)
        await self.db.flush()

        return certificate

    async def get_certificate(self, certificate_code: str) -> Optional[CompletionCertificate]:
        stmt = select(CompletionCertificate).where(
            CompletionCertificate.certificate_code == certificate_code
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_certificate_by_id(self, certificate_id: int) -> Optional[CompletionCertificate]:
        return await self.db.get(CompletionCertificate, certificate_id)

    async def verify_certificate(
        self,
        certificate_code: str,
        verified_by_user_id: int,
        notes: Optional[str] = None,
    ) -> Optional[CompletionCertificate]:
        # Verify the verifying user exists
        verifier = await self.db.get(User, verified_by_user_id)
        if not verifier:
            raise ValueError(f"User with ID {verified_by_user_id} not found")

        # Get the certificate
        certificate = await self.get_certificate(certificate_code)
        if not certificate:
            return None

        # Mark as verified
        certificate.is_verified = True
        certificate.verified_by_id = verified_by_user_id
        certificate.verified_at = datetime.now(timezone.utc)
        if notes:
            certificate.notes = notes

        await self.db.flush()
        return certificate

    async def email_certificate(
        self,
        certificate_id: int,
        email_address: str,
    ) -> Optional[CompletionCertificate]:
        certificate = await self.get_certificate_by_id(certificate_id)
        if not certificate:
            return None

        certificate.emailed_to = email_address
        certificate.email_sent_at = datetime.now(timezone.utc)

        await self.db.flush()
        return certificate

    async def get_user_certificates(
        self,
        user_id: int,
        program_id: Optional[int] = None,
        verified_only: bool = False,
    ) -> list:
        stmt = select(CompletionCertificate).where(
            CompletionCertificate.user_id == user_id
        )

        if program_id is not None:
            stmt = stmt.where(CompletionCertificate.program_id == program_id)

        if verified_only:
            stmt = stmt.where(CompletionCertificate.is_verified == True)

        stmt = stmt.order_by(CompletionCertificate.issued_at.desc())

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_program_certificates(
        self,
        program_id: int,
        verified_only: bool = False,
    ) -> list:
        stmt = select(CompletionCertificate).where(
            CompletionCertificate.program_id == program_id
        )

        if verified_only:
            stmt = stmt.where(CompletionCertificate.is_verified == True)

        stmt = stmt.order_by(CompletionCertificate.issued_at.desc())

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_template(
        self,
        program_id: Optional[int] = None,
        template_id: Optional[int] = None,
    ) -> Optional[CertificateTemplate]:
        if template_id is not None:
            return await self.db.get(CertificateTemplate, template_id)

        # Get template for program, or org-wide default
        if program_id is not None:
            stmt = select(CertificateTemplate).where(
                (CertificateTemplate.program_id == program_id) |
                (CertificateTemplate.program_id == None)
            ).where(
                CertificateTemplate.is_active == True
            ).order_by(
                CertificateTemplate.program_id.desc()  # Program-specific first
            )
        else:
            # Get org-wide default
            stmt = select(CertificateTemplate).where(
                (CertificateTemplate.program_id == None) &
                (CertificateTemplate.is_active == True) &
                (CertificateTemplate.is_default == True)
            )

        result = await self.db.execute(stmt)
        return result.scalars().first()

    async def get_program_templates(
        self,
        program_id: int,
        include_inactive: bool = False,
    ) -> list:
        stmt = select(CertificateTemplate).where(
            CertificateTemplate.program_id == program_id
        )

        if not include_inactive:
            stmt = stmt.where(CertificateTemplate.is_active == True)

        stmt = stmt.order_by(CertificateTemplate.is_default.desc())

        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def create_template(
        self,
        name: str,
        title_text: str,
        congratulations_text: str,
        recognition_text: str,
        program_id: Optional[int] = None,
        background_color: str = "#FFFFFF",
        accent_color: str = "#0066CC",
        border_style: Optional[str] = None,
        include_logo: bool = True,
        include_seal: bool = True,
        template_file_url: Optional[str] = None,
        is_default: bool = False,
        created_by_id: Optional[int] = None,
        description: Optional[str] = None,
    ) -> CertificateTemplate:
        template = CertificateTemplate(
            name=name,
            description=description,
            program_id=program_id,
            title_text=title_text,
            congratulations_text=congratulations_text,
            recognition_text=recognition_text,
            background_color=background_color,
            accent_color=accent_color,
            border_style=border_style,
            include_logo=include_logo,
            include_seal=include_seal,
            template_file_url=template_file_url,
            is_active=True,
            is_default=is_default,
            created_by_id=created_by_id,
        )

        self.db.add(template)
        await self.db.flush()

        return template

    async def update_certificate_pdf_url(
        self,
        certificate_id: int,
        pdf_url: str,
    ) -> Optional[CompletionCertificate]:
        certificate = await self.get_certificate_by_id(certificate_id)
        if not certificate:
            return None

        certificate.certificate_pdf_url = pdf_url
        await self.db.flush()
        return certificate

    async def update_certificate_badge_url(
        self,
        certificate_id: int,
        badge_url: str,
    ) -> Optional[CompletionCertificate]:
        certificate = await self.get_certificate_by_id(certificate_id)
        if not certificate:
            return None

        certificate.digital_badge_url = badge_url
        await self.db.flush()
        return certificate

    # ========================================================================
    # Private helper methods
    # ========================================================================

    def _generate_certificate_code(self) -> str:
        year = datetime.now().year
        random_suffix = uuid.uuid4().hex[:6].upper()
        return f"CERT-{year}-{random_suffix}"

    async def _get_default_template_id(self, program_id: int) -> Optional[int]:
        template = await self.get_template(program_id=program_id)
        return template.id if template else None
