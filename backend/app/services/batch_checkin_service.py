# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.branch_resolver import label_to_branch_id, branch_id_to_label
from sqlalchemy.orm import selectinload

from ..core.cache import get_redis, _acquire_lock, _release_lock
from ..models.book_drop import (
    BookDrop, CheckInSession, CheckInSessionStatus,
    CheckInResult, CheckInResultStatus, CheckInException,
    ExceptionType, SortDestination, SIP2Device
)
from ..models.user import User
from ..schemas.book_drop import (
    BatchCheckInItem, BatchCheckInResponse, CheckInResultResponse
)
from .book_drop_service import BookDropService
from .sip2_service import SIP2Service

_CHECKIN_LOCK_TIMEOUT = 10  # seconds

logger = get_logger(__name__)


@dataclass
class BatchProcessingResult:
    session_id: int
    processed_count: int = 0
    successful_count: int = 0
    holds_trapped: int = 0
    transits_created: int = 0
    exceptions_count: int = 0

    results: list[CheckInResult] = field(default_factory=list)
    items_with_holds: list[CheckInResult] = field(default_factory=list)
    items_for_transit: list[CheckInResult] = field(default_factory=list)
    items_with_exceptions: list[CheckInResult] = field(default_factory=list)

    processing_time_ms: int = 0
    errors: list[str] = field(default_factory=list)


class BatchCheckInService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.book_drop_service = BookDropService(db)
        self.sip2_service = SIP2Service(db)

    async def process_batch(
        self,
        session: CheckInSession,
        items: list[BatchCheckInItem],
        staff: User,
        skip_condition_check: bool = False,
        override_backdate: Optional[datetime] = None
    ) -> BatchProcessingResult:
        start_time = datetime.now(timezone.utc)

        result = BatchProcessingResult(session_id=session.id)

        # Acquire Redis for distributed locking
        redis_client = await get_redis()

        # Process items one at a time using savepoints so a single
        # item failure does not corrupt the entire batch.
        for item in items:
            lock_token = None
            lock_key = f"checkin:barcode:{item.barcode}"
            try:
                # Acquire distributed lock on barcode to prevent
                # concurrent batch sessions from double-processing
                if redis_client is not None:
                    lock_token = await _acquire_lock(redis_client, lock_key, _CHECKIN_LOCK_TIMEOUT)
                    if lock_token is None:
                        result.errors.append(f"{item.barcode}: already being processed")
                        continue

                # Create a savepoint before each item so we can roll back
                # only this item's changes if it fails.
                async with self.db.begin_nested():
                    checkin_result = await self.book_drop_service.process_checkin(
                        session=session,
                        barcode=item.barcode,
                        staff=staff,
                        condition_status=item.condition_status if not skip_condition_check else None,
                        condition_notes=item.condition_notes if not skip_condition_check else None,
                        override_backdate=override_backdate
                    )

                result.processed_count += 1
                result.results.append(checkin_result)

                # Categorize results
                if checkin_result.status == CheckInResultStatus.SUCCESS:
                    result.successful_count += 1
                elif checkin_result.status == CheckInResultStatus.HOLD_TRAPPED:
                    result.successful_count += 1
                    result.holds_trapped += 1
                    result.items_with_holds.append(checkin_result)
                elif checkin_result.status == CheckInResultStatus.TRANSIT_REQUIRED:
                    result.successful_count += 1
                    result.transits_created += 1
                    result.items_for_transit.append(checkin_result)
                elif checkin_result.status in [
                    CheckInResultStatus.EXCEPTION,
                    CheckInResultStatus.CONDITION_ISSUE
                ]:
                    result.exceptions_count += 1
                    result.items_with_exceptions.append(checkin_result)

            except Exception as e:  # noqa: BLE001 -- per-iteration boundary: one item failure must not crash batch checkin
                # Savepoint is automatically rolled back on exception,
                # so only this item's changes are reverted.
                logger.error(f"Error processing item {item.barcode}: {e}")
                result.errors.append(f"{item.barcode}: {str(e)}")
            finally:
                # Release barcode lock
                if redis_client is not None and lock_token is not None:
                    try:
                        await _release_lock(redis_client, lock_key, lock_token)
                    except Exception:  # noqa: BLE001 -- lock release best-effort: TTL expiry recovers
                        logger.warning("Failed to release checkin lock for barcode=%s", item.barcode)

        # Commit all successful items
        await self.db.commit()

        # Calculate processing time
        end_time = datetime.now(timezone.utc)
        result.processing_time_ms = int(
            (end_time - start_time).total_seconds() * 1000
        )

        logger.info(
            f"Batch check-in completed: session={session.session_code}, "
            f"processed={result.processed_count}, "
            f"successful={result.successful_count}, "
            f"time_ms={result.processing_time_ms}"
        )

        return result

    async def process_book_drop(
        self,
        book_drop: BookDrop,
        items: list[BatchCheckInItem],
        staff: User,
        apply_backdating: bool = True,
        calculate_backdate_from: Optional[datetime] = None
    ) -> BatchProcessingResult:
        # Start session with book drop
        session = await self.book_drop_service.start_session(
            staff=staff,
            branch_location=book_drop.branch_location,
            branch_id=book_drop.branch_id,
            book_drop_id=book_drop.id
        )

        # Calculate backdating
        override_backdate = None
        if apply_backdating:
            override_backdate = self.book_drop_service.calculate_backdate(
                book_drop,
                calculate_backdate_from
            )

        # Process batch
        result = await self.process_batch(
            session=session,
            items=items,
            staff=staff,
            override_backdate=override_backdate
        )

        # End session
        await self.book_drop_service.end_session(session.id)

        return result

    async def process_with_sorting(
        self,
        session: CheckInSession,
        items: list[BatchCheckInItem],
        staff: User,
        sip2_device: SIP2Device
    ) -> BatchProcessingResult:
        result = await self.process_batch(session, items, staff)

        # Send sort instructions for each result
        for checkin_result in result.results:
            if checkin_result.sort_destination:
                # Determine sort bin
                sort_instruction = self.sip2_service.determine_sort_destination(
                    device=sip2_device,
                    checkin_status=checkin_result.status,
                    has_hold=checkin_result.hold_id is not None,
                    needs_transit=checkin_result.destination_branch is not None,
                    has_exception=checkin_result.exception_type is not None
                )

                # Send to sorting system
                success = await self.sip2_service.send_sort_instruction(
                    device=sip2_device,
                    barcode=checkin_result.barcode,
                    sort_bin=sort_instruction.bin_id
                )

                if success:
                    checkin_result.sort_bin = sort_instruction.bin_id
                else:
                    logger.warning(
                        f"Failed to send sort instruction for {checkin_result.barcode}"
                    )

        return result

    async def get_pending_exceptions(
        self,
        branch_location: Optional[str] = None,
        exception_type: Optional[ExceptionType] = None,
        limit: int = 50,
        offset: int = 0,
        branch_id: Optional[int] = None,
    ) -> tuple[list[CheckInException], int]:
        query = (
            select(CheckInException)
            .join(CheckInResult)
            .join(CheckInSession)
            .where(CheckInException.resolved == False)
        )

        if branch_id is None and branch_location:
            branch_id = label_to_branch_id(branch_location)

        if branch_id is not None:
            query = query.where(CheckInSession.branch_id == branch_id)
        elif branch_location:
            query = query.where(CheckInSession.branch_location == branch_location)
        if exception_type:
            query = query.where(CheckInException.exception_type == exception_type)

        # Count query
        count_query = (
            select(func.count(CheckInException.id))
            .join(CheckInResult)
            .join(CheckInSession)
            .where(CheckInException.resolved == False)
        )
        if branch_id is not None:
            count_query = count_query.where(CheckInSession.branch_id == branch_id)
        elif branch_location:
            count_query = count_query.where(
                CheckInSession.branch_location == branch_location
            )
        if exception_type:
            count_query = count_query.where(
                CheckInException.exception_type == exception_type
            )

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Get items
        query = query.order_by(CheckInException.created_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        exceptions = list(result.scalars().all())

        return exceptions, total

    async def resolve_exception(
        self,
        exception_id: int,
        staff: User,
        action_taken: str
    ) -> CheckInException:
        result = await self.db.execute(
            select(CheckInException)
            .where(CheckInException.id == exception_id)
        )
        exception = result.scalar_one_or_none()

        if not exception:
            raise ValueError(f"Exception {exception_id} not found")

        exception.resolved = True
        exception.resolved_by_id = staff.id
        exception.resolved_at = datetime.now(timezone.utc)
        exception.action_taken = action_taken

        # Also update the check-in result
        if exception.check_in_result_id:
            await self.db.execute(
                select(CheckInResult)
                .where(CheckInResult.id == exception.check_in_result_id)
            )
            checkin_result = (await self.db.execute(
                select(CheckInResult)
                .where(CheckInResult.id == exception.check_in_result_id)
            )).scalar_one_or_none()

            if checkin_result:
                checkin_result.exception_resolved = True
                checkin_result.resolved_by_id = staff.id
                checkin_result.resolved_at = datetime.now(timezone.utc)
                checkin_result.resolution_notes = action_taken

        await self.db.commit()

        logger.info(
            f"Exception {exception_id} resolved by staff {staff.id}: {action_taken}"
        )

        return exception

    async def get_session_summary(
        self,
        session_id: int
    ) -> dict:
        session = await self.book_drop_service.get_session(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        # Get all results
        results = await self.book_drop_service.get_session_results(
            session_id, limit=10000
        )

        # Calculate statistics
        total_fines = Decimal(0)
        fines_waived = Decimal(0)
        overdue_count = 0

        status_breakdown = {}
        sort_breakdown = {}
        exception_breakdown = {}

        for r in results:
            # Status breakdown
            status = str(r.status) if r.status else "unknown"
            status_breakdown[status] = status_breakdown.get(status, 0) + 1

            # Sort destination breakdown
            if r.sort_destination:
                dest = str(r.sort_destination)
                sort_breakdown[dest] = sort_breakdown.get(dest, 0) + 1

            # Exception breakdown
            if r.exception_type:
                exc_type = str(r.exception_type)
                exception_breakdown[exc_type] = exception_breakdown.get(exc_type, 0) + 1

            # Fine totals
            if r.fine_amount:
                total_fines += r.fine_amount
            if r.fine_waived_by_backdate and r.fine_amount:
                fines_waived += r.fine_amount

            if r.was_overdue:
                overdue_count += 1

        # Calculate processing rate
        if session.ended_at and session.started_at:
            duration = (session.ended_at - session.started_at).total_seconds()
            items_per_minute = (
                session.total_items / (duration / 60) if duration > 0 else 0
            )
        else:
            items_per_minute = 0

        return {
            "session_id": session.id,
            "session_code": session.session_code,
            "branch_location": session.branch_location,
            "book_drop_id": session.book_drop_id,
            "staff_id": session.staff_id,
            "status": str(session.status),
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "use_backdating": session.use_backdating,
            "backdate_to": session.backdate_to.isoformat() if session.backdate_to else None,

            # Counts
            "total_items": session.total_items,
            "successful_checkins": session.successful_checkins,
            "holds_trapped": session.holds_trapped,
            "transits_created": session.transits_created,
            "exceptions_count": session.exceptions_count,

            # Calculated stats
            "success_rate": (
                session.successful_checkins / session.total_items * 100
                if session.total_items > 0 else 0
            ),
            "items_per_minute": round(items_per_minute, 2),
            "overdue_count": overdue_count,
            "total_fines": str(total_fines),
            "fines_waived": str(fines_waived),

            # Breakdowns
            "status_breakdown": status_breakdown,
            "sort_breakdown": sort_breakdown,
            "exception_breakdown": exception_breakdown
        }

    async def list_active_sessions(
        self,
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> list[CheckInSession]:
        if branch_id is None and branch_location:
            branch_id = label_to_branch_id(branch_location)

        query = (
            select(CheckInSession)
            .options(selectinload(CheckInSession.staff))
            .where(CheckInSession.status == CheckInSessionStatus.ACTIVE)
        )

        if branch_id is not None:
            query = query.where(CheckInSession.branch_id == branch_id)
        elif branch_location:
            query = query.where(CheckInSession.branch_location == branch_location)

        query = query.order_by(CheckInSession.started_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_recent_sessions(
        self,
        branch_location: Optional[str] = None,
        limit: int = 20,
        branch_id: Optional[int] = None,
    ) -> list[CheckInSession]:
        query = (
            select(CheckInSession)
            .options(
                selectinload(CheckInSession.staff),
                selectinload(CheckInSession.book_drop)
            )
        )

        if branch_id is None and branch_location:
            branch_id = label_to_branch_id(branch_location)
        if branch_id is not None:
            query = query.where(CheckInSession.branch_id == branch_id)
        elif branch_location:
            query = query.where(CheckInSession.branch_location == branch_location)

        query = query.order_by(CheckInSession.started_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
