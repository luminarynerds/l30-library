# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.multi_branch import (
    BillingCycleType,
    BillingItemType,
    BillingStatus,
    Consortium,
    ConsortiumBilling,
    ConsortiumMember,
    ConsortiumSettings,
    ConsortiumTransaction,
)


class ConsortiumBillingService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # TRANSACTION RECORDING
    # =========================================================================

    async def record_ill_transaction(
        self,
        consortium_id: int,
        lending_member_id: int,
        borrowing_member_id: int,
        item_copy_id: int,
        patron_user_id: int,
        reference_id: int,  # ILL request ID
    ) -> ConsortiumTransaction:
        # Get the ILL fee from consortium settings
        fee = await self._get_ill_fee(consortium_id)

        return await self._create_transaction(
            consortium_id=consortium_id,
            transaction_type="ill_loan",
            lending_member_id=lending_member_id,
            borrowing_member_id=borrowing_member_id,
            item_copy_id=item_copy_id,
            patron_user_id=patron_user_id,
            fee_amount=fee,
            reference_type="ill_request",
            reference_id=reference_id,
        )

    async def record_reciprocal_checkout(
        self,
        consortium_id: int,
        home_member_id: int,  # Patron's home library
        checkout_member_id: int,  # Where checkout occurred
        item_copy_id: int,
        patron_user_id: int,
        checkout_id: int,
    ) -> ConsortiumTransaction:
        return await self._create_transaction(
            consortium_id=consortium_id,
            transaction_type="reciprocal_checkout",
            lending_member_id=checkout_member_id,
            borrowing_member_id=home_member_id,
            item_copy_id=item_copy_id,
            patron_user_id=patron_user_id,
            fee_amount=Decimal("0.00"),  # Usually no fee for reciprocal
            reference_type="checkout",
            reference_id=checkout_id,
        )

    async def record_transit_transaction(
        self,
        consortium_id: int,
        sending_member_id: int,
        receiving_member_id: int,
        item_copy_id: int,
        transit_request_id: int,
    ) -> ConsortiumTransaction:
        # Get the transit fee from consortium settings
        fee = await self._get_transit_fee(consortium_id)

        return await self._create_transaction(
            consortium_id=consortium_id,
            transaction_type="transit",
            lending_member_id=sending_member_id,
            borrowing_member_id=receiving_member_id,
            item_copy_id=item_copy_id,
            fee_amount=fee,
            reference_type="transit_request",
            reference_id=transit_request_id,
        )

    async def record_lost_item_reimbursement(
        self,
        consortium_id: int,
        owning_member_id: int,
        responsible_member_id: int,
        item_copy_id: int,
        amount: Decimal,
        reference_type: str,
        reference_id: int,
        notes: str | None = None,
    ) -> ConsortiumTransaction:
        return await self._create_transaction(
            consortium_id=consortium_id,
            transaction_type="lost_item_reimbursement",
            lending_member_id=owning_member_id,
            borrowing_member_id=responsible_member_id,
            item_copy_id=item_copy_id,
            fee_amount=amount,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
        )

    async def _create_transaction(
        self,
        consortium_id: int,
        transaction_type: str,
        lending_member_id: int | None = None,
        borrowing_member_id: int | None = None,
        item_copy_id: int | None = None,
        patron_user_id: int | None = None,
        fee_amount: Decimal = Decimal("0.00"),
        reference_type: str | None = None,
        reference_id: int | None = None,
        notes: str | None = None,
    ) -> ConsortiumTransaction:
        transaction = ConsortiumTransaction(
            consortium_id=consortium_id,
            transaction_type=transaction_type,
            lending_member_id=lending_member_id,
            borrowing_member_id=borrowing_member_id,
            item_copy_id=item_copy_id,
            patron_user_id=patron_user_id,
            fee_amount=fee_amount,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
        )
        self.db.add(transaction)
        await self.db.commit()
        await self.db.refresh(transaction)
        return transaction

    async def _get_ill_fee(self, consortium_id: int) -> Decimal:
        result = await self.db.execute(
            select(ConsortiumSettings).where(
                ConsortiumSettings.consortium_id == consortium_id
            )
        )
        settings = result.scalar_one_or_none()
        return settings.ill_fee_per_item if settings else Decimal("0.00")

    async def _get_transit_fee(self, consortium_id: int) -> Decimal:
        result = await self.db.execute(
            select(ConsortiumSettings).where(
                ConsortiumSettings.consortium_id == consortium_id
            )
        )
        settings = result.scalar_one_or_none()
        return settings.transit_fee_per_item if settings else Decimal("0.00")

    # =========================================================================
    # BILLING GENERATION
    # =========================================================================

    async def generate_billing_for_period(
        self,
        consortium_id: int,
        period_start: date,
        period_end: date,
    ) -> list[ConsortiumBilling]:
        # Get all active members
        result = await self.db.execute(
            select(ConsortiumMember).where(
                and_(
                    ConsortiumMember.consortium_id == consortium_id,
                    ConsortiumMember.status == "active"
                )
            )
        )
        members = list(result.scalars().all())

        billing_records = []

        # Generate billing for each pair of members
        for billing_member in members:
            for billed_member in members:
                if billing_member.id == billed_member.id:
                    continue

                # Get unbilled transactions where billing_member is owed money by billed_member
                records = await self._generate_member_billing(
                    consortium_id=consortium_id,
                    billing_member_id=billing_member.id,
                    billed_member_id=billed_member.id,
                    period_start=period_start,
                    period_end=period_end,
                )
                billing_records.extend(records)

        return billing_records

    async def _generate_member_billing(
        self,
        consortium_id: int,
        billing_member_id: int,  # Member being paid (lending library)
        billed_member_id: int,  # Member paying (borrowing library)
        period_start: date,
        period_end: date,
    ) -> list[ConsortiumBilling]:
        # Get transactions where billing_member lent to billed_member
        result = await self.db.execute(
            select(ConsortiumTransaction).where(
                and_(
                    ConsortiumTransaction.consortium_id == consortium_id,
                    ConsortiumTransaction.lending_member_id == billing_member_id,
                    ConsortiumTransaction.borrowing_member_id == billed_member_id,
                    ConsortiumTransaction.billed == False,
                    ConsortiumTransaction.fee_amount > 0,
                    ConsortiumTransaction.transaction_date >= datetime.combine(period_start, datetime.min.time()),
                    ConsortiumTransaction.transaction_date <= datetime.combine(period_end, datetime.max.time()),
                )
            )
        )
        transactions = list(result.scalars().all())

        if not transactions:
            return []

        # Group transactions by type
        by_type: dict[str, list[ConsortiumTransaction]] = {}
        for tx in transactions:
            if tx.transaction_type not in by_type:
                by_type[tx.transaction_type] = []
            by_type[tx.transaction_type].append(tx)

        billing_records = []

        # Create billing record for each type
        type_to_billing_type = {
            "ill_loan": BillingItemType.ILL_FEE,
            "transit": BillingItemType.TRANSIT_FEE,
            "lost_item_reimbursement": BillingItemType.LOST_ITEM_REIMBURSEMENT,
            "damaged_item_reimbursement": BillingItemType.DAMAGED_ITEM_REIMBURSEMENT,
        }

        for tx_type, txs in by_type.items():
            billing_type = type_to_billing_type.get(tx_type, BillingItemType.SERVICE_FEE)
            quantity = len(txs)
            total = sum(tx.fee_amount for tx in txs)

            # Calculate unit amount (average)
            unit_amount = total / quantity if quantity > 0 else Decimal("0.00")

            billing = ConsortiumBilling(
                consortium_id=consortium_id,
                billing_member_id=billing_member_id,
                billed_member_id=billed_member_id,
                billing_period_start=period_start,
                billing_period_end=period_end,
                item_type=billing_type,
                quantity=quantity,
                unit_amount=unit_amount,
                total_amount=total,
                status=BillingStatus.PENDING,
                reference_ids=[tx.id for tx in txs],
                description=f"{billing_type.value} for period {period_start} to {period_end}",
            )
            self.db.add(billing)
            await self.db.flush()

            # Mark transactions as billed
            for tx in txs:
                tx.billed = True
                tx.billing_record_id = billing.id

            billing_records.append(billing)

        await self.db.commit()

        # Refresh all records
        for record in billing_records:
            await self.db.refresh(record)

        return billing_records

    async def create_membership_fee_billing(
        self,
        consortium_id: int,
        member_id: int,
        period_start: date,
        period_end: date,
        amount: Decimal,
    ) -> ConsortiumBilling:
        billing = ConsortiumBilling(
            consortium_id=consortium_id,
            billing_member_id=0,  # Consortium itself
            billed_member_id=member_id,
            billing_period_start=period_start,
            billing_period_end=period_end,
            item_type=BillingItemType.MEMBERSHIP_FEE,
            quantity=1,
            unit_amount=amount,
            total_amount=amount,
            status=BillingStatus.PENDING,
            description=f"Membership fee for {period_start.year}",
        )
        self.db.add(billing)
        await self.db.commit()
        await self.db.refresh(billing)
        return billing

    # =========================================================================
    # INVOICE MANAGEMENT
    # =========================================================================

    async def create_invoice(
        self,
        billing_ids: list[int],
        due_days: int = 30,
    ) -> list[ConsortiumBilling]:
        invoice_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
        now = datetime.now(timezone.utc)
        due_date = date.today() + timedelta(days=due_days)

        result = await self.db.execute(
            select(ConsortiumBilling).where(ConsortiumBilling.id.in_(billing_ids))
        )
        records = list(result.scalars().all())

        for record in records:
            record.invoice_number = invoice_number
            record.invoiced_at = now
            record.due_date = due_date
            record.status = BillingStatus.INVOICED

        await self.db.commit()

        for record in records:
            await self.db.refresh(record)

        return records

    async def get_billing_record(self, billing_id: int) -> ConsortiumBilling | None:
        result = await self.db.execute(
            select(ConsortiumBilling)
            .options(
                joinedload(ConsortiumBilling.billing_member).joinedload(ConsortiumMember.library_system),
                joinedload(ConsortiumBilling.billed_member).joinedload(ConsortiumMember.library_system),
            )
            .where(ConsortiumBilling.id == billing_id)
        )
        return result.unique().scalar_one_or_none()

    async def list_billing_records(
        self,
        consortium_id: int,
        member_id: int | None = None,
        status: BillingStatus | None = None,
        from_date: date | None = None,
        to_date: date | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ConsortiumBilling]:
        query = select(ConsortiumBilling).where(
            ConsortiumBilling.consortium_id == consortium_id
        )

        if member_id:
            query = query.where(
                or_(
                    ConsortiumBilling.billing_member_id == member_id,
                    ConsortiumBilling.billed_member_id == member_id,
                )
            )
        if status:
            query = query.where(ConsortiumBilling.status == status)
        if from_date:
            query = query.where(ConsortiumBilling.billing_period_start >= from_date)
        if to_date:
            query = query.where(ConsortiumBilling.billing_period_end <= to_date)

        query = query.order_by(
            ConsortiumBilling.billing_period_start.desc()
        ).offset(offset).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_invoice_records(
        self,
        invoice_number: str
    ) -> list[ConsortiumBilling]:
        result = await self.db.execute(
            select(ConsortiumBilling).where(
                ConsortiumBilling.invoice_number == invoice_number
            )
        )
        return list(result.scalars().all())

    # =========================================================================
    # PAYMENT TRACKING
    # =========================================================================

    async def record_payment(
        self,
        billing_id: int,
        payment_reference: str | None = None,
    ) -> ConsortiumBilling | None:
        record = await self.get_billing_record(billing_id)
        if not record:
            return None

        record.status = BillingStatus.PAID
        record.paid_at = datetime.now(timezone.utc)
        record.payment_reference = payment_reference

        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def record_invoice_payment(
        self,
        invoice_number: str,
        payment_reference: str | None = None,
    ) -> list[ConsortiumBilling]:
        records = await self.get_invoice_records(invoice_number)
        now = datetime.now(timezone.utc)

        for record in records:
            record.status = BillingStatus.PAID
            record.paid_at = now
            record.payment_reference = payment_reference

        await self.db.commit()

        for record in records:
            await self.db.refresh(record)

        return records

    async def mark_overdue(
        self,
        consortium_id: int | None = None
    ) -> int:
        today = date.today()

        query = select(ConsortiumBilling).where(
            and_(
                ConsortiumBilling.status == BillingStatus.INVOICED,
                ConsortiumBilling.due_date < today,
            )
        )

        if consortium_id:
            query = query.where(ConsortiumBilling.consortium_id == consortium_id)

        result = await self.db.execute(query)
        records = list(result.scalars().all())

        for record in records:
            record.status = BillingStatus.OVERDUE

        await self.db.commit()
        return len(records)

    # =========================================================================
    # DISPUTE HANDLING
    # =========================================================================

    async def dispute_billing(
        self,
        billing_id: int,
        reason: str,
    ) -> ConsortiumBilling | None:
        record = await self.get_billing_record(billing_id)
        if not record:
            return None

        record.status = BillingStatus.DISPUTED
        record.disputed_at = datetime.now(timezone.utc)
        record.dispute_reason = reason

        await self.db.commit()
        await self.db.refresh(record)
        return record

    async def resolve_dispute(
        self,
        billing_id: int,
        resolution: str,  # "paid", "written_off", "adjusted"
        adjustment_amount: Decimal | None = None,
    ) -> ConsortiumBilling | None:
        record = await self.get_billing_record(billing_id)
        if not record:
            return None

        record.dispute_resolved_at = datetime.now(timezone.utc)

        if resolution == "paid":
            record.status = BillingStatus.PAID
            record.paid_at = datetime.now(timezone.utc)
        elif resolution == "written_off":
            record.status = BillingStatus.WRITTEN_OFF
        elif resolution == "adjusted" and adjustment_amount is not None:
            # Create a credit record
            credit = ConsortiumBilling(
                consortium_id=record.consortium_id,
                billing_member_id=record.billed_member_id,  # Reversed
                billed_member_id=record.billing_member_id,
                billing_period_start=record.billing_period_start,
                billing_period_end=record.billing_period_end,
                item_type=BillingItemType.ADJUSTMENT,
                quantity=1,
                unit_amount=adjustment_amount,
                total_amount=adjustment_amount,
                status=BillingStatus.PENDING,
                description=f"Adjustment for dispute on billing {record.id}",
            )
            self.db.add(credit)
            record.status = BillingStatus.PAID
            record.paid_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(record)
        return record

    # =========================================================================
    # FINANCIAL REPORTS
    # =========================================================================

    async def get_member_balance(
        self,
        consortium_id: int,
        member_id: int,
    ) -> dict[str, Decimal]:
        # Amount owed TO this member (they are billing_member)
        owed_to_query = select(func.coalesce(func.sum(ConsortiumBilling.total_amount), 0)).where(
            and_(
                ConsortiumBilling.consortium_id == consortium_id,
                ConsortiumBilling.billing_member_id == member_id,
                ConsortiumBilling.status.in_([BillingStatus.PENDING, BillingStatus.INVOICED, BillingStatus.OVERDUE]),
            )
        )
        result = await self.db.execute(owed_to_query)
        owed_to = result.scalar() or Decimal("0.00")

        # Amount this member OWES (they are billed_member)
        owes_query = select(func.coalesce(func.sum(ConsortiumBilling.total_amount), 0)).where(
            and_(
                ConsortiumBilling.consortium_id == consortium_id,
                ConsortiumBilling.billed_member_id == member_id,
                ConsortiumBilling.status.in_([BillingStatus.PENDING, BillingStatus.INVOICED, BillingStatus.OVERDUE]),
            )
        )
        result = await self.db.execute(owes_query)
        owes = result.scalar() or Decimal("0.00")

        return {
            "owed_to_member": owed_to,
            "member_owes": owes,
            "net_balance": owed_to - owes,
        }

    async def get_consortium_financial_summary(
        self,
        consortium_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        conditions = [ConsortiumBilling.consortium_id == consortium_id]
        if from_date:
            conditions.append(ConsortiumBilling.billing_period_start >= from_date)
        if to_date:
            conditions.append(ConsortiumBilling.billing_period_end <= to_date)

        # Total by status
        status_query = (
            select(ConsortiumBilling.status, func.sum(ConsortiumBilling.total_amount))
            .where(and_(*conditions))
            .group_by(ConsortiumBilling.status)
        )
        result = await self.db.execute(status_query)
        by_status = {row[0].value: float(row[1] or 0) for row in result.all()}

        # Total by type
        type_query = (
            select(ConsortiumBilling.item_type, func.sum(ConsortiumBilling.total_amount))
            .where(and_(*conditions))
            .group_by(ConsortiumBilling.item_type)
        )
        result = await self.db.execute(type_query)
        by_type = {row[0].value: float(row[1] or 0) for row in result.all()}

        # Total transactions
        tx_query = (
            select(
                func.count(ConsortiumTransaction.id),
                func.sum(ConsortiumTransaction.fee_amount)
            )
            .where(ConsortiumTransaction.consortium_id == consortium_id)
        )
        if from_date:
            tx_query = tx_query.where(
                ConsortiumTransaction.transaction_date >= datetime.combine(from_date, datetime.min.time())
            )
        if to_date:
            tx_query = tx_query.where(
                ConsortiumTransaction.transaction_date <= datetime.combine(to_date, datetime.max.time())
            )
        result = await self.db.execute(tx_query)
        tx_count, tx_total = result.one()

        return {
            "total_by_status": by_status,
            "total_by_type": by_type,
            "total_transactions": tx_count or 0,
            "total_transaction_amount": float(tx_total or 0),
            "period": {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
            }
        }

    async def get_member_transaction_summary(
        self,
        consortium_id: int,
        member_id: int,
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> dict[str, Any]:
        conditions = [
            ConsortiumTransaction.consortium_id == consortium_id,
            or_(
                ConsortiumTransaction.lending_member_id == member_id,
                ConsortiumTransaction.borrowing_member_id == member_id,
            )
        ]

        if from_date:
            conditions.append(
                ConsortiumTransaction.transaction_date >= datetime.combine(from_date, datetime.min.time())
            )
        if to_date:
            conditions.append(
                ConsortiumTransaction.transaction_date <= datetime.combine(to_date, datetime.max.time())
            )

        # As lending member (providing items)
        lending_query = (
            select(
                ConsortiumTransaction.transaction_type,
                func.count(ConsortiumTransaction.id),
                func.sum(ConsortiumTransaction.fee_amount)
            )
            .where(
                and_(
                    *conditions,
                    ConsortiumTransaction.lending_member_id == member_id,
                )
            )
            .group_by(ConsortiumTransaction.transaction_type)
        )
        result = await self.db.execute(lending_query)
        lending_stats = {
            row[0]: {"count": row[1], "amount": float(row[2] or 0)}
            for row in result.all()
        }

        # As borrowing member (receiving items)
        borrowing_query = (
            select(
                ConsortiumTransaction.transaction_type,
                func.count(ConsortiumTransaction.id),
                func.sum(ConsortiumTransaction.fee_amount)
            )
            .where(
                and_(
                    *conditions,
                    ConsortiumTransaction.borrowing_member_id == member_id,
                )
            )
            .group_by(ConsortiumTransaction.transaction_type)
        )
        result = await self.db.execute(borrowing_query)
        borrowing_stats = {
            row[0]: {"count": row[1], "amount": float(row[2] or 0)}
            for row in result.all()
        }

        return {
            "member_id": member_id,
            "as_lending_library": lending_stats,
            "as_borrowing_library": borrowing_stats,
            "period": {
                "from": from_date.isoformat() if from_date else None,
                "to": to_date.isoformat() if to_date else None,
            }
        }
