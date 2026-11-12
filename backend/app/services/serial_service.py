# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, timedelta
from dateutil.relativedelta import relativedelta

from sqlalchemy import func, select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.serial import (
    SerialTitle, SerialPredictionPattern, SerialSubscription,
    SerialIssue, SerialClaimLog,
    SerialIssueStatus, SubscriptionRenewalStatus, PublicationFrequency,
)
from app.models.user import User
from app.models.acquisition import Vendor, Fund
from app.models.multi_branch import Branch

logger = get_logger(__name__)


class SerialService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # -- Titles -------------------------------------------------------------

    async def list_titles(
        self, *, page: int = 1, per_page: int = 20,
        search: str | None = None, is_active: bool | None = None,
        frequency: str | None = None,
    ) -> tuple[list[SerialTitle], int]:
        query = select(SerialTitle)
        count_query = select(func.count(SerialTitle.id))

        if search:
            like = f"%{search}%"
            filt = or_(
                SerialTitle.title.ilike(like),
                SerialTitle.issn_print.ilike(like),
                SerialTitle.publisher.ilike(like),
            )
            query = query.where(filt)
            count_query = count_query.where(filt)

        if is_active is not None:
            query = query.where(SerialTitle.is_active == is_active)
            count_query = count_query.where(SerialTitle.is_active == is_active)

        if frequency:
            query = query.where(SerialTitle.frequency == frequency)
            count_query = count_query.where(SerialTitle.frequency == frequency)

        total = (await self.db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            query.order_by(SerialTitle.title).offset(offset).limit(per_page)
        )
        return list(result.scalars().all()), total

    async def get_title(self, title_id: int) -> SerialTitle | None:
        result = await self.db.execute(
            select(SerialTitle)
            .options(
                selectinload(SerialTitle.subscriptions),
                selectinload(SerialTitle.prediction_patterns),
            )
            .where(SerialTitle.id == title_id)
        )
        return result.scalar_one_or_none()

    async def create_title(self, **kwargs) -> SerialTitle:
        title = SerialTitle(**kwargs)
        self.db.add(title)
        await self.db.flush()
        await self.db.refresh(title)
        return title

    async def update_title(self, title_id: int, updates: dict) -> SerialTitle | None:
        title = await self.get_title(title_id)
        if not title:
            return None
        for key, value in updates.items():
            if value is not None:
                setattr(title, key, value)
        await self.db.flush()
        await self.db.refresh(title)
        return title

    # -- Subscriptions ------------------------------------------------------

    async def list_subscriptions(
        self, *, page: int = 1, per_page: int = 20,
        title_id: int | None = None, renewal_status: str | None = None,
    ) -> tuple[list, int]:
        query = (
            select(
                SerialSubscription,
                SerialTitle.title.label("serial_title_name"),
                Vendor.name.label("vendor_name"),
                Branch.name.label("branch_name"),
            )
            .outerjoin(SerialTitle, SerialTitle.id == SerialSubscription.serial_title_id)
            .outerjoin(Vendor, Vendor.id == SerialSubscription.vendor_id)
            .outerjoin(Branch, Branch.id == SerialSubscription.branch_id)
        )
        count_query = select(func.count(SerialSubscription.id))

        if title_id:
            query = query.where(SerialSubscription.serial_title_id == title_id)
            count_query = count_query.where(SerialSubscription.serial_title_id == title_id)
        if renewal_status:
            query = query.where(SerialSubscription.renewal_status == renewal_status)
            count_query = count_query.where(SerialSubscription.renewal_status == renewal_status)

        total = (await self.db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            query.order_by(SerialSubscription.end_date.desc()).offset(offset).limit(per_page)
        )
        return list(result.all()), total

    async def create_subscription(self, **kwargs) -> SerialSubscription:
        sub = SerialSubscription(**kwargs)
        self.db.add(sub)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    async def update_subscription(self, sub_id: int, updates: dict) -> SerialSubscription | None:
        result = await self.db.execute(
            select(SerialSubscription).where(SerialSubscription.id == sub_id)
        )
        sub = result.scalar_one_or_none()
        if not sub:
            return None
        for key, value in updates.items():
            if value is not None:
                setattr(sub, key, value)
        await self.db.flush()
        await self.db.refresh(sub)
        return sub

    # -- Issues -------------------------------------------------------------

    async def list_issues(
        self, *, page: int = 1, per_page: int = 20,
        title_id: int | None = None, subscription_id: int | None = None,
        status: str | None = None, expected_from: date | None = None,
        expected_to: date | None = None,
    ) -> tuple[list, int]:
        query = (
            select(SerialIssue, SerialTitle.title.label("serial_title_name"))
            .outerjoin(SerialTitle, SerialTitle.id == SerialIssue.serial_title_id)
        )
        count_query = select(func.count(SerialIssue.id))

        conditions = []
        if title_id:
            conditions.append(SerialIssue.serial_title_id == title_id)
        if subscription_id:
            conditions.append(SerialIssue.serial_subscription_id == subscription_id)
        if status:
            conditions.append(SerialIssue.status == status)
        if expected_from:
            conditions.append(SerialIssue.expected_date >= expected_from)
        if expected_to:
            conditions.append(SerialIssue.expected_date <= expected_to)

        if conditions:
            combined = and_(*conditions)
            query = query.where(combined)
            count_query = count_query.where(combined)

        total = (await self.db.execute(count_query)).scalar() or 0
        offset = (page - 1) * per_page
        result = await self.db.execute(
            query.order_by(SerialIssue.expected_date.desc()).offset(offset).limit(per_page)
        )
        return list(result.all()), total

    async def checkin_issues(
        self, issue_ids: list[int], received_by_id: int,
        received_date: date | None = None, notes: str | None = None,
    ) -> list[SerialIssue]:
        recv_date = received_date or date.today()
        result = await self.db.execute(
            select(SerialIssue).where(SerialIssue.id.in_(issue_ids))
        )
        issues = list(result.scalars().all())
        checked_in = []
        for issue in issues:
            issue.status = SerialIssueStatus.received
            issue.received_date = recv_date
            issue.received_by_id = received_by_id
            if notes:
                issue.notes = (issue.notes or "") + f"\n{notes}" if issue.notes else notes
            checked_in.append(issue)
        await self.db.flush()
        return checked_in

    # -- Claims -------------------------------------------------------------

    async def create_claim(
        self, issue_id: int, claimed_by_id: int, claim_type: str = "not_received",
        claim_number: str | None = None, notes: str | None = None,
    ) -> SerialClaimLog:
        # Update issue status
        result = await self.db.execute(
            select(SerialIssue).where(SerialIssue.id == issue_id)
        )
        issue = result.scalar_one_or_none()
        if issue:
            issue.status = SerialIssueStatus.claimed

        claim = SerialClaimLog(
            serial_issue_id=issue_id,
            claim_date=date.today(),
            claim_type=claim_type,
            claim_number=claim_number,
            claimed_by_id=claimed_by_id,
            response=notes,
        )
        self.db.add(claim)
        await self.db.flush()
        await self.db.refresh(claim)
        return claim

    # -- Prediction ---------------------------------------------------------

    async def predict_issues(
        self, title_id: int, subscription_id: int, months_ahead: int = 12,
    ) -> list[SerialIssue]:
        result = await self.db.execute(
            select(SerialPredictionPattern).where(
                SerialPredictionPattern.serial_title_id == title_id,
                SerialPredictionPattern.is_active == True,
            ).order_by(SerialPredictionPattern.effective_from.desc()).limit(1)
        )
        pattern = result.scalar_one_or_none()
        if not pattern:
            return []

        today = date.today()
        end_date = today + relativedelta(months=months_ahead)
        details = pattern.pattern_details or {}
        combined_months = details.get("combined_months", [])
        publication_gaps = details.get("publication_gaps", [])

        dates = self._generate_dates(pattern.frequency, today, end_date, details)

        # Filter out gaps
        filtered_dates = []
        for d in dates:
            in_gap = False
            for gap in publication_gaps:
                gap_from = date.fromisoformat(gap["from"] + "-01")
                gap_to_parts = gap["to"].split("-")
                gap_to = date(int(gap_to_parts[0]), int(gap_to_parts[1]), 28)
                if gap_from <= d <= gap_to:
                    in_gap = True
                    break
            if not in_gap:
                filtered_dates.append(d)

        # Generate issues
        vol = pattern.starting_volume or 1
        num = pattern.starting_number or 1
        npv = pattern.numbers_per_volume or 12
        template = pattern.designation_template or "Vol. {volume}, No. {number}"

        created = []
        for d in filtered_dates:
            # Check for combined months
            is_combined = False
            combined_desig = None
            skip = False
            for cm in combined_months:
                if d.month == cm[1]:
                    skip = True
                    break
                if d.month == cm[0]:
                    is_combined = True
                    combined_desig = f"No. {num}/{num + 1}"
                    break
            if skip:
                continue

            designation = template.format(volume=vol, number=num, year=d.year)

            # Check if issue already exists
            existing = await self.db.execute(
                select(SerialIssue.id).where(
                    SerialIssue.serial_title_id == title_id,
                    SerialIssue.serial_subscription_id == subscription_id,
                    SerialIssue.volume == str(vol),
                    SerialIssue.number == str(num),
                )
            )
            if existing.scalar_one_or_none():
                num += 2 if is_combined else 1
                if num > npv:
                    vol += 1
                    num = 1
                continue

            issue = SerialIssue(
                serial_title_id=title_id,
                serial_subscription_id=subscription_id,
                volume=str(vol),
                number=str(num),
                designation=designation,
                expected_date=d,
                status=SerialIssueStatus.expected,
                is_combined=is_combined,
                combined_designation=combined_desig,
            )
            self.db.add(issue)
            created.append(issue)

            num += 2 if is_combined else 1
            if num > npv:
                vol += 1
                num = 1

        await self.db.flush()
        return created

    def _generate_dates(
        self, frequency: str, start: date, end: date, details: dict,
    ) -> list[date]:
        dates = []
        current = start
        day_of_month = details.get("day_of_month", 1)
        day_of_week = details.get("day_of_week", 0)

        if frequency in ("monthly", "bimonthly"):
            step = 1 if frequency == "monthly" else 2
            current = current.replace(day=min(day_of_month, 28))
            if current < start:
                current += relativedelta(months=step)
            while current <= end:
                dates.append(current)
                current += relativedelta(months=step)

        elif frequency == "weekly":
            current = current + timedelta(days=(day_of_week - current.weekday()) % 7)
            while current <= end:
                dates.append(current)
                current += timedelta(weeks=1)

        elif frequency == "biweekly":
            current = current + timedelta(days=(day_of_week - current.weekday()) % 7)
            while current <= end:
                dates.append(current)
                current += timedelta(weeks=2)

        elif frequency == "quarterly":
            expected_months = details.get("expected_months", [1, 4, 7, 10])
            for yr in range(start.year, end.year + 1):
                for m in expected_months:
                    d = date(yr, m, min(day_of_month, 28))
                    if start <= d <= end:
                        dates.append(d)

        elif frequency == "semimonthly":
            days = details.get("days_of_month", [1, 15])
            current = start.replace(day=1)
            while current <= end:
                for d in days:
                    dt = current.replace(day=min(d, 28))
                    if start <= dt <= end:
                        dates.append(dt)
                current += relativedelta(months=1)

        elif frequency == "semiannual":
            expected_months = details.get("expected_months", [1, 7])
            for yr in range(start.year, end.year + 1):
                for m in expected_months:
                    d = date(yr, m, min(day_of_month, 28))
                    if start <= d <= end:
                        dates.append(d)

        elif frequency == "annual":
            month = details.get("expected_months", [1])[0] if details.get("expected_months") else 1
            for yr in range(start.year, end.year + 1):
                d = date(yr, month, min(day_of_month, 28))
                if start <= d <= end:
                    dates.append(d)

        elif frequency == "irregular":
            expected_months = details.get("expected_months", [])
            for yr in range(start.year, end.year + 1):
                for m in expected_months:
                    d = date(yr, m, min(day_of_month, 28))
                    if start <= d <= end:
                        dates.append(d)

        return sorted(dates)

    # -- Dashboard ----------------------------------------------------------

    async def get_dashboard(self) -> dict:
        today = date.today()
        week_ago = today - timedelta(days=7)
        thirty_days = today + timedelta(days=30)

        stats = (await self.db.execute(select(
            func.count(SerialIssue.id).filter(
                and_(SerialIssue.status == SerialIssueStatus.expected, SerialIssue.expected_date == today)
            ).label("expected_today"),
            func.count(SerialIssue.id).filter(
                and_(SerialIssue.status == SerialIssueStatus.expected, SerialIssue.expected_date < today)
            ).label("overdue_count"),
            func.count(SerialIssue.id).filter(
                SerialIssue.status == SerialIssueStatus.claimed
            ).label("claimed_count"),
            func.count(SerialIssue.id).filter(
                and_(SerialIssue.status == SerialIssueStatus.received, SerialIssue.received_date >= week_ago)
            ).label("received_this_week"),
        ))).one()

        active_titles = (await self.db.execute(
            select(func.count(SerialTitle.id)).where(SerialTitle.is_active == True)
        )).scalar() or 0

        active_subs = (await self.db.execute(
            select(func.count(SerialSubscription.id)).where(
                SerialSubscription.renewal_status == SubscriptionRenewalStatus.active
            )
        )).scalar() or 0

        expiring_subs = (await self.db.execute(
            select(func.count(SerialSubscription.id)).where(
                and_(
                    SerialSubscription.renewal_status == SubscriptionRenewalStatus.active,
                    SerialSubscription.end_date <= thirty_days,
                    SerialSubscription.end_date >= today,
                )
            )
        )).scalar() or 0

        return {
            "expected_today": stats.expected_today,
            "overdue_count": stats.overdue_count,
            "claimed_count": stats.claimed_count,
            "received_this_week": stats.received_this_week,
            "expiring_subscriptions": expiring_subs,
            "total_active_titles": active_titles,
            "total_active_subscriptions": active_subs,
        }

    async def generate_renewal_po(self, subscription_id: int, created_by_id: int):
        import uuid
        from datetime import date
        from decimal import Decimal
        from app.models.acquisition import PurchaseOrder, PurchaseOrderItem, PurchaseOrderStatus

        # Load subscription with relationships
        result = await self.db.execute(
            select(SerialSubscription)
            .where(SerialSubscription.id == subscription_id)
            .options(
                selectinload(SerialSubscription.serial_title),
                selectinload(SerialSubscription.vendor),
                selectinload(SerialSubscription.fund),
            )
        )
        sub = result.scalar_one_or_none()
        if not sub:
            raise ValueError("Subscription not found")
        if sub.renewal_status not in [SubscriptionRenewalStatus.active.value, SubscriptionRenewalStatus.pending_renewal.value, SubscriptionRenewalStatus.active, SubscriptionRenewalStatus.pending_renewal]:
            raise ValueError(f"Subscription must be active or pending renewal, got: {sub.renewal_status}")
        if not sub.vendor_id:
            raise ValueError("Subscription has no vendor assigned")
        if not sub.fund_id:
            raise ValueError("Subscription has no fund assigned")

        title = sub.serial_title
        cost = Decimal(str(sub.cost or 0))
        copies = sub.copies_ordered or 1
        unit_price = cost / copies if copies > 1 else cost

        po_number = f"PO-SERIAL-{date.today().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        po = PurchaseOrder(
            po_number=po_number,
            vendor_id=sub.vendor_id,
            fund_id=sub.fund_id,
            order_date=date.today(),
            status=PurchaseOrderStatus.DRAFT,
            total_amount=cost,
            notes=f"Serial renewal: {title.title} ({sub.subscription_number or 'no sub #'})",
            created_by_id=created_by_id,
        )
        self.db.add(po)
        await self.db.flush()

        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            title=f"{title.title} - Renewal {(sub.end_date.year if sub.end_date else date.today().year) + 1}",
            author=title.publisher,
            isbn=title.issn_print,
            quantity=copies,
            unit_price=unit_price,
            notes=f"Subscription #{sub.subscription_number}, ISSN: {title.issn_print or 'N/A'}",
        )
        self.db.add(po_item)

        return po
