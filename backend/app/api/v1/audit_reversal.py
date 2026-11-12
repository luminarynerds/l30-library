# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Audit Reversal API Endpoints

Provides endpoints for checking and performing audit trail reversals.
Requires ADMIN or SUPER_ADMIN role (not STAFF).
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User, UserRole
from ...services.unified_reversal_service import (
    UnifiedReversalService,
    REVERSIBLE_ACTIONS,
    NON_REVERSIBLE_ACTIONS,
)
from .auth import get_current_user
from .users import get_client_ip
from .dependencies import require_admin
from fastapi import Depends

router = APIRouter(prefix="/admin/audit", tags=["audit-reversal"])


# =============================================================================
# Pydantic Schemas
# =============================================================================


class ReversibilityCheckResponse(BaseModel):
    audit_log_id: int
    is_reversible: bool
    action: str
    reason: str
    details: Optional[Dict[str, Any]] = None
    warnings: List[str] = []


class ReversalResponse(BaseModel):
    success: bool
    audit_log_id: int
    action: str
    reversal_audit_log_id: Optional[int] = None
    reverted_changes: Optional[Dict[str, Any]] = None
    warnings: List[str] = []


class ReversibleActionsResponse(BaseModel):
    reversible: List[str]
    non_reversible: List[str]


# =============================================================================
# Authorization Dependency
# =============================================================================


async def require_admin_for_reversal(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Super Admin access required for audit reversal operations",
        )
    return current_user


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/reversible-actions", response_model=ReversibleActionsResponse)
async def get_reversible_action_types(
    admin_user: User = Depends(require_admin_for_reversal),
) -> ReversibleActionsResponse:
    """
    Get the list of action types that can and cannot be reversed.

    This endpoint provides documentation about which audit action types
    support reversal and which do not.

    Returns:
        ReversibleActionsResponse with lists of reversible and non-reversible actions

    Raises:
        403: If user doesn't have admin privileges
    """
    return ReversibleActionsResponse(
        reversible=[action.value for action in REVERSIBLE_ACTIONS],
        non_reversible=[action.value for action in NON_REVERSIBLE_ACTIONS],
    )


@router.get("/{audit_log_id}/reversible", response_model=ReversibilityCheckResponse)
async def check_if_reversible(
    audit_log_id: int,
    admin_user: User = Depends(require_admin_for_reversal),
    db: AsyncSession = Depends(get_db),
) -> ReversibilityCheckResponse:
    """
    Check if a specific audit log entry can be reversed.

    This endpoint analyzes the audit log entry and determines:
    - Whether the action type is reversible
    - Whether the necessary data for reversal is available
    - Whether the target entities still exist
    - Whether the action has already been reverted

    Args:
        audit_log_id: ID of the audit log entry to check

    Returns:
        ReversibilityCheckResponse with details about reversibility

    Raises:
        403: If user doesn't have admin privileges
        404: If audit log entry not found
    """
    service = UnifiedReversalService(db)

    # Check if the audit log exists
    audit_log = await service.get_audit_log(audit_log_id)
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )

    # Check if already reverted (check details for reverted flag)
    details = audit_log.details or {}
    if details.get("reverted", False):
        return ReversibilityCheckResponse(
            audit_log_id=audit_log_id,
            is_reversible=False,
            action=str(audit_log.action),
            reason="This action has already been reverted",
            details={"reverted_at": details.get("reverted_at")},
            warnings=[],
        )

    result = await service.check_can_revert(audit_log_id)

    return ReversibilityCheckResponse(
        audit_log_id=audit_log_id,
        is_reversible=result.can_revert,
        action=str(audit_log.action),
        reason=result.reason,
        details=result.details,
        warnings=result.warnings,
    )


@router.get("/{audit_log_id}/can-revert", response_model=ReversibilityCheckResponse)
async def check_can_revert(
    audit_log_id: int,
    admin_user: User = Depends(require_admin_for_reversal),
    db: AsyncSession = Depends(get_db),
) -> ReversibilityCheckResponse:
    """
    Alias for /reversible endpoint. Check if a specific audit log entry can be reversed.

    Args:
        audit_log_id: ID of the audit log entry to check

    Returns:
        ReversibilityCheckResponse with details about reversibility

    Raises:
        403: If user doesn't have admin privileges
        404: If audit log entry not found
    """
    return await check_if_reversible(audit_log_id, admin_user, db)


@router.post("/{audit_log_id}/revert", response_model=ReversalResponse)
async def revert_audit_action(
    audit_log_id: int,
    request: Request,
    admin_user: User = Depends(require_admin_for_reversal),
    db: AsyncSession = Depends(get_db),
    _guard: User = Depends(require_admin),
) -> ReversalResponse:
    """
    Perform the reversal of an audit log entry.

    This endpoint will:
    1. Verify the action can be reversed
    2. Restore the previous state of the affected entity
    3. Create a new audit log entry documenting the reversal
    4. Mark the original audit log as reverted

    Not all actions can be reversed. Non-reversible actions include:
    - CREATE_USER: Cannot un-create a user
    - DELETE_USER / GDPR_DELETION_COMPLETED: Data may be permanently deleted
    - RESET_PASSWORD: Cannot restore old password
    - Bulk operations: Too complex to reverse atomically
    - Already reverted actions: Cannot double-revert

    Reversible actions include:
    - UPDATE_USER: Restores old field values
    - LOCK_USER: Unlocks the user
    - UNLOCK_USER: Re-locks the user
    - PRIVACY_CHANGE_*: Restores old privacy setting
    - PATRON_MERGE: Best-effort reversal with warnings

    Args:
        audit_log_id: ID of the audit log entry to revert

    Returns:
        ReversalResponse with details about the reversal

    Raises:
        400: If the action cannot be reversed
        403: If user doesn't have admin privileges
        404: If audit log entry not found
    """
    service = UnifiedReversalService(db)

    # First check if the audit log exists
    audit_log = await service.get_audit_log(audit_log_id)
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )

    # Check if already reverted
    details = audit_log.details or {}
    if details.get("reverted", False):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This action has already been reverted and cannot be reverted again",
        )

    # Check if it can be reverted
    can_revert_result = await service.check_can_revert(audit_log_id)
    if not can_revert_result.can_revert:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=can_revert_result.reason,
        )

    # Perform the reversal
    result = await service.revert(
        audit_log_id=audit_log_id,
        admin_id=admin_user.id,
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    # Mark the original audit log as reverted
    from datetime import datetime, timezone
    if audit_log.details is None:
        audit_log.details = {}
    audit_log.details["reverted"] = True
    audit_log.details["reverted_at"] = datetime.now(timezone.utc).isoformat()
    audit_log.details["reverted_by"] = admin_user.id
    audit_log.details["reversal_audit_log_id"] = result.audit_log_id

    # Commit the transaction
    await db.commit()

    return ReversalResponse(
        success=result.success,
        audit_log_id=audit_log_id,
        action=str(audit_log.action),
        reversal_audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


@router.get("/{audit_log_id}/reversal-preview", response_model=Dict[str, Any])
async def preview_reversal(
    audit_log_id: int,
    admin_user: User = Depends(require_admin_for_reversal),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Preview what a reversal would do without actually performing it.

    This is useful for administrators to understand the impact of a
    reversal before committing to it.

    Args:
        audit_log_id: ID of the audit log entry to preview

    Returns:
        Dictionary with preview details including:
        - can_revert: Whether the action can be reverted
        - action_type: The type of action
        - target_user_id: The affected user (if applicable)
        - changes_to_revert: What would be changed
        - warnings: Any warnings about the reversal

    Raises:
        403: If user doesn't have admin privileges
        404: If audit log entry not found
    """
    service = UnifiedReversalService(db)

    audit_log = await service.get_audit_log(audit_log_id)
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Audit log entry not found",
        )

    # Check if already reverted
    details = audit_log.details or {}
    if details.get("reverted", False):
        return {
            "audit_log_id": audit_log_id,
            "action_type": str(audit_log.action),
            "target_user_id": audit_log.target_user_id,
            "admin_id": audit_log.admin_id,
            "created_at": audit_log.created_at.isoformat() if audit_log.created_at else None,
            "can_revert": False,
            "reason": "This action has already been reverted",
            "details": {"reverted_at": details.get("reverted_at")},
            "warnings": [],
            "original_details": audit_log.details,
        }

    can_revert_result = await service.check_can_revert(audit_log_id)

    # Build preview response
    preview = {
        "audit_log_id": audit_log_id,
        "action_type": str(audit_log.action),
        "target_user_id": audit_log.target_user_id,
        "admin_id": audit_log.admin_id,
        "created_at": audit_log.created_at.isoformat() if audit_log.created_at else None,
        "can_revert": can_revert_result.can_revert,
        "reason": can_revert_result.reason,
        "details": can_revert_result.details,
        "warnings": can_revert_result.warnings,
        "original_details": audit_log.details,
    }

    # If it can be reverted, add more specific preview information
    if can_revert_result.can_revert:
        if str(audit_log.action) == "UPDATE_USER":
            changes = audit_log.details.get("changes", {}) if audit_log.details else {}
            preview["changes_to_revert"] = {
                field: {
                    "current": change.get("new"),
                    "will_restore": change.get("old"),
                }
                for field, change in changes.items()
                if isinstance(change, dict) and "old" in change
            }
        elif str(audit_log.action) in ["LOCK_USER", "UNLOCK_USER"]:
            preview["changes_to_revert"] = {
                "action": f"Will {'unlock' if audit_log.action == 'LOCK_USER' else 're-lock'} the user"
            }
        elif str(audit_log.action).startswith("PRIVACY_CHANGE"):
            if audit_log.details:
                preview["changes_to_revert"] = {
                    "resource_type": audit_log.details.get("resource_type"),
                    "resource_id": audit_log.details.get("resource_id"),
                    "current_privacy": audit_log.details.get("new_privacy"),
                    "will_restore": audit_log.details.get("old_privacy"),
                }

    return preview
