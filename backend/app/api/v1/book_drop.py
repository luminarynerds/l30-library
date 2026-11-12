# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Book Drop and Batch Check-in API Endpoints.

Provides endpoints for:
- Book drop configuration management
- Batch check-in sessions
- Check-in statistics and analytics
- SIP2 device management
- Exception handling

All endpoints require staff authentication.
"""

from app.core.logging import get_logger
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.branch_resolver import label_to_branch_id
from ...core.shortcuts import get_or_404
from ...core.exceptions import APIError
from ...models.book_drop import (
    BookDrop, BookDropStatus, CheckInSession, CheckInSessionStatus,
    CheckInResult, CheckInResultStatus, CheckInStatistic,
    CheckInException, ExceptionType, SIP2Device, SortDestination
)
from ...models.user import User
from ...models.catalog import CatalogItem
from ...models.inventory import ItemCopy
from ...schemas.book_drop import (
    BookDropCreate, BookDropUpdate, BookDropResponse,
    SIP2DeviceCreate, SIP2DeviceUpdate, SIP2DeviceResponse,
    CheckInSessionCreate, CheckInSessionResponse, CheckInSessionSummary,
    BatchCheckInItem, BatchCheckInRequest, SingleCheckInRequest,
    CheckInResultResponse, BatchCheckInResponse,
    BookDropCheckInRequest, BookDropCheckInResponse,
    CheckInExceptionResponse, ResolveExceptionRequest,
    CheckInStatisticResponse, StatisticsQuery, StatisticsSummary,
    ConditionCheckRequest, ConditionCheckResponse,
    FastProcessingScanRequest, FastProcessingResponse, DestinationSummary,
    ClaimsReturnedResolution, DamageCheckRequirement
)
from ...services.book_drop_service import BookDropService
from ...services.batch_checkin_service import BatchCheckInService
from ...services.sip2_service import SIP2Service
from .auth import get_current_user
from .dependencies import require_staff, require_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/book-drop", tags=["book-drop"])


# =============================================================================
# Book Drop Management
# =============================================================================

@router.post("/locations", response_model=BookDropResponse, status_code=status.HTTP_201_CREATED)
async def create_book_drop(
    data: BookDropCreate,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new book drop location.

    Requires admin role. Book drops represent physical locations where
    patrons can return items outside of regular service hours.
    """
    service = BookDropService(db)

    try:
        book_drop = await service.create_book_drop(
            name=data.name,
            code=data.code,
            branch_location=data.branch_location,
            created_by=staff_user,
            description=data.description,
            physical_location=data.physical_location,
            backdate_mode=data.backdate_mode,
            backdate_fixed_time=data.backdate_fixed_time,
            backdate_hours=data.backdate_hours,
            backdate_days=data.backdate_days,
            processing_start_time=data.processing_start_time,
            processing_end_time=data.processing_end_time,
            exempt_overnight_fines=data.exempt_overnight_fines,
            max_backdate_hours=data.max_backdate_hours,
            sip2_device_id=data.sip2_device_id,
        )
        await db.commit()

        logger.info(f"Book drop created: {book_drop.code} by user {staff_user.id}")
        return book_drop

    except HTTPException:
        raise
    except APIError:
        # e.g. ConflictError (duplicate code) -> handled by the global
        # APIError handler (main.py), which returns the correct status
        # code (409) instead of being swallowed into a generic 500 below.
        raise
    except Exception as e:
        logger.error(f"Failed to create book drop: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create book drop"
        ) from e


@router.get("/locations", response_model=list[BookDropResponse])
async def list_book_drops(
    branch_location: Optional[str] = Query(None, description="Filter by branch"),
    branch_id: Optional[int] = Query(None, description="Filter by branch FK (preferred)"),
    status_filter: Optional[BookDropStatus] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    List all book drop locations.

    Supports filtering by branch location and status.
    """
    service = BookDropService(db)
    book_drops, total = await service.list_book_drops(
        branch_location=branch_location,
        status_filter=status_filter,
        limit=limit,
        offset=offset
    )
    return book_drops


@router.get("/locations/{book_drop_id}", response_model=BookDropResponse)
async def get_book_drop(
    book_drop_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific book drop by ID."""
    service = BookDropService(db)
    book_drop = await service.get_book_drop(book_drop_id)

    if not book_drop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book drop not found"
        )

    return book_drop


@router.patch("/locations/{book_drop_id}", response_model=BookDropResponse)
async def update_book_drop(
    book_drop_id: int,
    data: BookDropUpdate,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update book drop configuration.

    Requires admin role.
    """
    service = BookDropService(db)

    try:
        book_drop = await service.update_book_drop(
            book_drop_id,
            **data.model_dump(exclude_unset=True)
        )
        await db.commit()

        logger.info(f"Book drop {book_drop_id} updated by user {staff_user.id}")
        return book_drop

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update book drop: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update book drop"
        ) from e


@router.delete("/locations/{book_drop_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_book_drop(
    book_drop_id: int,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a book drop location.

    Requires admin role. Will fail if there are active sessions.
    """
    service = BookDropService(db)
    book_drop = await service.get_book_drop(book_drop_id)

    if not book_drop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book drop not found"
        )

    # Check for active sessions
    result = await db.execute(
        select(CheckInSession).where(
            CheckInSession.book_drop_id == book_drop_id,
            CheckInSession.status == CheckInSessionStatus.ACTIVE
        )
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete book drop with active sessions"
        )

    await db.delete(book_drop)
    await db.commit()

    logger.info(f"Book drop {book_drop_id} deleted by user {staff_user.id}")


# =============================================================================
# Check-in Sessions
# =============================================================================

@router.post("/sessions", response_model=CheckInSessionResponse, status_code=status.HTTP_201_CREATED)
async def start_checkin_session(
    data: CheckInSessionCreate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a new batch check-in session.

    Creates a session for batch processing. If book_drop_id is provided,
    backdating will be calculated based on the book drop's configuration.
    """
    service = BookDropService(db)

    try:
        session = await service.start_session(
            staff=staff_user,
            branch_location=data.branch_location,
            book_drop_id=data.book_drop_id,
            workstation_id=data.workstation_id
        )

        # Handle manual backdating override
        if data.backdate_to and not session.book_drop_id:
            session.use_backdating = True
            session.backdate_to = data.backdate_to

        await db.commit()

        logger.info(
            f"Check-in session started: {session.session_code} "
            f"by user {staff_user.id}"
        )

        return session

    except Exception as e:
        logger.error(f"Failed to start session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start check-in session"
        ) from e


@router.get("/sessions", response_model=list[CheckInSessionSummary])
async def list_sessions(
    branch_location: Optional[str] = Query(None, deprecated=True),
    branch_id: Optional[int] = Query(None),
    status_filter: Optional[CheckInSessionStatus] = Query(None, alias="status"),
    limit: int = Query(20, ge=1, le=100),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List recent check-in sessions.

    branch_id is preferred; branch_location resolves via the canonical map.
    """
    if branch_id is None and branch_location:
        branch_id = label_to_branch_id(branch_location)
    batch_service = BatchCheckInService(db)
    sessions = await batch_service.get_recent_sessions(
        branch_location=branch_location,
        limit=limit,
        branch_id=branch_id,
    )

    # Build summary response with staff names
    results = []
    for session in sessions:
        staff_name = None
        if session.staff:
            staff_name = f"{session.staff.first_name} {session.staff.last_name}"

        results.append(CheckInSessionSummary(
            id=session.id,
            session_code=session.session_code,
            branch_id=session.branch_id,
            branch_location=session.branch_location,
            status=session.status,
            started_at=session.started_at,
            ended_at=session.ended_at,
            total_items=session.total_items,
            staff_name=staff_name
        ))

    return results


@router.get("/sessions/active", response_model=list[CheckInSessionResponse])
async def list_active_sessions(
    branch_location: Optional[str] = Query(None, deprecated=True),
    branch_id: Optional[int] = Query(None),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List currently active check-in sessions.

    branch_id is preferred; branch_location resolves via the canonical map.
    """
    if branch_id is None and branch_location:
        branch_id = label_to_branch_id(branch_location)
    batch_service = BatchCheckInService(db)
    sessions = await batch_service.list_active_sessions(
        branch_location=branch_location,
        branch_id=branch_id,
    )
    return sessions


@router.get("/sessions/{session_id}", response_model=CheckInSessionResponse)
async def get_session(
    session_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get check-in session details."""
    service = BookDropService(db)
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    # Calculate success rate
    success_rate = None
    if session.total_items > 0:
        success_rate = session.successful_checkins / session.total_items * 100

    return CheckInSessionResponse(
        id=session.id,
        session_code=session.session_code,
        book_drop_id=session.book_drop_id,
        branch_location=session.branch_location,
        workstation_id=session.workstation_id,
        staff_id=session.staff_id,
        status=session.status,
        started_at=session.started_at,
        ended_at=session.ended_at,
        use_backdating=session.use_backdating,
        backdate_to=session.backdate_to,
        total_items=session.total_items,
        successful_checkins=session.successful_checkins,
        holds_trapped=session.holds_trapped,
        transits_created=session.transits_created,
        exceptions_count=session.exceptions_count,
        success_rate=success_rate
    )


@router.get("/sessions/{session_id}/summary")
async def get_session_summary(
    session_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed session summary with breakdowns."""
    batch_service = BatchCheckInService(db)

    try:
        summary = await batch_service.get_session_summary(session_id)
        return summary
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e


@router.post("/sessions/{session_id}/end", response_model=CheckInSessionResponse)
async def end_session(
    session_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """End a check-in session."""
    service = BookDropService(db)

    try:
        session = await service.end_session(session_id)
        await db.commit()

        logger.info(f"Session {session.session_code} ended by user {staff_user.id}")
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to end session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to end session"
        ) from e


# =============================================================================
# Check-in Operations
# =============================================================================

@router.post("/sessions/{session_id}/checkin", response_model=CheckInResultResponse)
async def checkin_single_item(
    session_id: int,
    data: SingleCheckInRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Check in a single item within a session.

    This is the primary endpoint for real-time check-in operations.
    """
    service = BookDropService(db)

    # Get session
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status != CheckInSessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active"
        )

    try:
        result = await service.process_checkin(
            session=session,
            barcode=data.barcode,
            staff=staff_user,
            condition_status=data.condition_status,
            condition_notes=data.condition_notes,
            override_backdate=data.override_backdate
        )
        await db.commit()

        # Build response with item details
        item_title = None
        item_author = None
        hold_patron_name = None

        if result.item_copy_id:
            item_result = await db.execute(
                select(ItemCopy)
                .options(selectinload(ItemCopy.catalog_item))
                .where(ItemCopy.id == result.item_copy_id)
            )
            item_copy = item_result.scalar_one_or_none()
            if item_copy and item_copy.catalog_item:
                item_title = item_copy.catalog_item.title
                item_author = item_copy.catalog_item.author

        if result.hold_patron_id:
            hold_patron_result = await db.execute(
                select(User).where(User.id == result.hold_patron_id)
            )
            hold_patron = hold_patron_result.scalar_one_or_none()
            if hold_patron:
                hold_patron_name = f"{hold_patron.first_name} {hold_patron.last_name}"

        return CheckInResultResponse(
            id=result.id,
            barcode=result.barcode,
            status=result.status,
            item_copy_id=result.item_copy_id,
            checkout_id=result.checkout_id,
            item_title=item_title,
            item_author=item_author,
            sort_destination=result.sort_destination,
            sort_bin=result.sort_bin,
            hold_id=result.hold_id,
            hold_patron_name=hold_patron_name,
            destination_branch_id=result.destination_branch_id,
            destination_branch=result.destination_branch,
            checked_in_at=result.checked_in_at,
            effective_checkin_time=result.effective_checkin_time,
            was_overdue=result.was_overdue,
            overdue_days=result.overdue_days,
            fine_amount=result.fine_amount or Decimal(0),
            fine_waived_by_backdate=result.fine_waived_by_backdate,
            condition_checked=result.condition_checked,
            condition_status=result.condition_status,
            exception_type=result.exception_type,
            exception_message=result.exception_message
        )

    except Exception as e:
        logger.error(f"Check-in failed for {data.barcode}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Check-in failed"
        ) from e


@router.post("/sessions/{session_id}/batch", response_model=BatchCheckInResponse)
async def checkin_batch(
    session_id: int,
    data: BatchCheckInRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Check in multiple items in batch.

    Optimized for high-volume processing. Returns all results including
    items requiring special handling (holds, transits, exceptions).
    """
    book_drop_service = BookDropService(db)
    batch_service = BatchCheckInService(db)

    # Get session
    session = await book_drop_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status != CheckInSessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active"
        )

    try:
        result = await batch_service.process_batch(
            session=session,
            items=data.items,
            staff=staff_user,
            skip_condition_check=data.skip_condition_check,
            override_backdate=data.override_backdate
        )

        # Build response
        all_results = []
        for r in result.results:
            all_results.append(CheckInResultResponse(
                id=r.id,
                barcode=r.barcode,
                status=r.status,
                item_copy_id=r.item_copy_id,
                checkout_id=r.checkout_id,
                sort_destination=r.sort_destination,
                sort_bin=r.sort_bin,
                hold_id=r.hold_id,
                destination_branch_id=r.destination_branch_id,
                destination_branch=r.destination_branch,
                checked_in_at=r.checked_in_at,
                effective_checkin_time=r.effective_checkin_time,
                was_overdue=r.was_overdue,
                overdue_days=r.overdue_days,
                fine_amount=r.fine_amount or Decimal(0),
                fine_waived_by_backdate=r.fine_waived_by_backdate,
                condition_checked=r.condition_checked,
                condition_status=r.condition_status,
                exception_type=r.exception_type,
                exception_message=r.exception_message
            ))

        # Categorize results for UI
        items_with_holds = [r for r in all_results if r.hold_id]
        items_for_transit = [r for r in all_results if r.destination_branch]
        items_with_exceptions = [r for r in all_results if r.exception_type]

        return BatchCheckInResponse(
            session_id=session_id,
            processed_count=result.processed_count,
            successful_count=result.successful_count,
            holds_trapped=result.holds_trapped,
            transits_created=result.transits_created,
            exceptions_count=result.exceptions_count,
            results=all_results,
            items_with_holds=items_with_holds,
            items_for_transit=items_for_transit,
            items_with_exceptions=items_with_exceptions
        )

    except Exception as e:
        logger.error(f"Batch check-in failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Batch check-in failed"
        ) from e


@router.post("/process-book-drop", response_model=BookDropCheckInResponse)
async def process_book_drop(
    data: BookDropCheckInRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Process items from a specific book drop.

    Automatically applies the book drop's backdating configuration.
    Use this when processing all items from a physical book drop.
    """
    book_drop_service = BookDropService(db)
    batch_service = BatchCheckInService(db)

    # Get book drop
    book_drop = await book_drop_service.get_book_drop(data.book_drop_id)
    if not book_drop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Book drop not found"
        )

    try:
        result = await batch_service.process_book_drop(
            book_drop=book_drop,
            items=data.items,
            staff=staff_user,
            apply_backdating=data.apply_backdating,
            calculate_backdate_from=data.calculate_backdate_from
        )

        # Build response
        all_results = []
        fines_waived_count = 0
        fines_waived_amount = Decimal(0)

        for r in result.results:
            if r.fine_waived_by_backdate:
                fines_waived_count += 1
                fines_waived_amount += r.fine_amount or Decimal(0)

            all_results.append(CheckInResultResponse(
                id=r.id,
                barcode=r.barcode,
                status=r.status,
                item_copy_id=r.item_copy_id,
                checkout_id=r.checkout_id,
                sort_destination=r.sort_destination,
                sort_bin=r.sort_bin,
                hold_id=r.hold_id,
                destination_branch_id=r.destination_branch_id,
                destination_branch=r.destination_branch,
                checked_in_at=r.checked_in_at,
                effective_checkin_time=r.effective_checkin_time,
                was_overdue=r.was_overdue,
                overdue_days=r.overdue_days,
                fine_amount=r.fine_amount or Decimal(0),
                fine_waived_by_backdate=r.fine_waived_by_backdate,
                condition_checked=r.condition_checked,
                condition_status=r.condition_status,
                exception_type=r.exception_type,
                exception_message=r.exception_message
            ))

        # Get session info
        session = await book_drop_service.get_session(result.session_id)

        return BookDropCheckInResponse(
            book_drop_id=book_drop.id,
            book_drop_name=book_drop.name,
            session_id=result.session_id,
            backdated_to=session.backdate_to if session else None,
            fines_waived_count=fines_waived_count,
            fines_waived_amount=fines_waived_amount,
            processed_count=result.processed_count,
            successful_count=result.successful_count,
            holds_trapped=result.holds_trapped,
            transits_created=result.transits_created,
            exceptions_count=result.exceptions_count,
            results=all_results
        )

    except Exception as e:
        logger.error(f"Book drop processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Book drop processing failed"
        ) from e


# =============================================================================
# Session Results
# =============================================================================

@router.get("/sessions/{session_id}/results", response_model=list[CheckInResultResponse])
async def get_session_results(
    session_id: int,
    status_filter: Optional[CheckInResultStatus] = Query(None, alias="status"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get check-in results for a session."""
    service = BookDropService(db)
    results = await service.get_session_results(
        session_id=session_id,
        status_filter=status_filter,
        limit=limit,
        offset=offset
    )

    # Build response
    response = []
    for r in results:
        response.append(CheckInResultResponse(
            id=r.id,
            barcode=r.barcode,
            status=r.status,
            item_copy_id=r.item_copy_id,
            checkout_id=r.checkout_id,
            sort_destination=r.sort_destination,
            sort_bin=r.sort_bin,
            hold_id=r.hold_id,
            destination_branch_id=r.destination_branch_id,
            destination_branch=r.destination_branch,
            checked_in_at=r.checked_in_at,
            effective_checkin_time=r.effective_checkin_time,
            was_overdue=r.was_overdue,
            overdue_days=r.overdue_days,
            fine_amount=r.fine_amount or Decimal(0),
            fine_waived_by_backdate=r.fine_waived_by_backdate,
            condition_checked=r.condition_checked,
            condition_status=r.condition_status,
            exception_type=r.exception_type,
            exception_message=r.exception_message
        ))

    return response


# =============================================================================
# Exceptions
# =============================================================================

@router.get("/exceptions", response_model=list[CheckInExceptionResponse])
async def list_exceptions(
    branch_location: Optional[str] = Query(None),
    exception_type: Optional[ExceptionType] = Query(None),
    resolved: bool = Query(False, description="Include resolved exceptions"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List check-in exceptions requiring attention."""
    batch_service = BatchCheckInService(db)
    exceptions, total = await batch_service.get_pending_exceptions(
        branch_location=branch_location,
        exception_type=exception_type,
        limit=limit,
        offset=offset
    )
    return exceptions


@router.post("/exceptions/{exception_id}/resolve", response_model=CheckInExceptionResponse)
async def resolve_exception(
    exception_id: int,
    data: ResolveExceptionRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Resolve a check-in exception."""
    batch_service = BatchCheckInService(db)

    try:
        exception = await batch_service.resolve_exception(
            exception_id=exception_id,
            staff=staff_user,
            action_taken=data.action_taken
        )
        return exception

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        ) from e
    except Exception as e:
        logger.error(f"Failed to resolve exception: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve exception"
        ) from e


# =============================================================================
# Statistics
# =============================================================================

@router.get("/statistics", response_model=list[CheckInStatisticResponse])
async def get_statistics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    branch_location: Optional[str] = Query(None),
    book_drop_id: Optional[int] = Query(None),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get check-in statistics for a date range."""
    service = BookDropService(db)
    stats = await service.get_statistics(
        start_date=start_date,
        end_date=end_date,
        branch_location=branch_location,
        book_drop_id=book_drop_id
    )
    return stats


@router.get("/statistics/summary", response_model=StatisticsSummary)
async def get_statistics_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    branch_location: Optional[str] = Query(None),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get summary statistics for a date range."""
    service = BookDropService(db)
    summary = await service.get_statistics_summary(
        start_date=start_date,
        end_date=end_date,
        branch_location=branch_location
    )

    return StatisticsSummary(
        period_start=summary["period_start"],
        period_end=summary["period_end"],
        branch_location=summary.get("branch_location"),
        total_checkins=summary["total_checkins"],
        avg_daily_checkins=summary.get("avg_daily_checkins", 0),
        peak_hour=summary.get("peak_hour", 0),
        peak_day_of_week=summary.get("peak_day_of_week", 0),
        holds_trapped_total=summary.get("holds_trapped_total", 0),
        transits_total=summary.get("transits_total", 0),
        exceptions_total=summary.get("exceptions_total", 0),
        total_fines=Decimal(str(summary.get("total_fines", 0))),
        total_fines_waived=Decimal(str(summary.get("total_fines_waived", 0))),
        staff_checkins_pct=summary.get("staff_checkins_pct", 0),
        book_drop_checkins_pct=summary.get("book_drop_checkins_pct", 0),
        self_service_checkins_pct=summary.get("self_service_checkins_pct", 0)
    )


# =============================================================================
# SIP2 Devices
# =============================================================================

@router.post("/sip2-devices", response_model=SIP2DeviceResponse, status_code=status.HTTP_201_CREATED)
async def create_sip2_device(
    data: SIP2DeviceCreate,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new SIP2 device configuration.

    Requires admin role. SIP2 devices are used for integration with
    automated materials handling (AMH) systems.
    """
    # Check for duplicate device_id
    existing = await db.execute(
        select(SIP2Device).where(SIP2Device.device_id == data.device_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Device with ID '{data.device_id}' already exists"
        )

    device = SIP2Device(**data.model_dump())
    db.add(device)
    await db.commit()
    await db.refresh(device)

    logger.info(f"SIP2 device created: {device.device_id} by user {staff_user.id}")
    return device


@router.get("/sip2-devices", response_model=list[SIP2DeviceResponse])
async def list_sip2_devices(
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """List all SIP2 devices."""
    sip2_service = SIP2Service(db)
    devices = await sip2_service.get_all_devices()
    return devices


@router.get("/sip2-devices/{device_id}", response_model=SIP2DeviceResponse)
async def get_sip2_device(
    device_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get SIP2 device details."""
    sip2_service = SIP2Service(db)
    device = await sip2_service.get_device(device_id)

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    return device


@router.patch("/sip2-devices/{device_id}", response_model=SIP2DeviceResponse)
async def update_sip2_device(
    device_id: int,
    data: SIP2DeviceUpdate,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update SIP2 device configuration."""
    sip2_service = SIP2Service(db)
    device = await sip2_service.get_device(device_id)

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(device, key, value)

    await db.commit()
    await db.refresh(device)

    logger.info(f"SIP2 device {device_id} updated by user {staff_user.id}")
    return device


@router.post("/sip2-devices/{device_id}/test")
async def test_sip2_device(
    device_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Test connection to a SIP2 device.

    Sends a status check message and returns the result.
    """
    sip2_service = SIP2Service(db)
    device = await sip2_service.get_device(device_id)

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )

    try:
        online = await sip2_service.check_device_status(device)
        await db.commit()

        return {
            "device_id": device.device_id,
            "online": online,
            "status": str(device.status),
            "last_communication": device.last_communication,
            "error_message": device.error_message
        }

    except Exception as e:
        logger.error(f"SIP2 device test failed: {e}", exc_info=True)
        return {
            "device_id": device.device_id,
            "online": False,
            "error": str(e)
        }


# =============================================================================
# Fast Processing Endpoints
# =============================================================================

@router.post("/sessions/{session_id}/fast-scan", response_model=FastProcessingResponse)
async def fast_processing_scan(
    session_id: int,
    data: FastProcessingScanRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Fast continuous scanning endpoint for book drop processing.

    This endpoint:
    - Processes items continuously without stopping
    - Auto-detects holds (yellow cue)
    - Auto-detects transit items (blue cue)
    - Returns visual/audio sorting cues
    - Only prompts for damage check if needed
    - Provides running count by destination
    """
    service = BookDropService(db)

    # Get session
    session = await service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    if session.status != CheckInSessionStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session is not active"
        )

    try:
        # Process check-in
        result = await service.process_checkin(
            session=session,
            barcode=data.barcode,
            staff=staff_user,
            condition_status=data.damage_status if data.check_damage else None
        )
        await db.commit()

        # Get item details
        hold_patron_name = None
        if result.item_copy_id:
            item_result = await db.execute(
                select(ItemCopy)
                .options(selectinload(ItemCopy.catalog_item))
                .where(ItemCopy.id == result.item_copy_id)
            )
            item_copy = item_result.scalar_one_or_none()
            if item_copy and item_copy.catalog_item:
                pass  # item details loaded into session

        if result.hold_patron_id:
            hold_patron_result = await db.execute(
                select(User).where(User.id == result.hold_patron_id)
            )
            hold_patron = hold_patron_result.scalar_one_or_none()
            if hold_patron:
                hold_patron_name = f"{hold_patron.first_name} {hold_patron.last_name}"

        # Get patron holds count for interrupt modal (if this was a checkout return)
        patron_id = None
        patron_name = None
        patron_holds_count = 0
        if result.checkout and result.checkout.user:
            patron = result.checkout.user
            patron_id = patron.id
            patron_name = f"{patron.first_name} {patron.last_name}"
            patron_holds_count = await service.count_patron_ready_holds(patron.id)

        # Determine sort color and sound based on destination
        sort_color = "green"  # Default: shelve
        sort_sound = "shelve"

        if result.sort_destination == SortDestination.HOLD_SHELF:
            sort_color = "yellow"
            sort_sound = "holds"
        elif result.sort_destination == SortDestination.TRANSIT:
            sort_color = "blue"
            sort_sound = "transit"
        elif result.sort_destination in [SortDestination.EXCEPTION, SortDestination.CONDITION_CHECK]:
            sort_color = "red"
            sort_sound = "exception"

        # Get destination summary
        summary_data = await service.get_destination_summary(session_id)
        summary = DestinationSummary(**summary_data)

        # Check if damage check is required
        exceptions = await service._check_for_exceptions(
            result.checkout,
            result.item_copy
        ) if result.checkout and result.item_copy else []
        requires_damage_check = service.should_prompt_damage_check(result, exceptions)

        return FastProcessingResponse(
            check_in_result_id=result.id,
            barcode=result.barcode,
            status=result.status,
            sort_destination=result.sort_destination,
            sort_color=sort_color,
            sort_sound=sort_sound,
            hold_patron_name=hold_patron_name,
            destination_branch_id=result.destination_branch_id,
            destination_branch=result.destination_branch,
            requires_damage_check=requires_damage_check and not data.check_damage,
            exception_message=result.exception_message,
            destination_summary=summary,
            patron_id=patron_id,
            patron_name=patron_name,
            patron_holds_count=patron_holds_count
        )

    except Exception as e:
        logger.error(f"Fast scan failed for {data.barcode}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fast scan processing failed"
        ) from e


@router.get("/sessions/{session_id}/destination-summary", response_model=DestinationSummary)
async def get_destination_summary(
    session_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get running count by destination for a check-in session.

    Returns the count of items destined for: shelve, holds, transit, exceptions
    """
    service = BookDropService(db)
    session = await service.get_session(session_id)

    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found"
        )

    try:
        summary_data = await service.get_destination_summary(session_id)
        return DestinationSummary(**summary_data)

    except Exception as e:
        logger.error(f"Failed to get destination summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get destination summary"
        ) from e


@router.post("/check-in-results/{result_id}/resolve-claims-returned")
async def resolve_claims_returned(
    result_id: int,
    data: ClaimsReturnedResolution,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Resolve claims returned exception inline during fast processing.

    Marks the exception as resolved with notes.
    """
    service = BookDropService(db)

    try:
        # Get the check-in result
        result = await get_or_404(db, CheckInResult, result_id, "Check-in result not found")

        # Mark as resolved
        await service.mark_claims_returned_resolved(
            result, data.resolution_notes, staff_user
        )
        await db.commit()

        logger.info(f"Claims returned resolved for result {result_id}")

        return {"status": "resolved", "result_id": result_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to resolve claims returned: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resolve claims returned"
        ) from e


@router.get("/check-in-results/{result_id}/damage-check-required", response_model=DamageCheckRequirement)
async def get_damage_check_requirement(
    result_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if damage check is required for a check-in result.

    Only returns True if item is flagged as damaged or returned after loss.
    """
    try:
        result_query = await db.execute(
            select(CheckInResult)
            .options(selectinload(CheckInResult.item_copy))
            .where(CheckInResult.id == result_id)
        )
        result = result_query.scalar_one_or_none()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Check-in result not found"
            )

        # Determine if damage check is needed
        item_title = None
        requires_check = False
        reason = None

        if result.item_copy and result.item_copy.catalog_item:
            item_title = result.item_copy.catalog_item.title

        # Check exceptions
        if result.exception_type:
            if result.exception_type in [ExceptionType.DAMAGED_ITEM, ExceptionType.LOST_ITEM_RETURNED]:
                requires_check = True
                reason = f"Item has {str(result.exception_type)} exception"

        return DamageCheckRequirement(
            check_in_result_id=result_id,
            barcode=result.barcode,
            requires_check=requires_check,
            reason=reason,
            item_title=item_title
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to check damage requirement: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to check damage requirement"
        ) from e



