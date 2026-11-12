# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import secrets
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...models.makerspace import (
    MakerspacePayment, MakerspaceReservation, MakerspaceJob,
    PaymentStatus,
)
from .base_service import BaseMakerspaceService

logger = get_logger(__name__)


class MakerspacePaymentService(BaseMakerspaceService[MakerspacePayment]):

    model = MakerspacePayment

    @staticmethod
    def _generate_receipt_number() -> str:
        return f"MS-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(2).upper()}"

    @staticmethod
    async def create_payment(
        db: AsyncSession,
        user_id: int,
        amount: Decimal,
        payment_method: str,
        processed_by_id: int | None = None,
        reservation_id: int | None = None,
        job_id: int | None = None,
        machine_time_fee: Decimal = Decimal("0.00"),
        consumables_fee: Decimal = Decimal("0.00"),
        setup_fee: Decimal = Decimal("0.00"),
        payment_reference: str | None = None,
        notes: str | None = None
    ) -> MakerspacePayment:
        payment = MakerspacePayment(
            user_id=user_id,
            amount=amount,
            payment_method=payment_method,
            status=PaymentStatus.paid,
            receipt_number=MakerspacePaymentService._generate_receipt_number(),
            machine_time_fee=machine_time_fee,
            consumables_fee=consumables_fee,
            setup_fee=setup_fee,
            payment_reference=payment_reference,
            processed_by_id=processed_by_id,
            notes=notes
        )
        db.add(payment)
        await db.flush()

        # Link to reservation or job
        if reservation_id:
            result = await db.execute(
                select(MakerspaceReservation)
                .where(MakerspaceReservation.id == reservation_id)
            )
            reservation = result.scalar_one_or_none()
            if reservation:
                reservation.payment_id = payment.id
                reservation.payment_status = PaymentStatus.paid

        if job_id:
            result = await db.execute(
                select(MakerspaceJob).where(MakerspaceJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if job:
                job.payment_id = payment.id
                job.payment_status = PaymentStatus.paid

        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def refund(
        db: AsyncSession,
        payment: MakerspacePayment,
        amount: Decimal,
        reason: str,
        processed_by_id: int | None = None
    ) -> MakerspacePayment:
        if amount > payment.amount - payment.refund_amount:
            raise ValueError("Refund amount exceeds available balance")

        payment.refund_amount += amount
        payment.refunded_at = datetime.now(timezone.utc)
        payment.refund_reason = reason

        if payment.refund_amount >= payment.amount:
            payment.status = PaymentStatus.refunded

        await db.commit()
        await db.refresh(payment)
        return payment

    @staticmethod
    async def calculate_cost(
        db: AsyncSession,
        resource_id: int,
        duration_hours: Decimal,
        consumables: list[dict] | None = None
    ) -> dict:
        # Import here to avoid circular imports
        from .resource_service import MakerspaceResourceService
        from .consumable_service import ConsumableService

        resource = await MakerspaceResourceService.get_by_id(db, resource_id)
        if not resource:
            raise ValueError("Resource not found")

        machine_time_cost = resource.hourly_cost * duration_hours
        setup_fee = resource.setup_fee
        consumables_cost = Decimal("0.00")
        breakdown = []

        breakdown.append({
            "item": f"Machine time ({duration_hours}h @ ${resource.hourly_cost}/hr)",
            "cost": machine_time_cost
        })

        if setup_fee > 0:
            breakdown.append({
                "item": "Setup fee",
                "cost": setup_fee
            })

        if consumables:
            for item in consumables:
                consumable = await ConsumableService.get_by_id(db, item["consumable_id"])
                if consumable:
                    item_cost = consumable.price_per_unit * item["quantity_used"]
                    consumables_cost += item_cost
                    breakdown.append({
                        "item": f"{consumable.name} ({item['quantity_used']} {consumable.unit})",
                        "cost": item_cost
                    })

        total_cost = machine_time_cost + setup_fee + consumables_cost

        return {
            "machine_time_hours": duration_hours,
            "machine_time_cost": machine_time_cost,
            "consumables_cost": consumables_cost,
            "setup_fee": setup_fee,
            "total_cost": total_cost,
            "breakdown": breakdown
        }
