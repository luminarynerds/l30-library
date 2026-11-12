# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import get_settings
from ....core.database import get_db
from ....core.email import send_magic_link_email
from ....core.rate_limit import client_ip, limiter
from ....core.turnstile import verify_turnstile
from ....core.security import (
    create_access_token,
    create_magic_link_token,
    create_refresh_token,
    get_magic_link_token_expiry,
    get_refresh_token_expiry,
    hash_magic_link_token,
    hash_refresh_token,
    revoke_token,
    verify_magic_link_token,
    verify_password_async,
)
from ....models.user import RefreshToken, User, UserRole, email_blind_hash
from ....schemas.user import (
    LoginRequest,
    MagicLinkRequest,
    MagicLinkVerifyRequest,
    MessageResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    TokenWithCookie,
)
from .helpers import (
    REFRESH_TOKEN_COOKIE_NAME,
    _get_known_device_cached,
    _invalidate_known_device_cache,
    _set_known_device_cached,
    add_deprecated_get_headers,
    clear_refresh_token_cookie,
    get_current_user,
    log_security_event,
    set_refresh_token_cookie,
)

logger = get_logger(__name__)
settings = get_settings()

router = APIRouter()


@router.post("/login", response_model=None)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login and get JWT tokens.

    The access token is returned in the response body.
    The refresh token is set as an httpOnly cookie for XSS protection.

    Accepts either 'email' or 'username' field for login credentials.
    If both are provided, 'email' takes precedence.
    """
    ip_address = client_ip(request)

    # Cloudflare Turnstile bot verification — fails open in dev when
    # CF_TURNSTILE_SECRET is unset; rejects bogus tokens when secret is set.
    if not await verify_turnstile(login_data.turnstile_token, ip_address):
        log_security_event(
            "LOGIN_FAILED",
            ip_address=ip_address,
            severity="WARNING",
            details={"reason": "turnstile_failed"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry.",
        )

    # Get the login identifier (email takes precedence over username)
    try:
        login_identifier = login_data.get_login_identifier()
    except ValueError:
        log_security_event(
            "LOGIN_FAILED",
            ip_address=ip_address,
            severity="WARNING",
            details={"reason": "missing_credentials"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please enter your email address or library card number to sign in.",
        ) from None

    # Query user by email hash (email is encrypted; look up via blind index).
    result = await db.execute(
        select(User).where(User.email_hash == email_blind_hash(login_identifier))
    )
    user = result.scalar_one_or_none()

    # Check if account is locked
    if user and user.is_locked():
        log_security_event(
            "LOGIN_ACCOUNT_LOCKED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            severity="WARNING",
        )
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=(
                f"Your account is locked for {settings.lockout_duration_minutes} minutes "
                "due to multiple failed login attempts. "
                f"You can try again after {settings.lockout_duration_minutes} minutes, "
                "or call (613) 555-1234 for immediate help."
            ),
        )

    # SECURITY: Always run password verification to prevent timing-based user enumeration.
    # If the user doesn't exist, verify against a dummy hash so the response time is
    # consistent regardless of whether the email is valid.
    _dummy_hash = "$2b$12$LJ3m4ys3Lg2VBe6p0C5Yn.OhIMFnXHPBpckgVMH/SkYFRsFfTeNHi"
    # Guard against null password_hash (users created without a password). Run the
    # bcrypt compare regardless, so response timing does not distinguish this case
    # from any other failed login (avoids a user-enumeration oracle).
    no_password_account = bool(user and not user.password_hash)

    password_valid = await verify_password_async(
        login_data.password,
        user.password_hash if (user and user.password_hash) else _dummy_hash,
    )

    if no_password_account:
        log_security_event(
            "LOGIN_FAILED",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            severity="WARNING",
            details={"reason": "no_password_set"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password combination didn't work. Please check and try again.",
        )

    if not user or not password_valid:
        # Increment failed login attempts
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.max_login_attempts:
                user.locked_until = datetime.now(timezone.utc) + timedelta(
                    minutes=settings.lockout_duration_minutes
                )
                log_security_event(
                    "LOGIN_ACCOUNT_LOCKED_DUE_TO_ATTEMPTS",
                    user_id=user.id,
                    email=user.email,
                    ip_address=ip_address,
                    severity="WARNING",
                    details={"failed_attempts": user.failed_login_attempts},
                )
            await db.commit()

        # Log failed login attempt
        log_security_event(
            "LOGIN_FAILED",
            email=login_identifier,
            ip_address=ip_address,
            severity="WARNING",
            details={"reason": "invalid_credentials"},
        )

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password combination didn't work. Please check and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        log_security_event(
            "LOGIN_INACTIVE_USER",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            severity="WARNING",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="That email and password combination didn't work. Please check and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Email verification check: Ensure email is verified before login
    if not user.email_verified:
        log_security_event(
            "LOGIN_UNVERIFIED_EMAIL",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            severity="INFO",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your email address has not been verified yet. "
                   "Please check your email for a verification link, or request a new one.",
        )

    # COPPA compliance: Check if minor requires parental consent
    if user.requires_parental_consent:
        log_security_event(
            "LOGIN_BLOCKED_PENDING_CONSENT",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            severity="INFO",
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account requires parental consent before it can be used. "
                   "A consent request has been sent to the parent/guardian email on file.",
        )

    # Reset failed login attempts on successful login
    user.failed_login_attempts = 0
    user.locked_until = None

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)

    # --- 2FA Check ---
    if user.totp_enabled:
        # Check if device is trusted (skip 2FA)
        from ....core.totp import compute_device_hash
        from ....core.security import create_2fa_pending_token
        from ....schemas.account_security import TwoFactorLoginResponse
        from ....models.known_device import KnownDevice

        ua = request.headers.get("User-Agent", "")
        ip = client_ip(request)
        device_hash = compute_device_hash(ua, ip)

        # Check Redis cache first for trusted device status
        cached = await _get_known_device_cached(user.id, device_hash)
        trusted = None
        if cached and cached.get("trusted_until"):
            from dateutil.parser import isoparse
            try:
                trusted_until = isoparse(cached["trusted_until"])
                if trusted_until > datetime.now(timezone.utc):
                    # Cache hit: device is trusted -- still need DB object to update last_seen
                    trusted_device = await db.execute(
                        select(KnownDevice).where(
                            KnownDevice.user_id == user.id,
                            KnownDevice.device_hash == device_hash,
                        )
                    )
                    trusted = trusted_device.scalar_one_or_none()
            except (ValueError, TypeError):
                pass  # malformed cache entry -- fall through to DB

        if trusted is None:
            # Cache miss or stale -- query DB with trusted_until filter
            trusted_device = await db.execute(
                select(KnownDevice).where(
                    KnownDevice.user_id == user.id,
                    KnownDevice.device_hash == device_hash,
                    KnownDevice.trusted_until > datetime.now(timezone.utc),
                )
            )
            trusted = trusted_device.scalar_one_or_none()
            # Populate cache regardless of result
            if trusted:
                await _set_known_device_cached(user.id, device_hash, {
                    "id": trusted.id,
                    "trusted_until": trusted.trusted_until.isoformat() if trusted.trusted_until else None,
                })

        if not trusted:
            # Not trusted -- require 2FA
            await db.commit()  # save the reset of failed_login_attempts
            pending_token = create_2fa_pending_token(user.id)
            return TwoFactorLoginResponse(pending_token=pending_token)
        else:
            trusted.last_seen_at = datetime.now(timezone.utc)

    # --- Known Device Detection + Audit ---
    from ....core.totp import compute_device_hash, parse_user_agent
    from ....models.known_device import KnownDevice
    from ....models.audit_log import AuditLog, AuditAction

    ua = request.headers.get("User-Agent", "")
    ip = client_ip(request)
    device_hash = compute_device_hash(ua, ip)

    # Check Redis cache first to avoid DB query on repeat logins
    cached_device = await _get_known_device_cached(user.id, device_hash)
    is_known = False

    if cached_device:
        # Cache hit -- device is known; update last_seen via lightweight UPDATE
        from sqlalchemy import update
        await db.execute(
            update(KnownDevice)
            .where(
                KnownDevice.user_id == user.id,
                KnownDevice.device_hash == device_hash,
            )
            .values(last_seen_at=datetime.now(timezone.utc))
        )
        is_known = True
    else:
        # Cache miss -- query DB
        existing_device = await db.execute(
            select(KnownDevice).where(
                KnownDevice.user_id == user.id,
                KnownDevice.device_hash == device_hash,
            )
        )
        known = existing_device.scalar_one_or_none()
        if known:
            known.last_seen_at = datetime.now(timezone.utc)
            is_known = True
            # Populate cache on DB hit
            await _set_known_device_cached(user.id, device_hash, {
                "id": known.id,
                "trusted_until": known.trusted_until.isoformat() if known.trusted_until else None,
            })

    if not is_known:
        # New device -- add to DB and invalidate cache
        friendly = parse_user_agent(ua)
        db.add(KnownDevice(
            user_id=user.id,
            device_hash=device_hash,
            friendly_name=friendly,
            ip_address=ip,
        ))
        await _invalidate_known_device_cache(user.id, device_hash)
        db.add(AuditLog(
            admin_id=user.id,
            target_user_id=user.id,
            action=AuditAction.NEW_DEVICE_DETECTED,
            details={"device": friendly, "ip": ip},
            ip_address=ip,
            user_agent=ua[:255],
        ))

        # Send security alert email if enabled
        if user.security_alert_new_login and str(getattr(user.notice_preference, "value", user.notice_preference)) != "NONE":
            try:
                from ....core.email import send_security_alert_new_login
                await send_security_alert_new_login(
                    to_email=user.email,
                    first_name=user.first_name,
                    device=friendly,
                    ip_address=ip,
                    timestamp=datetime.now(timezone.utc).strftime("%B %d, %Y at %I:%M %p UTC"),
                )
            except Exception as e:  # noqa: BLE001  # best-effort security alert email — login must not fail
                logger.warning(f"Failed to send new login alert: {e}")

    # Audit log successful login
    db.add(AuditLog(
        admin_id=user.id,
        target_user_id=user.id,
        action=AuditAction.LOGIN_SUCCESS,
        ip_address=ip,
        user_agent=ua[:255],
    ))

    # Create tokens
    access_token = create_access_token(
        subject=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
    )
    refresh_token_str = create_refresh_token()

    # Store refresh token in database
    refresh_token = RefreshToken(
        user_id=user.id,
        token=hash_refresh_token(refresh_token_str),
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=client_ip(request),
        expires_at=get_refresh_token_expiry(),
    )
    db.add(refresh_token)
    await db.commit()

    # Log successful login
    log_security_event(
        "LOGIN_SUCCESS",
        user_id=user.id,
        email=user.email,
        ip_address=ip_address,
        severity="INFO",
        details={"user_agent": request.headers.get("User-Agent", "")[:100]},
    )

    # Set refresh token as httpOnly cookie (XSS protection)
    set_refresh_token_cookie(response, refresh_token_str)

    # --- 2FA Enforcement for admin roles ---
    # Forced only when require_admin_2fa is on (default). Self-host/fork builds
    # turn it off so admins can log in without setting up an authenticator first;
    # 2FA is still available to opt into via account settings.
    # Roles that must run with 2FA. Keep in sync with
    # account_security.MANDATORY_2FA_ROLES: LEGAL has standing access to
    # law-enforcement request data, so it is forced here too. It was previously
    # omitted from this set, leaving LEGAL accounts on password-only auth even
    # though account_security already treated 2FA as mandatory for them.
    MANDATORY_2FA_ROLES = {UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR, UserRole.LEGAL}
    requires_2fa_setup = (
        settings.require_admin_2fa
        and user.role in MANDATORY_2FA_ROLES
        and not user.totp_enabled
    )

    if requires_2fa_setup:
        set_refresh_token_cookie(response, refresh_token_str)
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "requires_2fa_setup": True,
            "setup_dismissals_remaining": 0,
            "2fa_mandatory": True,
        }

    # Return only access token in body (refresh token is in cookie)
    return TokenWithCookie(access_token=access_token)


@router.post("/logout", response_model=MessageResponse)
@limiter.limit("10/minute")
async def logout(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    refresh_token_cookie: Optional[str] = Cookie(
        default=None, alias=REFRESH_TOKEN_COOKIE_NAME
    ),
    refresh_request: Optional[RefreshTokenRequest] = None,
):
    """Logout and revoke tokens.

    Revokes both the access token (used to authenticate this request) and
    the refresh token for immediate session invalidation.

    Supports both cookie-based and body-based refresh token for backwards compatibility.
    The refresh token is read from:
    1. httpOnly cookie (preferred, XSS-safe)
    2. Request body (backwards compatibility during migration)
    """
    ip_address = client_ip(request)

    # Revoke the access token used for this request
    # Extract from Authorization header
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        access_token = auth_header[7:]  # Remove "Bearer " prefix
        # Revoke for remaining token lifetime (max 15 minutes typical)
        # Use configured access token expiry as max revocation duration
        revoke_token(access_token, settings.access_token_expire_minutes * 60)
        logger.debug("Access token revoked on logout")

    # Get refresh token from cookie or body (backwards compatibility)
    refresh_token_value = refresh_token_cookie
    if not refresh_token_value and refresh_request:
        refresh_token_value = refresh_request.refresh_token

    if refresh_token_value:
        result = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token == hash_refresh_token(refresh_token_value),
                RefreshToken.user_id == current_user.id,
            )
        )
        token = result.scalar_one_or_none()

        if token:
            token.revoked_at = datetime.now(timezone.utc)
            await db.commit()

            # Revoke the refresh token by adding it to Redis
            now = datetime.now(timezone.utc)
            if token.expires_at > now:
                expiry_seconds = int((token.expires_at - now).total_seconds())
                revoke_token(
                    refresh_token_value, min(expiry_seconds, 86400)
                )  # Max 24 hours

    # Always clear the cookie on logout
    clear_refresh_token_cookie(response)

    log_security_event(
        "LOGOUT_SUCCESS",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=ip_address,
        severity="INFO",
        details={"access_token_revoked": True},
    )

    return MessageResponse(message="Successfully logged out")


@router.post("/refresh", response_model=RefreshTokenResponse)
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    refresh_token_cookie: Optional[str] = Cookie(
        default=None, alias=REFRESH_TOKEN_COOKIE_NAME
    ),
    refresh_request: Optional[RefreshTokenRequest] = None,
):
    """Exchange refresh token for new access token.

    Supports both cookie-based and body-based refresh token for backwards compatibility.
    The refresh token is read from:
    1. httpOnly cookie (preferred, XSS-safe)
    2. Request body (backwards compatibility during migration)
    """
    # Get refresh token from cookie or body (backwards compatibility)
    refresh_token_value = refresh_token_cookie
    if not refresh_token_value and refresh_request:
        refresh_token_value = refresh_request.refresh_token

    if not refresh_token_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
        )

    result = await db.execute(
        select(RefreshToken).where(RefreshToken.token == hash_refresh_token(refresh_token_value))
    )
    token = result.scalar_one_or_none()

    if not token or not token.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session has expired. Please sign in again.",
        )

    # Get user
    result = await db.execute(select(User).where(User.id == token.user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Your session is no longer active. Please sign in again.",
        )

    # SECURITY: Rotate refresh token (one-time use)
    # Revoke old refresh token to prevent replay attacks
    token.revoked_at = datetime.now(timezone.utc)

    # Create new refresh token
    new_refresh_token_str = create_refresh_token()
    new_refresh_token = RefreshToken(
        user_id=user.id,
        token=hash_refresh_token(new_refresh_token_str),
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=client_ip(request),
        expires_at=get_refresh_token_expiry(),
    )
    db.add(new_refresh_token)

    # Create new access token with user's email
    access_token = create_access_token(
        subject=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
    )

    await db.commit()

    # Set rotated refresh token in cookie
    set_refresh_token_cookie(response, new_refresh_token_str)

    return RefreshTokenResponse(access_token=access_token)


@router.post("/magic-link", response_model=MessageResponse)
@limiter.limit("3/minute")
async def request_magic_link(
    request: Request,
    magic_link_request: MagicLinkRequest,
    db: AsyncSession = Depends(get_db),
):
    """Request a magic link for passwordless login.

    Sends a one-time login link to the user's email.
    Only works for active, verified email accounts.
    Always returns a generic success message to prevent email enumeration.
    """
    ip_address = client_ip(request)

    # Cloudflare Turnstile bot verification — fails open in dev when
    # CF_TURNSTILE_SECRET is unset; rejects bogus tokens when secret is set.
    if not await verify_turnstile(magic_link_request.turnstile_token, ip_address):
        log_security_event(
            "MAGIC_LINK_FAILED",
            ip_address=ip_address,
            severity="WARNING",
            details={"reason": "turnstile_failed"},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Captcha verification failed. Please retry.",
        )

    result = await db.execute(
        select(User).where(User.email_hash == email_blind_hash(magic_link_request.email))
    )
    user = result.scalar_one_or_none()

    if user and user.email_verified and user.is_active:
        # Check if account is locked
        if user.is_locked():
            log_security_event(
                "MAGIC_LINK_ACCOUNT_LOCKED",
                user_id=user.id,
                email=user.email,
                ip_address=ip_address,
                severity="WARNING",
            )
            # Still return generic message to prevent enumeration
        else:
            token = create_magic_link_token()
            user.magic_link_token = hash_magic_link_token(token)
            user.magic_link_token_expires = get_magic_link_token_expiry()
            await db.commit()

            log_security_event(
                "MAGIC_LINK_REQUESTED",
                user_id=user.id,
                email=user.email,
                ip_address=ip_address,
                severity="INFO",
            )

            try:
                await send_magic_link_email(user.email, token, user.first_name)
            except Exception as e:  # noqa: BLE001  # best-effort magic link email — log and continue
                logger.warning(f"Failed to send magic link email for user_id={user.id}: {e}")
    else:
        log_security_event(
            "MAGIC_LINK_INVALID_EMAIL",
            email=magic_link_request.email,
            ip_address=ip_address,
            severity="INFO",
            details={"reason": "not_found_or_unverified"},
        )

    return MessageResponse(
        message="If a verified account exists with that email, a sign-in link has been sent."
    )


@router.post("/magic-link/verify", response_model=TokenWithCookie)
@limiter.limit("10/minute")
async def verify_magic_link(
    request: Request,
    response: Response,
    verify_request: MagicLinkVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify a magic link token and issue access/refresh tokens.

    The magic link token is single-use and expires after 15 minutes.
    On success, returns an access token in the body and sets a refresh
    token as an httpOnly cookie (same as the login endpoint).

    NOTE: This endpoint intentionally has no Turnstile gate. It is invoked
    by a link click from the user's email, not from a rendered form, so
    there is no UI surface in which to mount a TurnstileWidget. Abuse is
    bounded by the per-IP rate limit and the fact that magic-link tokens
    are single-use, expire in 15 minutes, and require possession of the
    user's email inbox. See spec §11 (rate-limiting-tiered-policy).
    """
    ip_address = client_ip(request)

    # Hash incoming token to compare against stored hash
    hashed_token = hash_magic_link_token(verify_request.token)
    result = await db.execute(
        select(User).where(User.magic_link_token == hashed_token)
    )
    user = result.scalar_one_or_none()

    if not user:
        log_security_event(
            "MAGIC_LINK_INVALID_TOKEN",
            ip_address=ip_address,
            severity="WARNING",
            details={"reason": "token_not_found"},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This sign-in link is no longer valid. Please request a new one.",
        )

    # Check token expiry
    if (
        user.magic_link_token_expires
        and datetime.now(timezone.utc) > user.magic_link_token_expires
    ):
        # Clear expired token
        user.magic_link_token = None
        user.magic_link_token_expires = None
        await db.commit()

        log_security_event(
            "MAGIC_LINK_EXPIRED_TOKEN",
            user_id=user.id,
            email=user.email,
            ip_address=ip_address,
            severity="WARNING",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic link has expired. Please request a new one.",
        )

    # Check account is still active and not locked
    if not user.is_active:
        user.magic_link_token = None
        user.magic_link_token_expires = None
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="This sign-in link is no longer valid. Please request a new one.",
        )

    if user.is_locked():
        user.magic_link_token = None
        user.magic_link_token_expires = None
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Your account is locked due to multiple failed login attempts. Please try again later.",
        )

    # Invalidate the token (single-use)
    user.magic_link_token = None
    user.magic_link_token_expires = None

    # Reset failed login attempts on successful magic link login
    user.failed_login_attempts = 0
    user.locked_until = None

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)

    # Create tokens (same flow as password login)
    access_token = create_access_token(
        subject=user.id,
        email=user.email,
        role=user.role.value if hasattr(user.role, 'value') else str(user.role),
    )
    refresh_token_str = create_refresh_token()

    # Store refresh token in database
    refresh_token = RefreshToken(
        user_id=user.id,
        token=hash_refresh_token(refresh_token_str),
        device_info=request.headers.get("User-Agent", "")[:255],
        ip_address=ip_address,
        expires_at=get_refresh_token_expiry(),
    )
    db.add(refresh_token)
    await db.commit()

    log_security_event(
        "MAGIC_LINK_LOGIN_SUCCESS",
        user_id=user.id,
        email=user.email,
        ip_address=ip_address,
        severity="INFO",
        details={"user_agent": request.headers.get("User-Agent", "")[:100]},
    )

    # Set refresh token as httpOnly cookie
    set_refresh_token_cookie(response, refresh_token_str)

    return TokenWithCookie(access_token=access_token)


@router.get("/login")
async def get_login(
    response: Response,
):
    """Legacy GET compatibility endpoint for login.

    Intentionally public to avoid breaking older clients that called this
    endpoint before authentication.
    """
    add_deprecated_get_headers(response, replacement_method="POST")
    return {"status": "ok"}


@router.get("/logout")
async def get_logout(
    response: Response,
):
    """Legacy GET compatibility endpoint for logout.

    Intentionally public to match login/forgot-password for consistency,
    though logout typically requires authentication in the POST variant.
    """
    add_deprecated_get_headers(response, replacement_method="POST")
    return {"status": "ok"}
