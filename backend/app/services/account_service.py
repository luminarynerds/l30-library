# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
import uuid
from decimal import Decimal
from typing import Callable, Optional, Tuple, List

from fastapi import HTTPException, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.patron_account import (
    PatronAccount, PatronTransaction,
    TransactionType, TransactionStatus, AccountPaymentMethod
)
from app.models.user import User
from app.core.audit_log import audit_log_event
from app.services import operations_audit_service as ops_audit

logger = get_logger(__name__)

# Low balance notification callbacks
_low_balance_callbacks: List[Callable] = []


def register_low_balance_callback(callback: Callable) -> None:
    _low_balance_callbacks.append(callback)


async def _check_low_balance(account: PatronAccount) -> None:
    if account.balance <= account.low_balance_threshold:
        logger.warning(
            "Low balance alert: patron %d balance $%s (threshold $%s)",
            account.patron_id, account.balance, account.low_balance_threshold,
        )
        for callback in _low_balance_callbacks:
            try:
                result = callback(account.patron_id, account.balance, account.low_balance_threshold)
                if hasattr(result, '__await__'):
                    await result
            except Exception:
                logger.exception("Low balance callback failed for patron %d", account.patron_id)


def _generate_receipt() -> str:
    return f"RCP-{uuid.uuid4().hex[:12].upper()}"


async def get_or_create_account(
    db: AsyncSession, patron_id: int, *, for_update: bool = False
) -> PatronAccount:
    query = select(PatronAccount).where(PatronAccount.patron_id == patron_id)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    account = result.scalar_one_or_none()
    if not account:
        account = PatronAccount(patron_id=patron_id)
        db.add(account)
        await db.flush()
        if for_update:
            # Re-fetch with lock after insert
            result = await db.execute(
                select(PatronAccount)
                .where(PatronAccount.patron_id == patron_id)
                .with_for_update()
            )
            account = result.scalar_one()
    return account


async def get_balance(db: AsyncSession, patron_id: int) -> PatronAccount:
    return await get_or_create_account(db, patron_id)


async def add_funds(
    db: AsyncSession,
    patron_id: int,
    amount: Decimal,
    payment_method: AccountPaymentMethod,
    processed_by_id: Optional[int] = None,
    notes: Optional[str] = None,
) -> PatronTransaction:
    account = await get_or_create_account(db, patron_id, for_update=True)

    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is inactive")

    balance_before = account.balance
    account.balance += amount
    account.total_deposited += amount
    account.last_deposit_at = func.now()

    transaction = PatronTransaction(
        account_id=account.id,
        transaction_type=TransactionType.DEPOSIT,
        status=TransactionStatus.COMPLETED,
        amount=amount,
        balance_before=balance_before,
        balance_after=account.balance,
        payment_method=payment_method,
        description=f"Deposit via {payment_method.value}",
        processed_by_id=processed_by_id,
        receipt_number=_generate_receipt(),
        notes=notes,
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)

    logger.info(f"Deposit of ${amount} for patron {patron_id}. New balance: ${account.balance}")

    # Audit: DB-queryable trail
    await ops_audit.log_account_deposit(
        db, patron_id=patron_id, amount_cents=int(amount * 100),
        payment_method=payment_method.value,
        receipt_number=transaction.receipt_number,
        balance_before_cents=int(balance_before * 100),
        balance_after_cents=int(account.balance * 100),
        processed_by_id=processed_by_id,
    )
    # Audit: tamper-evident trail
    audit_log_event(
        event_type="PAYMENT_PROCESSED", user_id=patron_id, severity="INFO",
        details={"amount": str(amount), "method": payment_method.value,
                 "receipt": transaction.receipt_number},
    )

    return transaction


async def charge(
    db: AsyncSession,
    patron_id: int,
    amount: Decimal,
    description: str,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None,
) -> PatronTransaction:
    # Lock the account row to prevent concurrent balance modifications
    result = await db.execute(
        select(PatronAccount)
        .where(PatronAccount.patron_id == patron_id)
        .with_for_update()
    )
    account = result.scalar_one_or_none()
    if not account:
        account = PatronAccount(patron_id=patron_id)
        db.add(account)
        await db.flush()

    if not account.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is inactive")

    if account.balance < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient funds. Balance: ${account.balance}, Required: ${amount}"
        )

    balance_before = account.balance
    account.balance -= amount
    account.total_spent += amount
    account.last_charge_at = func.now()

    transaction = PatronTransaction(
        account_id=account.id,
        transaction_type=TransactionType.CHARGE,
        status=TransactionStatus.COMPLETED,
        amount=amount,
        balance_before=balance_before,
        balance_after=account.balance,
        payment_method=AccountPaymentMethod.SYSTEM,
        description=description,
        reference_type=reference_type,
        reference_id=reference_id,
        receipt_number=_generate_receipt(),
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)

    logger.info(f"Charge of ${amount} for patron {patron_id}: {description}")

    # Audit: DB-queryable trail
    await ops_audit.log_account_charge(
        db, patron_id=patron_id, amount_cents=int(amount * 100),
        description=description, receipt_number=transaction.receipt_number,
        balance_before_cents=int(balance_before * 100),
        balance_after_cents=int(account.balance * 100),
        reference_type=reference_type, reference_id=reference_id,
    )

    await _check_low_balance(account)
    return transaction


async def refund(
    db: AsyncSession,
    patron_id: int,
    amount: Decimal,
    reason: str,
    processed_by_id: int,
    notes: Optional[str] = None,
) -> PatronTransaction:
    account = await get_or_create_account(db, patron_id, for_update=True)

    balance_before = account.balance
    account.balance += amount

    transaction = PatronTransaction(
        account_id=account.id,
        transaction_type=TransactionType.REFUND,
        status=TransactionStatus.COMPLETED,
        amount=amount,
        balance_before=balance_before,
        balance_after=account.balance,
        payment_method=AccountPaymentMethod.SYSTEM,
        description=f"Refund: {reason}",
        processed_by_id=processed_by_id,
        receipt_number=_generate_receipt(),
        notes=notes,
    )
    db.add(transaction)
    await db.flush()
    await db.refresh(transaction)

    logger.info(f"Refund of ${amount} for patron {patron_id}: {reason}")

    # Audit: DB-queryable trail
    await ops_audit.log_account_refund(
        db, patron_id=patron_id, amount_cents=int(amount * 100),
        reason=reason, receipt_number=transaction.receipt_number,
        balance_before_cents=int(balance_before * 100),
        balance_after_cents=int(account.balance * 100),
        processed_by_id=processed_by_id,
    )
    # Audit: tamper-evident trail
    audit_log_event(
        event_type="REFUND_PROCESSED", user_id=patron_id, severity="INFO",
        details={"amount": str(amount), "reason": reason,
                 "receipt": transaction.receipt_number,
                 "processed_by": processed_by_id},
    )

    return transaction


async def get_transactions(
    db: AsyncSession,
    patron_id: int,
    page: int = 1,
    per_page: int = 20,
    transaction_type: Optional[TransactionType] = None,
) -> Tuple[List[PatronTransaction], int]:
    account = await get_or_create_account(db, patron_id)

    query = select(PatronTransaction).where(
        PatronTransaction.account_id == account.id
    )

    if transaction_type:
        query = query.where(PatronTransaction.transaction_type == transaction_type)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch page
    query = query.order_by(PatronTransaction.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)

    result = await db.execute(query)
    transactions = list(result.scalars().all())

    return transactions, total
