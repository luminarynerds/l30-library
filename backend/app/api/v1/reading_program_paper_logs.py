# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Reading-program paper log and kiosk redemption routes."""

import io

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.reading import ReadingLogEntry, ReadingProgram, ReadingRegistration
from ...models.user import User
from ...schemas.reading import (
    PaperLogCodeResponse,
    PaperLogRedeemRequest,
    PaperLogRedeemResponse,
)
from ...services.paper_log_service import (
    force_regenerate_code,
    generate_or_get_code,
    redeem_code,
)
from .auth import get_current_user
from .dependencies import check_staff_access, is_staff_or_admin
from .feature_guards import require_reading_programs_paper_log_enabled

paper_log_router = APIRouter()


def _build_paper_log_pdf(
    *,
    library_name: str,
    program: ReadingProgram,
    patron_name: str,
    code: str,
    redeem_url: str,
) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.platypus import (
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=LETTER,
        leftMargin=0.6 * inch,
        rightMargin=0.6 * inch,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch,
        title=f"{program.name} - Reading Log",
    )
    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(f"<b>{library_name}</b>", styles["Title"]))
    story.append(Paragraph(program.name, styles["Heading2"]))
    story.append(Paragraph(f"Reader: <b>{patron_name}</b>", styles["Normal"]))
    if program.reading_goal_value and program.reading_goal_type:
        story.append(
            Paragraph(
                f"Goal: {program.reading_goal_value} {program.reading_goal_type}",
                styles["Normal"],
            )
        )
    story.append(
        Paragraph(
            f"Program runs {program.start_date.isoformat()} to {program.end_date.isoformat()}.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 0.18 * inch))

    header = ["Date", "Title", "Author", "Quantity", "Notes"]
    rows = [header] + [["", "", "", "", ""] for _ in range(20)]
    tbl = Table(
        rows,
        colWidths=[0.9 * inch, 2.2 * inch, 1.4 * inch, 0.9 * inch, 1.8 * inch],
        rowHeights=[0.28 * inch] + [0.32 * inch] * 20,
    )
    tbl.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 0.2 * inch))

    story.append(
        Paragraph(
            f"<b>Claim code:</b> <font size=16><b>{code}</b></font>",
            styles["Normal"],
        )
    )
    story.append(
        Paragraph(
            f"Bring this sheet to the desk or enter the code at "
            f"<b>{redeem_url}</b> to credit your entries.",
            styles["Normal"],
        )
    )

    try:
        import qrcode  # type: ignore
        from reportlab.lib.utils import ImageReader
        from reportlab.platypus import Image as RLImage

        qr = qrcode.QRCode(box_size=4, border=2)
        qr.add_data(redeem_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        qr_buf = io.BytesIO()
        img.save(qr_buf, format="PNG")
        qr_buf.seek(0)
        story.append(Spacer(1, 0.1 * inch))
        story.append(RLImage(ImageReader(qr_buf), width=1.1 * inch, height=1.1 * inch))
    except Exception:  # noqa: BLE001  # QR optional; printed URL is fallback
        # QR optional; printed URL is sufficient fallback.
        pass

    doc.build(story)
    return buf.getvalue()


@paper_log_router.get(
    "/programs/{program_id}/registrations/{registration_id}/log.pdf",
    dependencies=[Depends(require_reading_programs_paper_log_enabled)],
)
async def get_paper_log_pdf(
    program_id: int,
    registration_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate (or refresh) a paper log PDF for a registration."""
    registration = await get_or_404(
        db, ReadingRegistration, registration_id, "Registration not found"
    )
    if registration.program_id != program_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    is_staff = is_staff_or_admin(current_user)
    if not is_staff and registration.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your registration")

    program = await get_or_404(db, ReadingProgram, program_id, "Program not found")
    user = await get_or_404(db, User, registration.user_id, "User not found")

    code = await generate_or_get_code(db, registration)

    base = f"{request.url.scheme}://{request.url.netloc}"
    redeem_url = f"{base}/programs/redeem?code={code}"

    library_name = "Library"
    try:
        from ...models.organization_features import OrganizationFeatures

        result = await db.execute(select(OrganizationFeatures).limit(1))
        feat = result.scalar_one_or_none()
        if feat and getattr(feat, "library_name", None):
            library_name = feat.library_name
    except Exception:  # noqa: BLE001  # library name lookup best-effort — fall back to default
        pass

    patron_name = " ".join(
        n for n in [getattr(user, "first_name", None), getattr(user, "last_name", None)] if n
    ) or (getattr(user, "email", None) or "Reader")

    pdf_bytes = _build_paper_log_pdf(
        library_name=library_name,
        program=program,
        patron_name=patron_name,
        code=code,
        redeem_url=redeem_url,
    )
    headers = {"Content-Disposition": (f'attachment; filename="reading-log-{registration.id}.pdf"')}
    return StreamingResponse(io.BytesIO(pdf_bytes), media_type="application/pdf", headers=headers)


@paper_log_router.post(
    "/redeem",
    response_model=PaperLogRedeemResponse,
    dependencies=[Depends(require_reading_programs_paper_log_enabled)],
)
async def redeem_paper_log(
    payload: PaperLogRedeemRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Redeem a paper log claim code; bulk-insert entries; fire badge check."""
    is_staff = is_staff_or_admin(current_user)
    try:
        entry_dicts = [e.model_dump() for e in payload.entries]
        registration, program, created = await redeem_code(db, payload.code, entry_dicts)
    except ValueError as err:
        token = str(err)
        if token == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Code not found"
            ) from err
        if token == "already_redeemed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Code already redeemed",
            ) from err
        if token == "expired":
            raise HTTPException(status_code=status.HTTP_410_GONE, detail="Code expired") from err
        if token == "invalid_entry":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Entry validation failed",
            ) from err
        raise

    if not is_staff and registration.user_id != current_user.id:
        # Unwind: refund redemption so the code is reusable.
        registration.paper_log_code_redeemed_at = None
        for row in created:
            await db.delete(row)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your code")

    totals_result = await db.execute(
        select(
            func.coalesce(func.sum(ReadingLogEntry.books_read), 0),
            func.coalesce(func.sum(ReadingLogEntry.minutes_read), 0),
            func.coalesce(func.sum(ReadingLogEntry.pages_read), 0),
        ).where(ReadingLogEntry.registration_id == registration.id)
    )
    total_books, total_minutes, total_pages = totals_result.one()

    goal_percent = 0.0
    goal_value = program.reading_goal_value or 0
    goal_type = (program.reading_goal_type or "").lower()
    if goal_value:
        if goal_type == "books":
            goal_percent = (total_books / goal_value) * 100.0
        elif goal_type == "minutes":
            goal_percent = (total_minutes / goal_value) * 100.0
        elif goal_type == "pages":
            goal_percent = (total_pages / goal_value) * 100.0

    from ...services.reading_achievement_service import ReadingAchievementService

    new_achievements = 0
    try:
        ach_service = ReadingAchievementService(db)
        new = await ach_service.check_and_award_achievements(
            user_id=registration.user_id,
            program_id=registration.program_id,
            registration_id=registration.id,
        )
        new_achievements = len(new)
    except Exception:  # noqa: BLE001  # badge errors must not fail redemption
        # Never fail redemption on badge-side errors.
        pass

    return PaperLogRedeemResponse(
        registration_id=registration.id,
        program_id=registration.program_id,
        entries_created=len(created),
        new_achievements=new_achievements,
        total_books=int(total_books),
        total_minutes=int(total_minutes),
        total_pages=int(total_pages),
        goal_percent=round(min(goal_percent, 999.99), 2),
    )


@paper_log_router.post(
    "/programs/{program_id}/registrations/{registration_id}/reset-log-code",
    response_model=PaperLogCodeResponse,
    dependencies=[Depends(require_reading_programs_paper_log_enabled)],
)
async def reset_paper_log_code(
    program_id: int,
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Staff: force-regenerate a paper log code (lost-sheet path)."""
    check_staff_access(current_user)
    registration = await get_or_404(
        db, ReadingRegistration, registration_id, "Registration not found"
    )
    if registration.program_id != program_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")
    new_code = await force_regenerate_code(db, registration)
    return PaperLogCodeResponse(
        registration_id=registration.id,
        paper_log_code=new_code,
        paper_log_code_generated_at=registration.paper_log_code_generated_at,
    )
