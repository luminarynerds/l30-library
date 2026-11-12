# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Account Security API endpoints.

Handles:
- 2FA setup, confirmation, and disable
- 2FA login verification (TOTP + recovery codes)
- Recovery codes regeneration
- Recovery email management
- Security alert preferences
- Security activity log
- Security overview/checklist
"""

import base64
import io
import json
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

import qrcode

import secrets as secrets_module

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, select, func as sql_func
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...core.turnstile import verify_turnstile
from ...core.rate_limit import limiter
from ...core.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_token_expiry,
    hash_refresh_token,
    verify_password_async,
)
from ...core.totp import (
    MAX_2FA_ATTEMPTS,
    compute_device_hash,
    decrypt_totp_secret_and_migrate,
    encrypt_totp_secret,
    generate_recovery_codes,
    generate_totp_secret,
    get_totp_uri,
    parse_user_agent,
    verify_recovery_code,
    verify_totp_code,
    verify_totp_code_once,
)
from ...models.audit_log import AuditAction, AuditLog
from ...models.known_device import KnownDevice
from ...models.user import RefreshToken, User
from ...schemas.account_security import (
    RecoveryCodesCountResponse,
    RecoveryCodesRegenerateRequest,
    RecoveryCodesResponse,
    RecoveryEmailRequest,
    RecoveryEmailResponse,
    RecoveryEmailVerifyRequest,
    SecurityActivityItem,
    SecurityActivityResponse,
    SecurityAlertPreferences,
    SecurityOverview,
    TwoFactorConfirmRequest,
    TwoFactorConfirmResponse,
    TwoFactorDisableRequest,
    TwoFactorRecoveryRequest,
    TwoFactorSetupResponse,
    TwoFactorVerifyRequest,
)
from .auth import get_current_user

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter(prefix="/account/security", tags=["account-security"])


def _mask_email(email: str) -> str:
    if not email or '@' not in email:
        return '***'
    local, domain = email.rsplit('@', 1)
    return f"{local[0]}***@{domain}" if local else f"***@{domain}"


async def _decrypt_totp_secret_or_degrade(
    db: AsyncSession,
    user: User,
    request: Request,
    *,
    reset_totp_on_failure: bool,
    call_site: str = "unknown",
) -> str:
    """Decrypt a user's TOTP secret for one of the 4 call sites that need it.

    Never lets a decrypt failure raise past this point as a raw 500 (a
    TOTP_ENCRYPTION_KEY/SECRET_KEY rotation must not crash login). Also
    transparently persists a lazy read-old-write-new migration when the
    secret was still encrypted under a previous/legacy key.

    `reset_totp_on_failure=True` is for call sites where the caller has
    already re-verified identity via password (disable/regenerate) or is
    mid-enrollment (confirm) -- on failure it's safe to clear 2FA state and
    tell the user to set it up again. `reset_totp_on_failure=False` is for
    the bare login step (/2fa/verify), which has no fresher identity check
    than the code itself -- on failure it must fail closed and point the
    user at the recovery-code path instead of bypassing 2FA.

    `call_site` identifies which of the 4 callers is asking, so a decrypt-
    failure audit-log wave can be traced back to (e.g.) a login spike vs. a
    disable/regenerate spike instead of every call site looking identical.
    """
    try:
        secret, migrated_ciphertext = decrypt_totp_secret_and_migrate(user.totp_secret)
    except ValueError:
        logger.error(
            "TOTP secret decrypt failed for user %d -- likely a TOTP_ENCRYPTION_KEY "
            "or SECRET_KEY rotation left no working key",
            user.id,
        )
        db.add(AuditLog(
            admin_id=user.id,
            target_user_id=user.id,
            action=AuditAction.TWO_FA_VERIFY_FAILED,
            details={
                "reason": "decrypt_failure",
                "totp_reset": reset_totp_on_failure,
                "call_site": call_site,
            },
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:255],
        ))
        if reset_totp_on_failure:
            user.totp_secret = None
            user.totp_enabled = False
            user.totp_confirmed_at = None
            user.recovery_codes = None
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "We couldn't verify your saved authentication method, so "
                    "two-factor authentication has been reset. Please set it "
                    "up again."
                ),
            ) from None
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "We couldn't verify your authenticator code. Please sign in "
                "using a recovery code, then set up two-factor authentication "
                "again."
            ),
        ) from None

    if migrated_ciphertext is not None:
        user.totp_secret = migrated_ciphertext
        await db.commit()

    return secret


# ─── 2FA Setup/Confirm/Disable ──────────────────────────────────────────────


@limiter.limit("5/minute")
@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Initiate 2FA setup — generates TOTP secret and QR URI."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled.",
        )

    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email)

    # Store encrypted secret (not yet confirmed)
    current_user.totp_secret = encrypt_totp_secret(secret)
    current_user.totp_enabled = False
    await db.commit()

    # Generate QR code image server-side
    qr = qrcode.make(uri)
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    qr_base64 = base64.b64encode(buffer.getvalue()).decode()
    qr_image = f"data:image/png;base64,{qr_base64}"

    return TwoFactorSetupResponse(secret=secret, qr_image=qr_image)


@limiter.limit("5/minute")
@router.post("/2fa/confirm", response_model=TwoFactorConfirmResponse)
async def confirm_2fa(
    confirm_request: TwoFactorConfirmRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm 2FA setup with first TOTP code — activates 2FA and returns recovery codes."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled.",
        )

    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please initiate 2FA setup first.",
        )

    secret = await _decrypt_totp_secret_or_degrade(
        db, current_user, request, reset_totp_on_failure=True, call_site="confirm_2fa"
    )
    if not await verify_totp_code_once(secret, confirm_request.code, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid code. Please try again with a fresh code from your authenticator app.",
        )

    plain_codes, hashed_codes = generate_recovery_codes()

    current_user.totp_enabled = True
    current_user.totp_confirmed_at = datetime.now(timezone.utc)
    current_user.recovery_codes = json.dumps(hashed_codes)

    db.add(AuditLog(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action=AuditAction.TWO_FA_ENABLED,
        details={"method": "totp"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()
    logger.info(f"2FA enabled for user {current_user.id}")

    return TwoFactorConfirmResponse(recovery_codes=plain_codes)


@limiter.limit("3/minute")
@router.post("/2fa/disable")
async def disable_2fa(
    disable_request: TwoFactorDisableRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disable 2FA — requires current password and TOTP code."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is not enabled.",
        )

    if not await verify_password_async(disable_request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect password.",
        )

    secret = await _decrypt_totp_secret_or_degrade(
        db, current_user, request, reset_totp_on_failure=True, call_site="disable_2fa"
    )
    if not await verify_totp_code_once(secret, disable_request.code, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication code.",
        )

    current_user.totp_secret = None
    current_user.totp_enabled = False
    current_user.totp_confirmed_at = None
    current_user.recovery_codes = None

    db.add(AuditLog(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action=AuditAction.TWO_FA_DISABLED,
        details={"method": "totp"},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()
    logger.info(f"2FA disabled for user {current_user.id}")

    return {"message": "Two-factor authentication has been disabled."}


@limiter.limit("10/minute")
@router.post("/2fa/dismiss-setup")
async def dismiss_2fa_setup(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Dismiss 2FA setup prompt — increments dismissal counter."""
    if current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication is already enabled.",
        )

    # Admin roles must set up 2FA -- no dismissals allowed
    from app.models.user import UserRole
    MANDATORY_2FA_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}
    if current_user.role in MANDATORY_2FA_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Two-factor authentication is mandatory for your role and cannot be dismissed.",
        )

    current_user.totp_setup_dismissals += 1
    await db.commit()

    return {
        "dismissals_used": current_user.totp_setup_dismissals,
        "dismissals_remaining": max(0, 3 - current_user.totp_setup_dismissals),
    }


# ─── 2FA Login Verification ─────────────────────────────────────────────────


@limiter.limit("5/minute")
@router.post("/2fa/verify")
async def verify_2fa_login(
    verify_request: TwoFactorVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify 2FA code during login — consumes pending token, issues real tokens."""
    from ...core.security import (
        consume_2fa_pending_token,
        increment_2fa_attempts,
        verify_2fa_pending_token,
    )

    if not await verify_turnstile(verify_request.turnstile_token, request.client.host if request.client else None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry."
        )

    user_id = verify_2fa_pending_token(verify_request.pending_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or too many attempts. Please sign in again.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        )

    secret = await _decrypt_totp_secret_or_degrade(
        db, user, request, reset_totp_on_failure=False, call_site="verify_2fa_login"
    )
    if not await verify_totp_code_once(secret, verify_request.code, user.id):
        attempts = increment_2fa_attempts(verify_request.pending_token)
        remaining = MAX_2FA_ATTEMPTS - attempts

        db.add(AuditLog(
            admin_id=user.id,
            target_user_id=user.id,
            action=AuditAction.TWO_FA_VERIFY_FAILED,
            details={"attempts_remaining": remaining},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent", "")[:255],
        ))
        await db.commit()

        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Too many failed attempts. Please sign in again.",
            )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid code. {remaining} attempt{'s' if remaining != 1 else ''} remaining.",
        )

    # Consume pending token and issue real tokens
    consume_2fa_pending_token(verify_request.pending_token)

    access_token = create_access_token(
        subject=user.id, email=user.email, role=str(user.role), staff_role=user.staff_role
    )
    refresh_token = create_refresh_token()

    db.add(RefreshToken(
        user_id=user.id,
        token=hash_refresh_token(refresh_token),
        device_info=request.headers.get("user-agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=get_refresh_token_expiry(),
    ))

    # Handle trusted device
    if verify_request.trust_device:
        ua = request.headers.get("user-agent", "")
        ip = request.client.host if request.client else ""
        device_hash = compute_device_hash(ua, ip)

        existing = await db.execute(
            select(KnownDevice).where(
                and_(
                    KnownDevice.user_id == user.id,
                    KnownDevice.device_hash == device_hash,
                )
            )
        )
        device = existing.scalar_one_or_none()
        if device:
            device.trusted_until = datetime.now(timezone.utc) + timedelta(days=30)
            device.last_seen_at = datetime.now(timezone.utc)
        else:
            db.add(KnownDevice(
                user_id=user.id,
                device_hash=device_hash,
                friendly_name=parse_user_agent(ua),
                ip_address=ip,
                trusted_until=datetime.now(timezone.utc) + timedelta(days=30),
            ))

        # Invalidate known-device cache (trust status changed)
        from .auth import _invalidate_known_device_cache
        await _invalidate_known_device_cache(user.id, device_hash)

    db.add(AuditLog(
        admin_id=user.id,
        target_user_id=user.id,
        action=AuditAction.TWO_FA_VERIFY_SUCCESS,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()

    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
    })
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )
    return response


@limiter.limit("3/minute")
@router.post("/2fa/recovery")
async def verify_2fa_recovery(
    recovery_request: TwoFactorRecoveryRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Use a recovery code during login — burns the code, issues real tokens."""
    from ...core.security import (
        consume_2fa_pending_token,
        verify_2fa_pending_token,
    )

    if not await verify_turnstile(recovery_request.turnstile_token, request.client.host if request.client else None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry."
        )

    user_id = verify_2fa_pending_token(recovery_request.pending_token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.recovery_codes:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session.",
        )

    hashed_codes = json.loads(user.recovery_codes)
    matched_index = verify_recovery_code(recovery_request.recovery_code, hashed_codes)

    if matched_index is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recovery code.",
        )

    # Burn the code
    hashed_codes[matched_index] = None
    user.recovery_codes = json.dumps(hashed_codes)

    consume_2fa_pending_token(recovery_request.pending_token)

    access_token = create_access_token(
        subject=user.id, email=user.email, role=str(user.role), staff_role=user.staff_role
    )
    refresh_token = create_refresh_token()

    db.add(RefreshToken(
        user_id=user.id,
        token=hash_refresh_token(refresh_token),
        device_info=request.headers.get("user-agent", "")[:255],
        ip_address=request.client.host if request.client else None,
        expires_at=get_refresh_token_expiry(),
    ))

    remaining = sum(1 for c in hashed_codes if c)
    db.add(AuditLog(
        admin_id=user.id,
        target_user_id=user.id,
        action=AuditAction.RECOVERY_CODE_USED,
        details={"codes_remaining": remaining},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()

    response = JSONResponse(content={
        "access_token": access_token,
        "token_type": "bearer",
        "recovery_codes_remaining": remaining,
    })
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        path="/api/v1/auth",
    )
    return response


# ─── Recovery Codes ──────────────────────────────────────────────────────────


@limiter.limit("20/minute")
@router.get("/recovery-codes/count", response_model=RecoveryCodesCountResponse)
async def get_recovery_codes_count(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get count of remaining recovery codes."""
    if not current_user.totp_enabled or not current_user.recovery_codes:
        return RecoveryCodesCountResponse(total=8, remaining=0)

    hashed_codes = json.loads(current_user.recovery_codes)
    remaining = sum(1 for c in hashed_codes if c)
    return RecoveryCodesCountResponse(total=8, remaining=remaining)


@limiter.limit("3/minute")
@router.post("/recovery-codes/regenerate", response_model=RecoveryCodesResponse)
async def regenerate_recovery_codes(
    regen_request: RecoveryCodesRegenerateRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Regenerate recovery codes — invalidates old codes."""
    if not current_user.totp_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Two-factor authentication must be enabled first.",
        )

    if not await verify_password_async(regen_request.password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Incorrect password.",
        )

    secret = await _decrypt_totp_secret_or_degrade(
        db, current_user, request, reset_totp_on_failure=True, call_site="regenerate_recovery_codes"
    )
    if not await verify_totp_code_once(secret, regen_request.code, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid authentication code.",
        )

    plain_codes, hashed_codes = generate_recovery_codes()
    current_user.recovery_codes = json.dumps(hashed_codes)

    db.add(AuditLog(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action=AuditAction.RECOVERY_CODES_REGENERATED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()

    return RecoveryCodesResponse(recovery_codes=plain_codes)


# ─── Recovery Email ──────────────────────────────────────────────────────────


@limiter.limit("3/minute")
@router.post("/recovery-email", response_model=RecoveryEmailResponse)
async def set_recovery_email(
    email_request: RecoveryEmailRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set a recovery email address (sends verification link)."""
    if email_request.email.lower() == current_user.email.lower():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Recovery email must be different from your primary email.",
        )

    import secrets
    token = secrets.token_urlsafe(32)

    current_user.recovery_email = email_request.email
    current_user.recovery_email_verified = False
    current_user.recovery_email_token = token
    current_user.recovery_email_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    db.add(AuditLog(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action=AuditAction.RECOVERY_EMAIL_ADDED,
        details={"recovery_email": _mask_email(email_request.email)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()

    # Send verification email
    try:
        from ...core.email import send_recovery_email_verification
        verification_url = f"{settings.frontend_url}/account/verify-recovery-email?token={token}"
        await send_recovery_email_verification(
            to_email=email_request.email,
            first_name=current_user.first_name,
            verification_url=verification_url,
        )
    except Exception as e:  # noqa: BLE001  # best-effort email — main op already committed
        logger.warning(f"Failed to send recovery email verification: {e}")

    return RecoveryEmailResponse(
        recovery_email=email_request.email,
        verified=False,
        message="Verification email sent. Please check your inbox.",
    )


@limiter.limit("5/minute")
@router.post("/recovery-email/verify", response_model=RecoveryEmailResponse)
async def verify_recovery_email(
    verify_email_request: RecoveryEmailVerifyRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify recovery email with token from email link."""
    if not current_user.recovery_email_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recovery email verification pending.",
        )

    if not secrets_module.compare_digest(current_user.recovery_email_token or "", verify_email_request.token):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification token.",
        )

    if (
        current_user.recovery_email_token_expires
        and datetime.now(timezone.utc) > current_user.recovery_email_token_expires
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired. Please request a new one.",
        )

    current_user.recovery_email_verified = True
    current_user.recovery_email_token = None
    current_user.recovery_email_token_expires = None

    db.add(AuditLog(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action=AuditAction.RECOVERY_EMAIL_VERIFIED,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()

    return RecoveryEmailResponse(
        recovery_email=current_user.recovery_email,
        verified=True,
        message="Recovery email verified successfully.",
    )


@limiter.limit("3/minute")
@router.delete("/recovery-email")
async def remove_recovery_email(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Remove recovery email."""
    if not current_user.recovery_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No recovery email is set.",
        )

    old_email = current_user.recovery_email
    current_user.recovery_email = None
    current_user.recovery_email_verified = False
    current_user.recovery_email_token = None
    current_user.recovery_email_token_expires = None

    db.add(AuditLog(
        admin_id=current_user.id,
        target_user_id=current_user.id,
        action=AuditAction.RECOVERY_EMAIL_REMOVED,
        details={"removed_email": _mask_email(old_email)},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:255],
    ))

    await db.commit()

    return {"message": "Recovery email removed."}


# ─── Security Alert Preferences ──────────────────────────────────────────────


@limiter.limit("20/minute")
@router.get("/alert-preferences", response_model=SecurityAlertPreferences)
async def get_alert_preferences(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """Get security alert preferences."""
    return SecurityAlertPreferences(
        security_alert_new_login=current_user.security_alert_new_login,
        security_alert_changes=current_user.security_alert_changes,
    )


@limiter.limit("10/minute")
@router.put("/alert-preferences", response_model=SecurityAlertPreferences)
async def update_alert_preferences(
    prefs: SecurityAlertPreferences,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update security alert preferences."""
    current_user.security_alert_new_login = prefs.security_alert_new_login
    current_user.security_alert_changes = prefs.security_alert_changes
    await db.commit()
    return prefs


# ─── Security Activity ───────────────────────────────────────────────────────


SECURITY_ACTIONS = {
    AuditAction.LOGIN_SUCCESS: ("Signed in", "success"),
    AuditAction.LOGIN_FAILED: ("Failed sign-in attempt", "failed"),
    AuditAction.LOGIN_LOCKED: ("Account locked", "blocked"),
    AuditAction.LOGOUT: ("Signed out", "success"),
    AuditAction.PASSWORD_CHANGED: ("Password changed", "change"),
    AuditAction.RESET_PASSWORD: ("Password reset", "change"),
    AuditAction.TWO_FA_ENABLED: ("Two-factor authentication enabled", "change"),
    AuditAction.TWO_FA_DISABLED: ("Two-factor authentication disabled", "change"),
    AuditAction.TWO_FA_VERIFY_SUCCESS: ("Two-factor code verified", "success"),
    AuditAction.TWO_FA_VERIFY_FAILED: ("Two-factor code failed", "failed"),
    AuditAction.RECOVERY_CODE_USED: ("Recovery code used", "change"),
    AuditAction.RECOVERY_CODES_REGENERATED: ("Recovery codes regenerated", "change"),
    AuditAction.RECOVERY_EMAIL_ADDED: ("Recovery email added", "change"),
    AuditAction.RECOVERY_EMAIL_VERIFIED: ("Recovery email verified", "change"),
    AuditAction.RECOVERY_EMAIL_REMOVED: ("Recovery email removed", "change"),
    AuditAction.SESSION_REVOKED: ("Session revoked", "change"),
    AuditAction.ALL_SESSIONS_REVOKED: ("All other sessions revoked", "change"),
    AuditAction.NEW_DEVICE_DETECTED: ("New device detected", "change"),
}


@limiter.limit("20/minute")
@router.get("/activity", response_model=SecurityActivityResponse)
async def get_security_activity(
    request: Request,
    page: int = 1,
    per_page: int = Query(default=20, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get security activity log for current user."""
    security_action_values = [a.value for a in SECURITY_ACTIONS.keys()]

    count_query = select(sql_func.count(AuditLog.id)).where(
        and_(
            AuditLog.target_user_id == current_user.id,
            AuditLog.action.in_(security_action_values),
        )
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    offset = (page - 1) * per_page
    query = (
        select(AuditLog)
        .where(
            and_(
                AuditLog.target_user_id == current_user.id,
                AuditLog.action.in_(security_action_values),
            )
        )
        .order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(per_page)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    items = []
    for log in logs:
        action_enum = AuditAction(log.action) if isinstance(log.action, str) else log.action
        label, status_str = SECURITY_ACTIONS.get(action_enum, (str(log.action), "change"))
        device = parse_user_agent(log.user_agent) if log.user_agent else None

        items.append(SecurityActivityItem(
            action=log.action if isinstance(log.action, str) else log.action.value,
            action_label=label,
            timestamp=log.created_at,
            ip_address=log.ip_address,
            device=device,
            status=status_str,
        ))

    return SecurityActivityResponse(
        items=items, total=total, page=page, per_page=per_page,
    )


# ─── Security Overview ───────────────────────────────────────────────────────


@limiter.limit("20/minute")
@router.get("/overview", response_model=SecurityOverview)
async def get_security_overview(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get security status overview for the account."""
    recovery_remaining = 0
    if current_user.recovery_codes:
        hashed_codes = json.loads(current_user.recovery_codes)
        recovery_remaining = sum(1 for c in hashed_codes if c)

    sessions_result = await db.execute(
        select(sql_func.count(RefreshToken.id)).where(
            and_(
                RefreshToken.user_id == current_user.id,
                RefreshToken.revoked_at.is_(None),
                RefreshToken.expires_at > datetime.now(timezone.utc),
            )
        )
    )
    active_sessions = sessions_result.scalar() or 0

    devices_result = await db.execute(
        select(sql_func.count(KnownDevice.id)).where(
            KnownDevice.user_id == current_user.id
        )
    )
    known_devices = devices_result.scalar() or 0

    return SecurityOverview(
        totp_enabled=current_user.totp_enabled,
        totp_confirmed_at=current_user.totp_confirmed_at,
        recovery_email_set=current_user.recovery_email is not None,
        recovery_email_verified=current_user.recovery_email_verified,
        recovery_codes_remaining=recovery_remaining,
        security_alert_new_login=current_user.security_alert_new_login,
        security_alert_changes=current_user.security_alert_changes,
        active_sessions_count=active_sessions,
        known_devices_count=known_devices,
        has_stripe_connected=False,  # Placeholder until Stripe Connect is integrated
    )
