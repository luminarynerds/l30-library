# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
User Management API Endpoints
Includes current user profile and admin user management
"""

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy import and_, extract, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.database import get_db
from ...core.rate_limit import client_ip
from ...core.shortcuts import get_or_404
from ...core.security import (
    generate_library_card,
    hash_password,
    create_reset_token,
    hash_reset_token,
)
from ...models.audit_log import AuditAction, AuditLog
from ...models.user import User, UserRole, name_search_clause, email_match_clause, email_blind_hash
from ...schemas.user import UserResponse, UserAdminResponse, UserListResponse

from .auth import get_current_user
from .dependencies import require_admin
from ...services.reports.cache_invalidator import invalidate_patron_reports

router = APIRouter(prefix="/users", tags=["users"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class UserCreateAdmin(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    role: UserRole
    phone: str | None = None
    address: str | None = None
    is_active: bool = True


class UserUpdateAdmin(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    address: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserListResponse(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    limit: int


class BulkUserIds(BaseModel):
    user_ids: List[int]

    @field_validator("user_ids")
    @classmethod
    def validate_user_ids(cls, v: List[int]) -> List[int]:
        if not v:
            raise ValueError("user_ids cannot be empty")
        if len(v) > 100:
            raise ValueError("Cannot process more than 100 users at once")
        return v


class BulkActionResponse(BaseModel):
    success: bool
    processed: int
    skipped: int
    message: str


class UserStatsResponse(BaseModel):
    total_users: int
    active_users: int
    new_this_month: int
    locked_accounts: int


class PasswordResetResponse(BaseModel):
    message: str
    reset_link: str


# =============================================================================
# Audit Log Schemas
# =============================================================================


class AuditLogUserResponse(BaseModel):
    id: int
    email: str
    first_name: str | None = None
    last_name: str | None = None

    class Config:
        from_attributes = True


class AuditLogResponse(BaseModel):
    id: int
    admin_id: int | None
    target_user_id: int | None
    action: str
    details: dict | None
    ip_address: str | None
    created_at: datetime
    admin: AuditLogUserResponse | None = None
    target_user: AuditLogUserResponse | None = None

    class Config:
        from_attributes = True


class AuditLogListResponse(BaseModel):
    logs: List[AuditLogResponse]
    total: int
    page: int
    limit: int


# =============================================================================
# Helper Functions
# =============================================================================


def get_client_ip(request: Request) -> str | None:
    # Delegate to the shared helper (CF-Connecting-IP -> X-Real-IP -> peer).
    # The previous body trusted the leftmost X-Forwarded-For entry first, which
    # nginx appends to (proxy_add_x_forwarded_for) and is client-spoofable.
    return client_ip(request)


async def create_audit_log(
    db: AsyncSession,
    admin_id: int,
    action: AuditAction,
    target_user_id: int | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    audit_log = AuditLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_log)
    # Don't commit here - let the caller handle the transaction
    return audit_log


def get_changed_fields(old_values: dict, new_values: dict) -> dict:
    changes = {}
    for key, new_value in new_values.items():
        old_value = old_values.get(key)
        if old_value != new_value:
            changes[key] = {"old": old_value, "new": new_value}
    return changes


# =============================================================================
# Current User Endpoint
# =============================================================================


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Get current authenticated user profile."""
    return current_user


@router.get("/stats", response_model=UserStatsResponse)
async def get_user_stats(
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user statistics for admin dashboard.

    Returns:
        - total_users: Total count of all users
        - active_users: Count of users where is_active is True
        - new_this_month: Count of users created in the current month
        - locked_accounts: Count of users with active locks (locked_until > now)
    """
    now = datetime.now(timezone.utc)
    current_month = now.month
    current_year = now.year

    # Total users
    total_result = await db.execute(select(func.count(User.id)))
    total_users = total_result.scalar_one()

    # Active users (is_active = True)
    active_result = await db.execute(select(func.count(User.id)).where(User.is_active == True))
    active_users = active_result.scalar_one()

    # New users this month
    new_this_month_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                extract("month", User.created_at) == current_month,
                extract("year", User.created_at) == current_year,
            )
        )
    )
    new_this_month = new_this_month_result.scalar_one()

    # Locked accounts (locked_until is set and in the future)
    locked_result = await db.execute(
        select(func.count(User.id)).where(
            and_(
                User.locked_until != None,
                User.locked_until > now,
            )
        )
    )
    locked_accounts = locked_result.scalar_one()

    return UserStatsResponse(
        total_users=total_users,
        active_users=active_users,
        new_this_month=new_this_month,
        locked_accounts=locked_accounts,
    )


@router.get("/export")
async def export_users_csv(
    role: UserRole | None = None,
    status: str | None = Query(None, description="Filter by status: active, inactive, or locked"),
    search: str | None = None,
    user_ids: str | None = Query(None, description="Comma-separated list of user IDs to export"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Export users to CSV file.

    Accepts the same filter parameters as the list endpoint (search, role, status).
    Additionally, can filter by specific user_ids (comma-separated).
    Returns all matching users (no pagination) as CSV.

    CSV columns: ID, Email, First Name, Last Name, Role, Status, Locked, Created Date
    """
    query = select(User)

    # Filter by specific user IDs if provided
    if user_ids:
        try:
            ids = [int(id.strip()) for id in user_ids.split(",") if id.strip()]
            if ids:
                query = query.where(User.id.in_(ids))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_ids format") from None

    if role:
        query = query.where(User.role == role)

    # Status filtering: active, inactive, or locked
    now = datetime.now(timezone.utc)
    if status:
        if status.lower() == "active":
            query = query.where(User.is_active == True).where(
                (User.locked_until == None) | (User.locked_until < now)
            )
        elif status.lower() == "inactive":
            query = query.where(User.is_active == False)
        elif status.lower() == "locked":
            query = query.where(User.locked_until != None).where(User.locked_until > now)

    if search:
        # SECURITY: Escape SQL ILIKE special characters to prevent injection
        search_escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_filter = f"%{search_escaped}%"
        # email + names encrypted: exact email-hash + name blind index, not substring.
        _name_clause = name_search_clause(search)
        _email_clause = email_match_clause(search)
        query = query.where(
            (User.library_card.ilike(search_filter))
            | (_email_clause if _email_clause is not None else false())
            | (_name_clause if _name_clause is not None else false())
        )

    query = query.order_by(User.created_at.desc())

    # Generate filename with current date
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"users-export-{today}.csv"

    async def generate_csv():
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "ID",
                "Email",
                "First Name",
                "Last Name",
                "Role",
                "Status",
                "Locked",
                "Created Date",
                "Last Login",
            ]
        )
        yield output.getvalue()

        batch_size = 1000
        offset = 0
        while True:
            batch_query = query.offset(offset).limit(batch_size)
            result = await db.execute(batch_query)
            users = result.scalars().all()
            if not users:
                break

            output = io.StringIO()
            writer = csv.writer(output)
            for user in users:
                user_status = "Inactive" if not user.is_active else "Active"
                is_locked = user.locked_until is not None and user.locked_until > now
                locked_str = "Yes" if is_locked else "No"
                created_date = user.created_at.strftime("%Y-%m-%d") if user.created_at else ""
                last_login_date = (
                    user.last_login.strftime("%Y-%m-%d %H:%M:%S") if user.last_login else "Never"
                )
                writer.writerow(
                    [
                        user.id,
                        user.email,
                        user.first_name or "",
                        user.last_name or "",
                        str(user.role) if user.role else "",
                        user_status,
                        locked_str,
                        created_date,
                        last_login_date,
                    ]
                )
            yield output.getvalue()

            if len(users) < batch_size:
                break
            offset += batch_size

    return StreamingResponse(
        generate_csv(),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/csv; charset=utf-8",
        },
    )


# =============================================================================
# Admin User Management Endpoints
# =============================================================================


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    role: UserRole | None = None,
    status: str | None = Query(None, description="Filter by status: active, inactive, or locked"),
    search: str | None = None,
    sort_by: str | None = Query(
        None, description="Field to sort by: name, email, role, created_at"
    ),
    sort_order: str | None = Query(None, description="Sort order: asc or desc"),
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """List all users (paginated) with optional filtering and sorting"""
    offset = (page - 1) * limit
    query = select(User)

    if role:
        query = query.where(User.role == role)

    # Status filtering: active, inactive, or locked
    if status:
        from datetime import datetime, timezone

        if status.lower() == "active":
            # Active users: is_active=True AND not locked (locked_until is None or in the past)
            query = query.where(User.is_active == True).where(
                (User.locked_until == None) | (User.locked_until < datetime.now(timezone.utc))
            )
        elif status.lower() == "inactive":
            # Inactive users: is_active=False
            query = query.where(User.is_active == False)
        elif status.lower() == "locked":
            # Locked users: locked_until is set and in the future
            query = query.where(User.locked_until != None).where(
                User.locked_until > datetime.now(timezone.utc)
            )

    if search:
        # SECURITY: Escape SQL ILIKE special characters to prevent injection
        # Replace % and _ with escaped versions to treat them as literals
        search_escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        search_filter = f"%{search_escaped}%"
        # email + names encrypted: exact email-hash + name blind index, not substring.
        _name_clause = name_search_clause(search)
        _email_clause = email_match_clause(search)
        query = query.where(
            (User.library_card.ilike(search_filter))
            | (_email_clause if _email_clause is not None else false())
            | (_name_clause if _name_clause is not None else false())
        )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # Apply sorting based on sort_by and sort_order parameters
    valid_sort_fields = {
        "name": User.first_name,  # Sort by first_name for "name"
        "email": User.email,
        "role": User.role,
        "created_at": User.created_at,
        "last_login": User.last_login,
    }

    sort_field = valid_sort_fields.get(sort_by, User.created_at)

    if sort_order == "asc":
        query = query.order_by(sort_field.asc())
    else:
        # Default to descending order
        query = query.order_by(sort_field.desc())

    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(users=users, total=total, page=page, limit=limit)


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateAdmin,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new user with any role"""
    # Prevent role escalation: only SUPER_ADMIN can create SUPER_ADMIN users
    if user_data.role == UserRole.SUPER_ADMIN:
        if admin_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can create SUPER_ADMIN users",
            )

    existing = await db.execute(
        select(User).where(User.email_hash == email_blind_hash(user_data.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    library_card = generate_library_card() if user_data.role == UserRole.PATRON else None

    user = User(
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        role=user_data.role,
        address=user_data.address,
        library_card=library_card,
        is_active=user_data.is_active,
        email_verified=True,
        home_library_system_id=admin_user.home_library_system_id,
    )

    if user_data.phone:
        user.set_phone(user_data.phone)
    db.add(user)
    await db.flush()  # Flush to get the user ID before audit log

    # Create audit log entry
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.CREATE_USER,
        target_user_id=user.id,
        details={"email": user.email, "role": user.role},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    await db.refresh(user)

    # Invalidate patron report cache after new user creation
    await invalidate_patron_reports()

    return user


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get user by ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserUpdateAdmin,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update user information"""
    user = await get_or_404(db, User, user_id, "User not found")

    update_data = user_update.model_dump(exclude_unset=True)

    # Prevent role escalation: only SUPER_ADMIN can create/promote to SUPER_ADMIN
    if "role" in update_data and update_data["role"] == UserRole.SUPER_ADMIN:
        if admin_user.role != UserRole.SUPER_ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only SUPER_ADMIN can promote users to SUPER_ADMIN role",
            )

    # Capture old values before update for audit logging
    old_values = {}
    for field in update_data.keys():
        old_val = getattr(user, field)
        # Convert enum to string for comparison
        old_values[field] = old_val.value if hasattr(old_val, "value") else old_val

    for field, value in update_data.items():
        setattr(user, field, value)

    # Get changed fields for audit log
    new_values = {}
    for field in update_data.keys():
        new_val = getattr(user, field)
        new_values[field] = new_val.value if hasattr(new_val, "value") else new_val
    changed_fields = get_changed_fields(old_values, new_values)

    # Create audit log entry
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.UPDATE_USER,
        target_user_id=user.id,
        details={"changes": changed_fields} if changed_fields else None,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate user account"""
    user = await get_or_404(db, User, user_id, "User not found")

    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate your own account"
        )

    user.is_active = False

    # Create audit log entry
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.DEACTIVATE_USER,
        target_user_id=user.id,
        details={"email": user.email},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    return {"message": f"User {user.email} deactivated successfully"}


@router.post("/{user_id}/lock", response_model=UserAdminResponse)
async def lock_user(
    user_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lock a user account to prevent login"""
    from datetime import datetime, timedelta, timezone

    user = await get_or_404(db, User, user_id, "User not found")

    if user.id == admin_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot lock your own account"
        )

    # Lock the account indefinitely (far future date)
    user.locked_until = datetime.now(timezone.utc) + timedelta(days=36500)

    # Create audit log entry
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.LOCK_USER,
        target_user_id=user.id,
        details={"email": user.email},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/unlock", response_model=UserAdminResponse)
async def unlock_user(
    user_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Unlock a user account to allow login"""
    user = await get_or_404(db, User, user_id, "User not found")

    # Clear the lock
    user.locked_until = None
    user.failed_login_attempts = 0

    # Create audit log entry
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.UNLOCK_USER,
        target_user_id=user.id,
        details={"email": user.email},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()
    await db.refresh(user)
    return user


@router.post("/{user_id}/reset-password", response_model=PasswordResetResponse)
async def admin_reset_password(
    user_id: int,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Admin-initiated password reset for a user.

    Generates a secure reset token and stores it with the user's account.
    The token is valid for 24 hours.

    In production, this would send an email to the user. For development,
    the reset link is returned in the response.

    Args:
        user_id: ID of the user to reset password for

    Returns:
        Message confirming the reset was initiated and the reset link

    Raises:
        404: If user not found
        400: If user account is locked
    """
    user = await get_or_404(db, User, user_id, "User not found")

    # Check if account is locked
    if user.is_locked():
        raise HTTPException(
            status_code=400,
            detail="Cannot send password reset to a locked account. Please unlock the account first.",
        )

    # Generate a secure reset token
    reset_token = create_reset_token()

    # Store hashed token in database for security (prevents token theft if DB is compromised)
    user.reset_token = hash_reset_token(reset_token)
    # 24 hours expiry for admin-initiated resets
    user.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    # Create audit log entry
    await create_audit_log(
        db=db,
        admin_id=admin_user.id,
        action=AuditAction.RESET_PASSWORD,
        target_user_id=user.id,
        details={"email": user.email},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    await db.commit()

    # In production, this would send an email to the user
    # For development, we return the reset link directly
    # The frontend base URL would come from settings in production
    reset_link = f"/reset-password?token={reset_token}"

    return PasswordResetResponse(
        message=f"Password reset initiated for {user.email}. The user has 24 hours to reset their password.",
        reset_link=reset_link,
    )


# =============================================================================
# Bulk Action Endpoints
# =============================================================================


@router.post("/bulk-lock", response_model=BulkActionResponse)
async def bulk_lock_users(
    data: BulkUserIds,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Lock multiple user accounts at once"""
    # Remove admin's own ID from the list to prevent self-lock
    user_ids = [uid for uid in data.user_ids if uid != admin_user.id]
    skipped = len(data.user_ids) - len(user_ids)

    if not user_ids:
        return BulkActionResponse(
            success=True,
            processed=0,
            skipped=skipped,
            message="No users to lock (cannot lock your own account)",
        )

    # Fetch users to lock
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()

    # Lock all found users
    lock_until = datetime.now(timezone.utc) + timedelta(days=36500)
    processed = 0
    processed_ids = []
    for user in users:
        user.locked_until = lock_until
        processed += 1
        processed_ids.append(user.id)

    # Create audit log entry
    if processed > 0:
        await create_audit_log(
            db=db,
            admin_id=admin_user.id,
            action=AuditAction.BULK_LOCK,
            target_user_id=None,
            details={"user_ids": processed_ids, "count": processed},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )

    await db.commit()

    return BulkActionResponse(
        success=True,
        processed=processed,
        skipped=skipped + (len(user_ids) - processed),
        message=f"Successfully locked {processed} user(s)",
    )


@router.post("/bulk-unlock", response_model=BulkActionResponse)
async def bulk_unlock_users(
    data: BulkUserIds,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Unlock multiple user accounts at once"""
    user_ids = data.user_ids

    # Fetch users to unlock
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()

    # Unlock all found users
    processed = 0
    processed_ids = []
    for user in users:
        user.locked_until = None
        user.failed_login_attempts = 0
        processed += 1
        processed_ids.append(user.id)

    # Create audit log entry
    if processed > 0:
        await create_audit_log(
            db=db,
            admin_id=admin_user.id,
            action=AuditAction.BULK_UNLOCK,
            target_user_id=None,
            details={"user_ids": processed_ids, "count": processed},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )

    await db.commit()

    return BulkActionResponse(
        success=True,
        processed=processed,
        skipped=len(user_ids) - processed,
        message=f"Successfully unlocked {processed} user(s)",
    )


@router.post("/bulk-activate", response_model=BulkActionResponse)
async def bulk_activate_users(
    data: BulkUserIds,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Activate multiple user accounts at once"""
    user_ids = data.user_ids

    # Fetch users to activate
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()

    # Activate all found users
    processed = 0
    processed_ids = []
    for user in users:
        user.is_active = True
        processed += 1
        processed_ids.append(user.id)

    # Create audit log entry
    if processed > 0:
        await create_audit_log(
            db=db,
            admin_id=admin_user.id,
            action=AuditAction.BULK_ACTIVATE,
            target_user_id=None,
            details={"user_ids": processed_ids, "count": processed},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )

    await db.commit()

    return BulkActionResponse(
        success=True,
        processed=processed,
        skipped=len(user_ids) - processed,
        message=f"Successfully activated {processed} user(s)",
    )


@router.post("/bulk-deactivate", response_model=BulkActionResponse)
async def bulk_deactivate_users(
    data: BulkUserIds,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deactivate multiple user accounts at once"""
    # Remove admin's own ID from the list to prevent self-deactivation
    user_ids = [uid for uid in data.user_ids if uid != admin_user.id]
    skipped = len(data.user_ids) - len(user_ids)

    if not user_ids:
        return BulkActionResponse(
            success=True,
            processed=0,
            skipped=skipped,
            message="No users to deactivate (cannot deactivate your own account)",
        )

    # Fetch users to deactivate
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()

    # Deactivate all found users
    processed = 0
    processed_ids = []
    for user in users:
        user.is_active = False
        processed += 1
        processed_ids.append(user.id)

    # Create audit log entry
    if processed > 0:
        await create_audit_log(
            db=db,
            admin_id=admin_user.id,
            action=AuditAction.BULK_DEACTIVATE,
            target_user_id=None,
            details={"user_ids": processed_ids, "count": processed},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )

    await db.commit()

    return BulkActionResponse(
        success=True,
        processed=processed,
        skipped=skipped + (len(user_ids) - processed),
        message=f"Successfully deactivated {processed} user(s)",
    )


@router.post("/bulk-delete", response_model=BulkActionResponse)
async def bulk_delete_users(
    data: BulkUserIds,
    request: Request,
    admin_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete multiple user accounts at once (soft delete by deactivation)"""
    # Remove admin's own ID from the list to prevent self-deletion
    user_ids = [uid for uid in data.user_ids if uid != admin_user.id]
    skipped = len(data.user_ids) - len(user_ids)

    if not user_ids:
        return BulkActionResponse(
            success=True,
            processed=0,
            skipped=skipped,
            message="No users to delete (cannot delete your own account)",
        )

    # Fetch users to delete
    result = await db.execute(select(User).where(User.id.in_(user_ids)))
    users = result.scalars().all()

    # Soft delete all found users (deactivate)
    processed = 0
    processed_ids = []
    for user in users:
        user.is_active = False
        processed += 1
        processed_ids.append(user.id)

    # Create audit log entry
    if processed > 0:
        await create_audit_log(
            db=db,
            admin_id=admin_user.id,
            action=AuditAction.BULK_DELETE,
            target_user_id=None,
            details={"user_ids": processed_ids, "count": processed},
            ip_address=get_client_ip(request),
            user_agent=request.headers.get("User-Agent"),
        )

    await db.commit()

    return BulkActionResponse(
        success=True,
        processed=processed,
        skipped=skipped + (len(user_ids) - processed),
        message=f"Successfully deleted {processed} user(s)",
    )


@router.get("/bulk-activate")
async def get_bulk_activate_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get status of /bulk-activate operation."""
    return {"status": "pending", "processed": 0, "total": 0}


@router.get("/bulk-deactivate")
async def get_bulk_deactivate_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get status of /bulk-deactivate operation."""
    return {"status": "pending", "processed": 0, "total": 0}


@router.get("/bulk-delete")
async def get_bulk_delete_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get status of /bulk-delete operation."""
    return {"status": "pending", "processed": 0, "total": 0}


@router.get("/bulk-lock")
async def get_bulk_lock_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get status of /bulk-lock operation."""
    return {"status": "pending", "processed": 0, "total": 0}


@router.get("/bulk-unlock")
async def get_bulk_unlock_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Get status of /bulk-unlock operation."""
    return {"status": "pending", "processed": 0, "total": 0}
