# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
from app.core.logging import get_logger
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, cast, func, select, extract, desc, String
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models.annual_report import (
    AnnualReport,
    AnnualReportValidationRule,
    AnnualReportHistory,
    ReportStatus,
)
from ..models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ..models.catalog import CatalogItem, ItemType, Audience
from ..models.interlibrary_loan import ILLRequest, ILLRequestType
from ..models.inventory import ItemCopy
from ..models.user import User, PatronStatus, UserRole
from ..models.event import Event
from ..models.event_registration import EventRegistration
from ..models.program import Program, ProgramRegistration, ProgramAudience
from ..models.fine import Fine
from ..models.acquisition import Fund
from ..models.end_of_day import EODSession
from ..models.organization_features import OrganizationFeatures
from ..models.multi_branch import Branch, BranchHours, BranchStatus, BranchType
from ..models.usage_statistics import (
    CirculationStatistics,
    CollectionStatistics,
    PatronStatistics,
    ProgramStatistics,
    ComputerUsageStatistics,
    ReferenceStatistics,
    VisitCount,
    VisitStatistics,
)
from ..core.config import get_settings
from .umami_client import UmamiUnavailable, umami_get

logger = get_logger(__name__)


class AnnualReportService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_annual_report(
        self,
        fiscal_year: int,
        state_code: str,
        library_name: str,
        library_id: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> AnnualReport:
        logger.info(f"Generating annual report for FY{fiscal_year}, {state_code}")

        try:
            # Determine fiscal year dates (standard July-June)
            fiscal_start = date(fiscal_year - 1, 7, 1)
            fiscal_end = date(fiscal_year, 6, 30)

            # For current/future fiscal years, cap end date at today
            # so partial-year data is still captured
            today = date.today()
            if fiscal_end > today:
                fiscal_end = today

            # Run sequentially — shared DB session cannot handle concurrent ops
            circulation_data = await self._get_circulation_data(fiscal_start, fiscal_end)
            ill_data = await self._get_ill_data(fiscal_start, fiscal_end)
            patron_data = await self._get_patron_data(fiscal_start, fiscal_end)
            collection_data = await self._get_collection_data(fiscal_start, fiscal_end)
            program_data = await self._get_program_data(fiscal_start, fiscal_end)
            facility_data = await self._get_facility_data()
            technology_data = await self._get_technology_data(fiscal_start, fiscal_end)
            financial_data = await self._get_financial_data(fiscal_start, fiscal_end)
            staff_data = await self._get_staff_data(fiscal_start, fiscal_end)
            visitor_data = await self._get_visitor_data(fiscal_start, fiscal_end)
            website_traffic = await self._get_website_traffic_data(fiscal_start, fiscal_end)
            prior_year_data = await self._get_prior_year_data(fiscal_year - 2)

            # Merge all data
            report_dict = {
                **circulation_data,
                **ill_data,
                **patron_data,
                **collection_data,
                **program_data,
                **facility_data,
                **technology_data,
                **financial_data,
                **staff_data,
                **visitor_data,
                "additional_metrics": {"website_traffic": website_traffic},
                "data_sources": {
                    "circulation": "circulation_statistics + checkout/hold transactions",
                    "patrons": "patron_statistics + user registrations",
                    "programs": "program_statistics + program registrations",
                    "collection": "collection_statistics + catalog inventory",
                    "financial": "budget funds + fines",
                    "staff": "staff roles + branch operations",
                    "facility": "branch locations + branch hours",
                    "technology": "computer_usage_statistics + branch settings",
                    "visits": "visit_statistics + visit_counts + reference_statistics",
                    "website_traffic": "umami analytics (pageviews, visitors, top pages/referrers/countries)",
                },
                "calculation_notes": "Annual report generated automatically from FY date window with fallback to transactional records when pre-aggregated statistics are unavailable.",
            }

            # Calculate year-over-year growth
            yoy_data = self._calculate_yoy_comparisons(report_dict, prior_year_data)
            report_dict.update(yoy_data)

            # Add prior year data for comparison
            for key, value in prior_year_data.items():
                report_dict[f"prior_year_{key}"] = value

            # Create the report object
            annual_report = AnnualReport(
                fiscal_year=fiscal_year,
                state_code=state_code,
                library_name=library_name,
                library_id=library_id,
                generated_by_id=user_id,
                status=ReportStatus.GENERATED,
                **report_dict,
            )

            self.db.add(annual_report)
            await self.db.flush()
            await self.db.refresh(annual_report)

            logger.info(f"Annual report generated: ID {annual_report.id}")
            return annual_report

        except Exception as e:
            logger.error(f"Error generating annual report: {str(e)}", exc_info=True)
            raise

    # =========================================================================
    # CIRCULATION DATA
    # =========================================================================

    async def _get_circulation_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            period_start = datetime.combine(start_date, datetime.min.time())
            period_end = datetime.combine(end_date, datetime.max.time())

            # Aggregate checkout stats in SQL instead of loading all rows
            checkout_stats_query = select(
                func.count(Checkout.id).label("total_checkouts"),
                func.count(Checkout.id).filter(
                    and_(Checkout.renewal_count.isnot(None), Checkout.renewal_count > 0)
                ).label("total_renewals"),
                func.count(Checkout.id).filter(
                    Checkout.status == CheckoutStatus.returned
                ).label("total_returns"),
            ).where(
                and_(
                    Checkout.checked_out_at >= period_start,
                    Checkout.checked_out_at <= period_end,
                )
            )
            stats_row = (await self.db.execute(checkout_stats_query)).one()
            total_checkouts = stats_row.total_checkouts
            total_renewals = stats_row.total_renewals
            total_returns = stats_row.total_returns

            # Checkouts by item type via SQL GROUP BY
            # cast(item_type, String) required: COALESCE cannot match enum and varchar directly.
            item_type_expr = func.coalesce(cast(CatalogItem.item_type, String), "other")
            type_query = (
                select(
                    item_type_expr.label("item_type"),
                    func.count(Checkout.id).label("count"),
                )
                .join(ItemCopy, Checkout.item_copy_id == ItemCopy.id)
                .join(CatalogItem, ItemCopy.catalog_item_id == CatalogItem.id)
                .where(
                    and_(
                        Checkout.checked_out_at >= period_start,
                        Checkout.checked_out_at <= period_end,
                    )
                )
                .group_by(item_type_expr)
            )
            type_rows = (await self.db.execute(type_query)).all()
            checkouts_by_type = {row.item_type: row.count for row in type_rows} if type_rows else {}

            # Holds statistics via SQL COUNT
            holds_stats_query = select(
                func.count(Hold.id).label("total_placed"),
                func.count(Hold.id).filter(Hold.status == HoldStatus.fulfilled).label("total_filled"),
            ).where(
                and_(
                    Hold.created_at >= period_start,
                    Hold.created_at <= period_end,
                )
            )
            holds_row = (await self.db.execute(holds_stats_query)).one()
            total_holds_placed = holds_row.total_placed
            total_holds_filled = holds_row.total_filled

            # Collection turnover rate (checkouts / items owned)
            count_query = select(func.count(ItemCopy.id))
            result = await self.db.execute(count_query)
            total_items = result.scalar() or 1
            turnover_rate = Decimal(str(total_checkouts / total_items)) if total_items else Decimal("0")

            # PLS total circulation = checkouts + renewals
            total_circulation = (total_checkouts or 0) + (total_renewals or 0)

            # Electronic circulation = ebook checkouts. Join via the legacy
            # Checkout.item_id FK (NOT NULL on every checkout) rather than
            # item_copy_id, which is null on most rows and would undercount.
            elec_query = (
                select(func.count(Checkout.id))
                .join(CatalogItem, Checkout.item_id == CatalogItem.id)
                .where(
                    and_(
                        Checkout.checked_out_at >= period_start,
                        Checkout.checked_out_at <= period_end,
                        CatalogItem.item_type == ItemType.ebook,
                    )
                )
            )
            electronic_circulation = (await self.db.execute(elec_query)).scalar() or 0
            physical_circulation = (total_checkouts or 0) - electronic_circulation

            # Children's circulation = checkouts of items classified audience=children.
            childrens_query = (
                select(func.count(Checkout.id))
                .join(CatalogItem, Checkout.item_id == CatalogItem.id)
                .where(
                    and_(
                        Checkout.checked_out_at >= period_start,
                        Checkout.checked_out_at <= period_end,
                        CatalogItem.audience == Audience.children,
                    )
                )
            )
            childrens_circulation = (await self.db.execute(childrens_query)).scalar() or 0

            return {
                "total_checkouts": total_checkouts,
                "total_renewals": total_renewals,
                "total_returns": total_returns,
                "total_circulation": total_circulation,
                "electronic_circulation": electronic_circulation,
                "physical_circulation": physical_circulation,
                "childrens_circulation": childrens_circulation,
                "checkouts_by_item_type": checkouts_by_type or None,
                "total_holds_placed": total_holds_placed,
                "total_holds_filled": total_holds_filled,
                "collection_turnover_rate": turnover_rate,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting circulation data: {str(e)}")
            return {}

    async def _get_ill_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Interlibrary loan counts by direction (PLS), keyed on completed_at in the FY."""
        try:
            period_start = datetime.combine(start_date, datetime.min.time())
            period_end = datetime.combine(end_date, datetime.max.time())

            def count_for(request_type: ILLRequestType):
                return select(func.count(ILLRequest.id)).where(
                    and_(
                        ILLRequest.request_type == request_type,
                        ILLRequest.completed_at >= period_start,
                        ILLRequest.completed_at <= period_end,
                    )
                )

            loaned = (await self.db.execute(count_for(ILLRequestType.lend))).scalar() or 0
            borrowed = (await self.db.execute(count_for(ILLRequestType.borrow))).scalar() or 0
            return {
                "items_loaned_to_other_libraries": loaned,
                "items_borrowed_from_other_libraries": borrowed,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting ILL data: {str(e)}")
            return {}

    # =========================================================================
    # PATRON DATA
    # =========================================================================

    async def _get_patron_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            # Total registered patrons
            patron_query = select(func.count(User.id)).where(User.patron_status != PatronStatus.BLOCKED)
            result = await self.db.execute(patron_query)
            total_patrons = result.scalar() or 0

            # Active patrons (had checkouts in period)
            active_query = select(func.count(func.distinct(Checkout.user_id))).where(
                and_(
                    Checkout.checked_out_at >= datetime.combine(start_date, datetime.min.time()),
                    Checkout.checked_out_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            result = await self.db.execute(active_query)
            active_patrons = result.scalar() or 0

            # New patrons registered in period
            new_query = select(func.count(User.id)).where(
                and_(
                    User.created_at >= datetime.combine(start_date, datetime.min.time()),
                    User.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            result = await self.db.execute(new_query)
            new_patrons = result.scalar() or 0

            # Demographics by age group. date_of_birth is encrypted at rest, so
            # SQL date math is impossible; select the (auto-decrypted) DOBs and
            # bucket app-side.
            today = date.today()
            dob_rows = (
                await self.db.execute(
                    select(User.date_of_birth).where(
                        and_(
                            User.patron_status != PatronStatus.BLOCKED,
                            User.date_of_birth.isnot(None),
                        )
                    )
                )
            ).all()
            patrons_by_age = {
                "child_0_5": 0, "child_6_12": 0, "teen_13_18": 0,
                "adult": 0, "senior_65": 0,
            }
            for (dob,) in dob_rows:
                if dob is None:
                    continue
                yrs = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
                if yrs < 6:
                    patrons_by_age["child_0_5"] += 1
                elif yrs < 13:
                    patrons_by_age["child_6_12"] += 1
                elif yrs < 19:
                    patrons_by_age["teen_13_18"] += 1
                elif yrs < 65:
                    patrons_by_age["adult"] += 1
                else:
                    patrons_by_age["senior_65"] += 1

            # Resident count via SQL COUNT
            resident_count = total_patrons

            return {
                "total_registered_patrons": total_patrons,
                "active_patrons": active_patrons,
                "new_patrons_registered": new_patrons,
                "patrons_by_age_group": patrons_by_age or None,
                "resident_patrons": resident_count,
                "non_resident_patrons": 0,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting patron data: {str(e)}")
            return {}

    def _categorize_patrons_by_age(self, users: List[User]) -> Dict[str, int]:
        age_groups = {
            "child_0_5": 0,
            "child_6_12": 0,
            "teen_13_18": 0,
            "adult": 0,
            "senior_65": 0,
        }

        for user in users:
            if user.date_of_birth:
                today = date.today()
                age = today.year - user.date_of_birth.year - (
                    (today.month, today.day) < (user.date_of_birth.month, user.date_of_birth.day)
                )

                if age < 6:
                    age_groups["child_0_5"] += 1
                elif age < 13:
                    age_groups["child_6_12"] += 1
                elif age < 19:
                    age_groups["teen_13_18"] += 1
                elif age < 65:
                    age_groups["adult"] += 1
                else:
                    age_groups["senior_65"] += 1

        return age_groups

    # =========================================================================
    # COLLECTION DATA
    # =========================================================================

    async def _get_collection_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            stats_query = (
                select(CollectionStatistics)
                .where(
                    and_(
                        CollectionStatistics.snapshot_date >= start_date,
                        CollectionStatistics.snapshot_date <= end_date,
                    )
                )
                .order_by(desc(CollectionStatistics.snapshot_date))
                .limit(1)
            )
            stats_result = await self.db.execute(stats_query)
            stats = stats_result.scalar()

            if stats:
                return {
                    "total_items_owned": stats.total_items_owned,
                    "total_titles_owned": stats.total_titles_owned,
                    "items_by_format": stats.items_owned_by_format,
                    "items_added_during_year": stats.total_items_added,
                    "items_withdrawn_during_year": stats.total_items_withdrawn,
                    "items_withdrawn_by_reason": stats.items_withdrawn_by_reason,
                    "electronic_titles": stats.electronic_titles,
                    "electronic_databases": stats.electronic_databases,
                    "total_collection_value": stats.total_collection_value,
                }

            # Total items and titles
            items_query = select(func.count(ItemCopy.id))
            result = await self.db.execute(items_query)
            total_items = result.scalar() or 0

            titles_query = select(func.count(func.distinct(CatalogItem.id)))
            result = await self.db.execute(titles_query)
            total_titles = result.scalar() or 0

            # Items by format
            format_query = select(CatalogItem.item_type, func.count(ItemCopy.id)).join(
                ItemCopy, CatalogItem.id == ItemCopy.catalog_item_id
            ).group_by(CatalogItem.item_type)
            result = await self.db.execute(format_query)
            items_by_format = dict(result.all()) or None

            # Items added in period
            added_query = select(func.count(ItemCopy.id)).where(
                and_(
                    ItemCopy.created_at >= datetime.combine(start_date, datetime.min.time()),
                    ItemCopy.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            result = await self.db.execute(added_query)
            items_added = result.scalar() or 0

            # Items withdrawn (assume via lost/damaged tracking)
            # This would need to be tracked in your lifecycle or lost_damaged module
            items_withdrawn = 0

            return {
                "total_items_owned": total_items,
                "total_titles_owned": total_titles,
                "items_by_format": items_by_format,
                "items_added_during_year": items_added,
                "items_withdrawn_during_year": items_withdrawn,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting collection data: {str(e)}")
            return {}

    # =========================================================================
    # PROGRAM DATA
    # =========================================================================

    async def _get_program_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            program_stats_query = (
                select(ProgramStatistics)
                .where(
                    and_(
                        ProgramStatistics.period_start >= start_date,
                        ProgramStatistics.period_end <= end_date,
                    )
                )
                .order_by(desc(ProgramStatistics.period_end))
                .limit(1)
            )
            program_stats_result = await self.db.execute(program_stats_query)
            program_stats = program_stats_result.scalar()

            if program_stats:
                return {
                    "total_programs_offered": program_stats.total_programs_offered,
                    "total_program_attendance": program_stats.total_program_attendance,
                    "avg_attendance_per_program": program_stats.avg_attendance_per_program,
                    "childrens_programs_count": program_stats.childrens_programs_count,
                    "childrens_program_attendance": program_stats.childrens_program_attendance,
                    "young_adult_programs_count": program_stats.young_adult_programs_count,
                    "young_adult_program_attendance": program_stats.young_adult_program_attendance,
                    "adult_programs_count": program_stats.adult_programs_count,
                    "adult_program_attendance": program_stats.adult_program_attendance,
                    "outreach_programs_count": program_stats.outreach_programs_count,
                    "outreach_program_attendance": program_stats.outreach_program_attendance,
                    "virtual_programs_count": program_stats.virtual_programs_count,
                    "virtual_program_attendance": program_stats.virtual_program_attendance,
                    "reading_program_participants": program_stats.reading_program_participants,
                    "reading_program_completions": program_stats.reading_program_completions,
                    "programs_by_audience": program_stats.events_by_age_group,
                    "program_attendance_by_audience": program_stats.attendance_by_age_group,
                }

            # Get all programs in fiscal period
            programs_query = select(Program).where(
                and_(
                    Program.program_date >= start_date,
                    Program.program_date <= end_date,
                )
            )
            result = await self.db.execute(programs_query)
            programs = result.scalars().all()

            # Count total programs
            total_programs = len(programs)

            # Attendance count via SQL — attended registrations for programs HELD
            # in the FY (PLS counts attendance by program date, not registration date).
            attendance_query = (
                select(func.count(ProgramRegistration.id))
                .join(Program, ProgramRegistration.program_id == Program.id)
                .where(
                    and_(
                        Program.program_date >= start_date,
                        Program.program_date <= end_date,
                        ProgramRegistration.attended == True,
                    )
                )
            )
            total_program_attendance = (await self.db.execute(attendance_query)).scalar() or 0

            avg_attendance = (
                Decimal(str(total_program_attendance / total_programs))
                if total_programs > 0
                else Decimal("0")
            )

            # Count programs by audience from already-loaded programs list
            childrens_programs = len([p for p in programs if p.audience == ProgramAudience.CHILDREN])
            young_adult_programs = len([p for p in programs if p.audience == ProgramAudience.TEEN])
            adult_programs = len([p for p in programs if p.audience == ProgramAudience.ADULT])
            senior_programs = len([p for p in programs if p.audience == ProgramAudience.SENIOR])

            # Attendance by audience via SQL JOIN + GROUP BY (avoids N+1 lazy load)
            attendance_by_audience_query = (
                select(
                    Program.audience,
                    func.count(ProgramRegistration.id).label("count"),
                )
                .join(Program, ProgramRegistration.program_id == Program.id)
                .where(
                    and_(
                        ProgramRegistration.created_at >= datetime.combine(start_date, datetime.min.time()),
                        ProgramRegistration.created_at <= datetime.combine(end_date, datetime.max.time()),
                        ProgramRegistration.attended == True,
                    )
                )
                .group_by(Program.audience)
            )
            audience_rows = (await self.db.execute(attendance_by_audience_query)).all()
            audience_map = {row.audience: row.count for row in audience_rows}
            childrens_attendance = audience_map.get(ProgramAudience.CHILDREN, 0)
            teen_attendance = audience_map.get(ProgramAudience.TEEN, 0)
            adult_attendance = audience_map.get(ProgramAudience.ADULT, 0)
            senior_attendance = audience_map.get(ProgramAudience.SENIOR, 0)

            return {
                "total_programs_offered": total_programs,
                "total_program_attendance": total_program_attendance,
                "avg_attendance_per_program": avg_attendance,
                "childrens_programs_count": childrens_programs,
                "childrens_program_attendance": childrens_attendance,
                "young_adult_programs_count": young_adult_programs,
                "young_adult_program_attendance": teen_attendance,
                "adult_programs_count": adult_programs,
                "adult_program_attendance": adult_attendance,
                "programs_by_audience": {
                    "children": childrens_programs,
                    "teen": young_adult_programs,
                    "adult": adult_programs,
                    "senior": senior_programs,
                },
                "program_attendance_by_audience": {
                    "children": childrens_attendance,
                    "teen": teen_attendance,
                    "adult": adult_attendance,
                    "senior": senior_attendance,
                },
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting program data: {str(e)}")
            return {}

    # =========================================================================
    # FACILITY DATA
    # =========================================================================

    async def _get_facility_data(self) -> Dict[str, Any]:
        try:
            active_branches_query = select(Branch).where(Branch.status == BranchStatus.ACTIVE)
            active_branches_result = await self.db.execute(active_branches_query)
            branches = active_branches_result.scalars().all()

            if not branches:
                return {
                    "total_hours_open_per_week": 60,
                    "total_hours_open_per_year": 60 * 52,
                    "days_open_per_week": 6,
                    "building_square_footage": None,
                    "number_of_locations": 1,
                    "has_bookmobile": False,
                }

            branch_ids = [branch.id for branch in branches]
            hours_query = select(BranchHours).where(BranchHours.branch_id.in_(branch_ids))
            hours_result = await self.db.execute(hours_query)
            branch_hours = hours_result.scalars().all()

            weekly_hours = Decimal("0")
            open_days = set()
            for hours in branch_hours:
                if hours.is_closed or not hours.open_time or not hours.close_time:
                    continue
                daily_hours = datetime.combine(date.today(), hours.close_time) - datetime.combine(date.today(), hours.open_time)
                if hours.open_time_2 and hours.close_time_2:
                    daily_hours += datetime.combine(date.today(), hours.close_time_2) - datetime.combine(date.today(), hours.open_time_2)
                weekly_hours += Decimal(str(daily_hours.total_seconds() / 3600))
                open_days.add(hours.day_of_week)

            total_square_footage = sum((branch.square_footage or 0) for branch in branches) or None
            has_bookmobile = any(branch.branch_type == BranchType.BOOKMOBILE for branch in branches)

            return {
                "total_hours_open_per_week": int(weekly_hours) if weekly_hours > 0 else None,
                "total_hours_open_per_year": int(weekly_hours * Decimal("52")) if weekly_hours > 0 else None,
                "days_open_per_week": len(open_days) if open_days else None,
                "building_square_footage": total_square_footage,
                "number_of_locations": len(branches),
                "has_bookmobile": has_bookmobile,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting facility data: {str(e)}")
            return {}

    # =========================================================================
    # TECHNOLOGY DATA
    # =========================================================================

    async def _get_technology_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            usage_query = (
                select(ComputerUsageStatistics)
                .where(
                    and_(
                        ComputerUsageStatistics.period_start >= start_date,
                        ComputerUsageStatistics.period_end <= end_date,
                    )
                )
                .order_by(desc(ComputerUsageStatistics.period_end))
                .limit(1)
            )
            usage_result = await self.db.execute(usage_query)
            usage_stats = usage_result.scalar()

            branch_equipment_query = select(Branch).where(Branch.status == BranchStatus.ACTIVE)
            branch_result = await self.db.execute(branch_equipment_query)
            branches = branch_result.scalars().all()
            public_computer_stations = sum(1 for branch in branches if branch.has_computer_lab) * 10

            return {
                "public_computer_stations": public_computer_stations,
                "public_computer_sessions_per_year": usage_stats.total_sessions if usage_stats else 0,
                "wifi_enabled": True,
                "wifi_sessions": usage_stats.wifi_sessions if usage_stats else 0,
                "technology_equipment": {
                    "computer_labs": sum(1 for branch in branches if branch.has_computer_lab),
                    "self_checkout_locations": sum(1 for branch in branches if branch.has_self_checkout),
                    "makerspaces": sum(1 for branch in branches if branch.has_makerspace),
                } or None,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting technology data: {str(e)}")
            return {}

    # =========================================================================
    # FINANCIAL DATA
    # =========================================================================

    async def _get_financial_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            # Get all fines paid in period
            fines_query = select(func.sum(Fine.amount)).where(
                and_(
                    Fine.created_at >= datetime.combine(start_date, datetime.min.time()),
                    Fine.created_at <= datetime.combine(end_date, datetime.max.time()),
                )
            )
            result = await self.db.execute(fines_query)
            fines_revenue = result.scalar() or Decimal("0")

            # Personnel expenditure is now derived from PayrollRecord pay columns
            # (populated by payroll_integration_service from staff_pay_rates).
            from ..models.fair_scheduling import PayrollRecord

            personnel_q = await self.db.execute(
                select(func.coalesce(func.sum(
                    func.coalesce(PayrollRecord.regular_pay, 0)
                    + func.coalesce(PayrollRecord.overtime_pay, 0)
                    + func.coalesce(PayrollRecord.holiday_pay, 0)
                    + func.coalesce(PayrollRecord.weekend_differential_pay, 0)
                    + func.coalesce(PayrollRecord.evening_differential_pay, 0)
                ), 0))
                .where(PayrollRecord.pay_period_end.between(start_date, end_date))
            )
            personnel_expenditure = personnel_q.scalar() or Decimal("0")

            # GL-sourced fields require manual entry from the audited financial
            # statements — they must NOT be fabricated from budget ratios.
            # Only genuinely transactional values (fines) are kept.
            return {
                "total_operating_revenue": None,
                "total_operating_expenditure": None,
                # Keep only the real fines figure; preserve genuine zero (fines_revenue is
                # already Decimal("0") when no fines exist, so only skip if truly None).
                "revenue_by_source": {"fines": float(fines_revenue)} if fines_revenue is not None else None,
                "expenditure_by_category": None,
                # personnel_expenditure is already Decimal("0") or a real value; return it
                # directly so a genuine zero is not lost to falsy coercion.
                "personnel_expenditure": personnel_expenditure,
                "collection_expenditure": None,
                "technology_expenditure": None,
                "facility_expenditure": None,
                "other_expenditure": None,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting financial data: {str(e)}")
            return {}

    # =========================================================================
    # STAFF DATA
    # =========================================================================

    async def _get_staff_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            from ..models.staff_schedule_fairness import StaffShift
            from ..models.multi_branch import SystemSettings

            settings = (await self.db.execute(
                select(SystemSettings).order_by(SystemSettings.id.desc()).limit(1)
            )).scalar_one_or_none()
            fte_divisor = (settings.fte_annual_hours if settings else None) or 2080

            staff_roles = [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]
            hours_q = await self.db.execute(
                select(User.role, func.coalesce(func.sum(StaffShift.actual_hours), 0))
                .join(StaffShift, StaffShift.staff_id == User.id)
                .where(and_(
                    StaffShift.shift_date.between(start_date, end_date),
                    User.role.in_(staff_roles),
                ))
                .group_by(User.role)
            )
            hours_by_role: dict = {role: float(hours) for role, hours in hours_q.all()}

            librarian_hours = hours_by_role.get(UserRole.STAFF, 0.0)
            other_hours = sum(hours_by_role.get(r, 0.0) for r in (UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR))
            total_hours = librarian_hours + other_hours

            # MLS-credentialed hours — subset of staff, filtered by User.has_mls.
            mls_hours = float((await self.db.execute(
                select(func.coalesce(func.sum(StaffShift.actual_hours), 0))
                .join(User, StaffShift.staff_id == User.id)
                .where(and_(
                    StaffShift.shift_date.between(start_date, end_date),
                    User.role.in_(staff_roles),
                    User.has_mls.is_(True),
                ))
            )).scalar() or 0)

            def fte(h):
                v = (Decimal(str(h)) / Decimal(fte_divisor)).quantize(Decimal("0.01"))
                return v if v > 0 else None

            return {
                "total_staff_fte": fte(total_hours),
                "librarian_fte": fte(librarian_hours),
                "mls_librarian_fte": fte(mls_hours),
                "other_staff_fte": fte(other_hours),
                "staff_by_role": {str(r.value if hasattr(r, "value") else r): h for r, h in hours_by_role.items()} or None,
                "volunteer_hours": await self._get_volunteer_hours(start_date, end_date),
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting staff data: {str(e)}")
            return {}

    async def _get_volunteer_hours(self, start_date: date, end_date: date) -> float:
        try:
            from ..models.volunteer import VolunteerShift, ShiftSignup

            result = await self.db.execute(
                select(func.coalesce(func.sum(ShiftSignup.actual_hours), 0))
                .join(VolunteerShift, VolunteerShift.id == ShiftSignup.shift_id)
                .where(VolunteerShift.shift_date.between(start_date, end_date))
            )
            return float(result.scalar() or 0)
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting volunteer hours: {str(e)}")
            return 0.0

    # =========================================================================
    # VISITOR DATA
    # =========================================================================

    async def _get_visitor_data(self, start_date: date, end_date: date) -> Dict[str, Any]:
        try:
            visit_stats_query = (
                select(VisitStatistics)
                .where(
                    and_(
                        VisitStatistics.period_start >= start_date,
                        VisitStatistics.period_end <= end_date,
                    )
                )
                .order_by(desc(VisitStatistics.period_end))
                .limit(1)
            )
            visit_result = await self.db.execute(visit_stats_query)
            visit_stats = visit_result.scalar()

            reference_query = (
                select(ReferenceStatistics)
                .where(
                    and_(
                        ReferenceStatistics.period_start >= start_date,
                        ReferenceStatistics.period_end <= end_date,
                    )
                )
                .order_by(desc(ReferenceStatistics.period_end))
                .limit(1)
            )
            reference_result = await self.db.execute(reference_query)
            reference_stats = reference_result.scalar()

            if not visit_stats:
                fallback_visits_query = select(func.sum(VisitCount.adjusted_count)).where(
                    and_(VisitCount.count_date >= start_date, VisitCount.count_date <= end_date)
                )
                fallback_result = await self.db.execute(fallback_visits_query)
                total_visits = fallback_result.scalar() or 0
            else:
                total_visits = visit_stats.total_visits

            return {
                "total_library_visits": total_visits,
                "avg_daily_visits": visit_stats.avg_daily_visits if visit_stats else None,
                "visits_per_capita": visit_stats.visits_per_capita if visit_stats else None,
                "reference_questions_answered": reference_stats.total_questions if reference_stats else 0,
                "avg_reference_duration_minutes": reference_stats.avg_duration_minutes if reference_stats else None,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting visitor data: {str(e)}")
            return {}

    # =========================================================================
    # WEBSITE TRAFFIC (UMAMI)
    # =========================================================================

    async def _get_website_traffic_data(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        empty = {
            "available": False,
            "pageviews": None,
            "visitors": None,
            "visits": None,
            "bounces": None,
            "totaltime": None,
            "top_pages": [],
            "top_referrers": [],
            "top_countries": [],
        }

        settings = get_settings()
        if not settings.umami_website_id:
            logger.warning("Umami website ID not configured; website_traffic omitted")
            return empty

        period_start = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
        period_end = datetime.combine(end_date, datetime.max.time(), tzinfo=timezone.utc)
        start_at = int(period_start.timestamp() * 1000)
        end_at = int(period_end.timestamp() * 1000)

        website_id = settings.umami_website_id

        try:
            stats = await umami_get(
                f"/websites/{website_id}/stats",
                {"startAt": start_at, "endAt": end_at},
            )
        except UmamiUnavailable as exc:
            logger.warning("Umami unavailable for annual report stats: %s", exc)
            return empty

        def _val(metric: Any) -> Optional[int]:
            if isinstance(metric, dict):
                v = metric.get("value")
                return int(v) if isinstance(v, (int, float)) else None
            if isinstance(metric, (int, float)):
                return int(metric)
            return None

        async def _metric_rows(metric_type: str) -> List[Dict[str, Any]]:
            try:
                rows = await umami_get(
                    f"/websites/{website_id}/metrics",
                    {
                        "startAt": start_at,
                        "endAt": end_at,
                        "type": metric_type,
                        "limit": 10,
                    },
                )
            except UmamiUnavailable as exc:
                logger.warning(
                    "Umami unavailable for metrics/%s: %s", metric_type, exc
                )
                return []
            if not isinstance(rows, list):
                return []
            normalized: List[Dict[str, Any]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue
                label = row.get("x")
                count = row.get("y")
                if count is None:
                    continue
                try:
                    count_int = int(count)
                except (TypeError, ValueError):
                    continue
                normalized.append({"label": label, "count": count_int})
            return normalized

        top_pages = await _metric_rows("path")
        top_referrers = await _metric_rows("referrer")
        top_countries = await _metric_rows("country")

        return {
            "available": True,
            "pageviews": _val(stats.get("pageviews")),
            "visitors": _val(stats.get("visitors")),
            "visits": _val(stats.get("visits")),
            "bounces": _val(stats.get("bounces")),
            "totaltime": _val(stats.get("totaltime")),
            "top_pages": top_pages,
            "top_referrers": top_referrers,
            "top_countries": top_countries,
        }

    # =========================================================================
    # PRIOR YEAR DATA
    # =========================================================================

    async def _get_prior_year_data(self, fiscal_year: int) -> Dict[str, int]:
        try:
            if fiscal_year < 2000:  # Invalid year
                return {
                    "total_checkouts": None,
                    "total_patrons": None,
                    "total_visits": None,
                    "total_programs": None,
                    "total_expenditure": None,
                }

            # Look for prior year report
            query = select(AnnualReport).where(
                AnnualReport.fiscal_year == fiscal_year
            ).order_by(desc(AnnualReport.generated_at)).limit(1)

            result = await self.db.execute(query)
            prior_report = result.scalar()

            if prior_report:
                return {
                    "total_checkouts": prior_report.total_checkouts,
                    "total_patrons": prior_report.total_registered_patrons,
                    "total_visits": prior_report.total_library_visits,
                    "total_programs": prior_report.total_programs_offered,
                    "total_expenditure": prior_report.total_operating_expenditure,
                }

            return {
                "total_checkouts": None,
                "total_patrons": None,
                "total_visits": None,
                "total_programs": None,
                "total_expenditure": None,
            }
        except Exception as e:  # noqa: BLE001 — report-section boundary — section failure must not crash full annual report
            logger.error(f"Error getting prior year data: {str(e)}")
            return {}

    # =========================================================================
    # YEAR-OVER-YEAR CALCULATIONS
    # =========================================================================

    def _calculate_yoy_comparisons(
        self, current_data: Dict[str, Any], prior_data: Dict[str, Any]
    ) -> Dict[str, Optional[Decimal]]:
        comparisons = {}

        metrics = [
            ("total_checkouts", "checkout_growth_percent"),
            ("total_registered_patrons", "patron_growth_percent"),
            ("total_library_visits", "visit_growth_percent"),
            ("total_programs_offered", "program_growth_percent"),
        ]

        for current_key, growth_key in metrics:
            current_val = current_data.get(current_key)
            prior_val = prior_data.get(current_key.replace("total_", ""))

            if (
                current_val is not None
                and prior_val is not None
                and prior_val != 0
            ):
                growth_pct = Decimal(
                    str((current_val - prior_val) / prior_val * 100)
                )
                comparisons[growth_key] = growth_pct
            else:
                comparisons[growth_key] = None

        return comparisons

    # =========================================================================
    # VALIDATION
    # =========================================================================

    async def validate_report(self, report_id: int, state_code: Optional[str] = None) -> Tuple[bool, List[str]]:
        # Fetch report
        result = await self.db.execute(
            select(AnnualReport).where(AnnualReport.id == report_id)
        )
        report = result.scalar()

        if not report:
            return False, ["Report not found"]

        errors = []
        state = state_code or report.state_code

        # Get validation rules
        rules_query = select(AnnualReportValidationRule).where(
            and_(
                AnnualReportValidationRule.is_active == True,
                (AnnualReportValidationRule.state_code == state) |
                (AnnualReportValidationRule.state_code == None),
            )
        )
        result = await self.db.execute(rules_query)
        rules = result.scalars().all()

        # Apply each rule
        for rule in rules:
            field_value = getattr(report, rule.field_name, None)

            if rule.rule_type == "required" and field_value is None:
                errors.append(rule.error_message)
            elif rule.rule_type == "min_value" and field_value is not None:
                min_val = int(rule.rule_value)
                if field_value < min_val:
                    errors.append(rule.error_message)

        is_valid = len(errors) == 0

        # Update report validation status
        report.is_validated = is_valid
        report.validation_errors = errors if errors else None
        report.validated_at = datetime.now(timezone.utc)

        await self.db.commit()

        return is_valid, errors

    # =========================================================================
    # EXPORT
    # =========================================================================

    async def get_report(self, report_id: int) -> Optional[AnnualReport]:
        result = await self.db.execute(
            select(AnnualReport).where(AnnualReport.id == report_id)
        )
        return result.scalar()

    async def list_reports(
        self, fiscal_year: Optional[int] = None, state_code: Optional[str] = None
    ) -> List[AnnualReport]:
        query = select(AnnualReport)

        if fiscal_year:
            query = query.where(AnnualReport.fiscal_year == fiscal_year)
        if state_code:
            query = query.where(AnnualReport.state_code == state_code)

        query = query.order_by(desc(AnnualReport.generated_at))
        result = await self.db.execute(query)
        return result.scalars().all()
