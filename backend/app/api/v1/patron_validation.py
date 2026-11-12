# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron validation endpoint for third-party app integrations."""
import hashlib
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.rate_limit import limiter
from ...core.security import verify_password_async
from ...models.api_key import APIKey
from ...models.user import User

logger = get_logger(__name__)
router = APIRouter(prefix="/patron", tags=["patron-validation"])


class PatronValidateRequest(BaseModel):
    card_number: str
    pin: str


class PatronValidateResponse(BaseModel):
    valid: bool
    patron_id: str | None = None
    patron_type: str | None = None
    card_status: str | None = None
    expiration_date: str | None = None
    home_library: str | None = None
    reason: str | None = None


async def _verify_api_key(
    db: AsyncSession,
    x_api_key: str,
    request: Request,
) -> APIKey:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")

    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    result = await db.execute(
        select(APIKey).where(APIKey.key_hash == key_hash, APIKey.is_active == True)
    )
    api_key = result.scalar_one_or_none()

    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check IP allowlist if configured
    if api_key.allowed_ips:
        client_ip = request.client.host if request.client else None
        allowed = [ip.strip() for ip in api_key.allowed_ips.split(",")]
        if client_ip and client_ip not in allowed:
            raise HTTPException(status_code=403, detail="IP not allowed")

    # Update last_used timestamp
    api_key.last_used_at = datetime.now(timezone.utc)
    await db.commit()

    return api_key


@router.post("/validate", response_model=PatronValidateResponse)
@limiter.limit("100/minute")
async def validate_patron(  # noqa: role-check -- API-key gated for 3rd-party patron validation
    request: Request,
    body: PatronValidateRequest,
    db: AsyncSession = Depends(get_db),
    x_api_key: str = Header(default=""),
):
    """Validate a patron library card and PIN.

    Used by third-party apps (hoopla, Libby, Kanopy) to verify
    patron membership. Requires a valid API key.
    """
    api_key = await _verify_api_key(db, x_api_key, request)

    # Look up patron by library card
    result = await db.execute(
        select(User).where(User.library_card == body.card_number)
    )
    user = result.scalar_one_or_none()

    # Timing-safe: always verify password even if user not found
    dummy_hash = "$2b$12$LJ3m4ys3Lg2VBe6p0C5Yn.OhIMFnXHPBpckgVMH/SkYFRsFfTeNHi"
    password_valid = await verify_password_async(
        body.pin,
        user.password_hash if user and user.password_hash else dummy_hash,
    )

    if not user or not password_valid:
        logger.info(
            "Patron validation failed",
            extra={
                "vendor": api_key.vendor_name,
                "card_prefix": body.card_number[:4] + "***",
                "reason": "not_found" if not user else "invalid_pin",
            },
        )
        return PatronValidateResponse(valid=False, reason="invalid_credentials")

    if not user.is_active:
        return PatronValidateResponse(valid=False, reason="account_inactive")

    if user.is_locked():
        return PatronValidateResponse(valid=False, reason="account_locked")

    # Generate anonymous patron ID (hash of user ID + vendor for consistency)
    patron_hash = hashlib.sha256(
        f"{user.id}:{api_key.vendor_name}".encode()
    ).hexdigest()[:12]

    # Determine card status
    card_status = "active"
    if getattr(user, "card_type", None) == "temporary":
        if user.card_trial_expires_at:
            if user.card_trial_expires_at < datetime.now(timezone.utc):
                return PatronValidateResponse(valid=False, reason="card_expired")
            card_status = "temporary"

    # Get expiration date if available
    expiration = None
    if user.card_expires_at:
        expiration = user.card_expires_at.strftime("%Y-%m-%d")

    logger.info(
        "Patron validation succeeded",
        extra={
            "vendor": api_key.vendor_name,
            "patron_type": getattr(user, "patron_type", "adult"),
        },
    )

    return PatronValidateResponse(
        valid=True,
        patron_id=patron_hash,
        patron_type=getattr(user, "patron_type", "adult"),
        card_status=card_status,
        expiration_date=expiration,
        home_library=str(user.home_branch_id) if user.home_branch_id else None,
    )
