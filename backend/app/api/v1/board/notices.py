# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Board public meeting notice compliance API endpoints."""

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.board import BoardMeeting, BoardMember
from ....models.board.compliance_profile import BoardStateComplianceProfile
from ....models.user import User, UserRole
from ....schemas.board import (
    NoticeComplianceStatus,
    NoticeGenerateRequest,
    NoticePostingLocation,
    NoticePostRequest,
    NoticeResponse,
)
from ..auth import get_current_user

router = APIRouter(tags=["board-notices"])


# ============ Notice Generation Endpoints ============


@router.post("/board/meetings/{meeting_id}/notice/generate", response_model=NoticeResponse)
async def generate_meeting_notice(
    meeting_id: int,
    request: NoticeGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a public meeting notice (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    # Get meeting with agenda items
    result = await db.execute(
        select(BoardMeeting)
        .options(selectinload(BoardMeeting.agenda_items))
        .where(BoardMeeting.id == meeting_id)
    )
    meeting = result.scalar_one_or_none()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400, detail="Cannot generate notice for a cancelled meeting"
        )

    # Generate notice content
    notice_lines = []

    # Header
    if request.custom_header:
        notice_lines.append(request.custom_header)
        notice_lines.append("")
    else:
        notice_lines.append("PUBLIC MEETING NOTICE")
        notice_lines.append("=" * 40)
        notice_lines.append("")

    # Meeting details
    notice_lines.append(f"MEETING: {meeting.title}")
    notice_lines.append(f"TYPE: {meeting.meeting_type.upper()}")
    notice_lines.append(f"DATE: {meeting.scheduled_date.strftime('%A, %B %d, %Y')}")

    if meeting.start_time:
        notice_lines.append(f"TIME: {meeting.start_time.strftime('%I:%M %p')}")
        if meeting.end_time:
            notice_lines.append(f"      to {meeting.end_time.strftime('%I:%M %p')}")

    notice_lines.append("")

    # Location
    if meeting.is_virtual:
        notice_lines.append("LOCATION: Virtual Meeting")
        if meeting.virtual_meeting_url:
            notice_lines.append(f"JOIN URL: {meeting.virtual_meeting_url}")
    elif meeting.location:
        notice_lines.append(f"LOCATION: {meeting.location}")

    notice_lines.append("")

    # Description
    if meeting.description:
        notice_lines.append("DESCRIPTION:")
        notice_lines.append(meeting.description)
        notice_lines.append("")

    # Agenda
    if request.include_agenda and meeting.agenda_items:
        notice_lines.append("AGENDA:")
        notice_lines.append("-" * 40)
        for item in sorted(meeting.agenda_items, key=lambda x: x.sort_order):
            line = f"{item.item_number}. {item.title}"
            if item.presenter:
                line += f" ({item.presenter})"
            if item.estimated_duration_minutes:
                line += f" [{item.estimated_duration_minutes} min]"
            notice_lines.append(line)
            if item.description:
                notice_lines.append(f"   {item.description}")
        notice_lines.append("")

    # Executive session notice
    if meeting.has_executive_session:
        notice_lines.append("EXECUTIVE SESSION NOTICE:")
        notice_lines.append(
            "This meeting may include an executive (closed) session as permitted by law."
        )
        if meeting.executive_session_reason:
            notice_lines.append(f"Purpose: {meeting.executive_session_reason}")
        notice_lines.append("")

    # Public comment
    if meeting.public_comment_enabled:
        notice_lines.append("PUBLIC COMMENT:")
        notice_lines.append("Members of the public are welcome to attend and participate.")
        if meeting.public_comment_instructions:
            notice_lines.append(meeting.public_comment_instructions)
        notice_lines.append("")

    # Accessibility
    if request.include_accessibility_info:
        notice_lines.append("ACCESSIBILITY:")
        if meeting.accessibility_info:
            notice_lines.append(meeting.accessibility_info)
        else:
            notice_lines.append(
                "Reasonable accommodations for individuals with disabilities are available "
                "upon request. Please contact the library at least 48 hours in advance."
            )
        notice_lines.append("")

    # Footer
    if request.custom_footer:
        notice_lines.append(request.custom_footer)
    else:
        notice_lines.append("-" * 40)
        notice_lines.append(f"Notice generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    notice_content = "\n".join(notice_lines)

    # Save notice content to meeting
    meeting.notice_content = notice_content
    meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return NoticeResponse(
        meeting_id=meeting_id,
        notice_content=notice_content,
        generated_at=datetime.now(timezone.utc),
        includes_agenda=request.include_agenda and bool(meeting.agenda_items),
        includes_accessibility_info=request.include_accessibility_info,
    )


@router.post("/board/meetings/{meeting_id}/notice/post")
async def post_meeting_notice(
    meeting_id: int,
    request: NoticePostRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record that a meeting notice has been posted to a location (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400, detail="Cannot post notice for a cancelled meeting"
        )

    # Add posting location
    posting_locations = meeting.notice_posting_locations or []
    new_location = {
        "location": request.location,
        "url": request.url,
        "posted_at": datetime.now(timezone.utc).isoformat(),
        "notes": request.notes,
    }
    posting_locations.append(new_location)

    meeting.notice_posting_locations = posting_locations

    # Update notice status if this is the first posting
    if meeting.notice_status == "not_posted" or meeting.notice_status == "draft":
        meeting.notice_status = "posted"
        meeting.notice_posted_at = datetime.now(timezone.utc)
        meeting.notice_posted_by_id = current_user.id

    meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "message": f"Notice posted to {request.location}",
        "notice_status": meeting.notice_status,
        "posting_locations": meeting.notice_posting_locations,
    }


# ============ Compliance Checking Endpoints ============


@router.get("/board/meetings/{meeting_id}/notice/compliance", response_model=NoticeComplianceStatus)
async def check_notice_compliance(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Check public meeting notice compliance status (staff/admin/board members)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        # Check if user is a board member
        result = await db.execute(
            select(BoardMember).where(
                BoardMember.user_id == current_user.id, BoardMember.is_current == True
            )
        )
        if not result.scalar_one_or_none():
            raise HTTPException(
                status_code=403, detail="Board member or staff access required"
            )

    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    compliance_issues = []
    is_compliant = True

    # Load active state compliance profile for authoritative lead time
    profile_result = await db.execute(
        select(BoardStateComplianceProfile).where(
            BoardStateComplianceProfile.is_active == True
        )
    )
    active_profile = profile_result.scalar_one_or_none()

    if active_profile:
        required_lead_hours = active_profile.notice_lead_hours
        citation = active_profile.open_meeting_law_citation or "state law"
    else:
        required_lead_hours = meeting.notice_lead_days_required * 24
        citation = "local policy"

    # Calculate lead time
    actual_lead_days = None
    if meeting.notice_posted_at:
        time_diff = meeting.scheduled_date - meeting.notice_posted_at
        actual_lead_hours = time_diff.total_seconds() / 3600
        actual_lead_days = actual_lead_hours / 24

        if actual_lead_hours < required_lead_hours:
            is_compliant = False
            compliance_issues.append(
                f"Notice posted {actual_lead_hours:.1f}h before meeting, "
                f"but {required_lead_hours}h required ({citation})"
            )
    else:
        if meeting.notice_status == "not_posted":
            is_compliant = False
            compliance_issues.append("Notice has not been posted")

    # Check if agenda is published
    agenda_published = meeting.agenda_published_at is not None
    if not agenda_published:
        compliance_issues.append("Agenda has not been published")

    # Check posting locations
    posting_locations = meeting.notice_posting_locations or []
    if len(posting_locations) == 0 and meeting.notice_status != "not_posted":
        compliance_issues.append("No posting locations recorded")

    # Check accessibility info
    has_accessibility_info = bool(meeting.accessibility_info)
    if not has_accessibility_info:
        compliance_issues.append("No accessibility information provided")

    # Executive session without reason
    if meeting.has_executive_session and not meeting.executive_session_reason:
        compliance_issues.append("Executive session marked but no legal reason provided")

    # Convert posting locations to schema format
    location_schemas = [
        NoticePostingLocation(
            location=loc.get("location", ""),
            url=loc.get("url"),
            posted_at=datetime.fromisoformat(loc["posted_at"]) if loc.get("posted_at") else None,
            notes=loc.get("notes"),
        )
        for loc in posting_locations
    ]

    return NoticeComplianceStatus(
        meeting_id=meeting_id,
        meeting_title=meeting.title,
        scheduled_date=meeting.scheduled_date,
        notice_status=meeting.notice_status,
        notice_posted_at=meeting.notice_posted_at,
        notice_lead_days_required=meeting.notice_lead_days_required,
        actual_lead_days=actual_lead_days,
        is_compliant=is_compliant and len(compliance_issues) == 0,
        compliance_issues=compliance_issues,
        posting_locations=location_schemas,
        agenda_published=agenda_published,
        has_accessibility_info=has_accessibility_info,
    )


@router.get("/board/notices/compliance-report", response_model=List[NoticeComplianceStatus])
async def get_compliance_report(
    upcoming_only: bool = Query(True, description="Only check upcoming meetings"),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get compliance report for multiple meetings (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    query = select(BoardMeeting).where(BoardMeeting.is_cancelled == False)
    if upcoming_only:
        query = query.where(BoardMeeting.scheduled_date >= datetime.now(timezone.utc))
    query = query.order_by(BoardMeeting.scheduled_date.asc()).limit(limit)

    result = await db.execute(query)
    meetings = result.scalars().all()

    compliance_reports = []
    for meeting in meetings:
        compliance_issues = []
        is_compliant = True

        # Calculate lead time
        actual_lead_days = None
        if meeting.notice_posted_at:
            time_diff = meeting.scheduled_date - meeting.notice_posted_at
            actual_lead_days = time_diff.total_seconds() / (24 * 3600)

            if actual_lead_days < meeting.notice_lead_days_required:
                is_compliant = False
                compliance_issues.append(
                    f"Notice posted {actual_lead_days:.1f} days before meeting, "
                    f"but {meeting.notice_lead_days_required} days required"
                )
        else:
            if meeting.notice_status == "not_posted":
                is_compliant = False
                compliance_issues.append("Notice has not been posted")

        agenda_published = meeting.agenda_published_at is not None
        if not agenda_published:
            compliance_issues.append("Agenda has not been published")

        posting_locations = meeting.notice_posting_locations or []
        has_accessibility_info = bool(meeting.accessibility_info)

        if meeting.has_executive_session and not meeting.executive_session_reason:
            compliance_issues.append("Executive session marked but no legal reason provided")

        location_schemas = [
            NoticePostingLocation(
                location=loc.get("location", ""),
                url=loc.get("url"),
                posted_at=datetime.fromisoformat(loc["posted_at"]) if loc.get("posted_at") else None,
                notes=loc.get("notes"),
            )
            for loc in posting_locations
        ]

        compliance_reports.append(
            NoticeComplianceStatus(
                meeting_id=meeting.id,
                meeting_title=meeting.title,
                scheduled_date=meeting.scheduled_date,
                notice_status=meeting.notice_status,
                notice_posted_at=meeting.notice_posted_at,
                notice_lead_days_required=meeting.notice_lead_days_required,
                actual_lead_days=actual_lead_days,
                is_compliant=is_compliant and len(compliance_issues) == 0,
                compliance_issues=compliance_issues,
                posting_locations=location_schemas,
                agenda_published=agenda_published,
                has_accessibility_info=has_accessibility_info,
            )
        )

    return compliance_reports


@router.post("/board/meetings/{meeting_id}/notice/publish")
async def publish_meeting_notice(
    meeting_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark meeting notice as officially published (admin only)."""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(status_code=403, detail="Admin access required")

    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    if meeting.is_cancelled:
        raise HTTPException(
            status_code=400, detail="Cannot publish notice for a cancelled meeting"
        )

    if meeting.notice_status == "not_posted":
        raise HTTPException(
            status_code=400,
            detail="Notice must be posted to at least one location before publishing"
        )

    meeting.notice_status = "published"
    if not meeting.notice_posted_at:
        meeting.notice_posted_at = datetime.now(timezone.utc)
        meeting.notice_posted_by_id = current_user.id
    meeting.updated_at = datetime.now(timezone.utc)

    await db.commit()

    return {
        "message": "Notice published successfully",
        "notice_status": meeting.notice_status,
        "notice_posted_at": meeting.notice_posted_at.isoformat(),
    }


@router.delete("/board/meetings/{meeting_id}/notice/posting/{location}")
async def remove_posting_location(
    meeting_id: int,
    location: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove a posting location from a meeting notice (staff/admin)."""
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(status_code=403, detail="Staff access required")

    meeting = await get_or_404(db, BoardMeeting, meeting_id, "Meeting not found")

    if meeting.notice_status == "published":
        raise HTTPException(
            status_code=400,
            detail="Cannot modify posting locations after notice is published"
        )

    posting_locations = meeting.notice_posting_locations or []
    original_count = len(posting_locations)

    # Remove matching locations
    posting_locations = [loc for loc in posting_locations if loc.get("location") != location]

    if len(posting_locations) == original_count:
        raise HTTPException(status_code=404, detail=f"Posting location '{location}' not found")

    meeting.notice_posting_locations = posting_locations

    # If no locations left, reset status
    if len(posting_locations) == 0:
        meeting.notice_status = "not_posted"
        meeting.notice_posted_at = None
        meeting.notice_posted_by_id = None

    meeting.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "message": f"Posting location '{location}' removed",
        "notice_status": meeting.notice_status,
        "posting_locations": meeting.notice_posting_locations,
    }
