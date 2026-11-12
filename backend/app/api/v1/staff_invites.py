# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .dependencies import require_admin
from ...core.database import get_db
from ...core.security import create_reset_token, hash_reset_token, hash_password
from ...core.staff_invite_email import send_staff_invite_email
from ...models.user import User, UserRole, email_blind_hash
from ...models.audit_log import AuditAction
from .users import create_audit_log, get_client_ip

router = APIRouter(prefix="/staff-invites", tags=["staff-invites"])

_INVITABLE_ROLES = {UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DIRECTOR, UserRole.LIBRARY_ADMIN, UserRole.STAFF}
_INVITE_TTL = timedelta(hours=72)


class StaffInviteCreate(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    staff_role: str | None = None


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_staff_invite(
    payload: StaffInviteCreate,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    if payload.role not in _INVITABLE_ROLES:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Role is not a staff role")
    if payload.role == UserRole.SUPER_ADMIN and admin_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only SUPER_ADMIN can invite SUPER_ADMIN")

    existing = await db.execute(select(User).where(User.email_hash == email_blind_hash(payload.email)))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    raw = create_reset_token()
    user = User(
        email=payload.email,
        password_hash=hash_password(secrets.token_urlsafe(32)),
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
        staff_role=payload.staff_role,
        is_active=False,
        email_verified=False,
        home_library_system_id=admin_user.home_library_system_id,
    )
    user.invite_token = hash_reset_token(raw)
    user.invite_token_expires = datetime.now(timezone.utc) + _INVITE_TTL
    db.add(user)
    await db.flush()

    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.CREATE_USER,
        target_user_id=user.id,
        details={"email": user.email, "role": user.role, "invited": True},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    try:
        await send_staff_invite_email(payload.email, raw, payload.first_name)
    except Exception:  # invite is created; email is best-effort and recoverable via resend
        logging.getLogger("staff_invites").exception(
            "Failed to send staff invite email to %s", payload.email
        )
    return {"status": "invited", "user_id": user.id}


@router.post("/{user_id}/resend", status_code=status.HTTP_200_OK)
async def resend_staff_invite(
    user_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or user.is_active or user.invite_token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending invite for this user")
    raw = create_reset_token()
    user.invite_token = hash_reset_token(raw)
    user.invite_token_expires = datetime.now(timezone.utc) + _INVITE_TTL
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.UPDATE_USER,
        target_user_id=user.id,
        details={"email": user.email, "invite_resent": True},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await db.commit()
    try:
        await send_staff_invite_email(user.email, raw, user.first_name)
    except Exception:
        logging.getLogger("staff_invites").exception("Failed to resend staff invite email to %s", user.email)
    return {"status": "resent"}


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def revoke_staff_invite(
    user_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None or user.is_active or user.invite_token is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No pending invite for this user")
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.DELETE_USER,
        target_user_id=user.id,
        details={"email": user.email, "invite_revoked": True},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )
    await db.flush()  # persist audit log row before deleting the referenced user
    await db.delete(user)
    await db.commit()
    return {"status": "revoked"}
