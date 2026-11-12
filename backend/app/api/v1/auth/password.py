# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response, status
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.email import send_password_reset_email, send_verification_email
from ....core.rate_limit import client_ip, limiter
from ....core.turnstile import verify_turnstile
from ....core.security import (
    PASSWORD_HISTORY_COUNT,
    PasswordValidationError,
    create_reset_token,
    create_verification_token,
    get_reset_token_expiry,
    get_verification_token_expiry,
    hash_password_async,
    hash_reset_token,
    validate_password,
    verify_password_async,
)
from ....models.user import PasswordHistory, RefreshToken, User, email_blind_hash
from ....schemas.user import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    MessageResponse,
    ResendVerificationRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from pydantic import BaseModel
from .helpers import add_deprecated_get_headers, get_current_user, log_security_event
from ....models.audit_log import AuditAction, AuditLog

logger = get_logger(__name__)

router = APIRouter()


async def _send_password_reset_email_safe(
    email: str, token: str, first_name: str | None, user_id: int
) -> None:
    # Background-task wrapper: errors after the response has shipped must be
    # logged but never raised. Preserves the prior try/except behavior that
    # disappeared once the send moved off the request path.
    try:
        await send_password_reset_email(email, token, first_name)
    except Exception as e:  # noqa: BLE001 -- log-and-swallow is intentional in bg task
        logger.warning(
            f"Failed to send password reset email for user_id={user_id}: {e}"
        )


@router.post("/forgot-password", response_model=MessageResponse)
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    forgot_request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email. Only works for verified email accounts."""
    ip_address = client_ip(request)

    if not await verify_turnstile(forgot_request.turnstile_token, client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry."
        )

    result = await db.execute(select(User).where(User.email_hash == email_blind_hash(forgot_request.email)))
    user = result.scalar_one_or_none()

    # Only allow password reset for verified email accounts
    # Always return generic success message to prevent email enumeration
    if user and user.email_verified:
        reset_token = create_reset_token()
        # Store hashed token in database for security (prevents token theft if DB is compromised)
        user.reset_token = hash_reset_token(reset_token)
        user.reset_token_expires = get_reset_token_expiry()
        await db.commit()

        log_security_event(
            "PASSWORD_RESET_REQUESTED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            severity="INFO",
        )

        # Defer the SMTP send so the response returns at the same time for both
        # the exists and not-exists branches. Synchronous `await` here leaked
        # account existence via response latency (timing oracle). See spec
        # 2026-05-19-l30-rate-limiting-tiered-policy.md §11.
        background_tasks.add_task(
            _send_password_reset_email_safe,
            user.email,
            reset_token,
            user.first_name,
            user.id,
        )
    else:
        # Log different types of failed reset attempts
        if user and not user.email_verified:
            log_security_event(
                "PASSWORD_RESET_UNVERIFIED_EMAIL",
                user_id=user.id,
                email=user.email,
                ip_address=ip_address,
                severity="INFO",
                details={"reason": "email_not_verified"},
            )
        else:
            log_security_event(
                "PASSWORD_RESET_NONEXISTENT_EMAIL",
                email=forgot_request.email,
                ip_address=ip_address,
                severity="INFO",
            )

    return MessageResponse(
        message="If a verified account exists with that email, a reset link has been sent."
    )


@router.post("/reset-password", response_model=MessageResponse)
@limiter.limit("5/hour")
async def reset_password(
    request: Request,
    reset_request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)
):
    """Reset password using token from email."""
    # Hash the incoming token to compare against stored hash
    hashed_token = hash_reset_token(reset_request.token)
    result = await db.execute(
        select(User).where(User.reset_token == hashed_token)
    )
    user = result.scalar_one_or_none()

    if not user:
        log_security_event(
            "PASSWORD_RESET_INVALID_TOKEN",
            severity="WARNING",
            details={"reason": "token_not_found"},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This password reset link is no longer valid. Please request a new one.")

    if (
        user.reset_token_expires
        and datetime.now(timezone.utc) > user.reset_token_expires
    ):
        log_security_event(
            "PASSWORD_RESET_EXPIRED_TOKEN",
            user_id=user.id,
            email=user.email,
            severity="WARNING",
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This password reset link has expired. Please request a new one.")

    # Validate new password
    try:
        validate_password(reset_request.new_password)
    except PasswordValidationError as e:
        log_security_event(
            "PASSWORD_RESET_INVALID_PASSWORD",
            user_id=user.id,
            email=user.email,
            severity="WARNING",
            details={"reason": str(e)},
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Check against current password
    if await verify_password_async(reset_request.new_password, user.password_hash):
        log_security_event(
            "PASSWORD_RESET_REUSE_ATTEMPT",
            user_id=user.id,
            email=user.email,
            severity="WARNING",
            details={"reason": "password_reused"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please choose a different password. For security, you can't reuse one of your last 5 passwords.",
        )

    # Check against password history
    history_result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(PASSWORD_HISTORY_COUNT)
    )
    password_history = history_result.scalars().all()

    for history_entry in password_history:
        if await verify_password_async(reset_request.new_password, history_entry.password_hash):
            log_security_event(
                "PASSWORD_RESET_REUSE_ATTEMPT",
                user_id=user.id,
                email=user.email,
                severity="WARNING",
                details={"reason": "password_in_history"},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please choose a different password. For security, you can't reuse one of your last 5 passwords.",
            )

    # Save current password to history before updating
    history_entry = PasswordHistory(
        user_id=user.id,
        password_hash=user.password_hash,
    )
    db.add(history_entry)

    # Clean up old password history entries (keep only last N)
    old_history_result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == user.id)
        .order_by(PasswordHistory.created_at.desc())
        .offset(PASSWORD_HISTORY_COUNT)
    )
    old_entries = old_history_result.scalars().all()
    for old_entry in old_entries:
        await db.delete(old_entry)

    # Update password and clear reset token
    user.password_hash = await hash_password_async(reset_request.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    user.failed_login_attempts = 0
    user.locked_until = None
    await db.commit()

    log_security_event(
        "PASSWORD_RESET_SUCCESS", user_id=user.id, email=user.email, severity="INFO"
    )

    return MessageResponse(message="Password has been reset successfully")


@router.post("/change-password", response_model=MessageResponse)
@limiter.limit("10/minute")
async def change_password(
    request: Request,
    change_request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change password for authenticated user."""
    if not await verify_password_async(change_request.current_password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="That password didn't match your current one. Please try again.")

    # Validate new password
    try:
        validate_password(change_request.new_password)
    except PasswordValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Check against current password
    if await verify_password_async(change_request.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please choose a different password. For security, you can't reuse one of your last 5 passwords.",
        )

    # Check against password history
    history_result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == current_user.id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(PASSWORD_HISTORY_COUNT)
    )
    password_history = history_result.scalars().all()

    for history_entry in password_history:
        if await verify_password_async(change_request.new_password, history_entry.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Please choose a different password. For security, you can't reuse one of your last 5 passwords.",
            )

    # Save current password to history before updating
    history_entry = PasswordHistory(
        user_id=current_user.id,
        password_hash=current_user.password_hash,
    )
    db.add(history_entry)

    # Clean up old password history entries (keep only last N)
    old_history_result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == current_user.id)
        .order_by(PasswordHistory.created_at.desc())
        .offset(PASSWORD_HISTORY_COUNT)
    )
    old_entries = old_history_result.scalars().all()
    for old_entry in old_entries:
        await db.delete(old_entry)

    current_user.password_hash = await hash_password_async(change_request.new_password)

    # Revoke all other refresh tokens for security
    other_tokens = await db.execute(
        select(RefreshToken).where(
            and_(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
            )
        )
    )
    current_token_hint = request.cookies.get("refresh_token", "")
    for token_row in other_tokens.scalars():
        if token_row.token != current_token_hint:
            token_row.revoked_at = datetime.now(timezone.utc)

    await db.commit()

    return MessageResponse(message="Password changed successfully")


@router.post("/verify-email", response_model=MessageResponse)
@limiter.limit("10/minute")
async def verify_email(
    request: Request, verify_request: VerifyEmailRequest, db: AsyncSession = Depends(get_db)
):
    """Verify email address using token."""
    # SECURITY: Hash incoming token to compare against stored hash
    hashed_token = hash_reset_token(verify_request.token)
    result = await db.execute(
        select(User).where(User.verification_token == hashed_token)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This verification link is no longer valid. Please request a new one.")

    if (
        user.verification_token_expires
        and datetime.now(timezone.utc) > user.verification_token_expires
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This verification link has expired. Please request a new one.")

    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    await db.commit()

    return MessageResponse(message="Email verified successfully")


async def _send_verification_email_safe(
    email: str, token: str, first_name: str | None, user_id: int
) -> None:
    try:
        await send_verification_email(email, token, first_name)
    except Exception as e:  # noqa: BLE001  # best-effort verification email
        logger.warning(
            f"Failed to resend verification email for user_id={user_id}: {e}"
        )


@router.post("/resend-verification", response_model=MessageResponse)
@limiter.limit("10/minute")
async def resend_verification(
    request: Request,
    resend_request: ResendVerificationRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Resend email verification link."""
    if not await verify_turnstile(resend_request.turnstile_token, client_ip(request)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry."
        )

    result = await db.execute(select(User).where(User.email_hash == email_blind_hash(resend_request.email)))
    user = result.scalar_one_or_none()

    if user and not user.email_verified:
        verification_token = create_verification_token()
        # SECURITY: Store hashed token, send plain token to user
        user.verification_token = hash_reset_token(verification_token)
        user.verification_token_expires = get_verification_token_expiry()
        await db.commit()
        # Defer SMTP so the response is constant-time across the
        # exists-unverified / exists-verified / no-user branches
        # (closes timing oracle). Same pattern as forgot_password (#922).
        background_tasks.add_task(
            _send_verification_email_safe,
            user.email,
            verification_token,
            user.first_name,
            user_id=user.id,
        )

    return MessageResponse(
        message="If an unverified account exists, a verification email has been sent."
    )


@router.get("/change-password")
async def get_change_password(
    response: Response,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Legacy GET compatibility endpoint for change-password."""
    add_deprecated_get_headers(response, replacement_method="POST")
    return {"status": "ok"}


@router.get("/forgot-password")
async def get_forgot_password(
    response: Response,
):
    """Legacy GET compatibility endpoint for forgot-password.

    Intentionally public to avoid breaking older clients that called this
    endpoint before authentication.
    """
    add_deprecated_get_headers(response, replacement_method="POST")
    return {"status": "ok"}


def _get_client_ip(request: Request) -> str | None:
    # Delegate to the shared helper (CF-Connecting-IP -> X-Real-IP -> peer).
    # The previous body trusted the leftmost X-Forwarded-For entry first, which
    # nginx appends to and is therefore client-spoofable.
    return client_ip(request)


async def _create_audit_log(
    db: AsyncSession,
    admin_id: int,
    action: AuditAction,
    target_user_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_log)
    return audit_log


class AcceptInviteRequest(BaseModel):
    token: str
    new_password: str


@router.post("/accept-invite", response_model=MessageResponse)
@limiter.limit("10/hour")
async def accept_invite(request: Request, body: AcceptInviteRequest, db: AsyncSession = Depends(get_db)):
    """Redeem an invite token: activate the pre-created user and set their password."""
    hashed = hash_reset_token(body.token)
    result = await db.execute(select(User).where(User.invite_token == hashed).with_for_update())
    user = result.scalar_one_or_none()
    if user is None or user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation link is no longer valid.")
    expires = user.invite_token_expires
    if expires is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation link is no longer valid.")
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation link is no longer valid.")
    try:
        validate_password(body.new_password)
    except PasswordValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    user.password_hash = await hash_password_async(body.new_password)
    user.is_active = True
    user.email_verified = True
    user.invite_token = None
    user.invite_token_expires = None
    await _create_audit_log(
        db=db, admin_id=user.id, action=AuditAction.UPDATE_USER,
        target_user_id=user.id, details={"email": user.email, "invite_accepted": True},
        ip_address=_get_client_ip(request), user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()
    return MessageResponse(message="Your account is ready. You can now sign in.")
