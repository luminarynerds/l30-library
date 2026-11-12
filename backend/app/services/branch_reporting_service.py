# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.multi_branch import (
    Branch,
    BranchItemCopy,
    BranchStatistics,
    BranchStatus,
    LibrarySystem,
    Region,
    TransitRequest,
    TransitStatus,
)
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.inventory import ItemCopy, ItemCondition
from app.models.fine import Fine, FineStatus
from app.models.user import User, UserRole


class BranchReportingService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # BRANCH-LEVEL STATISTICS
    # =========================================================================

    async def generate_branch_statistics(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
    ) -> BranchStatistics:
        # Check if stats already exist
        result = await self.db.execute(
            select(BranchStatistics).where(
                and_(
                    BranchStatistics.branch_id == branch_id,
                    BranchStatistics.period_start == period_start,
                    BranchStatistics.period_end == period_end,
                )
            )
        )
        existing = result.scalar_one_or_none()

        # Calculate circulation stats
        circ_stats = await self._calculate_circulation_stats(
            branch_id, period_start, period_end
        )

        # Calculate collection stats
        collection_stats = await self._calculate_collection_stats(
            branch_id, period_start, period_end
        )

        # Calculate transit stats
        transit_stats = await self._calculate_transit_stats(
            branch_id, period_start, period_end
        )

        # Calculate patron stats
        patron_stats = await self._calculate_patron_stats(
            branch_id, period_start, period_end
        )

        # Calculate financial stats
        financial_stats = await self._calculate_financial_stats(
            branch_id, period_start, period_end
        )

        if existing:
            # Update existing record
            existing.total_checkouts = circ_stats["checkouts"]
            existing.total_renewals = circ_stats["renewals"]
            existing.total_checkins = circ_stats["checkins"]
            existing.total_holds_placed = circ_stats["holds_placed"]
            existing.total_holds_filled = circ_stats["holds_filled"]
            existing.items_owned = collection_stats["items_owned"]
            existing.items_added = collection_stats["items_added"]
            existing.items_withdrawn = collection_stats["items_withdrawn"]
            existing.items_sent_to_other_branches = transit_stats["sent"]
            existing.items_received_from_other_branches = transit_stats["received"]
            existing.active_patrons = patron_stats["active"]
            existing.new_registrations = patron_stats["new"]
            existing.fines_assessed = financial_stats["assessed"]
            existing.fines_collected = financial_stats["collected"]
            existing.fines_waived = financial_stats["waived"]
            existing.generated_at = datetime.now(timezone.utc)
            stats = existing
        else:
            # Create new record
            stats = BranchStatistics(
                branch_id=branch_id,
                period_start=period_start,
                period_end=period_end,
                total_checkouts=circ_stats["checkouts"],
                total_renewals=circ_stats["renewals"],
                total_checkins=circ_stats["checkins"],
                total_holds_placed=circ_stats["holds_placed"],
                total_holds_filled=circ_stats["holds_filled"],
                items_owned=collection_stats["items_owned"],
                items_added=collection_stats["items_added"],
                items_withdrawn=collection_stats["items_withdrawn"],
                items_sent_to_other_branches=transit_stats["sent"],
                items_received_from_other_branches=transit_stats["received"],
                active_patrons=patron_stats["active"],
                new_registrations=patron_stats["new"],
                fines_assessed=financial_stats["assessed"],
                fines_collected=financial_stats["collected"],
                fines_waived=financial_stats["waived"],
            )
            self.db.add(stats)

        await self.db.commit()
        await self.db.refresh(stats)
        return stats

    async def _calculate_circulation_stats(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
    ) -> dict[str, int]:
        start_dt = datetime.combine(period_start, datetime.min.time())
        end_dt = datetime.combine(period_end, datetime.max.time())

        # Join with BranchItemCopy to filter by branch
        # Checkouts
        checkout_query = (
            select(func.count(Checkout.id))
            .join(BranchItemCopy, Checkout.item_copy_id == BranchItemCopy.item_copy_id)
            .where(
                and_(
                    BranchItemCopy.current_branch_id == branch_id,
                    Checkout.checkout_date >= start_dt,
                    Checkout.checkout_date <= end_dt,
                )
            )
        )
        result = await self.db.execute(checkout_query)
        checkouts = result.scalar() or 0

        # Renewals (simplified - count where renewal_count > 0)
        renewal_query = (
            select(func.sum(Checkout.renewal_count))
            .join(BranchItemCopy, Checkout.item_copy_id == BranchItemCopy.item_copy_id)
            .where(
                and_(
                    BranchItemCopy.current_branch_id == branch_id,
                    Checkout.checkout_date >= start_dt,
                    Checkout.checkout_date <= end_dt,
                )
            )
        )
        result = await self.db.execute(renewal_query)
        renewals = result.scalar() or 0

        # Check-ins
        checkin_query = (
            select(func.count(Checkout.id))
            .join(BranchItemCopy, Checkout.item_copy_id == BranchItemCopy.item_copy_id)
            .where(
                and_(
                    BranchItemCopy.current_branch_id == branch_id,
                    Checkout.returned_date >= start_dt,
                    Checkout.returned_date <= end_dt,
                )
            )
        )
        result = await self.db.execute(checkin_query)
        checkins = result.scalar() or 0

        # Holds placed (by pickup location)
        holds_placed_query = (
            select(func.count(Hold.id))
            .where(
                and_(
                    Hold.pickup_branch_id == branch_id,
                    Hold.created_at >= start_dt,
                    Hold.created_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(holds_placed_query)
        holds_placed = result.scalar() or 0

        # Holds filled
        holds_filled_query = (
            select(func.count(Hold.id))
            .where(
                and_(
                    Hold.pickup_branch_id == branch_id,
                    Hold.status == HoldStatus.FULFILLED,
                    Hold.fulfilled_date >= start_dt,
                    Hold.fulfilled_date <= end_dt,
                )
            )
        )
        result = await self.db.execute(holds_filled_query)
        holds_filled = result.scalar() or 0

        return {
            "checkouts": checkouts,
            "renewals": renewals,
            "checkins": checkins,
            "holds_placed": holds_placed,
            "holds_filled": holds_filled,
        }

    async def _calculate_collection_stats(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
    ) -> dict[str, int]:
        start_dt = datetime.combine(period_start, datetime.min.time())
        end_dt = datetime.combine(period_end, datetime.max.time())

        # Items currently owned (home branch = this branch)
        owned_query = (
            select(func.count(BranchItemCopy.id))
            .where(BranchItemCopy.home_branch_id == branch_id)
        )
        result = await self.db.execute(owned_query)
        items_owned = result.scalar() or 0

        # Items added during period
        added_query = (
            select(func.count(BranchItemCopy.id))
            .where(
                and_(
                    BranchItemCopy.home_branch_id == branch_id,
                    BranchItemCopy.assigned_at >= start_dt,
                    BranchItemCopy.assigned_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(added_query)
        items_added = result.scalar() or 0

        # Items withdrawn (condition = WITHDRAWN)
        withdrawn_query = (
            select(func.count(ItemCopy.id))
            .join(BranchItemCopy, ItemCopy.id == BranchItemCopy.item_copy_id)
            .where(
                and_(
                    BranchItemCopy.home_branch_id == branch_id,
                    ItemCopy.condition == ItemCondition.WITHDRAWN,
                    ItemCopy.updated_at >= start_dt,
                    ItemCopy.updated_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(withdrawn_query)
        items_withdrawn = result.scalar() or 0

        return {
            "items_owned": items_owned,
            "items_added": items_added,
            "items_withdrawn": items_withdrawn,
        }

    async def _calculate_transit_stats(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
    ) -> dict[str, int]:
        start_dt = datetime.combine(period_start, datetime.min.time())
        end_dt = datetime.combine(period_end, datetime.max.time())

        # Items sent to other branches
        sent_query = (
            select(func.count(TransitRequest.id))
            .where(
                and_(
                    TransitRequest.from_branch_id == branch_id,
                    TransitRequest.status == TransitStatus.RECEIVED,
                    TransitRequest.requested_at >= start_dt,
                    TransitRequest.requested_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(sent_query)
        sent = result.scalar() or 0

        # Items received from other branches
        received_query = (
            select(func.count(TransitRequest.id))
            .where(
                and_(
                    TransitRequest.to_branch_id == branch_id,
                    TransitRequest.status == TransitStatus.RECEIVED,
                    TransitRequest.received_at >= start_dt,
                    TransitRequest.received_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(received_query)
        received = result.scalar() or 0

        return {
            "sent": sent,
            "received": received,
        }

    async def _calculate_patron_stats(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
    ) -> dict[str, int]:
        start_dt = datetime.combine(period_start, datetime.min.time())
        end_dt = datetime.combine(period_end, datetime.max.time())

        # Active patrons (home branch = this branch, has checkouts in period)
        active_query = (
            select(func.count(func.distinct(Checkout.user_id)))
            .join(User, Checkout.user_id == User.id)
            .where(
                and_(
                    User.home_branch_id == branch_id,
                    Checkout.checkout_date >= start_dt,
                    Checkout.checkout_date <= end_dt,
                )
            )
        )
        result = await self.db.execute(active_query)
        active = result.scalar() or 0

        # New registrations
        new_query = (
            select(func.count(User.id))
            .where(
                and_(
                    User.home_branch_id == branch_id,
                    User.role == UserRole.PATRON,
                    User.created_at >= start_dt,
                    User.created_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(new_query)
        new = result.scalar() or 0

        return {
            "active": active,
            "new": new,
        }

    async def _calculate_financial_stats(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
    ) -> dict[str, Decimal]:
        start_dt = datetime.combine(period_start, datetime.min.time())
        end_dt = datetime.combine(period_end, datetime.max.time())

        # Fines assessed (for patrons with home branch = this branch)
        assessed_query = (
            select(func.coalesce(func.sum(Fine.amount), 0))
            .join(User, Fine.user_id == User.id)
            .where(
                and_(
                    User.home_branch_id == branch_id,
                    Fine.created_at >= start_dt,
                    Fine.created_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(assessed_query)
        assessed = result.scalar() or Decimal("0.00")

        # Fines collected
        collected_query = (
            select(func.coalesce(func.sum(Fine.amount_paid), 0))
            .join(User, Fine.user_id == User.id)
            .where(
                and_(
                    User.home_branch_id == branch_id,
                    Fine.status == FineStatus.PAID,
                    Fine.paid_date >= start_dt,
                    Fine.paid_date <= end_dt,
                )
            )
        )
        result = await self.db.execute(collected_query)
        collected = result.scalar() or Decimal("0.00")

        # Fines waived
        waived_query = (
            select(func.coalesce(func.sum(Fine.amount - Fine.amount_paid), 0))
            .join(User, Fine.user_id == User.id)
            .where(
                and_(
                    User.home_branch_id == branch_id,
                    Fine.status == FineStatus.WAIVED,
                    Fine.updated_at >= start_dt,
                    Fine.updated_at <= end_dt,
                )
            )
        )
        result = await self.db.execute(waived_query)
        waived = result.scalar() or Decimal("0.00")

        return {
            "assessed": assessed,
            "collected": collected,
            "waived": waived,
        }

    # =========================================================================
    # SYSTEM-LEVEL REPORTS
    # =========================================================================

    async def get_system_statistics(
        self,
        library_system_id: int,
        period_start: date,
        period_end: date,
    ) -> dict[str, Any]:
        # Get all branches in the system
        result = await self.db.execute(
            select(Branch).where(Branch.library_system_id == library_system_id)
        )
        branches = list(result.scalars().all())
        branch_ids = [b.id for b in branches]

        # Generate stats for each branch if needed
        for branch in branches:
            await self.generate_branch_statistics(
                branch.id, period_start, period_end
            )

        # Aggregate from stored statistics
        result = await self.db.execute(
            select(
                func.sum(BranchStatistics.total_checkouts),
                func.sum(BranchStatistics.total_renewals),
                func.sum(BranchStatistics.total_checkins),
                func.sum(BranchStatistics.total_holds_placed),
                func.sum(BranchStatistics.total_holds_filled),
                func.sum(BranchStatistics.items_owned),
                func.sum(BranchStatistics.items_added),
                func.sum(BranchStatistics.items_withdrawn),
                func.sum(BranchStatistics.items_sent_to_other_branches),
                func.sum(BranchStatistics.items_received_from_other_branches),
                func.sum(BranchStatistics.active_patrons),
                func.sum(BranchStatistics.new_registrations),
                func.sum(BranchStatistics.fines_assessed),
                func.sum(BranchStatistics.fines_collected),
                func.sum(BranchStatistics.fines_waived),
            ).where(
                and_(
                    BranchStatistics.branch_id.in_(branch_ids),
                    BranchStatistics.period_start == period_start,
                    BranchStatistics.period_end == period_end,
                )
            )
        )
        row = result.one()

        return {
            "library_system_id": library_system_id,
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "branch_count": len(branches),
            "circulation": {
                "checkouts": row[0] or 0,
                "renewals": row[1] or 0,
                "checkins": row[2] or 0,
                "holds_placed": row[3] or 0,
                "holds_filled": row[4] or 0,
            },
            "collection": {
                "items_owned": row[5] or 0,
                "items_added": row[6] or 0,
                "items_withdrawn": row[7] or 0,
            },
            "transit": {
                "items_sent": row[8] or 0,
                "items_received": row[9] or 0,
            },
            "patrons": {
                "active": row[10] or 0,
                "new_registrations": row[11] or 0,
            },
            "financial": {
                "fines_assessed": float(row[12] or 0),
                "fines_collected": float(row[13] or 0),
                "fines_waived": float(row[14] or 0),
            },
        }

    async def get_branch_comparison(
        self,
        library_system_id: int,
        period_start: date,
        period_end: date,
    ) -> list[dict[str, Any]]:
        # Get all branches with their stats
        result = await self.db.execute(
            select(Branch, BranchStatistics)
            .join(BranchStatistics, Branch.id == BranchStatistics.branch_id)
            .where(
                and_(
                    Branch.library_system_id == library_system_id,
                    BranchStatistics.period_start == period_start,
                    BranchStatistics.period_end == period_end,
                )
            )
            .order_by(Branch.name)
        )
        rows = result.all()

        comparison = []
        for branch, stats in rows:
            comparison.append({
                "branch_id": branch.id,
                "branch_code": branch.code,
                "branch_name": branch.name,
                "checkouts": stats.total_checkouts,
                "checkins": stats.total_checkins,
                "holds_placed": stats.total_holds_placed,
                "holds_filled": stats.total_holds_filled,
                "items_owned": stats.items_owned,
                "active_patrons": stats.active_patrons,
                "new_registrations": stats.new_registrations,
                "fines_collected": float(stats.fines_collected or 0),
                "items_sent": stats.items_sent_to_other_branches,
                "items_received": stats.items_received_from_other_branches,
            })

        return comparison

    async def get_region_statistics(
        self,
        region_id: int,
        period_start: date,
        period_end: date,
    ) -> dict[str, Any]:
        # Get all branches in the region
        result = await self.db.execute(
            select(Branch).where(Branch.region_id == region_id)
        )
        branches = list(result.scalars().all())
        branch_ids = [b.id for b in branches]

        if not branch_ids:
            return {
                "region_id": region_id,
                "branch_count": 0,
                "circulation": {},
                "collection": {},
                "patrons": {},
                "financial": {},
            }

        # Get region info
        region_result = await self.db.execute(
            select(Region).where(Region.id == region_id)
        )
        region = region_result.scalar_one_or_none()

        # Aggregate stats
        result = await self.db.execute(
            select(
                func.sum(BranchStatistics.total_checkouts),
                func.sum(BranchStatistics.total_holds_filled),
                func.sum(BranchStatistics.items_owned),
                func.sum(BranchStatistics.active_patrons),
                func.sum(BranchStatistics.fines_collected),
            ).where(
                and_(
                    BranchStatistics.branch_id.in_(branch_ids),
                    BranchStatistics.period_start == period_start,
                    BranchStatistics.period_end == period_end,
                )
            )
        )
        row = result.one()

        return {
            "region_id": region_id,
            "region_name": region.name if region else None,
            "branch_count": len(branches),
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat(),
            },
            "total_checkouts": row[0] or 0,
            "total_holds_filled": row[1] or 0,
            "total_items": row[2] or 0,
            "active_patrons": row[3] or 0,
            "fines_collected": float(row[4] or 0),
        }

    # =========================================================================
    # TREND ANALYSIS
    # =========================================================================

    async def get_circulation_trend(
        self,
        branch_id: int | None = None,
        library_system_id: int | None = None,
        months: int = 12,
    ) -> list[dict[str, Any]]:
        end_date = date.today().replace(day=1) - timedelta(days=1)  # End of last month
        start_date = (end_date - timedelta(days=30 * months)).replace(day=1)

        # Build query conditions
        conditions = []
        if branch_id:
            conditions.append(BranchStatistics.branch_id == branch_id)
        elif library_system_id:
            branch_subquery = (
                select(Branch.id)
                .where(Branch.library_system_id == library_system_id)
                .scalar_subquery()
            )
            conditions.append(BranchStatistics.branch_id.in_(branch_subquery))

        conditions.append(BranchStatistics.period_start >= start_date)
        conditions.append(BranchStatistics.period_end <= end_date)

        # Get monthly aggregates
        month_trunc = func.date_trunc('month', BranchStatistics.period_start).label('month')
        query = (
            select(
                month_trunc,
                func.sum(BranchStatistics.total_checkouts),
                func.sum(BranchStatistics.total_holds_filled),
                func.sum(BranchStatistics.active_patrons),
            )
            .where(and_(*conditions))
            .group_by(month_trunc)
            .order_by(month_trunc)
        )

        result = await self.db.execute(query)
        trend = []
        for row in result.all():
            trend.append({
                "month": row[0].strftime("%Y-%m") if row[0] else None,
                "checkouts": row[1] or 0,
                "holds_filled": row[2] or 0,
                "active_patrons": row[3] or 0,
            })

        return trend

    # =========================================================================
    # BRANCH AVAILABILITY
    # =========================================================================

    async def get_item_availability_by_branch(
        self,
        catalog_item_id: int,
        library_system_id: int | None = None,
    ) -> list[dict[str, Any]]:
        query = (
            select(
                Branch.id,
                Branch.code,
                Branch.name,
                func.count(BranchItemCopy.id).label('total_copies'),
                func.sum(
                    case(
                        (ItemCopy.condition.notin_([ItemCondition.WITHDRAWN, ItemCondition.DAMAGED]), 1),
                        else_=0
                    )
                ).label('available_copies'),
            )
            .join(BranchItemCopy, Branch.id == BranchItemCopy.current_branch_id)
            .join(ItemCopy, BranchItemCopy.item_copy_id == ItemCopy.id)
            .where(ItemCopy.catalog_item_id == catalog_item_id)
        )

        if library_system_id:
            query = query.where(Branch.library_system_id == library_system_id)

        query = query.group_by(Branch.id, Branch.code, Branch.name)
        query = query.order_by(Branch.name)

        result = await self.db.execute(query)
        availability = []
        for row in result.all():
            availability.append({
                "branch_id": row[0],
                "branch_code": row[1],
                "branch_name": row[2],
                "total_copies": row[3] or 0,
                "available_copies": row[4] or 0,
            })

        return availability

    # =========================================================================
    # STORED STATISTICS RETRIEVAL
    # =========================================================================

    async def get_branch_statistics(
        self,
        branch_id: int,
        period_start: date,
        period_end: date,
    ) -> BranchStatistics | None:
        result = await self.db.execute(
            select(BranchStatistics).where(
                and_(
                    BranchStatistics.branch_id == branch_id,
                    BranchStatistics.period_start == period_start,
                    BranchStatistics.period_end == period_end,
                )
            )
        )
        return result.scalar_one_or_none()

    async def list_branch_statistics(
        self,
        branch_id: int | None = None,
        library_system_id: int | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 100,
    ) -> list[BranchStatistics]:
        query = select(BranchStatistics)

        if branch_id:
            query = query.where(BranchStatistics.branch_id == branch_id)
        elif library_system_id:
            result = await self.db.execute(
                select(Branch.id).where(Branch.library_system_id == library_system_id)
            )
            branch_ids = [row[0] for row in result.all()]
            query = query.where(BranchStatistics.branch_id.in_(branch_ids))

        if from_date:
            query = query.where(BranchStatistics.period_start >= from_date)
        if to_date:
            query = query.where(BranchStatistics.period_end <= to_date)

        query = query.order_by(BranchStatistics.period_start.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())
