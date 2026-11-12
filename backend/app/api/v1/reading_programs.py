# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Reading Programs API for L30 Library.
Manage reading challenges, summer reading, and reading log entries.
"""

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import Date, and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.rate_limit import limiter
from ...models.reading import (
    ReadingAchievement,
    ReadingLogEntry,
    ReadingPrize,
    ReadingProgram,
    ReadingProgramType,
    ReadingRegistration,
)
from ...models.user import User, UserRole
from ...schemas.reading import (
    LogEntryWithAchievementsResponse,
    ProgramProgressResponse,
    ReadingAchievementResponse,
    ReadingLogEntryCreate,
    ReadingLogEntryResponse,
    ReadingProgramCreate,
    ReadingProgramResponse,
    ReadingRegistrationCreate,
    ReadingRegistrationResponse,
)
from .auth import get_current_user
from .dependencies import check_staff_access, is_staff_or_admin
from pydantic import BaseModel, Field
from ...services.organization_features_service import OrganizationFeaturesService
from .reading_program_booklists import booklist_router
from .reading_program_paper_logs import paper_log_router


async def require_reading_programs_enabled(db: AsyncSession = Depends(get_db)) -> None:
    enabled = await OrganizationFeaturesService.is_feature_enabled(db, "reading_programs_enabled")
    if not enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading programs feature is not enabled",
        )


router = APIRouter(
    prefix="/reading-programs",
    tags=["reading-programs"],
    dependencies=[Depends(require_reading_programs_enabled)],
)


class PaginatedProgramsResponse(BaseModel):
    items: List[ReadingProgramResponse]
    total: int
    limit: int
    offset: int


class SummerLaunchRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = None
    start_date: date
    end_date: date
    theme: str = Field(..., min_length=2, max_length=120)


class SummerLaunchTask(BaseModel):
    key: str
    title: str
    due_date: date
    notes: str
    status: str = "scheduled"


class SummerLaunchResponse(BaseModel):
    source_program_id: int
    new_program_id: int
    cloned_prizes: int
    theme: str
    tasks: List[SummerLaunchTask]


async def _validate_log_entry_context(
    entry: "ReadingLogEntryCreate",
    db: AsyncSession,
    current_user: User,
) -> tuple["ReadingRegistration", "ReadingProgram"]:
    reg_result = await db.execute(
        select(ReadingRegistration).where(ReadingRegistration.id == entry.registration_id)
    )
    registration = reg_result.scalar_one_or_none()

    if not registration:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Registration not found")

    is_staff = is_staff_or_admin(current_user)
    if not is_staff and registration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Can only log for your own registrations"
        )

    program = await get_or_404(db, ReadingProgram, registration.program_id, "Program not found")

    if not program.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This program is no longer active"
        )

    today = date.today()
    if today < program.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This program hasn't started yet. Logging opens on {program.start_date.isoformat()}",
        )
    if today > program.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This program has ended and is no longer accepting reading logs",
        )

    return registration, program


# ============================================================================
# Reading Programs CRUD
# ============================================================================


@router.get("", response_model=PaginatedProgramsResponse)
@limiter.limit("60/minute")
async def list_reading_programs_root(
    request: Request,
    active_only: bool = Query(False, description="Show only active programs"),
    program_type: Optional[ReadingProgramType] = Query(None, description="Filter by program type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of programs to return"),
    offset: int = Query(0, ge=0, description="Number of programs to skip"),
    db: AsyncSession = Depends(get_db),
):
    """List all reading programs with pagination. Root endpoint."""
    # Build filter conditions
    conditions = []
    if active_only:
        conditions.append(ReadingProgram.is_active == True)
    if program_type:
        conditions.append(ReadingProgram.program_type == program_type)

    # Get total count
    count_query = select(func.count(ReadingProgram.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated programs
    query = select(ReadingProgram)
    if conditions:
        query = query.where(*conditions)
    query = query.order_by(ReadingProgram.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    programs = result.scalars().all()

    if not programs:
        return PaginatedProgramsResponse(items=[], total=total, limit=limit, offset=offset)

    # Get program IDs for batch stats queries
    program_ids = [p.id for p in programs]

    # Batch query for registration counts (eliminates N+1)
    reg_counts_result = await db.execute(
        select(
            ReadingRegistration.program_id,
            func.count(ReadingRegistration.id).label("count"),
        )
        .where(ReadingRegistration.program_id.in_(program_ids))
        .group_by(ReadingRegistration.program_id)
    )
    reg_counts = {row[0]: row[1] for row in reg_counts_result.all()}

    # Batch query for reading stats (eliminates N+1)
    stats_result = await db.execute(
        select(
            ReadingRegistration.program_id,
            func.sum(ReadingLogEntry.minutes_read).label("total_minutes"),
            func.sum(ReadingLogEntry.books_read).label("total_books"),
        )
        .select_from(ReadingLogEntry)
        .join(ReadingRegistration)
        .where(ReadingRegistration.program_id.in_(program_ids))
        .group_by(ReadingRegistration.program_id)
    )
    reading_stats = {row[0]: (row[1], row[2]) for row in stats_result.all()}

    # Build responses using batched data
    responses = []
    for program in programs:
        response = ReadingProgramResponse.model_validate(program)
        response.registration_count = reg_counts.get(program.id, 0)
        stats = reading_stats.get(program.id, (0, 0))
        response.total_minutes_read = int(stats[0]) if stats[0] else 0
        response.total_books_read = int(stats[1]) if stats[1] else 0
        responses.append(response)

    return PaginatedProgramsResponse(
        items=responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/programs", response_model=ReadingProgramResponse, status_code=status.HTTP_201_CREATED
)
async def create_reading_program(
    program: ReadingProgramCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new reading program (staff only)."""
    check_staff_access(current_user)

    # Validate dates
    if program.end_date <= program.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be after start date"
        )

    db_program = ReadingProgram(**program.model_dump(), created_by_id=current_user.id)

    db.add(db_program)
    await db.commit()
    await db.refresh(db_program)

    # Calculate stats
    registration_count_result = await db.execute(
        select(func.count(ReadingRegistration.id)).where(
            ReadingRegistration.program_id == db_program.id
        )
    )
    registration_count = registration_count_result.scalar() or 0

    response = ReadingProgramResponse.model_validate(db_program)
    response.registration_count = registration_count
    response.total_minutes_read = 0
    response.total_books_read = 0

    return response


@router.post("/programs/{program_id}/launch-summer", response_model=SummerLaunchResponse)
async def launch_summer_reading_automation(
    program_id: int,
    payload: SummerLaunchRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Clone a prior program and generate an automated summer launch plan."""
    check_staff_access(current_user)

    if payload.end_date <= payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be after start date"
        )

    source_program = await get_or_404(db, ReadingProgram, program_id, "Source program not found")

    cloned_program = ReadingProgram(
        name=payload.name,
        description=payload.description or source_program.description,
        program_type=ReadingProgramType.summer,
        age_group=source_program.age_group,
        target_age_min=source_program.target_age_min,
        target_age_max=source_program.target_age_max,
        start_date=payload.start_date,
        end_date=payload.end_date,
        reading_goal_type=source_program.reading_goal_type,
        reading_goal_value=source_program.reading_goal_value,
        is_active=True,
        is_school_program=source_program.is_school_program,
        partner_id=source_program.partner_id,
        curriculum_alignment=source_program.curriculum_alignment,
        grade_levels=source_program.grade_levels,
        reading_levels=source_program.reading_levels,
        created_by_id=current_user.id,
    )
    db.add(cloned_program)
    await db.flush()

    source_prizes_result = await db.execute(
        select(ReadingPrize).where(ReadingPrize.program_id == source_program.id)
    )
    source_prizes = source_prizes_result.scalars().all()

    cloned_prizes = 0
    for prize in source_prizes:
        db.add(
            ReadingPrize(
                program_id=cloned_program.id,
                name=prize.name,
                description=prize.description,
                prize_type=prize.prize_type,
                prize_value=prize.prize_value,
                image_url=prize.image_url,
                threshold_type=prize.threshold_type,
                threshold_value=prize.threshold_value,
                quantity_available=prize.quantity_available,
                quantity_redeemed=0,
                is_active=True,
                available_from=payload.start_date,
                available_until=payload.end_date,
                sort_order=prize.sort_order,
                notes=prize.notes,
                created_by_id=current_user.id,
            )
        )
        cloned_prizes += 1

    await db.commit()

    kickoff_date = payload.start_date + timedelta(days=2)
    celebration_date = payload.end_date + timedelta(days=3)
    registration_live_date = payload.start_date - timedelta(days=21)

    tasks = [
        SummerLaunchTask(
            key="clone_structure",
            title="Clone last year's program structure",
            due_date=payload.start_date - timedelta(days=30),
            notes="Program and settings cloned from prior year baseline.",
        ),
        SummerLaunchTask(
            key="update_dates_theme",
            title="Update dates and themes",
            due_date=payload.start_date - timedelta(days=29),
            notes=f"Theme set to '{payload.theme}' and schedule refreshed.",
        ),
        SummerLaunchTask(
            key="prize_inventory",
            title="Prize inventory setup",
            due_date=payload.start_date - timedelta(days=24),
            notes=f"{cloned_prizes} prior prize templates cloned and reset for new inventory counts.",
        ),
        SummerLaunchTask(
            key="reading_log_config",
            title="Reading log configuration",
            due_date=payload.start_date - timedelta(days=21),
            notes="Goal type and thresholds copied; logging windows aligned to program dates.",
        ),
        SummerLaunchTask(
            key="marketing_materials",
            title="Marketing material generation",
            due_date=payload.start_date - timedelta(days=18),
            notes=f"Auto-brief generated for '{payload.theme}' social, flyer, and newsletter assets.",
        ),
        SummerLaunchTask(
            key="registration_activation",
            title="Registration page activation",
            due_date=registration_live_date,
            notes=f"Registration opens {registration_live_date.isoformat()} for patrons.",
        ),
        SummerLaunchTask(
            key="staff_training",
            title="Staff training checklist",
            due_date=payload.start_date - timedelta(days=14),
            notes="Checklist includes scripts, FAQs, and escalation pathways.",
        ),
        SummerLaunchTask(
            key="kickoff_scheduling",
            title="Kickoff event scheduling",
            due_date=kickoff_date,
            notes=f"Kickoff event queued for {kickoff_date.isoformat()}.",
        ),
        SummerLaunchTask(
            key="partner_reminders",
            title="Partner coordination reminders",
            due_date=payload.start_date - timedelta(days=10),
            notes="Reminder cadence created for schools and community partners.",
        ),
        SummerLaunchTask(
            key="dashboard_tracking",
            title="Progress tracking dashboards",
            due_date=payload.start_date - timedelta(days=7),
            notes="Dashboard tiles prepared for registration, logs, and prize redemptions.",
        ),
        SummerLaunchTask(
            key="celebration_planning",
            title="Celebration event planning",
            due_date=celebration_date,
            notes=f"Celebration planning milestone set for {celebration_date.isoformat()}.",
        ),
    ]

    return SummerLaunchResponse(
        source_program_id=source_program.id,
        new_program_id=cloned_program.id,
        cloned_prizes=cloned_prizes,
        theme=payload.theme,
        tasks=tasks,
    )


@router.get("/programs", response_model=PaginatedProgramsResponse)
@limiter.limit("60/minute")
async def list_reading_programs(
    request: Request,
    active_only: bool = Query(False, description="Show only active programs"),
    program_type: Optional[ReadingProgramType] = Query(None, description="Filter by program type"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of programs to return"),
    offset: int = Query(0, ge=0, description="Number of programs to skip"),
    db: AsyncSession = Depends(get_db),
):
    """List all reading programs with pagination (public endpoint)."""

    # Build filter conditions
    conditions = []
    if active_only:
        conditions.append(ReadingProgram.is_active == True)
    if program_type:
        conditions.append(ReadingProgram.program_type == program_type)

    # Get total count
    count_query = select(func.count(ReadingProgram.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated programs
    query = select(ReadingProgram)
    if conditions:
        query = query.where(*conditions)
    query = query.order_by(ReadingProgram.start_date.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    programs = result.scalars().all()

    if not programs:
        return PaginatedProgramsResponse(items=[], total=total, limit=limit, offset=offset)

    # Get program IDs for batch stats queries
    program_ids = [p.id for p in programs]

    # Batch query for registration counts (eliminates N+1)
    reg_counts_result = await db.execute(
        select(
            ReadingRegistration.program_id,
            func.count(ReadingRegistration.id).label("count"),
        )
        .where(ReadingRegistration.program_id.in_(program_ids))
        .group_by(ReadingRegistration.program_id)
    )
    reg_counts = {row[0]: row[1] for row in reg_counts_result.all()}

    # Batch query for reading stats (eliminates N+1)
    stats_result = await db.execute(
        select(
            ReadingRegistration.program_id,
            func.sum(ReadingLogEntry.minutes_read).label("total_minutes"),
            func.sum(ReadingLogEntry.books_read).label("total_books"),
        )
        .select_from(ReadingLogEntry)
        .join(ReadingRegistration)
        .where(ReadingRegistration.program_id.in_(program_ids))
        .group_by(ReadingRegistration.program_id)
    )
    reading_stats = {row[0]: (row[1], row[2]) for row in stats_result.all()}

    # Build responses using batched data
    responses = []
    for program in programs:
        response = ReadingProgramResponse.model_validate(program)
        response.registration_count = reg_counts.get(program.id, 0)
        stats = reading_stats.get(program.id, (0, 0))
        response.total_minutes_read = int(stats[0]) if stats[0] else 0
        response.total_books_read = int(stats[1]) if stats[1] else 0
        responses.append(response)

    return PaginatedProgramsResponse(
        items=responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/programs/{program_id}", response_model=ReadingProgramResponse)
@limiter.limit("120/minute")
async def get_reading_program(
    request: Request,
    program_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific reading program (public endpoint)."""

    program = await get_or_404(db, ReadingProgram, program_id, "Program not found")

    # Get stats
    reg_result = await db.execute(
        select(func.count(ReadingRegistration.id)).where(
            ReadingRegistration.program_id == program.id
        )
    )
    registration_count = reg_result.scalar() or 0

    stats_result = await db.execute(
        select(func.sum(ReadingLogEntry.minutes_read), func.sum(ReadingLogEntry.books_read))
        .select_from(ReadingLogEntry)
        .join(ReadingRegistration)
        .where(ReadingRegistration.program_id == program.id)
    )
    stats = stats_result.first()
    total_minutes = int(stats[0]) if stats and stats[0] else 0
    total_books = int(stats[1]) if stats and stats[1] else 0

    response = ReadingProgramResponse.model_validate(program)
    response.registration_count = registration_count
    response.total_minutes_read = total_minutes
    response.total_books_read = total_books

    return response


@router.put("/programs/{program_id}", response_model=ReadingProgramResponse)
async def update_reading_program(
    program_id: int,
    program_update: ReadingProgramCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a reading program (staff only)."""
    check_staff_access(current_user)

    program = await get_or_404(db, ReadingProgram, program_id, "Program not found")

    # Validate dates
    if program_update.end_date <= program_update.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be after start date"
        )

    # Update fields
    for field, value in program_update.model_dump().items():
        setattr(program, field, value)

    await db.commit()
    await db.refresh(program)

    # Get stats
    reg_result = await db.execute(
        select(func.count(ReadingRegistration.id)).where(
            ReadingRegistration.program_id == program.id
        )
    )
    registration_count = reg_result.scalar() or 0

    stats_result = await db.execute(
        select(func.sum(ReadingLogEntry.minutes_read), func.sum(ReadingLogEntry.books_read))
        .select_from(ReadingLogEntry)
        .join(ReadingRegistration)
        .where(ReadingRegistration.program_id == program.id)
    )
    stats = stats_result.first()
    total_minutes = int(stats[0]) if stats and stats[0] else 0
    total_books = int(stats[1]) if stats and stats[1] else 0

    response = ReadingProgramResponse.model_validate(program)
    response.registration_count = registration_count
    response.total_minutes_read = total_minutes
    response.total_books_read = total_books

    return response


@router.delete("/programs/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_reading_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a reading program (staff only)."""
    check_staff_access(current_user)

    program = await get_or_404(db, ReadingProgram, program_id, "Program not found")

    # Check if program has registrations
    reg_count_result = await db.execute(
        select(func.count(ReadingRegistration.id)).where(
            ReadingRegistration.program_id == program_id
        )
    )
    reg_count = reg_count_result.scalar() or 0

    if reg_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete program with {reg_count} active registration(s). Mark as inactive instead.",
        )

    await db.delete(program)
    await db.commit()

    return None


# ============================================================================
# Registrations
# ============================================================================


class PaginatedRegistrationsResponse(BaseModel):
    items: List[ReadingRegistrationResponse]
    total: int
    limit: int
    offset: int


@router.get("/registrations", response_model=PaginatedRegistrationsResponse)
@limiter.limit("60/minute")
async def list_registrations(
    request: Request,
    program_id: Optional[int] = Query(None, description="Filter by program ID"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of registrations to return"),
    offset: int = Query(0, ge=0, description="Number of registrations to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all registrations (staff only).
    Patrons can only see their own registrations via /registrations/my.
    """
    check_staff_access(current_user)

    # Build filter conditions
    conditions = []
    if program_id:
        conditions.append(ReadingRegistration.program_id == program_id)

    # Get total count
    count_query = select(func.count(ReadingRegistration.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated registrations
    query = select(ReadingRegistration).options(selectinload(ReadingRegistration.program))
    if conditions:
        query = query.where(*conditions)
    query = query.order_by(ReadingRegistration.registered_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    registrations = result.scalars().all()

    if not registrations:
        return PaginatedRegistrationsResponse(items=[], total=total, limit=limit, offset=offset)

    # Get all registration IDs for batch stats query
    reg_ids = [reg.id for reg in registrations]

    # Batch query for reading stats
    stats_result = await db.execute(
        select(
            ReadingLogEntry.registration_id,
            func.sum(ReadingLogEntry.minutes_read),
            func.sum(ReadingLogEntry.books_read),
            func.sum(ReadingLogEntry.pages_read),
        )
        .where(ReadingLogEntry.registration_id.in_(reg_ids))
        .group_by(ReadingLogEntry.registration_id)
    )
    stats_by_reg = {}
    for row in stats_result.all():
        reg_id, minutes, books, pages = row
        stats_by_reg[reg_id] = {
            "minutes": int(minutes) if minutes else 0,
            "books": int(books) if books else 0,
            "pages": int(pages) if pages else 0,
        }

    # Build responses
    responses = []
    for reg in registrations:
        stats = stats_by_reg.get(reg.id, {"minutes": 0, "books": 0, "pages": 0})
        total_minutes = stats["minutes"]
        total_books = stats["books"]
        total_pages = stats["pages"]

        # Calculate progress percentage
        progress = 0.0
        if reg.goal_target and reg.goal_target > 0 and reg.program:
            if reg.program.reading_goal_type == "minutes":
                progress = (total_minutes / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "books":
                progress = (total_books / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "pages":
                progress = (total_pages / reg.goal_target) * 100

        response = ReadingRegistrationResponse.model_validate(reg)
        response.total_minutes = total_minutes
        response.total_books = total_books
        response.total_pages = total_pages
        response.progress_percentage = min(round(progress, 2), 100.0)
        responses.append(response)

    return PaginatedRegistrationsResponse(
        items=responses,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/registrations",
    response_model=ReadingRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_for_program(
    registration: ReadingRegistrationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Register current user for a reading program."""

    # Check if program exists
    program = await get_or_404(db, ReadingProgram, registration.program_id, "Program not found")

    if not program.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program is not active")

    # Check if registration is within program dates
    today = date.today()
    if today < program.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration opens on {program.start_date.isoformat()}",
        )
    if today > program.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This program has ended and is no longer accepting registrations",
        )

    # Check if already registered
    existing_result = await db.execute(
        select(ReadingRegistration).where(
            and_(
                ReadingRegistration.user_id == current_user.id,
                ReadingRegistration.program_id == registration.program_id,
            )
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered for this program"
        )

    db_registration = ReadingRegistration(
        user_id=current_user.id,
        program_id=registration.program_id,
        goal_target=registration.goal_target,
    )

    db.add(db_registration)
    await db.commit()
    await db.refresh(db_registration)

    response = ReadingRegistrationResponse.model_validate(db_registration)
    response.total_minutes = 0
    response.total_books = 0
    response.total_pages = 0
    response.progress_percentage = 0.0

    return response


@router.get("/registrations/my", response_model=List[ReadingRegistrationResponse])
async def get_my_registrations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's program registrations."""

    # Eagerly load program to avoid N+1 queries
    result = await db.execute(
        select(ReadingRegistration)
        .options(selectinload(ReadingRegistration.program))
        .where(ReadingRegistration.user_id == current_user.id)
        .order_by(ReadingRegistration.registered_at.desc())
    )
    registrations = result.scalars().all()

    if not registrations:
        return []

    # Get all registration IDs
    reg_ids = [reg.id for reg in registrations]

    # Fetch all stats in a single query with GROUP BY (fixes N+1)
    stats_result = await db.execute(
        select(
            ReadingLogEntry.registration_id,
            func.sum(ReadingLogEntry.minutes_read),
            func.sum(ReadingLogEntry.books_read),
            func.sum(ReadingLogEntry.pages_read),
        )
        .where(ReadingLogEntry.registration_id.in_(reg_ids))
        .group_by(ReadingLogEntry.registration_id)
    )
    # Build stats lookup dict
    stats_by_reg = {}
    for row in stats_result.all():
        reg_id, minutes, books, pages = row
        stats_by_reg[reg_id] = {
            "minutes": int(minutes) if minutes else 0,
            "books": int(books) if books else 0,
            "pages": int(pages) if pages else 0,
        }

    responses = []
    for reg in registrations:
        # Get stats from pre-fetched lookup
        stats = stats_by_reg.get(reg.id, {"minutes": 0, "books": 0, "pages": 0})
        total_minutes = stats["minutes"]
        total_books = stats["books"]
        total_pages = stats["pages"]

        # Calculate progress percentage using eagerly loaded program
        progress = 0.0
        if reg.goal_target and reg.goal_target > 0 and reg.program:
            if reg.program.reading_goal_type == "minutes":
                progress = (total_minutes / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "books":
                progress = (total_books / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "pages":
                progress = (total_pages / reg.goal_target) * 100

        response = ReadingRegistrationResponse.model_validate(reg)
        response.total_minutes = total_minutes
        response.total_books = total_books
        response.total_pages = total_pages
        response.progress_percentage = min(round(progress, 2), 100.0)

        responses.append(response)

    return responses


# ============================================================================
# Reading Log Entries
# ============================================================================


@router.post(
    "/log-entries", response_model=ReadingLogEntryResponse, status_code=status.HTTP_201_CREATED
)
async def create_log_entry(
    entry: ReadingLogEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Log reading activity for a program registration."""
    await _validate_log_entry_context(entry, db, current_user)

    db_entry = ReadingLogEntry(**entry.model_dump())

    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)

    from ...services.reading_program_notifications_service import (
        try_send_progress_nudge_safe,
    )

    await try_send_progress_nudge_safe(db, db_entry.registration_id)

    return ReadingLogEntryResponse.model_validate(db_entry)


@router.get("/log-entries/my", response_model=List[ReadingLogEntryResponse])
async def get_my_log_entries(
    registration_id: Optional[int] = Query(None, description="Filter by registration"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's reading log entries."""

    # Get user's registrations
    reg_result = await db.execute(
        select(ReadingRegistration.id).where(ReadingRegistration.user_id == current_user.id)
    )
    user_registration_ids = [r[0] for r in reg_result.all()]

    if not user_registration_ids:
        return []

    query = select(ReadingLogEntry).where(
        ReadingLogEntry.registration_id.in_(user_registration_ids)
    )

    if registration_id:
        if registration_id not in user_registration_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Not your registration"
            )
        query = query.where(ReadingLogEntry.registration_id == registration_id)

    query = query.order_by(ReadingLogEntry.logged_at.desc()).limit(limit)

    result = await db.execute(query)
    entries = result.scalars().all()

    return [ReadingLogEntryResponse.model_validate(e) for e in entries]


@router.get("/progress/{registration_id}", response_model=ProgramProgressResponse)
async def get_program_progress(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get detailed progress for a program registration."""

    # Get registration
    registration = await get_or_404(
        db, ReadingRegistration, registration_id, "Registration not found"
    )

    # Check access
    is_staff = is_staff_or_admin(current_user)
    if not is_staff and registration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other users' progress"
        )

    # Get program
    program_result = await db.execute(
        select(ReadingProgram).where(ReadingProgram.id == registration.program_id)
    )
    program = program_result.scalar_one_or_none()

    # Get log entries
    entries_result = await db.execute(
        select(ReadingLogEntry)
        .where(ReadingLogEntry.registration_id == registration_id)
        .order_by(ReadingLogEntry.logged_at.desc())
    )
    log_entries = entries_result.scalars().all()

    # Get achievements
    achievements_result = await db.execute(
        select(ReadingAchievement).where(
            and_(
                ReadingAchievement.user_id == registration.user_id,
                ReadingAchievement.program_id == registration.program_id,
            )
        )
    )
    achievements = achievements_result.scalars().all()

    # Calculate summary stats
    total_minutes = sum(e.minutes_read for e in log_entries)
    total_books = sum(e.books_read for e in log_entries)
    total_pages = sum(e.pages_read for e in log_entries)
    days_participated = len(set(e.logged_at.date() for e in log_entries))

    # Calculate completion percentage
    completion = 0.0
    if registration.goal_target and registration.goal_target > 0 and program:
        if program.reading_goal_type == "minutes":
            completion = (total_minutes / registration.goal_target) * 100
        elif program.reading_goal_type == "books":
            completion = (total_books / registration.goal_target) * 100
        elif program.reading_goal_type == "pages":
            completion = (total_pages / registration.goal_target) * 100

    return ProgramProgressResponse(
        registration=ReadingRegistrationResponse.model_validate(registration),
        program=ReadingProgramResponse.model_validate(program),
        log_entries=[ReadingLogEntryResponse.model_validate(e) for e in log_entries],
        achievements=[ReadingAchievementResponse.model_validate(a) for a in achievements],
        total_minutes=total_minutes,
        total_books=total_books,
        total_pages=total_pages,
        days_participated=days_participated,
        completion_percentage=min(round(completion, 2), 100.0),
    )


# ============================================================================
# Leaderboard Endpoints (Upgrade 2)
# ============================================================================


class LeaderboardEntry(BaseModel):
    rank: int
    display_name: str
    total_books: int
    total_minutes: int
    total_pages: int
    achievement_count: int
    current_streak: int
    completion_percentage: float


class LeaderboardResponse(BaseModel):
    program_id: int
    program_name: str
    leaderboard_type: str
    entries: List[LeaderboardEntry]
    total_participants: int
    user_rank: Optional[int] = None


@router.get("/programs/{program_id}/leaderboard", response_model=LeaderboardResponse)
@limiter.limit("60/minute")
async def get_program_leaderboard(
    request: Request,
    program_id: int,
    sort_by: str = Query("minutes", description="Sort by: minutes, books, pages, achievements"),
    limit: int = Query(25, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Get leaderboard for a reading program.
    Ranking, ordering, and pagination run at the SQL level so programs with
    thousands of participants stay fast and memory-bounded.
    """
    program = await get_or_404(db, ReadingProgram, program_id, "Program not found")

    valid_sort = ["minutes", "books", "pages", "achievements"]
    if sort_by not in valid_sort:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"sort_by must be one of: {valid_sort}"
        )

    stats_subq = (
        select(
            ReadingLogEntry.registration_id.label("reg_id"),
            func.coalesce(func.sum(ReadingLogEntry.minutes_read), 0).label("minutes"),
            func.coalesce(func.sum(ReadingLogEntry.books_read), 0).label("books"),
            func.coalesce(func.sum(ReadingLogEntry.pages_read), 0).label("pages"),
        )
        .group_by(ReadingLogEntry.registration_id)
        .subquery()
    )

    ach_subq = (
        select(
            ReadingAchievement.user_id.label("uid"),
            func.count(ReadingAchievement.id).label("ach_count"),
        )
        .where(ReadingAchievement.program_id == program_id)
        .group_by(ReadingAchievement.user_id)
        .subquery()
    )

    minutes_col = func.coalesce(stats_subq.c.minutes, 0)
    books_col = func.coalesce(stats_subq.c.books, 0)
    pages_col = func.coalesce(stats_subq.c.pages, 0)
    ach_col = func.coalesce(ach_subq.c.ach_count, 0)

    metric_col = {
        "minutes": minutes_col,
        "books": books_col,
        "pages": pages_col,
        "achievements": ach_col,
    }[sort_by]

    total_participants = (
        await db.execute(
            select(func.count(ReadingRegistration.id)).where(
                ReadingRegistration.program_id == program_id
            )
        )
    ).scalar() or 0

    if total_participants == 0:
        return LeaderboardResponse(
            program_id=program_id,
            program_name=program.name,
            leaderboard_type=sort_by,
            entries=[],
            total_participants=0,
            user_rank=None,
        )

    page_q = (
        select(
            ReadingRegistration.id.label("reg_id"),
            ReadingRegistration.user_id,
            ReadingRegistration.goal_target,
            User.first_name,
            minutes_col.label("minutes"),
            books_col.label("books"),
            pages_col.label("pages"),
            ach_col.label("ach_count"),
        )
        .join(User, User.id == ReadingRegistration.user_id)
        .outerjoin(stats_subq, stats_subq.c.reg_id == ReadingRegistration.id)
        .outerjoin(ach_subq, ach_subq.c.uid == ReadingRegistration.user_id)
        .where(ReadingRegistration.program_id == program_id)
        .order_by(metric_col.desc(), ReadingRegistration.id.asc())
        .limit(limit)
        .offset(offset)
    )
    page_rows = (await db.execute(page_q)).all()

    entries: List[LeaderboardEntry] = []
    for i, row in enumerate(page_rows, start=offset + 1):
        minutes_v = int(row.minutes or 0)
        books_v = int(row.books or 0)
        pages_v = int(row.pages or 0)
        ach_v = int(row.ach_count or 0)

        completion = 0.0
        if row.goal_target and row.goal_target > 0:
            if program.reading_goal_type == "minutes":
                completion = (minutes_v / row.goal_target) * 100
            elif program.reading_goal_type == "books":
                completion = (books_v / row.goal_target) * 100
            elif program.reading_goal_type == "pages":
                completion = (pages_v / row.goal_target) * 100

        display_name = f"Reader #{row.user_id % 10000:04d}"
        if row.first_name:
            display_name = f"{row.first_name[:1]}***"

        entries.append(
            LeaderboardEntry(
                rank=i,
                display_name=display_name,
                total_books=books_v,
                total_minutes=minutes_v,
                total_pages=pages_v,
                achievement_count=ach_v,
                current_streak=0,
                completion_percentage=min(round(completion, 2), 100.0),
            )
        )

    user_rank: Optional[int] = None
    if current_user:
        my_row = (
            await db.execute(
                select(metric_col.label("m"), ReadingRegistration.id.label("rid"))
                .select_from(ReadingRegistration)
                .outerjoin(stats_subq, stats_subq.c.reg_id == ReadingRegistration.id)
                .outerjoin(ach_subq, ach_subq.c.uid == ReadingRegistration.user_id)
                .where(
                    ReadingRegistration.program_id == program_id,
                    ReadingRegistration.user_id == current_user.id,
                )
            )
        ).first()
        if my_row is not None:
            my_metric = int(my_row.m or 0)
            my_rid = my_row.rid
            higher = (
                await db.execute(
                    select(func.count())
                    .select_from(ReadingRegistration)
                    .outerjoin(stats_subq, stats_subq.c.reg_id == ReadingRegistration.id)
                    .outerjoin(ach_subq, ach_subq.c.uid == ReadingRegistration.user_id)
                    .where(
                        ReadingRegistration.program_id == program_id,
                        or_(
                            metric_col > my_metric,
                            and_(metric_col == my_metric, ReadingRegistration.id < my_rid),
                        ),
                    )
                )
            ).scalar() or 0
            user_rank = int(higher) + 1

    return LeaderboardResponse(
        program_id=program_id,
        program_name=program.name,
        leaderboard_type=sort_by,
        entries=entries,
        total_participants=int(total_participants),
        user_rank=user_rank,
    )


# ============================================================================
# Streak Tracking Endpoints (Upgrade 3)
# ============================================================================


class StreakInfoResponse(BaseModel):
    current_streak: int
    longest_streak: int
    last_log_date: Optional[date] = None
    streak_at_risk: bool = False
    days_until_streak_lost: int = 1


@router.get("/registrations/{registration_id}/streak", response_model=StreakInfoResponse)
async def get_registration_streak(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get streak information for a reading registration.
    Tracks consecutive days of reading activity.
    """
    # Get registration
    registration = await get_or_404(
        db, ReadingRegistration, registration_id, "Registration not found"
    )

    # Check access
    is_staff = is_staff_or_admin(current_user)
    if not is_staff and registration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other users' streaks"
        )

    # Get all log entry dates
    entries_result = await db.execute(
        select(ReadingLogEntry.logged_at)
        .where(ReadingLogEntry.registration_id == registration_id)
        .order_by(ReadingLogEntry.logged_at.desc())
    )
    log_dates = [row[0].date() for row in entries_result.all()]

    if not log_dates:
        return StreakInfoResponse(
            current_streak=0,
            longest_streak=0,
            last_log_date=None,
            streak_at_risk=False,
            days_until_streak_lost=1,
        )

    # Get unique dates sorted
    unique_dates = sorted(set(log_dates), reverse=True)
    last_log = unique_dates[0]
    today = date.today()

    # Calculate current streak
    current_streak = 0
    days_gap = (today - last_log).days

    if days_gap <= 1:  # Logged today or yesterday
        current_streak = 1
        check_date = last_log
        for i in range(1, len(unique_dates)):
            expected = check_date - timedelta(days=1)
            if unique_dates[i] == expected:
                current_streak += 1
                check_date = unique_dates[i]
            else:
                break

    # Calculate longest streak (scan all dates)
    longest_streak = 0
    if unique_dates:
        streak = 1
        sorted_asc = sorted(unique_dates)
        for i in range(1, len(sorted_asc)):
            if (sorted_asc[i] - sorted_asc[i - 1]).days == 1:
                streak += 1
            else:
                longest_streak = max(longest_streak, streak)
                streak = 1
        longest_streak = max(longest_streak, streak)

    # Determine if streak is at risk
    streak_at_risk = days_gap == 1 and current_streak > 0
    days_until_lost = max(0, 2 - days_gap) if current_streak > 0 else 1

    return StreakInfoResponse(
        current_streak=current_streak,
        longest_streak=max(longest_streak, current_streak),
        last_log_date=last_log,
        streak_at_risk=streak_at_risk,
        days_until_streak_lost=days_until_lost,
    )


# ============================================================================
# Achievement Integration (connects to Upgrade 1)
# ============================================================================


class BadgeProgressResponse(BaseModel):
    badge_id: str
    name: str
    description: str
    type: str
    threshold: int
    current: int
    progress_percentage: float
    earned: bool
    earned_at: Optional[datetime] = None


@router.get("/registrations/{registration_id}/badges", response_model=List[BadgeProgressResponse])
async def get_badge_progress(
    registration_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get progress towards all available badges for a registration.
    Shows both earned and in-progress badges.
    """
    from ...services.reading_achievement_service import ReadingAchievementService

    # Get registration
    registration = await get_or_404(
        db, ReadingRegistration, registration_id, "Registration not found"
    )

    # Check access
    is_staff = is_staff_or_admin(current_user)
    if not is_staff and registration.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot view other users' badges"
        )

    # Use achievement service to get progress
    service = ReadingAchievementService(db)
    progress = await service.get_user_achievement_progress(
        registration.user_id, registration.program_id, registration_id
    )

    return [BadgeProgressResponse(**p) for p in progress]


@router.post(
    "/log-entries-with-achievements",
    response_model=LogEntryWithAchievementsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_log_entry_with_achievements(
    entry: ReadingLogEntryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log reading activity and automatically check for new achievements.
    Returns the log entry and any newly earned badges.
    """
    from ...services.reading_achievement_service import ReadingAchievementService

    registration, _ = await _validate_log_entry_context(entry, db, current_user)

    # Create log entry
    db_entry = ReadingLogEntry(**entry.model_dump())
    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)

    from ...services.reading_program_notifications_service import (
        try_send_progress_nudge_safe,
    )

    await try_send_progress_nudge_safe(db, db_entry.registration_id)

    # Check for new achievements
    service = ReadingAchievementService(db)
    new_achievements = await service.check_and_award_achievements(
        registration.user_id, registration.program_id, registration.id
    )

    return LogEntryWithAchievementsResponse(
        log_entry=ReadingLogEntryResponse.model_validate(db_entry),
        new_achievements=[ReadingAchievementResponse.model_validate(a) for a in new_achievements],
        achievements_earned=len(new_achievements),
    )


# ============================================================================
# Simplified Convenience Endpoints (Upgrade 4)
# ============================================================================


class JoinProgramRequest(BaseModel):
    program_id: int


class LogReadingRequest(BaseModel):
    program_id: int
    book_title: Optional[str] = None
    pages_read: int = 0
    reading_minutes: int = 0
    notes: Optional[str] = None


class ProgressResponseWithProgram(BaseModel):
    program_id: int
    program_name: str
    registration_id: int
    total_minutes: int
    total_books: int
    total_pages: int
    progress_percentage: float
    goal_target: Optional[int]
    days_participated: int


@router.post(
    "/join", response_model=ReadingRegistrationResponse, status_code=status.HTTP_201_CREATED
)
async def join_reading_program(
    request: JoinProgramRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Join a reading program (simplified endpoint).
    Takes only program_id and joins the authenticated user.
    """
    # Check if program exists
    program = await get_or_404(db, ReadingProgram, request.program_id, "Program not found")

    if not program.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program is not active")

    # Check if registration is within program dates
    today = date.today()
    if today < program.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration opens on {program.start_date.isoformat()}",
        )
    if today > program.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This program has ended and is no longer accepting registrations",
        )

    # Check if already registered
    existing_result = await db.execute(
        select(ReadingRegistration).where(
            and_(
                ReadingRegistration.user_id == current_user.id,
                ReadingRegistration.program_id == request.program_id,
            )
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Already registered for this program"
        )

    # Create registration with default goal if program has a goal value
    goal_target = program.reading_goal_value if program.reading_goal_value else None

    db_registration = ReadingRegistration(
        user_id=current_user.id,
        program_id=request.program_id,
        goal_target=goal_target,
    )

    db.add(db_registration)
    await db.commit()
    await db.refresh(db_registration)

    response = ReadingRegistrationResponse.model_validate(db_registration)
    response.total_minutes = 0
    response.total_books = 0
    response.total_pages = 0
    response.progress_percentage = 0.0

    return response


@router.get("/my-programs", response_model=List[ProgressResponseWithProgram])
async def get_my_programs(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all reading programs user is enrolled in with progress summary.
    Returns progress information for each enrolled program.
    """
    # Eagerly load program to avoid N+1 queries
    result = await db.execute(
        select(ReadingRegistration)
        .options(selectinload(ReadingRegistration.program))
        .where(ReadingRegistration.user_id == current_user.id)
        .order_by(ReadingRegistration.registered_at.desc())
    )
    registrations = result.scalars().all()

    if not registrations:
        return []

    # Get all registration IDs
    reg_ids = [reg.id for reg in registrations]

    # Fetch all stats in a single query with GROUP BY
    stats_result = await db.execute(
        select(
            ReadingLogEntry.registration_id,
            func.sum(ReadingLogEntry.minutes_read),
            func.sum(ReadingLogEntry.books_read),
            func.sum(ReadingLogEntry.pages_read),
        )
        .where(ReadingLogEntry.registration_id.in_(reg_ids))
        .group_by(ReadingLogEntry.registration_id)
    )
    # Build stats lookup dict
    stats_by_reg = {}
    for row in stats_result.all():
        reg_id, minutes, books, pages = row
        stats_by_reg[reg_id] = {
            "minutes": int(minutes) if minutes else 0,
            "books": int(books) if books else 0,
            "pages": int(pages) if pages else 0,
        }

    responses = []
    for reg in registrations:
        # Get stats from pre-fetched lookup
        stats = stats_by_reg.get(reg.id, {"minutes": 0, "books": 0, "pages": 0})
        total_minutes = stats["minutes"]
        total_books = stats["books"]
        total_pages = stats["pages"]

        # Calculate progress percentage using eagerly loaded program
        progress = 0.0
        if reg.goal_target and reg.goal_target > 0 and reg.program:
            if reg.program.reading_goal_type == "minutes":
                progress = (total_minutes / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "books":
                progress = (total_books / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "pages":
                progress = (total_pages / reg.goal_target) * 100

        # Count unique days with entries
        days_result = await db.execute(
            select(func.count(func.distinct(func.cast(ReadingLogEntry.logged_at, Date)))).where(
                ReadingLogEntry.registration_id == reg.id
            )
        )
        days_participated = days_result.scalar() or 0

        responses.append(
            ProgressResponseWithProgram(
                program_id=reg.program.id,
                program_name=reg.program.name,
                registration_id=reg.id,
                total_minutes=total_minutes,
                total_books=total_books,
                total_pages=total_pages,
                progress_percentage=min(round(progress, 2), 100.0),
                goal_target=reg.goal_target,
                days_participated=days_participated,
            )
        )

    return responses


@router.get("/progress", response_model=List[ProgressResponseWithProgram])
async def get_reading_progress(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get reading progress for all enrolled programs.
    Alias for /my-programs endpoint with same functionality.
    """
    # Eagerly load program to avoid N+1 queries
    result = await db.execute(
        select(ReadingRegistration)
        .options(selectinload(ReadingRegistration.program))
        .where(ReadingRegistration.user_id == current_user.id)
        .order_by(ReadingRegistration.registered_at.desc())
    )
    registrations = result.scalars().all()

    if not registrations:
        return []

    # Get all registration IDs
    reg_ids = [reg.id for reg in registrations]

    # Fetch all stats in a single query with GROUP BY
    stats_result = await db.execute(
        select(
            ReadingLogEntry.registration_id,
            func.sum(ReadingLogEntry.minutes_read),
            func.sum(ReadingLogEntry.books_read),
            func.sum(ReadingLogEntry.pages_read),
        )
        .where(ReadingLogEntry.registration_id.in_(reg_ids))
        .group_by(ReadingLogEntry.registration_id)
    )
    # Build stats lookup dict
    stats_by_reg = {}
    for row in stats_result.all():
        reg_id, minutes, books, pages = row
        stats_by_reg[reg_id] = {
            "minutes": int(minutes) if minutes else 0,
            "books": int(books) if books else 0,
            "pages": int(pages) if pages else 0,
        }

    responses = []
    for reg in registrations:
        # Get stats from pre-fetched lookup
        stats = stats_by_reg.get(reg.id, {"minutes": 0, "books": 0, "pages": 0})
        total_minutes = stats["minutes"]
        total_books = stats["books"]
        total_pages = stats["pages"]

        # Calculate progress percentage using eagerly loaded program
        progress = 0.0
        if reg.goal_target and reg.goal_target > 0 and reg.program:
            if reg.program.reading_goal_type == "minutes":
                progress = (total_minutes / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "books":
                progress = (total_books / reg.goal_target) * 100
            elif reg.program.reading_goal_type == "pages":
                progress = (total_pages / reg.goal_target) * 100

        # Count unique days with entries
        days_result = await db.execute(
            select(func.count(func.distinct(func.cast(ReadingLogEntry.logged_at, Date)))).where(
                ReadingLogEntry.registration_id == reg.id
            )
        )
        days_participated = days_result.scalar() or 0

        responses.append(
            ProgressResponseWithProgram(
                program_id=reg.program.id,
                program_name=reg.program.name,
                registration_id=reg.id,
                total_minutes=total_minutes,
                total_books=total_books,
                total_pages=total_pages,
                progress_percentage=min(round(progress, 2), 100.0),
                goal_target=reg.goal_target,
                days_participated=days_participated,
            )
        )

    return responses


@router.post(
    "/log-reading", response_model=ReadingLogEntryResponse, status_code=status.HTTP_201_CREATED
)
async def log_reading(
    request: LogReadingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log reading activity for a program (simplified endpoint).
    Takes program_id, book_title, pages_read, reading_minutes, and notes.
    Automatically finds the user's registration for the program.
    """
    # Find user's registration for this program
    reg_result = await db.execute(
        select(ReadingRegistration).where(
            and_(
                ReadingRegistration.user_id == current_user.id,
                ReadingRegistration.program_id == request.program_id,
            )
        )
    )
    registration = reg_result.scalar_one_or_none()

    if not registration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not registered for this program",
        )

    # Get the program and validate it's still accepting entries
    program = await get_or_404(db, ReadingProgram, request.program_id, "Program not found")

    if not program.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="This program is no longer active"
        )

    today = date.today()
    if today < program.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"This program hasn't started yet. Logging opens on {program.start_date.isoformat()}",
        )
    if today > program.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This program has ended and is no longer accepting reading logs",
        )

    # Validate reading data
    if request.pages_read < 0 or request.pages_read > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="pages_read must be between 0 and 10000",
        )

    if request.reading_minutes < 0 or request.reading_minutes > 120:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="reading_minutes must be between 0 and 120",
        )

    # Create log entry - count as 1 book if pages or minutes logged
    books_read = 1 if (request.pages_read > 0 or request.reading_minutes > 0) else 0

    db_entry = ReadingLogEntry(
        registration_id=registration.id,
        books_read=books_read,
        minutes_read=request.reading_minutes,
        pages_read=request.pages_read,
        title=request.book_title,
        notes=request.notes,
    )

    db.add(db_entry)
    await db.commit()
    await db.refresh(db_entry)

    from ...services.reading_program_notifications_service import (
        try_send_progress_nudge_safe,
    )

    await try_send_progress_nudge_safe(db, db_entry.registration_id)

    return ReadingLogEntryResponse.model_validate(db_entry)


@router.get("/join")
async def get_join(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a join dashboard of active programs and user registration state."""
    today = date.today()

    programs_result = await db.execute(
        select(ReadingProgram)
        .where(
            and_(
                ReadingProgram.is_active.is_(True),
                ReadingProgram.start_date <= today,
                ReadingProgram.end_date >= today,
            )
        )
        .order_by(ReadingProgram.start_date.asc(), ReadingProgram.id.asc())
    )
    programs = programs_result.scalars().all()

    reg_result = await db.execute(
        select(ReadingRegistration.program_id, ReadingRegistration.id).where(
            ReadingRegistration.user_id == current_user.id
        )
    )
    registrations = {program_id: reg_id for program_id, reg_id in reg_result.all()}

    return {
        "available_programs": [
            {
                "program_id": program.id,
                "name": program.name,
                "description": program.description,
                "program_type": str(program.program_type) if program.program_type else None,
                "age_group": program.age_group,
                "reading_goal_type": program.reading_goal_type,
                "reading_goal_value": program.reading_goal_value,
                "start_date": program.start_date.isoformat(),
                "end_date": program.end_date.isoformat(),
                "already_joined": program.id in registrations,
                "registration_id": registrations.get(program.id),
            }
            for program in programs
        ],
        "total_available": len(programs),
    }


@router.get("/log-entries")
async def get_log_entries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the current user's recent reading log entries across registrations."""
    reg_ids_result = await db.execute(
        select(ReadingRegistration.id).where(ReadingRegistration.user_id == current_user.id)
    )
    registration_ids = [rid for (rid,) in reg_ids_result.all()]

    if not registration_ids:
        return {"entries": [], "total": 0}

    entries_result = await db.execute(
        select(ReadingLogEntry)
        .where(ReadingLogEntry.registration_id.in_(registration_ids))
        .order_by(ReadingLogEntry.logged_at.desc())
        .limit(20)
    )
    entries = entries_result.scalars().all()

    return {
        "entries": [
            ReadingLogEntryResponse.model_validate(entry).model_dump(mode="json")
            for entry in entries
        ],
        "total": len(entries),
    }


@router.get("/log-entries-with-achievements")
async def get_log_entries_with_achievements(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get recent log entries with achievement summary for the current user."""
    reg_ids_result = await db.execute(
        select(ReadingRegistration.id, ReadingRegistration.program_id).where(
            ReadingRegistration.user_id == current_user.id
        )
    )
    registrations = reg_ids_result.all()
    registration_ids = [rid for rid, _ in registrations]

    if not registration_ids:
        return {"entries": [], "achievements": [], "totals": {"entries": 0, "achievements": 0}}

    entries_result = await db.execute(
        select(ReadingLogEntry)
        .where(ReadingLogEntry.registration_id.in_(registration_ids))
        .order_by(ReadingLogEntry.logged_at.desc())
        .limit(20)
    )
    entries = entries_result.scalars().all()

    program_ids = [pid for _, pid in registrations]
    achievements_result = await db.execute(
        select(ReadingAchievement)
        .where(
            and_(
                ReadingAchievement.user_id == current_user.id,
                ReadingAchievement.program_id.in_(program_ids),
            )
        )
        .order_by(ReadingAchievement.unlocked_at.desc())
    )
    achievements = achievements_result.scalars().all()

    return {
        "entries": [
            ReadingLogEntryResponse.model_validate(entry).model_dump(mode="json")
            for entry in entries
        ],
        "achievements": [
            {
                "badge_id": achievement.badge_id,
                "badge_name": achievement.badge_name,
                "badge_description": achievement.badge_description,
                "program_id": achievement.program_id,
                "unlocked_at": achievement.unlocked_at.isoformat(),
            }
            for achievement in achievements
        ],
        "totals": {"entries": len(entries), "achievements": len(achievements)},
    }


@router.get("/log-reading")
async def get_log_reading(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get metadata for logging reading activity."""
    return {
        "required_fields": ["program_id"],
        "optional_fields": ["book_title", "pages_read", "reading_minutes", "notes"],
        "validation": {
            "pages_read": {"min": 0, "max": 10000},
            "reading_minutes": {"min": 0, "max": 120},
        },
        "message": "Use POST /reading-programs/log-reading to submit reading activity.",
    }


# Keep extracted route groups at the end to preserve FastAPI match order.
router.include_router(booklist_router)
router.include_router(paper_log_router)
