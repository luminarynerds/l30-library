# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Admin-only endpoints for managing staff pay-rate history."""
from app.core.logging import get_logger
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....models.staff_pay_rate import StaffPayRate
from ....services.pay_rate_service import PayRateService
from ..dependencies import require_admin

router = APIRouter(prefix="/staff/pay-rates", tags=["staff-pay-rates"])
logger = get_logger(__name__)


class PayRateResponse(BaseModel):
    id: int
    staff_id: int
    hourly_rate: float
    effective_from: str
    effective_to: str | None
    notes: str | None
    created_at: str


class PayRateCreateRequest(BaseModel):
    staff_id: int
    hourly_rate: Decimal = Field(..., gt=0)
    effective_from: date
    notes: str | None = None


class PayRateUpdateRequest(BaseModel):
    notes: str | None = None
    effective_from: date | None = None


class CurrentRateEntry(BaseModel):
    staff_id: int
    staff_name: str
    role: str
    hourly_rate: float | None
    effective_from: str | None


def _to_response(r: StaffPayRate) -> PayRateResponse:
    return PayRateResponse(
        id=r.id,
        staff_id=r.staff_id,
        hourly_rate=float(r.hourly_rate),
        effective_from=r.effective_from.isoformat(),
        effective_to=r.effective_to.isoformat() if r.effective_to else None,
        notes=r.notes,
        created_at=r.created_at.isoformat(),
    )


@router.get("/active", response_model=list[CurrentRateEntry])
async def list_active(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = PayRateService(db)
    rows = await service.list_current()
    return [
        CurrentRateEntry(
            staff_id=u.id,
            staff_name=f"{u.first_name} {u.last_name}".strip(),
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            hourly_rate=float(r.hourly_rate) if r else None,
            effective_from=r.effective_from.isoformat() if r else None,
        )
        for u, r in rows
    ]


@router.get("/{staff_id}", response_model=list[PayRateResponse])
async def get_history(
    staff_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    rows = await PayRateService(db).list_history(staff_id)
    return [_to_response(r) for r in rows]


@router.post("", response_model=PayRateResponse, status_code=status.HTTP_201_CREATED)
async def set_rate(
    payload: PayRateCreateRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    audit = f"set by {admin_user.first_name} (admin id={admin_user.id})"
    full_notes = (payload.notes.strip() + " -- " + audit) if payload.notes else audit
    row = await PayRateService(db).set_rate(
        staff_id=payload.staff_id,
        hourly_rate=payload.hourly_rate,
        effective_from=payload.effective_from,
        notes=full_notes[:1000],
        set_by_id=admin_user.id,
    )
    return _to_response(row)


@router.patch("/{rate_id}", response_model=PayRateResponse)
async def amend_rate(
    rate_id: int,
    payload: PayRateUpdateRequest,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(select(StaffPayRate).where(StaffPayRate.id == rate_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Pay rate not found")

    audit = f"amended by {admin_user.first_name} (admin id={admin_user.id})"
    if payload.notes is not None:
        existing = (row.notes or "").strip()
        new_notes = (payload.notes.strip() + " -- " + audit) if payload.notes.strip() else audit
        row.notes = (f"{existing}; {new_notes}" if existing else new_notes)[:1000]
    if payload.effective_from is not None:
        row.effective_from = payload.effective_from

    await db.flush()
    return _to_response(row)


@router.delete("/{rate_id}", status_code=204)
async def revert_rate(
    rate_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    from sqlalchemy import select
    result = await db.execute(select(StaffPayRate).where(StaffPayRate.id == rate_id))
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Pay rate not found")
    await db.delete(row)
    await db.flush()
    return None
