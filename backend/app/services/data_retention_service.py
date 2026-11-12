# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import hashlib
import secrets
from app.core.logging import get_logger
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import send_deletion_complete_email
from ..models.attendance import AttendanceCheckIn, AttendanceSession
from ..models.audit_log import AuditAction, AuditLog
from ..models.cipa_compliance import ComputerSession
from ..models.circulation import Checkout, Hold
from ..models.journey_instrumentation import JourneyEvent
from ..models.book_challenge import BookChallenge
from ..models.ai_agents import AgentConversation
from ..models.ai_guardrails import AIUsageLog
from ..models.computer import ComputerReservation
from ..models.equipment import EquipmentCheckout
from ..models.event import Event
from ..models.event_registration import EventRegistration
from ..models.event_review import EventReview
from ..models.favorite import Favorite
from ..models.fine import Fine
from ..models.reading import ReadingLog, ReadingLogEntry, ReadingRegistration, ReadingStats
from ..models.reading_list import ReadingList
from ..models.privacy_ledger import ConsentRecord, DataCorrectionLog, DataSharingLog
from ..models.room import RoomQueue, RoomReservation, RoomWaitlist
from ..models.user import DeletedEmail, PasswordHistory, RefreshToken, User, UserRole
from ..models.database_subscription import DatabaseAccessLog
from ..models.staff_safety import DataRetentionPolicy
from ..models.law_enforcement_request import LawEnforcementRequest, WorkflowStatus
from ..models.compliance_tracking import COPPACompliance

logger = get_logger(__name__)
settings = get_settings()

# Retention periods (configurable)
REFRESH_TOKEN_CLEANUP_DAYS = 30  # Remove expired/revoked tokens after 30 days
PASSWORD_HISTORY_KEEP_COUNT = 5  # Keep only last 5 passwords
CONSENT_TOKEN_CLEANUP_DAYS = 30  # Remove expired consent tokens after 30 days
INACTIVE_ACCOUNT_YEARS = 3  # Archive accounts inactive for 3 years
CHECKOUT_ANONYMIZE_YEARS = 7  # Anonymize checkout records after 7 years
EMAIL_BLOCK_PERIOD_DAYS = 90  # Re-registration block period
ACCESS_LOG_RETENTION_DAYS = int(os.getenv("DATABASE_ACCESS_LOG_RETENTION_DAYS", "365"))
JOURNEY_EVENT_RETENTION_DAYS = 90
AI_CONVERSATION_RETENTION_DAYS = 90  # Delete patron chatbot transcripts after 90 days
AI_USAGE_LOG_RETENTION_DAYS = 90  # Delete AI tool usage logs after 90 days
AI_USAGE_LOG_TEXT_SCRUB_DAYS = 30  # Null prompt/response text after 30 days; keep metadata
CHALLENGER_PII_RETENTION_MONTHS = (
    12  # null challenger name/contact 12 months after a challenge resolves
)
DEFAULT_MINOR_RETENTION_MONTHS = (
    12  # under-18 minor-retention default if no COPPACompliance record exists
)


def hash_email_for_block(email: str) -> str:
    salt = settings.secret_key[:16] if hasattr(settings, "secret_key") else "lsc-email-salt"
    salted = f"{salt}:{email.lower().strip()}"
    return hashlib.sha256(salted.encode()).hexdigest()


async def _get_minor_retention_months(db: AsyncSession) -> int:
    result = await db.execute(select(COPPACompliance.minor_data_retention_months).limit(1))
    value = result.scalar_one_or_none()
    return value if value is not None else DEFAULT_MINOR_RETENTION_MONTHS


async def _get_minor_patron_ids(db: AsyncSession) -> set[int]:
    result = await db.execute(
        select(User.id).where(
            and_(
                User.is_active == True,
                or_(
                    User.role == UserRole.CHILD.value,
                    # date_of_birth is encrypted, so classify minors from the
                    # maintained under_18 flag rather than a SQL date comparison.
                    User.under_18.is_(True),
                ),
            )
        )
    )
    return {row[0] for row in result.all()}


async def _get_minor_patron_emails(db: AsyncSession, minor_ids: set[int]) -> set[str]:
    if not minor_ids:
        return set()
    # Email is encrypted: select the column (auto-decrypted) and lower app-side.
    result = await db.execute(select(User.email).where(User.id.in_(minor_ids)))
    return {row[0].lower() for row in result.all() if row[0]}


async def cleanup_expired_refresh_tokens(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=REFRESH_TOKEN_CLEANUP_DAYS)

    result = await db.execute(
        delete(RefreshToken).where(
            or_(
                # Expired tokens past grace period
                and_(
                    RefreshToken.expires_at.isnot(None),
                    RefreshToken.expires_at < cutoff,
                ),
                # Revoked tokens past grace period
                and_(
                    RefreshToken.revoked_at.isnot(None),
                    RefreshToken.revoked_at < cutoff,
                ),
            )
        )
    )

    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} expired/revoked refresh tokens")

    return deleted_count


async def cleanup_excess_password_history(db: AsyncSession) -> int:
    # Bulk delete excess password history using a window function subquery
    from sqlalchemy import func as sa_func, over

    # Subquery: rank each entry per user by recency
    ranked = (
        select(
            PasswordHistory.id,
            sa_func.row_number()
            .over(
                partition_by=PasswordHistory.user_id,
                order_by=PasswordHistory.created_at.desc(),
            )
            .label("rn"),
        )
    ).subquery()

    # Find IDs to delete (rank > keep count)
    ids_to_delete = select(ranked.c.id).where(ranked.c.rn > PASSWORD_HISTORY_KEEP_COUNT)

    result = await db.execute(delete(PasswordHistory).where(PasswordHistory.id.in_(ids_to_delete)))
    total_deleted = result.rowcount

    if total_deleted > 0:
        logger.info(f"Cleaned up {total_deleted} excess password history entries")

    return total_deleted


async def cleanup_expired_consent_tokens(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=CONSENT_TOKEN_CLEANUP_DAYS)

    result = await db.execute(
        update(User)
        .where(
            and_(
                User.parental_consent_token.isnot(None),
                User.parental_consent_token_expires.isnot(None),
                User.parental_consent_token_expires < cutoff,
            )
        )
        .values(
            parental_consent_token=None,
            parental_consent_token_expires=None,
        )
    )

    cleared_count = result.rowcount
    if cleared_count > 0:
        logger.info(f"Cleared {cleared_count} expired parental consent tokens")

    return cleared_count


async def cleanup_expired_email_blocks(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)

    result = await db.execute(delete(DeletedEmail).where(DeletedEmail.block_expires_at < now))

    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} expired email re-registration blocks")

    return deleted_count


async def cleanup_old_journey_events(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=JOURNEY_EVENT_RETENTION_DAYS)

    result = await db.execute(delete(JourneyEvent).where(JourneyEvent.event_timestamp < cutoff))

    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(
            f"Deleted {deleted_count} journey events older than {JOURNEY_EVENT_RETENTION_DAYS} days"
        )

    return deleted_count


async def cleanup_old_agent_conversations(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=AI_CONVERSATION_RETENTION_DAYS)
    result = await db.execute(
        delete(AgentConversation).where(AgentConversation.created_at < cutoff)
    )
    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(
            f"Deleted {deleted_count} agent conversations older than {AI_CONVERSATION_RETENTION_DAYS} days"
        )
    return deleted_count


async def cleanup_ai_usage_logs(db: AsyncSession) -> int:
    now = datetime.now(timezone.utc)
    # Scrub the sensitive prompt/response text early but keep the metadata row
    # (tokens, timing, guardrails) for the audit trail.
    scrub_cutoff = now - timedelta(days=AI_USAGE_LOG_TEXT_SCRUB_DAYS)
    scrub_result = await db.execute(
        update(AIUsageLog)
        .where(and_(AIUsageLog.created_at < scrub_cutoff, AIUsageLog.prompt_preview.is_not(None)))
        .values(prompt_preview=None, response_preview=None, system_prompt_used=None)
    )
    if scrub_result.rowcount > 0:
        logger.info(
            f"Scrubbed text from {scrub_result.rowcount} AI usage logs older than {AI_USAGE_LOG_TEXT_SCRUB_DAYS} days"
        )

    delete_cutoff = now - timedelta(days=AI_USAGE_LOG_RETENTION_DAYS)
    result = await db.execute(delete(AIUsageLog).where(AIUsageLog.created_at < delete_cutoff))
    deleted_count = result.rowcount
    if deleted_count > 0:
        logger.info(
            f"Deleted {deleted_count} AI usage logs older than {AI_USAGE_LOG_RETENTION_DAYS} days"
        )
    return deleted_count


async def process_scheduled_deletions(
    db: AsyncSession, *, held_patron_ids: set[int] = frozenset()
) -> int:
    now = datetime.now(timezone.utc)

    # Find accounts scheduled for deletion
    result = await db.execute(
        select(User).where(
            and_(
                User.deletion_scheduled_for.isnot(None),
                User.deletion_scheduled_for <= now,
            )
        )
    )
    users_to_delete = result.scalars().all()

    deleted_count = 0

    for user in users_to_delete:
        try:
            # Skip patrons with active litigation holds
            if user.id in held_patron_ids:
                logger.warning(
                    "Skipping deletion of user %d - active litigation hold",
                    user.id,
                )
                continue

            # Check if user still has unpaid fines or active checkouts
            # (They may have accrued during the grace period)
            fines_result = await db.execute(
                select(Fine).where(
                    Fine.user_id == user.id,
                    Fine.amount > Fine.amount_paid,
                )
            )
            if fines_result.scalars().first():
                logger.warning(
                    f"Skipping deletion of user {user.id} - unpaid fines acquired during grace period"
                )
                # Clear the deletion request so staff can review
                user.deletion_requested_at = None
                user.deletion_scheduled_for = None
                continue

            checkouts_result = await db.execute(
                select(Checkout).where(
                    Checkout.user_id == user.id,
                    Checkout.status.in_(["active", "overdue"]),
                )
            )
            if checkouts_result.scalars().first():
                logger.warning(f"Skipping deletion of user {user.id} - active checkouts")
                # Clear the deletion request so staff can review
                user.deletion_requested_at = None
                user.deletion_scheduled_for = None
                continue

            # Store info needed for post-deletion tasks
            user_email = user.email
            user_first_name = user.first_name
            user_role = str(user.role)
            account_age = (now - user.created_at).days if user.created_at else None

            # Record email for 90-day re-registration block
            await _record_deleted_email(
                db=db,
                email=user_email,
                deletion_type="scheduled",
            )

            # Create anonymized audit log entry BEFORE deleting user
            audit_entry = AuditLog(
                admin_id=None,  # System automated
                target_user_id=None,  # Anonymized - don't reference deleted user
                action=AuditAction.GDPR_DELETION_COMPLETED,
                details={
                    "deletion_type": "scheduled_automatic",
                    "user_role": user_role,
                    "account_age_days": account_age,
                    "grace_period_completed": True,
                },
                ip_address=None,
                user_agent="DataRetentionService/1.0",
            )
            db.add(audit_entry)

            # Perform deletion
            await _delete_user_data(db, user.id)

            deleted_count += 1
            logger.info(f"Processed scheduled deletion for user {user.id}")

            # Send final confirmation email (best effort, after commit)
            try:
                await send_deletion_complete_email(user_email, user_first_name)
            except Exception as email_error:  # noqa: BLE001 - best-effort post-deletion email; failure must not undo the completed deletion
                logger.warning(f"Failed to send deletion confirmation email: {email_error}")

        except Exception as e:  # noqa: BLE001 - per-iteration boundary: one user's deletion failure must not crash the batch over all users
            logger.error(f"Error processing deletion for user {user.id}: {e}")
            continue

    return deleted_count


async def _record_deleted_email(
    db: AsyncSession,
    email: str,
    deletion_type: str,
    staff_id: Optional[int] = None,
) -> None:
    email_hash = hash_email_for_block(email)
    now = datetime.now(timezone.utc)

    # Check if already exists
    result = await db.execute(select(DeletedEmail).where(DeletedEmail.email_hash == email_hash))
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


def scrub_user_pii(user: User, *, now: datetime) -> None:
    """Tombstone a user row in place: clear every PII column but keep the row
    so NOT NULL / RESTRICT circulation FKs stay intact. Blind-index hashes
    (email/name/phone) and the under-18 flag recompute automatically on flush
    via the User event listeners. Shared by the GDPR deletion path
    (api/v1/privacy/helpers.py) and retention deletion below.
    """
    user.email = f"deleted-{user.id}@deleted.local"
    user.set_name("Deleted", "User")
    user.set_phone(None)
    user.address = None
    user.address_line1 = None
    user.address_line2 = None
    user.city = None
    user.state = None
    user.zip_code = None
    user.date_of_birth = None
    user.emergency_contact_name = None
    user.emergency_contact_phone = None
    user.pronouns = None
    user.accessibility_needs = None
    user.photo_url = None
    user.custom_fields = None
    user.parental_consent_email = None
    user.recovery_email = None
    user.estate_contact_name = None
    user.estate_contact_email = None
    user.estate_contact_phone = None
    user.estate_followup_notes = None
    # Random token so the hash can never match a legitimate password.
    user.password_hash = secrets.token_urlsafe(32)
    user.is_active = False
    user.deletion_requested_at = now


async def _delete_user_data(db: AsyncSession, user_id: int) -> None:
    # Look up the user's email so we can clean up tables keyed on patron_email
    # rather than user_id (events, reviews use email-only identifiers).
    email_result = await db.execute(select(User.email).where(User.id == user_id))
    user_email = email_result.scalar_one_or_none()

    # Delete tokens and history
    await db.execute(delete(RefreshToken).where(RefreshToken.user_id == user_id))
    await db.execute(delete(PasswordHistory).where(PasswordHistory.user_id == user_id))

    # Cancel and delete holds
    await db.execute(update(Hold).where(Hold.user_id == user_id).values(status="cancelled"))
    await db.execute(delete(Hold).where(Hold.user_id == user_id))

    # Delete user content
    await db.execute(delete(Favorite).where(Favorite.user_id == user_id))
    await db.execute(delete(ReadingList).where(ReadingList.user_id == user_id))
    await db.execute(delete(ReadingLog).where(ReadingLog.user_id == user_id))
    await db.execute(delete(ReadingStats).where(ReadingStats.user_id == user_id))

    # Event registrations and reviews are keyed on patron_email (no user_id column).
    # Use a case-insensitive match so capitalization differences don't leave PII behind.
    if user_email:
        normalized_email = user_email.lower()
        await db.execute(
            delete(EventRegistration).where(
                func.lower(EventRegistration.patron_email) == normalized_email
            )
        )
        await db.execute(
            delete(EventReview).where(func.lower(EventReview.patron_email) == normalized_email)
        )

    # Delete room-related records — these lose meaning without the patron.
    await db.execute(delete(RoomWaitlist).where(RoomWaitlist.patron_id == user_id))
    await db.execute(delete(RoomQueue).where(RoomQueue.patron_id == user_id))
    # Room reservations: anonymize so historical room usage stats stay intact,
    # but strip the patron_id and any contact PII captured for the booking.
    await db.execute(
        update(RoomReservation)
        .where(RoomReservation.patron_id == user_id)
        .values(
            patron_id=None,
            contact_name=None,
            contact_email=None,
            contact_phone=None,
        )
    )

    # Equipment checkouts — delete patron-linked records (FK is SET NULL but the
    # row contains personal lending history, so remove it entirely).
    await db.execute(delete(EquipmentCheckout).where(EquipmentCheckout.user_id == user_id))

    # Anonymize attendance check-ins so program/event attendance counts remain
    # accurate without retaining patron identifiers or guest contact details.
    await db.execute(
        update(AttendanceCheckIn)
        .where(AttendanceCheckIn.patron_id == user_id)
        .values(patron_id=None, guest_name=None, guest_email=None, guest_phone=None)
    )

    # Anonymize computer reservations and sessions (kept for usage stats /
    # CIPA reporting, but strip patron link and guest PII).
    await db.execute(
        update(ComputerReservation)
        .where(ComputerReservation.patron_id == user_id)
        .values(
            patron_id=None,
            guest_name=None,
            guest_email=None,
            guest_phone=None,
        )
    )
    await db.execute(
        update(ComputerSession).where(ComputerSession.patron_id == user_id).values(patron_id=None)
    )

    # Checkout history: KEEP user_id pointing at the soft-deleted row below.
    # checkouts.user_id is NOT NULL with ondelete=RESTRICT by design (never
    # orphan circulation records); the PII-scrubbed tombstone severs the
    # identity link. Setting user_id=None here raised NotNullViolation and
    # rolled back retention deletion for any patron with checkout history
    # (same bug class as the GDPR deletion path, fixed the same way).
    await db.execute(update(Fine).where(Fine.user_id == user_id).values(user_id=None))

    # Anonymize audit logs (keep the log but remove user reference)
    await db.execute(
        update(AuditLog).where(AuditLog.target_user_id == user_id).values(target_user_id=None)
    )
    await db.execute(update(AuditLog).where(AuditLog.admin_id == user_id).values(admin_id=None))

    # Anonymize privacy ledger records (keep for compliance, remove user link)
    await db.execute(
        update(ConsentRecord).where(ConsentRecord.user_id == user_id).values(user_id=None)
    )
    await db.execute(
        update(DataSharingLog).where(DataSharingLog.user_id == user_id).values(user_id=None)
    )
    await db.execute(
        update(DataCorrectionLog).where(DataCorrectionLog.user_id == user_id).values(user_id=None)
    )

    # Soft-delete the user record: scrub PII but keep the row so NOT NULL /
    # RESTRICT circulation FKs stay intact (mirrors the GDPR deletion path).
    # A hard delete(User) raised ForeignKeyViolation for any patron with
    # checkout history.
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user:
        scrub_user_pii(user, now=datetime.now(timezone.utc))


# checkouts.user_id is NOT NULL with ondelete=RESTRICT by design, so
# anonymization cannot null the column. Instead, aged checkouts are repointed
# at a single inactive system patron (the standard ILS pattern, e.g. Koha's
# AnonymousPatron), which severs the real-patron link while keeping
# circulation rows and their FK invariant intact.
ANONYMIZED_PATRON_EMAIL = "anonymized-patron@system.local"


async def get_or_create_anonymized_patron(db: AsyncSession) -> int:
    result = await db.execute(select(User.id).where(User.email == ANONYMIZED_PATRON_EMAIL))
    anon_id = result.scalar_one_or_none()
    if anon_id is not None:
        return anon_id
    anon = User(
        email=ANONYMIZED_PATRON_EMAIL,
        first_name="Anonymized",
        last_name="Patron",
        # Random token: this account must never be able to log in.
        password_hash=secrets.token_urlsafe(32),
        role=UserRole.PATRON,
        is_active=False,
    )
    db.add(anon)
    await db.flush()
    return anon.id


async def anonymize_old_checkouts(
    db: AsyncSession, *, held_patron_ids: set[int] = frozenset()
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=CHECKOUT_ANONYMIZE_YEARS * 365)
    anon_id = await get_or_create_anonymized_patron(db)

    conditions = [
        Checkout.user_id != anon_id,
        Checkout.returned_at.isnot(None),
        Checkout.returned_at < cutoff,
    ]
    if held_patron_ids:
        conditions.append(Checkout.user_id.notin_(held_patron_ids))

    result = await db.execute(update(Checkout).where(and_(*conditions)).values(user_id=anon_id))

    anonymized_count = result.rowcount
    if anonymized_count > 0:
        logger.info(f"Anonymized {anonymized_count} old checkout records")

    return anonymized_count


async def _anonymize_minor_checkouts(
    db: AsyncSession,
    *,
    minor_ids: set[int],
    retention_months: int,
    held_patron_ids: set[int] = frozenset(),
) -> int:
    if not minor_ids:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_months * 30)
    target_ids = minor_ids - held_patron_ids

    if not target_ids:
        return 0

    anon_id = await get_or_create_anonymized_patron(db)
    conditions = [
        Checkout.user_id.in_(target_ids),
        Checkout.returned_at.isnot(None),
        Checkout.returned_at < cutoff,
    ]

    result = await db.execute(update(Checkout).where(and_(*conditions)).values(user_id=anon_id))

    count = result.rowcount
    if count > 0:
        logger.info(
            "Minor (under-18) retention: anonymized %d checkout records (retention=%d months)",
            count,
            retention_months,
        )
    return count


async def anonymize_old_access_logs(
    db: AsyncSession, *, held_patron_ids: set[int] = frozenset()
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=ACCESS_LOG_RETENTION_DAYS)

    conditions = [
        DatabaseAccessLog.accessed_at < cutoff,
        DatabaseAccessLog.user_id.isnot(None),
    ]
    if held_patron_ids:
        conditions.append(DatabaseAccessLog.user_id.notin_(held_patron_ids))

    result = await db.execute(
        update(DatabaseAccessLog).where(and_(*conditions)).values(user_id=None)
    )

    anonymized_count = result.rowcount
    if anonymized_count > 0:
        logger.info(f"Anonymized {anonymized_count} old database access log records")

    return anonymized_count


async def _anonymize_minor_access_logs(
    db: AsyncSession,
    *,
    minor_ids: set[int],
    retention_months: int,
    held_patron_ids: set[int] = frozenset(),
) -> int:
    if not minor_ids:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_months * 30)
    target_ids = minor_ids - held_patron_ids

    if not target_ids:
        return 0

    conditions = [
        DatabaseAccessLog.user_id.in_(target_ids),
        DatabaseAccessLog.accessed_at < cutoff,
    ]

    result = await db.execute(
        update(DatabaseAccessLog).where(and_(*conditions)).values(user_id=None)
    )

    count = result.rowcount
    if count > 0:
        logger.info(
            "Minor (under-18) retention: anonymized %d database access log records (retention=%d months)",
            count,
            retention_months,
        )
    return count


async def anonymize_old_reading_log_entries(
    db: AsyncSession, *, held_patron_ids: set[int] = frozenset()
) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=CHECKOUT_ANONYMIZE_YEARS * 365)

    # ReadingLogEntry links to user via ReadingRegistration.
    # Find entry IDs belonging to held patrons so we can exclude them.
    held_entry_ids = set()
    if held_patron_ids:
        held_result = await db.execute(
            select(ReadingLogEntry.id)
            .join(ReadingRegistration, ReadingLogEntry.registration_id == ReadingRegistration.id)
            .where(ReadingRegistration.user_id.in_(held_patron_ids))
        )
        held_entry_ids = {row[0] for row in held_result.all()}

    conditions = [
        ReadingLogEntry.logged_at < cutoff,
        ReadingLogEntry.title.isnot(None),
    ]
    if held_entry_ids:
        conditions.append(ReadingLogEntry.id.notin_(held_entry_ids))

    result = await db.execute(
        update(ReadingLogEntry)
        .where(and_(*conditions))
        .values(title=None, author=None, notes=None, book_cover_url=None)
    )
    anonymized_count = result.rowcount
    held_count = len(held_entry_ids)
    if anonymized_count > 0 or held_count > 0:
        logger.info(
            "Reading log retention: anonymized=%d held=%d (cutoff=%s)",
            anonymized_count,
            held_count,
            cutoff.isoformat(),
        )
    return anonymized_count


async def flag_inactive_accounts(db: AsyncSession) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=INACTIVE_ACCOUNT_YEARS * 365)

    # Find users who haven't logged in (no recent refresh tokens)
    # and haven't had any activity
    inactive_result = await db.execute(
        select(User.id)
        .outerjoin(RefreshToken, RefreshToken.user_id == User.id)
        .outerjoin(Checkout, Checkout.user_id == User.id)
        .where(
            and_(
                User.is_active == True,
                User.deletion_requested_at.is_(None),
                or_(
                    User.updated_at.is_(None),
                    User.updated_at < cutoff,
                ),
            )
        )
        .group_by(User.id)
        .having(
            and_(
                # No recent tokens (max created_at is still old, or no tokens)
                or_(
                    func.count(RefreshToken.id) == 0,
                    func.max(RefreshToken.created_at) < cutoff,
                ),
                # No recent checkouts (max checked_out_at is still old, or no checkouts)
                or_(
                    func.count(Checkout.id) == 0,
                    func.max(Checkout.checked_out_at) < cutoff,
                ),
            )
        )
    )

    inactive_ids = [row[0] for row in inactive_result.all()]

    # For now, just log these - actual archival would need policy decision
    if inactive_ids:
        logger.info(f"Found {len(inactive_ids)} potentially inactive accounts for review")

    return len(inactive_ids)


# Marker used to make event-registration / attendance-checkin anonymization
# idempotent across runs. Any row whose email matches this domain is skipped.
ANONYMIZED_EMAIL_DOMAIN = "@anonymized.invalid"
ANONYMIZED_NAME_PLACEHOLDER = "[anonymized]"
_RETENTION_BATCH_SIZE = 1000


async def anonymize_old_event_registrations(
    db: AsyncSession, *, held_patron_ids: set[int] = frozenset()
) -> dict:
    cfg = get_settings()
    cutoff = datetime.now(timezone.utc) - timedelta(days=cfg.event_registration_retention_days)

    # Look up emails for patrons under litigation hold so we can exclude
    # their event registrations (which are keyed on patron_email, not user_id).
    held_emails: set[str] = set()
    if held_patron_ids:
        email_result = await db.execute(select(User.email).where(User.id.in_(held_patron_ids)))
        held_emails = {row[0].lower() for row in email_result.all() if row[0]}

    # Use end_time when available, otherwise fall back to start_time.
    event_time = func.coalesce(Event.end_time, Event.start_time)

    # Candidate rows: joined to events whose effective time is past cutoff.
    base_select = (
        select(EventRegistration.id, EventRegistration.patron_email)
        .join(Event, EventRegistration.event_id == Event.id)
        .where(event_time < cutoff)
    )

    result = await db.execute(base_select)
    rows = result.all()

    anonymized = 0
    deleted = 0
    skipped = 0
    held = 0

    if cfg.retention_anonymize_instead_of_delete:
        # Process in batches to keep transactions reasonably sized.
        to_anonymize: list[int] = []
        for reg_id, email in rows:
            if email and email.endswith(ANONYMIZED_EMAIL_DOMAIN):
                skipped += 1
                continue
            if email and email.lower() in held_emails:
                held += 1
                continue
            to_anonymize.append(reg_id)

        for i in range(0, len(to_anonymize), _RETENTION_BATCH_SIZE):
            chunk = to_anonymize[i : i + _RETENTION_BATCH_SIZE]
            # Per-row update so the email placeholder embeds the row id.
            for reg_id in chunk:
                await db.execute(
                    update(EventRegistration)
                    .where(EventRegistration.id == reg_id)
                    .values(
                        patron_name=ANONYMIZED_NAME_PLACEHOLDER,
                        patron_email=f"anon-{reg_id}{ANONYMIZED_EMAIL_DOMAIN}",
                        patron_phone=None,
                    )
                )
                anonymized += 1
            await db.flush()
    else:
        ids = [reg_id for reg_id, email in rows if not (email and email.lower() in held_emails)]
        for i in range(0, len(ids), _RETENTION_BATCH_SIZE):
            chunk = ids[i : i + _RETENTION_BATCH_SIZE]
            res = await db.execute(delete(EventRegistration).where(EventRegistration.id.in_(chunk)))
            deleted += res.rowcount or 0
            await db.flush()
        held = len(rows) - len(ids)

    if held:
        logger.warning(
            "Event-registration retention: %d record(s) skipped due to litigation hold",
            held,
        )
    summary = {
        "anonymized": anonymized,
        "deleted": deleted,
        "skipped_already_anonymized": skipped,
        "skipped_litigation_hold": held,
    }
    if anonymized or deleted:
        logger.info(
            "Event-registration retention: anonymized=%d deleted=%d skipped=%d (cutoff=%s)",
            anonymized,
            deleted,
            skipped,
            cutoff.isoformat(),
        )
    return summary


async def anonymize_old_attendance_records(
    db: AsyncSession, *, held_patron_ids: set[int] = frozenset()
) -> dict:
    cfg = get_settings()
    cutoff_date = (
        datetime.now(timezone.utc) - timedelta(days=cfg.attendance_record_retention_days)
    ).date()

    base_select = (
        select(
            AttendanceCheckIn.id,
            AttendanceCheckIn.guest_email,
            AttendanceCheckIn.patron_id,
        )
        .join(AttendanceSession, AttendanceCheckIn.session_id == AttendanceSession.id)
        .where(AttendanceSession.session_date < cutoff_date)
    )

    result = await db.execute(base_select)
    rows = result.all()

    anonymized = 0
    deleted = 0
    skipped = 0
    held = 0

    if cfg.retention_anonymize_instead_of_delete:
        to_anonymize: list[int] = []
        for ci_id, email, patron_id in rows:
            # guest_email is nullable here, so a row with NULL email can't be
            # marked already-anonymized via the email domain. We use the
            # marker only when an email is present -- if guest_email is NULL
            # AND guest_name/library_card_number/phone are also empty we
            # still re-issue the update (cheap, idempotent in effect).
            if email and email.endswith(ANONYMIZED_EMAIL_DOMAIN):
                skipped += 1
                continue
            if patron_id and patron_id in held_patron_ids:
                held += 1
                continue
            to_anonymize.append(ci_id)

        for i in range(0, len(to_anonymize), _RETENTION_BATCH_SIZE):
            chunk = to_anonymize[i : i + _RETENTION_BATCH_SIZE]
            for ci_id in chunk:
                await db.execute(
                    update(AttendanceCheckIn)
                    .where(AttendanceCheckIn.id == ci_id)
                    .values(
                        guest_name=None,
                        guest_email=f"anon-{ci_id}{ANONYMIZED_EMAIL_DOMAIN}",
                        guest_phone=None,
                        library_card_number=None,
                    )
                )
                anonymized += 1
            await db.flush()
    else:
        ids = []
        for ci_id, email, patron_id in rows:
            if patron_id and patron_id in held_patron_ids:
                held += 1
                continue
            ids.append(ci_id)
        for i in range(0, len(ids), _RETENTION_BATCH_SIZE):
            chunk = ids[i : i + _RETENTION_BATCH_SIZE]
            res = await db.execute(delete(AttendanceCheckIn).where(AttendanceCheckIn.id.in_(chunk)))
            deleted += res.rowcount or 0
            await db.flush()

    if held:
        logger.warning(
            "Attendance retention: %d record(s) skipped due to litigation hold",
            held,
        )
    summary = {
        "anonymized": anonymized,
        "deleted": deleted,
        "skipped_already_anonymized": skipped,
        "skipped_litigation_hold": held,
    }
    if anonymized or deleted:
        logger.info(
            "Attendance retention: anonymized=%d deleted=%d skipped=%d (cutoff=%s)",
            anonymized,
            deleted,
            skipped,
            cutoff_date.isoformat(),
        )
    return summary


async def _anonymize_minor_event_registrations(
    db: AsyncSession,
    *,
    minor_emails: set[str],
    retention_months: int,
    held_patron_ids: set[int] = frozenset(),
) -> int:
    if not minor_emails:
        return 0

    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_months * 30)
    event_time = func.coalesce(Event.end_time, Event.start_time)

    # Look up emails under litigation hold to exclude
    held_emails: set[str] = set()
    if held_patron_ids:
        email_result = await db.execute(select(User.email).where(User.id.in_(held_patron_ids)))
        held_emails = {row[0].lower() for row in email_result.all() if row[0]}

    target_emails = minor_emails - held_emails

    if not target_emails:
        return 0

    base_select = (
        select(EventRegistration.id, EventRegistration.patron_email)
        .join(Event, EventRegistration.event_id == Event.id)
        .where(
            event_time < cutoff,
            func.lower(EventRegistration.patron_email).in_(target_emails),
        )
    )

    result = await db.execute(base_select)
    rows = result.all()

    anonymized = 0
    for reg_id, email in rows:
        if email and email.endswith(ANONYMIZED_EMAIL_DOMAIN):
            continue
        await db.execute(
            update(EventRegistration)
            .where(EventRegistration.id == reg_id)
            .values(
                patron_name=ANONYMIZED_NAME_PLACEHOLDER,
                patron_email=f"anon-{reg_id}{ANONYMIZED_EMAIL_DOMAIN}",
                patron_phone=None,
            )
        )
        anonymized += 1

    if anonymized > 0:
        await db.flush()
        logger.info(
            "Minor (under-18) retention: anonymized %d event registration records (retention=%d months)",
            anonymized,
            retention_months,
        )
    return anonymized


async def _anonymize_minor_attendance_records(
    db: AsyncSession,
    *,
    minor_ids: set[int],
    retention_months: int,
    held_patron_ids: set[int] = frozenset(),
) -> int:
    if not minor_ids:
        return 0

    cutoff_date = (datetime.now(timezone.utc) - timedelta(days=retention_months * 30)).date()
    target_ids = minor_ids - held_patron_ids

    if not target_ids:
        return 0

    base_select = (
        select(AttendanceCheckIn.id, AttendanceCheckIn.guest_email)
        .join(AttendanceSession, AttendanceCheckIn.session_id == AttendanceSession.id)
        .where(
            AttendanceSession.session_date < cutoff_date,
            AttendanceCheckIn.patron_id.in_(target_ids),
        )
    )

    result = await db.execute(base_select)
    rows = result.all()

    anonymized = 0
    for ci_id, email in rows:
        if email and email.endswith(ANONYMIZED_EMAIL_DOMAIN):
            continue
        await db.execute(
            update(AttendanceCheckIn)
            .where(AttendanceCheckIn.id == ci_id)
            .values(
                guest_name=None,
                guest_email=f"anon-{ci_id}{ANONYMIZED_EMAIL_DOMAIN}",
                guest_phone=None,
                library_card_number=None,
            )
        )
        anonymized += 1

    if anonymized > 0:
        await db.flush()
        logger.info(
            "Minor (under-18) retention: anonymized %d attendance records (retention=%d months)",
            anonymized,
            retention_months,
        )
    return anonymized


# Map purge job keys to data_retention_policies.data_type values
_JOB_DATA_TYPE_MAP = {
    "refresh_tokens_deleted": "patron_accounts",
    "password_history_cleaned": "patron_accounts",
    "consent_tokens_cleared": "patron_accounts",
    "email_blocks_cleaned": "patron_accounts",
    "scheduled_deletions_processed": "patron_accounts",
    "checkouts_anonymized": "circulation_records",
    "inactive_accounts_flagged": "patron_accounts",
    "access_logs_anonymized": "database_access_logs",
    "reading_logs_anonymized": "reading_programs",
}

# Jobs that anonymize/delete patron-linked records and must respect litigation holds.
_PATRON_SENSITIVE_JOBS = {
    "scheduled_deletions_processed",
    "checkouts_anonymized",
    "access_logs_anonymized",
    "event_registrations_retention",
    "attendance_records_retention",
    "reading_logs_anonymized",
}


async def _get_legal_holds(db: AsyncSession) -> dict[str, bool]:
    result = await db.execute(
        select(DataRetentionPolicy.data_type, DataRetentionPolicy.has_legal_hold_exception).where(
            DataRetentionPolicy.is_active == True
        )
    )
    return {row.data_type: row.has_legal_hold_exception for row in result.all()}


# Terminal statuses: request is resolved and no longer requires a hold.
_LE_TERMINAL_STATUSES = {
    WorkflowStatus.COMPLETED,
    WorkflowStatus.REJECTED,
    WorkflowStatus.WITHDRAWN,
}


async def get_litigation_hold_patron_ids(db: AsyncSession) -> set[int]:
    result = await db.execute(
        select(LawEnforcementRequest.patron_id).where(
            and_(
                LawEnforcementRequest.patron_id.isnot(None),
                LawEnforcementRequest.workflow_status.notin_(
                    [s.value for s in _LE_TERMINAL_STATUSES]
                ),
            )
        )
    )
    return {row[0] for row in result.all()}


async def has_active_litigation_hold(db: AsyncSession, patron_id: int) -> bool:
    result = await db.execute(
        select(LawEnforcementRequest.id)
        .where(
            and_(
                LawEnforcementRequest.patron_id == patron_id,
                LawEnforcementRequest.workflow_status.notin_(
                    [s.value for s in _LE_TERMINAL_STATUSES]
                ),
            )
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def purge_resolved_challenger_pii(db: AsyncSession) -> int:
    """Null challenger identity 12 months after a challenge is resolved.

    The reconsideration form on the public /banned-books page collects a name
    and contact alongside the objection. Keeping the challenge record forever
    serves transparency; keeping the identity of the person who filed it does
    not, so the identity ages out while the record stays.

    challenger_complaint is deliberately NOT purged. It is the substance of the
    objection and part of the institutional record, and the public transparency
    output is built from public_title/public_summary rather than from any of
    these fields, so nothing visible changes.

    Rows with a NULL date_resolved are untouched: the clock starts at
    resolution, and an open challenge still needs its contact details.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=30 * CHALLENGER_PII_RETENTION_MONTHS)

    result = await db.execute(
        update(BookChallenge)
        .where(
            BookChallenge.date_resolved.is_not(None),
            BookChallenge.date_resolved < cutoff,
            or_(
                BookChallenge.challenger_name.is_not(None),
                BookChallenge.challenger_contact.is_not(None),
            ),
        )
        .values(challenger_name=None, challenger_contact=None)
    )

    purged = result.rowcount or 0
    if purged > 0:
        logger.info(
            "Purged challenger identity from %d challenge(s) resolved before %s",
            purged,
            cutoff.date(),
        )
    return purged


async def run_all_retention_jobs(db: AsyncSession) -> dict:
    results: dict = {
        "refresh_tokens_deleted": 0,
        "password_history_cleaned": 0,
        "consent_tokens_cleared": 0,
        "email_blocks_cleaned": 0,
        "journey_events_deleted": 0,
        "ai_conversations_deleted": 0,
        "ai_usage_logs_deleted": 0,
        "scheduled_deletions_processed": 0,
        "checkouts_anonymized": 0,
        "inactive_accounts_flagged": 0,
        "event_registrations_retention": {},
        "attendance_records_retention": {},
        "access_logs_anonymized": 0,
        "reading_logs_anonymized": 0,
        "challenger_pii_purged": 0,
        "minor_records_anonymized": 0,
    }

    # Query Minor (under-18) retention period and current minor patron IDs
    minor_retention_months = await _get_minor_retention_months(db)
    minor_ids = await _get_minor_patron_ids(db)
    if minor_ids:
        logger.info(
            "Minor (under-18) retention: %d minor patron(s), retention=%d months",
            len(minor_ids),
            minor_retention_months,
        )

    jobs = [
        ("refresh_tokens_deleted", cleanup_expired_refresh_tokens),
        ("password_history_cleaned", cleanup_excess_password_history),
        ("consent_tokens_cleared", cleanup_expired_consent_tokens),
        ("email_blocks_cleaned", cleanup_expired_email_blocks),
        ("journey_events_deleted", cleanup_old_journey_events),
        ("ai_conversations_deleted", cleanup_old_agent_conversations),
        ("ai_usage_logs_deleted", cleanup_ai_usage_logs),
        ("scheduled_deletions_processed", process_scheduled_deletions),
        ("checkouts_anonymized", anonymize_old_checkouts),
        ("inactive_accounts_flagged", flag_inactive_accounts),
        ("event_registrations_retention", anonymize_old_event_registrations),
        ("attendance_records_retention", anonymize_old_attendance_records),
        ("access_logs_anonymized", anonymize_old_access_logs),
        ("reading_logs_anonymized", anonymize_old_reading_log_entries),
        ("challenger_pii_purged", purge_resolved_challenger_pii),
    ]

    # Query legal holds once for all jobs
    legal_holds = await _get_legal_holds(db)

    # Query active law enforcement requests for patron-level litigation holds
    held_patron_ids = await get_litigation_hold_patron_ids(db)
    if held_patron_ids:
        logger.warning(
            "Litigation hold active: %d patron(s) excluded from retention jobs",
            len(held_patron_ids),
        )

    for key, func in jobs:
        try:
            # Check if a legal hold blocks this purge category
            data_type = _JOB_DATA_TYPE_MAP.get(key)
            if data_type and legal_holds.get(data_type, False):
                logger.info(f"Skipping purge for {key}: legal hold active on {data_type}")
                continue

            # Pass litigation-hold patron IDs to jobs that support it
            if key in _PATRON_SENSITIVE_JOBS:
                results[key] = await func(db, held_patron_ids=held_patron_ids)
            else:
                results[key] = await func(db)
            await db.commit()
        except Exception as e:  # noqa: BLE001 - per-iteration boundary: one retention job's failure must not crash the other jobs in the schedule
            await db.rollback()
            logger.warning("Retention job '%s' failed (skipping): %s", key, e)

    # Minor (under-18) retention: apply shorter retention period for current minors
    if minor_ids:
        minor_total = 0
        minor_emails = await _get_minor_patron_emails(db, minor_ids)

        minor_jobs = [
            ("minor_checkouts", _anonymize_minor_checkouts, {"minor_ids": minor_ids}),
            ("minor_access_logs", _anonymize_minor_access_logs, {"minor_ids": minor_ids}),
            (
                "minor_event_registrations",
                _anonymize_minor_event_registrations,
                {"minor_emails": minor_emails},
            ),
            ("minor_attendance", _anonymize_minor_attendance_records, {"minor_ids": minor_ids}),
        ]

        for label, job_func, kwargs in minor_jobs:
            try:
                count = await job_func(
                    db,
                    retention_months=minor_retention_months,
                    held_patron_ids=held_patron_ids,
                    **kwargs,
                )
                minor_total += count
                await db.commit()
            except Exception as e:  # noqa: BLE001 - per-iteration boundary: one minor-retention job's failure must not crash the other minor jobs
                await db.rollback()
                logger.warning("Minor retention job '%s' failed (skipping): %s", label, e)

        results["minor_records_anonymized"] = minor_total

    logger.info("Data retention jobs completed: %s", results)

    # #12: Emit per-type deletion counters for monitoring
    try:
        from ..core.metrics import increment

        for key, count in results.items():
            if isinstance(count, dict):
                # New retention summaries report multiple sub-counts.
                for subkey, subcount in count.items():
                    if isinstance(subcount, int) and subcount > 0:
                        increment(
                            "data_retention_records_deleted",
                            {"type": f"{key}.{subkey}"},
                            subcount,
                        )
            elif isinstance(count, int) and count > 0:
                increment("data_retention_records_deleted", {"type": key}, count)
    except Exception:  # noqa: BLE001 - best-effort metrics emission: metrics module failure must not impact retention job results returned to caller
        logger.debug("Failed to emit data retention deletion metrics")

    return results
