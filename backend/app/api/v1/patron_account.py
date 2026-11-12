# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron Account & Billing API endpoints."""

from app.core.logging import get_logger
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.patron_account import TransactionType
from ...models.user import User
from ...schemas.patron_account import (
    AccountBalanceResponse,
    DepositRequest,
    StaffDepositRequest,
    RefundRequest,
    TransactionResponse,
    TransactionListResponse,
)
from ...services import account_service
from .dependencies import get_current_user, require_staff

logger = get_logger(__name__)
router = APIRouter(prefix="/patron/account", tags=["patron-account"])


@router.get("", response_model=AccountBalanceResponse)
async def get_account_balance(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current patron's account balance and info."""
    account = await account_service.get_balance(db, current_user.id)
    return AccountBalanceResponse.model_validate(account)


@router.get("/transactions", response_model=TransactionListResponse)
async def get_transactions(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    transaction_type: Optional[TransactionType] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transaction history with pagination."""
    transactions, total = await account_service.get_transactions(
        db, current_user.id, page=page, per_page=per_page,
        transaction_type=transaction_type,
    )
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        per_page=per_page,
    )


@router.post("/deposit", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def deposit_funds(
    request: DepositRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Deposit funds into patron's own account (online payment)."""
    transaction = await account_service.add_funds(
        db, current_user.id,
        amount=request.amount,
        payment_method=request.payment_method,
        notes=request.notes,
    )
    return TransactionResponse.model_validate(transaction)


# Staff endpoints
staff_router = APIRouter(prefix="/staff/patron", tags=["staff-patron-account"])


@staff_router.get("/{patron_id}/account", response_model=AccountBalanceResponse)
async def staff_get_account_balance(
    patron_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    account = await account_service.get_balance(db, patron_id)
    return AccountBalanceResponse.model_validate(account)


@staff_router.get("/{patron_id}/transactions", response_model=TransactionListResponse)
async def staff_get_transactions(
    patron_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    transaction_type: Optional[TransactionType] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    transactions, total = await account_service.get_transactions(
        db, patron_id, page=page, per_page=per_page,
        transaction_type=transaction_type,
    )
    return TransactionListResponse(
        items=[TransactionResponse.model_validate(t) for t in transactions],
        total=total,
        page=page,
        per_page=per_page,
    )


@staff_router.post("/{patron_id}/deposit", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def staff_deposit(
    patron_id: int,
    request: StaffDepositRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    transaction = await account_service.add_funds(
        db, patron_id,
        amount=request.amount,
        payment_method=request.payment_method,
        processed_by_id=current_user.id,
        notes=request.notes,
    )
    return TransactionResponse.model_validate(transaction)


@staff_router.post("/{patron_id}/refund", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED)
async def staff_refund(
    patron_id: int,
    request: RefundRequest,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    transaction = await account_service.refund(
        db, patron_id,
        amount=request.amount,
        reason=request.reason,
        processed_by_id=current_user.id,
        notes=request.notes,
    )
    return TransactionResponse.model_validate(transaction)
