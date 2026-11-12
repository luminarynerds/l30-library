# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Data Correction Request Endpoints."""

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.shortcuts import get_or_404
from ....models.audit_log import AuditAction
from ....models.user import User, UserRole
from ....models.privacy_ledger import CorrectionStatus, DataCorrectionLog
from ..auth import get_current_user
from ..dependencies import require_staff

from .schemas import DataCorrectionListResponse, DataCorrectionRequest, DataCorrectionResponse
from .helpers import create_audit_log

logger = get_logger(__name__)

# Fields patrons are allowed to request corrections for
CORRECTABLE_FIELDS = {
    "first_name", "last_name", "email", "phone", "address",
    "address_line1", "address_line2", "city", "state", "zip_code",
    "emergency_contact_name", "emergency_contact_phone",
    "language_preference", "accessibility_needs", "date_of_birth",
}

router = APIRouter()


@router.post("/correct", response_model=DataCorrectionResponse, status_code=status.HTTP_201_CREATED)
async def request_data_correction(
    request: Request,
    correction: DataCorrectionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request a correction to personal data.

    Creates a correction request with an edit trail. Some fields can be
    self-corrected immediately; others (like email, date_of_birth) require
    staff review.
    """
    if correction.field_name not in CORRECTABLE_FIELDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot correct field '{correction.field_name}'. Correctable fields: {sorted(CORRECTABLE_FIELDS)}"
        )

    # Get current value
    old_value = getattr(current_user, correction.field_name, None)
    old_value_str = str(old_value) if old_value is not None else None

    # Fields that can be self-corrected immediately (low-risk)
    self_correctable = {
        "phone", "address", "address_line1", "address_line2", "city",
        "state", "zip_code", "emergency_contact_name", "emergency_contact_phone",
        "language_preference", "accessibility_needs",
    }

    if correction.field_name in self_correctable:
        # Apply immediately
        if correction.field_name == "phone":
            current_user.set_phone(correction.new_value)
        else:
            setattr(current_user, correction.field_name, correction.new_value)
        correction_status = CorrectionStatus.APPLIED
    else:
        # Requires staff review (email, name, date_of_birth)
        correction_status = CorrectionStatus.PENDING

    log_entry = DataCorrectionLog(
        user_id=current_user.id,
        field_name=correction.field_name,
        old_value=old_value_str,
        new_value=correction.new_value,
        reason=correction.reason,
        status=correction_status,
        requested_by_user_id=current_user.id,
        processed_at=datetime.now(timezone.utc) if correction_status == CorrectionStatus.APPLIED else None,
    )
    db.add(log_entry)

    await create_audit_log(
        db=db,
        action=AuditAction.UPDATE_USER,
        target_user_id=current_user.id,
        details={
            "correction_request": True,
            "field": correction.field_name,
            "old_value": old_value_str,
            "new_value": correction.new_value,
            "reason": correction.reason,
            "auto_applied": correction_status == CorrectionStatus.APPLIED,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()
    await db.refresh(log_entry)

    return DataCorrectionResponse(
        id=log_entry.id,
        field_name=log_entry.field_name,
        old_value=log_entry.old_value,
        new_value=log_entry.new_value,
        reason=log_entry.reason,
        status=log_entry.status.value if hasattr(log_entry.status, 'value') else str(log_entry.status),
        created_at=log_entry.created_at.isoformat() if log_entry.created_at else datetime.now(timezone.utc).isoformat(),
    )


@router.get("/corrections", response_model=DataCorrectionListResponse)
async def get_my_corrections(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all data correction requests and their status.

    Shows the full edit trail for the patron's data corrections.
    """
    result = await db.execute(
        select(DataCorrectionLog)
        .where(DataCorrectionLog.user_id == current_user.id)
        .order_by(DataCorrectionLog.created_at.desc())
    )
    records = result.scalars().all()

    return DataCorrectionListResponse(
        records=[
            DataCorrectionResponse(
                id=r.id,
                field_name=r.field_name,
                old_value=r.old_value,
                new_value=r.new_value,
                reason=r.reason,
                status=r.status.value if hasattr(r.status, 'value') else str(r.status),
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in records
        ],
        total=len(records),
    )


# =============================================================================
# Staff: Process Data Correction Requests
# =============================================================================


@router.post("/staff/corrections/{correction_id}/approve")
async def staff_approve_correction(
    request: Request,
    correction_id: int,
    staff_notes: Optional[str] = None,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Staff approves and applies a data correction request.

    Only for corrections that require staff review (name, email, DOB).
    """
    correction = await get_or_404(db, DataCorrectionLog, correction_id, "Correction request not found")

    if correction.status != CorrectionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Correction is already {correction.status}"
        )

    # Apply the correction to the user record
    result = await db.execute(select(User).where(User.id == correction.user_id))
    target_user = result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found")

    setattr(target_user, correction.field_name, correction.new_value)

    correction.status = CorrectionStatus.APPLIED
    correction.processed_by_staff_id = current_user.id
    correction.processed_at = datetime.now(timezone.utc)
    correction.staff_notes = staff_notes

    await create_audit_log(
        db=db,
        action=AuditAction.UPDATE_USER,
        admin_id=current_user.id,
        target_user_id=correction.user_id,
        details={
            "correction_id": correction.id,
            "field": correction.field_name,
            "old_value": correction.old_value,
            "new_value": correction.new_value,
            "approved_by_staff": True,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    return {"message": "Correction approved and applied", "correction_id": correction.id}


@router.post("/staff/corrections/{correction_id}/reject")
async def staff_reject_correction(
    request: Request,
    correction_id: int,
    staff_notes: str = Body(..., description="Reason for rejection"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Staff rejects a data correction request with a reason."""
    correction = await get_or_404(db, DataCorrectionLog, correction_id, "Correction request not found")

    if correction.status != CorrectionStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Correction is already {correction.status}"
        )

    correction.status = CorrectionStatus.REJECTED
    correction.processed_by_staff_id = current_user.id
    correction.processed_at = datetime.now(timezone.utc)
    correction.staff_notes = staff_notes

    await db.commit()

    return {"message": "Correction rejected", "correction_id": correction.id, "reason": staff_notes}
