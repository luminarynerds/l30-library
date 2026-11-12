# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Error Recovery Operations API Endpoints

Provides endpoints for graceful error recovery:
- Undo accidental checkout (within 5 minutes)
- Reverse mistaken return
- Undo fine waiver
- Restore soft-deleted patron
- Revert item status change
- Confirm destructive actions (with warnings)
"""
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import List, Optional, Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....models.circulation import Checkout, CheckoutStatus
from ....models.catalog import CatalogItem, ItemStatus
from ....models.fine import Fine
from ....services.circulation_reversal_service import (
    undo_checkout,
    reverse_return,
    revert_item_status_change,
)
from ....services.fine_reversal_service import undo_fine_waiver
from ....services.patron_recovery_service import (
    restore_deactivated_patron,
    unblock_patron,
    unsuspend_patron,
    list_recoverable_patrons,
)
from ..auth import get_current_user
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/staff/error-recovery", tags=["staff-error-recovery"])


# ============================================================================
# Request/Response Models
# ============================================================================


class DestructiveActionConfirmation(BaseModel):
    action_type: str = Field(..., description="Type of action (checkout, return, waive_fine, etc.)")
    resource_id: int = Field(..., description="ID of resource being affected")
    resource_type: str = Field(..., description="Type of resource (checkout, fine, patron, item)")


class DestructiveActionWarning(BaseModel):
    severity: str = Field(..., description="critical, high, medium, low")
    message: str = Field(..., description="Description of the warning")
    irreversible: bool = Field(default=False, description="Whether this action cannot be undone")


class DestructiveActionConfirmationResponse(BaseModel):
    action_type: str
    resource_id: int
    warnings: List[DestructiveActionWarning]
    requires_confirmation: bool = True
    confirmation_message: str = "Are you sure? This action cannot be easily undone."


class ReversalResult(BaseModel):
    success: bool
    message: str
    audit_log_id: Optional[int] = None
    reverted_changes: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class UndoCheckoutRequest(BaseModel):
    checkout_id: int = Field(..., description="ID of checkout to undo")
    reason: Optional[str] = Field(default="Accidental checkout", description="Reason for undoing")


class ReverseReturnRequest(BaseModel):
    checkout_id: int = Field(..., description="ID of checkout to restore")
    reason: Optional[str] = Field(default="Mistaken return", description="Reason for reversal")


class UndoFineWaiverRequest(BaseModel):
    fine_id: int = Field(..., description="ID of fine to un-waive")
    reason: Optional[str] = Field(default="Waiver error", description="Reason for undoing waiver")


class RevertItemStatusRequest(BaseModel):
    item_id: int = Field(..., description="ID of item to revert")
    previous_status: ItemStatus = Field(..., description="Previous status to restore")
    reason: Optional[str] = Field(default="Staff correction", description="Reason for reversion")


class RestorePatronRequest(BaseModel):
    patron_id: int = Field(..., description="ID of patron to restore")
    reason: Optional[str] = Field(default="Account restoration", description="Reason for restoration")


class UnblockPatronRequest(BaseModel):
    patron_id: int = Field(..., description="ID of patron to unblock")
    reason: Optional[str] = Field(default="Block removal", description="Reason for unblocking")


class UnsuspendPatronRequest(BaseModel):
    patron_id: int = Field(..., description="ID of patron to unsuspend")
    reason: Optional[str] = Field(default="Suspension removal", description="Reason for unsuspending")


class RecoverablePatron(BaseModel):
    id: int
    email: str
    name: str
    is_active: bool
    patron_status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


class RecoverablePaltronsResponse(BaseModel):
    patrons: List[RecoverablePatron]
    total_count: int


# ============================================================================
# Confirmation Endpoints
# ============================================================================


@router.post(
    "/confirm-action",
    response_model=DestructiveActionConfirmationResponse,
    status_code=status.HTTP_200_OK
)
async def confirm_destructive_action(
    confirmation: DestructiveActionConfirmation,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get confirmation warnings before performing a destructive action.

    This endpoint helps prevent accidental data loss by showing warnings
    and confirmation messages before destructive operations.

    Returns list of warnings and whether confirmation is required.
    """
    warnings: List[DestructiveActionWarning] = []

    if confirmation.action_type == "delete_checkout":
        warnings.append(
            DestructiveActionWarning(
                severity="high",
                message="This checkout will be marked as returned immediately.",
                irreversible=False,
            )
        )
        # Check if checkout is recent
        result = await db.execute(
            select(Checkout).where(Checkout.id == confirmation.resource_id)
        )
        checkout = result.scalar_one_or_none()
        if checkout:
            elapsed = datetime.now(timezone.utc) - checkout.checked_out_at
            if elapsed.total_seconds() > 300:  # 5 minutes
                warnings.append(
                    DestructiveActionWarning(
                        severity="medium",
                        message=f"Checkout was made {elapsed.total_seconds() / 60:.1f} minutes ago and is outside the standard undo window.",
                        irreversible=False,
                    )
                )

    elif confirmation.action_type == "reverse_return":
        warnings.append(
            DestructiveActionWarning(
                severity="medium",
                message="This will restore the checkout to active status.",
                irreversible=False,
            )
        )

    elif confirmation.action_type == "waive_fine":
        warnings.append(
            DestructiveActionWarning(
                severity="high",
                message="Fine will be marked as waived. Fine reversal requires audit trail review.",
                irreversible=False,
            )
        )

    elif confirmation.action_type == "delete_item":
        warnings.append(
            DestructiveActionWarning(
                severity="critical",
                message="Item will be permanently deleted from catalog.",
                irreversible=True,
            )
        )

    return DestructiveActionConfirmationResponse(
        action_type=confirmation.action_type,
        resource_id=confirmation.resource_id,
        warnings=warnings,
    )


# ============================================================================
# Circulation Recovery Endpoints
# ============================================================================


@router.post("/checkout/undo", response_model=ReversalResult, status_code=status.HTTP_200_OK)
async def undo_accidental_checkout(
    request: UndoCheckoutRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Undo an accidental checkout within 5 minutes.

    Requirements:
    - Checkout must have occurred within 5 minutes
    - Item must still be checked out
    - No return can have been processed

    Returns success/failure details and audit log ID.
    """
    result = await undo_checkout(
        checkout_id=request.checkout_id,
        performer=staff_user,
        db=db,
        reason=request.reason or "User error - accidental checkout",
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    await db.commit()

    return ReversalResult(
        success=result.success,
        message=result.message,
        audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


@router.post("/checkout/reverse-return", response_model=ReversalResult, status_code=status.HTTP_200_OK)
async def reverse_mistaken_return(
    request: ReverseReturnRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Reverse a mistaken return, restoring checkout to active status.

    Requirements:
    - Checkout must be in returned status
    - Item must be available or on hold
    - No other active checkout can exist for this item

    Returns success/failure details and audit log ID.
    """
    result = await reverse_return(
        checkout_id=request.checkout_id,
        performer=staff_user,
        db=db,
        reason=request.reason or "User error - mistaken return",
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    await db.commit()

    return ReversalResult(
        success=result.success,
        message=result.message,
        audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


@router.post("/item/revert-status", response_model=ReversalResult, status_code=status.HTTP_200_OK)
async def revert_item_status_change_endpoint(
    request: RevertItemStatusRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Revert an item status change to its previous state.

    Useful for correcting mistakes like incorrectly marking an item as
    lost, damaged, or withdrawn.

    Returns success/failure details and audit log ID.
    """
    result = await revert_item_status_change(
        item_id=request.item_id,
        previous_status=request.previous_status,
        performer=staff_user,
        db=db,
        reason=request.reason or "Staff correction",
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    await db.commit()

    return ReversalResult(
        success=result.success,
        message=result.message,
        audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


# ============================================================================
# Fine Recovery Endpoints
# ============================================================================


@router.post("/fine/undo-waiver", response_model=ReversalResult, status_code=status.HTTP_200_OK)
async def undo_fine_waiver_endpoint(
    request: UndoFineWaiverRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Undo a fine waiver, restoring the fine to unpaid status.

    Requirements:
    - Fine must be in waived status
    - Fine must not have been partially paid

    Returns success/failure details and audit log ID.
    """
    result = await undo_fine_waiver(
        fine_id=request.fine_id,
        performer=staff_user,
        db=db,
        reason=request.reason or "Staff correction - waiver undone",
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    await db.commit()

    return ReversalResult(
        success=result.success,
        message=result.message,
        audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


# ============================================================================
# Patron Recovery Endpoints
# ============================================================================


@router.post("/patron/restore", response_model=ReversalResult, status_code=status.HTTP_200_OK)
async def restore_patron_endpoint(
    request: RestorePatronRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Restore a deactivated patron account.

    Allows recovery from accidental deactivation of a patron account.
    The patron is restored to ACTIVE status.

    Returns success/failure details and audit log ID.
    """
    result = await restore_deactivated_patron(
        patron_id=request.patron_id,
        performer=staff_user,
        db=db,
        reason=request.reason or "Account restoration - error recovery",
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    await db.commit()

    return ReversalResult(
        success=result.success,
        message=result.message,
        audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


@router.post("/patron/unblock", response_model=ReversalResult, status_code=status.HTTP_200_OK)
async def unblock_patron_endpoint(
    request: UnblockPatronRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Unblock an administratively blocked patron.

    Allows recovery from accidental blocking of a patron account.
    The patron is restored to ACTIVE status.

    Returns success/failure details and audit log ID.
    """
    result = await unblock_patron(
        patron_id=request.patron_id,
        performer=staff_user,
        db=db,
        reason=request.reason or "Block removal",
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    await db.commit()

    return ReversalResult(
        success=result.success,
        message=result.message,
        audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


@router.post("/patron/unsuspend", response_model=ReversalResult, status_code=status.HTTP_200_OK)
async def unsuspend_patron_endpoint(
    request: UnsuspendPatronRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Unsuspend a temporarily suspended patron.

    Allows recovery from accidental suspension of a patron account.
    The patron is restored to ACTIVE status.

    Returns success/failure details and audit log ID.
    """
    result = await unsuspend_patron(
        patron_id=request.patron_id,
        performer=staff_user,
        db=db,
        reason=request.reason or "Suspension removal",
    )

    if not result.success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result.message,
        )

    await db.commit()

    return ReversalResult(
        success=result.success,
        message=result.message,
        audit_log_id=result.audit_log_id,
        reverted_changes=result.reverted_changes,
        warnings=result.warnings,
    )


@router.get("/patrons/recoverable", response_model=RecoverablePaltronsResponse, status_code=status.HTTP_200_OK)
async def list_recoverable_patrons_endpoint(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    List patrons that can be recovered (deactivated, suspended, blocked).

    Useful for finding patrons who may have been accidentally affected
    by administrative actions.

    Returns paginated list of recoverable patrons.
    """
    patrons = await list_recoverable_patrons(db=db, limit=limit, offset=offset)

    return RecoverablePaltronsResponse(
        patrons=[RecoverablePatron(**p) for p in patrons],
        total_count=len(patrons),
    )
