# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Shelf Reading API routes.

Shelf reading verifies that items on library shelves are in correct
call number order. Endpoints cover:
- Session management (create, pause, resume, complete, cancel)
- Item scanning with order detection
- Schedule management for regular shelf reads
- Accuracy reports and historical trends
- Gamification leaderboards
- Branch-level tracking
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...models.inventory import ItemCopy
from ...models.multi_branch import Branch
from ...models.shelf_reading import (
    ScanResult,
    ShelfReadingSchedule,
    ShelfReadingScan,
    ShelfReadingSession,
    ShelfReadingStatus,
)
from ...models.user import User
from ...schemas.shelf_reading import (
    BranchAccuracySummary,
    HistoricalAccuracyReport,
    ShelfAccuracyReport,
    ShelfReadingLeaderboard,
    ShelfReadingProgress,
    ShelfReadingScanCreate,
    ShelfReadingScanListResponse,
    ShelfReadingScanResponse,
    ShelfReadingScheduleCreate,
    ShelfReadingScheduleListResponse,
    ShelfReadingScheduleResponse,
    ShelfReadingScheduleUpdate,
    ShelfReadingSessionCreate,
    ShelfReadingSessionListResponse,
    ShelfReadingSessionResponse,
)
from ...services.shelf_reading_service import ShelfReadingService
from .auth import get_current_user
from .dependencies import require_staff

router = APIRouter(prefix="/shelf-reading", tags=["shelf-reading"])


# ============ Sessions ============


@router.get("/sessions", response_model=ShelfReadingSessionListResponse)
async def list_sessions(
    branch_id: int | None = Query(None),
    status_filter: ShelfReadingStatus | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List shelf reading sessions with optional filters."""
    await require_staff(current_user)

    query = select(ShelfReadingSession).options(
        selectinload(ShelfReadingSession.created_by),
        selectinload(ShelfReadingSession.branch),
    )
    count_query = select(func.count(ShelfReadingSession.id))

    if branch_id:
        query = query.where(ShelfReadingSession.branch_id == branch_id)
        count_query = count_query.where(ShelfReadingSession.branch_id == branch_id)

    if status_filter:
        query = query.where(ShelfReadingSession.status == status_filter)
        count_query = count_query.where(ShelfReadingSession.status == status_filter)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(
        ShelfReadingSession.started_at.desc()
    )

    result = await db.execute(query)
    sessions = result.scalars().all()

    items = []
    for session in sessions:
        item_dict = ShelfReadingSessionResponse.model_validate(session).model_dump()
        item_dict["created_by_name"] = (
            session.created_by.full_name if session.created_by else None
        )
        item_dict["branch_name"] = (
            session.branch.name if session.branch else None
        )
        items.append(item_dict)

    return ShelfReadingSessionListResponse(
        items=items, total=total, page=page, per_page=per_page
    )


@router.post(
    "/sessions",
    response_model=ShelfReadingSessionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    session_in: ShelfReadingSessionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Start a new shelf reading session."""
    await require_staff(current_user)

    # Verify branch exists
    branch_result = await db.execute(
        select(Branch).where(Branch.id == session_in.branch_id)
    )
    branch = branch_result.scalar_one_or_none()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found"
        )

    session = await ShelfReadingService.create_session(
        db=db,
        name=session_in.name,
        branch_id=session_in.branch_id,
        location=session_in.location,
        created_by_id=current_user.id,
        description=session_in.description,
        call_number_start=session_in.call_number_start,
        call_number_end=session_in.call_number_end,
    )
    await db.commit()
    await db.refresh(session)

    response = ShelfReadingSessionResponse.model_validate(session)
    response.branch_name = branch.name
    return response


@router.get("/sessions/{session_id}", response_model=ShelfReadingSessionResponse)
async def get_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get shelf reading session details."""
    await require_staff(current_user)

    session = await ShelfReadingService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    response = ShelfReadingSessionResponse.model_validate(session)
    response.created_by_name = (
        session.created_by.full_name if session.created_by else None
    )
    response.branch_name = session.branch.name if session.branch else None
    return response


@router.get(
    "/sessions/{session_id}/progress", response_model=ShelfReadingProgress
)
async def get_session_progress(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current progress for a shelf reading session."""
    await require_staff(current_user)

    session = await ShelfReadingService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Get last scanned call number
    last_scan_result = await db.execute(
        select(ShelfReadingScan)
        .where(ShelfReadingScan.session_id == session_id)
        .order_by(ShelfReadingScan.scan_order.desc())
        .limit(1)
    )
    last_scan = last_scan_result.scalar_one_or_none()

    return ShelfReadingProgress(
        session_id=session.id,
        session_name=session.name,
        status=session.status,
        total_items_scanned=session.total_items_scanned,
        items_in_order=session.items_in_order,
        items_out_of_order=session.items_out_of_order,
        items_wrong_shelf=session.items_wrong_shelf,
        accuracy_percentage=session.accuracy_percentage,
        last_scanned_call_number=(
            last_scan.scanned_call_number if last_scan else None
        ),
        points_earned=session.points_earned,
    )


@router.post(
    "/sessions/{session_id}/complete",
    response_model=ShelfReadingSessionResponse,
)
async def complete_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Complete a shelf reading session."""
    await require_staff(current_user)

    session = await ShelfReadingService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if session.status == ShelfReadingStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session already completed",
        )
    if session.status == ShelfReadingStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled session",
        )

    session = await ShelfReadingService.complete_session(db, session)

    # Update schedule if this session was for a scheduled read
    await _update_schedule_on_completion(db, session)

    await db.commit()
    await db.refresh(session)

    response = ShelfReadingSessionResponse.model_validate(session)
    response.created_by_name = (
        session.created_by.full_name if session.created_by else None
    )
    response.branch_name = session.branch.name if session.branch else None
    return response


@router.post(
    "/sessions/{session_id}/pause",
    response_model=ShelfReadingSessionResponse,
)
async def pause_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Pause a shelf reading session."""
    await require_staff(current_user)

    session = await ShelfReadingService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if session.status != ShelfReadingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only in-progress sessions can be paused",
        )

    session = await ShelfReadingService.pause_session(db, session)
    await db.commit()
    await db.refresh(session)

    response = ShelfReadingSessionResponse.model_validate(session)
    response.branch_name = session.branch.name if session.branch else None
    return response


@router.post(
    "/sessions/{session_id}/resume",
    response_model=ShelfReadingSessionResponse,
)
async def resume_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resume a paused shelf reading session."""
    await require_staff(current_user)

    session = await ShelfReadingService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if session.status != ShelfReadingStatus.PAUSED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only paused sessions can be resumed",
        )

    session = await ShelfReadingService.resume_session(db, session)
    await db.commit()
    await db.refresh(session)

    response = ShelfReadingSessionResponse.model_validate(session)
    response.branch_name = session.branch.name if session.branch else None
    return response


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=ShelfReadingSessionResponse,
)
async def cancel_session(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Cancel a shelf reading session."""
    await require_staff(current_user)

    session = await ShelfReadingService.get_session(db, session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if session.status in (ShelfReadingStatus.COMPLETED, ShelfReadingStatus.CANCELLED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is already completed or cancelled",
        )

    session = await ShelfReadingService.cancel_session(db, session)
    await db.commit()
    await db.refresh(session)

    response = ShelfReadingSessionResponse.model_validate(session)
    response.branch_name = session.branch.name if session.branch else None
    return response


# ============ Scanning ============


@router.post(
    "/sessions/{session_id}/scan",
    response_model=ShelfReadingScanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def scan_item(
    session_id: int,
    scan_in: ShelfReadingScanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Scan an item during shelf reading.

    Scans the item's barcode and determines:
    - If the item is in correct call number order
    - If the item is out of order relative to the previous scan
    - If the item is on the wrong shelf entirely
    """
    await require_staff(current_user)

    # Get session (with lock to prevent concurrent stat updates)
    session_result = await db.execute(
        select(ShelfReadingSession)
        .where(ShelfReadingSession.id == session_id)
        .options(selectinload(ShelfReadingSession.branch))
        .with_for_update()
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )
    if session.status != ShelfReadingStatus.IN_PROGRESS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not in progress",
        )

    # Find item by barcode
    copy_result = await db.execute(
        select(ItemCopy)
        .where(ItemCopy.barcode == scan_in.barcode)
        .options(selectinload(ItemCopy.catalog_item))
    )
    copy = copy_result.scalar_one_or_none()
    if not copy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found with this barcode",
        )

    # Check if already scanned in this session
    existing = await db.execute(
        select(ShelfReadingScan).where(
            ShelfReadingScan.session_id == session_id,
            ShelfReadingScan.item_copy_id == copy.id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Item already scanned in this session",
        )

    scan = await ShelfReadingService.scan_item(
        db=db,
        session=session,
        item_copy=copy,
        scanned_by_id=current_user.id,
    )

    await db.commit()
    await db.refresh(scan)

    response = ShelfReadingScanResponse.model_validate(scan)
    response.barcode = copy.barcode
    response.catalog_title = copy.catalog_item.title if copy.catalog_item else None
    response.catalog_author = copy.catalog_item.author if copy.catalog_item else None
    return response


@router.get(
    "/sessions/{session_id}/scans", response_model=ShelfReadingScanListResponse
)
async def list_session_scans(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all scans for a shelf reading session."""
    await require_staff(current_user)

    # Verify session exists
    session_result = await db.execute(
        select(ShelfReadingSession).where(ShelfReadingSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    scans = await ShelfReadingService.get_session_scans(db, session_id)

    items = []
    for scan in scans:
        item_dict = ShelfReadingScanResponse.model_validate(scan).model_dump()
        if scan.item_copy:
            item_dict["barcode"] = scan.item_copy.barcode
            if scan.item_copy.catalog_item:
                item_dict["catalog_title"] = scan.item_copy.catalog_item.title
                item_dict["catalog_author"] = scan.item_copy.catalog_item.author
        items.append(item_dict)

    return ShelfReadingScanListResponse(
        items=items,
        total=len(items),
        session_accuracy=session.accuracy_percentage,
    )


# ============ Schedules ============


@router.get("/schedules", response_model=ShelfReadingScheduleListResponse)
async def list_schedules(
    branch_id: int | None = Query(None),
    active_only: bool = Query(True),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List shelf reading schedules."""
    await require_staff(current_user)

    query = select(ShelfReadingSchedule).options(
        selectinload(ShelfReadingSchedule.assigned_to),
        selectinload(ShelfReadingSchedule.branch),
        selectinload(ShelfReadingSchedule.created_by),
    )
    count_query = select(func.count(ShelfReadingSchedule.id))

    if branch_id:
        query = query.where(ShelfReadingSchedule.branch_id == branch_id)
        count_query = count_query.where(ShelfReadingSchedule.branch_id == branch_id)

    if active_only:
        query = query.where(ShelfReadingSchedule.is_active == True)  # noqa: E712
        count_query = count_query.where(ShelfReadingSchedule.is_active == True)  # noqa: E712

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = query.offset(offset).limit(per_page).order_by(
        ShelfReadingSchedule.next_due_at.asc().nullslast()
    )

    result = await db.execute(query)
    schedules = result.scalars().all()

    items = []
    for schedule in schedules:
        item_dict = ShelfReadingScheduleResponse.model_validate(schedule).model_dump()
        item_dict["assigned_to_name"] = (
            schedule.assigned_to.full_name if schedule.assigned_to else None
        )
        item_dict["branch_name"] = (
            schedule.branch.name if schedule.branch else None
        )
        items.append(item_dict)

    return ShelfReadingScheduleListResponse(
        items=items, total=total, page=page, per_page=per_page
    )


@router.post(
    "/schedules",
    response_model=ShelfReadingScheduleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_schedule(
    schedule_in: ShelfReadingScheduleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new shelf reading schedule."""
    await require_staff(current_user)

    # Verify branch
    branch_result = await db.execute(
        select(Branch).where(Branch.id == schedule_in.branch_id)
    )
    branch = branch_result.scalar_one_or_none()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found"
        )

    schedule = ShelfReadingSchedule(
        **schedule_in.model_dump(),
        created_by_id=current_user.id,
    )
    db.add(schedule)
    await db.commit()
    await db.refresh(schedule)

    response = ShelfReadingScheduleResponse.model_validate(schedule)
    response.branch_name = branch.name
    return response


@router.get(
    "/schedules/{schedule_id}", response_model=ShelfReadingScheduleResponse
)
async def get_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get shelf reading schedule details."""
    await require_staff(current_user)

    result = await db.execute(
        select(ShelfReadingSchedule)
        .where(ShelfReadingSchedule.id == schedule_id)
        .options(
            selectinload(ShelfReadingSchedule.assigned_to),
            selectinload(ShelfReadingSchedule.branch),
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
        )

    response = ShelfReadingScheduleResponse.model_validate(schedule)
    response.assigned_to_name = (
        schedule.assigned_to.full_name if schedule.assigned_to else None
    )
    response.branch_name = schedule.branch.name if schedule.branch else None
    return response


@router.patch(
    "/schedules/{schedule_id}", response_model=ShelfReadingScheduleResponse
)
async def update_schedule(
    schedule_id: int,
    schedule_in: ShelfReadingScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a shelf reading schedule."""
    await require_staff(current_user)

    result = await db.execute(
        select(ShelfReadingSchedule)
        .where(ShelfReadingSchedule.id == schedule_id)
        .options(
            selectinload(ShelfReadingSchedule.assigned_to),
            selectinload(ShelfReadingSchedule.branch),
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
        )

    update_data = schedule_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(schedule, field, value)
    schedule.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(schedule)

    response = ShelfReadingScheduleResponse.model_validate(schedule)
    response.assigned_to_name = (
        schedule.assigned_to.full_name if schedule.assigned_to else None
    )
    response.branch_name = schedule.branch.name if schedule.branch else None
    return response


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a shelf reading schedule."""
    await require_staff(current_user)

    result = await db.execute(
        select(ShelfReadingSchedule).where(ShelfReadingSchedule.id == schedule_id)
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found"
        )

    await db.delete(schedule)
    await db.commit()


@router.get("/schedules/due", response_model=ShelfReadingScheduleListResponse)
async def list_due_schedules(
    branch_id: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List shelf reading schedules that are due or overdue."""
    await require_staff(current_user)

    now = datetime.now(timezone.utc)
    query = (
        select(ShelfReadingSchedule)
        .where(
            ShelfReadingSchedule.is_active == True,  # noqa: E712
            ShelfReadingSchedule.next_due_at <= now,
        )
        .options(
            selectinload(ShelfReadingSchedule.assigned_to),
            selectinload(ShelfReadingSchedule.branch),
        )
    )

    if branch_id:
        query = query.where(ShelfReadingSchedule.branch_id == branch_id)

    query = query.order_by(ShelfReadingSchedule.next_due_at.asc())

    result = await db.execute(query)
    schedules = result.scalars().all()

    items = []
    for schedule in schedules:
        item_dict = ShelfReadingScheduleResponse.model_validate(schedule).model_dump()
        item_dict["assigned_to_name"] = (
            schedule.assigned_to.full_name if schedule.assigned_to else None
        )
        item_dict["branch_name"] = (
            schedule.branch.name if schedule.branch else None
        )
        items.append(item_dict)

    return ShelfReadingScheduleListResponse(
        items=items, total=len(items), page=1, per_page=len(items) or 20
    )


# ============ Reports ============


@router.get("/reports/accuracy", response_model=ShelfAccuracyReport)
async def get_accuracy_report(
    branch_id: int = Query(...),
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a shelving accuracy report for a branch."""
    await require_staff(current_user)

    period_end = datetime.now(timezone.utc)
    period_start = period_end - timedelta(days=days)

    report = await ShelfReadingService.get_accuracy_report(
        db, branch_id, period_start, period_end
    )
    return ShelfAccuracyReport(**report)


@router.get("/reports/branches", response_model=list[BranchAccuracySummary])
async def get_branch_summaries(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get accuracy summaries for all branches."""
    await require_staff(current_user)

    summaries = await ShelfReadingService.get_branch_summaries(db)
    return [BranchAccuracySummary(**s) for s in summaries]


@router.get(
    "/reports/history/{branch_id}", response_model=HistoricalAccuracyReport
)
async def get_historical_accuracy(
    branch_id: int,
    months: int = Query(12, ge=1, le=36),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get historical accuracy trends for a branch."""
    await require_staff(current_user)

    # Get branch name
    branch_result = await db.execute(
        select(Branch).where(Branch.id == branch_id)
    )
    branch = branch_result.scalar_one_or_none()
    if not branch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Branch not found"
        )

    data_points = await ShelfReadingService.get_historical_accuracy(
        db, branch_id, months
    )

    return HistoricalAccuracyReport(
        branch_id=branch_id,
        branch_name=branch.name,
        data_points=data_points,
    )


# ============ Gamification ============


@router.get("/leaderboard", response_model=ShelfReadingLeaderboard)
async def get_leaderboard(
    period: str = Query("all_time", pattern="^(all_time|weekly|monthly)$"),
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get the shelf reading leaderboard."""
    await require_staff(current_user)

    entries = await ShelfReadingService.get_leaderboard(db, period, limit)
    return ShelfReadingLeaderboard(entries=entries, period=period)


# ============ Helpers ============


async def _update_schedule_on_completion(
    db: AsyncSession, session: ShelfReadingSession
) -> None:
    # Find matching active schedule
    result = await db.execute(
        select(ShelfReadingSchedule).where(
            ShelfReadingSchedule.branch_id == session.branch_id,
            ShelfReadingSchedule.location == session.location,
            ShelfReadingSchedule.is_active == True,  # noqa: E712
        )
    )
    schedule = result.scalar_one_or_none()
    if not schedule:
        return

    schedule.last_completed_at = session.completed_at

    # Calculate next due date based on frequency
    freq_days = {
        "weekly": 7,
        "biweekly": 14,
        "monthly": 30,
        "quarterly": 90,
    }
    days = freq_days.get(str(schedule.frequency), 30)
    schedule.next_due_at = session.completed_at + timedelta(days=days)
    schedule.updated_at = datetime.now(timezone.utc)
