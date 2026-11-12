# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board Report Generation API endpoints.

Provides endpoints for:
- Generating board reports with stats and visualizations
- Managing report templates and customization
- Scheduling automatic report generation
- Exporting to PowerPoint and PDF formats
- Email distribution to board members
"""

import io
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.exceptions import InternalServerError
from ....core.error_codes import ErrorCode
from ....models.board.report import (
    BoardReport, BoardReportTemplate, BoardReportSchedule
)
from ....schemas.board import (
    BoardReportGenerateRequest, BoardReportResponse,
    BoardReportTemplateCreate, BoardReportTemplateUpdate, BoardReportTemplateResponse,
    BoardReportScheduleCreate, BoardReportScheduleUpdate, BoardReportScheduleResponse,
)
from ....services.board_report_service import BoardReportService
from ....services.board_report_generator import BoardReportGenerator
from ....services.board_report_email_service import BoardReportEmailService
from ....models.user import User, UserRole
from ..auth import get_current_user

router = APIRouter(prefix="/board/reports", tags=["board-reports"])

logger = get_logger(__name__)


# ============ Report Generation Endpoints ============


@router.post("/generate", response_model=BoardReportResponse)
async def generate_board_report(
    request: BoardReportGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Generate a new board report for specified date range.

    Aggregates:
    - Circulation statistics and trends
    - Financial metrics and revenue
    - Patron engagement data
    - Collection status and availability
    - Comparison to previous period (optional)

    Returns report data with optional PowerPoint/PDF files.
    """
    # Check authorization (must be staff or admin)
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    try:
        service = BoardReportService(db)

        # Generate report data
        report_data = await service.generate_board_report(
            start_date=request.start_date,
            end_date=request.end_date,
            template_id=request.template_id,
            comparison_enabled=request.include_comparison,
        )

        # Get narrative prompts for board discussion
        narrative_prompts = await service.get_narrative_prompts(report_data)
        report_data["narrative_prompts"] = narrative_prompts

        # Save report to database
        db_report = await service.save_report_to_db(
            report_data=report_data,
            template_id=request.template_id,
            recipient_emails=request.send_to_emails,
            created_by_id=current_user.id,
        )

        # Generate export files if requested
        if request.export_format in ["powerpoint", "both"]:
            template = await service.get_template_by_id(request.template_id) if request.template_id else None
            template_config = template.branding if template and template.branding else {}

            generator = BoardReportGenerator(template_config)
            pptx_content = generator.generate_powerpoint(
                report_data=report_data,
                title="Board Report",
                organization="Library System",
            )

            db_report.file_powerpoint = pptx_content

        if request.export_format in ["pdf", "both"]:
            template = await service.get_template_by_id(request.template_id) if request.template_id else None
            template_config = template.branding if template and template.branding else {}

            generator = BoardReportGenerator(template_config)
            pdf_content = generator.generate_pdf(
                report_data=report_data,
                title="Board Report",
                organization="Library System",
            )

            db_report.file_pdf = pdf_content

        db_report.format_generated = request.export_format
        db_report.generated_at = datetime.now(timezone.utc)
        db_report.status = "generated"

        await db.commit()
        await db.refresh(db_report)

        return db_report

    except Exception:
        logger.exception("Error generating board report")
        raise InternalServerError(code=ErrorCode.INTERNAL_ERROR) from None


@router.get("/{report_id}", response_model=BoardReportResponse)
async def get_board_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Retrieve a specific board report."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReport).where(BoardReport.id == report_id)
    result = await db.execute(query)
    report = result.scalars().first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return report


@router.get("", response_model=List[BoardReportResponse])
async def list_board_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List archived board reports with pagination."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReport).order_by(
        BoardReport.created_at.desc()
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    reports = result.scalars().all()

    return reports


@router.get("/{report_id}/powerpoint")
async def download_powerpoint(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Download board report as PowerPoint file."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReport).where(BoardReport.id == report_id)
    result = await db.execute(query)
    report = result.scalars().first()

    if not report or not report.file_powerpoint:
        raise HTTPException(status_code=404, detail="PowerPoint file not found")

    return StreamingResponse(
        io.BytesIO(report.file_powerpoint),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=board_report_{report_id}.pptx"},
    )


@router.get("/{report_id}/pdf")
async def download_pdf(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Download board report as PDF file."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReport).where(BoardReport.id == report_id)
    result = await db.execute(query)
    report = result.scalars().first()

    if not report or not report.file_pdf:
        raise HTTPException(status_code=404, detail="PDF file not found")

    return StreamingResponse(
        io.BytesIO(report.file_pdf),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=board_report_{report_id}.pdf"},
    )


# ============ Template Management Endpoints ============


@router.post("/templates", response_model=BoardReportTemplateResponse)
async def create_template(
    template: BoardReportTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create a new board report template."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    db_template = BoardReportTemplate(
        **template.model_dump(),
        created_by=current_user.id,
    )

    db.add(db_template)
    await db.commit()
    await db.refresh(db_template)

    return db_template


@router.get("/templates", response_model=List[BoardReportTemplateResponse])
async def list_templates(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
):
    """List available report templates."""
    query = select(BoardReportTemplate)
    if active_only:
        query = query.where(BoardReportTemplate.is_active == True)
    query = query.order_by(BoardReportTemplate.is_default.desc())

    result = await db.execute(query)
    return result.scalars().all()


# ============ Schedule Management Endpoints ============


@router.post("/schedules", response_model=BoardReportScheduleResponse)
async def create_schedule(
    schedule: BoardReportScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Create a new report generation schedule."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    db_schedule = BoardReportSchedule(
        **schedule.model_dump(),
        created_by=current_user.id,
        next_run_at=datetime.now(timezone.utc),
    )

    db.add(db_schedule)
    await db.commit()
    await db.refresh(db_schedule)

    logger.info(f"Created report schedule: {db_schedule.id}")
    return db_schedule


@router.get("/schedules", response_model=List[BoardReportScheduleResponse])
async def list_schedules(
    active_only: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """List report generation schedules."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReportSchedule)
    if active_only:
        query = query.where(BoardReportSchedule.is_active == True)
    query = query.order_by(BoardReportSchedule.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/schedules/{schedule_id}", response_model=BoardReportScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Get a specific report schedule."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReportSchedule).where(BoardReportSchedule.id == schedule_id)
    result = await db.execute(query)
    schedule = result.scalars().first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule


@router.put("/schedules/{schedule_id}", response_model=BoardReportScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule: BoardReportScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Update a report generation schedule."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReportSchedule).where(BoardReportSchedule.id == schedule_id)
    result = await db.execute(query)
    db_schedule = result.scalars().first()

    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    update_data = schedule.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_schedule, field, value)

    db_schedule.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(db_schedule)

    return db_schedule


@router.delete("/schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Delete a report generation schedule."""
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReportSchedule).where(BoardReportSchedule.id == schedule_id)
    result = await db.execute(query)
    db_schedule = result.scalars().first()

    if not db_schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await db.delete(db_schedule)
    await db.commit()

    return {"message": "Schedule deleted successfully"}


# ============ Quick-Access Endpoints ============


@router.get("/quick/monthly-report")
async def get_monthly_report(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Generate a quick monthly board report for the current month.

    Convenience endpoint for month-end board prep in 10 minutes.
    """
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    today = datetime.now(timezone.utc)
    # Current month
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_end = today

    # Previous month for comparison (reserved for future use)
    # first_day_this_month = today.replace(day=1)
    # last_day_prev_month = first_day_this_month - timedelta(days=1)
    # prev_month_start = last_day_prev_month.replace(day=1)

    service = BoardReportService(db)

    try:
        report_data = await service.generate_board_report(
            start_date=month_start,
            end_date=month_end,
            comparison_enabled=True,
        )

        # Add narrative prompts
        prompts = await service.get_narrative_prompts(report_data)
        report_data["narrative_prompts"] = prompts

        return report_data

    except Exception:
        logger.exception("Error generating monthly report")
        raise InternalServerError(code=ErrorCode.INTERNAL_ERROR) from None


# ============ Email Distribution Endpoints ============


@router.post("/{report_id}/send-email")
async def send_report_email(
    report_id: int,
    emails: List[str],
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Send a generated board report to specified email addresses.

    Attaches PowerPoint and/or PDF files if available.
    """
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReport).where(BoardReport.id == report_id)
    result = await db.execute(query)
    report = result.scalars().first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if not report.file_powerpoint and not report.file_pdf:
        raise HTTPException(status_code=400, detail="Report has no export files to send")

    success, error = await BoardReportEmailService.send_report_to_recipients(
        db=db,
        report=report,
        recipient_emails=emails,
        include_attachments=True,
    )

    if success:
        return {"message": f"Report sent to {len(emails)} recipient(s)", "success": True}
    else:
        return {"message": error or "Failed to send report", "success": False}


@router.get("/{report_id}/stats")
async def get_report_stats(
    report_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Get the statistics snapshot for a specific report.

    Returns the full stats data used for charts and visualizations.
    """
    if not current_user or current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    query = select(BoardReport).where(BoardReport.id == report_id)
    result = await db.execute(query)
    report = result.scalars().first()

    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "title": report.title,
        "stats_snapshot": report.stats_snapshot,
        "key_metrics": report.key_metrics,
        "narrative_prompts": report.narrative_prompts,
        "executive_summary": report.executive_summary,
    }
