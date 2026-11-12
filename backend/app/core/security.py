# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
from app.core.logging import get_logger
import re
import secrets
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any, Optional

try:
    import redis as redis_module

    REDIS_AVAILABLE = True
except ImportError:
    redis_module = None
    REDIS_AVAILABLE = False

if TYPE_CHECKING:
    import redis

import jwt
from jwt.exceptions import PyJWTError as JWTError
import bcrypt

from .cache_strategies import CacheTTL

from .config import get_settings

logger = get_logger(__name__)

settings = get_settings()


def generate_library_card() -> str:
    import string
    from .branding import branding

    # Format: LSC-XXXX-XXXX where X is alphanumeric
    # SECURITY: Use secrets module for cryptographically secure generation
    alphabet = string.ascii_uppercase + string.digits
    part1 = ''.join(secrets.choice(alphabet) for _ in range(4))
    part2 = ''.join(secrets.choice(alphabet) for _ in range(4))
    return f"{branding.CARD_PREFIX}-{part1}-{part2}"

# Number of previous passwords to check for password reuse prevention
PASSWORD_HISTORY_COUNT = 5

# Common weak passwords to block
COMMON_PASSWORDS = {
    "password",
    "password123",
    "password123!",
    "123456",
    "12345678",
    "qwerty",
    "abc123",
    "monkey",
    "1234567",
    "letmein",
    "trustno1",
    "dragon",
    "baseball",
    "iloveyou",
    "master",
    "sunshine",
    "ashley",
    "foobar",
    "passw0rd",
    "shadow",
    "123123",
    "654321",
    "superman",
    "qazwsx",
    "michael",
    "football",
    "password1",
    "password12",
    "princess",
    "admin",
    "welcome",
}

# Redis client for token revocation list
_redis_client: Optional["redis.Redis"] = None

# In-memory cache for graceful Redis degradation (circuit breaker)
# Maps token_hash -> timestamp_verified
_TOKEN_VERIFY_CACHE: OrderedDict[str, float] = OrderedDict()
_TOKEN_CACHE_MAX_SIZE = 10000
_TOKEN_CACHE_TTL_SECONDS = CacheTTL.MEDIUM  # 5 minutes — accept this security window during Redis outage
_redis_available = True
_redis_last_check = 0.0
_REDIS_RETRY_INTERVAL = 10.0  # seconds between Redis reconnection attempts
_redis_last_warning = 0.0
_REDIS_WARNING_INTERVAL = 60.0  # seconds between Redis warning log messages


def get_redis_client() -> Optional["redis.Redis"]:
    global _redis_client
    if not REDIS_AVAILABLE:
        return None

    if _redis_client is None:
        try:
            _redis_client = redis_module.from_url(settings.redis_url, decode_responses=True)
            _redis_client.ping()
        except Exception as e:  # noqa: BLE001  # Redis client init boundary — connection/auth/network errors all degrade to None
            logger.warning("Failed to connect to Redis for token revocation list: %s", e)
            _redis_client = None

    return _redis_client


def _token_revocation_key(token: str) -> str:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return f"token_revocation:{token_hash}"


def _get_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _cache_put(token_hash: str, timestamp: float) -> None:
    # Move to end if already present (LRU behavior)
    if token_hash in _TOKEN_VERIFY_CACHE:
        _TOKEN_VERIFY_CACHE.move_to_end(token_hash)
    _TOKEN_VERIFY_CACHE[token_hash] = timestamp
    # Evict oldest entries if cache exceeds max size
    while len(_TOKEN_VERIFY_CACHE) > _TOKEN_CACHE_MAX_SIZE:
        _TOKEN_VERIFY_CACHE.popitem(last=False)


def _cache_check(token_hash: str) -> bool | None:
    if token_hash not in _TOKEN_VERIFY_CACHE:
        return None
    cached_time = _TOKEN_VERIFY_CACHE[token_hash]
    if time.monotonic() - cached_time > _TOKEN_CACHE_TTL_SECONDS:
        # Expired entry — remove it
        _TOKEN_VERIFY_CACHE.pop(token_hash, None)
        return None
    return True


def is_token_revoked(token: str) -> bool:
    global _redis_available, _redis_last_check, _redis_last_warning

    token_hash = _get_token_hash(token)
    now = time.monotonic()

    # --- Normal path: try Redis first ---
    if _redis_available or (now - _redis_last_check >= _REDIS_RETRY_INTERVAL):
        try:
            redis_client = get_redis_client()
            if redis_client is None:
                raise ConnectionError("Redis client unavailable")

            revocation_key = _token_revocation_key(token)
            is_revoked = redis_client.exists(revocation_key) > 0

            # Redis is working — mark as available
            if not _redis_available:
                logger.info("Redis connection restored for token revocation checks")
            _redis_available = True

            # Cache non-revoked tokens for fallback during future outages
            if not is_revoked:
                _cache_put(token_hash, now)

            return is_revoked

        except Exception as e:  # noqa: BLE001  # Redis boundary — any failure must degrade to in-memory cache, not 500
            # Redis failed — enter degraded mode
            _redis_last_check = now
            if _redis_available or (now - _redis_last_warning >= _REDIS_WARNING_INTERVAL):
                logger.warning(
                    f"Redis unavailable for token revocation check: {str(e)} — "
                    f"falling back to in-memory cache for recently verified tokens"
                )
                _redis_last_warning = now
            _redis_available = False

    # --- Degraded path: Redis is down, use in-memory cache ---
    cache_result = _cache_check(token_hash)
    if cache_result is True:
        # Token was recently verified as non-revoked — allow it through
        return False

    # Unknown or expired token — fail-secure
    return True


def revoke_token(token: str, expiry_seconds: int) -> None:
    # Also remove from in-memory cache to ensure immediate logout
    token_hash = _get_token_hash(token)
    _TOKEN_VERIFY_CACHE.pop(token_hash, None)

    redis_client = get_redis_client()
    if redis_client is None:
        logger.error("Redis not available for token revocation - logout failed")
        raise Exception("Token revocation failed: Redis unavailable")

    try:
        revocation_key = _token_revocation_key(token)
        # Set with expiry so Redis automatically removes it
        redis_client.setex(revocation_key, expiry_seconds, "1")
        logger.debug("Token revoked with %ss expiry", expiry_seconds)
    except Exception as e:
        logger.error("Error revoking token: %s", e)
        # SECURITY: Raise exception to ensure logout fails visibly
        # Better to fail logout than silently allow continued access
        raise Exception(f"Token revocation failed: {str(e)}") from e


def get_token_cache_status() -> dict:
    return {
        "redis_available": _redis_available,
        "cached_tokens": len(_TOKEN_VERIFY_CACHE),
        "cache_max_size": _TOKEN_CACHE_MAX_SIZE,
        "cache_ttl_seconds": _TOKEN_CACHE_TTL_SECONDS,
    }


class PasswordValidationError(Exception):

    pass


def validate_password(password: str) -> None:
    if len(password) < settings.password_min_length:
        raise PasswordValidationError(
            f"Password must be at least {settings.password_min_length} characters"
        )

    if not re.search(r"\d", password):
        raise PasswordValidationError("Password must contain at least one number")

    if not re.search(r"[a-z]", password):
        raise PasswordValidationError("Password must contain at least one lowercase letter")

    if not re.search(r"[A-Z]", password):
        raise PasswordValidationError("Password must contain at least one uppercase letter")

    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise PasswordValidationError("Password must contain at least one special character")

    if password.lower() in COMMON_PASSWORDS:
        raise PasswordValidationError(
            "Password is too common, please choose a stronger one"
        )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError) as e:
        # Log the real error for debugging but don't expose to caller
        logger.warning("Password verification error: %s: %s", type(e).__name__, e)
        # Return False instead of raising - treats verification errors same as invalid password
        return False


def hash_password(password: str) -> str:
    try:
        # Bcrypt can handle most characters including null bytes via binary encoding
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    except Exception as e:
        # Catch any hashing errors and convert to validation error
        logger.warning("Password hashing error: %s: %s", type(e).__name__, e)
        raise PasswordValidationError("Password cannot be hashed: invalid characters") from e


async def verify_password_async(plain_password: str, hashed_password: str) -> bool:
    return await asyncio.to_thread(verify_password, plain_password, hashed_password)


async def hash_password_async(password: str) -> str:
    return await asyncio.to_thread(hash_password, password)


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    email: str | None = None,
    role: str | None = None,
    **kwargs,
) -> str:
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    # Handle dictionary subject or extract claims
    if isinstance(subject, dict):
        # Merge dictionary claims into kwargs
        subject_dict = subject.copy()
        # Extract sub and email from the dictionary if present
        sub_value = subject_dict.pop("sub", str(subject_dict))
        email_value = subject_dict.pop("email", email)
        # Merge remaining claims
        kwargs = {**subject_dict, **kwargs}
    else:
        sub_value = str(subject)
        email_value = email

    # Ensure email is provided or use a sensible default
    if email_value is None:
        email_value = f"user-{sub_value}@library.local"

    to_encode = {
        "sub": sub_value,
        "exp": expire,
        "email": email_value,
        "type": "access",
    }

    # Add role if provided
    if role is not None:
        to_encode["role"] = role

    # Include any additional claims
    to_encode.update(kwargs)

    # Use primary JWT key if configured, otherwise fall back to secret_key
    signing_key = settings.jwt_secret_key or settings.secret_key
    return jwt.encode(to_encode, signing_key, algorithm=settings.algorithm)


def create_refresh_token() -> str:
    return secrets.token_urlsafe(32)


def create_reset_token() -> str:
    return secrets.token_urlsafe(32)


def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_reset_token(plain_token: str, hashed_token: str) -> bool:
    computed_hash = hash_reset_token(plain_token)
    return secrets.compare_digest(computed_hash, hashed_token)


def create_verification_token() -> str:
    return secrets.token_urlsafe(32)


def decode_token(token: str) -> str | None:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key or settings.secret_key,
            algorithms=[settings.algorithm],
            options={"verify_exp": True},
        )
        return payload.get("sub")
    except (jwt.InvalidSignatureError, JWTError):
        # If primary key fails and previous key is configured, try it
        if settings.jwt_secret_key_previous:
            try:
                payload = jwt.decode(
                    token,
                    settings.jwt_secret_key_previous,
                    algorithms=[settings.algorithm],
                    options={"verify_exp": True},
                )
                user_id = payload.get("sub")
                if user_id:
                    logger.info(
                        "Token verified with previous key during rotation — user %s should refresh soon",
                        user_id
                    )
                return user_id
            except JWTError:
                return None
        return None


def verify_token(token: str, check_revocation: bool = True) -> dict[str, Any]:
    if not token or not isinstance(token, str):
        raise JWTError("Token must be a non-empty string")

    # Validate token format (should be three parts: header.payload.signature)
    token_parts = token.split(".")
    if len(token_parts) != 3:
        raise JWTError("Invalid token format. Expected 3 parts separated by dots.")

    # Check if token is revoked (logout)
    # SECURITY: Check after format validation so malformed tokens fail first
    if check_revocation and is_token_revoked(token):
        raise JWTError("Token has been revoked (logged out)")

    # Build list of keys to try for verification (primary first, then previous)
    keys_to_try = [settings.jwt_secret_key or settings.secret_key]
    if settings.jwt_secret_key_previous:
        keys_to_try.append(settings.jwt_secret_key_previous)

    payload = None
    last_error = None
    used_previous_key = False

    # Try each key in order
    for key_index, key in enumerate(keys_to_try):
        try:
            payload = jwt.decode(
                token,
                key,
                algorithms=[settings.algorithm],  # Only accept configured algorithm (HS256 allowlist)
                options={
                    "verify_exp": True
                },  # SECURITY: Explicitly enforce expiry validation
            )
            used_previous_key = (key_index > 0)
            break  # Success, stop trying keys
        except jwt.ExpiredSignatureError:
            # Re-raise expired signature errors immediately — don't try other keys
            raise
        except jwt.InvalidSignatureError as e:
            # Signature invalid with this key, try next if available
            last_error = e
            continue
        except JWTError as e:
            # Other JWT errors, try next key
            last_error = e
            continue

    # If all keys failed, raise error
    if payload is None:
        error_msg = "Token signature invalid against all configured keys"
        if last_error:
            error_msg = f"Token validation failed: {str(last_error)}"
        raise JWTError(error_msg)

    # Log when token is verified with previous key during rotation
    if used_previous_key:
        user_id = payload.get("sub")
        if user_id:
            logger.info(
                "Token verified with previous key — user %s should refresh soon",
                user_id
            )

    # Verify required claims exist
    if "sub" not in payload:
        raise jwt.MissingRequiredClaimError("sub")

    if "email" not in payload:
        raise jwt.MissingRequiredClaimError("email")

    # Verify token has expiry information
    if "exp" not in payload:
        raise jwt.MissingRequiredClaimError("exp")

    # SECURITY: At this point, token expiry has been verified by jwt.decode()
    # with verify_exp=True option. Expired tokens will raise ExpiredSignatureError
    # before reaching this code. All security validations have passed.
    # Algorithm is restricted to HS256 only to prevent algorithm confusion attacks.

    return payload


def get_refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )


def get_reset_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=1)


def get_verification_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=24)


def create_magic_link_token() -> str:
    return secrets.token_urlsafe(32)


def hash_magic_link_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_magic_link_token(plain_token: str, hashed_token: str) -> bool:
    computed_hash = hash_magic_link_token(plain_token)
    return secrets.compare_digest(computed_hash, hashed_token)


def get_magic_link_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=15)


# ─── 2FA Pending Tokens ─────────────────────────────────────────────────────
# Stored in Redis with 5-minute TTL. Contains user_id for token issuance after 2FA.

_TWO_FA_PENDING_PREFIX = "2fa_pending:"
_TWO_FA_PENDING_TTL = 300  # 5 minutes
_TWO_FA_ATTEMPTS_PREFIX = "2fa_attempts:"

# In-memory fallback for 2FA pending tokens (maps key -> (value, expiry_time))
_2fa_memory_cache: dict[str, tuple[str, float]] = {}


def create_2fa_pending_token(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    redis_client = get_redis_client()
    if redis_client:
        try:
            redis_client.setex(
                f"{_TWO_FA_PENDING_PREFIX}{token_hash}",
                _TWO_FA_PENDING_TTL,
                str(user_id),
            )
            redis_client.setex(
                f"{_TWO_FA_ATTEMPTS_PREFIX}{token_hash}",
                _TWO_FA_PENDING_TTL,
                "0",
            )
            return token
        except Exception as e:  # noqa: BLE001  # Redis boundary — fall back to in-memory cache, never block 2FA setup
            logger.warning("Redis error storing 2FA pending token: %s", e)

    # Fallback to in-memory
    _2fa_memory_cache[f"{_TWO_FA_PENDING_PREFIX}{token_hash}"] = (
        str(user_id),
        time.time() + _TWO_FA_PENDING_TTL,
    )
    _2fa_memory_cache[f"{_TWO_FA_ATTEMPTS_PREFIX}{token_hash}"] = (
        "0",
        time.time() + _TWO_FA_PENDING_TTL,
    )
    return token


def verify_2fa_pending_token(token: str) -> int | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    key = f"{_TWO_FA_PENDING_PREFIX}{token_hash}"

    redis_client = get_redis_client()
    if redis_client:
        try:
            from .totp import MAX_2FA_ATTEMPTS
            attempts = redis_client.get(f"{_TWO_FA_ATTEMPTS_PREFIX}{token_hash}")
            if attempts and int(attempts) >= MAX_2FA_ATTEMPTS:
                redis_client.delete(key)
                redis_client.delete(f"{_TWO_FA_ATTEMPTS_PREFIX}{token_hash}")
                return None

            user_id = redis_client.get(key)
            if user_id:
                return int(user_id)
            return None
        except Exception as e:  # noqa: BLE001  # Redis boundary — fall back to in-memory cache for 2FA verification
            logger.warning("Redis error verifying 2FA pending token: %s", e)

    # Fallback to memory
    if key in _2fa_memory_cache:
        value, expiry = _2fa_memory_cache[key]
        if time.time() < expiry:
            return int(value)
        del _2fa_memory_cache[key]

    return None


def increment_2fa_attempts(token: str) -> int:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    attempts_key = f"{_TWO_FA_ATTEMPTS_PREFIX}{token_hash}"

    redis_client = get_redis_client()
    if redis_client:
        try:
            return int(redis_client.incr(attempts_key))
        except Exception:  # noqa: BLE001  # Redis boundary — attempt tracking falls back to in-memory cache
            logger.debug("Redis 2FA attempt tracking failed, using memory fallback", exc_info=True)

    # Fallback
    if attempts_key in _2fa_memory_cache:
        val, exp = _2fa_memory_cache[attempts_key]
        new_val = str(int(val) + 1)
        _2fa_memory_cache[attempts_key] = (new_val, exp)
        return int(new_val)
    return 0


def consume_2fa_pending_token(token: str) -> int | None:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    key = f"{_TWO_FA_PENDING_PREFIX}{token_hash}"
    attempts_key = f"{_TWO_FA_ATTEMPTS_PREFIX}{token_hash}"

    redis_client = get_redis_client()
    if redis_client:
        try:
            user_id = redis_client.get(key)
            if user_id:
                redis_client.delete(key)
                redis_client.delete(attempts_key)
                return int(user_id)
            return None
        except Exception as e:  # noqa: BLE001  # Redis boundary — fall back to in-memory cache for 2FA token consumption
            logger.warning("Redis error consuming 2FA pending token: %s", e)

    # Fallback
    if key in _2fa_memory_cache:
        value, expiry = _2fa_memory_cache.pop(key)
        _2fa_memory_cache.pop(attempts_key, None)
        if time.time() < expiry:
            return int(value)

    return None
