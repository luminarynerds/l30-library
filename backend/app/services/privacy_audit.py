# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit_log import AuditLog, AuditAction

logger = get_logger(__name__)


class PrivacyAuditLogger:

    @staticmethod
    async def log_privacy_change(
        db: AsyncSession,
        user_id: int,
        action: AuditAction,
        resource_type: str,
        resource_id: int,
        old_value: bool,
        new_value: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        # Build description
        old_privacy = "public" if old_value else "private"
        new_privacy = "public" if new_value else "private"

        details = {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "old_privacy": old_privacy,
            "new_privacy": new_privacy,
            "changed_at": datetime.now(timezone.utc).isoformat(),
        }

        # Create audit log entry
        # Note: admin_id is None because this is a user changing their own privacy settings
        # target_user_id is set to the user making the change
        audit_entry = AuditLog(
            admin_id=None,
            target_user_id=user_id,
            action=action,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else None,
        )

        db.add(audit_entry)
        logger.info(
            f"Privacy change logged: user={user_id}, resource={resource_type}/{resource_id}, "
            f"{old_privacy}->{new_privacy}"
        )

        return audit_entry

    @staticmethod
    async def log_reading_list_privacy_change(
        db: AsyncSession,
        user_id: int,
        list_id: int,
        old_is_public: bool,
        new_is_public: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        return await PrivacyAuditLogger.log_privacy_change(
            db=db,
            user_id=user_id,
            action=AuditAction.PRIVACY_CHANGE_READING_LIST,
            resource_type="reading_list",
            resource_id=list_id,
            old_value=old_is_public,
            new_value=new_is_public,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_favorites_privacy_change(
        db: AsyncSession,
        user_id: int,
        old_is_public: bool,
        new_is_public: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        # Use user_id as the resource_id since favorites belong to a single user
        return await PrivacyAuditLogger.log_privacy_change(
            db=db,
            user_id=user_id,
            action=AuditAction.PRIVACY_CHANGE_FAVORITES,
            resource_type="favorites",
            resource_id=user_id,
            old_value=old_is_public,
            new_value=new_is_public,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    @staticmethod
    async def log_generic_privacy_change(
        db: AsyncSession,
        user_id: int,
        resource_type: str,
        resource_id: int,
        old_value: bool,
        new_value: bool,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLog:
        return await PrivacyAuditLogger.log_privacy_change(
            db=db,
            user_id=user_id,
            action=AuditAction.PRIVACY_CHANGE_GENERIC,
            resource_type=resource_type,
            resource_id=resource_id,
            old_value=old_value,
            new_value=new_value,
            ip_address=ip_address,
            user_agent=user_agent,
        )
