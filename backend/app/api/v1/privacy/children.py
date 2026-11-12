# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""COPPA - Child Account and Parental Consent Endpoints."""

import hashlib
from app.core.logging import get_logger
import secrets
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.security import hash_reset_token
from ....models.audit_log import AuditAction
from ....models.privacy_ledger import (
    ConsentMethod,
    ConsentRecord,
    ConsentStatus,
    ConsentType,
)
from ....models.user import COPPA_AGE_THRESHOLD, User, UserRole, email_blind_hash
from ..auth import get_current_user

from .schemas import (
    ChildAccountInfo,
    ChildRegistrationRequest,
    ConsentTokenInfoResponse,
    ParentalConsentRequest,
    ParentalConsentResponse,
)
from .helpers import check_email_blocked, create_audit_log, send_parental_consent_email

logger = get_logger(__name__)

router = APIRouter()

# ---- Pydantic models for consent endpoints ----

STAFF_ROLES = {UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}


class ConsentRequestBody(BaseModel):
    parent_email: EmailStr


class ConsentVerifyBody(BaseModel):
    token: str


# =============================================================================
# Child registration
# =============================================================================


@router.post("/child/register", status_code=status.HTTP_201_CREATED)
async def register_child_account(
    request: ChildRegistrationRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a child account (under 13). Requires parental consent.

    The child account will be created in a pending state.
    A consent request email will be sent to the parent's email.
    The child cannot log in until the parent grants consent.
    """
    from ....core.security import hash_password, validate_password, PasswordValidationError

    # Verify child is actually under COPPA threshold
    today = date.today()
    age = today.year - request.date_of_birth.year - (
        (today.month, today.day) < (request.date_of_birth.month, request.date_of_birth.day)
    )

    if age >= COPPA_AGE_THRESHOLD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Use regular registration for users {COPPA_AGE_THRESHOLD} or older"
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email_hash == email_blind_hash(request.email)))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Check if email is blocked
    is_blocked, block_expires = await check_email_blocked(db, request.email)
    if is_blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This email cannot be used for registration at this time"
        )

    # Validate password
    try:
        validate_password(request.password)
    except PasswordValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Generate consent token -- store hash, send plain token
    consent_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(consent_token)

    # Create child account (inactive until consent)
    from ..auth import generate_library_card

    child = User(
        email=request.email,
        password_hash=hash_password(request.password),
        first_name=request.first_name,
        last_name=request.last_name,
        role=UserRole.CHILD,
        library_card=generate_library_card(),
        date_of_birth=request.date_of_birth,
        parental_consent_email=request.parent_email,
        parental_consent_token=token_hash,
        parental_consent_token_expires=datetime.now(timezone.utc) + timedelta(days=7),
        parental_consent_given=False,
        email_verified=False,
    )
    db.add(child)
    await db.commit()
    await db.refresh(child)

    # Send consent request to parent
    try:
        await send_parental_consent_email(
            parent_email=request.parent_email,
            child_name=f"{request.first_name} {request.last_name}",
            consent_token=consent_token,
        )
    except Exception as e:  # noqa: BLE001  # best-effort parental consent email — child row already saved
        logger.warning(f"Failed to send parental consent email: {e}")

    return {
        "message": "Child account created. Parental consent required.",
        "consent_email_sent_to": request.parent_email,
        "consent_expires_in_days": 7,
    }


# =============================================================================
# Consent grant (from registration flow)
# =============================================================================


@router.post("/child/consent", response_model=ParentalConsentResponse)
async def grant_parental_consent(
    payload: ParentalConsentRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Grant or deny parental consent for a child account.

    Called when a parent clicks the consent link in their email. The endpoint
    is public (no auth) — possession of the token is the proof of authority.
    On grant, writes a ConsentRecord ledger entry and an audit log entry; on
    deny, the pending child account is removed and the denial is logged
    (anonymized) before deletion.
    """
    if not payload.token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing consent token")

    token_hash = hash_reset_token(payload.token)
    result = await db.execute(
        select(User).where(User.parental_consent_token == token_hash)
    )
    child = result.scalar_one_or_none()
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid consent token")

    if child.parental_consent_token_expires and \
       datetime.now(timezone.utc) > child.parental_consent_token_expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent token has expired")

    ip = request.client.host if request.client else None
    user_agent = request.headers.get("User-Agent", "")[:500]
    now = datetime.now(timezone.utc)

    if payload.consent_given:
        child.parental_consent_given = True
        child.parental_consent_date = now
        child.parental_consent_method = "email_verification"
        child.parental_consent_token = None
        child.parental_consent_token_expires = None

        db.add(ConsentRecord(
            user_id=child.id,
            consent_type=ConsentType.PARENTAL_CONSENT,
            status=ConsentStatus.GRANTED,
            method=ConsentMethod.EMAIL_CONFIRMATION,
            ip_address=ip,
            user_agent=user_agent,
            details={
                "child_email": child.email,
                "parent_email": child.parental_consent_email,
                "verified_via": "email_token",
            },
        ))

        await create_audit_log(
            db=db,
            action=AuditAction.PRIVACY_SETTING_CHANGED,
            target_user_id=child.id,
            details={
                "event": "parental_consent_granted",
                "consent_type": ConsentType.PARENTAL_CONSENT.value,
                "method": ConsentMethod.EMAIL_CONFIRMATION.value,
            },
            ip_address=ip,
            user_agent=user_agent,
        )

        message = "Consent granted. The library account is now active."
    else:
        # Log the denial against a NULL user_id (FK is SET NULL on delete) so we
        # retain a privacy-ledger entry even after the pending account is purged.
        db.add(ConsentRecord(
            user_id=None,
            consent_type=ConsentType.PARENTAL_CONSENT,
            status=ConsentStatus.WITHDRAWN,
            method=ConsentMethod.EMAIL_CONFIRMATION,
            ip_address=ip,
            user_agent=user_agent,
            details={
                "event": "parental_consent_denied",
                "child_email": child.email,
                "parent_email": child.parental_consent_email,
            },
        ))
        await create_audit_log(
            db=db,
            action=AuditAction.PRIVACY_SETTING_CHANGED,
            target_user_id=None,
            details={
                "event": "parental_consent_denied",
                "consent_type": ConsentType.PARENTAL_CONSENT.value,
                "method": ConsentMethod.EMAIL_CONFIRMATION.value,
            },
            ip_address=ip,
            user_agent=user_agent,
        )
        await db.delete(child)
        message = "Consent denied. The child account has been removed."

    await db.commit()

    return ParentalConsentResponse(message=message, consent_given=payload.consent_given)


# =============================================================================
# Resend consent email
# =============================================================================


@router.post("/child/resend-consent")
async def resend_parental_consent(
    child_email: EmailStr,
    db: AsyncSession = Depends(get_db),
):
    """Resend parental consent email for a pending child account."""
    result = await db.execute(
        select(User).where(
            User.email_hash == email_blind_hash(child_email),
            User.parental_consent_given == False,
        )
    )
    child = result.scalar_one_or_none()

    if not child:
        # Don't reveal if email exists
        return {"message": "If a pending child account exists, a consent email has been sent."}

    if not child.parental_consent_email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No parent email on record")

    # Generate new consent token -- store hash, send plain token
    consent_token = secrets.token_urlsafe(32)
    child.parental_consent_token = hash_reset_token(consent_token)
    child.parental_consent_token_expires = datetime.now(timezone.utc) + timedelta(days=7)
    await db.commit()

    try:
        await send_parental_consent_email(
            parent_email=child.parental_consent_email,
            child_name=child.full_name,
            consent_token=consent_token,
        )
    except Exception as e:
        logger.error(
            "Failed to send parental consent email to %s for child %s: %s",
            child.parental_consent_email,
            child.full_name,
            e,
            exc_info=True
        )

    return {"message": "If a pending child account exists, a consent email has been sent."}


# =============================================================================
# List children
# =============================================================================


@router.get("/children")
async def get_my_children(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get list of child accounts linked to the current user (parent)."""
    result = await db.execute(
        select(User).where(User.parent_guardian_id == current_user.id)
    )
    children = result.scalars().all()

    return [
        ChildAccountInfo(
            id=c.id,
            first_name=c.first_name,
            last_name=c.last_name,
            email=c.email,
            parental_consent_given=c.parental_consent_given,
            created_at=c.created_at,
        )
        for c in children
    ]


# =============================================================================
# Staff-initiated consent request for existing child accounts
# =============================================================================


@router.post("/children/{child_id}/request-consent")
async def request_consent(
    child_id: int,
    body: ConsentRequestBody,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Staff sends a parental consent request for an existing child account.

    Generates a cryptographically secure token, stores its SHA-256 hash on the
    child record, and emails the parent a verification link.
    """
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required"
        )

    # Look up the child
    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child account not found")

    if not child.is_minor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account does not belong to a minor"
        )

    if child.parental_consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parental consent has already been granted for this account"
        )

    # Generate token -- store hash, send plain
    consent_token = secrets.token_urlsafe(32)
    token_hash = hash_reset_token(consent_token)

    child.parental_consent_token = token_hash
    child.parental_consent_token_expires = datetime.now(timezone.utc) + timedelta(hours=72)
    child.parental_consent_email = body.parent_email

    # Audit
    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        admin_id=current_user.id,
        target_user_id=child.id,
        details={
            "action": "consent_request_sent",
            "parent_email_domain": body.parent_email.split("@")[1],
            "expires_hours": 72,
        },
        ip_address=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    # Send email (after commit so the token is persisted even if email fails)
    try:
        await send_parental_consent_email(
            parent_email=body.parent_email,
            child_name=child.full_name,
            consent_token=consent_token,
        )
    except Exception as e:
        logger.error(
            "Failed to send parental consent email to %s for child %s (id=%d): %s",
            body.parent_email, child.full_name, child.id, e, exc_info=True,
        )
        # Don't raise -- token is stored, staff can retry or troubleshoot email
        return {
            "message": "Consent token created but email delivery failed. Check email configuration.",
            "child_id": child.id,
            "consent_email": body.parent_email,
            "expires_in_hours": 72,
            "email_sent": False,
        }

    return {
        "message": "Parental consent request sent",
        "child_id": child.id,
        "consent_email": body.parent_email,
        "expires_in_hours": 72,
        "email_sent": True,
    }


# =============================================================================
# Unauthenticated consent verification (parent clicks email link)
# =============================================================================


@router.post("/children/verify-consent")
async def verify_consent(
    body: ConsentVerifyBody,
    http_request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Verify parental consent using a token from the emailed link.

    This endpoint is unauthenticated -- the parent clicks a link containing
    the token, which proves they control the email address.
    """
    token_hash = hash_reset_token(body.token)

    result = await db.execute(
        select(User).where(User.parental_consent_token == token_hash)
    )
    child = result.scalar_one_or_none()

    if not child:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired consent token"
        )

    if child.parental_consent_token_expires and \
       datetime.now(timezone.utc) > child.parental_consent_token_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Consent token has expired. Please contact the library to request a new one."
        )

    # Grant consent
    child.parental_consent_given = True
    child.parental_consent_date = datetime.now(timezone.utc)
    child.parental_consent_method = "email_verification"
    child.parental_consent_token = None
    child.parental_consent_token_expires = None

    # Audit
    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        target_user_id=child.id,
        details={
            "action": "parental_consent_verified",
            "method": "email_verification",
            "parent_email_domain": child.parental_consent_email.split("@")[1] if child.parental_consent_email else "unknown",
        },
        ip_address=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    return {
        "message": f"Parental consent verified for {child.full_name}. The library account is now active.",
        "child_name": child.full_name,
        "consent_given": True,
    }


# =============================================================================
# Consent revocation (staff or parent/guardian)
# =============================================================================


@router.post("/children/{child_id}/revoke-consent")
async def revoke_consent(
    child_id: int,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke parental consent for a child account.

    Accessible by staff or the linked parent/guardian. Once revoked, the child
    cannot log in until consent is re-granted (enforced by the login check).
    """
    # Authorization: staff or the child's linked parent/guardian
    is_staff = current_user.role in STAFF_ROLES

    result = await db.execute(select(User).where(User.id == child_id))
    child = result.scalar_one_or_none()
    if not child:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Child account not found")

    is_parent = child.parent_guardian_id is not None and child.parent_guardian_id == current_user.id

    if not is_staff and not is_parent:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only staff or the linked parent/guardian can revoke consent"
        )

    if not child.parental_consent_given:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parental consent is not currently active for this account"
        )

    # Revoke
    child.parental_consent_given = False
    child.parental_consent_date = None
    child.parental_consent_method = None
    # Clear any pending token as well
    child.parental_consent_token = None
    child.parental_consent_token_expires = None

    # Audit
    revoker_type = "staff" if is_staff else "parent_guardian"
    await create_audit_log(
        db=db,
        action=AuditAction.PRIVACY_SETTING_CHANGED,
        admin_id=current_user.id if is_staff else None,
        target_user_id=child.id,
        details={
            "action": "parental_consent_revoked",
            "revoked_by": revoker_type,
            "revoked_by_user_id": current_user.id,
        },
        ip_address=http_request.client.host if http_request.client else None,
        user_agent=http_request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    return {
        "message": f"Parental consent revoked for {child.full_name}. The account is now inactive.",
        "child_id": child.id,
        "consent_given": False,
    }


# =============================================================================
# GET stubs (keep existing contract)
# =============================================================================


@router.get("/child/consent", response_model=ConsentTokenInfoResponse)
async def get_child_consent(
    token: str = Query(..., min_length=1, description="Consent token from the parent's email"),
    db: AsyncSession = Depends(get_db),
):
    """
    Look up a parental consent request by token.

    Public (no auth) — the parent uses this from the email link to preview the
    pending request before granting or denying. Returns minimal information
    about the child to avoid exposing PII to anyone holding only an email link.
    """
    token_hash = hash_reset_token(token)
    result = await db.execute(
        select(User).where(User.parental_consent_token == token_hash)
    )
    child = result.scalar_one_or_none()
    if child is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid consent token")

    if child.parental_consent_token_expires and \
       datetime.now(timezone.utc) > child.parental_consent_token_expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Consent token has expired")

    last_initial = (child.last_name[:1] if child.last_name else "").upper()
    return ConsentTokenInfoResponse(
        child_first_name=child.first_name or "",
        child_last_initial=last_initial,
        parent_email=child.parental_consent_email or "",
        expires_at=child.parental_consent_token_expires.isoformat()
            if child.parental_consent_token_expires else "",
        already_decided=bool(child.parental_consent_given),
    )


@router.get("/child/register")
async def get_child_register(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get /child/register information."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")


@router.get("/child/resend-consent")
async def get_child_resend_consent(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get /child/resend-consent information."""
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented")
