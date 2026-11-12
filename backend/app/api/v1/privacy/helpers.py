# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Privacy helper functions (non-endpoint utilities)."""

import hashlib
from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.config import get_settings
from ....core.email import send_email
from ....core.frontend_routes import routes
from ....models.audit_log import AuditAction, AuditLog
from ....models.circulation import Checkout, Hold
from ....models.event_registration import EventRegistration
from ....models.favorite import Favorite
from ....models.fine import Fine
from ....models.reading import ReadingLog, ReadingStats
from ....models.reading_list import ReadingList
from ....models.ai_agents import AgentConversation
from ....models.ebook_checkout_log import EbookCheckoutLog
from ....models.user import DeletedEmail, PasswordHistory, RefreshToken, User
from ....models.privacy_ledger import ConsentRecord, DataCorrectionLog, DataSharingLog

from .schemas import DeletionEligibilityResponse

settings = get_settings()
logger = get_logger(__name__)

# Constants
DELETION_GRACE_PERIOD_DAYS = 30
EMAIL_BLOCK_PERIOD_DAYS = 90


def hash_email_for_block(email: str) -> str:
    # Use a consistent salt from settings for deterministic hashing
    salt = settings.secret_key[:16] if hasattr(settings, 'secret_key') else "lsc-email-salt"
    salted = f"{salt}:{email.lower().strip()}"
    return hashlib.sha256(salted.encode()).hexdigest()


async def check_email_blocked(db: AsyncSession, email: str) -> tuple[bool, Optional[datetime]]:
    email_hash = hash_email_for_block(email)
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(DeletedEmail).where(
            and_(
                DeletedEmail.email_hash == email_hash,
                DeletedEmail.block_expires_at > now,
            )
        )
    )
    blocked = result.scalar_one_or_none()

    if blocked:
        return True, blocked.block_expires_at
    return False, None


async def record_deleted_email(
    db: AsyncSession,
    email: str,
    deletion_type: str,
    staff_id: Optional[int] = None,
) -> None:
    email_hash = hash_email_for_block(email)
    now = datetime.now(timezone.utc)

    # Check if already exists (shouldn't happen, but be safe)
    result = await db.execute(
        select(DeletedEmail).where(DeletedEmail.email_hash == email_hash)
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update expiry
        existing.block_expires_at = now + timedelta(days=EMAIL_BLOCK_PERIOD_DAYS)
        existing.deleted_at = now
        existing.deletion_type = deletion_type
        existing.processed_by_staff_id = staff_id
    else:
        # Create new record
        deleted_email = DeletedEmail(
            email_hash=email_hash,
            deleted_at=now,
            block_expires_at=now + timedelta(days=EMAIL_BLOCK_PERIOD_DAYS),
            deletion_type=deletion_type,
            processed_by_staff_id=staff_id,
        )
        db.add(deleted_email)


async def create_audit_log(
    db: AsyncSession,
    action: AuditAction,
    admin_id: Optional[int] = None,
    target_user_id: Optional[int] = None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    audit_entry = AuditLog(
        admin_id=admin_id,
        target_user_id=target_user_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(audit_entry)


async def check_deletion_eligibility(
    db: AsyncSession, user: User
) -> DeletionEligibilityResponse:
    blockers = []

    # Check for unpaid fines
    fines_result = await db.execute(
        select(Fine).where(
            and_(
                Fine.user_id == user.id,
                Fine.amount > Fine.amount_paid,
            )
        )
    )
    unpaid_fines = fines_result.scalars().all()
    total_owed = sum(float(f.amount - f.amount_paid) for f in unpaid_fines) if unpaid_fines else 0

    # Check for active checkouts
    active_checkouts_result = await db.execute(
        select(Checkout).where(
            and_(
                Checkout.user_id == user.id,
                Checkout.status.in_(["active", "overdue"]),
            )
        )
    )
    active_checkouts = active_checkouts_result.scalars().all()

    # Check for child accounts
    children_result = await db.execute(
        select(User).where(User.parent_guardian_id == user.id)
    )
    children = children_result.scalars().all()

    # Build blockers list
    if unpaid_fines:
        blockers.append(f"Unpaid fines: ${total_owed:.2f}")
    if active_checkouts:
        blockers.append(f"Active checkouts: {len(active_checkouts)} item(s) not returned")
    if children:
        blockers.append(f"Child accounts: {len(children)} linked account(s)")

    return DeletionEligibilityResponse(
        eligible=len(blockers) == 0,
        has_unpaid_fines=len(unpaid_fines) > 0,
        unpaid_fine_amount=total_owed if unpaid_fines else None,
        has_active_checkouts=len(active_checkouts) > 0,
        active_checkout_count=len(active_checkouts),
        has_child_accounts=len(children) > 0,
        child_account_count=len(children),
        deletion_pending=user.deletion_requested_at is not None,
        deletion_scheduled_for=user.deletion_scheduled_for.isoformat() if user.deletion_scheduled_for else None,
        blockers=blockers,
    )


async def _perform_user_deletion(db: AsyncSession, user_id: int) -> None:
    now = datetime.now(timezone.utc)

    # 1. Delete refresh tokens and password history (these are session tokens, safe to hard-delete)
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.execute(delete(PasswordHistory).where(PasswordHistory.user_id == user_id))

    # 2. Hard-delete Favorites (user preference records - completely remove)
    await db.execute(delete(Favorite).where(Favorite.user_id == user_id))

    # 3. Hard-delete ReadingLists (user-created lists - completely remove)
    # Note: ListItem records are deleted via cascade due to ForeignKey ondelete="CASCADE"
    await db.execute(delete(ReadingList).where(ReadingList.user_id == user_id))

    # 4. Hard-delete ReadingLogs (activity records - completely remove)
    await db.execute(delete(ReadingLog).where(ReadingLog.user_id == user_id))

    # 5. Hard-delete ReadingStats (gamification data - completely remove)
    await db.execute(delete(ReadingStats).where(ReadingStats.user_id == user_id))

    # 6. Cancel active holds (soft-delete: mark as cancelled, preserve records for audit)
    await db.execute(
        update(Hold)
        .where(Hold.user_id == user_id)
        .values(status="cancelled")
    )

    # 7. Checkout history: KEEP user_id pointing at the soft-deleted row.
    # checkouts.user_id is NOT NULL with ondelete=RESTRICT by design (never
    # orphan circulation records); anonymization happens in step 14, which
    # scrubs all PII from the user row itself. Setting user_id=None here
    # raised NotNullViolation and rolled back the entire deletion for any
    # patron with checkout history.

    # 8. Anonymize fine records (keep for financial/legal records)
    await db.execute(
        update(Fine)
        .where(Fine.user_id == user_id)
        .values(user_id=None)
    )

    # 9. Anonymize event registrations (replace patron_email with anonymized value)
    # Use a hash of the user_id to create a unique but anonymous email address
    anonymous_email = f"deleted-{hashlib.sha256(str(user_id).encode()).hexdigest()[:16]}@anonymous.local"
    await db.execute(
        update(EventRegistration)
        .where(EventRegistration.patron_email.in_(
            select(User.email).where(User.id == user_id)
        ))
        .values(patron_email=anonymous_email)
    )

    # 10. Anonymize audit logs (keep the log but remove user references)
    await db.execute(
        update(AuditLog)
        .where(AuditLog.target_user_id == user_id)
        .values(target_user_id=None)
    )
    await db.execute(
        update(AuditLog)
        .where(AuditLog.admin_id == user_id)
        .values(admin_id=None)
    )

    # 11. Anonymize consent records, data sharing logs, and correction logs
    # (keep the records for compliance but remove user link)
    await db.execute(
        update(ConsentRecord)
        .where(ConsentRecord.user_id == user_id)
        .values(user_id=None)
    )
    await db.execute(
        update(DataSharingLog)
        .where(DataSharingLog.user_id == user_id)
        .values(user_id=None)
    )
    await db.execute(
        update(DataCorrectionLog)
        .where(DataCorrectionLog.user_id == user_id)
        .values(user_id=None)
    )

    # 12. Anonymize AI conversation logs (strip content but keep row for analytics)
    await db.execute(
        update(AgentConversation)
        .where(AgentConversation.user_id == user_id)
        .values(
            user_message="[deleted]",
            agent_response="[deleted]",
            conversation_context=None,
            detected_intent=None,
            feedback_note=None,
            user_id=None,
        )
    )

    # 13. Ebook checkout logs: strip potentially-identifying metadata but KEEP
    # user_id — the column is NOT NULL (same class as checkouts, step 7); the
    # soft-deleted user row in step 14 is what severs the identity link.
    await db.execute(
        update(EbookCheckoutLog)
        .where(EbookCheckoutLog.user_id == user_id)
        .values(metadata_=None)
    )

    # 14. Soft-delete the user record: clear PII but keep the row for
    # referential integrity. scrub_user_pii clears the FULL PII column set
    # (phone/address/DOB/contacts/etc.), not just email+name — shared with
    # the retention deletion path so the two can't drift apart again.
    from app.services.data_retention_service import scrub_user_pii

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        scrub_user_pii(user, now=now)


async def send_parental_consent_email(
    parent_email: str,
    child_name: str,
    consent_token: str,
) -> None:
    consent_url = f"{routes.url(settings.frontend_url, routes.consent)}?token={consent_token}"

    subject = f"Parental Consent Required - Library Account for {child_name}"
    body = f"""
Hello,

A library account has been created for {child_name} at {settings.app_name}.

Under the Children's Online Privacy Protection Act (COPPA), we require parental consent before activating accounts for children under 13.

Please click the link below to review and provide consent:

{consent_url}

This link will expire in 7 days.

If you did not expect this email or have questions, please contact the library at (613) 555-1234.

Thank you,
{settings.app_name}
"""

    await send_email(
        to_email=parent_email,
        subject=subject,
        html_content=f"<pre style='font-family: Arial, sans-serif;'>{body}</pre>",
    )
