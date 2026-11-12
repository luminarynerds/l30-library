# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
SIP2 Terminal Management API Endpoints

Provides REST endpoints for managing SIP2 self-checkout terminals:
- Terminal registration and configuration
- Terminal status monitoring
- Transaction log viewing
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...core.logging import get_logger
from ...core.security import hash_password, verify_password
from ...models.sip2 import SIP2CommandType, SIP2Terminal, SIP2Transaction
from ...models.user import User

from .auth import get_current_user
from .dependencies import require_admin, require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/sip2", tags=["sip2"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class TerminalCreate(BaseModel):

    terminal_id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    institution_id: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=4, max_length=100)
    is_active: bool = True
    allow_checkout: bool = True
    allow_checkin: bool = True
    allow_renewal: bool = True
    allow_patron_info: bool = True
    settings: Optional[dict] = None


class TerminalUpdate(BaseModel):

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    location: Optional[str] = Field(None, max_length=200)
    institution_id: Optional[str] = Field(None, max_length=100)
    password: Optional[str] = Field(None, min_length=4, max_length=100)
    is_active: Optional[bool] = None
    allow_checkout: Optional[bool] = None
    allow_checkin: Optional[bool] = None
    allow_renewal: Optional[bool] = None
    allow_patron_info: Optional[bool] = None
    settings: Optional[dict] = None


class TerminalResponse(BaseModel):

    id: int
    terminal_id: str
    name: str
    description: Optional[str]
    location: Optional[str]
    institution_id: Optional[str]
    is_active: bool
    allow_checkout: bool
    allow_checkin: bool
    allow_renewal: bool
    allow_patron_info: bool
    settings: Optional[dict]
    last_seen_at: Optional[datetime]
    last_ip: Optional[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class TerminalListResponse(BaseModel):

    terminals: List[TerminalResponse]
    total: int
    page: int
    per_page: int


class TransactionResponse(BaseModel):

    id: int
    session_id: str
    terminal_id: Optional[str]
    institution_id: Optional[str]
    request_id: Optional[str]
    command: str
    patron_id: Optional[str]
    item_id: Optional[str]
    success: bool
    error_message: Optional[str]
    client_ip: Optional[str]
    created_at: datetime
    response_at: Optional[datetime]
    processing_time_ms: Optional[int]

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):

    transactions: List[TransactionResponse]
    total: int
    page: int
    per_page: int


class TransactionStatsResponse(BaseModel):

    total_transactions: int
    successful_transactions: int
    failed_transactions: int
    checkouts: int
    checkins: int
    renewals: int
    patron_lookups: int
    avg_processing_time_ms: Optional[float]


class TerminalStatsResponse(BaseModel):

    total_terminals: int
    active_terminals: int
    inactive_terminals: int
    terminals_online_today: int


# =============================================================================
# Terminal Management Endpoints
# =============================================================================


@router.get("/terminals", response_model=TerminalListResponse)
async def list_terminals(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    List all SIP2 terminals with pagination.

    Requires staff or admin role.
    """
    query = select(SIP2Terminal)

    # Apply filters
    if is_active is not None:
        query = query.where(SIP2Terminal.is_active == is_active)

    if search:
        search_filter = f"%{search}%"
        query = query.where(
            (SIP2Terminal.terminal_id.ilike(search_filter))
            | (SIP2Terminal.name.ilike(search_filter))
            | (SIP2Terminal.location.ilike(search_filter))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Apply pagination
    offset = (page - 1) * limit
    query = query.order_by(SIP2Terminal.name).offset(offset).limit(limit)

    result = await db.execute(query)
    terminals = result.scalars().all()

    return TerminalListResponse(
        terminals=[TerminalResponse.model_validate(t) for t in terminals],
        total=total,
        page=page,
        per_page=limit,
    )


@router.post("/terminals", response_model=TerminalResponse, status_code=status.HTTP_201_CREATED)
async def create_terminal(
    terminal: TerminalCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new SIP2 terminal.

    Requires admin role.
    """
    # Check if terminal ID already exists
    result = await db.execute(
        select(SIP2Terminal).where(SIP2Terminal.terminal_id == terminal.terminal_id)
    )
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Terminal with ID '{terminal.terminal_id}' already exists",
        )

    # Create terminal
    new_terminal = SIP2Terminal(
        terminal_id=terminal.terminal_id,
        name=terminal.name,
        description=terminal.description,
        location=terminal.location,
        institution_id=terminal.institution_id,
        password_hash=hash_password(terminal.password) if terminal.password else None,
        is_active=terminal.is_active,
        allow_checkout=terminal.allow_checkout,
        allow_checkin=terminal.allow_checkin,
        allow_renewal=terminal.allow_renewal,
        allow_patron_info=terminal.allow_patron_info,
        settings=terminal.settings,
    )

    db.add(new_terminal)
    await db.commit()
    await db.refresh(new_terminal)

    logger.info(
        "SIP2 terminal created",
        extra={
            "terminal_id": terminal.terminal_id,
            "created_by": current_user.id,
        },
    )

    return TerminalResponse.model_validate(new_terminal)


@router.get("/terminals/{terminal_id}", response_model=TerminalResponse)
async def get_terminal(
    terminal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get a specific SIP2 terminal by ID.

    Requires staff or admin role.
    """
    terminal = await get_or_404(db, SIP2Terminal, terminal_id, "Terminal not found")

    return TerminalResponse.model_validate(terminal)


@router.patch("/terminals/{terminal_id}", response_model=TerminalResponse)
async def update_terminal(
    terminal_id: str,
    updates: TerminalUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Update a SIP2 terminal.

    Requires admin role.
    """
    terminal = await get_or_404(db, SIP2Terminal, terminal_id, "Terminal not found")

    # Update fields
    update_data = updates.model_dump(exclude_unset=True)

    # Handle password separately
    if "password" in update_data:
        password = update_data.pop("password")
        if password:
            terminal.password_hash = hash_password(password)

    for field, value in update_data.items():
        setattr(terminal, field, value)

    terminal.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(terminal)

    logger.info(
        "SIP2 terminal updated",
        extra={
            "terminal_id": terminal_id,
            "updated_by": current_user.id,
            "fields": list(update_data.keys()),
        },
    )

    return TerminalResponse.model_validate(terminal)


@router.delete("/terminals/{terminal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_terminal(
    terminal_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Delete a SIP2 terminal.

    Requires admin role. This does not delete transaction history.
    """
    terminal = await get_or_404(db, SIP2Terminal, terminal_id, "Terminal not found")

    await db.delete(terminal)
    await db.commit()

    logger.info(
        "SIP2 terminal deleted",
        extra={
            "terminal_id": terminal_id,
            "deleted_by": current_user.id,
        },
    )


# =============================================================================
# Transaction Log Endpoints
# =============================================================================


@router.get("/transactions", response_model=TransactionListResponse)
async def list_transactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    terminal_id: Optional[str] = None,
    patron_id: Optional[str] = None,
    item_id: Optional[str] = None,
    command: Optional[str] = None,
    success: Optional[bool] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    List SIP2 transactions with filtering.

    Requires staff or admin role.
    """
    query = select(SIP2Transaction)

    # Apply filters
    if terminal_id:
        query = query.where(SIP2Transaction.terminal_id == terminal_id)

    if patron_id:
        query = query.where(SIP2Transaction.patron_id == patron_id)

    if item_id:
        query = query.where(SIP2Transaction.item_id == item_id)

    if command:
        try:
            cmd_enum = SIP2CommandType(command)
            query = query.where(SIP2Transaction.command == cmd_enum)
        except ValueError:
            pass  # Invalid command, ignore filter

    if success is not None:
        query = query.where(SIP2Transaction.success == success)

    if start_date:
        query = query.where(SIP2Transaction.created_at >= start_date)

    if end_date:
        query = query.where(SIP2Transaction.created_at <= end_date)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    result = await db.execute(count_query)
    total = result.scalar() or 0

    # Apply pagination and ordering
    offset = (page - 1) * limit
    query = query.order_by(SIP2Transaction.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    transactions = result.scalars().all()

    return TransactionListResponse(
        transactions=[
            TransactionResponse(
                id=t.id,
                session_id=t.session_id,
                terminal_id=t.terminal_id,
                institution_id=t.institution_id,
                request_id=t.request_id,
                command=str(t.command) if t.command else "",
                patron_id=t.patron_id,
                item_id=t.item_id,
                success=t.success,
                error_message=t.error_message,
                client_ip=t.client_ip,
                created_at=t.created_at,
                response_at=t.response_at,
                processing_time_ms=t.processing_time_ms,
            )
            for t in transactions
        ],
        total=total,
        page=page,
        per_page=limit,
    )


@router.get("/transactions/{transaction_id}")
async def get_transaction(
    transaction_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get a specific SIP2 transaction with full details.

    Requires staff or admin role.
    """
    transaction = await get_or_404(db, SIP2Transaction, transaction_id, "Transaction not found")

    return {
        "id": transaction.id,
        "session_id": transaction.session_id,
        "terminal_id": transaction.terminal_id,
        "institution_id": transaction.institution_id,
        "request_id": transaction.request_id,
        "command": str(transaction.command) if transaction.command else "",
        "patron_id": transaction.patron_id,
        "item_id": transaction.item_id,
        "user_id": transaction.user_id,
        "catalog_item_id": transaction.catalog_item_id,
        "checkout_id": transaction.checkout_id,
        "success": transaction.success,
        "error_message": transaction.error_message,
        "request_message": transaction.request_message,
        "response_message": transaction.response_message,
        "transaction_data": transaction.transaction_data,
        "client_ip": transaction.client_ip,
        "client_port": transaction.client_port,
        "created_at": transaction.created_at,
        "response_at": transaction.response_at,
        "processing_time_ms": transaction.processing_time_ms,
    }


# =============================================================================
# Statistics Endpoints
# =============================================================================


@router.get("/stats/terminals", response_model=TerminalStatsResponse)
async def get_terminal_stats(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get SIP2 terminal statistics.

    Requires staff or admin role.
    """
    # Total terminals
    result = await db.execute(select(func.count(SIP2Terminal.id)))
    total = result.scalar() or 0

    # Active terminals
    result = await db.execute(
        select(func.count(SIP2Terminal.id)).where(SIP2Terminal.is_active == True)
    )
    active = result.scalar() or 0

    # Terminals seen today
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(SIP2Terminal.id)).where(
            SIP2Terminal.last_seen_at >= today_start
        )
    )
    online_today = result.scalar() or 0

    return TerminalStatsResponse(
        total_terminals=total,
        active_terminals=active,
        inactive_terminals=total - active,
        terminals_online_today=online_today,
    )


@router.get("/stats/transactions", response_model=TransactionStatsResponse)
async def get_transaction_stats(
    days: int = Query(7, ge=1, le=90),
    terminal_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """
    Get SIP2 transaction statistics.

    Requires staff or admin role.
    """
    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    base_filter = SIP2Transaction.created_at >= start_date
    if terminal_id:
        base_filter = and_(base_filter, SIP2Transaction.terminal_id == terminal_id)

    # Total transactions
    result = await db.execute(
        select(func.count(SIP2Transaction.id)).where(base_filter)
    )
    total = result.scalar() or 0

    # Successful transactions
    result = await db.execute(
        select(func.count(SIP2Transaction.id)).where(
            and_(base_filter, SIP2Transaction.success == True)
        )
    )
    successful = result.scalar() or 0

    # Checkouts
    result = await db.execute(
        select(func.count(SIP2Transaction.id)).where(
            and_(
                base_filter,
                SIP2Transaction.command == SIP2CommandType.CHECKOUT_RESPONSE,
            )
        )
    )
    checkouts = result.scalar() or 0

    # Checkins
    result = await db.execute(
        select(func.count(SIP2Transaction.id)).where(
            and_(
                base_filter,
                SIP2Transaction.command == SIP2CommandType.CHECKIN_RESPONSE,
            )
        )
    )
    checkins = result.scalar() or 0

    # Renewals
    result = await db.execute(
        select(func.count(SIP2Transaction.id)).where(
            and_(
                base_filter,
                SIP2Transaction.command == SIP2CommandType.RENEW_RESPONSE,
            )
        )
    )
    renewals = result.scalar() or 0

    # Patron lookups
    result = await db.execute(
        select(func.count(SIP2Transaction.id)).where(
            and_(
                base_filter,
                SIP2Transaction.command == SIP2CommandType.PATRON_STATUS_RESPONSE,
            )
        )
    )
    patron_lookups = result.scalar() or 0

    # Average processing time
    result = await db.execute(
        select(func.avg(SIP2Transaction.processing_time_ms)).where(
            and_(base_filter, SIP2Transaction.processing_time_ms.isnot(None))
        )
    )
    avg_time = result.scalar()

    return TransactionStatsResponse(
        total_transactions=total,
        successful_transactions=successful,
        failed_transactions=total - successful,
        checkouts=checkouts,
        checkins=checkins,
        renewals=renewals,
        patron_lookups=patron_lookups,
        avg_processing_time_ms=round(avg_time, 2) if avg_time else None,
    )
