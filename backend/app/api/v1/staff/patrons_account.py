# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff - Patron Account Management API Endpoints

This module provides endpoints for:
- Password reset (trigger reset, generate temp code)
- Duplicate detection and merging
- Library card printing
- Account settings management

Related modules:
- staff.py: Basic patron management
- staff_fines.py: Fines management
"""

from app.core.logging import get_logger
import re
import secrets
import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ....core.config import get_settings
from ....core.database import get_db
from ....core.frontend_routes import routes
from ....core.shortcuts import get_or_404
from ....core.email import send_email, COLORS
from ....core.rate_limit import limiter
from ....core.security import hash_password, hash_reset_token
from ....models.audit_log import AuditAction, AuditLog
from ....models.catalog import CatalogItem
from ....models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from ....models.favorite import Favorite
from ....models.fine import Fine, FineStatus
from ....models.notification import NotificationPreferences
from ....models.patron_merge_audit import PatronMergeAudit
from ....models.patron_communication import PatronNote
from ....models.reading_list import ReadingList, ListItem
from ....models.user import (
    User,
    UserRole,
    PasswordHistory,
    PatronStatus,
    name_blind_hash,
    email_blind_hash,
)
from ....schemas.user import UserResponse
from ..dependencies import require_staff, require_admin

router = APIRouter(prefix="/staff/patrons", tags=["staff-patron-account"])
settings = get_settings()
logger = get_logger(__name__)


from .patrons_account_helpers import check_staff_access_permission
from .patrons_account_schemas import (
    AccountSettingsResponse,
    AccountSettingsUpdate,
    CardPrintHistory,
    CardPrintedRequest,
    CardPrintedResponse,
    DeceasedPatronResponse,
    DuplicatePatron,
    DuplicateSearchResponse,
    EstateOutstandingItemsResponse,
    LibraryCardData,
    MarkDeceasedRequest,
    MergeHistoryResponse,
    MergePreview,
    MergeRequest,
    MergeResponse,
    PasswordResetRequest,
    PasswordResetResponse,
    PatronMergeAuditLogResponse,
    StaffAccessConsentResponse,
)


# =============================================================================
# Password Reset Endpoints
# =============================================================================


@router.post("/{patron_id}/reset-password", response_model=PasswordResetResponse)
@limiter.limit("10/minute")
async def reset_patron_password(
    request: Request,
    patron_id: int,
    reset_request: PasswordResetRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger password reset for a patron.

    Options:
    - send_email: Send password reset link to patron's email
    - generate_temp_code: Generate a temporary access code (6 characters)
    """
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    if patron.role != UserRole.PATRON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only reset passwords for patron accounts",
        )

    if reset_request.send_email and reset_request.generate_temp_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate both email link and temporary code simultaneously. Choose one.",
        )

    email_sent = False
    temp_code = None

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    patron.reset_token = hash_reset_token(reset_token)
    patron.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=24)

    if reset_request.send_email:
        # Send password reset email
        reset_link = (
            f"{routes.url(settings.frontend_url, routes.reset_password)}?token={reset_token}"
        )

        subject = "Password Reset Request"
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: {COLORS["heading"]};">Password Reset</h2>
            <p>Hi {patron.first_name},</p>
            <p>A password reset was requested for your library account by library staff.</p>
            <p>Click the button below to set a new password:</p>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_link}"
                   style="background-color: {COLORS["button"]}; color: white; padding: 12px 30px;
                          text-decoration: none; border-radius: 5px; display: inline-block;">
                    Reset Password
                </a>
            </p>

            <p style="color: {COLORS["body"]};">
                This link will expire in 24 hours. If you did not request this reset,
                please contact the library.
            </p>

            <hr style="border: none; border-top: 1px solid {COLORS["divider"]}; margin: 30px 0;">
            <p style="color: #888; font-size: 12px;">
                {settings.app_name}<br>
                This is an automated message. Please do not reply to this email.
            </p>
        </div>
        """

        try:
            email_sent = await send_email(
                to_email=patron.email,
                subject=subject,
                html_content=html_content,
            )
        except Exception as e:  # noqa: BLE001  # best-effort password reset email
            logger.error(f"Failed to send password reset email: {e}")

    if reset_request.generate_temp_code:
        # Generate a 6-character temporary access code
        temp_code = "".join(
            secrets.choice(string.ascii_uppercase + string.digits) for _ in range(6)
        )
        # Store hashed version
        patron.reset_token = hash_reset_token(temp_code)
        patron.reset_token_expires = datetime.now(timezone.utc) + timedelta(hours=4)

    # Get last password change date from history
    last_change = None
    history_result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == patron_id)
        .order_by(PasswordHistory.created_at.desc())
        .limit(1)
    )
    last_history = history_result.scalar_one_or_none()
    if last_history:
        last_change = last_history.created_at

    await db.commit()

    logger.info(
        f"Password reset initiated for patron {patron_id} by staff {staff_user.id}",
        extra={"patron_id": patron_id, "staff_id": staff_user.id, "email_sent": email_sent},
    )

    return PasswordResetResponse(
        message="Password reset initiated successfully",
        email_sent=email_sent,
        temp_code=temp_code,
        last_password_change=last_change,
    )


@router.get("/{patron_id}/password-info")
async def get_patron_password_info(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get password change history information for a patron."""
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    # Get password change history count and last change
    history_result = await db.execute(
        select(PasswordHistory)
        .where(PasswordHistory.user_id == patron_id)
        .order_by(PasswordHistory.created_at.desc())
    )
    history = history_result.scalars().all()

    last_change = history[0].created_at if history else patron.created_at

    return {
        "patron_id": patron_id,
        "last_password_change": last_change,
        "password_change_count": len(history),
        "has_pending_reset": patron.reset_token is not None
        and patron.reset_token_expires
        and patron.reset_token_expires > datetime.now(timezone.utc),
    }


# =============================================================================
# Duplicate Detection Endpoints
# =============================================================================


@router.get("/{patron_id}/duplicates", response_model=DuplicateSearchResponse)
async def find_duplicate_patrons(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Find potential duplicate patron records based on:
    - Exact email match
    - Similar name (first + last)
    - Same phone number
    - Similar library card pattern
    """
    # Get the source patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    duplicates = []
    search_criteria = {
        "email": patron.email,
        "name": f"{patron.first_name} {patron.last_name}",
        "phone": patron.phone,
    }

    # Search for duplicates (exclude the source patron)
    query = select(User).where(
        User.id != patron_id,
        User.role == UserRole.PATRON,
    )

    # Build OR conditions for matching
    conditions = []

    # Exact email match (different casing) via blind index (email is encrypted)
    if patron.email:
        conditions.append(User.email_hash == email_blind_hash(patron.email))

    # Same first and last name (names are encrypted; match via blind index)
    conditions.append(
        and_(
            User.first_name_hash == name_blind_hash((patron.first_name or "").strip().lower()),
            User.last_name_hash == name_blind_hash((patron.last_name or "").strip().lower()),
        )
    )

    # Same phone number (if exists)
    if patron.phone:
        # Match by phone last 4 digits (phone is encrypted)
        normalized_phone = "".join(c for c in patron.phone if c.isdigit())
        if len(normalized_phone) >= 4:
            conditions.append(User.phone_last4 == normalized_phone[-4:])

    # Similar name variations (swapped first/last; blind index)
    conditions.append(
        and_(
            User.first_name_hash == name_blind_hash((patron.last_name or "").strip().lower()),
            User.last_name_hash == name_blind_hash((patron.first_name or "").strip().lower()),
        )
    )

    query = query.where(or_(*conditions))

    result = await db.execute(query)
    potential_duplicates = result.scalars().all()

    # Batch fetch statistics for all potential duplicates (avoids N+1 queries)
    dup_ids = [d.id for d in potential_duplicates]
    if dup_ids:
        checkout_result = await db.execute(
            select(Checkout.user_id, func.count(Checkout.id))
            .where(Checkout.user_id.in_(dup_ids))
            .group_by(Checkout.user_id)
        )
        checkout_counts = dict(checkout_result.all())

        hold_result = await db.execute(
            select(Hold.user_id, func.count(Hold.id))
            .where(Hold.user_id.in_(dup_ids))
            .group_by(Hold.user_id)
        )
        hold_counts = dict(hold_result.all())

        fines_result = await db.execute(
            select(Fine.user_id, func.sum(Fine.amount - Fine.amount_paid))
            .where(
                Fine.user_id.in_(dup_ids), Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
            )
            .group_by(Fine.user_id)
        )
        fines_by_user = dict(fines_result.all())
    else:
        checkout_counts = {}
        hold_counts = {}
        fines_by_user = {}

    for dup in potential_duplicates:
        # Determine match type and score
        match_type = "name"
        match_score = 0.0

        if dup.email.lower() == patron.email.lower():
            match_type = "email"
            match_score = 1.0
        elif (
            dup.first_name.lower() == patron.first_name.lower()
            and dup.last_name.lower() == patron.last_name.lower()
        ):
            match_type = "name"
            match_score = 0.9
        elif dup.phone and patron.phone:
            dup_phone = "".join(c for c in dup.phone if c.isdigit())
            src_phone = "".join(c for c in patron.phone if c.isdigit())
            if dup_phone == src_phone:
                match_type = "phone"
                match_score = 0.85
        else:
            match_score = 0.7

        duplicates.append(
            DuplicatePatron(
                id=dup.id,
                email=dup.email,
                first_name=dup.first_name,
                last_name=dup.last_name,
                phone=dup.phone,
                library_card=dup.library_card,
                created_at=dup.created_at,
                is_active=dup.is_active,
                match_type=match_type,
                match_score=match_score,
                total_checkouts=checkout_counts.get(dup.id, 0),
                total_holds=hold_counts.get(dup.id, 0),
                fines_balance=fines_by_user.get(dup.id, Decimal("0.00")),
            )
        )

    # Sort by match score descending
    duplicates.sort(key=lambda x: x.match_score, reverse=True)

    return DuplicateSearchResponse(
        patron_id=patron_id,
        duplicates=duplicates,
        search_criteria=search_criteria,
    )


@router.post("/merge/preview", response_model=MergePreview)
async def preview_patron_merge(
    merge_request: MergeRequest,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Preview what will happen when merging two patron records.
    Requires admin privileges.
    """
    # Get both patrons
    primary_result = await db.execute(
        select(User).where(User.id == merge_request.primary_patron_id)
    )
    primary = primary_result.scalar_one_or_none()

    secondary_result = await db.execute(
        select(User).where(User.id == merge_request.secondary_patron_id)
    )
    secondary = secondary_result.scalar_one_or_none()

    if not primary or not secondary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="One or both patrons not found"
        )

    if primary.id == secondary.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge a patron with itself"
        )

    # Count items to transfer
    checkout_count = await db.execute(
        select(func.count(Checkout.id)).where(Checkout.user_id == secondary.id)
    )
    hold_count = await db.execute(select(func.count(Hold.id)).where(Hold.user_id == secondary.id))
    fine_count = await db.execute(select(func.count(Fine.id)).where(Fine.user_id == secondary.id))
    reading_list_count = await db.execute(
        select(func.count(ReadingList.id)).where(ReadingList.user_id == secondary.id)
    )
    favorite_count = await db.execute(
        select(func.count(Favorite.id)).where(Favorite.user_id == secondary.id)
    )

    return MergePreview(
        primary_patron={
            "id": primary.id,
            "email": primary.email,
            "name": f"{primary.first_name} {primary.last_name}",
            "library_card": primary.library_card,
            "created_at": primary.created_at.isoformat(),
        },
        secondary_patron={
            "id": secondary.id,
            "email": secondary.email,
            "name": f"{secondary.first_name} {secondary.last_name}",
            "library_card": secondary.library_card,
            "created_at": secondary.created_at.isoformat(),
        },
        checkouts_to_transfer=checkout_count.scalar() or 0,
        holds_to_transfer=hold_count.scalar() or 0,
        fines_to_transfer=fine_count.scalar() or 0,
        history_records_to_transfer=0,  # Would add reading history count
        reading_lists_to_transfer=reading_list_count.scalar() or 0,
        favorites_to_transfer=favorite_count.scalar() or 0,
    )


@router.post("/merge", response_model=MergeResponse)
@limiter.limit("5/minute")
async def merge_patron_records(
    request: Request,
    merge_request: MergeRequest,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Merge two patron records. The secondary patron's data is transferred
    to the primary patron, then the secondary patron is deleted.

    Creates a complete audit trail including:
    - Snapshot of secondary patron's data before deletion
    - Details of all data transferred
    - Counts of items transferred

    Requires admin privileges. Data can be recovered from audit log if needed.
    """
    # Get both patrons
    primary_result = await db.execute(
        select(User).where(User.id == merge_request.primary_patron_id)
    )
    primary = primary_result.scalar_one_or_none()

    secondary_result = await db.execute(
        select(User).where(User.id == merge_request.secondary_patron_id)
    )
    secondary = secondary_result.scalar_one_or_none()

    if not primary or not secondary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="One or both patrons not found"
        )

    if primary.id == secondary.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot merge a patron with itself"
        )

    if primary.role != UserRole.PATRON or secondary.role != UserRole.PATRON:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Can only merge patron accounts"
        )

    # =========================================================================
    # Step 1: Archive secondary patron's data BEFORE any modifications
    # =========================================================================

    # Get notification preferences for archiving
    prefs_result = await db.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == secondary.id)
    )
    notification_prefs = prefs_result.scalar_one_or_none()

    # Archive secondary patron's user data
    archived_user_data = {
        "id": secondary.id,
        "email": secondary.email,
        "first_name": secondary.first_name,
        "last_name": secondary.last_name,
        "phone": secondary.phone,
        "address": secondary.address,
        "library_card": secondary.library_card,
        "is_active": secondary.is_active,
        "role": str(secondary.role) if secondary.role else None,
        "created_at": secondary.created_at.isoformat() if secondary.created_at else None,
        "notification_preferences": {
            "email_enabled": notification_prefs.email_enabled if notification_prefs else True,
            "sms_enabled": notification_prefs.sms_enabled if notification_prefs else False,
        }
        if notification_prefs
        else None,
    }

    # Collect data to transfer and archive
    data_transferred = {
        "checkouts": [],
        "holds": [],
        "fines": [],
        "reading_lists": [],
        "favorites": [],
        "notes": [],
    }

    data_archived = {
        "user": archived_user_data,
        "checkouts": [],
        "holds": [],
        "fines": [],
        "reading_lists": [],
        "favorites": [],
        "notes": [],
    }

    # =========================================================================
    # Step 2: Transfer checkouts (with archiving)
    # =========================================================================
    checkouts_transferred = 0
    result = await db.execute(select(Checkout).where(Checkout.user_id == secondary.id))
    checkouts = result.scalars().all()
    for checkout in checkouts:
        checkout_data = {
            "id": checkout.id,
            "item_id": checkout.item_id,
            "status": str(checkout.status) if checkout.status else None,
            "checked_out_at": checkout.checked_out_at.isoformat()
            if checkout.checked_out_at
            else None,
            "due_date": checkout.due_date.isoformat() if checkout.due_date else None,
        }
        data_archived["checkouts"].append(checkout_data)

        if merge_request.merge_checkouts:
            checkout.user_id = primary.id
            data_transferred["checkouts"].append(checkout_data)
            checkouts_transferred += 1

    # =========================================================================
    # Step 3: Transfer holds (with archiving)
    # =========================================================================
    holds_transferred = 0
    result = await db.execute(select(Hold).where(Hold.user_id == secondary.id))
    holds = result.scalars().all()
    for hold in holds:
        hold_data = {
            "id": hold.id,
            "item_id": hold.item_id,
            "status": str(hold.status) if hold.status else None,
            "position": hold.position,
            "created_at": hold.created_at.isoformat() if hold.created_at else None,
        }
        data_archived["holds"].append(hold_data)

        if merge_request.merge_holds:
            hold.user_id = primary.id
            data_transferred["holds"].append(hold_data)
            holds_transferred += 1

    # =========================================================================
    # Step 4: Transfer fines (with archiving)
    # =========================================================================
    fines_transferred = 0
    result = await db.execute(select(Fine).where(Fine.user_id == secondary.id))
    fines = result.scalars().all()
    for fine in fines:
        fine_data = {
            "id": fine.id,
            "fine_type": str(fine.fine_type) if fine.fine_type else None,
            "amount": str(fine.amount) if fine.amount else "0.00",
            "amount_paid": str(fine.amount_paid) if fine.amount_paid else "0.00",
            "status": str(fine.status) if fine.status else None,
            "description": fine.description,
            "created_at": fine.created_at.isoformat() if fine.created_at else None,
        }
        data_archived["fines"].append(fine_data)

        if merge_request.merge_fines:
            fine.user_id = primary.id
            data_transferred["fines"].append(fine_data)
            fines_transferred += 1

    # =========================================================================
    # Step 5: Transfer reading lists (with archiving) - TRANSFER instead of delete
    # =========================================================================
    reading_lists_transferred = 0
    result = await db.execute(
        select(ReadingList)
        .where(ReadingList.user_id == secondary.id)
        .options(selectinload(ReadingList.items))
    )
    reading_lists = result.scalars().all()
    for reading_list in reading_lists:
        list_data = {
            "id": reading_list.id,
            "name": reading_list.name,
            "description": reading_list.description,
            "created_at": reading_list.created_at.isoformat() if reading_list.created_at else None,
            "items": [
                {
                    "id": item.id,
                    "catalog_item_id": item.catalog_item_id,
                    "added_at": item.added_at.isoformat() if item.added_at else None,
                }
                for item in reading_list.items
            ],
        }
        data_archived["reading_lists"].append(list_data)

        if merge_request.merge_reading_lists:
            # Transfer the reading list to primary patron
            reading_list.user_id = primary.id
            # Append "(merged)" to name to indicate it came from a merge
            reading_list.name = f"{reading_list.name} (merged)"
            data_transferred["reading_lists"].append(list_data)
            reading_lists_transferred += 1

    # =========================================================================
    # Step 6: Transfer favorites (with archiving) - TRANSFER instead of delete
    # =========================================================================
    favorites_transferred = 0
    result = await db.execute(select(Favorite).where(Favorite.user_id == secondary.id))
    favorites = result.scalars().all()

    # Get existing favorites for primary patron to avoid duplicates
    primary_favorites_result = await db.execute(
        select(Favorite.catalog_item_id).where(Favorite.user_id == primary.id)
    )
    primary_favorite_item_ids = set(primary_favorites_result.scalars().all())

    for favorite in favorites:
        favorite_data = {
            "id": favorite.id,
            "catalog_item_id": favorite.catalog_item_id,
            "created_at": favorite.created_at.isoformat() if favorite.created_at else None,
        }
        data_archived["favorites"].append(favorite_data)

        if merge_request.merge_favorites:
            # Only transfer if primary doesn't already have this favorite
            if favorite.catalog_item_id not in primary_favorite_item_ids:
                favorite.user_id = primary.id
                data_transferred["favorites"].append(favorite_data)
                favorites_transferred += 1
                primary_favorite_item_ids.add(favorite.catalog_item_id)
            else:
                # Delete duplicate favorite (will be deleted with patron anyway)
                await db.delete(favorite)

    # =========================================================================
    # Step 6a: Carry over the more restrictive patron status
    #
    # A merge must never RELAX a restriction. Without this, merging a BLOCKED
    # duplicate into an ACTIVE primary left the survivor ACTIVE and deleted the
    # blocked record -- i.e. "merge the duplicate" silently cleared the block.
    # =========================================================================
    _STATUS_SEVERITY = {
        PatronStatus.ACTIVE: 0,
        PatronStatus.SUSPENDED: 1,
        PatronStatus.BLOCKED: 2,
        PatronStatus.DECEASED: 3,
    }
    # A status missing from that table must not default to 0, which ranks it as
    # permissive as ACTIVE and lets the merge drop it -- the same silent relaxing
    # this block exists to prevent. Rank an unmapped status above everything known,
    # so a PatronStatus added later is carried over until someone ranks it.
    _UNMAPPED_SEVERITY = max(_STATUS_SEVERITY.values()) + 1
    # User.patron_status is a legacy `Column(SQLEnum(PatronStatus))`, so mypy reads
    # it as Column[Any] rather than PatronStatus and rejects the dict lookup. The
    # value is a real PatronStatus at runtime; the ignores go when the model moves
    # to Mapped[].
    primary_severity = _STATUS_SEVERITY.get(primary.patron_status, _UNMAPPED_SEVERITY)  # type: ignore[call-overload]
    secondary_severity = _STATUS_SEVERITY.get(secondary.patron_status, _UNMAPPED_SEVERITY)  # type: ignore[call-overload]
    if secondary_severity > primary_severity:
        primary.patron_status = secondary.patron_status
        # A restriction with no reason attached is not auditable, so carry the
        # secondary's justification across with the status it belongs to.
        primary.suspension_reason = secondary.suspension_reason
        primary.suspended_until = secondary.suspended_until

    # =========================================================================
    # Step 6b: Transfer staff notes (with archiving)
    #
    # PatronNote.patron_id is NOT NULL with a `patron` backref, so leaving these
    # attached to the secondary and then deleting it makes SQLAlchemy try to
    # nullify the FK -> NotNullViolationError. Merging duplicate patrons is
    # precisely when notes exist, so this 500'd the common case.
    # =========================================================================
    notes_transferred = 0
    result = await db.execute(select(PatronNote).where(PatronNote.patron_id == secondary.id))
    for note in result.scalars().all():
        note_data = {
            "id": note.id,
            "created_at": note.created_at.isoformat() if note.created_at else None,
        }
        data_archived["notes"].append(note_data)
        note.patron_id = primary.id
        data_transferred["notes"].append(note_data)
        notes_transferred += 1

    # =========================================================================
    # Step 7: Create audit record BEFORE deleting secondary patron
    # =========================================================================

    # Get IP address and user agent for security tracking
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")

    # Create the merge audit record
    merge_audit = PatronMergeAudit(
        primary_patron_id=primary.id,
        secondary_patron_id=secondary.id,
        merged_by_id=staff_user.id,
        merged_at=datetime.now(timezone.utc),
        data_transferred=data_transferred,
        data_archived=data_archived,
        checkouts_transferred=checkouts_transferred,
        holds_transferred=holds_transferred,
        fines_transferred=fines_transferred,
        reading_lists_transferred=reading_lists_transferred,
        favorites_transferred=favorites_transferred,
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent and len(user_agent) > 500 else user_agent,
    )
    db.add(merge_audit)

    # Also create a general audit log entry for the PATRON_MERGE action
    audit_log = AuditLog(
        admin_id=staff_user.id,
        target_user_id=primary.id,
        action=AuditAction.PATRON_MERGE,
        details={
            "primary_patron_id": primary.id,
            "secondary_patron_id": secondary.id,
            "secondary_patron_email": secondary.email,
            "secondary_patron_name": f"{secondary.first_name} {secondary.last_name}",
            "checkouts_transferred": checkouts_transferred,
            "holds_transferred": holds_transferred,
            "fines_transferred": fines_transferred,
            "reading_lists_transferred": reading_lists_transferred,
            "favorites_transferred": favorites_transferred,
            "notes_transferred": notes_transferred,
            "patron_status_after_merge": str(primary.patron_status),
        },
        ip_address=ip_address,
        user_agent=user_agent[:500] if user_agent and len(user_agent) > 500 else user_agent,
    )
    db.add(audit_log)

    # Flush to get the audit record ID before deleting the patron
    await db.flush()
    audit_log_id = merge_audit.id

    # =========================================================================
    # Step 8: Delete the secondary patron
    # =========================================================================
    await db.delete(secondary)

    await db.commit()

    logger.info(
        f"Merged patron {secondary.id} into {primary.id} by admin {staff_user.id}",
        extra={
            "primary_id": primary.id,
            "secondary_id": secondary.id,
            "admin_id": staff_user.id,
            "audit_log_id": audit_log_id,
            "checkouts": checkouts_transferred,
            "holds": holds_transferred,
            "fines": fines_transferred,
            "reading_lists": reading_lists_transferred,
            "favorites": favorites_transferred,
        },
    )

    return MergeResponse(
        message="Patron records merged successfully",
        merged_patron_id=primary.id,
        deleted_patron_id=secondary.id,
        checkouts_transferred=checkouts_transferred,
        holds_transferred=holds_transferred,
        fines_transferred=fines_transferred,
        history_transferred=notes_transferred,
        reading_lists_transferred=reading_lists_transferred,
        favorites_transferred=favorites_transferred,
        audit_log_id=audit_log_id,
    )


@router.get("/{patron_id}/merge-history", response_model=MergeHistoryResponse)
async def get_patron_merge_history(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the merge history for a patron.

    Returns all merges where this patron was either:
    - The primary patron (received data from another patron)
    - The secondary patron (was merged into another patron and deleted)

    Note: If a patron was merged as secondary, their ID will no longer exist
    in the users table, but the merge history is preserved.
    """
    # Check if patron exists (for primary patron queries)
    result = await db.execute(select(User).where(User.id == patron_id))
    patron = result.scalar_one_or_none()

    # Get merges where this patron was the primary (kept) patron
    as_primary_result = await db.execute(
        select(PatronMergeAudit)
        .where(PatronMergeAudit.primary_patron_id == patron_id)
        .order_by(PatronMergeAudit.merged_at.desc())
    )
    merges_as_primary = as_primary_result.scalars().all()

    # Get merges where this patron was the secondary (deleted) patron
    as_secondary_result = await db.execute(
        select(PatronMergeAudit)
        .where(PatronMergeAudit.secondary_patron_id == patron_id)
        .order_by(PatronMergeAudit.merged_at.desc())
    )
    merges_as_secondary = as_secondary_result.scalars().all()

    # If no patron exists and no merge history, return 404
    if not patron and not merges_as_primary and not merges_as_secondary:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patron not found and no merge history exists",
        )

    # Batch fetch all staff users referenced in merge audits (avoids N+1 queries)
    all_merges = list(merges_as_primary) + list(merges_as_secondary)
    staff_ids = {m.merged_by_id for m in all_merges if m.merged_by_id}
    staff_by_id = {}
    if staff_ids:
        staff_result = await db.execute(select(User).where(User.id.in_(staff_ids)))
        staff_by_id = {u.id: u for u in staff_result.scalars().all()}

    # Convert to response format
    def audit_to_response(audit: PatronMergeAudit) -> PatronMergeAuditLogResponse:
        # Get merged_by user name from pre-fetched data
        merged_by_name = None
        if audit.merged_by_id and audit.merged_by_id in staff_by_id:
            staff = staff_by_id[audit.merged_by_id]
            merged_by_name = f"{staff.first_name} {staff.last_name}"

        # Extract deleted patron info from archived data
        deleted_patron_email = None
        deleted_patron_name = None
        if audit.data_archived and "user" in audit.data_archived:
            user_data = audit.data_archived["user"]
            deleted_patron_email = user_data.get("email")
            first_name = user_data.get("first_name", "")
            last_name = user_data.get("last_name", "")
            deleted_patron_name = f"{first_name} {last_name}".strip() or None

        return PatronMergeAuditLogResponse(
            id=audit.id,
            merged_at=audit.merged_at,
            merged_by_id=audit.merged_by_id,
            merged_by_name=merged_by_name,
            primary_patron_id=audit.primary_patron_id,
            secondary_patron_id=audit.secondary_patron_id,
            deleted_patron_email=deleted_patron_email,
            deleted_patron_name=deleted_patron_name,
            checkouts_transferred=audit.checkouts_transferred,
            holds_transferred=audit.holds_transferred,
            fines_transferred=audit.fines_transferred,
            reading_lists_transferred=audit.reading_lists_transferred,
            favorites_transferred=audit.favorites_transferred,
            total_items_transferred=audit.total_items_transferred,
            has_archived_data=audit.data_archived is not None,
        )

    as_primary_responses = [audit_to_response(m) for m in merges_as_primary]
    as_secondary_responses = [audit_to_response(m) for m in merges_as_secondary]

    return MergeHistoryResponse(
        patron_id=patron_id,
        as_primary=as_primary_responses,
        as_secondary=as_secondary_responses,
        total_merges=len(merges_as_primary) + len(merges_as_secondary),
    )


@router.get("/merge-audit/{audit_id}")
async def get_merge_audit_details(
    audit_id: int,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the full details of a specific merge audit record.

    Requires admin privileges. Returns the complete archived data
    for potential data recovery purposes.
    """
    audit = await get_or_404(db, PatronMergeAudit, audit_id, "Merge audit record not found")

    # Get merged_by user info
    merged_by_info = None
    if audit.merged_by_id:
        staff_result = await db.execute(select(User).where(User.id == audit.merged_by_id))
        merged_by = staff_result.scalar_one_or_none()
        if merged_by:
            merged_by_info = {
                "id": merged_by.id,
                "name": f"{merged_by.first_name} {merged_by.last_name}",
                "email": merged_by.email,
            }

    # Get primary patron info if they still exist
    primary_patron_info = None
    if audit.primary_patron_id:
        primary_result = await db.execute(select(User).where(User.id == audit.primary_patron_id))
        primary = primary_result.scalar_one_or_none()
        if primary:
            primary_patron_info = {
                "id": primary.id,
                "name": f"{primary.first_name} {primary.last_name}",
                "email": primary.email,
                "library_card": primary.library_card,
            }

    return {
        "id": audit.id,
        "merged_at": audit.merged_at,
        "merged_by": merged_by_info,
        "primary_patron": primary_patron_info,
        "primary_patron_id": audit.primary_patron_id,
        "secondary_patron_id": audit.secondary_patron_id,
        "data_transferred": audit.data_transferred,
        "data_archived": audit.data_archived,
        "checkouts_transferred": audit.checkouts_transferred,
        "holds_transferred": audit.holds_transferred,
        "fines_transferred": audit.fines_transferred,
        "reading_lists_transferred": audit.reading_lists_transferred,
        "favorites_transferred": audit.favorites_transferred,
        "total_items_transferred": audit.total_items_transferred,
        "notes": audit.notes,
        "ip_address": audit.ip_address,
        "created_at": audit.created_at,
    }


# =============================================================================
# Library Card Printing Endpoints
# =============================================================================


@router.get("/{patron_id}/card", response_model=LibraryCardData)
async def get_library_card_data(
    patron_id: int,
    card_type: str = Query("standard", description="Card type: standard, youth, senior"),
    renew_if_expired: bool = Query(
        False, description="Set new expiration if card is expired or not set"
    ),
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get patron data formatted for library card printing.

    If renew_if_expired is True and the patron's card is expired (or has no expiration set),
    the card expiration will be updated to a new date based on the library system's
    card_expiry_years setting.
    """
    from ....core.authorization import calculate_card_expiration_date, get_card_expiry_years

    patron = await get_or_404(db, User, patron_id, "Patron not found")

    # Generate library card number if not exists
    library_card = patron.library_card
    if not library_card:
        # Generate a new library card number
        library_card = f"LSC{patron_id:08d}"
        patron.library_card = library_card

    # Handle card expiration date
    expiration_date = patron.card_expires_at

    # If no expiration set or renew_if_expired flag is set and card is expired
    needs_new_expiration = expiration_date is None or (
        renew_if_expired and patron.is_card_expired()
    )
    if needs_new_expiration:
        # Get card expiry years from library system settings
        expiry_years = await get_card_expiry_years(patron, db)
        expiration_date = calculate_card_expiration_date(expiry_years=expiry_years)
        patron.card_expires_at = expiration_date
        logger.info(
            f"Card expiration set for patron {patron_id} to {expiration_date.isoformat()} "
            f"by staff {staff_user.id}"
        )

    await db.commit()
    await db.refresh(patron)

    return LibraryCardData(
        patron_id=patron.id,
        patron_name=f"{patron.first_name} {patron.last_name}",
        library_card_number=library_card,
        barcode_value=library_card,
        library_name=settings.app_name,
        library_logo_url=routes.url(settings.frontend_url, routes.logo),
        expiration_date=expiration_date,
        card_type=card_type,
        issue_date=datetime.now(timezone.utc),
        patron_photo_url=patron.photo_url,
    )


@router.post(
    "/{patron_id}/card-printed",
    response_model=CardPrintedResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("30/minute")
async def log_card_printed(
    request: Request,
    patron_id: int,
    print_request: CardPrintedRequest,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Log that a library card was printed for this patron.
    Tracks print history for replacement card management.
    """
    await get_or_404(db, User, patron_id, "Patron not found")

    # For now, we'll return a simple response
    # In a full implementation, you would create a CardPrintLog model
    logger.info(
        f"Library card printed for patron {patron_id} by staff {staff_user.id}",
        extra={
            "patron_id": patron_id,
            "staff_id": staff_user.id,
            "card_type": print_request.card_type,
            "is_replacement": print_request.is_replacement,
            "reason": print_request.reason,
        },
    )

    return CardPrintedResponse(
        message="Card print logged successfully",
        print_count=1,  # Would query actual count from database
        print_history=[
            CardPrintHistory(
                id=1,
                printed_at=datetime.now(timezone.utc),
                card_type=print_request.card_type,
                is_replacement=print_request.is_replacement,
                reason=print_request.reason,
                printed_by_id=staff_user.id,
                printed_by_name=f"{staff_user.first_name} {staff_user.last_name}",
            )
        ],
    )


# =============================================================================
# Account Settings Endpoints
# =============================================================================


@router.get("/{patron_id}/settings", response_model=AccountSettingsResponse)
async def get_patron_account_settings(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Get account settings for a patron."""
    await get_or_404(db, User, patron_id, "Patron not found")

    # Get notification preferences
    prefs_result = await db.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == patron_id)
    )
    prefs = prefs_result.scalar_one_or_none()

    # Count saved searches and reading lists
    # These would come from their respective models
    saved_searches_count = 0
    reading_lists_count = 0

    return AccountSettingsResponse(
        patron_id=patron_id,
        notification_email=prefs.email_enabled if prefs else True,
        notification_sms=prefs.sms_enabled if prefs else False,
        notification_hold_ready=prefs.hold_ready_enabled if prefs else True,
        notification_due_reminder=prefs.due_reminder_enabled if prefs else True,
        notification_overdue=prefs.overdue_enabled if prefs else True,
        checkout_limit=25,  # Would come from patron settings or default
        hold_limit=10,
        saved_searches_count=saved_searches_count,
        reading_lists_count=reading_lists_count,
    )


@router.put("/{patron_id}/settings", response_model=AccountSettingsResponse)
@limiter.limit("30/minute")
async def update_patron_account_settings(
    request: Request,
    patron_id: int,
    settings_update: AccountSettingsUpdate,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update account settings for a patron on their behalf."""
    await get_or_404(db, User, patron_id, "Patron not found")

    # Get or create notification preferences
    prefs_result = await db.execute(
        select(NotificationPreferences).where(NotificationPreferences.user_id == patron_id)
    )
    prefs = prefs_result.scalar_one_or_none()

    if not prefs:
        prefs = NotificationPreferences(user_id=patron_id)
        db.add(prefs)

    # Update notification preferences
    if settings_update.notification_email is not None:
        prefs.email_enabled = settings_update.notification_email
    if settings_update.notification_sms is not None:
        prefs.sms_enabled = settings_update.notification_sms
    if settings_update.notification_hold_ready is not None:
        prefs.hold_ready_enabled = settings_update.notification_hold_ready
    if settings_update.notification_due_reminder is not None:
        prefs.due_reminder_enabled = settings_update.notification_due_reminder
    if settings_update.notification_overdue is not None:
        prefs.overdue_enabled = settings_update.notification_overdue

    await db.commit()

    logger.info(
        f"Account settings updated for patron {patron_id} by staff {staff_user.id}",
        extra={"patron_id": patron_id, "staff_id": staff_user.id},
    )

    return await get_patron_account_settings(patron_id, staff_user, db)


# =============================================================================
# Deceased Patron Handling Endpoints
# =============================================================================


@router.post("/{patron_id}/mark-deceased", response_model=DeceasedPatronResponse)
@limiter.limit("10/minute")
async def mark_patron_deceased(
    request: Request,
    patron_id: int,
    deceased_request: MarkDeceasedRequest,
    staff_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark a patron as deceased.

    This is a sensitive operation that:
    - Changes patron status to DECEASED
    - Blocks all circulation operations
    - Preserves account data for records
    - Flags outstanding items/fines for estate follow-up
    - Optionally stores estate contact information
    - Sends notification to estate contact if email provided

    Requires admin privileges due to the sensitive nature of this operation.
    """
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    if patron.role not in [UserRole.PATRON, UserRole.CHILD, UserRole.BOOKMOBILE, UserRole.HOMEBOND]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only mark patron accounts as deceased (not staff accounts)",
        )

    if patron.patron_status == PatronStatus.DECEASED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Patron is already marked as deceased"
        )

    # Check for outstanding checkouts
    checkout_result = await db.execute(
        select(Checkout).where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )
    outstanding_checkouts = checkout_result.scalars().all()

    # Check for outstanding holds
    hold_result = await db.execute(
        select(Hold).where(
            Hold.user_id == patron_id, Hold.status.in_([HoldStatus.pending, HoldStatus.ready])
        )
    )
    outstanding_holds = hold_result.scalars().all()

    # Calculate outstanding fines
    fines_result = await db.execute(
        select(func.sum(Fine.amount - Fine.amount_paid)).where(
            Fine.user_id == patron_id, Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
    )
    outstanding_fines_amount = fines_result.scalar() or Decimal("0.00")

    # Determine if estate follow-up is required
    estate_followup_required = len(outstanding_checkouts) > 0 or outstanding_fines_amount > Decimal(
        "0.00"
    )

    # Update patron record
    patron.patron_status = PatronStatus.DECEASED
    patron.is_active = False  # Also set is_active for backwards compatibility

    if deceased_request.date_of_death:
        patron.date_of_death = deceased_request.date_of_death.date()

    patron.deceased_marked_at = datetime.now(timezone.utc)
    patron.deceased_marked_by_id = staff_user.id

    # Store estate contact information
    if deceased_request.estate_contact_name:
        patron.estate_contact_name = deceased_request.estate_contact_name
    if deceased_request.estate_contact_email:
        patron.estate_contact_email = deceased_request.estate_contact_email
    if deceased_request.estate_contact_phone:
        patron.estate_contact_phone = deceased_request.estate_contact_phone

    patron.estate_followup_required = estate_followup_required
    if deceased_request.notes:
        patron.estate_followup_notes = deceased_request.notes

    # Cancel any pending/ready holds (they can no longer be fulfilled)
    for hold in outstanding_holds:
        hold.status = HoldStatus.cancelled

    # Send notification to estate contact if email provided and there are outstanding items/fines
    notification_sent = False
    if deceased_request.estate_contact_email and estate_followup_required:
        try:
            # Build list of outstanding items
            items_list = ""
            for checkout in outstanding_checkouts:
                item_result = await db.execute(
                    select(CatalogItem).where(CatalogItem.id == checkout.item_id)
                )
                item = item_result.scalar_one_or_none()
                if item:
                    items_list += f"<li>{item.title} by {item.author} (Due: {checkout.due_date.strftime('%B %d, %Y')})</li>"

            subject = f"Library Account Notice - {patron.full_name}"
            html_content = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: {COLORS["heading"]};">Library Account Notice</h2>

                <p>Dear {deceased_request.estate_contact_name or "Estate Representative"},</p>

                <p>We are writing regarding the library account of <strong>{patron.full_name}</strong>.</p>

                <p>Our records show the following outstanding items/balances that require attention:</p>

                {"<h3>Outstanding Items:</h3><ul>" + items_list + "</ul>" if items_list else ""}

                {"<h3>Outstanding Balance:</h3><p>$" + str(outstanding_fines_amount) + "</p>" if outstanding_fines_amount > 0 else ""}

                <p>Please contact our circulation desk at your convenience to discuss how to
                resolve these matters. We understand this is a difficult time and are here to help.</p>

                <hr style="border: none; border-top: 1px solid {COLORS["divider"]}; margin: 30px 0;">
                <p style="color: #888; font-size: 12px;">
                    {settings.app_name}<br>
                    This is an automated message. Please do not reply to this email.
                </p>
            </div>
            """

            notification_sent = await send_email(
                to_email=deceased_request.estate_contact_email,
                subject=subject,
                html_content=html_content,
            )
        except Exception as e:  # noqa: BLE001  # best-effort estate notification email
            logger.error(f"Failed to send estate notification: {e}")

    await db.commit()

    logger.info(
        f"Patron {patron_id} marked as deceased by staff {staff_user.id}",
        extra={
            "patron_id": patron_id,
            "staff_id": staff_user.id,
            "outstanding_checkouts": len(outstanding_checkouts),
            "outstanding_fines": float(outstanding_fines_amount),
            "estate_followup_required": estate_followup_required,
        },
    )

    return DeceasedPatronResponse(
        message="Patron has been marked as deceased. Account is now locked.",
        patron_id=patron.id,
        patron_name=patron.full_name,
        date_of_death=patron.date_of_death,
        outstanding_checkouts=len(outstanding_checkouts),
        outstanding_holds=len(outstanding_holds),
        outstanding_fines_amount=outstanding_fines_amount,
        estate_followup_required=estate_followup_required,
        estate_contact_name=patron.estate_contact_name,
        estate_contact_email=patron.estate_contact_email,
        notification_sent=notification_sent,
    )


@router.get("/{patron_id}/estate-outstanding", response_model=EstateOutstandingItemsResponse)
async def get_estate_outstanding_items(
    patron_id: int,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Get outstanding items and fines for a deceased patron's estate.

    Returns detailed information about:
    - Outstanding checkouts (items that need to be returned)
    - Outstanding fines (amounts owed)
    - Estate contact information

    This helps staff manage estate follow-up and coordinate with family/executors.
    """
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    if patron.patron_status != PatronStatus.DECEASED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for deceased patron accounts",
        )

    # Get outstanding checkouts with item details
    checkout_result = await db.execute(
        select(Checkout, CatalogItem)
        .join(CatalogItem, Checkout.item_id == CatalogItem.id)
        .where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )
    checkouts = []
    for checkout, item in checkout_result.all():
        checkouts.append(
            {
                "checkout_id": checkout.id,
                "item_id": item.id,
                "title": item.title,
                "author": item.author,
                "barcode": item.barcode,
                "checked_out_at": checkout.checked_out_at.isoformat()
                if checkout.checked_out_at
                else None,
                "due_date": checkout.due_date.isoformat() if checkout.due_date else None,
                "status": str(checkout.status),
            }
        )

    # Get outstanding fines with details
    fines_result = await db.execute(
        select(Fine).where(
            Fine.user_id == patron_id, Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
    )
    fines = []
    total_fines = Decimal("0.00")
    for fine in fines_result.scalars().all():
        amount_due = fine.amount - fine.amount_paid
        total_fines += amount_due
        fines.append(
            {
                "fine_id": fine.id,
                "type": str(fine.fine_type) if fine.fine_type else "other",
                "amount": float(fine.amount),
                "amount_paid": float(fine.amount_paid),
                "amount_due": float(amount_due),
                "description": fine.description,
                "created_at": fine.created_at.isoformat() if fine.created_at else None,
            }
        )

    return EstateOutstandingItemsResponse(
        patron_id=patron.id,
        patron_name=patron.full_name,
        date_of_death=patron.date_of_death,
        estate_contact_name=patron.estate_contact_name,
        estate_contact_email=patron.estate_contact_email,
        estate_contact_phone=patron.estate_contact_phone,
        checkouts=checkouts,
        fines=fines,
        total_fines_amount=total_fines,
        notes=patron.estate_followup_notes,
    )


@router.put("/{patron_id}/estate-contact")
@limiter.limit("30/minute")
async def update_estate_contact(
    request: Request,
    patron_id: int,
    estate_contact_name: Optional[str] = None,
    estate_contact_email: Optional[str] = None,
    estate_contact_phone: Optional[str] = None,
    notes: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Update estate contact information for a deceased patron.

    Allows staff to add or update contact information for the estate
    as new information becomes available.
    """
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    if patron.patron_status != PatronStatus.DECEASED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for deceased patron accounts",
        )

    # Update estate contact information
    if estate_contact_name is not None:
        patron.estate_contact_name = estate_contact_name
    if estate_contact_email is not None:
        patron.estate_contact_email = estate_contact_email
    if estate_contact_phone is not None:
        patron.estate_contact_phone = estate_contact_phone
    if notes is not None:
        patron.estate_followup_notes = notes

    await db.commit()

    logger.info(
        f"Estate contact updated for deceased patron {patron_id} by staff {staff_user.id}",
        extra={"patron_id": patron_id, "staff_id": staff_user.id},
    )

    return {
        "message": "Estate contact information updated",
        "patron_id": patron.id,
        "estate_contact_name": patron.estate_contact_name,
        "estate_contact_email": patron.estate_contact_email,
        "estate_contact_phone": patron.estate_contact_phone,
    }


@router.post("/{patron_id}/estate-resolved")
@limiter.limit("10/minute")
async def mark_estate_resolved(
    request: Request,
    patron_id: int,
    resolution_notes: Optional[str] = None,
    staff_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Mark estate follow-up as resolved for a deceased patron.

    Use this when all outstanding items have been returned and
    fines have been settled or waived.
    """
    # Get patron
    patron = await get_or_404(db, User, patron_id, "Patron not found")

    if patron.patron_status != PatronStatus.DECEASED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint is only for deceased patron accounts",
        )

    # Check if there are still outstanding items/fines
    checkout_count = await db.execute(
        select(func.count(Checkout.id)).where(
            Checkout.user_id == patron_id,
            Checkout.status.in_([CheckoutStatus.active, CheckoutStatus.overdue]),
        )
    )
    outstanding_checkouts = checkout_count.scalar() or 0

    fines_result = await db.execute(
        select(func.sum(Fine.amount - Fine.amount_paid)).where(
            Fine.user_id == patron_id, Fine.status.in_([FineStatus.unpaid, FineStatus.partial])
        )
    )
    outstanding_fines = fines_result.scalar() or Decimal("0.00")

    if outstanding_checkouts > 0 or outstanding_fines > Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot mark as resolved. Outstanding items: {outstanding_checkouts}, Outstanding fines: ${outstanding_fines}",
        )

    # Mark as resolved
    patron.estate_followup_required = False
    if resolution_notes:
        existing_notes = patron.estate_followup_notes or ""
        patron.estate_followup_notes = f"{existing_notes}\n\n[RESOLVED {datetime.now(timezone.utc).strftime('%Y-%m-%d')} by {staff_user.full_name}] {resolution_notes}".strip()

    await db.commit()

    logger.info(
        f"Estate followup resolved for deceased patron {patron_id} by staff {staff_user.id}",
        extra={"patron_id": patron_id, "staff_id": staff_user.id},
    )

    return {
        "message": "Estate follow-up marked as resolved",
        "patron_id": patron.id,
        "estate_followup_required": False,
    }
