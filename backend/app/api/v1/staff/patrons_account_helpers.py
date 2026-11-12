# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Helper functions for staff patron account endpoints."""

from fastapi import HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.shortcuts import get_or_404
from ....models.user import User, UserRole


async def check_staff_access_permission(
    patron_id: int,
    staff_user: User,
    db: AsyncSession,
    require_consent: bool = True,
    request: Request | None = None,
) -> dict:
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    if staff_user.role in [UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DIRECTOR]:
        # Audit log: admin/director overriding patron consent preference
        if not patron.allow_staff_access_to_history:
            from ....models.audit_log import AuditAction, AuditLog
            db.add(AuditLog(
                admin_id=staff_user.id,
                target_user_id=patron.id,
                action=AuditAction.VIEWED,
                details={
                    "resource_type": "patron_history",
                    "event": "consent_override",
                    "override_reason": "Administrator access",
                    "patron_consent": False,
                    "staff_role": staff_user.role.value,
                },
                ip_address=request.client.host if request and request.client else None,
            ))
            await db.flush()
        return {
            "allowed": True,
            "consent_given": patron.allow_staff_access_to_history,
            "requires_consent": True,
            "override_reason": "Administrator access",
        }

    if not patron.allow_staff_access_to_history:
        if require_consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Access denied: Patron has opted out of staff viewing history. "
                    "Patron must enable 'allow_staff_access_to_history' in privacy settings."
                ),
            )
        return {
            "allowed": False,
            "consent_given": False,
            "requires_consent": True,
        }

    return {
        "allowed": True,
        "consent_given": True,
        "requires_consent": True,
    }
