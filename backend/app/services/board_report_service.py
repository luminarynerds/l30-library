# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import and_, case, func, select, extract
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.board.report import BoardReport, BoardReportTemplate, BoardReportSchedule
from ..models.circulation import Checkout, Hold, HoldStatus
from ..models.fine import Fine, FineStatus
from ..models.user import User, UserRole
from ..models.catalog import CatalogItem
from ..models.inventory import ItemCopy
from .financial_reports_service import FinancialReportsService
from . import umami_client
from ..core.config import get_settings

logger = get_logger(__name__)


class BoardReportService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.financial_service = FinancialReportsService(db)

    async def generate_board_report(
        self,
        start_date: datetime,
        end_date: datetime,
        template_id: Optional[int] = None,
        comparison_enabled: bool = True,
    ) -> Dict[str, Any]:
        logger.info(f"Generating board report: {start_date.date()} to {end_date.date()}")

        try:
            # Run sequentially — shared DB session cannot handle concurrent ops
            circulation_data = await self._get_circulation_metrics(start_date, end_date)
            financial_data = await self._get_financial_metrics(start_date, end_date)
            patron_data = await self._get_patron_metrics(start_date, end_date)
            collection_data = await self._get_collection_metrics(start_date, end_date)
            holds_data = await self._get_holds_metrics(start_date, end_date)
            website_data = await self._get_website_metrics(start_date, end_date)

            report = {
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
                "circulation": circulation_data,
                "financial": financial_data,
                "patrons": patron_data,
                "collection": collection_data,
                "holds": holds_data,
                "website": website_data,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

            # Add comparison data if enabled
            if comparison_enabled:
                comparison_period_days = (end_date - start_date).days
                comparison_start = start_date - timedelta(days=comparison_period_days)
                comparison_end = start_date

                # Run sequentially — shared DB session cannot handle concurrent ops
                circulation_comp = await self._get_circulation_metrics(comparison_start, comparison_end)
                financial_comp = await self._get_financial_metrics(comparison_start, comparison_end)
                patron_comp = await self._get_patron_metrics(comparison_start, comparison_end)
                website_comp = await self._get_website_metrics(comparison_start, comparison_end)

                report["comparison"] = {
                    "period": {
                        "start_date": comparison_start.isoformat(),
                        "end_date": comparison_end.isoformat(),
                    },
                    "circulation": circulation_comp,
                    "financial": financial_comp,
                    "patrons": patron_comp,
                    "website": website_comp,
                }

                # Calculate trends
                report["trends"] = self._calculate_trends(report)

            return report

        except Exception as e:
            logger.error(f"Error generating board report: {e}", exc_info=True)
            raise

    async def _get_circulation_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        query = select(
            func.count(Checkout.id).label("total_checkouts"),
            func.sum(
                case(
                    (Checkout.returned_at.isnot(None), 1),
                    else_=0
                )
            ).label("completed_checkouts"),
            func.avg(
                func.extract("epoch", Checkout.returned_at - Checkout.checked_out_at)
                / 86400
            ).label("avg_checkout_days"),
        ).where(
            and_(
                Checkout.checked_out_at >= start_date,
                Checkout.checked_out_at <= end_date,
            )
        )

        result = await self.db.execute(query)
        row = result.first()

        total = row[0] or 0
        completed = row[1] or 0
        avg_days = float(row[2]) if row[2] else 0.0

        return {
            "total_checkouts": total,
            "completed_checkouts": completed,
            "active_checkouts": total - completed,
            "avg_checkout_duration_days": round(avg_days, 1),
        }

    async def _get_financial_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        # Revenue summary
        revenue_summary = await self.financial_service.get_revenue_summary(
            start_date, end_date, use_cache=False
        )

        # Fine trends
        fine_trends = await self.financial_service.get_fine_trends(
            days=(end_date - start_date).days, use_cache=False
        )

        # Outstanding balances
        outstanding_query = select(
            func.count(Fine.id).label("count"),
            func.sum(Fine.amount - Fine.amount_paid).label("total_balance"),
        ).where(
            and_(
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
                Fine.created_at <= end_date,
            )
        )

        result = await self.db.execute(outstanding_query)
        row = result.first()

        outstanding_count = row[0] or 0
        outstanding_balance = float(row[1] or Decimal("0"))

        return {
            "total_revenue": revenue_summary.get("total_revenue", 0),
            "revenue_by_type": revenue_summary.get("by_type", {}),
            "monthly_breakdown": revenue_summary.get("monthly_breakdown", []),
            "daily_collection_count": len(fine_trends.get("daily_collection", [])),
            "outstanding_fines_count": outstanding_count,
            "outstanding_balance": outstanding_balance,
            "payment_methods": await self.financial_service.get_payment_methods(
                start_date, end_date, use_cache=False
            ),
        }

    async def _get_patron_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        # New patrons
        new_patrons_query = select(func.count(User.id)).where(
            and_(
                User.created_at >= start_date,
                User.created_at <= end_date,
                User.role == UserRole.PATRON,
            )
        )

        result = await self.db.execute(new_patrons_query)
        new_patrons = result.scalar() or 0

        # Active patrons (those who checked out items)
        active_patrons_query = select(func.count(func.distinct(Checkout.user_id))).where(
            and_(
                Checkout.checked_out_at >= start_date,
                Checkout.checked_out_at <= end_date,
            )
        )

        result = await self.db.execute(active_patrons_query)
        active_patrons = result.scalar() or 0

        # Patrons with fines
        fines_query = select(func.count(func.distinct(Fine.user_id))).where(
            and_(
                Fine.created_at >= start_date,
                Fine.created_at <= end_date,
            )
        )

        result = await self.db.execute(fines_query)
        patrons_with_fines = result.scalar() or 0

        return {
            "new_patrons": new_patrons,
            "active_patrons": active_patrons,
            "patrons_with_fines": patrons_with_fines,
        }

    async def _get_collection_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        # Total collection
        total_items_query = select(func.count(ItemCopy.id))
        result = await self.db.execute(total_items_query)
        total_items = result.scalar() or 0

        # Checked out items (have an active/overdue checkout with no return)
        checked_out_query = select(
            func.count(func.distinct(Checkout.item_copy_id))
        ).where(
            and_(
                Checkout.returned_at.is_(None),
                Checkout.status.in_(["active", "overdue"]),
            )
        )
        result = await self.db.execute(checked_out_query)
        checked_out_items = result.scalar() or 0

        # Available items = total minus checked out
        available_items = total_items - checked_out_items

        # Total titles
        titles_query = select(func.count(func.distinct(CatalogItem.id)))
        result = await self.db.execute(titles_query)
        total_titles = result.scalar() or 0

        return {
            "total_items": total_items,
            "total_titles": total_titles,
            "checked_out_items": checked_out_items,
            "available_items": available_items,
            "availability_rate": (
                (available_items / total_items * 100) if total_items > 0 else 0
            ),
        }

    async def _get_holds_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Dict[str, Any]:
        # New holds
        new_holds_query = select(func.count(Hold.id)).where(
            and_(
                Hold.created_at >= start_date,
                Hold.created_at <= end_date,
            )
        )

        result = await self.db.execute(new_holds_query)
        new_holds = result.scalar() or 0

        # Active holds
        active_holds_query = select(func.count(Hold.id)).where(
            and_(
                Hold.status.in_([HoldStatus.pending, HoldStatus.ready]),
                Hold.created_at <= end_date,
            )
        )

        result = await self.db.execute(active_holds_query)
        active_holds = result.scalar() or 0

        return {
            "new_holds": new_holds,
            "active_holds": active_holds,
        }

    async def _get_website_metrics(
        self, start_date: datetime, end_date: datetime
    ) -> Optional[Dict[str, Any]]:
        settings = get_settings()
        if not settings.umami_website_id or not settings.umami_url:
            return None

        try:
            start_ms = int(start_date.timestamp() * 1000)
            end_ms = int(end_date.timestamp() * 1000)
            base = f"/websites/{settings.umami_website_id}"

            stats = await umami_client.umami_get(
                f"{base}/stats", {"startAt": start_ms, "endAt": end_ms}
            )
            pages = await umami_client.umami_get(
                f"{base}/metrics",
                {"startAt": start_ms, "endAt": end_ms, "type": "path", "limit": 10},
            )
            referrers = await umami_client.umami_get(
                f"{base}/metrics",
                {"startAt": start_ms, "endAt": end_ms, "type": "referrer", "limit": 10},
            )
            countries = await umami_client.umami_get(
                f"{base}/metrics",
                {"startAt": start_ms, "endAt": end_ms, "type": "country", "limit": 10},
            )

            def _val(key: str) -> int:
                node = stats.get(key) if isinstance(stats, dict) else None
                if isinstance(node, dict):
                    return int(node.get("value", 0) or 0)
                return 0

            return {
                "pageviews": _val("pageviews"),
                "visitors": _val("visitors"),
                "visits": _val("visits"),
                "bounces": _val("bounces"),
                "top_pages": [
                    {"path": r.get("x"), "views": r.get("y", 0)}
                    for r in (pages or [])
                ][:10],
                "top_referrers": [
                    {"referrer": r.get("x"), "views": r.get("y", 0)}
                    for r in (referrers or [])
                ][:10],
                "top_countries": [
                    {"country": r.get("x"), "visits": r.get("y", 0)}
                    for r in (countries or [])
                ][:10],
            }
        except Exception as e:  # noqa: BLE001 -- analytics fetch is optional: report continues without website metrics
            logger.warning(f"Website metrics unavailable: {e}")
            return None

    def _calculate_trends(self, report: Dict[str, Any]) -> Dict[str, Any]:
        trends = {}

        if "comparison" not in report:
            return trends

        # Circulation trends
        current_checkouts = report["circulation"].get("total_checkouts", 0)
        previous_checkouts = report["comparison"]["circulation"].get("total_checkouts", 0)

        if previous_checkouts > 0:
            trends["checkout_change_percent"] = (
                (current_checkouts - previous_checkouts) / previous_checkouts * 100
            )

        # Financial trends
        current_revenue = report["financial"].get("total_revenue", 0)
        previous_revenue = report["comparison"]["financial"].get("total_revenue", 0)

        if previous_revenue > 0:
            trends["revenue_change_percent"] = (
                (current_revenue - previous_revenue) / previous_revenue * 100
            )

        # Patron trends
        current_active = report["patrons"].get("active_patrons", 0)
        previous_active = report["comparison"]["patrons"].get("active_patrons", 0)

        if previous_active > 0:
            trends["patron_engagement_change_percent"] = (
                (current_active - previous_active) / previous_active * 100
            )

        return trends

    async def save_report_to_db(
        self,
        report_data: Dict[str, Any],
        template_id: Optional[int] = None,
        recipient_emails: Optional[List[str]] = None,
        created_by_id: Optional[int] = None,
    ) -> BoardReport:
        report = BoardReport(
            title=f"Board Report {report_data['period']['start_date']} to {report_data['period']['end_date']}",
            description="Auto-generated monthly board report",
            report_period_start=datetime.fromisoformat(report_data["period"]["start_date"]),
            report_period_end=datetime.fromisoformat(report_data["period"]["end_date"]),
            template_id=template_id,
            status="generated",
            frequency="monthly",
            stats_snapshot=report_data,
            recipient_emails=recipient_emails or [],
            created_by=created_by_id,
        )

        self.db.add(report)
        await self.db.flush()

        logger.info(f"Saved board report to database: {report.id}")
        return report

    async def get_narrative_prompts(
        self, report_data: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        prompts = {
            "circulation": [],
            "financial": [],
            "patrons": [],
            "general": [],
        }

        # Circulation prompts
        checkouts = report_data["circulation"].get("total_checkouts", 0)
        if "comparison" in report_data:
            previous_checkouts = report_data["comparison"]["circulation"].get(
                "total_checkouts", 0
            )
            change_percent = (
                (checkouts - previous_checkouts) / previous_checkouts * 100
                if previous_checkouts > 0
                else 0
            )

            if change_percent > 10:
                prompts["circulation"].append(
                    f"Circulation increased by {change_percent:.1f}% - what factors contributed to this growth?"
                )
            elif change_percent < -10:
                prompts["circulation"].append(
                    f"Circulation decreased by {abs(change_percent):.1f}% - what challenges should we address?"
                )

        availability_rate = report_data["collection"].get("availability_rate", 0)
        if availability_rate < 70:
            prompts["circulation"].append(
                f"Collection availability is at {availability_rate:.1f}% - should we consider additional funding for acquisitions?"
            )

        # Financial prompts
        revenue = report_data["financial"].get("total_revenue", 0)
        outstanding = report_data["financial"].get("outstanding_balance", 0)

        if outstanding > revenue * 2:
            prompts["financial"].append(
                f"Outstanding fines total ${outstanding:,.2f} - should we review fine adjustment policies?"
            )

        prompts["financial"].append(
            f"This period's revenue: ${revenue:,.2f} - does this align with budget expectations?"
        )

        # Patron prompts
        new_patrons = report_data["patrons"].get("new_patrons", 0)
        active_patrons = report_data["patrons"].get("active_patrons", 0)

        prompts["patrons"].append(
            f"Added {new_patrons} new patrons this period - how can we increase patron engagement initiatives?"
        )

        if active_patrons > 0 and new_patrons > 0:
            new_patron_percentage = (new_patrons / active_patrons * 100) if active_patrons else 0
            prompts["patrons"].append(
                f"New patrons represent {new_patron_percentage:.1f}% of active users - are we effectively reaching new communities?"
            )

        # General prompts
        prompts["general"].append(
            "What strategic initiatives should we prioritize for next quarter?"
        )
        prompts["general"].append(
            "Are there any operational challenges that need board attention?"
        )

        return prompts

    async def get_template_by_id(self, template_id: int) -> Optional[BoardReportTemplate]:
        query = select(BoardReportTemplate).where(BoardReportTemplate.id == template_id)
        result = await self.db.execute(query)
        return result.scalars().first()

    async def list_templates(self, active_only: bool = True) -> List[BoardReportTemplate]:
        query = select(BoardReportTemplate)
        if active_only:
            query = query.where(BoardReportTemplate.is_active == True)
        query = query.order_by(BoardReportTemplate.is_default.desc())

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_schedule_next_run(self, schedule_id: int) -> Optional[datetime]:
        query = select(BoardReportSchedule).where(BoardReportSchedule.id == schedule_id)
        result = await self.db.execute(query)
        schedule = result.scalars().first()

        if not schedule or not schedule.is_active:
            return None

        return schedule.next_run_at
