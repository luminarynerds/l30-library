# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Cash Drawer API endpoints for daily reconciliation and till balancing."""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.cash_drawer import CashDrawer, CashDrawerSession, CashTransaction
from ...schemas.cash_drawer import (
    ApproveSessionRequest,
    CashDrawerCreate,
    CashDrawerResponse,
    CashDrawerSessionResponse,
    CashDrawerUpdate,
    CashTransactionResponse,
    CloseSessionRequest,
    CreateTransactionRequest,
    OpenSessionRequest,
    SessionHistoryResponse,
    SessionSummary,
    TransactionListResponse,
)
from ...services import cash_drawer_service as svc
from .auth import get_current_user
from .dependencies import require_staff

logger = get_logger(__name__)
router = APIRouter(prefix="/cash-drawers", tags=["cash-drawers"])


def _staff_name(user) -> str:
    return f"{user.first_name or ''} {user.last_name or ''}".strip() or user.email


# --- Drawer CRUD ---

@router.get("", response_model=list[CashDrawerResponse])
async def list_drawers(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    return await svc.list_drawers(db, active_only=active_only)


@router.post("", response_model=CashDrawerResponse, status_code=status.HTTP_201_CREATED)
async def create_drawer(
    data: CashDrawerCreate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    drawer = await svc.create_drawer(db, **data.model_dump())
    await db.commit()
    return drawer


@router.patch("/{drawer_id}", response_model=CashDrawerResponse)
async def update_drawer(
    drawer_id: int,
    data: CashDrawerUpdate,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    drawer = await get_or_404(db, CashDrawer, drawer_id)
    drawer = await svc.update_drawer(db, drawer, **data.model_dump(exclude_unset=True))
    await db.commit()
    return drawer


@router.delete("/{drawer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_drawer(
    drawer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    drawer = await get_or_404(db, CashDrawer, drawer_id)
    drawer.is_active = False
    await db.commit()


# --- Session Lifecycle ---

@router.post("/{drawer_id}/open", response_model=CashDrawerSessionResponse, status_code=status.HTTP_201_CREATED)
async def open_session(
    drawer_id: int,
    data: OpenSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    drawer = await get_or_404(db, CashDrawer, drawer_id)
    if not drawer.is_active:
        raise HTTPException(status_code=400, detail="Drawer is not active")
    try:
        session = await svc.open_session(db, drawer_id, current_user.id, data.opening_float)
        await db.commit()
        return CashDrawerSessionResponse(
            **{c.name: getattr(session, c.name) for c in session.__table__.columns},
            opener_name=_staff_name(current_user),
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.get("/{drawer_id}/current-session", response_model=CashDrawerSessionResponse)
async def get_current_session(
    drawer_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    session = await svc.get_active_session(db, drawer_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    totals = await svc.compute_session_totals(db, session.id)
    return CashDrawerSessionResponse(
        **{c.name: getattr(session, c.name) for c in session.__table__.columns},
        summary=SessionSummary(**totals),
    )


@router.post("/{drawer_id}/close", response_model=CashDrawerSessionResponse)
async def close_session(
    drawer_id: int,
    data: CloseSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    session = await svc.get_active_session(db, drawer_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active session")
    try:
        session = await svc.close_session(
            db, session, current_user.id,
            data.counted_total, data.denomination_breakdown, data.notes,
        )
        await db.commit()
        totals = await svc.compute_session_totals(db, session.id)
        return CashDrawerSessionResponse(
            **{c.name: getattr(session, c.name) for c in session.__table__.columns},
            summary=SessionSummary(**totals),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post("/sessions/{session_id}/approve", response_model=CashDrawerSessionResponse)
async def approve_session(
    session_id: int,
    data: ApproveSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    session = await get_or_404(db, CashDrawerSession, session_id)
    if session.closed_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot approve your own cash drawer session",
        )
    try:
        session = await svc.approve_session(db, session, current_user.id, data.notes)
        await db.commit()
        return CashDrawerSessionResponse(
            **{c.name: getattr(session, c.name) for c in session.__table__.columns},
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# --- Transactions ---

@router.post("/sessions/{session_id}/transactions", response_model=CashTransactionResponse, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    session_id: int,
    data: CreateTransactionRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    try:
        txn = await svc.log_transaction(
            db, session_id, current_user.id,
            direction=data.direction,
            category=data.category,
            amount=data.amount,
            amount_tendered=data.amount_tendered,
            description=data.description,
            reference_type=data.reference_type,
            reference_id=data.reference_id,
        )
        await db.commit()
        return CashTransactionResponse(
            **{c.name: getattr(txn, c.name) for c in txn.__table__.columns},
            staff_name=_staff_name(current_user),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/sessions/{session_id}/transactions", response_model=TransactionListResponse)
async def list_transactions(
    session_id: int,
    include_voided: bool = Query(False),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    txns = await svc.get_session_transactions(db, session_id, include_voided)
    return TransactionListResponse(transactions=txns, total=len(txns))


@router.delete("/sessions/{session_id}/transactions/{txn_id}", response_model=CashTransactionResponse)
async def void_transaction(
    session_id: int,
    txn_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    txn = await get_or_404(db, CashTransaction, txn_id)
    if txn.session_id != session_id:
        raise HTTPException(status_code=404, detail="Transaction not in this session")
    try:
        txn = await svc.void_transaction(db, txn)
        await db.commit()
        return txn
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


# --- History ---

@router.get("/{drawer_id}/history", response_model=SessionHistoryResponse)
async def get_session_history(
    drawer_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    count_result = await db.execute(
        select(sqlfunc.count()).select_from(CashDrawerSession).where(
            CashDrawerSession.drawer_id == drawer_id,
            CashDrawerSession.status == "closed",
        )
    )
    total = count_result.scalar() or 0
    result = await db.execute(
        select(CashDrawerSession)
        .where(CashDrawerSession.drawer_id == drawer_id)
        .where(CashDrawerSession.status == "closed")
        .order_by(CashDrawerSession.closed_at.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    )
    sessions = list(result.scalars().all())
    return SessionHistoryResponse(sessions=sessions, total=total, page=page, per_page=per_page)


# --- PDF Reports ---

@router.get("/sessions/{session_id}/reconciliation-report")
async def get_reconciliation_report(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    from starlette.responses import StreamingResponse
    from io import BytesIO
    from ...services.cash_drawer_pdf import generate_reconciliation_pdf

    session = await get_or_404(db, CashDrawerSession, session_id)
    drawer = await get_or_404(db, CashDrawer, session.drawer_id)
    txns = await svc.get_session_transactions(db, session_id, include_voided=True)

    # Fetch names
    from ...models.user import User
    opener = await db.get(User, session.opened_by) if session.opened_by else None
    closer = await db.get(User, session.closed_by) if session.closed_by else None
    opener_name = _staff_name(opener) if opener else ""
    closer_name = _staff_name(closer) if closer else ""

    pdf_bytes = generate_reconciliation_pdf(session, txns, drawer, opener_name, closer_name)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=reconciliation-{session_id}.pdf"},
    )


@router.get("/sessions/{session_id}/deposit-slip")
async def get_deposit_slip(
    session_id: int,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(require_staff),
):
    from starlette.responses import StreamingResponse
    from io import BytesIO
    from ...services.cash_drawer_pdf import generate_deposit_slip_pdf

    session = await get_or_404(db, CashDrawerSession, session_id)
    drawer = await get_or_404(db, CashDrawer, session.drawer_id)

    from ...models.user import User
    closer = await db.get(User, session.closed_by) if session.closed_by else None
    prepared_by = _staff_name(closer) if closer else ""

    pdf_bytes = generate_deposit_slip_pdf(session, drawer, prepared_by)
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=deposit-slip-{session_id}.pdf"},
    )
