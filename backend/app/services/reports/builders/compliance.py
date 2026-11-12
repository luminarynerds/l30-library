# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, func, select

from ....models.annual_report import AnnualReport
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout, Hold
from ....models.event import Event
from ....models.event_registration import EventRegistration
from ....models.fine import Fine
from ....models.inventory import ItemCopy
from ....models.user import User, UserRole
from ..base import ReportBuilder, ReportFilters, ReportResult

logger = get_logger(__name__)


class ComplianceReportBuilder(ReportBuilder):

    report_name = "compliance"

    async def query_data(self, filters: ReportFilters) -> Dict[str, Any]:
        fy = filters.fiscal_year
        if fy is None:
            fy = datetime.now(timezone.utc).year

        # Standard July-June fiscal year
        fiscal_start = datetime(fy - 1, 7, 1, tzinfo=timezone.utc)
        fiscal_end = datetime(fy, 6, 30, 23, 59, 59, tzinfo=timezone.utc)

        # Run sequentially — shared DB session cannot handle concurrent ops
        circulation = await self._get_circulation(fiscal_start, fiscal_end)
        patrons = await self._get_patrons(fiscal_start, fiscal_end)
        collection = await self._get_collection(fiscal_start, fiscal_end)
        programs = await self._get_programs(fiscal_start, fiscal_end)
        financial = await self._get_financial(fiscal_start, fiscal_end)
        prior_year = await self._get_prior_year(fy - 1)

        return {
            "fiscal_year": fy,
            "fiscal_start": fiscal_start,
            "fiscal_end": fiscal_end,
            "circulation": circulation,
            "patrons": patrons,
            "collection": collection,
            "programs": programs,
            "financial": financial,
            "prior_year": prior_year,
        }

    async def aggregate(self, data: Dict[str, Any], filters: ReportFilters) -> ReportResult:
        circ = data["circulation"]
        patrons = data["patrons"]
        coll = data["collection"]
        programs = data["programs"]
        financial = data["financial"]
        prior = data["prior_year"]

        # Year-over-year calculations
        yoy = {}
        if prior.get("total_checkouts") and prior["total_checkouts"] > 0:
            yoy["checkout_growth"] = round(
                (circ["total_checkouts"] - prior["total_checkouts"])
                / prior["total_checkouts"] * 100, 1
            )
        if prior.get("total_patrons") and prior["total_patrons"] > 0:
            yoy["patron_growth"] = round(
                (patrons["total_registered"] - prior["total_patrons"])
                / prior["total_patrons"] * 100, 1
            )

        # Validate critical fields
        validation_warnings = []
        if circ["total_checkouts"] == 0:
            validation_warnings.append("Total checkouts is zero")
        if patrons["total_registered"] == 0:
            validation_warnings.append("No registered patrons found")

        return ReportResult(
            title=f"Annual Compliance Report - FY{data['fiscal_year']}",
            period_start=data["fiscal_start"],
            period_end=data["fiscal_end"],
            summary={
                "fiscal_year": data["fiscal_year"],
                "total_checkouts": circ["total_checkouts"],
                "total_renewals": circ["total_renewals"],
                "total_holds_placed": circ["total_holds"],
                "total_registered_patrons": patrons["total_registered"],
                "active_patrons": patrons["active_patrons"],
                "new_patrons": patrons["new_patrons"],
                "total_items_owned": coll["total_items"],
                "total_titles": coll["total_titles"],
                "items_added": coll["items_added"],
                "total_programs": programs["total_programs"],
                "total_program_attendance": programs["total_attendance"],
                "fine_revenue": financial["fine_revenue"],
            },
            sections={
                "circulation": circ,
                "patrons": patrons,
                "collection": coll,
                "programs": programs,
                "financial": financial,
                "year_over_year": yoy,
            },
            metadata={
                "state_code": filters.state_code or "NA",
                "validation_warnings": validation_warnings,
                "prior_year_data": prior,
            },
        )

    # -- circulation -------------------------------------------------------

    async def _get_circulation(self, start, end) -> Dict[str, Any]:
        total_q = select(func.count(Checkout.id)).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        ))
        total = (await self.db.execute(total_q)).scalar() or 0

        renewals_q = select(func.coalesce(func.sum(Checkout.renewal_count), 0)).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        ))
        renewals = (await self.db.execute(renewals_q)).scalar() or 0

        holds_q = select(func.count(Hold.id)).where(and_(
            Hold.created_at >= start,
            Hold.created_at <= end,
        ))
        holds = (await self.db.execute(holds_q)).scalar() or 0

        return {
            "total_checkouts": total,
            "total_renewals": int(renewals),
            "total_holds": holds,
        }

    # -- patrons -----------------------------------------------------------

    async def _get_patrons(self, start, end) -> Dict[str, Any]:
        total_q = select(func.count(User.id)).where(
            User.role == UserRole.PATRON
        )
        total = (await self.db.execute(total_q)).scalar() or 0

        active_q = select(func.count(func.distinct(Checkout.user_id))).where(and_(
            Checkout.checked_out_at >= start,
            Checkout.checked_out_at <= end,
        ))
        active = (await self.db.execute(active_q)).scalar() or 0

        new_q = select(func.count(User.id)).where(and_(
            User.created_at >= start,
            User.created_at <= end,
            User.role == UserRole.PATRON,
        ))
        new = (await self.db.execute(new_q)).scalar() or 0

        return {
            "total_registered": total,
            "active_patrons": active,
            "new_patrons": new,
        }

    # -- collection --------------------------------------------------------

    async def _get_collection(self, start, end) -> Dict[str, Any]:
        items_q = select(func.count(ItemCopy.id))
        total_items = (await self.db.execute(items_q)).scalar() or 0

        titles_q = select(func.count(func.distinct(CatalogItem.id)))
        total_titles = (await self.db.execute(titles_q)).scalar() or 0

        added_q = select(func.count(ItemCopy.id)).where(and_(
            ItemCopy.created_at >= start,
            ItemCopy.created_at <= end,
        ))
        added = (await self.db.execute(added_q)).scalar() or 0

        return {
            "total_items": total_items,
            "total_titles": total_titles,
            "items_added": added,
        }

    # -- programs ----------------------------------------------------------

    async def _get_programs(self, start, end) -> Dict[str, Any]:
        programs_q = select(func.count(Event.id)).where(and_(
            Event.start_time >= start,
            Event.start_time <= end,
        ))
        total = (await self.db.execute(programs_q)).scalar() or 0

        attendance_q = select(func.count(EventRegistration.id)).where(and_(
            EventRegistration.registered_at >= start,
            EventRegistration.registered_at <= end,
        ))
        attendance = (await self.db.execute(attendance_q)).scalar() or 0

        return {
            "total_programs": total,
            "total_attendance": attendance,
        }

    # -- financial ---------------------------------------------------------

    async def _get_financial(self, start, end) -> Dict[str, Any]:
        fines_q = select(func.coalesce(func.sum(Fine.amount_paid), 0)).where(and_(
            Fine.paid_at >= start,
            Fine.paid_at <= end,
        ))
        revenue = (await self.db.execute(fines_q)).scalar() or Decimal("0")
        return {"fine_revenue": float(revenue)}

    # -- prior year --------------------------------------------------------

    async def _get_prior_year(self, fiscal_year: int) -> Dict[str, Any]:
        q = select(AnnualReport).where(
            AnnualReport.fiscal_year == fiscal_year
        ).order_by(desc(AnnualReport.generated_at)).limit(1)

        report = (await self.db.execute(q)).scalar()
        if report:
            return {
                "total_checkouts": report.total_checkouts,
                "total_patrons": report.total_registered_patrons,
                "total_programs": report.total_programs_offered,
            }
        return {}
