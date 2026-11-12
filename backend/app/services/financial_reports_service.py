# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import csv
import io
import json
from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Date, and_, cast, func, or_, select, extract
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..models.fine import Fine, FineStatus, FineType, FinePaymentHistory, PaymentMethod
from ..models.user import User
from ..models.circulation import Checkout
from ..models.serial import SerialSubscription, SubscriptionRenewalStatus

logger = get_logger(__name__)


class FinancialReportsCache:

    def __init__(self, ttl_seconds: int = 300):
        self._cache: "OrderedDict[str, Tuple[Any, datetime]]" = OrderedDict()
        self._ttl = ttl_seconds
        self._max_entries = 500
        self._locks: Dict[str, asyncio.Lock] = {}
        self._locks_lock = asyncio.Lock()  # Lock for managing the locks dict

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            value, timestamp = self._cache[key]
            if (datetime.now(timezone.utc) - timestamp).total_seconds() < self._ttl:
                self._cache.move_to_end(key)
                return value
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any) -> None:
        self._cache[key] = (value, datetime.now(timezone.utc))
        self._cache.move_to_end(key)
        self._prune()

    def clear(self) -> None:
        self._cache.clear()

    def _prune(self) -> None:
        now = datetime.now(timezone.utc)
        expired_keys = [
            key
            for key, (_, timestamp) in self._cache.items()
            if (now - timestamp).total_seconds() >= self._ttl
        ]
        for key in expired_keys:
            del self._cache[key]

        while len(self._cache) > self._max_entries:
            removed_key = self._cache.popitem(last=False)[0]
            # Clean up lock for removed entry
            self._locks.pop(removed_key, None)

        # Clean up locks for any expired cache entries
        expired_lock_keys = [k for k in self._locks if k not in self._cache]
        for key in expired_lock_keys:
            del self._locks[key]

    async def _get_lock(self, key: str) -> asyncio.Lock:
        async with self._locks_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()
            return self._locks[key]

    async def get_or_compute(
        self,
        key: str,
        compute_func: Any,
        use_cache: bool = True
    ) -> Any:
        if use_cache:
            cached = self.get(key)
            if cached is not None:
                return cached

        # Acquire per-key lock to prevent stampede
        lock = await self._get_lock(key)
        async with lock:
            # Double-check cache after acquiring lock (another request may have populated it)
            if use_cache:
                cached = self.get(key)
                if cached is not None:
                    return cached

            # Compute the value
            value = await compute_func()

            # Store in cache
            if use_cache:
                self.set(key, value)

            return value


# Global cache instance (5-minute TTL)
_financial_cache = FinancialReportsCache(ttl_seconds=300)


class FinancialReportsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_revenue_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        cache_key = f"revenue_summary_{start_date.date()}_{end_date.date()}"

        async def compute_summary() -> Dict[str, Any]:
            # Query paid fines by type
            fine_query = select(
                Fine.fine_type,
                func.count(Fine.id).label("count"),
                func.sum(Fine.amount_paid).label("total"),
            ).where(
                and_(
                    Fine.status.in_([FineStatus.paid, FineStatus.partial]),
                    Fine.paid_at >= start_date,
                    Fine.paid_at <= end_date,
                )
            ).group_by(Fine.fine_type)

            result = await self.db.execute(fine_query)
            fine_data = result.all()

            # Build revenue summary
            revenue_by_type = {}
            total_revenue = Decimal("0")

            for fine_type, count, total in fine_data:
                amount = total or Decimal("0")
                revenue_by_type[fine_type.value] = {
                    "count": count,
                    "total": float(amount),
                }
                total_revenue += amount

            # Get monthly breakdown
            monthly_query = select(
                extract("year", Fine.paid_at).label("year"),
                extract("month", Fine.paid_at).label("month"),
                func.sum(Fine.amount_paid).label("total"),
            ).where(
                and_(
                    Fine.status.in_([FineStatus.paid, FineStatus.partial]),
                    Fine.paid_at >= start_date,
                    Fine.paid_at <= end_date,
                )
            ).group_by("year", "month").order_by("year", "month")

            result = await self.db.execute(monthly_query)
            monthly_data = result.all()

            monthly_breakdown = [
                {
                    "month": f"{int(year)}-{int(month):02d}",
                    "revenue": float(total or Decimal("0")),
                }
                for year, month, total in monthly_data
            ]

            return {
                "total_revenue": float(total_revenue),
                "by_type": revenue_by_type,
                "monthly_breakdown": monthly_breakdown,
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            }

        return await _financial_cache.get_or_compute(cache_key, compute_summary, use_cache)

    async def get_fine_trends(
        self,
        days: int = 90,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        cache_key = f"fine_trends_{days}"

        async def compute_trends() -> Dict[str, Any]:
            end_date = datetime.now(timezone.utc)
            start_date = end_date - timedelta(days=days)

            # Get total collected in period (from FinePaymentHistory for accuracy)
            collected_query = select(func.sum(FinePaymentHistory.amount)).where(
                FinePaymentHistory.created_at >= start_date,
                FinePaymentHistory.created_at <= end_date,
            )
            result = await self.db.execute(collected_query)
            total_collected = result.scalar() or Decimal("0")

            # Get total outstanding (all unpaid/partial, regardless of date)
            outstanding_query = select(
                func.sum(Fine.amount - Fine.amount_paid)
            ).where(
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
            )
            result = await self.db.execute(outstanding_query)
            total_outstanding = result.scalar() or Decimal("0")

            # Calculate collection rate
            total_assessed = total_collected + total_outstanding
            if total_assessed > 0:
                collection_rate = float(total_collected) / float(total_assessed)
            else:
                collection_rate = 0.0

            # Daily fine collection trend
            paid_date = cast(Fine.paid_at, Date)
            daily_query = select(
                paid_date.label("date"),
                func.count(Fine.id).label("count"),
                func.sum(Fine.amount_paid).label("collected"),
            ).where(
                and_(
                    Fine.status.in_([FineStatus.paid, FineStatus.partial]),
                    Fine.paid_at >= start_date,
                    Fine.paid_at <= end_date,
                )
            ).group_by(paid_date).order_by(paid_date)

            result = await self.db.execute(daily_query)
            daily_data = result.all()

            # Get daily outstanding balance (for each day, sum of unpaid balances on fines created by that date)
            daily_outstanding_data = []
            for rec_date, _, _ in daily_data:
                outstanding_on_date = select(
                    func.sum(Fine.amount - Fine.amount_paid)
                ).where(
                    and_(
                        Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
                        Fine.created_at <= rec_date,
                    )
                )
                result = await self.db.execute(outstanding_on_date)
                outstanding_balance = result.scalar() or Decimal("0")
                daily_outstanding_data.append((rec_date, outstanding_balance))

            # Build daily_data array combining collected and outstanding
            daily_combined = []
            for rec_date, count, collected in daily_data:
                # Find outstanding for this date
                outstanding = Decimal("0")
                for o_date, o_balance in daily_outstanding_data:
                    if o_date == rec_date:
                        outstanding = o_balance
                        break

                daily_combined.append({
                    "date": str(rec_date),
                    "collected": float(collected or Decimal("0")),
                    "outstanding": float(outstanding),
                })

            return {
                "daily_data": daily_combined,
                "total_collected": float(total_collected),
                "total_outstanding": float(total_outstanding),
                "collection_rate": collection_rate,
                "period_days": days,
            }

        return await _financial_cache.get_or_compute(cache_key, compute_trends, use_cache)

    async def get_payment_methods(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        cache_key = f"payment_methods_{start_date.date()}_{end_date.date()}"

        async def compute_payment_methods() -> Dict[str, Any]:
            # Query payment methods
            query = select(
                FinePaymentHistory.payment_method,
                func.count(FinePaymentHistory.id).label("count"),
                func.sum(FinePaymentHistory.amount).label("total"),
            ).where(
                and_(
                    FinePaymentHistory.created_at >= start_date,
                    FinePaymentHistory.created_at <= end_date,
                )
            ).group_by(FinePaymentHistory.payment_method)

            result = await self.db.execute(query)
            data = result.all()

            methods = {}
            total_amount = Decimal("0")

            for method, count, total in data:
                amount = total or Decimal("0")
                methods[method.value] = {
                    "count": count,
                    "total": float(amount),
                    "percentage": 0.0,  # Will be calculated below
                }
                total_amount += amount

            # Calculate percentages
            if total_amount > 0:
                for method in methods.values():
                    method["percentage"] = (method["total"] / float(total_amount)) * 100

            return {
                "payment_methods": methods,
                "total_collected": float(total_amount),
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                },
            }

        return await _financial_cache.get_or_compute(cache_key, compute_payment_methods, use_cache)

    async def get_waived_fines(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        if start_date is None:
            start_date = datetime.now(timezone.utc) - timedelta(days=90)
        if end_date is None:
            end_date = datetime.now(timezone.utc)

        # Query waived fines
        query = select(Fine).where(
            and_(
                Fine.status == FineStatus.waived,
                Fine.waived_at >= start_date,
                Fine.waived_at <= end_date,
            )
        ).order_by(Fine.waived_at.desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        waived_fines = result.scalars().all()

        # Get total count for pagination
        count_query = select(func.count(Fine.id)).where(
            and_(
                Fine.status == FineStatus.waived,
                Fine.waived_at >= start_date,
                Fine.waived_at <= end_date,
            )
        )
        count_result = await self.db.execute(count_query)
        total_count = count_result.scalar() or 0

        # Get waived summary
        summary_query = select(
            func.count(Fine.id).label("count"),
            func.sum(Fine.amount).label("total_waived"),
        ).where(
            and_(
                Fine.status == FineStatus.waived,
                Fine.waived_at >= start_date,
                Fine.waived_at <= end_date,
            )
        )
        summary_result = await self.db.execute(summary_query)
        count, total = summary_result.first() or (0, Decimal("0"))

        waived_details = []
        for fine in waived_fines:
            waived_details.append({
                "id": fine.id,
                "patron_id": fine.user_id,
                "fine_type": str(fine.fine_type),
                "amount": float(fine.amount),
                "waived_at": fine.waived_at.isoformat() if fine.waived_at else None,
                "waived_by_id": fine.waived_by_id,
                "notes": fine.notes,
            })

        return {
            "fines": waived_details,
            "summary": {
                "total_waived_count": count,
                "total_waived_amount": float(total or Decimal("0")),
            },
            "pagination": {
                "limit": limit,
                "offset": offset,
                "total": total_count,
            },
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
        }

    async def get_outstanding_balances(
        self,
        minimum_balance: Decimal = Decimal("0.01"),
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        now = datetime.now(timezone.utc)

        # Get total outstanding balance
        total_query = select(
            func.sum(Fine.amount - Fine.amount_paid)
        ).where(
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
        result = await self.db.execute(total_query)
        total_outstanding = result.scalar() or Decimal("0")

        # Get unpaid/partial fines with patron info (ordered by balance DESC for delinquent accounts)
        query = select(Fine, User).join(User, Fine.user_id == User.id).where(
            and_(
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial]),
                (Fine.amount - Fine.amount_paid) >= minimum_balance,
            )
        ).order_by((Fine.amount - Fine.amount_paid).desc()).limit(limit).offset(offset)

        result = await self.db.execute(query)
        rows = result.all()

        # Categorize by age and build delinquent accounts list
        by_age = {
            "0-30 days": Decimal("0"),
            "31-60 days": Decimal("0"),
            "61-90 days": Decimal("0"),
            "90+ days": Decimal("0"),
        }

        delinquent_accounts = []

        for fine, user in rows:
            balance = fine.amount - fine.amount_paid
            days_old = (now - fine.created_at).days

            # Categorize by age for by_age report
            if days_old <= 30:
                by_age["0-30 days"] += balance
            elif days_old <= 60:
                by_age["31-60 days"] += balance
            elif days_old <= 90:
                by_age["61-90 days"] += balance
            else:
                by_age["90+ days"] += balance

            # Add to delinquent accounts (top accounts by balance)
            delinquent_accounts.append({
                "patron_id": fine.user_id,
                "patron_name": user.full_name,
                "balance": float(balance),
                "days_overdue": days_old,
            })

        # Convert decimal values to float in by_age
        by_age_float = {k: float(v) for k, v in by_age.items()}

        return {
            "total_outstanding": float(total_outstanding),
            "by_age": by_age_float,
            "delinquent_accounts": delinquent_accounts,
        }

    async def get_budget_vs_actual(
        self,
        year: int = None,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        if year is None:
            year = datetime.now(timezone.utc).year

        cache_key = f"budget_vs_actual_{year}"

        async def compute_budget_vs_actual() -> Dict[str, Any]:
            start_date = datetime(year, 1, 1, tzinfo=timezone.utc)
            end_date = datetime(year, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

            # Get monthly actual revenue
            query = select(
                extract("month", Fine.paid_at).label("month"),
                func.sum(Fine.amount_paid).label("total"),
            ).where(
                and_(
                    Fine.status.in_([FineStatus.paid, FineStatus.partial]),
                    Fine.paid_at >= start_date,
                    Fine.paid_at <= end_date,
                )
            ).group_by(extract("month", Fine.paid_at)).order_by(
                extract("month", Fine.paid_at)
            )

            result = await self.db.execute(query)
            monthly_data = result.all()

            # Build monthly breakdown
            monthly_actual = {}
            for month, total in monthly_data:
                month_key = f"month_{int(month):02d}"
                monthly_actual[month_key] = float(total or Decimal("0"))

            # Note: Budget data would come from a Budget table in production
            return {
                "note": "Budget data not configured. Showing actual revenue only.",
                "monthly_actual": monthly_actual,
                "year": year,
            }

        return await _financial_cache.get_or_compute(cache_key, compute_budget_vs_actual, use_cache)

    async def export_to_csv(
        self,
        report_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "revenue_summary":
            data = await self.get_revenue_summary(start_date, end_date, use_cache=False)
            writer.writerow(["Revenue Summary", f"From {data['period']['start_date']} to {data['period']['end_date']}"])
            writer.writerow([])
            writer.writerow(["Category", "Count", "Amount"])
            for category, info in data["by_type"].items():
                writer.writerow([category, info["count"], info["total"]])
            writer.writerow([])
            writer.writerow(["Total Revenue", "", data["total_revenue"]])

        elif report_type == "payment_methods":
            data = await self.get_payment_methods(start_date, end_date, use_cache=False)
            writer.writerow(["Payment Methods Report", f"From {data['period']['start_date']} to {data['period']['end_date']}"])
            writer.writerow([])
            writer.writerow(["Method", "Count", "Amount", "Percentage"])
            for method, info in data["payment_methods"].items():
                writer.writerow([method, info["count"], info["total"], f"{info['percentage']:.1f}%"])
            writer.writerow([])
            writer.writerow(["Total Collected", "", data["total_collected"], "100%"])

        elif report_type == "outstanding_balances":
            data = await self.get_outstanding_balances(limit=10000)
            writer.writerow(["Outstanding Balances Report"])
            writer.writerow([f"Total Outstanding: ${data.get('total_outstanding', 0):.2f}"])
            writer.writerow([])

            # Aging breakdown
            writer.writerow(["Aging Breakdown"])
            writer.writerow(["Period", "Amount"])
            for period, amount in data.get("by_age", {}).items():
                writer.writerow([period, f"${amount:.2f}"])
            writer.writerow([])

            # Delinquent accounts
            writer.writerow(["Delinquent Accounts"])
            writer.writerow(["Patron ID", "Patron Name", "Balance", "Days Overdue"])
            for account in data.get("delinquent_accounts", []):
                writer.writerow([
                    account["patron_id"],
                    account["patron_name"],
                    f"${account['balance']:.2f}",
                    account["days_overdue"],
                ])

        return output.getvalue()

    async def get_fund_overview(self) -> Dict[str, Any]:
        from ..models.acquisition import Fund, FundStatus

        try:
            current_year = datetime.now().year

            result = await self.db.execute(
                select(Fund)
                .where(Fund.fiscal_year == current_year)
                .order_by(Fund.name)
            )
            funds = result.scalars().all()

            fund_list = []
            total_allocated = Decimal("0")
            total_spent = Decimal("0")
            total_encumbered = Decimal("0")

            for f in funds:
                allocated = Decimal(str(f.allocated_amount or 0))
                spent = Decimal(str(f.spent_amount or 0))
                encumbered = Decimal(str(f.encumbered_amount or 0))
                available = allocated - spent - encumbered

                total_allocated += allocated
                total_spent += spent
                total_encumbered += encumbered

                serial_cost_result = await self.db.execute(
                    select(func.coalesce(func.sum(SerialSubscription.cost), 0))
                    .where(
                        SerialSubscription.fund_id == f.id,
                        SerialSubscription.renewal_status.in_([
                            SubscriptionRenewalStatus.active.value,
                            SubscriptionRenewalStatus.pending_renewal.value,
                        ])
                    )
                )
                serial_cost = float(serial_cost_result.scalar() or 0)

                fund_list.append({
                    "id": f.id,
                    "code": f.code,
                    "name": f.name,
                    "description": f.description,
                    "fiscal_year": f.fiscal_year,
                    "allocated_amount": float(allocated),
                    "spent_amount": float(spent),
                    "encumbered_amount": float(encumbered),
                    "serial_subscription_cost": serial_cost,
                    "total_committed": float(encumbered) + serial_cost,
                    "available_amount": float(available),
                    "utilization_percentage": float(
                        ((spent + encumbered) / allocated * 100) if allocated > 0 else 0
                    ),
                    "status": str(f.status) if f.status else "active",
                })

            total_available = total_allocated - total_spent - total_encumbered

            return {
                "fiscal_year": current_year,
                "funds": fund_list,
                "summary": {
                    "total_funds": len(fund_list),
                    "total_allocated": float(total_allocated),
                    "total_spent": float(total_spent),
                    "total_encumbered": float(total_encumbered),
                    "total_available": float(total_available),
                    "overall_utilization": float(
                        ((total_spent + total_encumbered) / total_allocated * 100)
                        if total_allocated > 0 else 0
                    ),
                },
            }
        except Exception as e:
            logger.error(f"Error getting fund overview: {e}")
            raise

    async def get_acquisition_spending(self, year: Optional[int] = None) -> Dict[str, Any]:
        from ..models.acquisition import (
            Fund, PurchaseOrder, PurchaseOrderItem, Vendor, PurchaseOrderStatus
        )

        try:
            target_year = year or datetime.now().year

            # Top vendors by spending
            vendor_query = (
                select(
                    Vendor.name,
                    func.sum(PurchaseOrder.total_amount).label("total_spent"),
                    func.count(PurchaseOrder.id).label("order_count"),
                )
                .join(PurchaseOrder, PurchaseOrder.vendor_id == Vendor.id)
                .where(extract("year", PurchaseOrder.order_date) == target_year)
                .where(PurchaseOrder.status.notin_([
                    PurchaseOrderStatus.DRAFT,
                    PurchaseOrderStatus.REJECTED,
                    PurchaseOrderStatus.CANCELLED,
                ]))
                .group_by(Vendor.name)
                .order_by(func.sum(PurchaseOrder.total_amount).desc())
                .limit(10)
            )
            vendor_result = await self.db.execute(vendor_query)
            top_vendors = [
                {
                    "vendor_name": row.name,
                    "total_spent": float(row.total_spent or 0),
                    "order_count": row.order_count,
                }
                for row in vendor_result
            ]

            # Monthly spending trends
            monthly_query = (
                select(
                    extract("month", PurchaseOrder.order_date).label("month"),
                    func.sum(PurchaseOrder.total_amount).label("total_spent"),
                    func.count(PurchaseOrder.id).label("order_count"),
                )
                .where(extract("year", PurchaseOrder.order_date) == target_year)
                .where(PurchaseOrder.status.notin_([
                    PurchaseOrderStatus.DRAFT,
                    PurchaseOrderStatus.REJECTED,
                    PurchaseOrderStatus.CANCELLED,
                ]))
                .group_by(extract("month", PurchaseOrder.order_date))
                .order_by(extract("month", PurchaseOrder.order_date))
            )
            monthly_result = await self.db.execute(monthly_query)
            monthly_trends = [
                {
                    "month": int(row.month),
                    "total_spent": float(row.total_spent or 0),
                    "order_count": row.order_count,
                }
                for row in monthly_result
            ]

            # Spending by fund (as proxy for category)
            fund_query = (
                select(
                    Fund.name,
                    Fund.allocated_amount,
                    func.sum(PurchaseOrder.total_amount).label("total_spent"),
                    func.count(PurchaseOrder.id).label("order_count"),
                )
                .join(PurchaseOrder, PurchaseOrder.fund_id == Fund.id)
                .where(extract("year", PurchaseOrder.order_date) == target_year)
                .where(PurchaseOrder.status.notin_([
                    PurchaseOrderStatus.DRAFT,
                    PurchaseOrderStatus.REJECTED,
                    PurchaseOrderStatus.CANCELLED,
                ]))
                .group_by(Fund.name, Fund.allocated_amount)
                .order_by(func.sum(PurchaseOrder.total_amount).desc())
            )
            fund_result = await self.db.execute(fund_query)
            spending_by_fund = [
                {
                    "fund_name": row.name,
                    "allocated": float(row.allocated_amount or 0),
                    "spent": float(row.total_spent or 0),
                    "order_count": row.order_count,
                    "utilization_percentage": float(
                        (row.total_spent / row.allocated_amount * 100)
                        if row.allocated_amount and row.allocated_amount > 0
                        else 0
                    ),
                }
                for row in fund_result
            ]

            # Overall totals
            total_spent = sum(v["total_spent"] for v in top_vendors)
            total_orders = sum(v["order_count"] for v in top_vendors)

            # Serial subscription annual cost
            serial_query = select(
                func.coalesce(func.sum(SerialSubscription.cost), 0)
            ).where(
                SerialSubscription.renewal_status.in_([
                    SubscriptionRenewalStatus.active.value,
                    SubscriptionRenewalStatus.pending_renewal.value,
                ])
            )
            serial_result = await self.db.execute(serial_query)
            serial_subscription_total = float(serial_result.scalar() or 0)

            return {
                "year": target_year,
                "top_vendors": top_vendors,
                "monthly_trends": monthly_trends,
                "spending_by_fund": spending_by_fund,
                "summary": {
                    "total_spent": total_spent,
                    "total_orders": total_orders,
                    "average_order_value": (
                        total_spent / total_orders if total_orders > 0 else 0
                    ),
                    "serial_subscription_total": serial_subscription_total,
                    "total_committed": total_spent + serial_subscription_total,
                },
            }
        except Exception as e:
            logger.error(f"Error getting acquisition spending: {e}")
            raise

    async def get_financial_health_metrics(self) -> Dict[str, Any]:
        try:
            # Get current financial data
            await self.get_revenue_summary(None, None, use_cache=True)
            trends = await self.get_fine_trends(90, use_cache=True)
            balances = await self.get_outstanding_balances(Decimal("0.01"))

            total_collected = trends.get("total_collected", 0)
            total_outstanding = trends.get("total_outstanding", 0)
            total_receivable = total_collected + total_outstanding

            # Calculate health metrics
            collection_rate = (
                (total_collected / total_receivable * 100)
                if total_receivable > 0
                else 0
            )
            days_outstanding = 30 if collection_rate > 80 else 60 if collection_rate > 60 else 90

            return {
                "collection_effectiveness": {
                    "rate": collection_rate,
                    "status": (
                        "Excellent" if collection_rate >= 90
                        else "Good" if collection_rate >= 80
                        else "Fair" if collection_rate >= 60
                        else "Poor"
                    ),
                },
                "days_sales_outstanding": days_outstanding,
                "cash_flow_status": {
                    "collected": total_collected,
                    "outstanding": total_outstanding,
                    "receivables": total_receivable,
                },
                "liquidity_indicators": {
                    "current_ratio": (total_collected / max(total_outstanding, 1)),
                    "quick_ratio": (total_collected / max(total_outstanding * 0.8, 1)),
                },
                "delinquency_status": {
                    "accounts_30_days": len([
                        a for a in balances.get("delinquent_accounts", [])
                        if a.get("days_overdue", 0) <= 30
                    ]),
                    "accounts_60_days": len([
                        a for a in balances.get("delinquent_accounts", [])
                        if 30 < a.get("days_overdue", 0) <= 60
                    ]),
                    "accounts_90_plus_days": len([
                        a for a in balances.get("delinquent_accounts", [])
                        if a.get("days_overdue", 0) > 90
                    ]),
                },
                "overall_health_score": (
                    (collection_rate / 100) * 0.5 +
                    (1 - min(total_outstanding / max(total_receivable, 1), 1)) * 0.3 +
                    min(total_collected / 50000, 1) * 0.2
                ) * 100,
            }
        except Exception as e:  # noqa: BLE001 -- report aggregation boundary: degrade to zeros rather than crash dashboard
            logger.error(f"Error getting financial health metrics: {e}")
            return {
                "collection_effectiveness": {"rate": 0, "status": "Unknown"},
                "days_sales_outstanding": 0,
                "cash_flow_status": {"collected": 0, "outstanding": 0, "receivables": 0},
                "liquidity_indicators": {"current_ratio": 0, "quick_ratio": 0},
                "delinquency_status": {
                    "accounts_30_days": 0,
                    "accounts_60_days": 0,
                    "accounts_90_plus_days": 0,
                },
                "overall_health_score": 0,
            }

    async def generate_monthly_report(self, year: int, month: int) -> str:
        try:
            # Create a unique report ID based on year-month
            report_id = f"{year}-{month:02d}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

            # Generate report data
            report_data = {
                "report_id": report_id,
                "year": year,
                "month": month,
                "generated_date": datetime.now(timezone.utc).isoformat(),
                "revenue_summary": await self.get_revenue_summary(None, None, use_cache=False),
                "fine_trends": await self.get_fine_trends(90, use_cache=False),
                "payment_methods": await self.get_payment_methods(None, None, use_cache=False),
                "outstanding_balances": await self.get_outstanding_balances(Decimal("0.01")),
                "budget_vs_actual": await self.get_budget_vs_actual(year, use_cache=False),
                "personnel_summary": await self._build_personnel_summary(year, month),
                "financial_health": await self.get_financial_health_metrics(),
            }

            # Store report (placeholder - would need database storage implementation)
            _financial_cache.set(f"report_{report_id}", report_data)

            logger.info(f"Generated monthly report {report_id}")
            return report_id
        except Exception as e:
            logger.error(f"Error generating monthly report: {e}")
            raise

    async def list_monthly_reports(
        self, year: Optional[int] = None, limit: int = 12, offset: int = 0
    ) -> List[Dict[str, Any]]:
        reports = []

        # Gather reports from in-memory cache (generated via generate_monthly_report)
        for key, (value, timestamp) in list(_financial_cache._cache.items()):
            if not key.startswith("report_"):
                continue
            report_data = value
            if not isinstance(report_data, dict):
                continue
            report_year = report_data.get("year")
            if year is not None and report_year != year:
                continue
            reports.append({
                "report_id": report_data.get("report_id", key.replace("report_", "")),
                "year": report_year,
                "month": report_data.get("month"),
                "generated_date": report_data.get("generated_date"),
                "source": "cache",
            })

        # Also check BoardReport table for persisted reports
        try:
            from ..models.board.report import BoardReport

            query = select(BoardReport).where(
                BoardReport.frequency == "monthly"
            )
            if year is not None:
                query = query.where(
                    extract("year", BoardReport.report_period_start) == year
                )
            query = query.order_by(BoardReport.report_period_start.desc())

            result = await self.db.execute(query)
            db_reports = result.scalars().all()

            for r in db_reports:
                reports.append({
                    "report_id": str(r.id),
                    "year": r.report_period_start.year if r.report_period_start else None,
                    "month": r.report_period_start.month if r.report_period_start else None,
                    "generated_date": r.generated_at.isoformat() if r.generated_at else None,
                    "title": r.title,
                    "status": r.status,
                    "source": "database",
                })
        except SQLAlchemyError as e:
            logger.warning(f"Could not query BoardReport table: {e}")

        # Sort by generated_date descending, apply pagination
        reports.sort(key=lambda r: r.get("generated_date") or "", reverse=True)
        return reports[offset:offset + limit]

    async def get_monthly_report(self, report_id: str, format: str = "pdf") -> Any:
        try:
            # Retrieve report from cache/database
            report_data = _financial_cache.get(f"report_{report_id}")

            if not report_data:
                raise ValueError(f"Report {report_id} not found")

            if format == "json":
                return report_data

            elif format == "pdf":
                # Generate PDF (placeholder - would use ReportLab)
                return self._generate_monthly_report_pdf(report_data)

            elif format == "csv":
                # Generate CSV
                return self._generate_monthly_report_csv(report_data)

            else:
                raise ValueError(f"Invalid format: {format}")

        except Exception as e:
            logger.error(f"Error getting monthly report: {e}")
            raise

    async def _get_volunteer_hours_for_period(self, start: date, end: date) -> float:
        from sqlalchemy import select, func
        from ..models.volunteer import VolunteerShift
        result = await self.db.execute(
            select(func.coalesce(func.sum(VolunteerShift.actual_hours), 0))
            .where(VolunteerShift.shift_date.between(start, end))
        )
        return float(result.scalar() or 0)

    async def _build_personnel_summary(self, year: int, month: int) -> dict:
        from datetime import date, timedelta
        from decimal import Decimal
        from sqlalchemy import select, and_
        from dateutil.relativedelta import relativedelta
        from ..models.fair_scheduling import PayrollRecord
        from ..models.user import User, UserRole
        from ..models.multi_branch import SystemSettings

        period_start = date(year, month, 1)
        period_end = (period_start + relativedelta(months=1)) - timedelta(days=1)

        result = await self.db.execute(
            select(PayrollRecord, User.role)
            .join(User, User.id == PayrollRecord.staff_id)
            .where(and_(
                PayrollRecord.pay_period_start >= period_start,
                PayrollRecord.pay_period_end <= period_end,
            ))
        )
        rows = result.all()

        def row_pay(r):
            return float((r.regular_pay or 0) + (r.overtime_pay or 0) + (r.holiday_pay or 0)
                         + (r.weekend_differential_pay or 0) + (r.evening_differential_pay or 0))

        def row_hours(r):
            return float((r.regular_hours or 0) + (r.overtime_hours or 0) + (r.holiday_hours or 0))

        total_hours = sum(row_hours(r) for r, _ in rows)
        total_pay = sum(row_pay(r) for r, _ in rows)

        by_role = {"librarians": {"hours": 0.0, "pay": 0.0},
                   "other_staff": {"hours": 0.0, "pay": 0.0}}
        for r, role in rows:
            bucket = "librarians" if role == UserRole.STAFF else "other_staff"
            by_role[bucket]["hours"] += row_hours(r)
            by_role[bucket]["pay"] += row_pay(r)

        by_type = {
            "regular": {"hours": sum(float(r.regular_hours or 0) for r, _ in rows),
                        "pay": sum(float(r.regular_pay or 0) for r, _ in rows)},
            "overtime": {"hours": sum(float(r.overtime_hours or 0) for r, _ in rows),
                         "pay": sum(float(r.overtime_pay or 0) for r, _ in rows)},
        }

        volunteer_hours = await self._get_volunteer_hours_for_period(period_start, period_end)
        settings = (await self.db.execute(
            select(SystemSettings).order_by(SystemSettings.id.desc()).limit(1)
        )).scalar_one_or_none()
        volunteer_rate = (settings.volunteer_hour_value if settings else None) or Decimal("33.49")
        volunteer_value = float(Decimal(str(volunteer_hours)) * volunteer_rate)

        warnings = []
        no_rate_count = sum(1 for r, _ in rows if r.discrepancy_notes and "No pay rate on file" in r.discrepancy_notes)
        if no_rate_count:
            warnings.append(f"{no_rate_count} shift(s) had no pay rate on file -- not included in pay totals")

        return {
            "headline": {"total_pay": total_pay, "total_hours": total_hours},
            "by_role": by_role,
            "by_type": by_type,
            "volunteers": {"hours": volunteer_hours, "estimated_value": volunteer_value, "rate": float(volunteer_rate)},
            "warnings": warnings,
        }

    def _generate_monthly_report_pdf(self, report_data: Dict[str, Any]) -> bytes:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
        )

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontSize=18,
            spaceAfter=6,
        )
        heading_style = ParagraphStyle(
            "SectionHeading",
            parent=styles["Heading2"],
            fontSize=13,
            spaceBefore=12,
            spaceAfter=4,
            textColor=colors.HexColor("#2c4a7c"),
        )
        normal_style = styles["Normal"]

        month_num = report_data.get("month", 0)
        year = report_data.get("year", "")
        try:
            month_name = datetime(int(year), int(month_num), 1).strftime("%B")
        except (ValueError, TypeError):
            month_name = str(month_num)
        generated_date = report_data.get("generated_date", "")

        story = []

        # Title
        story.append(Paragraph("Monthly Financial Report", title_style))
        story.append(Paragraph(f"{month_name} {year}", styles["Heading2"]))
        story.append(Paragraph(f"Generated: {generated_date}", normal_style))
        story.append(Spacer(1, 0.2 * inch))

        table_style_base = TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2c4a7c")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING", (0, 0), (-1, 0), 6),
            ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f5f5f5")),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4fb")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ])

        # Revenue Summary
        revenue = report_data.get("revenue_summary", {})
        story.append(Paragraph("Revenue Summary", heading_style))
        rev_data = [
            ["Metric", "Value"],
            ["Total Revenue", f"${revenue.get('total_revenue', 0):,.2f}"],
            ["Transaction Count", str(revenue.get("count", 0))],
        ]
        rev_table = Table(rev_data, colWidths=[3.5 * inch, 2 * inch])
        rev_table.setStyle(table_style_base)
        story.append(rev_table)
        story.append(Spacer(1, 0.15 * inch))

        # Fine Collection Trends
        trends = report_data.get("fine_trends", {})
        story.append(Paragraph("Fine Collection Trends", heading_style))
        collection_rate = trends.get("collection_rate", 0)
        try:
            collection_rate_pct = f"{float(collection_rate) * 100:.1f}%"
        except (TypeError, ValueError):
            collection_rate_pct = str(collection_rate)
        trend_data = [
            ["Metric", "Value"],
            ["Total Collected", f"${trends.get('total_collected', 0):,.2f}"],
            ["Total Outstanding", f"${trends.get('total_outstanding', 0):,.2f}"],
            ["Collection Rate", collection_rate_pct],
        ]
        trend_table = Table(trend_data, colWidths=[3.5 * inch, 2 * inch])
        trend_table.setStyle(table_style_base)
        story.append(trend_table)
        story.append(Spacer(1, 0.15 * inch))

        # Payment Methods
        methods = report_data.get("payment_methods", {})
        method_list = methods.get("methods", [])
        if method_list:
            story.append(Paragraph("Payment Methods", heading_style))
            pm_data = [["Method", "Count", "Amount"]]
            for m in method_list:
                pm_data.append([
                    str(m.get("method", "")),
                    str(m.get("count", 0)),
                    f"${m.get('amount', 0):,.2f}",
                ])
            pm_table = Table(pm_data, colWidths=[2.5 * inch, 1.5 * inch, 1.5 * inch])
            pm_table.setStyle(table_style_base)
            story.append(pm_table)
            story.append(Spacer(1, 0.15 * inch))

        # Personnel
        personnel = report_data.get("personnel_summary", {})
        if personnel:
            story.append(Paragraph("Personnel", heading_style))
            story.append(Spacer(1, 6))
            headline = personnel["headline"]
            story.append(Paragraph(f"Personnel total: ${headline['total_pay']:,.2f}  ({headline['total_hours']:.1f} hrs)", normal_style))
            story.append(Spacer(1, 6))
            br = personnel["by_role"]
            story.append(Paragraph("By role:", normal_style))
            story.append(Paragraph(f"  Librarians: ${br['librarians']['pay']:,.2f} ({br['librarians']['hours']:.1f} hrs)", normal_style))
            story.append(Paragraph(f"  Other staff: ${br['other_staff']['pay']:,.2f} ({br['other_staff']['hours']:.1f} hrs)", normal_style))
            story.append(Spacer(1, 6))
            bt = personnel["by_type"]
            story.append(Paragraph("By type:", normal_style))
            story.append(Paragraph(f"  Regular: ${bt['regular']['pay']:,.2f} ({bt['regular']['hours']:.1f} hrs)", normal_style))
            story.append(Paragraph(f"  Overtime: ${bt['overtime']['pay']:,.2f} ({bt['overtime']['hours']:.1f} hrs)", normal_style))
            v = personnel["volunteers"]
            story.append(Paragraph(f"Volunteer hours: {v['hours']:.1f} hrs (~${v['estimated_value']:,.2f} at ${v['rate']:.2f}/hr)", normal_style))
            for w in personnel.get("warnings", []):
                story.append(Paragraph(f"WARNING: {w}", normal_style))
            story.append(Spacer(1, 12))

        # Financial Health
        health = report_data.get("financial_health", {})
        story.append(Paragraph("Financial Health", heading_style))
        effectiveness = health.get("collection_effectiveness", {})
        try:
            eff_rate = f"{float(effectiveness.get('rate', 0)):.1f}%"
        except (TypeError, ValueError):
            eff_rate = str(effectiveness.get("rate", 0))
        eff_status = effectiveness.get("status", "Unknown")
        health_data = [
            ["Metric", "Value"],
            ["Collection Effectiveness", f"{eff_rate} ({eff_status})"],
            ["Days Sales Outstanding", str(health.get("days_sales_outstanding", 0))],
            ["Overall Health Score", f"{health.get('overall_health_score', 0):.1f}/100"],
        ]
        health_table = Table(health_data, colWidths=[3.5 * inch, 2 * inch])
        health_table.setStyle(table_style_base)
        story.append(health_table)

        doc.build(story)
        return buffer.getvalue()

    def _generate_monthly_report_csv(self, report_data: Dict[str, Any]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(["Monthly Financial Report"])
        writer.writerow([
            f"Month: {report_data['month']}/{report_data['year']}",
            f"Generated: {report_data['generated_date']}",
        ])
        writer.writerow([])

        # Revenue Summary
        revenue = report_data.get("revenue_summary", {})
        writer.writerow(["REVENUE SUMMARY"])
        writer.writerow(["Total Revenue", revenue.get("total_revenue", 0)])
        writer.writerow(["Count", revenue.get("count", 0)])
        writer.writerow([])

        # Fine Trends
        trends = report_data.get("fine_trends", {})
        writer.writerow(["FINE COLLECTION TRENDS"])
        writer.writerow(["Total Collected", trends.get("total_collected", 0)])
        writer.writerow(["Total Outstanding", trends.get("total_outstanding", 0)])
        writer.writerow(["Collection Rate", f"{trends.get('collection_rate', 0) * 100:.1f}%"])
        writer.writerow([])

        # Payment Methods
        methods = report_data.get("payment_methods", {})
        writer.writerow(["PAYMENT METHODS"])
        if methods.get("methods"):
            writer.writerow(["Method", "Count", "Amount"])
            for method in methods.get("methods", []):
                writer.writerow([
                    method.get("method"),
                    method.get("count"),
                    method.get("amount"),
                ])
        writer.writerow([])

        # Personnel
        personnel = report_data.get("personnel_summary")
        if personnel:
            writer.writerow([])
            writer.writerow(["PERSONNEL"])
            writer.writerow(["Total pay", f"${personnel['headline']['total_pay']:,.2f}", "Total hours", f"{personnel['headline']['total_hours']:.1f}"])
            for role, vals in personnel["by_role"].items():
                writer.writerow([role.title(), f"${vals['pay']:,.2f}", f"{vals['hours']:.1f} hrs"])
            for pt, vals in personnel["by_type"].items():
                writer.writerow([pt.title(), f"${vals['pay']:,.2f}", f"{vals['hours']:.1f} hrs"])
            v = personnel["volunteers"]
            writer.writerow(["Volunteer hours", f"{v['hours']:.1f}", "Estimated value", f"${v['estimated_value']:,.2f}"])
            for w in personnel.get("warnings", []):
                writer.writerow(["WARNING", w])
            writer.writerow([])

        # Financial Health
        health = report_data.get("financial_health", {})
        writer.writerow(["FINANCIAL HEALTH"])
        effectiveness = health.get("collection_effectiveness", {})
        writer.writerow(["Collection Effectiveness", f"{effectiveness.get('rate', 0):.1f}% ({effectiveness.get('status', 'Unknown')})"])
        writer.writerow(["Days Sales Outstanding", health.get("days_sales_outstanding", 0)])
        writer.writerow(["Overall Health Score", f"{health.get('overall_health_score', 0):.1f}/100"])

        return output.getvalue()

    async def clear_cache(self) -> None:
        _financial_cache.clear()
