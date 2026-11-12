# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Outreach Deposit collection, refund, and application endpoints."""

from datetime import date, datetime
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.database import get_db
from ....core.logging import get_logger
from ....models.outreach import (
    OutreachPartner, OutreachDeposit, DepositApplication,
    DepositStatus
)
from ....models.user import User
from ....schemas.outreach import (
    OutreachDepositCreate, OutreachDepositRefund, OutreachDepositResponse,
    OutreachDepositListResponse, DepositApplicationCreate, DepositApplicationResponse,
)
from .helpers import require_staff

logger = get_logger(__name__)

router = APIRouter()


@router.post("/deposits", response_model=OutreachDepositResponse, status_code=201)
async def collect_deposit(
    deposit_data: OutreachDepositCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Collect a new deposit from a partner."""
    # Verify partner exists
    partner_query = select(OutreachPartner).where(OutreachPartner.id == deposit_data.partner_id)
    partner = (await db.execute(partner_query)).scalar_one_or_none()
    if not partner:
        raise HTTPException(status_code=404, detail="Partner not found")

    # Generate receipt number
    receipt_number = f"DEP-{datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(4).upper()}"

    deposit = OutreachDeposit(
        **deposit_data.model_dump(),
        receipt_number=receipt_number,
        collected_by_id=current_user.id,
        status=DepositStatus.HELD.value
    )
    db.add(deposit)
    await db.commit()
    await db.refresh(deposit)

    logger.info(f"Collected deposit ${deposit.amount} from partner {partner.name}",
                extra={"deposit_id": deposit.id, "partner_id": deposit_data.partner_id})

    # Build response with partner name
    response = OutreachDepositResponse.model_validate(deposit)
    response.partner_name = partner.name
    response.amount_remaining = deposit.amount - deposit.amount_applied - deposit.amount_refunded
    return response


@router.get("/deposits", response_model=OutreachDepositListResponse)
async def list_deposits(
    partner_id: Optional[int] = None,
    status: Optional[DepositStatus] = None,
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """List deposits with optional filtering."""
    query = select(OutreachDeposit).options(
        selectinload(OutreachDeposit.partner)
    )

    if partner_id:
        query = query.where(OutreachDeposit.partner_id == partner_id)
    if status:
        query = query.where(OutreachDeposit.status == status.value)

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(OutreachDeposit.collected_date.desc()).offset(offset).limit(limit)
    result = await db.execute(query)
    deposits = result.scalars().all()

    deposit_responses = []
    for d in deposits:
        response = OutreachDepositResponse.model_validate(d)
        response.partner_name = d.partner.name if d.partner else None
        response.amount_remaining = d.amount - d.amount_applied - d.amount_refunded
        deposit_responses.append(response)

    return OutreachDepositListResponse(
        deposits=deposit_responses,
        total=total,
        limit=limit,
        offset=offset
    )


@router.post("/deposits/{deposit_id}/refund", response_model=OutreachDepositResponse)
async def refund_deposit(
    deposit_id: int,
    refund_data: OutreachDepositRefund,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Refund all or part of a deposit."""
    query = select(OutreachDeposit).options(
        selectinload(OutreachDeposit.partner)
    ).where(OutreachDeposit.id == deposit_id)
    result = await db.execute(query)
    deposit = result.scalar_one_or_none()

    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    available = deposit.amount - deposit.amount_applied - deposit.amount_refunded
    if refund_data.refund_amount > available:
        raise HTTPException(
            status_code=400,
            detail=f"Refund amount exceeds available balance of ${available:.2f}"
        )

    deposit.amount_refunded += refund_data.refund_amount
    deposit.refund_reason = refund_data.refund_reason
    deposit.refund_date = date.today()
    deposit.refunded_by_id = current_user.id

    # Update status
    remaining = deposit.amount - deposit.amount_applied - deposit.amount_refunded
    if remaining <= 0:
        deposit.status = DepositStatus.REFUNDED.value

    await db.commit()
    await db.refresh(deposit)

    logger.info(f"Refunded ${refund_data.refund_amount} from deposit {deposit_id}",
                extra={"deposit_id": deposit_id})

    response = OutreachDepositResponse.model_validate(deposit)
    response.partner_name = deposit.partner.name if deposit.partner else None
    response.amount_remaining = remaining
    return response


@router.post("/deposits/{deposit_id}/apply", response_model=DepositApplicationResponse)
async def apply_deposit(
    deposit_id: int,
    application_data: DepositApplicationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff)
):
    """Apply deposit funds to fines or fees."""
    query = select(OutreachDeposit).where(OutreachDeposit.id == deposit_id)
    result = await db.execute(query)
    deposit = result.scalar_one_or_none()

    if not deposit:
        raise HTTPException(status_code=404, detail="Deposit not found")

    available = deposit.amount - deposit.amount_applied - deposit.amount_refunded
    if application_data.amount > available:
        raise HTTPException(
            status_code=400,
            detail=f"Application amount exceeds available balance of ${available:.2f}"
        )

    application = DepositApplication(
        deposit_id=deposit_id,
        amount=application_data.amount,
        reason=application_data.reason,
        fine_id=application_data.fine_id,
        bulk_checkout_id=application_data.bulk_checkout_id,
        applied_by_id=current_user.id,
        notes=application_data.notes
    )
    db.add(application)

    deposit.amount_applied += application_data.amount
    remaining = deposit.amount - deposit.amount_applied - deposit.amount_refunded
    if remaining <= 0:
        deposit.status = DepositStatus.FULLY_APPLIED.value
    else:
        deposit.status = DepositStatus.PARTIALLY_APPLIED.value

    await db.commit()
    await db.refresh(application)

    logger.info(f"Applied ${application_data.amount} from deposit {deposit_id}",
                extra={"deposit_id": deposit_id, "application_id": application.id})

    return application
