# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from sqlalchemy import and_, case, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger

logger = get_logger(__name__)

from ..models.catalog import CatalogItem, ItemType
from ..models.fine import Fine, FineStatus, FineType
from ..models.inventory import ItemCopy
from ..models.lost_damaged import (
    LostItemRecord, LostItemStatus, LostItemType,
    DamagedItemRecord, DamagedItemStatus, DamageSeverity,
    ClaimsReturnedDispute, ClaimDisputeStatus
)


@dataclass
class FinancialSummary:
    total_charges: Decimal
    total_collected: Decimal
    total_outstanding: Decimal
    total_waived: Decimal
    total_credits: Decimal
    collection_rate: float  # Percentage collected of total charges
    period_start: datetime
    period_end: datetime


@dataclass
class LostItemFinancialDetail:
    lost_record_id: int
    patron_name: str
    item_title: str
    charge_date: datetime
    charge_amount: Decimal
    amount_paid: Decimal
    amount_waived: Decimal
    balance: Decimal
    status: str
    is_found: bool


@dataclass
class ChargesByType:
    lost_item_charges: Decimal
    damaged_item_charges: Decimal
    processing_fees: Decimal
    total: Decimal


@dataclass
class InventorySummary:
    total_lost: int
    lost_by_patron: int
    lost_in_transit: int
    claims_returned: int
    total_damaged: int
    damaged_repairable: int
    damaged_withdrawn: int
    in_mending: int
    items_found: int
    period_start: datetime
    period_end: datetime


@dataclass
class LostByCategory:
    item_type: str
    count: int
    total_value: Decimal
    percentage_of_total: float


@dataclass
class LostByLocation:
    location: str
    count: int
    total_value: Decimal
    percentage_of_total: float


@dataclass
class TrendData:
    period: str  # e.g., "2024-01", "Week 1"
    lost_count: int
    damaged_count: int
    charges: Decimal
    credits: Decimal
    net: Decimal


@dataclass
class PatronRiskReport:
    patron_id: int
    patron_name: str
    patron_email: Optional[str]
    lost_item_count: int
    damaged_item_count: int
    claims_returned_count: int
    total_charges: Decimal
    outstanding_balance: Decimal
    risk_score: int  # 1-10, higher = more risk


class LostDamagedReportsService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_financial_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        location: Optional[str] = None,
    ) -> FinancialSummary:
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=30)

        # Build base query for fines related to lost/damaged items
        conditions = [
            Fine.fine_type.in_([FineType.lost_item, FineType.damaged_item]),
            Fine.created_at >= start_date,
            Fine.created_at <= end_date,
        ]

        # Get all relevant fines
        result = await self.db.execute(
            select(Fine).where(and_(*conditions))
        )
        fines = result.scalars().all()

        # Calculate totals
        total_charges = Decimal("0.00")
        total_collected = Decimal("0.00")
        total_waived = Decimal("0.00")
        total_credits = Decimal("0.00")

        for fine in fines:
            if fine.amount > 0:
                total_charges += fine.amount
                total_collected += fine.amount_paid or Decimal("0.00")
                if fine.status == FineStatus.waived:
                    total_waived += fine.amount
            else:
                # Negative amounts are credits
                total_credits += abs(fine.amount)

        total_outstanding = total_charges - total_collected - total_waived

        collection_rate = 0.0
        if total_charges > 0:
            collection_rate = float((total_collected / total_charges) * 100)

        return FinancialSummary(
            total_charges=total_charges,
            total_collected=total_collected,
            total_outstanding=total_outstanding,
            total_waived=total_waived,
            total_credits=total_credits,
            collection_rate=round(collection_rate, 2),
            period_start=start_date,
            period_end=end_date
        )

    async def get_charges_by_type(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> ChargesByType:
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=30)

        conditions = [
            Fine.created_at >= start_date,
            Fine.created_at <= end_date,
            Fine.amount > 0,
        ]

        # Get lost item charges
        lost_result = await self.db.execute(
            select(func.coalesce(func.sum(Fine.amount), 0)).where(
                and_(*conditions, Fine.fine_type == FineType.lost_item)
            )
        )
        lost_charges = Decimal(str(lost_result.scalar() or 0))

        # Get damaged item charges
        damaged_result = await self.db.execute(
            select(func.coalesce(func.sum(Fine.amount), 0)).where(
                and_(*conditions, Fine.fine_type == FineType.damaged_item)
            )
        )
        damaged_charges = Decimal(str(damaged_result.scalar() or 0))

        # Get processing fees from lost records
        fee_result = await self.db.execute(
            select(func.coalesce(func.sum(LostItemRecord.processing_fee), 0)).where(
                and_(
                    LostItemRecord.charged_at >= start_date,
                    LostItemRecord.charged_at <= end_date,
                    LostItemRecord.processing_fee != None
                )
            )
        )
        processing_fees = Decimal(str(fee_result.scalar() or 0))

        return ChargesByType(
            lost_item_charges=lost_charges,
            damaged_item_charges=damaged_charges,
            processing_fees=processing_fees,
            total=lost_charges + damaged_charges
        )

    async def get_financial_details(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Tuple[List[LostItemFinancialDetail], int]:
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=30)

        query = select(LostItemRecord).options(
            selectinload(LostItemRecord.patron),
            selectinload(LostItemRecord.catalog_item),
            selectinload(LostItemRecord.fine)
        ).where(
            LostItemRecord.reported_at >= start_date,
            LostItemRecord.reported_at <= end_date,
        )

        if status_filter:
            try:
                status = LostItemStatus(status_filter)
                query = query.where(LostItemRecord.status == status)
            except ValueError:
                logger.warning("Invalid lost item status filter value: %s", status_filter)

        # Get count
        count_query = select(func.count()).select_from(LostItemRecord).where(
            LostItemRecord.reported_at >= start_date,
            LostItemRecord.reported_at <= end_date,
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        query = query.order_by(LostItemRecord.reported_at.desc())
        query = query.limit(limit).offset(offset)
        result = await self.db.execute(query)
        records = result.scalars().all()

        details = []
        for record in records:
            patron_name = f"{record.patron.first_name} {record.patron.last_name}" if record.patron else "Unknown"
            item_title = record.catalog_item.title if record.catalog_item else "Unknown"

            charge_amount = record.replacement_cost or Decimal("0.00")
            amount_paid = Decimal("0.00")
            amount_waived = Decimal("0.00")

            if record.fine:
                charge_amount = record.fine.amount
                amount_paid = record.fine.amount_paid or Decimal("0.00")
                if record.fine.status == FineStatus.waived:
                    amount_waived = record.fine.amount

            details.append(LostItemFinancialDetail(
                lost_record_id=record.id,
                patron_name=patron_name,
                item_title=item_title,
                charge_date=record.charged_at or record.reported_at,
                charge_amount=charge_amount,
                amount_paid=amount_paid,
                amount_waived=amount_waived,
                balance=charge_amount - amount_paid - amount_waived,
                status=str(record.status),
                is_found=record.status == LostItemStatus.FOUND
            ))

        return details, total

    async def get_inventory_summary(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        location: Optional[str] = None,
    ) -> InventorySummary:
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=30)

        base_conditions = [
            LostItemRecord.reported_at >= start_date,
            LostItemRecord.reported_at <= end_date,
        ]

        # Lost items by type
        lost_by_patron = await self._count_lost_items(
            base_conditions + [LostItemRecord.lost_type == LostItemType.LOST_BY_PATRON]
        )
        lost_in_transit = await self._count_lost_items(
            base_conditions + [LostItemRecord.lost_type == LostItemType.LOST_IN_TRANSIT]
        )
        claims_returned = await self._count_lost_items(
            base_conditions + [LostItemRecord.lost_type == LostItemType.CLAIMS_RETURNED]
        )
        items_found = await self._count_lost_items(
            base_conditions + [LostItemRecord.status == LostItemStatus.FOUND]
        )

        total_lost = lost_by_patron + lost_in_transit + claims_returned

        # Damaged items
        damaged_conditions = [
            DamagedItemRecord.reported_at >= start_date,
            DamagedItemRecord.reported_at <= end_date,
        ]

        damaged_repairable = await self._count_damaged_items(
            damaged_conditions + [DamagedItemRecord.status.in_([
                DamagedItemStatus.REPAIRABLE,
                DamagedItemStatus.IN_MENDING,
                DamagedItemStatus.REPAIRED
            ])]
        )
        damaged_withdrawn = await self._count_damaged_items(
            damaged_conditions + [DamagedItemRecord.status == DamagedItemStatus.WITHDRAWN]
        )
        in_mending = await self._count_damaged_items(
            damaged_conditions + [DamagedItemRecord.status == DamagedItemStatus.IN_MENDING]
        )

        total_damaged = damaged_repairable + damaged_withdrawn

        return InventorySummary(
            total_lost=total_lost,
            lost_by_patron=lost_by_patron,
            lost_in_transit=lost_in_transit,
            claims_returned=claims_returned,
            total_damaged=total_damaged,
            damaged_repairable=damaged_repairable,
            damaged_withdrawn=damaged_withdrawn,
            in_mending=in_mending,
            items_found=items_found,
            period_start=start_date,
            period_end=end_date
        )

    async def get_lost_by_category(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LostByCategory]:
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=30)

        query = select(
            CatalogItem.item_type,
            func.count(LostItemRecord.id).label("count"),
            func.coalesce(func.sum(LostItemRecord.replacement_cost), 0).label("total_value")
        ).join(
            LostItemRecord, LostItemRecord.catalog_item_id == CatalogItem.id
        ).where(
            LostItemRecord.reported_at >= start_date,
            LostItemRecord.reported_at <= end_date,
        ).group_by(CatalogItem.item_type)

        result = await self.db.execute(query)
        rows = result.all()

        total_count = sum(r.count for r in rows)
        categories = []

        for row in rows:
            percentage = (row.count / total_count * 100) if total_count > 0 else 0
            categories.append(LostByCategory(
                item_type=str(row.item_type) if row.item_type else "unknown",
                count=row.count,
                total_value=Decimal(str(row.total_value)),
                percentage_of_total=round(percentage, 2)
            ))

        return sorted(categories, key=lambda x: x.count, reverse=True)

    async def get_lost_by_location(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> List[LostByLocation]:
        now = datetime.now(timezone.utc)
        if not end_date:
            end_date = now
        if not start_date:
            start_date = now - timedelta(days=30)

        query = select(
            LostItemRecord.last_known_location,
            func.count(LostItemRecord.id).label("count"),
            func.coalesce(func.sum(LostItemRecord.replacement_cost), 0).label("total_value")
        ).where(
            LostItemRecord.reported_at >= start_date,
            LostItemRecord.reported_at <= end_date,
            LostItemRecord.last_known_location != None,
        ).group_by(LostItemRecord.last_known_location)

        result = await self.db.execute(query)
        rows = result.all()

        total_count = sum(r.count for r in rows)
        locations = []

        for row in rows:
            percentage = (row.count / total_count * 100) if total_count > 0 else 0
            locations.append(LostByLocation(
                location=row.last_known_location or "Unknown",
                count=row.count,
                total_value=Decimal(str(row.total_value)),
                percentage_of_total=round(percentage, 2)
            ))

        return sorted(locations, key=lambda x: x.count, reverse=True)

    async def get_monthly_trend(
        self,
        months: int = 12,
    ) -> List[TrendData]:
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=months * 30)

        # Lost items by month
        lost_query = select(
            extract('year', LostItemRecord.reported_at).label('year'),
            extract('month', LostItemRecord.reported_at).label('month'),
            func.count(LostItemRecord.id).label('count'),
            func.coalesce(func.sum(LostItemRecord.replacement_cost), 0).label('charges')
        ).where(
            LostItemRecord.reported_at >= start_date
        ).group_by(
            extract('year', LostItemRecord.reported_at),
            extract('month', LostItemRecord.reported_at)
        )

        lost_result = await self.db.execute(lost_query)
        lost_data = {(int(r.year), int(r.month)): (r.count, Decimal(str(r.charges)))
                     for r in lost_result.all()}

        # Damaged items by month
        damaged_query = select(
            extract('year', DamagedItemRecord.reported_at).label('year'),
            extract('month', DamagedItemRecord.reported_at).label('month'),
            func.count(DamagedItemRecord.id).label('count'),
            func.coalesce(func.sum(DamagedItemRecord.charge_amount), 0).label('charges')
        ).where(
            DamagedItemRecord.reported_at >= start_date
        ).group_by(
            extract('year', DamagedItemRecord.reported_at),
            extract('month', DamagedItemRecord.reported_at)
        )

        damaged_result = await self.db.execute(damaged_query)
        damaged_data = {(int(r.year), int(r.month)): (r.count, Decimal(str(r.charges)))
                        for r in damaged_result.all()}

        # Credits by month
        credits_query = select(
            extract('year', LostItemRecord.found_at).label('year'),
            extract('month', LostItemRecord.found_at).label('month'),
            func.coalesce(func.sum(LostItemRecord.credit_amount), 0).label('credits')
        ).where(
            LostItemRecord.found_at >= start_date,
            LostItemRecord.status == LostItemStatus.FOUND
        ).group_by(
            extract('year', LostItemRecord.found_at),
            extract('month', LostItemRecord.found_at)
        )

        credits_result = await self.db.execute(credits_query)
        credits_data = {(int(r.year), int(r.month)): Decimal(str(r.credits))
                        for r in credits_result.all()}

        # Build trend data
        trends = []
        current = start_date
        while current <= now:
            year_month = (current.year, current.month)
            lost_count, lost_charges = lost_data.get(year_month, (0, Decimal("0.00")))
            damaged_count, damaged_charges = damaged_data.get(year_month, (0, Decimal("0.00")))
            credits = credits_data.get(year_month, Decimal("0.00"))

            total_charges = lost_charges + damaged_charges

            trends.append(TrendData(
                period=f"{current.year}-{current.month:02d}",
                lost_count=lost_count,
                damaged_count=damaged_count,
                charges=total_charges,
                credits=credits,
                net=total_charges - credits
            ))

            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)

        return trends

    async def get_patron_risk_report(
        self,
        min_incidents: int = 2,
        days_back: int = 365,
        limit: int = 50,
    ) -> List[PatronRiskReport]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

        # Get patrons with lost items
        lost_query = select(
            LostItemRecord.patron_id,
            func.count(LostItemRecord.id).label('lost_count'),
            func.coalesce(func.sum(LostItemRecord.replacement_cost), 0).label('lost_charges')
        ).where(
            LostItemRecord.reported_at >= cutoff,
            LostItemRecord.patron_id != None
        ).group_by(LostItemRecord.patron_id)

        lost_result = await self.db.execute(lost_query)
        lost_data = {r.patron_id: (r.lost_count, Decimal(str(r.lost_charges)))
                     for r in lost_result.all()}

        # Get patrons with damaged items
        damaged_query = select(
            DamagedItemRecord.patron_id,
            func.count(DamagedItemRecord.id).label('damaged_count'),
            func.coalesce(func.sum(DamagedItemRecord.charge_amount), 0).label('damaged_charges')
        ).where(
            DamagedItemRecord.reported_at >= cutoff,
            DamagedItemRecord.patron_id != None,
            DamagedItemRecord.is_patron_responsible == True
        ).group_by(DamagedItemRecord.patron_id)

        damaged_result = await self.db.execute(damaged_query)
        damaged_data = {r.patron_id: (r.damaged_count, Decimal(str(r.damaged_charges)))
                        for r in damaged_result.all()}

        # Get claims returned counts
        claims_query = select(
            ClaimsReturnedDispute.patron_id,
            func.count(ClaimsReturnedDispute.id).label('claims_count')
        ).where(
            ClaimsReturnedDispute.filed_at >= cutoff,
            ClaimsReturnedDispute.patron_id != None
        ).group_by(ClaimsReturnedDispute.patron_id)

        claims_result = await self.db.execute(claims_query)
        claims_data = {r.patron_id: r.claims_count for r in claims_result.all()}

        # Get outstanding balances
        balance_query = select(
            Fine.user_id,
            func.sum(Fine.amount - Fine.amount_paid).label('balance')
        ).where(
            Fine.fine_type.in_([FineType.lost_item, FineType.damaged_item]),
            Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        ).group_by(Fine.user_id)

        balance_result = await self.db.execute(balance_query)
        balance_data = {r.user_id: Decimal(str(r.balance)) for r in balance_result.all()}

        # Combine data and calculate risk scores
        all_patron_ids = set(lost_data.keys()) | set(damaged_data.keys()) | set(claims_data.keys())
        risk_reports = []

        from ..models.user import User
        for patron_id in all_patron_ids:
            lost_count, lost_charges = lost_data.get(patron_id, (0, Decimal("0.00")))
            damaged_count, damaged_charges = damaged_data.get(patron_id, (0, Decimal("0.00")))
            claims_count = claims_data.get(patron_id, 0)
            balance = balance_data.get(patron_id, Decimal("0.00"))

            total_incidents = lost_count + damaged_count

            if total_incidents < min_incidents:
                continue

            # Calculate risk score (1-10)
            risk_score = min(10, (
                lost_count * 2 +
                damaged_count * 2 +
                claims_count +
                (1 if balance > 50 else 0) * 2
            ))

            # Get patron info
            patron_result = await self.db.execute(
                select(User).where(User.id == patron_id)
            )
            patron = patron_result.scalar_one_or_none()

            if patron:
                risk_reports.append(PatronRiskReport(
                    patron_id=patron_id,
                    patron_name=f"{patron.first_name} {patron.last_name}",
                    patron_email=patron.email,
                    lost_item_count=lost_count,
                    damaged_item_count=damaged_count,
                    claims_returned_count=claims_count,
                    total_charges=lost_charges + damaged_charges,
                    outstanding_balance=balance,
                    risk_score=risk_score
                ))

        # Sort by risk score descending
        risk_reports.sort(key=lambda x: x.risk_score, reverse=True)
        return risk_reports[:limit]

    async def _count_lost_items(self, conditions: list) -> int:
        query = select(func.count()).select_from(LostItemRecord).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar() or 0

    async def _count_damaged_items(self, conditions: list) -> int:
        query = select(func.count()).select_from(DamagedItemRecord).where(and_(*conditions))
        result = await self.db.execute(query)
        return result.scalar() or 0
