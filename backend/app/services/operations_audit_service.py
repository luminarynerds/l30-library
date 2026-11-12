# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.operations_audit_log import (
    OperationCategory,
    OperationsAuditLog,
    OperationType,
    PolicyChangeLog,
)
from ..models.user import User

logger = get_logger(__name__)


def _user_identifier(user: Optional[User]) -> Optional[str]:
    if user is None:
        return None
    parts = []
    if getattr(user, "library_card", None):
        parts.append(f"card:{user.library_card}")
    if getattr(user, "email", None):
        parts.append(f"email:{user.email}")
    if not parts:
        parts.append(f"id:{user.id}")
    return "|".join(parts)


def _item_identifier(item: Any) -> Optional[str]:
    if item is None:
        return None
    parts = []
    if getattr(item, "title", None):
        # Truncate title to keep identifier reasonable
        title = item.title[:100] if len(item.title) > 100 else item.title
        parts.append(f"title:{title}")
    if getattr(item, "isbn", None):
        parts.append(f"isbn:{item.isbn}")
    if not parts:
        parts.append(f"id:{getattr(item, 'id', '?')}")
    return "|".join(parts)


def _new_correlation_id() -> str:
    return str(uuid.uuid4())


async def _safe_add(db: AsyncSession, record: Any) -> bool:
    try:
        db.add(record)
        await db.flush()
        return True
    except Exception:  # noqa: BLE001 -- audit logging must not fail caller's transaction: swallow and report
        logger.exception("Failed to write operations audit log entry")
        # Expunge the failed record to avoid polluting the session
        try:
            db.expunge(record)
        except Exception:  # noqa: BLE001 -- best-effort session cleanup after audit log failure
            logger.debug("Failed to expunge audit record from session", exc_info=True)
        return False


# ---------------------------------------------------------------------------
# Circulation audit logging
# ---------------------------------------------------------------------------

async def log_checkout_created(
    db: AsyncSession,
    *,
    patron: User,
    item: Any,
    checkout: Any,
    staff: Optional[User] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.CHECKOUT_CREATED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=getattr(checkout, "item_id", None),
        item_identifier=_item_identifier(item),
        checkout_id=checkout.id,
        after_state={
            "checkout_id": checkout.id,
            "item_id": getattr(checkout, "item_id", None),
            "item_copy_id": getattr(checkout, "item_copy_id", None),
            "due_date": str(getattr(checkout, "due_date", None)),
            "status": str(getattr(checkout, "status", None)),
        },
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_checkout_returned(
    db: AsyncSession,
    *,
    patron: User,
    item: Any,
    checkout: Any,
    was_overdue: bool = False,
    staff: Optional[User] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.CHECKOUT_RETURNED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=getattr(checkout, "item_id", None),
        item_identifier=_item_identifier(item),
        checkout_id=checkout.id,
        after_state={
            "checkout_id": checkout.id,
            "returned_at": str(getattr(checkout, "returned_at", None)),
            "was_overdue": was_overdue,
            "renewal_count": getattr(checkout, "renewal_count", 0),
        },
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_checkout_renewed(
    db: AsyncSession,
    *,
    patron: User,
    checkout: Any,
    previous_due_date: Any,
    new_due_date: Any,
    staff: Optional[User] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.CHECKOUT_RENEWED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=getattr(checkout, "item_id", None),
        checkout_id=checkout.id,
        before_state={"due_date": str(previous_due_date)},
        after_state={
            "due_date": str(new_due_date),
            "renewal_count": getattr(checkout, "renewal_count", 0),
        },
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_hold_placed(
    db: AsyncSession,
    *,
    patron: User,
    item: Any,
    hold: Any,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.HOLD_PLACED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        item_id=getattr(hold, "item_id", None),
        item_identifier=_item_identifier(item),
        hold_id=hold.id,
        after_state={
            "hold_id": hold.id,
            "position": getattr(hold, "position", None),
            "status": str(getattr(hold, "status", None)),
        },
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_hold_cancelled(
    db: AsyncSession,
    *,
    patron: User,
    hold: Any,
    cancelled_by: str = "patron",
    reason: Optional[str] = None,
    staff: Optional[User] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.HOLD_CANCELLED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        hold_id=hold.id,
        before_state={
            "status": str(getattr(hold, "status", None)),
            "position": getattr(hold, "position", None),
        },
        reason=reason or f"Cancelled by {cancelled_by}",
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_hold_overridden(
    db: AsyncSession,
    *,
    staff: Optional[User],
    bumped_patron: Optional[User],
    item: Any,
    hold: Any,
    disposition: str,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.HOLD_OVERRIDDEN.value,
        patron_id=bumped_patron.id if bumped_patron else None,
        patron_identifier=_user_identifier(bumped_patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=getattr(item, "id", None),
        item_identifier=_item_identifier(item),
        hold_id=getattr(hold, "id", None),
        before_state={
            # Hardcoded: an override only ever acts on a ready hold, and the
            # caller mutates hold.status before calling this helper.
            "status": "ready",
            "position": getattr(hold, "position", None),
        },
        after_state={
            "disposition": disposition,
            "status": str(getattr(hold, "status", None)),
        },
        reason=f"Hold overridden by staff ({disposition})",
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# Fine audit logging
# ---------------------------------------------------------------------------

async def log_fine_assessed(
    db: AsyncSession,
    *,
    patron: User,
    fine: Any,
    checkout: Optional[Any] = None,
    staff: Optional[User] = None,
    correlation_id: Optional[str] = None,
) -> bool:
    amount_cents = int(fine.amount * 100) if hasattr(fine, "amount") else None
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.FINE.value,
        operation_type=OperationType.FINE_ASSESSED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        fine_id=fine.id,
        checkout_id=getattr(checkout, "id", getattr(fine, "checkout_id", None)),
        amount_cents=amount_cents,
        after_state={
            "fine_id": fine.id,
            "fine_type": str(getattr(fine, "fine_type", None)),
            "amount": str(fine.amount),
            "status": str(getattr(fine, "status", None)),
        },
        correlation_id=correlation_id,
    ))


async def log_fine_waived(
    db: AsyncSession,
    *,
    patron: User,
    fine: Any,
    staff: User,
    reason: str = "",
    ip_address: Optional[str] = None,
) -> bool:
    amount_cents = int(fine.amount * 100) if hasattr(fine, "amount") else None
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.FINE.value,
        operation_type=OperationType.FINE_WAIVED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id,
        staff_identifier=_user_identifier(staff),
        fine_id=fine.id,
        checkout_id=getattr(fine, "checkout_id", None),
        amount_cents=amount_cents,
        before_state={
            "status": "unpaid",
            "amount": str(fine.amount),
            "amount_paid": str(getattr(fine, "amount_paid", 0)),
        },
        after_state={
            "status": "waived",
            "waived_at": str(getattr(fine, "waived_at", None)),
        },
        reason=reason,
        ip_address=ip_address,
    ))


async def log_fine_paid(
    db: AsyncSession,
    *,
    patron: User,
    fine: Any,
    payment_amount_cents: int,
    payment_method: str = "unknown",
    is_partial: bool = False,
    staff: Optional[User] = None,
    receipt_number: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    op_type = OperationType.FINE_PARTIAL_PAYMENT if is_partial else OperationType.FINE_PAID
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.FINE.value,
        operation_type=op_type.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        fine_id=fine.id,
        amount_cents=payment_amount_cents,
        after_state={
            "fine_id": fine.id,
            "payment_method": payment_method,
            "receipt_number": receipt_number,
            "fine_status": str(getattr(fine, "status", None)),
            "remaining_balance": str(getattr(fine, "balance", None)),
        },
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# Patron audit logging
# ---------------------------------------------------------------------------

async def log_patron_created(
    db: AsyncSession,
    *,
    patron: User,
    staff: Optional[User] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.PATRON.value,
        operation_type=OperationType.PATRON_CREATED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        after_state={
            "role": str(getattr(patron, "role", None)),
            "patron_status": str(getattr(patron, "patron_status", None)),
            "home_branch_id": getattr(patron, "home_branch_id", None),
        },
        ip_address=ip_address,
    ))


async def log_patron_status_change(
    db: AsyncSession,
    *,
    patron: User,
    old_status: str,
    new_status: str,
    operation_type: OperationType,
    staff: Optional[User] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.PATRON.value,
        operation_type=operation_type.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        before_state={"patron_status": old_status},
        after_state={"patron_status": new_status},
        reason=reason,
        ip_address=ip_address,
    ))


async def log_patron_updated(
    db: AsyncSession,
    *,
    patron: User,
    changes: dict,
    staff: Optional[User] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.PATRON.value,
        operation_type=OperationType.PATRON_UPDATED.value,
        patron_id=patron.id,
        patron_identifier=_user_identifier(patron),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        before_state={k: v.get("old") for k, v in changes.items()},
        after_state={k: v.get("new") for k, v in changes.items()},
        reason=reason,
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# Catalog item audit logging
# ---------------------------------------------------------------------------

async def log_item_status_changed(
    db: AsyncSession,
    *,
    item: Any,
    old_status: str,
    new_status: str,
    staff: Optional[User] = None,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    op_type = OperationType.ITEM_STATUS_CHANGED
    if new_status == "withdrawn":
        op_type = OperationType.ITEM_WITHDRAWN
    elif new_status == "missing":
        op_type = OperationType.ITEM_MARKED_MISSING
    elif new_status == "damaged":
        op_type = OperationType.ITEM_MARKED_DAMAGED

    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CATALOG.value,
        operation_type=op_type.value,
        item_id=item.id,
        item_identifier=_item_identifier(item),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        before_state={"status": old_status},
        after_state={"status": new_status},
        reason=reason,
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_item_created(
    db: AsyncSession,
    *,
    item: Any,
    staff: Optional[User] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CATALOG.value,
        operation_type=OperationType.ITEM_CREATED.value,
        item_id=item.id,
        item_identifier=_item_identifier(item),
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        after_state={
            "item_type": str(getattr(item, "item_type", None)),
            "status": str(getattr(item, "status", None)),
            "title": getattr(item, "title", None),
        },
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# Account / financial audit logging
# ---------------------------------------------------------------------------

async def log_account_deposit(
    db: AsyncSession,
    *,
    patron_id: int,
    amount_cents: int,
    payment_method: str,
    receipt_number: Optional[str] = None,
    balance_before_cents: int = 0,
    balance_after_cents: int = 0,
    processed_by_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.ACCOUNT.value,
        operation_type=OperationType.ACCOUNT_DEPOSIT.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}",
        staff_id=processed_by_id,
        amount_cents=amount_cents,
        before_state={"balance_cents": balance_before_cents},
        after_state={
            "balance_cents": balance_after_cents,
            "payment_method": payment_method,
            "receipt_number": receipt_number,
        },
        ip_address=ip_address,
    ))


async def log_account_charge(
    db: AsyncSession,
    *,
    patron_id: int,
    amount_cents: int,
    description: str,
    receipt_number: Optional[str] = None,
    balance_before_cents: int = 0,
    balance_after_cents: int = 0,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.ACCOUNT.value,
        operation_type=OperationType.ACCOUNT_CHARGE.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}",
        amount_cents=amount_cents,
        before_state={"balance_cents": balance_before_cents},
        after_state={
            "balance_cents": balance_after_cents,
            "description": description,
            "receipt_number": receipt_number,
            "reference_type": reference_type,
            "reference_id": reference_id,
        },
        ip_address=ip_address,
    ))


async def log_account_refund(
    db: AsyncSession,
    *,
    patron_id: int,
    amount_cents: int,
    reason: str,
    receipt_number: Optional[str] = None,
    balance_before_cents: int = 0,
    balance_after_cents: int = 0,
    processed_by_id: Optional[int] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.ACCOUNT.value,
        operation_type=OperationType.ACCOUNT_REFUND.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}",
        staff_id=processed_by_id,
        amount_cents=amount_cents,
        before_state={"balance_cents": balance_before_cents},
        after_state={
            "balance_cents": balance_after_cents,
            "reason": reason,
            "receipt_number": receipt_number,
        },
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# Equipment audit logging
# ---------------------------------------------------------------------------

async def log_equipment_deposit_deducted(
    db: AsyncSession,
    *,
    patron_id: Optional[int],
    equipment_id: Optional[int],
    checkout_id: int,
    deposit_amount_cents: int,
    deduction_amount_cents: int,
    refund_amount_cents: int,
    reason: Optional[str] = None,
    staff: Optional[User] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.ACCOUNT.value,
        operation_type=OperationType.ACCOUNT_CHARGE.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}" if patron_id else None,
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=equipment_id,
        checkout_id=checkout_id,
        amount_cents=deduction_amount_cents,
        before_state={
            "deposit_amount_cents": deposit_amount_cents,
        },
        after_state={
            "event": "equipment_deposit_deducted",
            "equipment_id": equipment_id,
            "equipment_checkout_id": checkout_id,
            "deduction_amount_cents": deduction_amount_cents,
            "refund_amount_cents": refund_amount_cents,
        },
        reason=reason,
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_equipment_deposit_refunded(
    db: AsyncSession,
    *,
    patron_id: Optional[int],
    equipment_id: Optional[int],
    checkout_id: int,
    refund_amount_cents: int,
    deposit_amount_cents: int,
    staff: Optional[User] = None,
    correlation_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.ACCOUNT.value,
        operation_type=OperationType.ACCOUNT_REFUND.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}" if patron_id else None,
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=equipment_id,
        checkout_id=checkout_id,
        amount_cents=refund_amount_cents,
        before_state={
            "deposit_amount_cents": deposit_amount_cents,
        },
        after_state={
            "event": "equipment_deposit_refunded",
            "equipment_id": equipment_id,
            "equipment_checkout_id": checkout_id,
            "refund_amount_cents": refund_amount_cents,
        },
        correlation_id=correlation_id,
        ip_address=ip_address,
    ))


async def log_equipment_reported_lost(
    db: AsyncSession,
    *,
    patron_id: Optional[int],
    equipment_id: int,
    checkout_id: int,
    reason: str,
    replacement_fee_cents: Optional[int] = None,
    staff: Optional[User] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.CHECKOUT_MARKED_LOST.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}" if patron_id else None,
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=equipment_id,
        checkout_id=checkout_id,
        amount_cents=replacement_fee_cents,
        after_state={
            "event": "equipment_reported_lost",
            "equipment_id": equipment_id,
            "equipment_checkout_id": checkout_id,
            "replacement_fee_cents": replacement_fee_cents,
        },
        reason=reason,
        ip_address=ip_address,
    ))


async def log_equipment_reported_damaged(
    db: AsyncSession,
    *,
    patron_id: Optional[int],
    equipment_id: int,
    checkout_id: int,
    damage_description: str,
    fee_amount_cents: Optional[int] = None,
    staff: Optional[User] = None,
    ip_address: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.CIRCULATION.value,
        operation_type=OperationType.ITEM_MARKED_DAMAGED.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}" if patron_id else None,
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        item_id=equipment_id,
        checkout_id=checkout_id,
        amount_cents=fee_amount_cents,
        after_state={
            "event": "equipment_reported_damaged",
            "equipment_id": equipment_id,
            "equipment_checkout_id": checkout_id,
            "damage_description": damage_description,
            "fee_amount_cents": fee_amount_cents,
        },
        reason=damage_description,
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# Content moderation audit logging
# ---------------------------------------------------------------------------

async def log_ebook_review_decision(
    db: AsyncSession,
    *,
    ebook_id: int,
    ebook_title: str,
    author_id: int,
    author_name: str,
    decision: str,
    staff: User,
    notes: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    op_type = (
        OperationType.EBOOK_APPROVED if decision == "approve"
        else OperationType.EBOOK_DECLINED
    )
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.MODERATION.value,
        operation_type=op_type.value,
        staff_id=staff.id,
        staff_identifier=_user_identifier(staff),
        item_id=ebook_id,
        item_identifier=f"title:{ebook_title[:100]}|author:{author_name}",
        after_state={
            "ebook_id": ebook_id,
            "author_id": author_id,
            "decision": decision,
        },
        reason=notes,
        ip_address=ip_address,
    ))


# ---------------------------------------------------------------------------
# Policy change logging
# ---------------------------------------------------------------------------

async def log_policy_change(
    db: AsyncSession,
    *,
    staff: User,
    policy_type: str,
    policy_name: str,
    before_value: Optional[dict] = None,
    after_value: Optional[dict] = None,
    fields_changed: Optional[list] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> bool:
    record = PolicyChangeLog(
        policy_type=policy_type,
        policy_name=policy_name,
        changed_by_staff_id=staff.id,
        changed_by_identifier=_user_identifier(staff),
        before_value=before_value,
        after_value=after_value,
        fields_changed=fields_changed,
        reason=reason,
        ip_address=ip_address,
    )

    # Also log to operations audit for unified querying
    await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.POLICY.value,
        operation_type=OperationType.POLICY_ROLE_SETTINGS_CHANGED.value,
        staff_id=staff.id,
        staff_identifier=_user_identifier(staff),
        before_state=before_value,
        after_state=after_value,
        reason=reason or f"Policy changed: {policy_name}",
        ip_address=ip_address,
    ))

    return await _safe_add(db, record)


# ---------------------------------------------------------------------------
# Public computer session logging
# ---------------------------------------------------------------------------

async def log_computer_session_ended(
    db: AsyncSession,
    *,
    session_id: int,
    computer_id: Optional[int],
    patron_id: Optional[int],
    duration_minutes: Optional[int],
    logoff_reason: str,
    reset_trigger_emitted: bool,
    correlation_id: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.SYSTEM.value,
        operation_type=OperationType.COMPUTER_SESSION_ENDED.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}" if patron_id else None,
        after_state={
            "session_id": session_id,
            "computer_id": computer_id,
            "patron_id": patron_id,
            "duration_minutes": duration_minutes,
            "logoff_reason": logoff_reason,
            "reset_trigger_emitted": reset_trigger_emitted,
        },
        reason=logoff_reason,
        correlation_id=correlation_id,
    ))


async def log_computer_session_reopened(
    db: AsyncSession,
    *,
    session_id: int,
    computer_id: Optional[int],
    patron_id: Optional[int],
    reopened_by_id: int,
    seconds_since_end: int,
    correlation_id: Optional[str] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.SYSTEM.value,
        operation_type=OperationType.COMPUTER_SESSION_REOPENED.value,
        patron_id=patron_id,
        patron_identifier=f"id:{patron_id}" if patron_id else None,
        after_state={
            "session_id": session_id,
            "computer_id": computer_id,
            "patron_id": patron_id,
            "reopened_by_id": reopened_by_id,
            "seconds_since_end": seconds_since_end,
        },
        reason="staff_undo",
        correlation_id=correlation_id,
    ))


# ---------------------------------------------------------------------------
# System operation logging
# ---------------------------------------------------------------------------

async def log_system_operation(
    db: AsyncSession,
    *,
    operation_type: OperationType,
    details: Optional[dict] = None,
    reason: Optional[str] = None,
    correlation_id: Optional[str] = None,
    staff: Optional[User] = None,
) -> bool:
    return await _safe_add(db, OperationsAuditLog(
        category=OperationCategory.SYSTEM.value,
        operation_type=operation_type.value,
        staff_id=staff.id if staff else None,
        staff_identifier=_user_identifier(staff),
        after_state=details,
        reason=reason,
        correlation_id=correlation_id,
    ))
