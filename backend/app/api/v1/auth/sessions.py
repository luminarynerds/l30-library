# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....core.rate_limit import client_ip, limiter
from ....models.user import RefreshToken, User
from ....schemas.user import RevokeAllSessionsResponse, SessionInfo, SessionList
from .helpers import get_current_user, log_security_event

logger = get_logger(__name__)

router = APIRouter()


@router.get("/sessions", response_model=SessionList)
@limiter.limit("20/minute")
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all active sessions for current user."""
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .order_by(RefreshToken.created_at.desc())
    )
    tokens = result.scalars().all()

    # Try to identify current session
    current_ip = client_ip(request)
    current_ua = request.headers.get("User-Agent", "")

    sessions = []
    for t in tokens:
        is_current = (
            t.ip_address == current_ip
            and t.device_info
            and current_ua.startswith(t.device_info[:50])
        )
        sessions.append(
            SessionInfo(
                id=t.id,
                device_info=t.device_info,
                ip_address=t.ip_address,
                created_at=t.created_at,
                last_active_at=t.last_active_at,
                is_current=is_current,
            )
        )

    return SessionList(sessions=sessions)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a specific session."""
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.id == session_id, RefreshToken.user_id == current_user.id
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="That session was not found or has already ended.")

    token.revoked_at = datetime.now(timezone.utc)
    await db.commit()


@router.post("/sessions/revoke-all-others", response_model=RevokeAllSessionsResponse)
async def revoke_all_other_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoke all sessions except the current one."""
    current_ip = client_ip(request)
    current_ua = request.headers.get("User-Agent", "")

    # Get all active sessions
    result = await db.execute(
        select(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    tokens = result.scalars().all()

    revoked_count = 0
    now = datetime.now(timezone.utc)

    for token in tokens:
        # Skip the current session
        is_current = (
            token.ip_address == current_ip
            and token.device_info
            and current_ua.startswith(token.device_info[:50])
        )
        if not is_current:
            token.revoked_at = now
            revoked_count += 1

    await db.commit()

    log_security_event(
        "SESSIONS_REVOKED_ALL_OTHERS",
        user_id=current_user.id,
        email=current_user.email,
        ip_address=current_ip,
        severity="INFO",
        details={"revoked_count": revoked_count},
    )

    return RevokeAllSessionsResponse(
        message=f"Successfully signed out of {revoked_count} other session{'s' if revoked_count != 1 else ''}",
        revoked_count=revoked_count,
    )
