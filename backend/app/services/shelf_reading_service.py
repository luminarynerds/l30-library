# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import CatalogItem
from app.models.inventory import ItemCopy
from app.models.multi_branch import Branch
from app.models.shelf_reading import (
    ScanResult,
    ShelfReadingSchedule,
    ShelfReadingScan,
    ShelfReadingSession,
    ShelfReadingStatus,
)
from app.models.user import User
from app.services.call_number_service import CallNumberService


# Points awarded per scan result
POINTS_IN_ORDER = 1
POINTS_OUT_OF_ORDER = 2  # More points for finding problems
POINTS_WRONG_SHELF = 3
POINTS_SESSION_COMPLETE_BONUS = 10
POINTS_PERFECT_ACCURACY_BONUS = 25


class ShelfReadingService:

    @staticmethod
    async def create_session(
        db: AsyncSession,
        name: str,
        branch_id: int,
        location: str,
        created_by_id: int,
        description: Optional[str] = None,
        call_number_start: Optional[str] = None,
        call_number_end: Optional[str] = None,
    ) -> ShelfReadingSession:
        session = ShelfReadingSession(
            name=name,
            description=description,
            branch_id=branch_id,
            location=location,
            call_number_start=call_number_start,
            call_number_end=call_number_end,
            created_by_id=created_by_id,
            status=ShelfReadingStatus.IN_PROGRESS,
        )
        db.add(session)
        await db.flush()
        return session

    @staticmethod
    async def get_session(
        db: AsyncSession, session_id: int
    ) -> Optional[ShelfReadingSession]:
        result = await db.execute(
            select(ShelfReadingSession)
            .where(ShelfReadingSession.id == session_id)
            .options(
                selectinload(ShelfReadingSession.created_by),
                selectinload(ShelfReadingSession.branch),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def scan_item(
        db: AsyncSession,
        session: ShelfReadingSession,
        item_copy: ItemCopy,
        scanned_by_id: int,
    ) -> ShelfReadingScan:
        # Get the item's call number from catalog
        catalog_result = await db.execute(
            select(CatalogItem).where(CatalogItem.id == item_copy.catalog_item_id)
        )
        catalog_item = catalog_result.scalar_one_or_none()
        current_call_number = catalog_item.call_number if catalog_item else None

        # Get the previous scan in this session
        prev_scan_result = await db.execute(
            select(ShelfReadingScan)
            .where(ShelfReadingScan.session_id == session.id)
            .order_by(ShelfReadingScan.scan_order.desc())
            .limit(1)
        )
        prev_scan = prev_scan_result.scalar_one_or_none()

        scan_order = (prev_scan.scan_order + 1) if prev_scan else 1
        prev_call_number = prev_scan.scanned_call_number if prev_scan else None

        # Determine scan result
        result = ScanResult.IN_ORDER
        expected_location = None
        correct_position_after = None

        # Check if item is on the wrong shelf entirely
        if item_copy.location and session.location:
            if item_copy.location.lower() != session.location.lower():
                result = ScanResult.WRONG_SHELF
                expected_location = item_copy.location

        # Check call number order (only if not wrong shelf and we have previous)
        if result != ScanResult.WRONG_SHELF and prev_call_number and current_call_number:
            comparison = CallNumberService.compare_call_numbers(
                prev_call_number, current_call_number
            )
            if comparison > 0:
                # Previous call number is greater - this item is out of order
                result = ScanResult.OUT_OF_ORDER
                correct_position_after = _find_correct_position(
                    db, session.id, current_call_number
                )

        # Calculate points
        points = POINTS_IN_ORDER
        if result == ScanResult.OUT_OF_ORDER:
            points = POINTS_OUT_OF_ORDER
        elif result == ScanResult.WRONG_SHELF:
            points = POINTS_WRONG_SHELF

        scan = ShelfReadingScan(
            session_id=session.id,
            item_copy_id=item_copy.id,
            scan_order=scan_order,
            scanned_call_number=current_call_number,
            previous_call_number=prev_call_number,
            result=result,
            expected_location=expected_location,
            correct_position_after=correct_position_after,
            scanned_by_id=scanned_by_id,
        )
        db.add(scan)

        # Update session stats
        session.total_items_scanned += 1
        if result == ScanResult.IN_ORDER:
            session.items_in_order += 1
        elif result == ScanResult.OUT_OF_ORDER:
            session.items_out_of_order += 1
        elif result == ScanResult.WRONG_SHELF:
            session.items_wrong_shelf += 1

        session.points_earned += points

        # Recalculate accuracy
        if session.total_items_scanned > 0:
            session.accuracy_percentage = round(
                (session.items_in_order / session.total_items_scanned) * 100, 2
            )

        session.updated_at = datetime.now(timezone.utc)

        await db.flush()
        return scan

    @staticmethod
    async def complete_session(
        db: AsyncSession, session: ShelfReadingSession
    ) -> ShelfReadingSession:
        session.status = ShelfReadingStatus.COMPLETED
        session.completed_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)

        # Award completion bonus
        session.points_earned += POINTS_SESSION_COMPLETE_BONUS

        # Perfect accuracy bonus
        if session.total_items_scanned > 0 and session.accuracy_percentage == 100.0:
            session.points_earned += POINTS_PERFECT_ACCURACY_BONUS

        await db.flush()
        return session

    @staticmethod
    async def pause_session(
        db: AsyncSession, session: ShelfReadingSession
    ) -> ShelfReadingSession:
        session.status = ShelfReadingStatus.PAUSED
        session.paused_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return session

    @staticmethod
    async def resume_session(
        db: AsyncSession, session: ShelfReadingSession
    ) -> ShelfReadingSession:
        session.status = ShelfReadingStatus.IN_PROGRESS
        session.paused_at = None
        session.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return session

    @staticmethod
    async def cancel_session(
        db: AsyncSession, session: ShelfReadingSession
    ) -> ShelfReadingSession:
        session.status = ShelfReadingStatus.CANCELLED
        session.completed_at = datetime.now(timezone.utc)
        session.updated_at = datetime.now(timezone.utc)
        await db.flush()
        return session

    @staticmethod
    async def get_session_scans(
        db: AsyncSession, session_id: int
    ) -> list[ShelfReadingScan]:
        result = await db.execute(
            select(ShelfReadingScan)
            .where(ShelfReadingScan.session_id == session_id)
            .options(
                selectinload(ShelfReadingScan.item_copy).selectinload(ItemCopy.catalog_item),
                selectinload(ShelfReadingScan.scanned_by),
            )
            .order_by(ShelfReadingScan.scan_order)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_accuracy_report(
        db: AsyncSession,
        branch_id: int,
        period_start: datetime,
        period_end: datetime,
    ) -> dict:
        result = await db.execute(
            select(
                func.count(ShelfReadingSession.id).label("total_sessions"),
                func.coalesce(func.sum(ShelfReadingSession.total_items_scanned), 0).label("total_scanned"),
                func.coalesce(func.sum(ShelfReadingSession.items_in_order), 0).label("in_order"),
                func.coalesce(func.sum(ShelfReadingSession.items_out_of_order), 0).label("out_of_order"),
                func.coalesce(func.sum(ShelfReadingSession.items_wrong_shelf), 0).label("wrong_shelf"),
            )
            .where(
                ShelfReadingSession.branch_id == branch_id,
                ShelfReadingSession.status == ShelfReadingStatus.COMPLETED,
                ShelfReadingSession.completed_at >= period_start,
                ShelfReadingSession.completed_at <= period_end,
            )
        )
        row = result.one()

        # Get branch name
        branch_result = await db.execute(
            select(Branch).where(Branch.id == branch_id)
        )
        branch = branch_result.scalar_one_or_none()
        branch_name = branch.name if branch else "Unknown"

        total_scanned = row.total_scanned or 0
        in_order = row.in_order or 0
        accuracy = round((in_order / total_scanned * 100), 2) if total_scanned > 0 else 0.0

        return {
            "branch_id": branch_id,
            "branch_name": branch_name,
            "total_sessions": row.total_sessions or 0,
            "total_items_scanned": total_scanned,
            "items_in_order": in_order,
            "items_out_of_order": row.out_of_order or 0,
            "items_wrong_shelf": row.wrong_shelf or 0,
            "overall_accuracy": accuracy,
            "period_start": period_start,
            "period_end": period_end,
        }

    @staticmethod
    async def get_branch_summaries(db: AsyncSession) -> list[dict]:
        result = await db.execute(
            select(
                ShelfReadingSession.branch_id,
                func.count(ShelfReadingSession.id).label("sessions_completed"),
                func.avg(ShelfReadingSession.accuracy_percentage).label("avg_accuracy"),
                func.max(ShelfReadingSession.completed_at).label("last_session_at"),
                func.coalesce(func.sum(ShelfReadingSession.points_earned), 0).label("total_points"),
            )
            .where(ShelfReadingSession.status == ShelfReadingStatus.COMPLETED)
            .group_by(ShelfReadingSession.branch_id)
        )
        rows = result.all()

        summaries = []
        for row in rows:
            # Get branch name
            branch_result = await db.execute(
                select(Branch).where(Branch.id == row.branch_id)
            )
            branch = branch_result.scalar_one_or_none()

            summaries.append({
                "branch_id": row.branch_id,
                "branch_name": branch.name if branch else "Unknown",
                "sessions_completed": row.sessions_completed,
                "average_accuracy": round(float(row.avg_accuracy or 0), 2),
                "last_session_at": row.last_session_at,
                "total_points_earned": row.total_points or 0,
            })

        return summaries

    @staticmethod
    async def get_historical_accuracy(
        db: AsyncSession,
        branch_id: int,
        months: int = 12,
    ) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

        result = await db.execute(
            select(
                extract("year", ShelfReadingSession.completed_at).label("year"),
                extract("month", ShelfReadingSession.completed_at).label("month"),
                func.avg(ShelfReadingSession.accuracy_percentage).label("avg_accuracy"),
                func.count(ShelfReadingSession.id).label("sessions"),
                func.coalesce(func.sum(ShelfReadingSession.total_items_scanned), 0).label("items_scanned"),
            )
            .where(
                ShelfReadingSession.branch_id == branch_id,
                ShelfReadingSession.status == ShelfReadingStatus.COMPLETED,
                ShelfReadingSession.completed_at >= cutoff,
            )
            .group_by(
                extract("year", ShelfReadingSession.completed_at),
                extract("month", ShelfReadingSession.completed_at),
            )
            .order_by(
                extract("year", ShelfReadingSession.completed_at),
                extract("month", ShelfReadingSession.completed_at),
            )
        )
        rows = result.all()

        return [
            {
                "period": f"{int(row.year)}-{int(row.month):02d}",
                "accuracy": round(float(row.avg_accuracy or 0), 2),
                "sessions": row.sessions,
                "items_scanned": row.items_scanned or 0,
            }
            for row in rows
        ]

    @staticmethod
    async def get_leaderboard(
        db: AsyncSession,
        period: str = "all_time",
        limit: int = 10,
    ) -> list[dict]:
        query = select(
            ShelfReadingSession.created_by_id,
            func.coalesce(func.sum(ShelfReadingSession.points_earned), 0).label("total_points"),
            func.count(ShelfReadingSession.id).label("sessions_completed"),
            func.avg(ShelfReadingSession.accuracy_percentage).label("avg_accuracy"),
        ).where(ShelfReadingSession.status == ShelfReadingStatus.COMPLETED)

        # Apply time filter
        now = datetime.now(timezone.utc)
        if period == "weekly":
            query = query.where(
                ShelfReadingSession.completed_at >= now - timedelta(weeks=1)
            )
        elif period == "monthly":
            query = query.where(
                ShelfReadingSession.completed_at >= now - timedelta(days=30)
            )

        query = (
            query.group_by(ShelfReadingSession.created_by_id)
            .order_by(func.sum(ShelfReadingSession.points_earned).desc())
            .limit(limit)
        )

        result = await db.execute(query)
        rows = result.all()

        entries = []
        for rank, row in enumerate(rows, 1):
            # Get user name
            user_result = await db.execute(
                select(User).where(User.id == row.created_by_id)
            )
            user = user_result.scalar_one_or_none()

            entries.append({
                "user_id": row.created_by_id,
                "user_name": user.full_name if user else "Unknown",
                "total_points": row.total_points or 0,
                "sessions_completed": row.sessions_completed,
                "average_accuracy": round(float(row.avg_accuracy or 0), 2),
                "rank": rank,
            })

        return entries


def _find_correct_position(
    db: AsyncSession,
    session_id: int,
    call_number: str,
) -> Optional[str]:
    # In a real implementation, we'd look at all previously scanned items
    # and find where this one should slot in. For now, return None and
    # let the API compute it from the scan list if needed.
    return None
