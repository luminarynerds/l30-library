# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
General Audit Endpoints - Admin Dashboard

Public endpoints for retrieving audit logs visible to admin dashboard.
Complements admin/audit endpoints with a more general-purpose structure.

All endpoints require ADMIN or SUPER_ADMIN role.
"""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.pagination import PaginationParams, calculate_total_pages
from ...models.audit_log import AuditAction, AuditLog
from ...models.user import User, UserRole
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class AdminAuditLogResponse(BaseModel):

    id: int
    admin_id: Optional[int] = None
    admin_email: Optional[str] = None
    action: str
    target_user_id: Optional[int] = None
    target_user_email: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminAuditLogsResponse(BaseModel):

    total: int
    page: int
    page_size: int
    total_pages: int
    logs: List[AdminAuditLogResponse]


# =============================================================================
# Authorization
# =============================================================================


async def verify_admin_access(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        logger.warning(
            "Unauthorized admin audit access attempt",
            extra={
                "user_id": current_user.id,
                "user_role": current_user.role,
                "endpoint": "/api/v1/audit/admin",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    return current_user


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/admin",
    response_model=AdminAuditLogsResponse,
    summary="Get admin-visible audit logs",
    description="Retrieve comprehensive audit logs for admin dashboard. "
    "Includes all audit actions across the system. Requires admin access.",
)
async def get_admin_audit_logs(
    page: int = Query(1, ge=1, description="Page number (default: 1)"),
    page_size: int = Query(
        10, ge=1, le=100, description="Items per page (default: 10, max: 100)"
    ),
    days_back: int = Query(
        1, ge=1, le=365, description="Number of days to look back (default: 1)"
    ),
    action: Optional[str] = Query(
        None, description="Filter by audit action type"
    ),
    admin_id: Optional[int] = Query(None, description="Filter by admin user ID"),
    target_user_id: Optional[int] = Query(
        None, description="Filter by target user ID"
    ),
    current_user: User = Depends(verify_admin_access),
    db: AsyncSession = Depends(get_db),
) -> AdminAuditLogsResponse:
    """
    Get comprehensive audit logs visible to admins.

    Filters:
    - action: Filter by specific audit action (e.g., CREATE_USER, DELETE_USER)
    - admin_id: Filter by the admin who performed the action
    - target_user_id: Filter by the user affected by the action
    - days_back: Only show actions from the last N days (default: 1, max: 365)

    Results are paginated and ordered by most recent first.
    """
    # Validate pagination
    if page < 1:
        page = 1
    if page_size < 1:
        page_size = 10
    if page_size > 100:
        page_size = 100

    # Calculate offset
    offset = (page - 1) * page_size

    # Apply time filter
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)

    # Build base query
    query = select(AuditLog).where(AuditLog.created_at >= cutoff_date)

    # Apply action filter
    if action is not None:
        try:
            audit_action = AuditAction[action]
            query = query.where(AuditLog.action == audit_action)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}. Must be a valid AuditAction enum value.",
            ) from None

    # Apply admin_id filter
    if admin_id is not None:
        query = query.where(AuditLog.admin_id == admin_id)

    # Apply target_user_id filter
    if target_user_id is not None:
        query = query.where(AuditLog.target_user_id == target_user_id)

    # Get total count
    count_query = select(func.count(AuditLog.id)).where(AuditLog.created_at >= cutoff_date)
    if action is not None:
        count_query = count_query.where(AuditLog.action == audit_action)
    if admin_id is not None:
        count_query = count_query.where(AuditLog.admin_id == admin_id)
    if target_user_id is not None:
        count_query = count_query.where(AuditLog.target_user_id == target_user_id)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by most recent first
    query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    query = query.offset(offset).limit(page_size)

    # Eagerly load admin and target_user to prevent N+1 lazy loads
    query = query.options(selectinload(AuditLog.admin), selectinload(AuditLog.target_user))

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    # Extract resource_type and resource_id from details JSON
    def _extract_details(audit_log: AuditLog) -> tuple:
        details = audit_log.details or {}
        return (
            details.get("resource_type"),
            details.get("resource_id"),
        )

    # Build response
    log_items = []
    for log in logs:
        resource_type, resource_id = _extract_details(log)

        log_items.append(
            AdminAuditLogResponse(
                id=log.id,
                admin_id=log.admin_id,
                admin_email=log.admin.email if log.admin else None,
                action=str(log.action),
                target_user_id=log.target_user_id,
                target_user_email=log.target_user.email if log.target_user else None,
                resource_type=resource_type,
                resource_id=resource_id,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )

    total_pages = calculate_total_pages(total, page_size)

    return AdminAuditLogsResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        logs=log_items,
    )
