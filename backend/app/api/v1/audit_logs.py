# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Privacy Audit Logs API Endpoints

Endpoints for viewing and filtering privacy setting change audit logs.

Privacy-change endpoints require ADMIN, SUPER_ADMIN, or DIRECTOR role
(surveillance-grade read of patron privacy history; not appropriate for
shelvers/pages/volunteer desk substitutes in the STAFF role).

The /staff-activity endpoint remains accessible to STAFF, ADMIN, and
SUPER_ADMIN as a staff-action audit for circulation/cataloging operations.
"""

import csv
import io

from app.core.logging import get_logger
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...core.pagination import PaginationParams, calculate_total_pages
from ...models.audit_log import AuditAction, AuditLog
from ...models.user import User, UserRole, email_blind_hash
from .auth import get_current_user

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/audit", tags=["audit"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class PrivacyAuditLogResponse(BaseModel):

    id: int
    user_id: int
    user_email: Optional[str] = None
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    old_privacy: Optional[str] = None
    new_privacy: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PrivacyAuditLogsResponse(BaseModel):

    total: int
    page: int
    page_size: int
    total_pages: int
    logs: List[PrivacyAuditLogResponse]


class StaffAuditLogResponse(BaseModel):

    id: int
    admin_id: Optional[int] = None
    admin_email: Optional[str] = None
    action: str
    target_user_id: Optional[int] = None
    target_user_email: Optional[str] = None
    ip_address: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    old_privacy: Optional[str] = None
    new_privacy: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StaffAuditLogsResponse(BaseModel):

    total: int
    page: int
    page_size: int
    total_pages: int
    logs: List[StaffAuditLogResponse]


# =============================================================================
# Helper Functions
# =============================================================================


async def verify_staff_access(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in (UserRole.STAFF, UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR):
        logger.warning(
            "Unauthorized staff audit access attempt",
            extra={
                "user_id": current_user.id,
                "user_role": current_user.role,
                "endpoint": "/api/v1/admin/audit/staff-activity",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )

    return current_user


async def verify_privacy_audit_access(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in (
        UserRole.ADMIN,
        UserRole.SUPER_ADMIN,
        UserRole.DIRECTOR,
    ):
        logger.warning(
            "Unauthorized privacy audit access attempt",
            extra={
                "user_id": current_user.id,
                "user_role": current_user.role,
                "endpoint": "/api/v1/admin/audit/privacy-changes",
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or director access required",
        )

    return current_user


def _extract_details(audit_log: AuditLog) -> tuple:
    details = audit_log.details or {}
    return (
        details.get("resource_type"),
        details.get("resource_id"),
        details.get("old_privacy"),
        details.get("new_privacy"),
    )


def _normalize_date_range(
    start_date: Optional[date],
    end_date: Optional[date],
) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    default_start = now - timedelta(days=30)

    if start_date is None and end_date is None:
        return default_start, now

    if start_date is None:
        start_date = end_date
    if end_date is None:
        end_date = start_date

    start_dt = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end_date, time.max, tzinfo=timezone.utc)
    if start_dt > end_dt:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be on or before end_date",
        )
    return start_dt, end_dt


# =============================================================================
# Endpoints
# =============================================================================


@router.get(
    "/privacy-changes",
    response_model=PrivacyAuditLogsResponse,
    summary="Get privacy change audit logs",
    description="Retrieve privacy setting change audit logs with optional filtering. "
    "Requires staff access.",
)
async def get_privacy_audit_logs(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    user_email: Optional[str] = Query(None, description="Filter by user email"),
    resource_type: Optional[str] = Query(
        None,
        description="Filter by resource type (reading_list, strain_list, favorites, etc)",
    ),
    action: Optional[str] = Query(
        None, description="Filter by audit action (PRIVACY_CHANGE_READING_LIST, etc)"
    ),
    days_back: int = Query(
        30, ge=1, le=365, description="Number of days to look back (default: 30)"
    ),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(verify_privacy_audit_access),
    db: AsyncSession = Depends(get_db),
) -> PrivacyAuditLogsResponse:
    """
    Get privacy change audit logs with optional filtering.

    Filters:
    - user_id: Filter by specific user
    - user_email: Filter by user email (partial match)
    - resource_type: Filter by resource type
    - action: Filter by audit action type
    - days_back: Only show changes from the last N days (default: 30)

    Results are paginated and ordered by most recent first.
    """
    # Build query
    query = select(AuditLog)

    # Filter for privacy-related actions
    privacy_actions = [
        AuditAction.PRIVACY_CHANGE_READING_LIST,
        AuditAction.PRIVACY_CHANGE_FAVORITES,
        AuditAction.PRIVACY_CHANGE_GENERIC,
    ]
    query = query.where(AuditLog.action.in_(privacy_actions))

    # Apply time filter
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    query = query.where(AuditLog.created_at >= cutoff_date)

    # Apply user_id filter
    if user_id is not None:
        query = query.where(AuditLog.target_user_id == user_id)

    # Apply user_email filter (join with User table)
    if user_email is not None:
        from sqlalchemy.orm import joinedload

        query = query.where(AuditLog.target_user).select_entity_from(AuditLog)
        # Email encrypted: exact-match via blind index (substring search dropped).
        query = query.filter(
            AuditLog.target_user.has(
                User.email_hash == email_blind_hash(user_email)  # type: ignore
            )
        )

    # Apply action filter
    if action is not None:
        try:
            audit_action = AuditAction[action]
            query = query.where(AuditLog.action == audit_action)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}",
            ) from None

    # Get total count
    count_query = select(func.count(AuditLog.id)).where(
        AuditLog.action.in_(privacy_actions),
        AuditLog.created_at >= cutoff_date,
    )
    if user_id is not None:
        count_query = count_query.where(AuditLog.target_user_id == user_id)
    if action is not None:
        count_query = count_query.where(AuditLog.action == audit_action)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Order by most recent first
    query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    query = query.offset(pagination.offset).limit(pagination.limit)

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    # Build response
    log_items = []
    for log in logs:
        resource_type, resource_id, old_privacy, new_privacy = _extract_details(log)

        log_items.append(
            PrivacyAuditLogResponse(
                id=log.id,
                user_id=log.target_user_id or 0,
                user_email=log.target_user.email if log.target_user else None,
                action=str(log.action),
                resource_type=resource_type,
                resource_id=resource_id,
                old_privacy=old_privacy,
                new_privacy=new_privacy,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )

    total_pages = calculate_total_pages(total, pagination.page_size)

    return PrivacyAuditLogsResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        logs=log_items,
    )


@router.get(
    "/privacy-changes/user/{user_id}",
    response_model=PrivacyAuditLogsResponse,
    summary="Get privacy changes for a specific user",
    description="Retrieve all privacy setting changes made by a specific user. "
    "Requires staff access.",
)
async def get_user_privacy_changes(
    user_id: int,
    days_back: int = Query(
        90, ge=1, le=365, description="Number of days to look back (default: 90)"
    ),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(verify_privacy_audit_access),
    db: AsyncSession = Depends(get_db),
) -> PrivacyAuditLogsResponse:
    """
    Get all privacy changes for a specific user.

    Useful for reviewing user activity or privacy change history for GDPR requests.
    """
    # Build query
    query = select(AuditLog)

    # Filter for privacy-related actions
    privacy_actions = [
        AuditAction.PRIVACY_CHANGE_READING_LIST,
        AuditAction.PRIVACY_CHANGE_FAVORITES,
        AuditAction.PRIVACY_CHANGE_GENERIC,
    ]
    query = query.where(AuditLog.action.in_(privacy_actions))

    # Filter by user
    query = query.where(AuditLog.target_user_id == user_id)

    # Apply time filter
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    query = query.where(AuditLog.created_at >= cutoff_date)

    # Get total count
    count_result = await db.execute(
        select(func.count(AuditLog.id))
        .where(AuditLog.action.in_(privacy_actions))
        .where(AuditLog.target_user_id == user_id)
        .where(AuditLog.created_at >= cutoff_date)
    )
    total = count_result.scalar() or 0

    # Order by most recent first
    query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    query = query.offset(pagination.offset).limit(pagination.limit)

    # Execute query
    result = await db.execute(query)
    logs = result.scalars().all()

    # Build response
    log_items = []
    for log in logs:
        resource_type, resource_id, old_privacy, new_privacy = _extract_details(log)

        log_items.append(
            PrivacyAuditLogResponse(
                id=log.id,
                user_id=log.target_user_id or 0,
                user_email=log.target_user.email if log.target_user else None,
                action=str(log.action),
                resource_type=resource_type,
                resource_id=resource_id,
                old_privacy=old_privacy,
                new_privacy=new_privacy,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )

    total_pages = calculate_total_pages(total, pagination.page_size)

    return PrivacyAuditLogsResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        logs=log_items,
    )


@router.get(
    "/privacy-changes/by-type/{resource_type}",
    response_model=PrivacyAuditLogsResponse,
    summary="Get privacy changes by resource type",
    description="Retrieve privacy changes for a specific resource type. "
    "Requires staff access.",
)
async def get_privacy_changes_by_type(
    resource_type: str,
    days_back: int = Query(
        30, ge=1, le=365, description="Number of days to look back (default: 30)"
    ),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(verify_privacy_audit_access),
    db: AsyncSession = Depends(get_db),
) -> PrivacyAuditLogsResponse:
    """
    Get privacy changes for a specific resource type.

    Useful for reviewing changes to a specific type of resource.
    """
    # Build query
    query = select(AuditLog)

    # Filter for privacy-related actions
    privacy_actions = [
        AuditAction.PRIVACY_CHANGE_READING_LIST,
        AuditAction.PRIVACY_CHANGE_FAVORITES,
        AuditAction.PRIVACY_CHANGE_GENERIC,
    ]
    query = query.where(AuditLog.action.in_(privacy_actions))

    # Apply time filter
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
    query = query.where(AuditLog.created_at >= cutoff_date)

    # Filter by resource type (in JSON details field)
    query = query.where(AuditLog.details["resource_type"].astext == resource_type)

    # Get total count
    count_result = await db.execute(
        select(func.count()).select_from(query.subquery())
    )
    total = count_result.scalar() or 0

    # Sort by most recent first
    query = query.order_by(desc(AuditLog.created_at))

    # Apply pagination
    paginated_result = await db.execute(query.offset(pagination.offset).limit(pagination.limit))
    paginated_logs = paginated_result.scalars().all()

    # Build response
    log_items = []
    for log in paginated_logs:
        res_type, resource_id, old_privacy, new_privacy = _extract_details(log)

        log_items.append(
            PrivacyAuditLogResponse(
                id=log.id,
                user_id=log.target_user_id or 0,
                user_email=log.target_user.email if log.target_user else None,
                action=str(log.action),
                resource_type=res_type,
                resource_id=resource_id,
                old_privacy=old_privacy,
                new_privacy=new_privacy,
                ip_address=log.ip_address,
                created_at=log.created_at,
            )
        )

    total_pages = calculate_total_pages(total, pagination.page_size)

    return PrivacyAuditLogsResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        logs=log_items,
    )


@router.get(
    "/staff-activity",
    response_model=StaffAuditLogsResponse,
    summary="Get staff activity audit logs",
    description="Retrieve staff activity audit logs with optional filtering. "
    "Requires staff access.",
)
async def get_staff_activity_audit_logs(
    admin_id: Optional[int] = Query(None, description="Filter by staff (admin) user ID"),
    admin_email: Optional[str] = Query(None, description="Filter by staff email"),
    action: Optional[str] = Query(
        None, description="Filter by audit action (CREATE_USER, UPDATE_USER, etc)"
    ),
    start_date: Optional[date] = Query(
        None, description="Start date (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="End date (YYYY-MM-DD)"
    ),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(verify_staff_access),
    db: AsyncSession = Depends(get_db),
) -> StaffAuditLogsResponse:
    """
    Get staff activity audit logs with optional filtering.

    Filters:
    - admin_id: Filter by staff member ID
    - admin_email: Filter by staff email (partial match)
    - action: Filter by audit action type
    - start_date/end_date: Inclusive date range (defaults to last 30 days)
    """
    start_dt, end_dt = _normalize_date_range(start_date, end_date)

    query = select(AuditLog).where(
        AuditLog.created_at >= start_dt,
        AuditLog.created_at <= end_dt,
    ).options(selectinload(AuditLog.admin), selectinload(AuditLog.target_user)
    )

    if admin_id is not None:
        query = query.where(AuditLog.admin_id == admin_id)

    if admin_email is not None:
        # Email encrypted: exact-match via blind index (substring search dropped).
        query = query.where(
            AuditLog.admin.has(User.email_hash == email_blind_hash(admin_email))  # type: ignore
        )

    if action is not None:
        try:
            audit_action = AuditAction[action]
            query = query.where(AuditLog.action == audit_action)
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}",
            ) from None

    count_query = select(func.count(AuditLog.id)).where(
        AuditLog.created_at >= start_dt,
        AuditLog.created_at <= end_dt,
    )
    if admin_id is not None:
        count_query = count_query.where(AuditLog.admin_id == admin_id)
    if admin_email is not None:
        count_query = count_query.where(
            AuditLog.admin.has(User.email_hash == email_blind_hash(admin_email))  # type: ignore
        )
    if action is not None:
        count_query = count_query.where(AuditLog.action == audit_action)

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(desc(AuditLog.created_at))
    query = query.offset(pagination.offset).limit(pagination.limit)

    result = await db.execute(query)
    logs = result.scalars().all()

    log_items = []
    for log in logs:
        res_type, resource_id, old_privacy, new_privacy = _extract_details(log)
        log_items.append(
            StaffAuditLogResponse(
                id=log.id,
                admin_id=log.admin_id,
                admin_email=log.admin.email if log.admin else None,
                action=str(log.action),
                target_user_id=log.target_user_id,
                target_user_email=log.target_user.email if log.target_user else None,
                ip_address=log.ip_address,
                resource_type=res_type,
                resource_id=resource_id,
                old_privacy=old_privacy,
                new_privacy=new_privacy,
                user_agent=log.user_agent,
                created_at=log.created_at,
            )
        )

    total_pages = calculate_total_pages(total, pagination.page_size)

    return StaffAuditLogsResponse(
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=total_pages,
        logs=log_items,
    )


@router.get(
    "/staff-activity/export",
    summary="Export staff activity audit logs as CSV",
    description="Export staff activity audit logs (max 5000 rows). Requires staff access.",
)
async def export_staff_activity_audit_logs(
    admin_id: Optional[int] = Query(None),
    admin_email: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
    current_user: User = Depends(verify_staff_access),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Export staff activity audit logs as CSV (newest first, max 5000 rows)."""
    start_dt, end_dt = _normalize_date_range(start_date, end_date)

    query = select(AuditLog).where(
        AuditLog.created_at >= start_dt,
        AuditLog.created_at <= end_dt,
    ).options(selectinload(AuditLog.admin), selectinload(AuditLog.target_user))

    if admin_id is not None:
        query = query.where(AuditLog.admin_id == admin_id)
    if admin_email is not None:
        query = query.where(
            AuditLog.admin.has(User.email_hash == email_blind_hash(admin_email))  # type: ignore
        )
    if action is not None:
        try:
            audit_action = AuditAction[action]
        except KeyError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid action: {action}",
            ) from None
        query = query.where(AuditLog.action == audit_action)

    query = query.order_by(desc(AuditLog.created_at)).limit(5000)
    result = await db.execute(query)
    logs = result.scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Time", "Staff Member", "Staff ID", "Action", "Target User",
        "Target User ID", "IP Address", "Resource Type", "Resource ID",
        "Old Privacy", "New Privacy", "User Agent",
    ])
    for log in logs:
        res_type, resource_id, old_privacy, new_privacy = _extract_details(log)
        writer.writerow([
            log.created_at.isoformat(),
            log.admin.email if log.admin else "",
            log.admin_id if log.admin_id is not None else "",
            str(log.action),
            log.target_user.email if log.target_user else "",
            log.target_user_id if log.target_user_id is not None else "",
            log.ip_address or "",
            res_type or "",
            resource_id if resource_id is not None else "",
            old_privacy or "",
            new_privacy or "",
            log.user_agent or "",
        ])

    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=staff-activity-audit.csv"},
    )
