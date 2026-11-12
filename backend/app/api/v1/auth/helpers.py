# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.cache_strategies import CacheTTL
from ....core.config import get_settings
from ....core.database import get_db
from ....core.security import verify_token
from ....core.audit_log import audit_log_event
from ....models.user import User

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Known Device Redis Cache Helpers
# ---------------------------------------------------------------------------
KNOWN_DEVICE_CACHE_TTL = CacheTTL.LONG  # 1 hour


def _known_device_cache_key(user_id: int, device_hash: str) -> str:
    return f"known_device:{user_id}:{device_hash}"


async def _get_known_device_cached(user_id: int, device_hash: str) -> Optional[dict]:
    from ....core.cache import get_cached
    try:
        return await get_cached(_known_device_cache_key(user_id, device_hash))
    except Exception:  # noqa: BLE001  # Redis fail-open — cache miss on any error
        logger.debug("Redis known-device cache miss (error)", exc_info=True)
        return None


async def _set_known_device_cached(
    user_id: int, device_hash: str, device_data: dict
) -> None:
    from ....core.cache import set_cached
    try:
        await set_cached(
            _known_device_cache_key(user_id, device_hash),
            device_data,
            ttl_seconds=KNOWN_DEVICE_CACHE_TTL,
        )
    except Exception:  # noqa: BLE001  # Redis fail-open — cache write best-effort
        logger.debug("Redis known-device cache write failed", exc_info=True)


async def _invalidate_known_device_cache(
    user_id: int, device_hash: str
) -> None:
    from ....core.cache import get_redis
    try:
        client = await get_redis()
        if client:
            await client.delete(_known_device_cache_key(user_id, device_hash))
    except Exception:  # noqa: BLE001  # Redis fail-open — invalidation best-effort
        logger.debug("Redis known-device cache invalidation failed", exc_info=True)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
settings = get_settings()

# Cookie configuration for refresh tokens
REFRESH_TOKEN_COOKIE_NAME = "refresh_token"
REFRESH_TOKEN_COOKIE_MAX_AGE = settings.refresh_token_expire_days * 24 * 60 * 60  # in seconds


def set_refresh_token_cookie(response: Response, refresh_token: str) -> None:
    is_production = settings.environment == "production"
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=is_production,
        samesite="lax",
        max_age=REFRESH_TOKEN_COOKIE_MAX_AGE,
        path="/api/v1/auth",  # Only send cookie to auth endpoints
    )


def clear_refresh_token_cookie(response: Response) -> None:
    is_production = settings.environment == "production"
    response.delete_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        httponly=True,
        secure=is_production,
        samesite="lax",
        path="/api/v1/auth",
    )


def log_security_event(
    event_type: str,
    user_id: Optional[int] = None,
    email: Optional[str] = None,
    ip_address: Optional[str] = None,
    severity: str = "INFO",
    details: Optional[dict] = None,
) -> None:
    log_data = {
        "event_type": event_type,
        "severity": severity,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if user_id:
        log_data["user_id"] = user_id
    if email:
        log_data["email"] = email
    if ip_address:
        log_data["ip_address"] = ip_address
    if details:
        log_data["details"] = details

    log_level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(log_level, f"SECURITY_EVENT: {event_type}", extra=log_data)

    # Write to immutable audit log for critical security events
    audit_events = {
        "LOGIN_SUCCESS",
        "LOGIN_FAILED",
        "ACCOUNT_LOCKED",
        "TOKEN_REVOKED",
        "ROLE_CHANGED",
        "PERMISSION_CHANGED",
        "PAYMENT_PROCESSED",
        "REFUND_PROCESSED",
        "USER_CREATED",
        "USER_DELETED",
        "PASSWORD_RESET",
        "EMAIL_CHANGED",
    }

    if event_type in audit_events:
        audit_log_event(
            event_type=event_type,
            user_id=user_id,
            email=email,
            ip_address=ip_address,
            severity=severity,
            details=details,
        )


def add_deprecated_get_headers(response: Response, replacement_method: str = "POST") -> None:
    response.headers["Warning"] = (
        '299 - "Deprecated auth GET endpoint. Use the documented method instead."'
    )
    response.headers["X-Deprecated"] = "true"
    response.headers["X-Replacement-Method"] = replacement_method


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Your session has expired. Please sign in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Verify token using comprehensive validation including revocation check
    try:
        payload = verify_token(token, check_revocation=True)
        user_id = payload.get("sub")
        if user_id is None:
            log_security_event(
                "TOKEN_VERIFICATION_FAILED",
                severity="WARNING",
                details={"reason": "missing_sub_claim"},
            )
            raise credentials_exception
    except Exception as e:
        log_security_event(
            "TOKEN_VERIFICATION_FAILED", severity="WARNING", details={"error": str(e)}
        )
        raise credentials_exception from e

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        log_security_event("USER_NOT_FOUND", user_id=int(user_id), severity="WARNING")
        raise credentials_exception

    return user


async def get_optional_user(
    token: Optional[str] = Depends(
        OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)
    ),
    db: AsyncSession = Depends(get_db),
) -> Optional[User]:
    if token is None:
        return None

    try:
        # Use verify_token instead of decode_token to check revocation
        payload = verify_token(token, check_revocation=True)
        user_id = payload.get("sub")
        if user_id is None:
            return None

        result = await db.execute(select(User).where(User.id == int(user_id)))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            return None

        return user
    except Exception:  # noqa: BLE001  # optional-user fallback — return None on any decode failure
        logger.warning("get_optional_user failed unexpectedly", exc_info=True)
        return None


def generate_library_card() -> str:
    import secrets
    # SECURITY: Use secrets module for cryptographically secure generation
    random_digits = ''.join(str(secrets.randbelow(10)) for _ in range(6))
    return f"LSC{random_digits}"


def generate_temp_card() -> str:
    import secrets
    import string
    from ....core.branding import branding

    alphabet = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(alphabet) for _ in range(4))
    part2 = ''.join(secrets.choice(alphabet) for _ in range(4))
    return f"{branding.TEMP_CARD_PREFIX}-{part1}-{part2}"


# Alias for backwards compatibility - use get_optional_user instead
get_current_user_optional = get_optional_user
