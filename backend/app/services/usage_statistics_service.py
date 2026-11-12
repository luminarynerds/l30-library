# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import (
    CatalogItem, Checkout, CheckoutStatus, Event, EventRegistration,
    Fine, Hold, HoldStatus, ItemCopy, ItemType, User, UserRole,
)
from ..models.program import Program
from ..models.usage_statistics import (
    CirculationStatistics, CollectionStatistics, ComputerUsageStatistics,
    PatronStatistics, PeerComparisonData, PeerComparisonLibrary,
    PeriodType, ProgramStatistics, ReferenceQuestion, ReferenceStatistics,
    StatisticalReport, ReportStatus, ReportType, UsageStatisticsSettings,
    VisitCount, VisitStatistics,
)
from ..schemas.usage_statistics import (
    CirculationStatisticsSummary, CollectionStatisticsSummary,
    ComputerUsageSummary, IMLSSurveyData, MonthOverMonthTrend,
    PatronStatisticsSummary, PeerComparisonResult, ProgramStatisticsSummary,
    ReferenceStatisticsSummary, StatisticsMetadata, TrendAnalysis,
    TrendDataPoint, UsageStatisticsDashboard, VisitStatisticsSummary,
    YearOverYearTrend, PeriodType as SchemaPeriodType,
)

logger = get_logger(__name__)


class UsageStatisticsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _resolve_branch_id_from_label(self, label: Optional[str]) -> Optional[int]:
        from ..core.branch_resolver import label_to_branch_id
        return label_to_branch_id(label)

    async def _resolve_branch_label_from_id(self, branch_id: Optional[int]) -> Optional[str]:
        from ..core.branch_resolver import branch_id_to_label
        return branch_id_to_label(branch_id)

    # ========================================================================
    # Circulation Statistics
    # ========================================================================

    async def generate_circulation_statistics(
        self,
        period_start: date,
        period_end: date,
        period_type: str,
        branch_location: Optional[str] = None,
        generated_by_id: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> CirculationStatistics:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)
        elif branch_id is not None and branch_location is None:
            branch_location = await self._resolve_branch_label_from_id(branch_id)

        start_dt = datetime.combine(period_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Build base filters
        checkout_filters = [
            Checkout.checked_out_at >= start_dt,
            Checkout.checked_out_at <= end_dt,
        ]

        # Get checkouts by item type
        checkouts_by_type = await self._get_checkouts_by_item_type(start_dt, end_dt)

        # Count total checkouts
        checkout_count_result = await self.db.execute(
            select(func.count(Checkout.id)).where(*checkout_filters)
        )
        total_checkouts = checkout_count_result.scalar() or 0

        # Count renewals
        renewal_result = await self.db.execute(
            select(func.count(Checkout.id)).where(
                *checkout_filters,
                Checkout.renewal_count > 0,
            )
        )
        total_renewals = renewal_result.scalar() or 0

        # Count holds placed
        holds_placed_result = await self.db.execute(
            select(func.count(Hold.id)).where(
                Hold.created_at >= start_dt,
                Hold.created_at <= end_dt,
            )
        )
        total_holds_placed = holds_placed_result.scalar() or 0

        # Count holds filled
        holds_filled_result = await self.db.execute(
            select(func.count(Hold.id)).where(
                Hold.status == HoldStatus.ready,
                Hold.updated_at >= start_dt,
                Hold.updated_at <= end_dt,
            )
        )
        total_holds_filled = holds_filled_result.scalar() or 0

        # Count returns
        returns_result = await self.db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.returned_at >= start_dt,
                Checkout.returned_at <= end_dt,
            )
        )
        total_returns = returns_result.scalar() or 0

        # Calculate turnover rate
        collection_count_result = await self.db.execute(
            select(func.count(ItemCopy.id))
        )
        collection_size = collection_count_result.scalar() or 1
        turnover_rate = (total_checkouts / collection_size) if collection_size > 0 else 0

        # Create statistics record
        stats = CirculationStatistics(
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            branch_id=branch_id,
            branch_location=branch_location,
            checkouts_by_item_type=checkouts_by_type,
            total_checkouts=total_checkouts,
            total_renewals=total_renewals,
            total_holds_placed=total_holds_placed,
            total_holds_filled=total_holds_filled,
            total_returns=total_returns,
            collection_turnover_rate=Decimal(str(round(turnover_rate, 4))),
            generated_by_id=generated_by_id,
        )

        self.db.add(stats)
        await self.db.commit()
        await self.db.refresh(stats)

        return stats

    async def _get_checkouts_by_item_type(
        self,
        start_dt: datetime,
        end_dt: datetime,
    ) -> Dict[str, int]:
        result = await self.db.execute(
            select(
                CatalogItem.item_type,
                func.count(Checkout.id),
            )
            .select_from(Checkout)
            .outerjoin(CatalogItem, Checkout.item_id == CatalogItem.id)
            .outerjoin(ItemCopy, Checkout.item_copy_id == ItemCopy.id)
            .where(
                Checkout.checked_out_at >= start_dt,
                Checkout.checked_out_at <= end_dt,
                # Ensure we can resolve to a catalog item via either path
                or_(CatalogItem.id.isnot(None), ItemCopy.catalog_item_id.isnot(None)),
            )
            .group_by(CatalogItem.item_type)
        )

        # For checkouts where item_id is NULL but item_copy_id is set,
        # we need a second query to get the type via item_copies
        direct_results = {str(item_type): count for item_type, count in result.all() if item_type is not None}

        # Get counts for checkouts only reachable via item_copy_id
        fallback_result = await self.db.execute(
            select(
                CatalogItem.item_type,
                func.count(Checkout.id),
            )
            .select_from(Checkout)
            .join(ItemCopy, Checkout.item_copy_id == ItemCopy.id)
            .join(CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id)
            .where(
                Checkout.checked_out_at >= start_dt,
                Checkout.checked_out_at <= end_dt,
                Checkout.item_id.is_(None),
            )
            .group_by(CatalogItem.item_type)
        )

        for item_type, count in fallback_result.all():
            key = str(item_type)
            direct_results[key] = direct_results.get(key, 0) + count

        return direct_results

    async def get_circulation_summary(
        self,
        period_start: date,
        period_end: date,
        period_type: str = "monthly",
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> CirculationStatisticsSummary:
        # Try to get existing stats, or generate them
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)

        q = select(CirculationStatistics).where(
            CirculationStatistics.period_start == period_start,
            CirculationStatistics.period_end == period_end,
            CirculationStatistics.period_type == period_type,
        )
        if branch_id is not None:
            q = q.where(CirculationStatistics.branch_id == branch_id)
        else:
            q = q.where(CirculationStatistics.branch_id.is_(None))

        result = await self.db.execute(q)
        stats = result.scalar_one_or_none()

        if not stats:
            stats = await self.generate_circulation_statistics(
                period_start, period_end, period_type, branch_location,
                branch_id=branch_id,
            )

        return CirculationStatisticsSummary(
            total_checkouts=stats.total_checkouts,
            total_renewals=stats.total_renewals,
            total_holds=stats.total_holds_placed,
            total_ill_transactions=(
                stats.items_loaned_to_other_libraries +
                stats.items_borrowed_from_other_libraries
            ),
            turnover_rate=float(stats.collection_turnover_rate) if stats.collection_turnover_rate else None,
            checkouts_by_item_type=stats.checkouts_by_item_type or {},
            metadata=StatisticsMetadata(
                generated_at=stats.generated_at,
                period_start=stats.period_start,
                period_end=stats.period_end,
                period_type=SchemaPeriodType(stats.period_type),
                branch_location=stats.branch_location,
            ),
        )

    # ========================================================================
    # Collection Statistics
    # ========================================================================

    async def generate_collection_statistics(
        self,
        snapshot_date: date,
        branch_location: Optional[str] = None,
        generated_by_id: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> CollectionStatistics:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)
        elif branch_id is not None and branch_location is None:
            branch_location = await self._resolve_branch_label_from_id(branch_id)

        # Count items by format
        items_by_format = await self._count_items_by_format()

        # Total items
        total_items_result = await self.db.execute(
            select(func.count(ItemCopy.id))
        )
        total_items = total_items_result.scalar() or 0

        # Total titles
        total_titles_result = await self.db.execute(
            select(func.count(CatalogItem.id))
        )
        total_titles = total_titles_result.scalar() or 0

        # Calculate totals by material type
        print_materials = items_by_format.get("book", 0) + items_by_format.get("magazine", 0)
        audio_materials = items_by_format.get("audiobook", 0) + items_by_format.get("cd", 0)
        video_materials = items_by_format.get("dvd", 0) + items_by_format.get("bluray", 0)

        stats = CollectionStatistics(
            snapshot_date=snapshot_date,
            branch_id=branch_id,
            branch_location=branch_location,
            items_owned_by_format=items_by_format,
            total_items_owned=total_items,
            total_titles_owned=total_titles,
            print_materials=print_materials,
            audio_materials=audio_materials,
            video_materials=video_materials,
            generated_by_id=generated_by_id,
        )

        self.db.add(stats)
        await self.db.commit()
        await self.db.refresh(stats)

        return stats

    async def _count_items_by_format(self) -> Dict[str, int]:
        result = await self.db.execute(
            select(
                CatalogItem.item_type,
                func.count(ItemCopy.id),
            )
            .join(ItemCopy, ItemCopy.catalog_item_id == CatalogItem.id)
            .group_by(CatalogItem.item_type)
        )

        return {str(item_type): count for item_type, count in result.all()}

    async def get_collection_summary(
        self,
        snapshot_date: Optional[date] = None,
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> CollectionStatisticsSummary:
        if snapshot_date is None:
            snapshot_date = date.today()

        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)

        q = select(CollectionStatistics).where(
            CollectionStatistics.snapshot_date == snapshot_date,
        )
        if branch_id is not None:
            q = q.where(CollectionStatistics.branch_id == branch_id)
        else:
            q = q.where(CollectionStatistics.branch_id.is_(None))

        result = await self.db.execute(q)
        stats = result.scalar_one_or_none()

        if not stats:
            stats = await self.generate_collection_statistics(
                snapshot_date, branch_location, branch_id=branch_id,
            )

        net_change = stats.total_items_added - stats.total_items_withdrawn

        return CollectionStatisticsSummary(
            total_items=stats.total_items_owned,
            total_titles=stats.total_titles_owned,
            items_by_format=stats.items_owned_by_format or {},
            net_change=net_change,
            collection_value=float(stats.total_collection_value) if stats.total_collection_value else None,
            snapshot_date=stats.snapshot_date,
        )

    # ========================================================================
    # Patron Statistics
    # ========================================================================

    async def generate_patron_statistics(
        self,
        period_start: date,
        period_end: date,
        period_type: str,
        branch_location: Optional[str] = None,
        generated_by_id: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> PatronStatistics:
        # Branch reconciliation: prefer branch_id; fill the missing side
        # so the new row carries both for back-compat reads.
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)
        elif branch_id is not None and branch_location is None:
            branch_location = await self._resolve_branch_label_from_id(branch_id)

        start_dt = datetime.combine(period_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Total registered patrons
        total_registered_result = await self.db.execute(
            select(func.count(User.id)).where(
                User.role.in_([UserRole.PATRON, UserRole.CHILD]),
                User.is_active == True,
            )
        )
        total_registered = total_registered_result.scalar() or 0

        # New registrations in period
        new_registrations_result = await self.db.execute(
            select(func.count(User.id)).where(
                User.role.in_([UserRole.PATRON, UserRole.CHILD]),
                User.created_at >= start_dt,
                User.created_at <= end_dt,
            )
        )
        new_registrations = new_registrations_result.scalar() or 0

        # Active borrowers (had checkouts in period)
        active_borrowers_result = await self.db.execute(
            select(func.count(func.distinct(Checkout.user_id))).where(
                Checkout.checked_out_at >= start_dt,
                Checkout.checked_out_at <= end_dt,
            )
        )
        active_borrowers = active_borrowers_result.scalar() or 0

        # Calculate average checkouts per active patron
        total_checkouts_result = await self.db.execute(
            select(func.count(Checkout.id)).where(
                Checkout.checked_out_at >= start_dt,
                Checkout.checked_out_at <= end_dt,
            )
        )
        total_checkouts = total_checkouts_result.scalar() or 0
        avg_checkouts = total_checkouts / active_borrowers if active_borrowers > 0 else 0

        stats = PatronStatistics(
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            branch_id=branch_id,
            branch_location=branch_location,
            total_registered_patrons=total_registered,
            new_registrations=new_registrations,
            active_borrowers=active_borrowers,
            avg_checkouts_per_active_patron=Decimal(str(round(avg_checkouts, 2))),
            generated_by_id=generated_by_id,
        )

        self.db.add(stats)
        await self.db.commit()
        await self.db.refresh(stats)

        return stats

    async def get_patron_summary(
        self,
        period_start: date,
        period_end: date,
        period_type: str = "monthly",
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> PatronStatisticsSummary:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)

        q = select(PatronStatistics).where(
            PatronStatistics.period_start == period_start,
            PatronStatistics.period_end == period_end,
            PatronStatistics.period_type == period_type,
        )
        if branch_id is not None:
            q = q.where(PatronStatistics.branch_id == branch_id)
        else:
            q = q.where(PatronStatistics.branch_id.is_(None))

        result = await self.db.execute(q)
        stats = result.scalar_one_or_none()

        if not stats:
            stats = await self.generate_patron_statistics(
                period_start, period_end, period_type, branch_location,
                branch_id=branch_id,
            )

        registration_rate = (
            stats.new_registrations / stats.total_registered_patrons
            if stats.total_registered_patrons > 0 else 0
        )
        engagement_rate = (
            stats.active_borrowers / stats.total_registered_patrons
            if stats.total_registered_patrons > 0 else 0
        )

        return PatronStatisticsSummary(
            total_registered=stats.total_registered_patrons,
            active_borrowers=stats.active_borrowers,
            new_registrations=stats.new_registrations,
            registration_rate=round(registration_rate, 4),
            engagement_rate=round(engagement_rate, 4),
            metadata=StatisticsMetadata(
                generated_at=stats.generated_at,
                period_start=stats.period_start,
                period_end=stats.period_end,
                period_type=SchemaPeriodType(stats.period_type),
                branch_location=stats.branch_location,
            ),
        )

    # ========================================================================
    # Program Statistics
    # ========================================================================

    async def generate_program_statistics(
        self,
        period_start: date,
        period_end: date,
        period_type: str,
        branch_location: Optional[str] = None,
        generated_by_id: Optional[int] = None,
        branch_id: Optional[int] = None,
    ) -> ProgramStatistics:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)
        elif branch_id is not None and branch_location is None:
            branch_location = await self._resolve_branch_label_from_id(branch_id)

        start_dt = datetime.combine(period_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Programs held in period. "held" = the program took place.
        # 'completed'  = done and recorded (canonical).
        # 'active'/'in_progress' = currently in progress at the moment of
        #   query; we only count these if program_date is in the past or
        #   today so that stuck rows (active but date passed long ago)
        #   don't get folded in, and rows that are future-scheduled-but-
        #   incorrectly-marked-active don't sneak in.
        # The legacy Event/EventRegistration path counted signups, not
        # attendance — kept as a fallback for deployments that haven't
        # migrated to the programs table.
        from app.models.program import ProgramStatus

        start_date = period_start
        end_date = period_end

        programs_result = await self.db.execute(
            select(
                func.count(Program.id),
                func.coalesce(func.sum(Program.actual_attendance), 0),
            ).where(
                Program.program_date >= start_date,
                Program.program_date <= end_date,
                or_(
                    Program.status == ProgramStatus.COMPLETED,
                    and_(
                        Program.status.in_([
                            ProgramStatus.ACTIVE,
                            ProgramStatus.IN_PROGRESS,
                        ]),
                        Program.program_date <= end_date,
                    ),
                ),
            )
        )
        held_count, held_attendance = programs_result.one()
        total_programs = int(held_count or 0)
        total_attendance = int(held_attendance or 0)

        if total_programs == 0:
            # Fallback to the legacy events path so older deployments that
            # haven't yet adopted the Programs table aren't silently zeroed.
            #
            # PLS / IMLS report ATTENDANCE, not registrations. Counting
            # EventRegistration rows is wrong on three axes:
            #   - registrations include waitlisted / cancelled / no-show rows
            #   - registrations include future events still in the window
            #   - one walk-in attendee with no registration is not counted at all
            #
            # We now read attendance from, in order of preference:
            #   1. Event.attended_count if set by staff (mirrors
            #      Program.actual_attendance).
            #   2. Sum of AttendanceSession.total_checked_in across all
            #      sessions whose parent event falls in the period.
            # If neither is populated, attendance is 0 — we explicitly do
            # NOT proxy registration counts to avoid inflating state reports.
            from app.models.attendance import AttendanceSession

            events_result = await self.db.execute(
                select(func.count(Event.id)).where(
                    Event.start_time >= start_dt,
                    Event.start_time <= end_dt,
                )
            )
            total_programs = events_result.scalar() or 0

            # 1. Sum of Event.attended_count for events with the field set.
            staff_attendance_result = await self.db.execute(
                select(func.coalesce(func.sum(Event.attended_count), 0)).where(
                    Event.start_time >= start_dt,
                    Event.start_time <= end_dt,
                    Event.attended_count.isnot(None),
                )
            )
            staff_attendance = int(staff_attendance_result.scalar() or 0)

            # 2. Sum of AttendanceSession.total_checked_in for events that
            #    do NOT have attended_count set (avoid double-counting).
            session_attendance_result = await self.db.execute(
                select(func.coalesce(func.sum(AttendanceSession.total_checked_in), 0))
                .join(Event, Event.id == AttendanceSession.event_id)
                .where(
                    Event.start_time >= start_dt,
                    Event.start_time <= end_dt,
                    Event.attended_count.is_(None),
                )
            )
            session_attendance = int(session_attendance_result.scalar() or 0)

            total_attendance = staff_attendance + session_attendance

        avg_attendance = total_attendance / total_programs if total_programs > 0 else 0

        # Get events by category
        events_by_category = await self._count_events_by_category(start_dt, end_dt)

        stats = ProgramStatistics(
            period_start=period_start,
            period_end=period_end,
            period_type=period_type,
            branch_id=branch_id,
            branch_location=branch_location,
            events_by_category=events_by_category,
            total_programs_offered=total_programs,
            total_program_attendance=total_attendance,
            avg_attendance_per_program=Decimal(str(round(avg_attendance, 2))),
            generated_by_id=generated_by_id,
        )

        self.db.add(stats)
        await self.db.commit()
        await self.db.refresh(stats)

        return stats

    async def _count_events_by_category(
        self,
        start_dt: datetime,
        end_dt: datetime,
    ) -> Dict[str, int]:
        result = await self.db.execute(
            select(
                Event.category,
                func.count(Event.id),
            )
            .where(
                Event.start_time >= start_dt,
                Event.start_time <= end_dt,
            )
            .group_by(Event.category)
        )

        return {str(category): count for category, count in result.all() if category}

    async def get_program_summary(
        self,
        period_start: date,
        period_end: date,
        period_type: str = "monthly",
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> ProgramStatisticsSummary:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)

        q = select(ProgramStatistics).where(
            ProgramStatistics.period_start == period_start,
            ProgramStatistics.period_end == period_end,
            ProgramStatistics.period_type == period_type,
        )
        if branch_id is not None:
            q = q.where(ProgramStatistics.branch_id == branch_id)
        else:
            q = q.where(ProgramStatistics.branch_id.is_(None))

        result = await self.db.execute(q)
        stats = result.scalar_one_or_none()

        if not stats:
            stats = await self.generate_program_statistics(
                period_start, period_end, period_type, branch_location,
                branch_id=branch_id,
            )

        programs_by_age = {
            "children": stats.childrens_programs_count,
            "young_adult": stats.young_adult_programs_count,
            "adult": stats.adult_programs_count,
        }

        attendance_by_age = {
            "children": stats.childrens_program_attendance,
            "young_adult": stats.young_adult_program_attendance,
            "adult": stats.adult_program_attendance,
        }

        return ProgramStatisticsSummary(
            total_programs=stats.total_programs_offered,
            total_attendance=stats.total_program_attendance,
            avg_attendance=float(stats.avg_attendance_per_program or 0),
            programs_by_age_group=programs_by_age,
            attendance_by_age_group=attendance_by_age,
            metadata=StatisticsMetadata(
                generated_at=stats.generated_at,
                period_start=stats.period_start,
                period_end=stats.period_end,
                period_type=SchemaPeriodType(stats.period_type),
                branch_location=stats.branch_location,
            ),
        )

    # ========================================================================
    # Computer Usage Statistics
    # ========================================================================

    async def get_computer_usage_summary(
        self,
        period_start: date,
        period_end: date,
        period_type: str = "monthly",
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> ComputerUsageSummary:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)

        q = select(ComputerUsageStatistics).where(
            ComputerUsageStatistics.period_start == period_start,
            ComputerUsageStatistics.period_end == period_end,
            ComputerUsageStatistics.period_type == period_type,
        )
        if branch_id is not None:
            q = q.where(ComputerUsageStatistics.branch_id == branch_id)
        else:
            q = q.where(ComputerUsageStatistics.branch_id.is_(None))

        result = await self.db.execute(q)
        stats = result.scalar_one_or_none()

        if stats:
            return ComputerUsageSummary(
                total_sessions=stats.total_sessions,
                unique_users=stats.unique_users,
                total_hours=float(stats.total_hours_used or 0),
                avg_session_minutes=float(stats.avg_session_length_minutes or 0),
                wifi_sessions=stats.wifi_sessions,
                metadata=StatisticsMetadata(
                    generated_at=stats.generated_at,
                    period_start=stats.period_start,
                    period_end=stats.period_end,
                    period_type=SchemaPeriodType(stats.period_type),
                    branch_location=stats.branch_location,
                ),
            )

        # Return empty summary if no data
        return ComputerUsageSummary(
            total_sessions=0,
            unique_users=0,
            total_hours=0,
            avg_session_minutes=0,
            wifi_sessions=0,
            metadata=StatisticsMetadata(
                generated_at=datetime.now(timezone.utc),
                period_start=period_start,
                period_end=period_end,
                period_type=SchemaPeriodType(period_type),
                branch_location=branch_location,
            ),
        )

    # ========================================================================
    # Reference Statistics
    # ========================================================================

    async def get_reference_summary(
        self,
        period_start: date,
        period_end: date,
        period_type: str = "monthly",
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> ReferenceStatisticsSummary:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)

        q = select(ReferenceStatistics).where(
            ReferenceStatistics.period_start == period_start,
            ReferenceStatistics.period_end == period_end,
            ReferenceStatistics.period_type == period_type,
        )
        if branch_id is not None:
            q = q.where(ReferenceStatistics.branch_id == branch_id)
        else:
            q = q.where(ReferenceStatistics.branch_id.is_(None))

        result = await self.db.execute(q)
        stats = result.scalar_one_or_none()

        if stats:
            return ReferenceStatisticsSummary(
                total_questions=stats.total_questions,
                questions_by_type=stats.questions_by_type or {},
                questions_by_method=stats.questions_by_method or {},
                avg_duration=float(stats.avg_duration_minutes) if stats.avg_duration_minutes else None,
                metadata=StatisticsMetadata(
                    generated_at=stats.generated_at,
                    period_start=stats.period_start,
                    period_end=stats.period_end,
                    period_type=SchemaPeriodType(stats.period_type),
                    branch_location=stats.branch_location,
                ),
            )

        # Aggregate from individual questions if no summary exists
        start_dt = datetime.combine(period_start, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(period_end, datetime.max.time()).replace(tzinfo=timezone.utc)

        # Count questions
        total_result = await self.db.execute(
            select(func.count(ReferenceQuestion.id)).where(
                ReferenceQuestion.asked_at >= start_dt,
                ReferenceQuestion.asked_at <= end_dt,
            )
        )
        total_questions = total_result.scalar() or 0

        # Questions by type
        type_result = await self.db.execute(
            select(
                ReferenceQuestion.question_type,
                func.count(ReferenceQuestion.id),
            )
            .where(
                ReferenceQuestion.asked_at >= start_dt,
                ReferenceQuestion.asked_at <= end_dt,
            )
            .group_by(ReferenceQuestion.question_type)
        )
        questions_by_type = {str(qtype): count for qtype, count in type_result.all()}

        # Questions by method
        method_result = await self.db.execute(
            select(
                ReferenceQuestion.contact_method,
                func.count(ReferenceQuestion.id),
            )
            .where(
                ReferenceQuestion.asked_at >= start_dt,
                ReferenceQuestion.asked_at <= end_dt,
            )
            .group_by(ReferenceQuestion.contact_method)
        )
        questions_by_method = {str(method): count for method, count in method_result.all()}

        # Average duration
        duration_result = await self.db.execute(
            select(func.avg(ReferenceQuestion.duration_minutes)).where(
                ReferenceQuestion.asked_at >= start_dt,
                ReferenceQuestion.asked_at <= end_dt,
                ReferenceQuestion.duration_minutes.isnot(None),
            )
        )
        avg_duration = duration_result.scalar()

        return ReferenceStatisticsSummary(
            total_questions=total_questions,
            questions_by_type=questions_by_type,
            questions_by_method=questions_by_method,
            avg_duration=float(avg_duration) if avg_duration else None,
            metadata=StatisticsMetadata(
                generated_at=datetime.now(timezone.utc),
                period_start=period_start,
                period_end=period_end,
                period_type=SchemaPeriodType(period_type),
                branch_location=branch_location,
            ),
        )

    # ========================================================================
    # Visit Statistics
    # ========================================================================

    async def get_visit_summary(
        self,
        period_start: date,
        period_end: date,
        period_type: str = "monthly",
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> VisitStatisticsSummary:
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)

        q = select(VisitStatistics).where(
            VisitStatistics.period_start == period_start,
            VisitStatistics.period_end == period_end,
            VisitStatistics.period_type == period_type,
        )
        if branch_id is not None:
            q = q.where(VisitStatistics.branch_id == branch_id)
        else:
            q = q.where(VisitStatistics.branch_id.is_(None))

        result = await self.db.execute(q)
        stats = result.scalar_one_or_none()

        if stats:
            day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            peak_day = day_names[stats.peak_day_of_week] if stats.peak_day_of_week is not None else None

            return VisitStatisticsSummary(
                total_visits=stats.total_visits,
                avg_daily_visits=float(stats.avg_daily_visits or 0),
                visits_per_capita=float(stats.visits_per_capita) if stats.visits_per_capita else None,
                peak_hour=stats.peak_hour,
                peak_day=peak_day,
                metadata=StatisticsMetadata(
                    generated_at=stats.generated_at,
                    period_start=stats.period_start,
                    period_end=stats.period_end,
                    period_type=SchemaPeriodType(stats.period_type),
                    branch_location=stats.branch_location,
                ),
            )

        # Aggregate from daily counts if no summary exists
        total_result = await self.db.execute(
            select(func.sum(VisitCount.door_count)).where(
                VisitCount.count_date >= period_start,
                VisitCount.count_date <= period_end,
            )
        )
        total_visits = total_result.scalar() or 0

        days_in_period = (period_end - period_start).days + 1
        avg_daily = total_visits / days_in_period if days_in_period > 0 else 0

        return VisitStatisticsSummary(
            total_visits=total_visits,
            avg_daily_visits=round(avg_daily, 2),
            visits_per_capita=None,
            peak_hour=None,
            peak_day=None,
            metadata=StatisticsMetadata(
                generated_at=datetime.now(timezone.utc),
                period_start=period_start,
                period_end=period_end,
                period_type=SchemaPeriodType(period_type),
                branch_location=branch_location,
            ),
        )

    # ========================================================================
    # Dashboard / Comprehensive Summary
    # ========================================================================

    async def get_dashboard(
        self,
        period_start: date,
        period_end: date,
        period_type: str = "monthly",
        branch_location: Optional[str] = None,
    ) -> UsageStatisticsDashboard:
        # Run summaries sequentially — they share a single DB session which
        # cannot handle concurrent operations (IllegalStateChangeError).
        circulation = await self.get_circulation_summary(period_start, period_end, period_type, branch_location)
        collection = await self.get_collection_summary(period_end, branch_location)
        patrons = await self.get_patron_summary(period_start, period_end, period_type, branch_location)
        programs = await self.get_program_summary(period_start, period_end, period_type, branch_location)
        computer = await self.get_computer_usage_summary(period_start, period_end, period_type, branch_location)
        reference = await self.get_reference_summary(period_start, period_end, period_type, branch_location)
        visits = await self.get_visit_summary(period_start, period_end, period_type, branch_location)

        return UsageStatisticsDashboard(
            circulation=circulation,
            collection=collection,
            patrons=patrons,
            programs=programs,
            computer_usage=computer,
            reference=reference,
            visits=visits,
            generated_at=datetime.now(timezone.utc),
        )

    # ========================================================================
    # Trend Analysis
    # ========================================================================

    async def get_month_over_month_trends(
        self,
        metric: str,
        months: int = 12,
        branch_location: Optional[str] = None,
    ) -> List[MonthOverMonthTrend]:
        trends = []
        today = date.today()

        for i in range(months - 1):
            # Current month
            current_month_start = date(today.year, today.month, 1) - timedelta(days=30 * i)
            current_month_start = current_month_start.replace(day=1)

            # Calculate last day of current month
            if current_month_start.month == 12:
                current_month_end = date(current_month_start.year + 1, 1, 1) - timedelta(days=1)
            else:
                current_month_end = date(current_month_start.year, current_month_start.month + 1, 1) - timedelta(days=1)

            # Previous month
            previous_month_end = current_month_start - timedelta(days=1)
            previous_month_start = previous_month_end.replace(day=1)

            # Get values based on metric
            current_value = await self._get_metric_value(
                metric, current_month_start, current_month_end, branch_location
            )
            previous_value = await self._get_metric_value(
                metric, previous_month_start, previous_month_end, branch_location
            )

            # Calculate change
            if previous_value > 0:
                change_percent = ((current_value - previous_value) / previous_value) * 100
            else:
                change_percent = 100 if current_value > 0 else 0

            trend_direction = "up" if change_percent > 1 else ("down" if change_percent < -1 else "stable")

            trends.append(MonthOverMonthTrend(
                metric=metric,
                current_month=current_month_start,
                current_value=current_value,
                previous_month=previous_month_start,
                previous_value=previous_value,
                change_percent=round(change_percent, 2),
                trend_direction=trend_direction,
            ))

        return trends

    async def get_year_over_year_trends(
        self,
        metric: str,
        years: int = 3,
        branch_location: Optional[str] = None,
    ) -> List[YearOverYearTrend]:
        trends = []
        current_year = date.today().year

        for i in range(years - 1):
            year = current_year - i
            previous_year = year - 1

            current_start = date(year, 1, 1)
            current_end = date(year, 12, 31)
            previous_start = date(previous_year, 1, 1)
            previous_end = date(previous_year, 12, 31)

            current_value = await self._get_metric_value(
                metric, current_start, current_end, branch_location
            )
            previous_value = await self._get_metric_value(
                metric, previous_start, previous_end, branch_location
            )

            if previous_value > 0:
                change_percent = ((current_value - previous_value) / previous_value) * 100
            else:
                change_percent = 100 if current_value > 0 else 0

            trend_direction = "up" if change_percent > 1 else ("down" if change_percent < -1 else "stable")

            trends.append(YearOverYearTrend(
                metric=metric,
                current_year=year,
                current_value=current_value,
                previous_year=previous_year,
                previous_value=previous_value,
                change_percent=round(change_percent, 2),
                trend_direction=trend_direction,
            ))

        return trends

    async def _get_metric_value(
        self,
        metric: str,
        start_date: date,
        end_date: date,
        branch_location: Optional[str] = None,
    ) -> float:
        start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        end_dt = datetime.combine(end_date, datetime.max.time()).replace(tzinfo=timezone.utc)

        if metric == "checkouts":
            result = await self.db.execute(
                select(func.count(Checkout.id)).where(
                    Checkout.checked_out_at >= start_dt,
                    Checkout.checked_out_at <= end_dt,
                )
            )
            return float(result.scalar() or 0)

        elif metric == "visits":
            result = await self.db.execute(
                select(func.sum(VisitCount.door_count)).where(
                    VisitCount.count_date >= start_date,
                    VisitCount.count_date <= end_date,
                )
            )
            return float(result.scalar() or 0)

        elif metric == "registrations":
            result = await self.db.execute(
                select(func.count(User.id)).where(
                    User.role.in_([UserRole.PATRON, UserRole.CHILD]),
                    User.created_at >= start_dt,
                    User.created_at <= end_dt,
                )
            )
            return float(result.scalar() or 0)

        elif metric == "programs":
            result = await self.db.execute(
                select(func.count(Event.id)).where(
                    Event.start_time >= start_dt,
                    Event.start_time <= end_dt,
                )
            )
            return float(result.scalar() or 0)

        elif metric == "attendance":
            result = await self.db.execute(
                select(func.count(EventRegistration.id)).where(
                    EventRegistration.registered_at >= start_dt,
                    EventRegistration.registered_at <= end_dt,
                )
            )
            return float(result.scalar() or 0)

        elif metric == "reference":
            result = await self.db.execute(
                select(func.count(ReferenceQuestion.id)).where(
                    ReferenceQuestion.asked_at >= start_dt,
                    ReferenceQuestion.asked_at <= end_dt,
                )
            )
            return float(result.scalar() or 0)

        else:
            logger.warning(f"Unknown metric: {metric}")
            return 0.0

    # ========================================================================
    # IMLS Survey Data
    # ========================================================================

    async def generate_imls_survey_data(
        self,
        fiscal_year: int,
        branch_location: Optional[str] = None,
        branch_id: Optional[int] = None,
    ) -> IMLSSurveyData:
        # Resolve missing side via canonical map.
        if branch_id is None and branch_location is not None:
            branch_id = await self._resolve_branch_id_from_label(branch_location)
        elif branch_id is not None and branch_location is None:
            branch_location = await self._resolve_branch_label_from_id(branch_id)

        # Get settings for library identifiers (prefer branch_id).
        if branch_id is not None:
            settings_q = select(UsageStatisticsSettings).where(
                UsageStatisticsSettings.is_active == True,
                UsageStatisticsSettings.branch_id == branch_id,
            )
        else:
            settings_q = select(UsageStatisticsSettings).where(
                UsageStatisticsSettings.is_active == True,
                UsageStatisticsSettings.branch_location == branch_location,
            )
        settings_result = await self.db.execute(settings_q)
        settings = settings_result.scalar_one_or_none()

        # Determine fiscal year dates (default July-June)
        fy_start_month = settings.fiscal_year_start_month if settings else 7
        if fy_start_month <= 6:
            fy_start = date(fiscal_year, fy_start_month, 1)
            fy_end = date(fiscal_year + 1, fy_start_month, 1) - timedelta(days=1)
        else:
            fy_start = date(fiscal_year - 1, fy_start_month, 1)
            fy_end = date(fiscal_year, fy_start_month, 1) - timedelta(days=1)

        # Get all summaries
        circulation = await self.get_circulation_summary(fy_start, fy_end, "yearly", branch_location)
        collection = await self.get_collection_summary(fy_end, branch_location)
        patrons = await self.get_patron_summary(fy_start, fy_end, "yearly", branch_location)
        programs = await self.get_program_summary(fy_start, fy_end, "yearly", branch_location)
        reference = await self.get_reference_summary(fy_start, fy_end, "yearly", branch_location)
        visits = await self.get_visit_summary(fy_start, fy_end, "yearly", branch_location)

        return IMLSSurveyData(
            fiscal_year=fiscal_year,
            library_fscs_id=settings.imls_library_id if settings else "",
            service_area_population=settings.legal_service_area_population if settings else 0,

            # Collection
            print_collection=collection.items_by_format.get("book", 0),
            ebook_collection=collection.items_by_format.get("ebook", 0),
            audio_physical=collection.items_by_format.get("audiobook", 0),
            audio_downloadable=collection.items_by_format.get("eaudiobook", 0),
            video_physical=collection.items_by_format.get("dvd", 0) + collection.items_by_format.get("bluray", 0),
            video_downloadable=collection.items_by_format.get("streaming_video", 0),

            # Circulation
            physical_circulation=circulation.total_checkouts,
            electronic_circulation=0,  # Would need e-resource tracking
            total_circulation=circulation.total_checkouts,

            # Programs
            childrens_programs=programs.programs_by_age_group.get("children", 0),
            childrens_program_attendance=programs.attendance_by_age_group.get("children", 0),
            young_adult_programs=programs.programs_by_age_group.get("young_adult", 0),
            young_adult_program_attendance=programs.attendance_by_age_group.get("young_adult", 0),
            total_programs=programs.total_programs,
            total_program_attendance=programs.total_attendance,

            # Reference
            reference_transactions=reference.total_questions,

            # Visits
            library_visits=visits.total_visits,

            # Computer Use
            computer_uses=0,  # Would need computer usage tracking

            # Registered Users
            registered_borrowers=patrons.total_registered,

            # ILL
            items_loaned=circulation.total_ill_transactions // 2,  # Approximate split
            items_borrowed=circulation.total_ill_transactions // 2,

            generated_at=datetime.now(timezone.utc),
        )

    # ========================================================================
    # Peer Comparison
    # ========================================================================

    async def get_peer_comparison(
        self,
        data_year: int,
    ) -> List[PeerComparisonResult]:
        # Get our library
        our_result = await self.db.execute(
            select(PeerComparisonLibrary).where(
                PeerComparisonLibrary.is_our_library == True,
                PeerComparisonLibrary.is_active == True,
            )
        )
        our_library = our_result.scalar_one_or_none()

        if not our_library:
            return []

        # Get our data
        our_data_result = await self.db.execute(
            select(PeerComparisonData).where(
                PeerComparisonData.peer_library_id == our_library.id,
                PeerComparisonData.data_year == data_year,
            )
        )
        our_data = our_data_result.scalar_one_or_none()

        if not our_data:
            return []

        # Get peer data
        peer_result = await self.db.execute(
            select(PeerComparisonData)
            .join(PeerComparisonLibrary)
            .where(
                PeerComparisonLibrary.is_our_library == False,
                PeerComparisonLibrary.is_active == True,
                PeerComparisonData.data_year == data_year,
            )
        )
        peer_data = peer_result.scalars().all()

        if not peer_data:
            return []

        # Metrics to compare
        metrics = [
            ("circulation_per_capita", our_data.circulation_per_capita),
            ("visits_per_capita", our_data.visits_per_capita),
            ("expenditure_per_capita", our_data.expenditure_per_capita),
            ("total_circulation", our_data.total_circulation),
            ("total_visits", our_data.total_visits),
            ("total_programs", our_data.total_programs),
            ("reference_transactions", our_data.reference_transactions),
        ]

        results = []
        for metric_name, our_value in metrics:
            peer_values = [
                getattr(p, metric_name)
                for p in peer_data
                if getattr(p, metric_name) is not None
            ]

            if not peer_values:
                continue

            peer_values_float = [float(v) for v in peer_values]
            peer_values_float.sort()

            peer_avg = sum(peer_values_float) / len(peer_values_float)
            peer_median = peer_values_float[len(peer_values_float) // 2]
            peer_min = min(peer_values_float)
            peer_max = max(peer_values_float)

            # Calculate percentile rank
            our_float = float(our_value) if our_value else 0
            below_count = sum(1 for v in peer_values_float if v < our_float)
            percentile = (below_count / len(peer_values_float)) * 100

            results.append(PeerComparisonResult(
                metric_name=metric_name,
                our_value=our_float,
                peer_avg=round(peer_avg, 2),
                peer_median=round(peer_median, 2),
                peer_min=round(peer_min, 2),
                peer_max=round(peer_max, 2),
                percentile_rank=round(percentile, 1),
            ))

        return results
