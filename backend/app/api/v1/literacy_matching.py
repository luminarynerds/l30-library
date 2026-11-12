# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Literacy Tutor Matching and Session Management API Routes.

Endpoints for:
- Tutor-learner matching
- Session scheduling
- Session logging
- Match management
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional, List
from datetime import date, time

from app.core.database import get_db
from app.models.literacy_matching import (
    LiteracyTutorMatch, LiteracySessionSchedule, LiteracySessionLog,
    LiteracySessionNotes, MatchStatus, LiteracySessionStatus, AttendanceStatus
)
from app.services.literacy_matching_service import TutorMatchingService
from app.services.literacy_progress_service import ProgressTrackingService
from app.schemas.literacy import (
    MatchRequest, MatchResponse, SessionScheduleRequest, SessionLogRequest,
    SessionNotesRequest
)
from .dependencies import require_staff
from fastapi import Depends
from ...models.user import User

router = APIRouter(prefix="/literacy", tags=["literacy_matching"])


@router.post("/matches", response_model=MatchResponse)
async def create_match(
    request: MatchRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """
    Create a new tutor-learner match.

    Attempts to pair a learner with a compatible tutor based on preferences
    and availability.
    """
    service = TutorMatchingService(db)

    match = await service.create_match(
        learner_id=request.learner_id,
        tutor_id=request.tutor_id,
        reason=request.reason,
        compatibility_score=request.compatibility_score
    )

    await db.commit()
    return MatchResponse.model_validate(match)


@router.get("/matches/{match_id}", response_model=MatchResponse)
async def get_match(
    match_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get match details."""
    match = await db.get(LiteracyTutorMatch, match_id)
    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    return MatchResponse.model_validate(match)


@router.post("/matches/{match_id}/activate")
async def activate_match(
    match_id: int,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Activate a proposed match."""
    service = TutorMatchingService(db)
    match = await service.activate_match(match_id)

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    await db.commit()
    return {
        "id": match.id,
        "status": str(match.status),
        "message": "Match activated successfully"
    }


@router.post("/matches/{match_id}/end")
async def end_match(
    match_id: int,
    reason: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """End an active match."""
    service = TutorMatchingService(db)
    match = await service.end_match(match_id, reason)

    if not match:
        raise HTTPException(status_code=404, detail="Match not found")

    await db.commit()
    return {
        "id": match.id,
        "status": str(match.status),
        "end_date": match.end_date.isoformat() if match.end_date else None
    }


@router.post("/sessions/schedule", response_model=dict)
async def schedule_session(
    request: SessionScheduleRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """
    Schedule a new tutoring session.

    Books a session between tutor and learner at specified date/time.
    Validates tutor availability.
    """
    service = TutorMatchingService(db)

    # Parse time
    time_parts = request.start_time.split(":")
    start_time = time(hour=int(time_parts[0]), minute=int(time_parts[1]))

    # Check availability
    is_available = await service.check_tutor_availability(
        tutor_id=(await db.get(LiteracyTutorMatch, request.match_id)).tutor_id,
        requested_date=request.scheduled_date,
        requested_time=start_time,
        duration_minutes=request.duration_minutes
    )

    if not is_available:
        raise HTTPException(status_code=409, detail="Tutor not available at requested time")

    session = await service.schedule_session(
        match_id=request.match_id,
        scheduled_date=request.scheduled_date,
        start_time=start_time,
        duration_minutes=request.duration_minutes,
        location=request.location,
        is_remote=request.is_remote,
        meeting_url=request.meeting_url
    )

    await db.commit()
    return {
        "id": session.id,
        "match_id": session.match_id,
        "scheduled_date": session.scheduled_date.isoformat(),
        "start_time": session.start_time.isoformat(),
        "status": str(session.status)
    }


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Get session details."""
    session = await db.get(LiteracySessionSchedule, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "match_id": session.match_id,
        "scheduled_date": session.scheduled_date.isoformat(),
        "start_time": session.start_time.isoformat(),
        "duration_minutes": session.duration_minutes,
        "status": str(session.status),
        "location": session.location,
        "is_remote": session.is_remote,
        "meeting_url": session.meeting_url,
        "learner_confirmed": session.learner_confirmed,
        "tutor_confirmed": session.tutor_confirmed
    }


@router.put("/sessions/{session_id}")
async def update_session(
    session_id: int,
    updates: dict,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Update session details (reschedule, confirm, etc.)."""
    session = await db.get(LiteracySessionSchedule, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    allowed_fields = {
        'location', 'is_remote', 'meeting_url', 'learner_confirmed',
        'tutor_confirmed', 'notes', 'status'
    }

    for field, value in updates.items():
        if field in allowed_fields and value is not None:
            setattr(session, field, value)

    await db.commit()
    return {"message": "Session updated successfully"}


@router.post("/sessions/{session_id}/log")
async def log_session(
    session_id: int,
    request: SessionLogRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """
    Log a completed tutoring session.

    Records attendance, engagement, and duration of actual session.
    """
    service = TutorMatchingService(db)
    progress_service = ProgressTrackingService(db)

    # Create session log
    session_log = await service.log_session(
        match_id=request.match_id,
        learner_id=request.learner_id,
        tutor_id=request.tutor_id,
        session_date=request.session_date,
        attendance_status=request.attendance_status,
        actual_duration_minutes=request.actual_duration_minutes,
        engagement_notes={
            "engagement": request.learner_engagement,
            "focus": request.learner_focus,
            "progress": request.progress_observed
        }
    )

    # Update progress
    await progress_service.record_session(session_log.id, request.session_date, request.learner_id)

    await db.commit()
    return {
        "id": session_log.id,
        "session_date": session_log.session_date.isoformat(),
        "attendance_status": request.attendance_status,
        "actual_duration_minutes": request.actual_duration_minutes,
        "message": "Session logged successfully"
    }


@router.post("/sessions/{session_id}/notes")
async def add_session_notes(
    session_id: int,
    request: SessionNotesRequest,
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """Add detailed notes to a session."""
    session_log = await db.get(LiteracySessionLog, session_id)
    if not session_log:
        raise HTTPException(status_code=404, detail="Session not found")

    # Check if notes already exist
    existing_notes = await db.scalar(
        select(LiteracySessionNotes).where(
            LiteracySessionNotes.session_id == session_id
        )
    )

    if existing_notes:
        # Update existing notes
        existing_notes.topics_covered = request.topics_covered
        existing_notes.activities_conducted = request.activities_conducted
        existing_notes.homework_assigned = request.homework_assigned
        existing_notes.learner_feedback = request.learner_feedback
        existing_notes.tutor_notes = request.tutor_notes
    else:
        # Create new notes
        notes = LiteracySessionNotes(
            session_id=session_id,
            topics_covered=request.topics_covered,
            activities_conducted=request.activities_conducted,
            homework_assigned=request.homework_assigned,
            learner_feedback=request.learner_feedback,
            tutor_notes=request.tutor_notes
        )
        db.add(notes)

    await db.commit()
    return {"message": "Session notes saved successfully"}


@router.get("/sessions")
async def list_sessions(
    match_id: Optional[int] = Query(None),
    learner_id: Optional[int] = Query(None),
    tutor_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    limit: int = Query(50, le=100),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db)
):
    """
    List sessions with optional filtering.

    Supports filtering by match, learner, tutor, date range, and status.
    """
    query = select(LiteracySessionSchedule)

    if match_id:
        query = query.where(LiteracySessionSchedule.match_id == match_id)
    if status:
        query = query.where(LiteracySessionSchedule.status == status)

    sessions = await db.scalars(
        query.order_by(LiteracySessionSchedule.scheduled_date.desc())
             .limit(limit)
             .offset(offset)
    )

    return [
        {
            "id": s.id,
            "match_id": s.match_id,
            "scheduled_date": s.scheduled_date.isoformat(),
            "start_time": s.start_time.isoformat(),
            "duration_minutes": s.duration_minutes,
            "status": str(s.status),
            "location": s.location,
            "is_remote": s.is_remote
        }
        for s in sessions
    ]


@router.post("/learner-matching")
async def find_tutors_for_learner(
    learner_id: int,
    criteria: dict = {},
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_staff),
):
    """
    Find compatible tutors for a learner.

    Returns list of tutors sorted by compatibility score.
    """
    service = TutorMatchingService(db)
    compatible_tutors = await service.find_compatible_tutors(learner_id, criteria)

    return [
        {
            "tutor_id": tutor.id,
            "user_id": tutor.user_id,
            "primary_focus": tutor.primary_focus,
            "compatibility_score": float(score),
            "total_learners_taught": tutor.total_learners_taught,
            "can_teach_ged": tutor.can_teach_ged,
            "can_teach_esol": tutor.can_teach_esol
        }
        for tutor, score in compatible_tutors[:10]  # Return top 10
    ]
