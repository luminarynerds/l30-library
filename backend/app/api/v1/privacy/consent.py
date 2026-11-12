# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Consent Records and Data Sharing Disclosure Endpoints."""

import json
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
from ....models.privacy_ledger import (
    ConsentRecord,
    ConsentMethod,
    ConsentStatus,
    ConsentType,
    DataSharingLog,
    DataSharingPurpose,
)
from ..auth import get_current_user

from .schemas import (
    ConsentRecordResponse,
    ConsentRecordsListResponse,
    DataSharingListResponse,
    DataSharingRecordResponse,
)
from .helpers import create_audit_log

logger = get_logger(__name__)

router = APIRouter()


@router.get("/consent-records", response_model=ConsentRecordsListResponse)
async def get_my_consent_records(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get all consent records for the authenticated patron.

    Answers: "I never consented to this" -- by providing a complete audit trail
    of when, how, and for what purpose consent was given or withdrawn.
    """
    result = await db.execute(
        select(ConsentRecord)
        .where(ConsentRecord.user_id == current_user.id)
        .order_by(ConsentRecord.created_at.desc())
    )
    records = result.scalars().all()

    return ConsentRecordsListResponse(
        records=[
            ConsentRecordResponse(
                id=r.id,
                consent_type=r.consent_type.value if hasattr(r.consent_type, 'value') else str(r.consent_type),
                status=r.status.value if hasattr(r.status, 'value') else str(r.status),
                method=r.method.value if hasattr(r.method, 'value') else str(r.method),
                policy_version=r.policy_version,
                details=r.details,
                expires_at=r.expires_at.isoformat() if r.expires_at else None,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in records
        ],
        total=len(records),
    )


@router.post("/consent-records/withdraw")
async def withdraw_consent(
    request: Request,
    consent_type: str = Body(..., description="The consent type to withdraw"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Withdraw a specific type of consent.

    Creates a new consent record with status WITHDRAWN and updates
    the related user settings accordingly.
    """
    # Validate consent_type
    try:
        ct = ConsentType(consent_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid consent type. Valid types: {[t.value for t in ConsentType]}"
        ) from None

    # Record the withdrawal
    withdrawal = ConsentRecord(
        user_id=current_user.id,
        consent_type=ct,
        status=ConsentStatus.WITHDRAWN,
        method=ConsentMethod.WEB_FORM,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
        details={"action": "patron_initiated_withdrawal"},
    )
    db.add(withdrawal)

    # Apply setting changes based on consent type
    if ct == ConsentType.READING_HISTORY_TRACKING:
        current_user.track_reading_history = False
    elif ct == ConsentType.EMAIL_NOTIFICATIONS:
        current_user.notification_frequency = "never"
    elif ct == ConsentType.STAFF_ACCESS_TO_HISTORY:
        current_user.allow_staff_access_to_history = False

    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        target_user_id=current_user.id,
        details={
            "consent_type": ct.value,
            "new_status": "WITHDRAWN",
            "method": "web_form",
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    return {"message": f"Consent for {ct.value} has been withdrawn", "consent_type": ct.value}


# =============================================================================
# Data Sharing Disclosure - "Who have you shared my data with?"
# =============================================================================


@router.get("/data-sharing", response_model=DataSharingListResponse)
async def get_my_data_sharing_log(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a complete log of every instance where the patron's data was shared
    with a third party.

    Answers: "Who have you shared my data with?" -- including what data was shared,
    to whom, for what purpose, and the legal basis for sharing.
    """
    result = await db.execute(
        select(DataSharingLog)
        .where(DataSharingLog.user_id == current_user.id)
        .order_by(DataSharingLog.created_at.desc())
    )
    records = result.scalars().all()

    return DataSharingListResponse(
        records=[
            DataSharingRecordResponse(
                id=r.id,
                recipient_name=r.recipient_name,
                recipient_type=r.recipient_type,
                purpose=r.purpose.value if hasattr(r.purpose, 'value') else str(r.purpose),
                data_categories=r.data_categories if r.data_categories else [],
                legal_basis=r.legal_basis,
                patron_notified=r.patron_notified,
                patron_notified_at=r.patron_notified_at.isoformat() if r.patron_notified_at else None,
                notes=r.notes,
                created_at=r.created_at.isoformat() if r.created_at else None,
            )
            for r in records
        ],
        total=len(records),
    )


# =============================================================================
# Staff: Record Data Sharing (for logging third-party disclosures)
# =============================================================================


@router.post("/staff/data-sharing", status_code=status.HTTP_201_CREATED)
async def staff_record_data_sharing(
    request: Request,
    patron_id: int,
    recipient_name: str,
    recipient_type: Optional[str] = None,
    purpose: str = "LEGAL_COMPLIANCE",
    data_categories: str = "[]",
    legal_basis: Optional[str] = None,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None,
    notify_patron: bool = True,
    notes: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Staff records an instance of patron data being shared with a third party.

    This must be called whenever patron data is disclosed to any external entity
    (law enforcement, vendors, consortiums, etc.) to maintain a complete
    data sharing ledger.
    """
    if current_user.role not in [UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Staff access required")

    # Validate patron exists
    await get_or_404(db, User, patron_id, "Patron not found")

    # Validate purpose
    try:
        sharing_purpose = DataSharingPurpose(purpose)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid purpose. Valid purposes: {[p.value for p in DataSharingPurpose]}"
        ) from None

    # Parse data_categories
    try:
        categories = json.loads(data_categories) if isinstance(data_categories, str) else data_categories
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="data_categories must be valid JSON array") from None

    now = datetime.now(timezone.utc)

    sharing_log = DataSharingLog(
        user_id=patron_id,
        recipient_name=recipient_name,
        recipient_type=recipient_type,
        purpose=sharing_purpose,
        data_categories=categories,
        legal_basis=legal_basis,
        reference_id=reference_id,
        reference_type=reference_type,
        patron_notified=notify_patron,
        patron_notified_at=now if notify_patron else None,
        shared_by_staff_id=current_user.id,
        notes=notes,
    )
    db.add(sharing_log)

    await db.commit()
    await db.refresh(sharing_log)

    return {
        "message": "Data sharing event recorded",
        "id": sharing_log.id,
        "patron_id": patron_id,
        "recipient": recipient_name,
    }
