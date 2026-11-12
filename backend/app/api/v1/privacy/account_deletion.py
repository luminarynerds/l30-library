# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""GDPR Article 17 - Right to Erasure (Patron-Initiated Account Deletion) Endpoints.

Also includes privacy settings and deletion verification transparency.
"""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import get_settings
from ....core.database import get_db
from ....core.email import (
    send_deletion_cancelled_email,
    send_deletion_complete_email,
    send_deletion_request_email,
)
from ....core.frontend_routes import routes
from ....core.security import verify_password_async
from ....models.audit_log import AuditAction, AuditLog
from ....models.user import User
from ..auth import get_current_user

from .schemas import (
    AccountDeletionRequest,
    DeletionEligibilityResponse,
    DeletionRequestResponse,
    DeletionVerificationResponse,
    PatronPrivacySettingsResponse,
    PatronPrivacySettingsUpdate,
)
from .helpers import (
    DELETION_GRACE_PERIOD_DAYS,
    EMAIL_BLOCK_PERIOD_DAYS,
    _perform_user_deletion,
    check_deletion_eligibility,
    create_audit_log,
    record_deleted_email,
)

settings = get_settings()
logger = get_logger(__name__)

router = APIRouter()


@router.get("/account/deletion-eligibility", response_model=DeletionEligibilityResponse)
async def check_my_deletion_eligibility(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if the current user is eligible for account deletion.

    Returns information about any blockers (unpaid fines, active checkouts, etc.)
    """
    return await check_deletion_eligibility(db, current_user)


@router.get("/account", response_model=DeletionEligibilityResponse)
async def get_account_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check current account status and deletion eligibility.

    Returns information about account deletion status and any blockers.
    """
    return await check_deletion_eligibility(db, current_user)


@router.delete("/account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_my_account(
    request: Request,
    deletion_request: AccountDeletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Permanently delete account and all personal data (GDPR Article 17 - Immediate).

    This action is IRREVERSIBLE. All personal data will be deleted or anonymized.

    Requires:
    - confirmation field must be exactly "DELETE"
    - Current password for verification

    Data handling:
    - DELETED: Personal info, reading history, preferences, holds, favorites, lists
    - ANONYMIZED: Checkout history, financial records (legal requirement)
    """
    # Verify confirmation
    if deletion_request.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation must be exactly 'DELETE'"
        )

    # Verify password (identity verification)
    if not await verify_password_async(deletion_request.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    # Check eligibility
    eligibility = await check_deletion_eligibility(db, current_user)
    if not eligibility.eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete account: {'; '.join(eligibility.blockers)}"
        )

    # Store email info before deletion for notification and blocking
    user_email = current_user.email
    user_first_name = current_user.first_name

    # Record email for 90-day re-registration block
    await record_deleted_email(
        db=db,
        email=user_email,
        deletion_type="self_service",
    )

    # Create anonymized audit log BEFORE deleting user
    await create_audit_log(
        db=db,
        action=AuditAction.GDPR_DELETION_COMPLETED,
        target_user_id=None,  # Anonymized - don't reference deleted user
        details={
            "deletion_type": "immediate_self_service",
            "user_role": str(current_user.role),
            "account_age_days": (datetime.now(timezone.utc) - current_user.created_at).days if current_user.created_at else None,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    # Perform deletion
    await _perform_user_deletion(db, current_user.id)

    await db.commit()

    # Send confirmation email (after commit, best effort)
    try:
        await send_deletion_complete_email(user_email, user_first_name)
    except Exception as e:  # noqa: BLE001  # best-effort confirmation email — deletion already committed
        logger.warning(f"Failed to send deletion confirmation email: {e}")

    return {
        "message": "Account permanently deleted",
        "deleted_at": datetime.now(timezone.utc).isoformat(),
        "email_blocked_until": (datetime.now(timezone.utc) + timedelta(days=EMAIL_BLOCK_PERIOD_DAYS)).isoformat(),
    }


@router.get("/account/request-deletion", response_model=DeletionEligibilityResponse)
async def check_deletion_request_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if account deletion can be requested.

    Returns eligibility status and any blockers preventing deletion.
    """
    return await check_deletion_eligibility(db, current_user)


@router.post("/account/request-deletion", response_model=DeletionRequestResponse)
async def request_account_deletion(
    request: Request,
    deletion_request: AccountDeletionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Request account deletion with a 30-day grace period (soft delete).

    Workflow:
    1. User requests deletion (this endpoint)
    2. System verifies identity (password)
    3. System checks for blockers (fines, checkouts, children)
    4. Account is scheduled for deletion in 30 days
    5. User receives confirmation email
    6. User can cancel within 30 days
    7. After 30 days, account is permanently deleted

    This is the recommended deletion flow as it allows for recovery.
    """
    # Verify confirmation
    if deletion_request.confirmation != "DELETE":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmation must be exactly 'DELETE'"
        )

    # Verify password (identity verification)
    if not await verify_password_async(deletion_request.password, current_user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid password")

    # Check if deletion already requested
    if current_user.deletion_requested_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Deletion already scheduled for {current_user.deletion_scheduled_for.isoformat()}"
        )

    # Check eligibility
    eligibility = await check_deletion_eligibility(db, current_user)
    if not eligibility.eligible:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete account: {'; '.join(eligibility.blockers)}"
        )

    # Schedule deletion for 30 days from now
    now = datetime.now(timezone.utc)
    deletion_date = now + timedelta(days=DELETION_GRACE_PERIOD_DAYS)

    current_user.deletion_requested_at = now
    current_user.deletion_scheduled_for = deletion_date

    # Create audit log
    await create_audit_log(
        db=db,
        action=AuditAction.GDPR_DELETION_REQUESTED,
        target_user_id=current_user.id,
        details={
            "deletion_type": "scheduled_self_service",
            "scheduled_for": deletion_date.isoformat(),
            "grace_period_days": DELETION_GRACE_PERIOD_DAYS,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    await db.commit()

    # Send confirmation email
    try:
        cancel_url = routes.url(settings.frontend_url, routes.account_settings)
        await send_deletion_request_email(
            to_email=current_user.email,
            first_name=current_user.first_name,
            deletion_date=deletion_date.strftime("%B %d, %Y"),
            cancel_url=cancel_url,
        )
    except Exception as e:  # noqa: BLE001  # best-effort deletion request email
        logger.warning(f"Failed to send deletion request email: {e}")

    return DeletionRequestResponse(
        message="Account deletion scheduled",
        deletion_scheduled_for=deletion_date.isoformat(),
        can_cancel_until=deletion_date.isoformat(),
        data_export_available=True,
    )


@router.get("/account/cancel-deletion", response_model=DeletionEligibilityResponse)
async def check_deletion_cancellation_status(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Check if a scheduled deletion can be cancelled.

    Returns account status including whether deletion is currently pending.
    """
    return await check_deletion_eligibility(db, current_user)


@router.post("/account/cancel-deletion")
async def cancel_account_deletion(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cancel a scheduled account deletion."""
    if not current_user.deletion_requested_at:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No deletion request pending")

    # Create audit log
    await create_audit_log(
        db=db,
        action=AuditAction.GDPR_DELETION_CANCELLED,
        target_user_id=current_user.id,
        details={
            "originally_scheduled_for": current_user.deletion_scheduled_for.isoformat() if current_user.deletion_scheduled_for else None,
            "days_before_deletion": (current_user.deletion_scheduled_for - datetime.now(timezone.utc)).days if current_user.deletion_scheduled_for else None,
        },
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent", "")[:500],
    )

    current_user.deletion_requested_at = None
    current_user.deletion_scheduled_for = None
    await db.commit()

    # Send cancellation email
    try:
        await send_deletion_cancelled_email(
            to_email=current_user.email,
            first_name=current_user.first_name,
        )
    except Exception as e:  # noqa: BLE001  # best-effort cancellation email
        logger.warning(f"Failed to send deletion cancellation email: {e}")

    return {"message": "Account deletion cancelled"}


# =============================================================================
# Privacy Settings
# =============================================================================


@router.get("/settings")
async def get_privacy_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current patron privacy settings."""
    return PatronPrivacySettingsResponse(
        discreet_receipts=current_user.discreet_receipts,
        allow_staff_access_to_history=current_user.allow_staff_access_to_history,
        track_reading_history=current_user.track_reading_history,
        aggregate_recommendations_opt_out=current_user.aggregate_recommendations_opt_out,
        notification_frequency=current_user.notification_frequency,
    )


@router.put("/settings")
async def update_privacy_settings(
    settings_update: PatronPrivacySettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update patron privacy settings.

    Privacy-conscious defaults:
    - discreet_receipts: True (hides item titles from printed notices)
    - allow_staff_access_to_history: False (patrons must opt-in to staff viewing)
    - track_reading_history: False (reading activity not tracked by default)
    - notification_frequency: 'instant' (immediate notifications, can switch to daily/weekly)
    """
    if settings_update.discreet_receipts is not None:
        current_user.discreet_receipts = settings_update.discreet_receipts

    if settings_update.allow_staff_access_to_history is not None:
        current_user.allow_staff_access_to_history = settings_update.allow_staff_access_to_history

    if settings_update.track_reading_history is not None:
        current_user.track_reading_history = settings_update.track_reading_history

    if settings_update.aggregate_recommendations_opt_out is not None:
        current_user.aggregate_recommendations_opt_out = settings_update.aggregate_recommendations_opt_out

    if settings_update.notification_frequency is not None:
        if settings_update.notification_frequency not in ['instant', 'daily', 'weekly', 'never']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="notification_frequency must be 'instant', 'daily', 'weekly', or 'never'"
            )
        current_user.notification_frequency = settings_update.notification_frequency

    # Log privacy setting changes in audit
    await db.execute(
        update(AuditLog.__table__).values(
            admin_id=current_user.id,
            target_user_id=current_user.id,
            action=AuditAction.PRIVACY_SETTING_CHANGED,
            details={
                "discreet_receipts": current_user.discreet_receipts,
                "allow_staff_access_to_history": current_user.allow_staff_access_to_history,
                "track_reading_history": current_user.track_reading_history,
                "aggregate_recommendations_opt_out": current_user.aggregate_recommendations_opt_out,
                "notification_frequency": current_user.notification_frequency,
            },
        )
    )

    await db.commit()

    logger.info(
        f"Privacy settings updated for user {current_user.id}",
        extra={
            "user_id": current_user.id,
            "settings": {
                "discreet_receipts": current_user.discreet_receipts,
                "allow_staff_access_to_history": current_user.allow_staff_access_to_history,
            }
        }
    )

    return PatronPrivacySettingsResponse(
        discreet_receipts=current_user.discreet_receipts,
        allow_staff_access_to_history=current_user.allow_staff_access_to_history,
        track_reading_history=current_user.track_reading_history,
        aggregate_recommendations_opt_out=current_user.aggregate_recommendations_opt_out,
        notification_frequency=current_user.notification_frequency,
    )


# =============================================================================
# Deletion Verification - "Can you truly delete, not just soft-delete?"
# =============================================================================


@router.get("/deletion-verification", response_model=DeletionVerificationResponse)
async def get_deletion_verification(
    current_user: User = Depends(get_current_user),
):
    """
    Explain exactly what happens to data when a patron requests deletion.

    Answers: "Can you truly delete, not just soft-delete? What about backups?
    What about audit logs?"

    This transparency endpoint documents the library's data deletion process
    so patrons understand what happens to their data.
    """
    return DeletionVerificationResponse(
        hard_deleted=[
            "Authentication tokens (refresh tokens, password history)",
            "Favorites and reading preferences",
            "Reading lists and saved items",
            "Reading activity logs and statistics",
            "Personal profile data (name, email, phone, address cleared from user record)",
        ],
        anonymized=[
            "Checkout history (user_id set to NULL — kept for library collection statistics only)",
            "Fine records (user_id set to NULL — kept for financial/legal compliance)",
            "Event registrations (email replaced with anonymous hash)",
            "Audit log references (user IDs set to NULL — log entries retained for compliance)",
        ],
        retained_in_backups=(
            "Database backups are retained for 30 days on a rolling basis. "
            "After 30 days, backup copies containing your data are overwritten. "
            "Backup data is encrypted at rest and is never used for analytics."
        ),
        backup_retention_policy=(
            "Daily backups: 7 days. Weekly backups: 30 days. "
            "Your data will be fully purged from all backup copies within 30 days of deletion."
        ),
        audit_log_handling=(
            "Audit logs are anonymized (your user ID is removed) but the log entries themselves "
            "are retained for legal compliance. No personal data remains in anonymized audit entries."
        ),
        re_registration_block_days=EMAIL_BLOCK_PERIOD_DAYS,
        deletion_is_true_erasure=True,
        what_remains_after_deletion=[
            "Anonymized checkout statistics (no link to your identity)",
            "Anonymized financial records (legal requirement, no link to your identity)",
            "Anonymized audit log entries (compliance requirement, no personal data)",
            "Hashed email in re-registration block list (expires after 90 days, cannot be reversed to your email)",
        ],
    )
