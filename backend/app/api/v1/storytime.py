# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for storytime program management.

Provides endpoints for:
- Storytime series management
- Session scheduling
- Attendance tracking
- Theme and book management
- Craft supply planning
- Caregiver communication
- Sub leader scheduling
- Annual planning
"""

from datetime import datetime, date, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from .dependencies import get_current_user, require_staff
from ...models import (
    User, StorytimeSeries, StorytimeSession, StorytimeAttendance, RepeatAttendee,
    StorytimeTheme, StorytimeBook, StorytimeSong, StorytimeRhyme, StorytimeCraft,
    CraftSupplyInventory, CaregiverContact, CaregiverCommunication,
    StorytimeSubLeader, SubLeaderAssignment, StorytimeAnnualPlan,
    StorytimeMonthlyPlan, WeatherAlert
)
from ...schemas import (
    StorytimeSeriesCreate, StorytimeSeriesUpdate, StorytimeSeriesResponse,
    StorytimeSessionCreate, StorytimeSessionUpdate, StorytimeSessionResponse,
    StorytimeAttendanceCreate, StorytimeAttendanceResponse,
    StorytimeThemeCreate, StorytimeThemeUpdate, StorytimeThemeResponse,
    StorytimeBookCreate, StorytimeBookUpdate, StorytimeBookResponse,
    StorytimeSongCreate, StorytimeSongResponse,
    StorytimeRhymeCreate, StorytimeRhymeResponse,
    StorytimeCraftCreate, StorytimeCraftResponse,
    CraftSupplyInventoryCreate, CraftSupplyInventoryResponse,
    CaregiverContactCreate, CaregiverContactUpdate, CaregiverContactResponse,
    CaregiverCommunicationCreate, CaregiverCommunicationResponse,
    StorytimeSubLeaderCreate, StorytimeSubLeaderUpdate, StorytimeSubLeaderResponse,
    SubLeaderAssignmentCreate, SubLeaderAssignmentResponse,
    StorytimeAnnualPlanCreate, StorytimeAnnualPlanResponse,
    StorytimeMonthlyPlanCreate, StorytimeMonthlyPlanResponse,
    WeatherAlertCreate, WeatherAlertResponse, WeatherCancellationApplyRequest,
    RepeatAttendeeResponse,
)

router = APIRouter(prefix="/storytime", tags=["storytime"])


def _build_caregiver_identifier(attendance: StorytimeAttendanceCreate) -> Optional[str]:
    if attendance.caregiver_email:
        return attendance.caregiver_email.strip().lower()
    if attendance.caregiver_name:
        normalized_name = " ".join(attendance.caregiver_name.split()).lower()
        child_key = (attendance.child_name or "unknown-child").strip().lower()
        return f"{normalized_name}::{child_key}"
    return None


def _recognition_from_total_sessions(total_sessions: int) -> tuple[str, List[str]]:
    if total_sessions >= 50:
        return "super_fan", ["regular_reader", "frequent_friend", "devoted_family", "super_fan"]
    if total_sessions >= 25:
        return "devoted", ["regular_reader", "frequent_friend", "devoted_family"]
    if total_sessions >= 10:
        return "frequent", ["regular_reader", "frequent_friend"]
    return "regular", ["regular_reader"]



# ============================================================================
# Storytime Series Endpoints
# ============================================================================

@router.post("/series", response_model=StorytimeSeriesResponse)
async def create_storytime_series(
    series: StorytimeSeriesCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new storytime series."""
    db_series = StorytimeSeries(**series.dict())
    db.add(db_series)
    await db.flush()
    await db.refresh(db_series)
    return db_series


@router.get("/series", response_model=List[StorytimeSeriesResponse])
async def list_storytime_series(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List storytime series with optional filtering."""
    stmt = select(StorytimeSeries)
    if is_active is not None:
        stmt = stmt.where(StorytimeSeries.is_active == is_active)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/series/{series_id}", response_model=StorytimeSeriesResponse)
async def get_storytime_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get a specific storytime series."""
    result = await db.execute(
        select(StorytimeSeries).where(StorytimeSeries.id == series_id)
    )
    series = result.scalars().first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")
    return series


@router.patch("/series/{series_id}", response_model=StorytimeSeriesResponse)
async def update_storytime_series(
    series_id: int,
    series_update: StorytimeSeriesUpdate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Update a storytime series."""
    result = await db.execute(
        select(StorytimeSeries).where(StorytimeSeries.id == series_id)
    )
    series = result.scalars().first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    update_data = series_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(series, field, value)

    await db.flush()
    await db.refresh(series)
    return series


@router.delete("/series/{series_id}")
async def delete_storytime_series(
    series_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Delete a storytime series."""
    result = await db.execute(
        select(StorytimeSeries).where(StorytimeSeries.id == series_id)
    )
    series = result.scalars().first()
    if not series:
        raise HTTPException(status_code=404, detail="Series not found")

    await db.delete(series)
    await db.flush()
    return {"deleted": True}


# ============================================================================
# Storytime Session Endpoints
# ============================================================================

@router.post("/sessions", response_model=StorytimeSessionResponse)
async def create_storytime_session(
    session: StorytimeSessionCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new storytime session."""
    db_session = StorytimeSession(**session.dict())
    db.add(db_session)
    await db.flush()
    await db.refresh(db_session)
    return db_session


@router.get("/sessions", response_model=List[StorytimeSessionResponse])
async def list_storytime_sessions(
    series_id: Optional[int] = None,
    session_date: Optional[date] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List storytime sessions with optional filtering."""
    stmt = select(StorytimeSession)
    if series_id:
        stmt = stmt.where(StorytimeSession.series_id == series_id)
    if session_date:
        stmt = stmt.where(StorytimeSession.session_date == session_date)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/sessions/{session_id}", response_model=StorytimeSessionResponse)
async def get_storytime_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get a specific storytime session."""
    result = await db.execute(
        select(StorytimeSession).where(StorytimeSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.patch("/sessions/{session_id}", response_model=StorytimeSessionResponse)
async def update_storytime_session(
    session_id: int,
    session_update: StorytimeSessionUpdate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Update a storytime session."""
    result = await db.execute(
        select(StorytimeSession).where(StorytimeSession.id == session_id)
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    update_data = session_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(session, field, value)

    await db.flush()
    await db.refresh(session)
    return session


# ============================================================================
# Attendance Endpoints
# ============================================================================

@router.post("/attendance", response_model=StorytimeAttendanceResponse)
async def record_attendance(
    attendance: StorytimeAttendanceCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Record attendance for a storytime session (walk-in)."""
    db_attendance = StorytimeAttendance(**attendance.dict())
    db.add(db_attendance)

    # Update session actual attendance
    result = await db.execute(
        select(StorytimeSession).where(
            StorytimeSession.id == attendance.session_id
        )
    )
    session = result.scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    session.actual_attendance = (session.actual_attendance or 0) + 1

    # Track repeat attendees for recognition workflows
    caregiver_identifier = _build_caregiver_identifier(attendance)
    if caregiver_identifier:
        repeat_result = await db.execute(
            select(RepeatAttendee).where(RepeatAttendee.caregiver_identifier == caregiver_identifier)
        )
        repeat_attendee = repeat_result.scalars().first()

        if repeat_attendee:
            repeat_attendee.total_sessions_attended += 1
            repeat_attendee.last_attended_date = session.session_date
        else:
            repeat_attendee = RepeatAttendee(
                session_id=session.id,
                caregiver_identifier=caregiver_identifier,
                caregiver_name=attendance.caregiver_name,
                caregiver_email=attendance.caregiver_email,
                first_attended_date=session.session_date,
                last_attended_date=session.session_date,
                total_sessions_attended=1,
                prefers_contact=bool(attendance.caregiver_email or attendance.caregiver_phone),
            )
            db.add(repeat_attendee)

        recognition_status, recognition_badges = _recognition_from_total_sessions(
            repeat_attendee.total_sessions_attended
        )
        repeat_attendee.recognition_status = recognition_status
        repeat_attendee.recognition_badges = recognition_badges

    await db.flush()
    await db.refresh(db_attendance)
    return db_attendance


@router.get("/attendance/{session_id}", response_model=List[StorytimeAttendanceResponse])
async def get_session_attendance(
    session_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get attendance records for a session."""
    result = await db.execute(
        select(StorytimeAttendance)
        .where(StorytimeAttendance.session_id == session_id)
        .offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/repeat-attendees", response_model=List[RepeatAttendeeResponse])
async def list_repeat_attendees(
    recognition_status: Optional[str] = None,
    minimum_sessions: int = Query(1, ge=1),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List repeat attendees for recognition and caregiver follow-up workflows."""
    stmt = select(RepeatAttendee).where(RepeatAttendee.total_sessions_attended >= minimum_sessions)
    if recognition_status:
        stmt = stmt.where(RepeatAttendee.recognition_status == recognition_status)
    stmt = stmt.order_by(RepeatAttendee.total_sessions_attended.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================================
# Theme Management Endpoints
# ============================================================================

@router.post("/themes", response_model=StorytimeThemeResponse)
async def create_theme(
    theme: StorytimeThemeCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new storytime theme."""
    db_theme = StorytimeTheme(**theme.dict())
    db.add(db_theme)
    await db.flush()
    await db.refresh(db_theme)
    return db_theme


@router.get("/themes", response_model=List[StorytimeThemeResponse])
async def list_themes(
    series_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List storytime themes."""
    stmt = select(StorytimeTheme)
    if series_id:
        stmt = stmt.where(StorytimeTheme.series_id == series_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/themes/{theme_id}", response_model=StorytimeThemeResponse)
async def get_theme(
    theme_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get a specific storytime theme."""
    result = await db.execute(
        select(StorytimeTheme).where(StorytimeTheme.id == theme_id)
    )
    theme = result.scalars().first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")
    return theme


@router.patch("/themes/{theme_id}", response_model=StorytimeThemeResponse)
async def update_theme(
    theme_id: int,
    theme_update: StorytimeThemeUpdate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Update a storytime theme."""
    result = await db.execute(
        select(StorytimeTheme).where(StorytimeTheme.id == theme_id)
    )
    theme = result.scalars().first()
    if not theme:
        raise HTTPException(status_code=404, detail="Theme not found")

    update_data = theme_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(theme, field, value)

    await db.flush()
    await db.refresh(theme)
    return theme


# ============================================================================
# Book Management Endpoints
# ============================================================================

@router.post("/books", response_model=StorytimeBookResponse)
async def create_book(
    book: StorytimeBookCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new storytime book."""
    db_book = StorytimeBook(**book.dict())
    db.add(db_book)
    await db.flush()
    await db.refresh(db_book)
    return db_book


@router.get("/books", response_model=List[StorytimeBookResponse])
async def list_books(
    age_group: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List storytime books."""
    stmt = select(StorytimeBook).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/books/{book_id}", response_model=StorytimeBookResponse)
async def get_book(
    book_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get a specific storytime book."""
    result = await db.execute(
        select(StorytimeBook).where(StorytimeBook.id == book_id)
    )
    book = result.scalars().first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")
    return book


# ============================================================================
# Song and Rhyme Library Endpoints
# ============================================================================

@router.post("/songs", response_model=StorytimeSongResponse)
async def create_song(
    song: StorytimeSongCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new storytime song."""
    db_song = StorytimeSong(**song.dict())
    db.add(db_song)
    await db.flush()
    await db.refresh(db_song)
    return db_song


@router.get("/songs", response_model=List[StorytimeSongResponse])
async def list_songs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List storytime songs."""
    result = await db.execute(
        select(StorytimeSong).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/rhymes", response_model=StorytimeRhymeResponse)
async def create_rhyme(
    rhyme: StorytimeRhymeCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new storytime rhyme."""
    db_rhyme = StorytimeRhyme(**rhyme.dict())
    db.add(db_rhyme)
    await db.flush()
    await db.refresh(db_rhyme)
    return db_rhyme


@router.get("/rhymes", response_model=List[StorytimeRhymeResponse])
async def list_rhymes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List storytime rhymes."""
    result = await db.execute(
        select(StorytimeRhyme).offset(skip).limit(limit)
    )
    return result.scalars().all()


# ============================================================================
# Craft Management Endpoints
# ============================================================================

@router.post("/crafts", response_model=StorytimeCraftResponse)
async def create_craft(
    craft: StorytimeCraftCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new storytime craft."""
    db_craft = StorytimeCraft(**craft.dict())
    db.add(db_craft)
    await db.flush()
    await db.refresh(db_craft)
    return db_craft


@router.get("/crafts", response_model=List[StorytimeCraftResponse])
async def list_crafts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List storytime crafts."""
    result = await db.execute(
        select(StorytimeCraft).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.post("/craft-supplies", response_model=CraftSupplyInventoryResponse)
async def create_craft_supply(
    supply: CraftSupplyInventoryCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new craft supply inventory item."""
    db_supply = CraftSupplyInventory(**supply.dict())
    db.add(db_supply)
    await db.flush()
    await db.refresh(db_supply)
    return db_supply


@router.get("/craft-supplies", response_model=List[CraftSupplyInventoryResponse])
async def list_craft_supplies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List craft supply inventory."""
    result = await db.execute(
        select(CraftSupplyInventory).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.get("/craft-supplies/low-stock")
async def get_low_stock_supplies(
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get craft supplies that are low in stock."""
    result = await db.execute(
        select(CraftSupplyInventory).where(
            CraftSupplyInventory.quantity_on_hand <= CraftSupplyInventory.reorder_level
        )
    )
    return result.scalars().all()


# ============================================================================
# Caregiver Communication Endpoints
# ============================================================================

@router.post("/caregiver-contacts", response_model=CaregiverContactResponse)
async def create_caregiver_contact(
    contact: CaregiverContactCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new caregiver contact."""
    db_contact = CaregiverContact(**contact.dict())
    db.add(db_contact)
    await db.flush()
    await db.refresh(db_contact)
    return db_contact


@router.get("/caregiver-contacts", response_model=List[CaregiverContactResponse])
async def list_caregiver_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List caregiver contacts."""
    result = await db.execute(
        select(CaregiverContact).offset(skip).limit(limit)
    )
    return result.scalars().all()


@router.patch("/caregiver-contacts/{contact_id}", response_model=CaregiverContactResponse)
async def update_caregiver_contact(
    contact_id: int,
    contact_update: CaregiverContactUpdate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Update a caregiver contact."""
    result = await db.execute(
        select(CaregiverContact).where(CaregiverContact.id == contact_id)
    )
    contact = result.scalars().first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = contact_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(contact, field, value)

    await db.flush()
    await db.refresh(contact)
    return contact


@router.post("/caregiver-communications", response_model=CaregiverCommunicationResponse)
async def create_communication(
    communication: CaregiverCommunicationCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new caregiver communication."""
    db_comm = CaregiverCommunication(**communication.dict())
    db.add(db_comm)
    await db.flush()
    await db.refresh(db_comm)
    return db_comm


@router.get("/caregiver-communications", response_model=List[CaregiverCommunicationResponse])
async def list_communications(
    caregiver_contact_id: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List caregiver communications."""
    stmt = select(CaregiverCommunication)
    if caregiver_contact_id:
        stmt = stmt.where(CaregiverCommunication.caregiver_contact_id == caregiver_contact_id)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================================
# Sub Leader Endpoints
# ============================================================================

@router.post("/sub-leaders", response_model=StorytimeSubLeaderResponse)
async def create_sub_leader(
    leader: StorytimeSubLeaderCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a new sub storytime leader."""
    db_leader = StorytimeSubLeader(**leader.dict())
    db.add(db_leader)
    await db.flush()
    await db.refresh(db_leader)
    return db_leader


@router.get("/sub-leaders", response_model=List[StorytimeSubLeaderResponse])
async def list_sub_leaders(
    status: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List sub storytime leaders."""
    stmt = select(StorytimeSubLeader)
    if status:
        stmt = stmt.where(StorytimeSubLeader.status == status)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/sub-leaders/{leader_id}", response_model=StorytimeSubLeaderResponse)
async def update_sub_leader(
    leader_id: int,
    leader_update: StorytimeSubLeaderUpdate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Update a sub storytime leader."""
    result = await db.execute(
        select(StorytimeSubLeader).where(StorytimeSubLeader.id == leader_id)
    )
    leader = result.scalars().first()
    if not leader:
        raise HTTPException(status_code=404, detail="Sub leader not found")

    update_data = leader_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(leader, field, value)

    await db.flush()
    await db.refresh(leader)
    return leader


@router.post("/sub-leader-assignments", response_model=SubLeaderAssignmentResponse)
async def create_assignment(
    assignment: SubLeaderAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a sub leader assignment."""
    db_assignment = SubLeaderAssignment(**assignment.dict())
    db.add(db_assignment)
    await db.flush()
    await db.refresh(db_assignment)
    return db_assignment


@router.get("/sub-leader-assignments/{session_id}", response_model=List[SubLeaderAssignmentResponse])
async def get_session_assignments(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get sub leader assignments for a session."""
    result = await db.execute(
        select(SubLeaderAssignment).where(
            SubLeaderAssignment.session_id == session_id
        )
    )
    return result.scalars().all()


# ============================================================================
# Planning Endpoints
# ============================================================================

@router.post("/annual-plans", response_model=StorytimeAnnualPlanResponse)
async def create_annual_plan(
    plan: StorytimeAnnualPlanCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create an annual storytime plan."""
    db_plan = StorytimeAnnualPlan(**plan.dict())
    db.add(db_plan)
    await db.flush()
    await db.refresh(db_plan)
    return db_plan


@router.get("/annual-plans/{year}", response_model=StorytimeAnnualPlanResponse)
async def get_annual_plan(
    year: int,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get annual plan for a specific year."""
    result = await db.execute(
        select(StorytimeAnnualPlan).where(StorytimeAnnualPlan.year == year)
    )
    plan = result.scalars().first()
    if not plan:
        raise HTTPException(status_code=404, detail="Annual plan not found")
    return plan


@router.post("/monthly-plans", response_model=StorytimeMonthlyPlanResponse)
async def create_monthly_plan(
    plan: StorytimeMonthlyPlanCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a monthly storytime plan."""
    db_plan = StorytimeMonthlyPlan(**plan.dict())
    db.add(db_plan)
    await db.flush()
    await db.refresh(db_plan)
    return db_plan


@router.get("/monthly-plans")
async def list_monthly_plans(
    year: Optional[int] = None,
    month: Optional[int] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List monthly plans."""
    stmt = select(StorytimeMonthlyPlan)
    if year:
        stmt = stmt.where(StorytimeMonthlyPlan.year == year)
    if month:
        stmt = stmt.where(StorytimeMonthlyPlan.month == month)
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


# ============================================================================
# Weather Alert Endpoints
# ============================================================================

@router.post("/weather-alerts", response_model=WeatherAlertResponse)
async def create_weather_alert(
    alert: WeatherAlertCreate,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Create a weather alert."""
    db_alert = WeatherAlert(**alert.dict())
    db.add(db_alert)
    await db.flush()
    await db.refresh(db_alert)
    return db_alert


@router.get("/weather-alerts", response_model=List[WeatherAlertResponse])
async def list_weather_alerts(
    active_only: bool = True,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """List weather alerts."""
    stmt = select(WeatherAlert)
    if active_only:
        now = datetime.now(timezone.utc)
        stmt = stmt.where(WeatherAlert.effective_from <= now)
        stmt = stmt.where(
            (WeatherAlert.effective_until.is_(None)) |
            (WeatherAlert.effective_until >= now)
        )
    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/weather-alerts/{alert_id}/apply-cancellations")
async def apply_weather_cancellations(
    alert_id: int,
    request: WeatherCancellationApplyRequest,
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Cancel matching scheduled sessions based on an existing weather alert."""
    alert = await get_or_404(db, WeatherAlert, alert_id, "Weather alert not found")

    sessions_stmt = (
        select(StorytimeSession)
        .join(StorytimeSeries, StorytimeSession.series_id == StorytimeSeries.id)
        .where(func.date(StorytimeSession.start_time) >= func.date(alert.effective_from))
    )

    if alert.effective_until:
        sessions_stmt = sessions_stmt.where(
            func.date(StorytimeSession.start_time) <= func.date(alert.effective_until)
        )

    if alert.affected_locations:
        safe_locs = [loc.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") for loc in alert.affected_locations]
        sessions_stmt = sessions_stmt.where(
            or_(*[StorytimeSeries.location.ilike(f"%{loc}%") for loc in safe_locs])
        )

    if request.include_only_scheduled:
        sessions_stmt = sessions_stmt.where(StorytimeSession.status == "scheduled")

    sessions = (await db.execute(sessions_stmt)).scalars().all()

    for session in sessions:
        session.is_cancelled = True
        session.status = "cancelled_weather"
        session.weather_alert = alert.alert_type
        session.cancellation_reason = request.cancellation_reason
        session.cancellation_notification_sent_at = datetime.now(timezone.utc)

    alert.sessions_cancelled = len(sessions)

    await db.flush()

    return {
        "alert_id": alert.id,
        "sessions_cancelled": len(sessions),
        "affected_locations": alert.affected_locations,
    }


# ============================================================================
# Dashboard Endpoints
# ============================================================================

@router.get("/dashboard/summary")
async def get_storytime_dashboard(
    db: AsyncSession = Depends(get_db),
    staff_user: User = Depends(require_staff),
):
    """Get storytime program dashboard summary."""
    total_series = (await db.execute(
        select(func.count()).select_from(StorytimeSeries)
    )).scalar() or 0

    active_series = (await db.execute(
        select(func.count()).select_from(StorytimeSeries).where(StorytimeSeries.is_active == True)
    )).scalar() or 0

    today = date.today()
    sessions_this_week = (await db.execute(
        select(func.count()).select_from(StorytimeSession).where(
            StorytimeSession.session_date >= today
        )
    )).scalar() or 0

    total_attendees = (await db.execute(
        select(func.count()).select_from(StorytimeAttendance)
    )).scalar() or 0

    repeat_attendees = (await db.execute(
        select(func.count()).select_from(RepeatAttendee)
    )).scalar() or 0

    books_in_library = (await db.execute(
        select(func.count()).select_from(StorytimeBook).where(
            StorytimeBook.is_in_collection == True
        )
    )).scalar() or 0

    crafts_available = (await db.execute(
        select(func.count()).select_from(StorytimeCraft)
    )).scalar() or 0

    low_stock_supplies = (await db.execute(
        select(func.count()).select_from(CraftSupplyInventory).where(
            CraftSupplyInventory.quantity_on_hand <= CraftSupplyInventory.reorder_level
        )
    )).scalar() or 0

    return {
        "total_series": total_series,
        "active_series": active_series,
        "sessions_this_week": sessions_this_week,
        "total_attendees": total_attendees,
        "repeat_attendees": repeat_attendees,
        "books_in_library": books_in_library,
        "crafts_available": crafts_available,
        "low_stock_supplies": low_stock_supplies,
    }
