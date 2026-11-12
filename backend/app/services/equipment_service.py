# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.equipment import (
    DEFAULT_EQUIPMENT_AGREEMENT,
    AgreementStatus,
    Equipment,
    EquipmentAlert,
    EquipmentAgreement,
    EquipmentCheckout,
    EquipmentCondition,
    EquipmentConditionLog,
    EquipmentMaintenance,
    EquipmentReservation,
    EquipmentStatus,
    EquipmentType,
    EquipmentMaintenanceStatus,
    EquipmentMaintenanceType,
    EquipmentReservationStatus,
    get_agreement_template,
)
from app.models.fine import Fine, FineStatus, FineType
from app.models.user import User
from app.core.audit_log import audit_log_event
from app.core.datetime_utils import ensure_utc, utc_now
from app.services import operations_audit_service as ops_audit

logger = get_logger(__name__)


# ============================================================================
# Equipment CRUD Operations
# ============================================================================


async def create_equipment(
    db: AsyncSession,
    data: dict,
    created_by_id: int,
) -> Equipment:
    equipment = Equipment(
        **data,
        created_by_id=created_by_id,
        status=EquipmentStatus.AVAILABLE,
        condition=EquipmentCondition.GOOD,
    )

    # Calculate next maintenance date if schedule is set
    if equipment.maintenance_schedule_days:
        equipment.next_maintenance_date = date.today() + timedelta(
            days=equipment.maintenance_schedule_days
        )

    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)
    return equipment


async def get_equipment(
    db: AsyncSession,
    equipment_id: int,
) -> Optional[Equipment]:
    result = await db.execute(
        select(Equipment).where(Equipment.id == equipment_id)
    )
    return result.scalar_one_or_none()


async def get_equipment_by_barcode(
    db: AsyncSession,
    barcode: str,
) -> Optional[Equipment]:
    result = await db.execute(
        select(Equipment).where(Equipment.barcode == barcode)
    )
    return result.scalar_one_or_none()


async def list_equipment(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    equipment_type: Optional[EquipmentType] = None,
    status: Optional[EquipmentStatus] = None,
    condition: Optional[EquipmentCondition] = None,
    location: Optional[str] = None,
    search: Optional[str] = None,
    available_only: bool = False,
) -> Tuple[list[Equipment], int]:
    query = select(Equipment).where(Equipment.status != EquipmentStatus.RETIRED)

    if equipment_type:
        query = query.where(Equipment.equipment_type == equipment_type)
    if status:
        query = query.where(Equipment.status == status)
    if condition:
        query = query.where(Equipment.condition == condition)
    if location:
        safe_location = location.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(Equipment.location.ilike(f"%{safe_location}%"))
    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where(
            or_(
                Equipment.name.ilike(f"%{safe_search}%"),
                Equipment.barcode.ilike(f"%{safe_search}%"),
                Equipment.serial_number.ilike(f"%{safe_search}%"),
                Equipment.manufacturer.ilike(f"%{safe_search}%"),
                Equipment.model.ilike(f"%{safe_search}%"),
            )
        )
    if available_only:
        query = query.where(Equipment.status == EquipmentStatus.AVAILABLE)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(Equipment.name).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total


async def update_equipment(
    db: AsyncSession,
    equipment_id: int,
    data: dict,
) -> Optional[Equipment]:
    equipment = await get_equipment(db, equipment_id)
    if not equipment:
        return None

    for key, value in data.items():
        if value is not None and hasattr(equipment, key):
            setattr(equipment, key, value)

    await db.commit()
    await db.refresh(equipment)
    return equipment


async def retire_equipment(
    db: AsyncSession,
    equipment_id: int,
    notes: Optional[str] = None,
) -> Optional[Equipment]:
    equipment = await get_equipment(db, equipment_id)
    if not equipment:
        return None

    if equipment.status == EquipmentStatus.CHECKED_OUT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot retire equipment that is currently checked out"
        )

    equipment.status = EquipmentStatus.RETIRED
    equipment.retired_at = utc_now()
    if notes:
        equipment.notes = (equipment.notes or "") + f"\nRetired: {notes}"

    await db.commit()
    await db.refresh(equipment)
    return equipment


# ============================================================================
# Agreement Operations
# ============================================================================


async def get_or_create_agreement(
    db: AsyncSession,
    user_id: int,
    equipment_types: Optional[list[EquipmentType]] = None,
) -> EquipmentAgreement:
    # Check for existing valid agreement
    result = await db.execute(
        select(EquipmentAgreement).where(
            EquipmentAgreement.user_id == user_id,
            EquipmentAgreement.status.in_([AgreementStatus.PENDING, AgreementStatus.SIGNED]),
        ).order_by(EquipmentAgreement.created_at.desc())
    )
    existing = result.scalar_one_or_none()

    if existing and existing.status == AgreementStatus.SIGNED:
        # Check if still valid (ensure_utc handles naive datetimes from SQLite)
        if existing.valid_until and utc_now() > ensure_utc(existing.valid_until):
            existing.status = AgreementStatus.EXPIRED
            await db.commit()
        else:
            return existing

    if existing and existing.status == AgreementStatus.PENDING:
        return existing

    # Create new agreement
    types_covered = None
    if equipment_types:
        types_covered = ",".join([t.value for t in equipment_types])

    # Use type-specific template when a single equipment type is specified
    primary_type = equipment_types[0] if equipment_types and len(equipment_types) == 1 else None
    agreement_text = get_agreement_template(primary_type)

    agreement = EquipmentAgreement(
        user_id=user_id,
        agreement_text=agreement_text,
        status=AgreementStatus.PENDING,
        equipment_types_covered=types_covered,
    )
    db.add(agreement)
    await db.commit()
    await db.refresh(agreement)
    return agreement


async def sign_agreement(
    db: AsyncSession,
    agreement_id: int,
    user_id: int,
    signature: str,
    ip_address: Optional[str] = None,
) -> EquipmentAgreement:
    result = await db.execute(
        select(EquipmentAgreement).where(
            EquipmentAgreement.id == agreement_id,
            EquipmentAgreement.user_id == user_id,
        ).with_for_update()
    )
    agreement = result.scalar_one_or_none()

    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )

    if agreement.status == AgreementStatus.SIGNED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agreement already signed"
        )

    if agreement.status != AgreementStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot sign agreement with status: {agreement.status}"
        )

    agreement.signature = signature
    agreement.signed_at = utc_now()
    agreement.ip_address = ip_address
    agreement.status = AgreementStatus.SIGNED
    agreement.valid_from = utc_now()
    agreement.valid_until = utc_now() + timedelta(days=365)  # Valid for 1 year

    await db.commit()
    await db.refresh(agreement)
    return agreement


async def check_patron_agreement(
    db: AsyncSession,
    user_id: int,
    equipment_type: Optional[EquipmentType] = None,
) -> Tuple[bool, Optional[EquipmentAgreement]]:
    query = select(EquipmentAgreement).where(
        EquipmentAgreement.user_id == user_id,
        EquipmentAgreement.status == AgreementStatus.SIGNED,
    )

    result = await db.execute(query)
    agreements = result.scalars().all()

    for agreement in agreements:
        # Check validity (ensure_utc handles naive datetimes from SQLite)
        if agreement.valid_until and utc_now() > ensure_utc(agreement.valid_until):
            agreement.status = AgreementStatus.EXPIRED
            continue

        # Check equipment type coverage
        # `equipment_type` may be a plain str (e.g. Equipment.equipment_type,
        # which is a String(50) column, not a SQLAlchemy enum type) or an
        # EquipmentType member (e.g. from a FastAPI query param) — handle both.
        if equipment_type and agreement.equipment_types_covered:
            covered_types = agreement.equipment_types_covered.split(",")
            equipment_type_value = (
                equipment_type.value if hasattr(equipment_type, "value") else equipment_type
            )
            if equipment_type_value not in covered_types:
                continue

        return True, agreement

    await db.commit()
    return False, None


async def revoke_agreement(
    db: AsyncSession,
    agreement_id: int,
    revoked_by_id: int,
    reason: str,
) -> EquipmentAgreement:
    result = await db.execute(
        select(EquipmentAgreement).where(EquipmentAgreement.id == agreement_id)
    )
    agreement = result.scalar_one_or_none()

    if not agreement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agreement not found"
        )

    agreement.status = AgreementStatus.REVOKED
    agreement.revoked_at = utc_now()
    agreement.revoked_by_id = revoked_by_id
    agreement.revocation_reason = reason

    await db.commit()
    await db.refresh(agreement)
    return agreement


# ============================================================================
# Checkout Operations
# ============================================================================


async def checkout_equipment(
    db: AsyncSession,
    equipment_id: int,
    patron_id: int,
    staff_id: Optional[int] = None,
    notes: Optional[str] = None,
    deposit_collected: bool = False,
) -> EquipmentCheckout:
    # Lock equipment
    result = await db.execute(
        select(Equipment).where(Equipment.id == equipment_id).with_for_update()
    )
    equipment = result.scalar_one_or_none()

    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )

    # Check equipment availability
    if equipment.status != EquipmentStatus.AVAILABLE:
        # Check if there's a confirmed reservation for this patron
        reservation = await _get_active_reservation(db, equipment_id, patron_id)
        if not reservation or reservation.status != EquipmentReservationStatus.READY_FOR_PICKUP:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Equipment not available (status: {equipment.status})"
            )

    # Check patron exists and is active
    patron_result = await db.execute(select(User).where(User.id == patron_id))
    patron = patron_result.scalar_one_or_none()

    if not patron or not patron.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patron not found or account is inactive"
        )

    # Check if agreement is required
    if equipment.requires_agreement:
        has_agreement, agreement = await check_patron_agreement(
            db, patron_id, equipment.equipment_type
        )
        if not has_agreement:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Equipment requires signed agreement before checkout. Please sign the equipment lending agreement first."
            )
    else:
        agreement = None

    # Check for existing active checkout
    existing = await db.execute(
        select(EquipmentCheckout).where(
            EquipmentCheckout.equipment_id == equipment_id,
            EquipmentCheckout.status == "active",
        ).with_for_update()
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Equipment is already checked out"
        )

    # Check patron's equipment checkout limit (default 3)
    # Lock patron's active checkout rows to prevent concurrent limit bypass
    locked_checkouts = await db.execute(
        select(EquipmentCheckout).where(
            EquipmentCheckout.user_id == patron_id,
            EquipmentCheckout.status.in_(["active", "overdue"]),
        ).with_for_update()
    )
    active_count = len(locked_checkouts.scalars().all())
    max_equipment_checkouts = 3  # Could be made configurable

    if active_count >= max_equipment_checkouts:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Equipment checkout limit reached ({active_count}/{max_equipment_checkouts})"
        )

    # Check if deposit is required but not collected
    if equipment.deposit_required and not deposit_collected:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deposit of ${equipment.deposit_amount} is required for this equipment. Please collect deposit before checkout."
        )

    # Create checkout with deposit tracking
    due_date = utc_now() + timedelta(days=equipment.max_checkout_days)
    checkout = EquipmentCheckout(
        equipment_id=equipment_id,
        user_id=patron_id,
        status="active",
        due_date=due_date,
        condition_at_checkout=equipment.condition,
        checkout_notes=notes,
        checked_out_by_id=staff_id,
        agreement_id=agreement.id if agreement else None,
        # Deposit tracking
        deposit_amount=equipment.deposit_amount if equipment.deposit_required else Decimal("0.00"),
        deposit_collected=deposit_collected and equipment.deposit_required,
        deposit_collected_at=utc_now() if (deposit_collected and equipment.deposit_required) else None,
    )
    db.add(checkout)

    # Update equipment status
    equipment.status = EquipmentStatus.CHECKED_OUT
    equipment.total_checkouts += 1

    # Update reservation if applicable
    reservation = await _get_active_reservation(db, equipment_id, patron_id)
    if reservation:
        reservation.status = EquipmentReservationStatus.CHECKED_OUT

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to checkout equipment")
        raise
    await db.refresh(checkout)
    return checkout


async def return_equipment(
    db: AsyncSession,
    checkout_id: int,
    condition_at_return: EquipmentCondition,
    staff_id: int,
    notes: Optional[str] = None,
    refund_deposit: bool = True,
    deposit_deduction_amount: Optional[Decimal] = None,
    deposit_deduction_reason: Optional[str] = None,
) -> EquipmentCheckout:
    # Lock checkout
    result = await db.execute(
        select(EquipmentCheckout)
        .where(EquipmentCheckout.id == checkout_id)
        .with_for_update()
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout not found"
        )

    if checkout.status not in ["active", "overdue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot return checkout with status: {checkout.status}"
        )

    # Get equipment
    equipment = await get_equipment(db, checkout.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )

    # Calculate fine if overdue
    now = utc_now()
    if now > checkout.due_date:
        overdue_days = (now - checkout.due_date).days
        fine_amount = Decimal(overdue_days) * equipment.fine_per_day
        checkout.fine_amount = fine_amount

        # Create fine record
        fine = Fine(
            user_id=checkout.user_id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=fine_amount,
            description=f"Overdue equipment: {equipment.name} ({overdue_days} days)",
        )
        db.add(fine)

    # Record condition change if different
    if condition_at_return != checkout.condition_at_checkout:
        condition_log = EquipmentConditionLog(
            equipment_id=equipment.id,
            previous_condition=checkout.condition_at_checkout,
            new_condition=condition_at_return,
            change_reason="Return inspection",
            notes=notes,
            checkout_id=checkout_id,
            recorded_by_id=staff_id,
        )
        db.add(condition_log)
        equipment.condition = condition_at_return

    # Update checkout
    checkout.status = "returned"
    checkout.returned_at = now
    checkout.condition_at_return = condition_at_return
    checkout.return_notes = notes
    checkout.returned_to_id = staff_id

    # Process deposit refund if deposit was collected
    deposit_audit_event: Optional[str] = None
    deposit_audit_amount: Decimal = Decimal("0")
    deposit_audit_refund: Decimal = Decimal("0")
    deposit_audit_reason: Optional[str] = None
    if checkout.deposit_collected and checkout.deposit_amount > Decimal("0"):
        if refund_deposit:
            # Calculate refund amount (full or partial)
            if deposit_deduction_amount and deposit_deduction_amount > Decimal("0"):
                refund_amount = max(Decimal("0"), checkout.deposit_amount - deposit_deduction_amount)
                checkout.deposit_deduction_reason = deposit_deduction_reason or "Deduction applied"
                deposit_audit_event = "deducted"
                deposit_audit_amount = min(deposit_deduction_amount, checkout.deposit_amount)
                deposit_audit_refund = refund_amount
                deposit_audit_reason = checkout.deposit_deduction_reason
            else:
                refund_amount = checkout.deposit_amount
                deposit_audit_event = "refunded"
                deposit_audit_refund = refund_amount

            checkout.deposit_refunded = True
            checkout.deposit_refunded_at = now
            checkout.deposit_refund_amount = refund_amount
        else:
            # No refund - full deposit kept (e.g., severe damage)
            checkout.deposit_refunded = False
            checkout.deposit_refund_amount = Decimal("0")
            checkout.deposit_deduction_reason = deposit_deduction_reason or "Deposit forfeited"
            deposit_audit_event = "deducted"
            deposit_audit_amount = checkout.deposit_amount
            deposit_audit_refund = Decimal("0")
            deposit_audit_reason = checkout.deposit_deduction_reason

    # Process next reservation
    next_reservation = await _get_next_reservation(db, equipment.id)
    if next_reservation:
        equipment.status = EquipmentStatus.RESERVED
        next_reservation.status = EquipmentReservationStatus.READY_FOR_PICKUP
        next_reservation.notified_at = now
        next_reservation.pickup_deadline = now + timedelta(days=2)

        # Create alert for ready pickup
        alert = EquipmentAlert(
            alert_type="reservation_ready",
            priority="medium",
            status="active",
            equipment_id=equipment.id,
            reservation_id=next_reservation.id,
            user_id=next_reservation.user_id,
            title=f"Equipment ready for pickup: {equipment.name}",
            message=f"Your reserved equipment is ready. Please pick up by {next_reservation.pickup_deadline}",
        )
        db.add(alert)
    else:
        equipment.status = EquipmentStatus.AVAILABLE

    # Resolve any overdue alerts
    await _resolve_overdue_alerts(db, checkout_id)

    # Audit deposit refund / deduction (financial event - must hit BOTH systems)
    if deposit_audit_event == "deducted":
        await ops_audit.log_equipment_deposit_deducted(
            db,
            patron_id=checkout.user_id,
            equipment_id=equipment.id,
            checkout_id=checkout.id,
            deposit_amount_cents=int(checkout.deposit_amount * 100),
            deduction_amount_cents=int(deposit_audit_amount * 100),
            refund_amount_cents=int(deposit_audit_refund * 100),
            reason=deposit_audit_reason,
            staff=None,
        )
        audit_log_event(
            event_type="EQUIPMENT_DEPOSIT_DEDUCTED",
            user_id=checkout.user_id,
            severity="WARNING",
            details={
                "checkout_id": checkout.id,
                "equipment_id": equipment.id,
                "deposit_amount": str(checkout.deposit_amount),
                "deduction_amount": str(deposit_audit_amount),
                "refund_amount": str(deposit_audit_refund),
                "reason": deposit_audit_reason,
                "staff_id": staff_id,
            },
        )
    elif deposit_audit_event == "refunded":
        await ops_audit.log_equipment_deposit_refunded(
            db,
            patron_id=checkout.user_id,
            equipment_id=equipment.id,
            checkout_id=checkout.id,
            refund_amount_cents=int(deposit_audit_refund * 100),
            deposit_amount_cents=int(checkout.deposit_amount * 100),
            staff=None,
        )
        audit_log_event(
            event_type="EQUIPMENT_DEPOSIT_REFUNDED",
            user_id=checkout.user_id,
            severity="INFO",
            details={
                "checkout_id": checkout.id,
                "equipment_id": equipment.id,
                "refund_amount": str(deposit_audit_refund),
                "staff_id": staff_id,
            },
        )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to return equipment")
        raise
    await db.refresh(checkout)
    return checkout


async def return_equipment_by_barcode(
    db: AsyncSession,
    barcode: str,
    condition_at_return: EquipmentCondition,
    staff_id: int,
    notes: Optional[str] = None,
    refund_deposit: bool = True,
    deposit_deduction_amount: Optional[Decimal] = None,
    deposit_deduction_reason: Optional[str] = None,
) -> EquipmentCheckout:
    equipment = await get_equipment_by_barcode(db, barcode)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )

    # Find active checkout
    result = await db.execute(
        select(EquipmentCheckout).where(
            EquipmentCheckout.equipment_id == equipment.id,
            EquipmentCheckout.status.in_(["active", "overdue"]),
        )
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active checkout found for this equipment"
        )

    return await return_equipment(
        db, checkout.id, condition_at_return, staff_id, notes,
        refund_deposit, deposit_deduction_amount, deposit_deduction_reason
    )


async def report_equipment_lost(
    db: AsyncSession,
    checkout_id: int,
    staff_id: int,
    reason: str,
    assess_replacement_fee: bool = True,
    notes: Optional[str] = None,
) -> EquipmentCheckout:
    # Lock checkout
    result = await db.execute(
        select(EquipmentCheckout)
        .where(EquipmentCheckout.id == checkout_id)
        .with_for_update()
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout not found",
        )

    if checkout.status not in ["active", "overdue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot report lost on checkout with status: {checkout.status}",
        )

    equipment = await get_equipment(db, checkout.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    now = utc_now()

    # Update checkout + equipment statuses
    checkout.status = "lost"
    checkout.return_notes = (
        (checkout.return_notes or "") + f"\nReported LOST: {reason}"
        + (f"\nNotes: {notes}" if notes else "")
    ).strip()
    equipment.status = EquipmentStatus.LOST

    # Optionally create replacement-cost fine
    fine: Optional[Fine] = None
    if (
        assess_replacement_fee
        and equipment.replacement_cost
        and equipment.replacement_cost > Decimal("0")
        and checkout.user_id is not None
    ):
        fine = Fine(
            user_id=checkout.user_id,
            checkout_id=None,  # equipment_checkouts.id is not the books checkouts.id
            fine_type=FineType.lost_item,
            status=FineStatus.unpaid,
            amount=equipment.replacement_cost,
            description=f"Lost equipment: {equipment.name} (replacement cost)",
            notes=reason,
        )
        db.add(fine)

    # Resolve any existing overdue alerts since item is now lost
    await _resolve_overdue_alerts(db, checkout_id)

    # Flush so the fine row gets an id before audit logging
    await db.flush()

    fee_cents = (
        int(fine.amount * 100) if fine is not None else None
    )

    # ops_audit (DB-queryable)
    await ops_audit.log_equipment_reported_lost(
        db,
        patron_id=checkout.user_id,
        equipment_id=equipment.id,
        checkout_id=checkout.id,
        reason=reason,
        replacement_fee_cents=fee_cents,
        staff=None,
    )
    # audit_log_event (HMAC-signed file)
    audit_log_event(
        event_type="EQUIPMENT_REPORTED_LOST",
        user_id=checkout.user_id,
        severity="WARNING",
        details={
            "checkout_id": checkout.id,
            "equipment_id": equipment.id,
            "equipment_barcode": equipment.barcode,
            "reason": reason,
            "replacement_fee_assessed": fine is not None,
            "replacement_fee_amount": (
                str(fine.amount) if fine is not None else None
            ),
            "fine_id": fine.id if fine is not None else None,
            "staff_id": staff_id,
            "notes": notes,
            "reported_at": now.isoformat(),
        },
    )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to report equipment lost")
        raise
    await db.refresh(checkout)
    return checkout


async def report_equipment_damaged(
    db: AsyncSession,
    checkout_id: int,
    staff_id: int,
    damage_description: str,
    fee_amount: Optional[Decimal] = None,
    notes: Optional[str] = None,
) -> EquipmentCheckout:
    # Lock checkout
    result = await db.execute(
        select(EquipmentCheckout)
        .where(EquipmentCheckout.id == checkout_id)
        .with_for_update()
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout not found",
        )

    if checkout.status not in ["active", "overdue", "returned"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot report damage on checkout with status: {checkout.status}",
        )

    equipment = await get_equipment(db, checkout.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    # Record condition change to NEEDS_REPAIR (closest existing condition)
    condition_log = EquipmentConditionLog(
        equipment_id=equipment.id,
        previous_condition=equipment.condition,
        new_condition=EquipmentCondition.NEEDS_REPAIR,
        change_reason="Damage report",
        notes=(damage_description + (f"\n{notes}" if notes else "")),
        checkout_id=checkout_id,
        recorded_by_id=staff_id,
    )
    db.add(condition_log)

    equipment.condition = EquipmentCondition.NEEDS_REPAIR
    equipment.status = EquipmentStatus.DAMAGED

    # Annotate the checkout
    checkout.return_notes = (
        (checkout.return_notes or "") + f"\nReported DAMAGED: {damage_description}"
        + (f"\nNotes: {notes}" if notes else "")
    ).strip()

    # Optionally create damage fine
    fine: Optional[Fine] = None
    if (
        fee_amount is not None
        and fee_amount > Decimal("0")
        and checkout.user_id is not None
    ):
        fine = Fine(
            user_id=checkout.user_id,
            checkout_id=None,
            fine_type=FineType.damaged_item,
            status=FineStatus.unpaid,
            amount=fee_amount,
            description=f"Damaged equipment: {equipment.name}",
            notes=damage_description,
        )
        db.add(fine)

    await db.flush()

    fee_cents = (
        int(fine.amount * 100) if fine is not None else None
    )

    await ops_audit.log_equipment_reported_damaged(
        db,
        patron_id=checkout.user_id,
        equipment_id=equipment.id,
        checkout_id=checkout.id,
        damage_description=damage_description,
        fee_amount_cents=fee_cents,
        staff=None,
    )
    audit_log_event(
        event_type="EQUIPMENT_REPORTED_DAMAGED",
        user_id=checkout.user_id,
        severity="WARNING",
        details={
            "checkout_id": checkout.id,
            "equipment_id": equipment.id,
            "equipment_barcode": equipment.barcode,
            "damage_description": damage_description,
            "fee_amount": str(fee_amount) if fee_amount is not None else None,
            "fee_assessed": fine is not None,
            "fine_id": fine.id if fine is not None else None,
            "staff_id": staff_id,
            "notes": notes,
        },
    )

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to report equipment damaged")
        raise
    await db.refresh(checkout)
    return checkout


async def renew_equipment_checkout(
    db: AsyncSession,
    checkout_id: int,
    patron_id: int,
    notes: Optional[str] = None,
) -> EquipmentCheckout:
    result = await db.execute(
        select(EquipmentCheckout).where(
            EquipmentCheckout.id == checkout_id,
            EquipmentCheckout.user_id == patron_id,
        ).with_for_update()
    )
    checkout = result.scalar_one_or_none()

    if not checkout:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Checkout not found"
        )

    if checkout.status not in ["active", "overdue"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot renew this checkout"
        )

    # Get equipment
    equipment = await get_equipment(db, checkout.equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )

    # Check renewal limit
    if checkout.renewal_count >= equipment.max_renewals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Renewal limit reached ({checkout.renewal_count}/{equipment.max_renewals})"
        )

    # Check for pending reservations
    has_reservations = await _has_pending_reservations(db, equipment.id)
    if has_reservations:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot renew: equipment has pending reservations"
        )

    # Extend due date
    checkout.due_date = utc_now() + timedelta(days=equipment.max_checkout_days)
    checkout.renewal_count += 1
    checkout.last_renewed_at = utc_now()
    checkout.status = "active"

    if notes:
        checkout.checkout_notes = (checkout.checkout_notes or "") + f"\nRenewal: {notes}"

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        logger.exception("Failed to renew equipment checkout")
        raise
    await db.refresh(checkout)
    return checkout


async def get_patron_equipment_checkouts(
    db: AsyncSession,
    patron_id: int,
    include_history: bool = False,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[list[EquipmentCheckout], int]:
    query = select(EquipmentCheckout).where(EquipmentCheckout.user_id == patron_id)

    if not include_history:
        query = query.where(EquipmentCheckout.status.in_(["active", "overdue"]))

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(EquipmentCheckout.checked_out_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total


# ============================================================================
# Reservation Operations
# ============================================================================


async def create_reservation(
    db: AsyncSession,
    equipment_id: int,
    patron_id: int,
    start_date: date,
    end_date: date,
    purpose: Optional[str] = None,
    notes: Optional[str] = None,
) -> EquipmentReservation:
    # Validate equipment exists
    equipment = await get_equipment(db, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )

    # Check patron exists
    patron_result = await db.execute(select(User).where(User.id == patron_id))
    patron = patron_result.scalar_one_or_none()
    if not patron or not patron.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Patron not found or inactive"
        )

    # Check agreement if required
    if equipment.requires_agreement:
        has_agreement, _ = await check_patron_agreement(
            db, patron_id, equipment.equipment_type
        )
        if not has_agreement:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Equipment requires signed agreement before reservation"
            )

    # Check for conflicting reservations
    conflicts = await db.execute(
        select(EquipmentReservation).where(
            EquipmentReservation.equipment_id == equipment_id,
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
                EquipmentReservationStatus.READY_FOR_PICKUP,
            ]),
            or_(
                and_(
                    EquipmentReservation.start_date <= start_date,
                    EquipmentReservation.end_date >= start_date,
                ),
                and_(
                    EquipmentReservation.start_date <= end_date,
                    EquipmentReservation.end_date >= end_date,
                ),
                and_(
                    EquipmentReservation.start_date >= start_date,
                    EquipmentReservation.end_date <= end_date,
                ),
            ),
        )
    )
    conflicting = conflicts.scalars().all()

    # Check for existing active reservation by this patron
    existing = await db.execute(
        select(EquipmentReservation).where(
            EquipmentReservation.equipment_id == equipment_id,
            EquipmentReservation.user_id == patron_id,
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
                EquipmentReservationStatus.READY_FOR_PICKUP,
            ]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have an active reservation for this equipment"
        )

    # Calculate position (queue)
    position = len(conflicting) + 1

    # Create reservation
    reservation = EquipmentReservation(
        equipment_id=equipment_id,
        user_id=patron_id,
        start_date=start_date,
        end_date=end_date,
        position=position,
        purpose=purpose,
        notes=notes,
        status=EquipmentReservationStatus.PENDING if conflicting else EquipmentReservationStatus.CONFIRMED,
    )
    db.add(reservation)

    await db.commit()
    await db.refresh(reservation)
    return reservation


async def cancel_reservation(
    db: AsyncSession,
    reservation_id: int,
    user_id: int,
    is_staff: bool = False,
    reason: Optional[str] = None,
) -> EquipmentReservation:
    result = await db.execute(
        select(EquipmentReservation).where(
            EquipmentReservation.id == reservation_id
        ).with_for_update()
    )
    reservation = result.scalar_one_or_none()

    if not reservation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reservation not found"
        )

    # Only allow patron to cancel their own or staff to cancel any
    if not is_staff and reservation.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot cancel another patron's reservation"
        )

    if reservation.status in [EquipmentReservationStatus.COMPLETED, EquipmentReservationStatus.CANCELLED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel reservation with status: {reservation.status}"
        )

    reservation.status = EquipmentReservationStatus.CANCELLED
    reservation.cancelled_at = utc_now()
    reservation.cancelled_by_id = user_id
    reservation.cancellation_reason = reason

    # Promote next in queue
    await _promote_reservations(db, reservation.equipment_id)

    await db.commit()
    await db.refresh(reservation)
    return reservation


async def get_equipment_reservations(
    db: AsyncSession,
    equipment_id: int,
    include_past: bool = False,
) -> list[EquipmentReservation]:
    query = select(EquipmentReservation).where(
        EquipmentReservation.equipment_id == equipment_id
    )

    if not include_past:
        query = query.where(
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
                EquipmentReservationStatus.READY_FOR_PICKUP,
            ])
        )

    query = query.order_by(EquipmentReservation.position)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_patron_reservations(
    db: AsyncSession,
    patron_id: int,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[list[EquipmentReservation], int]:
    query = select(EquipmentReservation).where(
        EquipmentReservation.user_id == patron_id,
        EquipmentReservation.status.in_([
            EquipmentReservationStatus.PENDING,
            EquipmentReservationStatus.CONFIRMED,
            EquipmentReservationStatus.READY_FOR_PICKUP,
        ]),
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(EquipmentReservation.start_date).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total


# ============================================================================
# Maintenance Operations
# ============================================================================


async def schedule_maintenance(
    db: AsyncSession,
    equipment_id: int,
    maintenance_type: EquipmentMaintenanceType,
    scheduled_date: Optional[date] = None,
    description: Optional[str] = None,
    staff_id: Optional[int] = None,
) -> EquipmentMaintenance:
    equipment = await get_equipment(db, equipment_id)
    if not equipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found"
        )

    maintenance = EquipmentMaintenance(
        equipment_id=equipment_id,
        maintenance_type=maintenance_type,
        status=EquipmentMaintenanceStatus.SCHEDULED,
        description=description,
        scheduled_date=scheduled_date or date.today(),
        condition_before=equipment.condition,
        performed_by_id=staff_id,
    )
    db.add(maintenance)

    await db.commit()
    await db.refresh(maintenance)
    return maintenance


async def start_maintenance(
    db: AsyncSession,
    maintenance_id: int,
    staff_id: int,
) -> EquipmentMaintenance:
    result = await db.execute(
        select(EquipmentMaintenance).where(
            EquipmentMaintenance.id == maintenance_id
        ).with_for_update()
    )
    maintenance = result.scalar_one_or_none()

    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found"
        )

    if maintenance.status != EquipmentMaintenanceStatus.SCHEDULED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot start maintenance with status: {maintenance.status}"
        )

    # Update equipment status
    equipment = await get_equipment(db, maintenance.equipment_id)
    if equipment and equipment.status == EquipmentStatus.AVAILABLE:
        equipment.status = EquipmentStatus.IN_MAINTENANCE

    maintenance.status = EquipmentMaintenanceStatus.IN_PROGRESS
    maintenance.started_at = utc_now()
    maintenance.performed_by_id = staff_id

    await db.commit()
    await db.refresh(maintenance)
    return maintenance


async def complete_maintenance(
    db: AsyncSession,
    maintenance_id: int,
    staff_id: int,
    work_performed: str,
    condition_after: EquipmentCondition,
    issues_found: Optional[str] = None,
    parts_cost: Decimal = Decimal("0.00"),
    labor_cost: Decimal = Decimal("0.00"),
    external_vendor: Optional[str] = None,
    vendor_invoice: Optional[str] = None,
    requires_followup: bool = False,
    followup_notes: Optional[str] = None,
    followup_date: Optional[date] = None,
) -> EquipmentMaintenance:
    result = await db.execute(
        select(EquipmentMaintenance).where(
            EquipmentMaintenance.id == maintenance_id
        ).with_for_update()
    )
    maintenance = result.scalar_one_or_none()

    if not maintenance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Maintenance record not found"
        )

    if maintenance.status not in [EquipmentMaintenanceStatus.SCHEDULED, EquipmentMaintenanceStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot complete maintenance with status: {maintenance.status}"
        )

    # Update maintenance
    maintenance.status = EquipmentMaintenanceStatus.COMPLETED
    maintenance.completed_at = utc_now()
    maintenance.work_performed = work_performed
    maintenance.condition_after = condition_after
    maintenance.issues_found = issues_found
    maintenance.parts_cost = parts_cost
    maintenance.labor_cost = labor_cost
    maintenance.external_vendor = external_vendor
    maintenance.vendor_invoice = vendor_invoice
    maintenance.requires_followup = requires_followup
    maintenance.followup_notes = followup_notes
    maintenance.followup_date = followup_date
    maintenance.performed_by_id = staff_id

    # Update equipment
    equipment = await get_equipment(db, maintenance.equipment_id)
    if equipment:
        # Record condition change
        if equipment.condition != condition_after:
            condition_log = EquipmentConditionLog(
                equipment_id=equipment.id,
                previous_condition=equipment.condition,
                new_condition=condition_after,
                change_reason="Maintenance completed",
                maintenance_id=maintenance_id,
                recorded_by_id=staff_id,
            )
            db.add(condition_log)
            equipment.condition = condition_after

        # Update maintenance dates
        equipment.last_maintenance_date = date.today()
        if equipment.maintenance_schedule_days:
            equipment.next_maintenance_date = date.today() + timedelta(
                days=equipment.maintenance_schedule_days
            )

        # Check for next reservation before setting available
        next_reservation = await _get_next_reservation(db, equipment.id)
        if next_reservation:
            equipment.status = EquipmentStatus.RESERVED
            next_reservation.status = EquipmentReservationStatus.READY_FOR_PICKUP
            next_reservation.notified_at = utc_now()
            next_reservation.pickup_deadline = utc_now() + timedelta(days=2)
        else:
            equipment.status = EquipmentStatus.AVAILABLE

    await db.commit()
    await db.refresh(maintenance)
    return maintenance


async def get_maintenance_history(
    db: AsyncSession,
    equipment_id: int,
    page: int = 1,
    per_page: int = 20,
) -> Tuple[list[EquipmentMaintenance], int]:
    query = select(EquipmentMaintenance).where(
        EquipmentMaintenance.equipment_id == equipment_id
    )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    offset = (page - 1) * per_page
    query = query.order_by(EquipmentMaintenance.created_at.desc()).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total


async def get_due_maintenance(
    db: AsyncSession,
) -> list[Equipment]:
    today = date.today()
    result = await db.execute(
        select(Equipment).where(
            Equipment.status != EquipmentStatus.RETIRED,
            Equipment.next_maintenance_date <= today,
        ).order_by(Equipment.next_maintenance_date)
    )
    return list(result.scalars().all())


# ============================================================================
# Alert Operations
# ============================================================================


async def get_active_alerts(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 50,
    priority: Optional[str] = None,
    alert_type: Optional[str] = None,
) -> Tuple[list[EquipmentAlert], int]:
    query = select(EquipmentAlert).where(
        EquipmentAlert.status.in_(["active", "acknowledged"])
    )

    if priority:
        query = query.where(EquipmentAlert.priority == priority)
    if alert_type:
        query = query.where(EquipmentAlert.alert_type == alert_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate with priority ordering
    offset = (page - 1) * per_page
    query = query.order_by(
        # Urgent first
        EquipmentAlert.priority.desc(),
        EquipmentAlert.created_at.desc(),
    ).offset(offset).limit(per_page)

    result = await db.execute(query)
    items = result.scalars().all()

    return list(items), total


async def acknowledge_alert(
    db: AsyncSession,
    alert_id: int,
    staff_id: int,
    notes: Optional[str] = None,
) -> EquipmentAlert:
    result = await db.execute(
        select(EquipmentAlert).where(EquipmentAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.status = "acknowledged"
    alert.acknowledged_by_id = staff_id
    alert.acknowledged_at = utc_now()
    if notes:
        alert.message = (alert.message or "") + f"\nAcknowledged: {notes}"

    await db.commit()
    await db.refresh(alert)
    return alert


async def resolve_alert(
    db: AsyncSession,
    alert_id: int,
    staff_id: int,
    resolution_notes: str,
) -> EquipmentAlert:
    result = await db.execute(
        select(EquipmentAlert).where(EquipmentAlert.id == alert_id)
    )
    alert = result.scalar_one_or_none()

    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )

    alert.status = "resolved"
    alert.resolved_by_id = staff_id
    alert.resolved_at = utc_now()
    alert.resolution_notes = resolution_notes

    await db.commit()
    await db.refresh(alert)
    return alert


async def create_overdue_alerts(
    db: AsyncSession,
) -> int:
    now = utc_now()
    alerts_created = 0

    # Find overdue checkouts
    overdue_result = await db.execute(
        select(EquipmentCheckout).where(
            EquipmentCheckout.status.in_(["active", "overdue"]),
            EquipmentCheckout.due_date < now,
        )
    )
    overdue_checkouts = overdue_result.scalars().all()

    for checkout in overdue_checkouts:
        # Update status
        checkout.status = "overdue"

        days_overdue = (now - checkout.due_date).days

        # Check for existing alert
        existing_result = await db.execute(
            select(EquipmentAlert).where(
                EquipmentAlert.checkout_id == checkout.id,
                EquipmentAlert.alert_type.in_(["overdue", "severely_overdue"]),
                EquipmentAlert.status.in_(["active", "acknowledged"]),
            )
        )
        existing_alert = existing_result.scalar_one_or_none()

        # Determine priority based on days overdue
        # Equipment overdue is more urgent than books
        if days_overdue >= 14:
            alert_type = "severely_overdue"
            priority = "urgent"
        elif days_overdue >= 7:
            alert_type = "overdue"
            priority = "high"
        elif days_overdue >= 3:
            alert_type = "overdue"
            priority = "medium"
        else:
            alert_type = "overdue"
            priority = "medium"

        equipment = await get_equipment(db, checkout.equipment_id)
        equipment_name = equipment.name if equipment else "Unknown equipment"

        if existing_alert:
            # Update existing alert
            existing_alert.days_overdue = days_overdue
            existing_alert.alert_type = alert_type
            existing_alert.priority = priority
            existing_alert.escalation_level = min(days_overdue // 7, 3)
            existing_alert.last_escalated_at = now
        else:
            # Create new alert
            alert = EquipmentAlert(
                alert_type=alert_type,
                priority=priority,
                status="active",
                equipment_id=checkout.equipment_id,
                checkout_id=checkout.id,
                user_id=checkout.user_id,
                title=f"Overdue equipment: {equipment_name}",
                message=f"Equipment {days_overdue} day(s) overdue. Patron should be contacted.",
                days_overdue=days_overdue,
            )
            db.add(alert)
            alerts_created += 1

    await db.commit()
    return alerts_created


# ============================================================================
# Helper Functions
# ============================================================================


async def _get_active_reservation(
    db: AsyncSession,
    equipment_id: int,
    patron_id: int,
) -> Optional[EquipmentReservation]:
    result = await db.execute(
        select(EquipmentReservation).where(
            EquipmentReservation.equipment_id == equipment_id,
            EquipmentReservation.user_id == patron_id,
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.CONFIRMED,
                EquipmentReservationStatus.READY_FOR_PICKUP,
            ]),
        )
    )
    return result.scalar_one_or_none()


async def _get_next_reservation(
    db: AsyncSession,
    equipment_id: int,
) -> Optional[EquipmentReservation]:
    result = await db.execute(
        select(EquipmentReservation).where(
            EquipmentReservation.equipment_id == equipment_id,
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
            ]),
        ).order_by(EquipmentReservation.position)
    )
    return result.scalar_one_or_none()


async def _has_pending_reservations(
    db: AsyncSession,
    equipment_id: int,
) -> bool:
    result = await db.execute(
        select(func.count()).select_from(EquipmentReservation).where(
            EquipmentReservation.equipment_id == equipment_id,
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
                EquipmentReservationStatus.READY_FOR_PICKUP,
            ]),
        )
    )
    count = result.scalar() or 0
    return count > 0


async def _promote_reservations(
    db: AsyncSession,
    equipment_id: int,
) -> None:
    result = await db.execute(
        select(EquipmentReservation).where(
            EquipmentReservation.equipment_id == equipment_id,
            EquipmentReservation.status.in_([
                EquipmentReservationStatus.PENDING,
                EquipmentReservationStatus.CONFIRMED,
            ]),
        ).order_by(EquipmentReservation.position)
    )
    reservations = result.scalars().all()

    for i, reservation in enumerate(reservations, 1):
        reservation.position = i


async def _resolve_overdue_alerts(
    db: AsyncSession,
    checkout_id: int,
) -> None:
    result = await db.execute(
        select(EquipmentAlert).where(
            EquipmentAlert.checkout_id == checkout_id,
            EquipmentAlert.alert_type.in_(["overdue", "severely_overdue"]),
            EquipmentAlert.status.in_(["active", "acknowledged"]),
        )
    )
    alerts = result.scalars().all()

    for alert in alerts:
        alert.status = "resolved"
        alert.resolved_at = utc_now()
        alert.resolution_notes = "Equipment returned"
