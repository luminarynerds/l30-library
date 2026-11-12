# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Patron Self-Service Profile Edit & Fine Review API Endpoints.

NOTE: These patron self-service profile endpoints are not currently consumed
by the frontend, which uses /auth/me instead. Kept for potential future use
or third-party integrations.

Provides endpoints for patrons to:
- View and update their own profile (email, phone, address, preferences)
- Email changes require re-verification for security
- View their own fines, balances, and payment history
"""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...models.fine import Fine, FinePaymentHistory, FineStatus
from ...models.user import User, email_blind_hash
from .auth import get_current_user

logger = get_logger(__name__)
router = APIRouter(prefix="/patron/profile", tags=["patron-profile"])


# =============================================================================
# Schemas
# =============================================================================


class PatronProfileResponse(BaseModel):
    id: int
    email: str
    first_name: str
    last_name: str
    phone: str | None = None
    address: str | None = None
    library_card: str | None = None
    notice_preference: str | None = None
    preferred_contact_method: str | None = None
    language_preference: str | None = None
    accessibility_needs: str | None = None

    class Config:
        from_attributes = True


class PatronProfileUpdateRequest(BaseModel):
    phone: str | None = Field(None, max_length=50)
    address: str | None = Field(None, max_length=500)
    preferred_contact_method: str | None = Field(None, max_length=20)
    language_preference: str | None = Field(None, max_length=50)
    accessibility_needs: str | None = None
    notice_preference: str | None = Field(None, max_length=20)


class PatronEmailChangeRequest(BaseModel):
    new_email: EmailStr
    current_password: str


class PatronEmailChangeResponse(BaseModel):
    message: str
    new_email: str
    verification_required: bool = True


class PatronFineResponse(BaseModel):
    id: int
    fine_type: str
    status: str
    amount: float
    amount_paid: float
    balance: float
    description: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PatronFineListResponse(BaseModel):
    fines: list[PatronFineResponse]
    total_outstanding: float
    total_paid: float
    total_fines: int


class PatronPaymentHistoryEntry(BaseModel):
    id: int
    fine_id: int
    amount: float
    payment_method: str
    notes: str | None = None
    created_at: datetime | None = None

    class Config:
        from_attributes = True


class PatronPaymentHistoryResponse(BaseModel):
    payments: list[PatronPaymentHistoryEntry]
    total: int
    page: int
    per_page: int


# =============================================================================
# Profile Endpoints
# =============================================================================


@router.get("", response_model=PatronProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    """Get the current patron's profile information."""
    return PatronProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        address=current_user.address,
        library_card=current_user.library_card,
        notice_preference=str(current_user.notice_preference) if current_user.notice_preference else None,
        preferred_contact_method=current_user.preferred_contact_method,
        language_preference=current_user.language_preference,
        accessibility_needs=current_user.accessibility_needs,
    )


@router.put("", response_model=PatronProfileResponse)
@limiter.limit("10/minute")
async def update_my_profile(
    request: Request,
    update_data: PatronProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update the current patron's profile.

    Patrons can update: phone, address, contact preferences, language, accessibility needs.
    Name and email changes are handled separately for security reasons.
    """
    changes = update_data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    for field, value in changes.items():
        if field == "phone":
            current_user.set_phone(value)
        else:
            setattr(current_user, field, value)

    current_user.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(current_user)

    return PatronProfileResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        phone=current_user.phone,
        address=current_user.address,
        library_card=current_user.library_card,
        notice_preference=str(current_user.notice_preference) if current_user.notice_preference else None,
        preferred_contact_method=current_user.preferred_contact_method,
        language_preference=current_user.language_preference,
        accessibility_needs=current_user.accessibility_needs,
    )


@router.post("/change-email", response_model=PatronEmailChangeResponse)
@limiter.limit("3/hour")
async def request_email_change(
    request: Request,
    email_change: PatronEmailChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Request an email change. Verifies current password and checks for duplicates.

    The new email must be verified before the change takes effect.
    A verification token is sent to the new email address.
    """
    from ...core.security import verify_password_async, create_verification_token

    # Verify current password
    if not await verify_password_async(email_change.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )

    new_email = email_change.new_email.lower()

    # Check if same as current
    if new_email == current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New email is the same as your current email.",
        )

    # Check if email is already in use
    existing = await db.execute(select(User).where(User.email_hash == email_blind_hash(new_email)))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This email is already associated with another account.",
        )

    # Generate verification token for the new email
    token = create_verification_token()
    current_user.verification_token = token
    current_user.verification_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)
    # Store the pending new email in a way that doesn't break the current email
    # We use custom_fields temporarily to hold the pending email change
    import json
    pending_data = {"pending_email": new_email}
    current_user.custom_fields = json.dumps(pending_data)

    await db.commit()

    logger.info(
        "Email change requested for user %d: %s -> %s",
        current_user.id,
        current_user.email,
        new_email,
    )

    return PatronEmailChangeResponse(
        message="A verification email has been sent to your new email address. "
                "Please verify it within 24 hours to complete the change.",
        new_email=new_email,
        verification_required=True,
    )


# =============================================================================
# Fine Review Endpoints (Patron self-service)
# =============================================================================


@router.get("/fines", response_model=PatronFineListResponse)
async def get_my_fines(
    status_filter: Optional[str] = Query(None, description="Filter by status: unpaid, paid, waived, partial"),
    limit: int = Query(50, ge=1, le=200, description="Max fines to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current patron's fines summary.

    Returns all fines with totals for outstanding and paid amounts.
    """
    query = select(Fine).where(Fine.user_id == current_user.id)

    if status_filter:
        try:
            fine_status = FineStatus(status_filter)
            query = query.where(Fine.status == fine_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status filter. Use: unpaid, paid, waived, partial",
            ) from None

    # Compute totals via SQL instead of loading all fines into memory
    totals_query = select(
        func.coalesce(
            func.sum(Fine.amount - Fine.amount_paid).filter(
                Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
            ), 0
        ).label("total_outstanding"),
        func.coalesce(func.sum(Fine.amount_paid), 0).label("total_paid"),
        func.count(Fine.id).label("total_fines"),
    ).where(Fine.user_id == current_user.id)
    if status_filter:
        totals_query = totals_query.where(Fine.status == FineStatus(status_filter))
    totals_row = (await db.execute(totals_query)).one()

    total_outstanding = float(totals_row.total_outstanding)
    total_paid = float(totals_row.total_paid)
    total_fines = totals_row.total_fines

    # Paginated fines listing
    query = query.order_by(Fine.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    fines = result.scalars().all()

    fine_responses = [
        PatronFineResponse(
            id=f.id,
            fine_type=f.fine_type.value,
            status=f.status.value,
            amount=float(f.amount),
            amount_paid=float(f.amount_paid),
            balance=float(f.balance),
            description=f.description,
            created_at=f.created_at,
        )
        for f in fines
    ]

    return PatronFineListResponse(
        fines=fine_responses,
        total_outstanding=total_outstanding,
        total_paid=total_paid,
        total_fines=total_fines,
    )


@router.get("/fines/{fine_id}/payments", response_model=PatronPaymentHistoryResponse)
async def get_my_fine_payments(
    fine_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get payment history for a specific fine.

    Only returns payments for fines belonging to the current patron.
    """
    # Verify the fine belongs to this patron
    fine_result = await db.execute(
        select(Fine).where(Fine.id == fine_id, Fine.user_id == current_user.id)
    )
    fine = fine_result.scalar_one_or_none()
    if not fine:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Fine not found.",
        )

    # Get payment history
    offset = (page - 1) * per_page
    query = (
        select(FinePaymentHistory)
        .where(FinePaymentHistory.fine_id == fine_id)
        .order_by(FinePaymentHistory.created_at.desc())
    )

    # Count total
    from sqlalchemy import func
    count_result = await db.execute(
        select(func.count(FinePaymentHistory.id)).where(FinePaymentHistory.fine_id == fine_id)
    )
    total = count_result.scalar_one()

    # Paginate
    result = await db.execute(query.offset(offset).limit(per_page))
    payments = result.scalars().all()

    payment_responses = [
        PatronPaymentHistoryEntry(
            id=p.id,
            fine_id=p.fine_id,
            amount=float(p.amount),
            payment_method=str(p.payment_method) if p.payment_method else "unknown",
            notes=p.notes,
            created_at=p.created_at,
        )
        for p in payments
    ]

    return PatronPaymentHistoryResponse(
        payments=payment_responses,
        total=total,
        page=page,
        per_page=per_page,
    )
