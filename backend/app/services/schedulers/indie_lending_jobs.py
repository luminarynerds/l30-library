# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from collections import defaultdict
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from ...core.config import get_settings
from ...core.database import AsyncSessionLocal
from ...core.email import COLORS, send_email
from ...core.frontend_routes import routes
from ...core.logging import get_logger
from ...models.indie_author import IndieAuthor
from ...models.indie_author_follow import IndieAuthorFollow
from ...models.indie_author_release_notification import IndieAuthorReleaseNotification
from ...models.indie_ebook_borrow import BorrowStatus, IndieEbookBorrow
from ...models.job_failure import JobSeverity
from ...models.notification_preference import UserNotificationPreference
from ...models.user import User
from ...services.metislib_errors import MetisLibError
from ..job_failure_service import JobExecutionContext

settings = get_settings()
logger = get_logger(__name__)

DUE_SOON_DAYS = 3


async def expire_overdue_indie_borrows() -> None:
    async with JobExecutionContext(
        job_id="indie_borrow_expiry",
        job_name="Indie Ebook Borrow Expiry",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            result = await db.execute(
                select(IndieEbookBorrow).where(
                    and_(
                        IndieEbookBorrow.status == BorrowStatus.active,
                        IndieEbookBorrow.due_at < now,
                    )
                )
            )
            overdue = result.scalars().all()

            for borrow in overdue:
                try:
                    borrow.status = BorrowStatus.expired
                    ctx.record_success()
                except Exception as e:
                    logger.error(
                        "Error expiring indie borrow %d: %s", borrow.id, e,
                        exc_info=True,
                    )
                    ctx.record_failure(
                        error=e,
                        entity_type="indie_ebook_borrow",
                        entity_id=borrow.id,
                    )

            if overdue:
                await db.commit()

            ctx.add_metric("borrows_expired", len(overdue))
            logger.info(
                "Indie borrow expiry completed",
                extra={"borrows_expired": len(overdue)},
            )


async def send_indie_due_soon_notifications() -> None:
    async with JobExecutionContext(
        job_id="indie_due_soon_notifications",
        job_name="Indie Ebook Due Soon Notifications",
        severity=JobSeverity.LOW,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            now = datetime.now(timezone.utc)
            threshold = now + timedelta(days=DUE_SOON_DAYS)

            # Active borrows due within 3 days that haven't been notified yet
            result = await db.execute(
                select(IndieEbookBorrow)
                .options(selectinload(IndieEbookBorrow.user))
                .where(
                    and_(
                        IndieEbookBorrow.status == BorrowStatus.active,
                        IndieEbookBorrow.due_at <= threshold,
                        IndieEbookBorrow.due_at > now,
                        IndieEbookBorrow.due_soon_notified_at.is_(None),
                    )
                )
            )
            borrows = result.scalars().all()

            notifications_sent = 0

            for borrow in borrows:
                try:
                    user = borrow.user
                    if not user or not user.email:
                        continue

                    days_left = max(1, (borrow.due_at - now).days)
                    day_word = "day" if days_left == 1 else "days"

                    success = await _send_due_soon_email(
                        user, borrow, days_left, day_word,
                    )

                    if success:
                        borrow.due_soon_notified_at = now
                        notifications_sent += 1

                    ctx.record_success()
                except Exception as e:
                    logger.error(
                        "Error sending due-soon notification for borrow %d: %s",
                        borrow.id, e,
                        exc_info=True,
                    )
                    ctx.record_failure(
                        error=e,
                        entity_type="indie_ebook_borrow",
                        entity_id=borrow.id,
                    )

            if notifications_sent:
                await db.commit()

            ctx.add_metric("notifications_sent", notifications_sent)
            logger.info(
                "Indie due-soon notifications completed",
                extra={"notifications_sent": notifications_sent},
            )


async def _send_due_soon_email(
    user: User,
    borrow: IndieEbookBorrow,
    days_left: int,
    day_word: str,
) -> bool:
    due_date = borrow.due_at.strftime("%B %d, %Y")
    subject = f"Your indie ebook borrow is due in {days_left} {day_word}"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">Borrow Due Soon</h2>
        <p>Hi {user.first_name},</p>
        <p>Your indie ebook borrow is due on <strong>{due_date}</strong>
           ({days_left} {day_word} from now).</p>
        <p>If you haven't finished reading, you can return the ebook early or
           it will be automatically returned on the due date.</p>
        <p style="text-align: center; margin: 30px 0;">
            <a href="{routes.url(settings.frontend_url, routes.indie_dashboard)}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                View My Borrows
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            {settings.app_name} - {settings.library_name}
        </p>
    </div>
    """

    try:
        return await send_email(
            user.email, subject, html_content,
            patron_id=user.id,
            notification_type="indie_due_soon",
        )
    except Exception as e:
        logger.error(
            "Failed to send indie due-soon email to user %d: %s",
            user.id, e,
            exc_info=True,
        )
        return False


# ── Follower digest ───────────────────────────────────────────

MAX_DIGEST_BOOKS_PER_USER = 10
DIGEST_NOTIFICATION_TYPE = "indie_author_release_digest"


async def _digest_email_enabled(db, user_id: int) -> bool:
    pref_row = await db.execute(
        select(UserNotificationPreference).where(
            UserNotificationPreference.user_id == user_id
        )
    )
    pref = pref_row.scalar_one_or_none()
    if pref is None or not isinstance(pref.channel_preferences, dict):
        return True
    setting = pref.channel_preferences.get(DIGEST_NOTIFICATION_TYPE)
    if not isinstance(setting, dict):
        return True
    return bool(setting.get("email", True))


async def send_indie_author_release_digests() -> None:
    async with JobExecutionContext(
        job_id="indie_author_release_digest",
        job_name="Indie Author Release Digest",
        severity=JobSeverity.LOW,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            # Load all follows joined to author + user (one query)
            follow_stmt = (
                select(IndieAuthorFollow, IndieAuthor, User)
                .join(IndieAuthor, IndieAuthorFollow.indie_author_id == IndieAuthor.id)
                .join(User, IndieAuthorFollow.user_id == User.id)
            )
            follow_rows = (await db.execute(follow_stmt)).all()
            if not follow_rows:
                ctx.add_metric("users_notified", 0)
                logger.info("Indie release digest: no follows, nothing to do")
                return

            # Bucket follows per user; keep the IndieAuthorFollow row so we can
            # consult/update seeded_at.
            follows_by_user: dict[int, list[tuple[IndieAuthorFollow, IndieAuthor, User]]] = defaultdict(list)
            for follow, author, user in follow_rows:
                follows_by_user[user.id].append((follow, author, user))

            # Fetch the indie catalog from MetisLib once (small catalog, ≤ a few hundred)
            try:
                from ...services.metislib_client import get_metislib_client
                client = get_metislib_client()
                catalog = await client.search_catalog(
                    query=None,
                    filters={"source_type": "indie"},
                    page=1,
                    per_page=200,
                )
            except MetisLibError as e:
                logger.warning("Indie release digest: catalog fetch failed: %s", e)
                ctx.add_metric("users_notified", 0)
                return

            all_items = catalog.get("items", []) if isinstance(catalog, dict) else []
            # Index by author_id for cheap per-user lookup
            books_by_author: dict[int, list[dict]] = defaultdict(list)
            for item in all_items:
                if not isinstance(item, dict):
                    continue
                aid = item.get("author_id")
                if isinstance(aid, int):
                    books_by_author[aid].append(item)

            users_notified = 0
            books_digested = 0
            authors_seeded = 0

            for user_id, author_user_pairs in follows_by_user.items():
                try:
                    if not author_user_pairs:
                        continue
                    user = author_user_pairs[0][2]
                    if not user.email:
                        continue

                    new_books: list[tuple[IndieAuthor, dict]] = []

                    for follow, author, _ in author_user_pairs:
                        candidate_books = books_by_author.get(author.id, [])
                        candidate_ids = [
                            b.get("id") for b in candidate_books if isinstance(b.get("id"), int)
                        ]
                        if not candidate_ids:
                            continue

                        # First time we process this follow: seed all current books
                        # as already-notified, send nothing, stamp seeded_at. Patron
                        # will only be alerted to books published AFTER this point.
                        if follow.seeded_at is None:
                            now = datetime.now(timezone.utc)
                            for book in candidate_books:
                                bid = book.get("id")
                                if isinstance(bid, int):
                                    db.add(
                                        IndieAuthorReleaseNotification(
                                            user_id=user_id,
                                            indie_author_id=author.id,
                                            metislib_ebook_id=bid,
                                        )
                                    )
                            follow.seeded_at = now
                            authors_seeded += 1
                            continue

                        # Already seeded: find books we haven't notified about yet
                        already_stmt = select(IndieAuthorReleaseNotification.metislib_ebook_id).where(
                            and_(
                                IndieAuthorReleaseNotification.user_id == user_id,
                                IndieAuthorReleaseNotification.metislib_ebook_id.in_(candidate_ids),
                            )
                        )
                        already = {
                            row for row in (await db.execute(already_stmt)).scalars().all()
                        }
                        for book in candidate_books:
                            bid = book.get("id")
                            if isinstance(bid, int) and bid not in already:
                                new_books.append((author, book))

                    if not new_books:
                        continue

                    new_books = new_books[:MAX_DIGEST_BOOKS_PER_USER]

                    # Record dedupe regardless of opt-out so re-opt-in starts fresh
                    # rather than dumping a backlog.
                    if not await _digest_email_enabled(db, user_id):
                        for author, book in new_books:
                            db.add(
                                IndieAuthorReleaseNotification(
                                    user_id=user_id,
                                    indie_author_id=author.id,
                                    metislib_ebook_id=book.get("id"),
                                )
                            )
                        logger.info(
                            "Indie release digest skipped (opted out)",
                            extra={"user_id": user_id, "books_skipped": len(new_books)},
                        )
                        ctx.record_success()
                        continue

                    sent = await _send_indie_release_digest_email(user, new_books)
                    if not sent:
                        ctx.record_failure(
                            error=RuntimeError("digest email send returned False"),
                            entity_type="user",
                            entity_id=user_id,
                        )
                        continue

                    for author, book in new_books:
                        db.add(
                            IndieAuthorReleaseNotification(
                                user_id=user_id,
                                indie_author_id=author.id,
                                metislib_ebook_id=book.get("id"),
                            )
                        )
                    users_notified += 1
                    books_digested += len(new_books)
                    ctx.record_success()
                except Exception as e:
                    logger.error(
                        "Error building digest for user %d: %s",
                        user_id, e,
                        exc_info=True,
                    )
                    ctx.record_failure(
                        error=e,
                        entity_type="user",
                        entity_id=user_id,
                    )

            # Commit both seed inserts and post-send notification inserts together.
            if users_notified or authors_seeded:
                await db.commit()

            ctx.add_metric("users_notified", users_notified)
            ctx.add_metric("books_digested", books_digested)
            ctx.add_metric("authors_seeded", authors_seeded)
            logger.info(
                "Indie author release digest completed",
                extra={
                    "users_notified": users_notified,
                    "books_digested": books_digested,
                    "authors_seeded": authors_seeded,
                },
            )


def _book_card_html(book: dict) -> str:
    title = (book.get("title") or "Untitled").replace("<", "&lt;").replace(">", "&gt;")
    author = (book.get("author_pen_name") or book.get("author_name") or "").replace("<", "&lt;").replace(">", "&gt;")
    ebook_id = book.get("id")
    description = (book.get("description") or "")[:160].replace("<", "&lt;").replace(">", "&gt;")
    detail_path = f"/indie/book/{ebook_id}" if ebook_id else "/indie"
    detail_url = routes.url(settings.frontend_url, detail_path)
    return (
        f'<div style="border-left: 3px solid {COLORS["button"]}; padding: 8px 12px; margin: 12px 0;">'
        f'<div style="font-weight: 600; color: {COLORS["heading"]};">{title}</div>'
        f'<div style="font-size: 12px; color: {COLORS["text_light"]};">by {author}</div>'
        f'<div style="font-size: 13px; margin-top: 4px;">{description}...</div>'
        f'<div style="margin-top: 6px;"><a href="{detail_url}" style="color: {COLORS["button"]};">View &raquo;</a></div>'
        f'</div>'
    )


async def _send_indie_release_digest_email(
    user: User,
    new_books: list[tuple[IndieAuthor, dict]],
) -> bool:
    count = len(new_books)
    word = "book" if count == 1 else "books"
    subject = f"{count} new {word} from authors you follow"

    cards = "".join(_book_card_html(book) for _, book in new_books)
    follows_url = routes.url(settings.frontend_url, "/indie")
    first_name = user.first_name or "there"

    html_content = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: {COLORS['heading']};">New from authors you follow</h2>
        <p>Hi {first_name},</p>
        <p>Authors you follow on the {settings.library_name} indie catalog have new books available:</p>
        {cards}
        <p style="text-align: center; margin: 30px 0;">
            <a href="{follows_url}"
               style="background-color: {COLORS['button']}; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Browse Indie Catalog
            </a>
        </p>
        <hr style="border: none; border-top: 1px solid {COLORS['divider']}; margin: 30px 0;">
        <p style="color: {COLORS['text_light']}; font-size: 12px;">
            You are receiving this because you follow these authors on {settings.library_name}.
            Manage your follows from any author profile page.
        </p>
    </div>
    """

    try:
        return await send_email(
            user.email, subject, html_content,
            patron_id=user.id,
            notification_type="indie_author_release_digest",
        )
    except Exception as e:
        logger.error(
            "Failed to send indie release digest to user %d: %s",
            user.id, e,
            exc_info=True,
        )
        return False


async def reconcile_metislib_borrow_sync() -> int:
    """Retry indie borrows/returns whose MetisLib mirror call failed.

    Closes the drift where a best-effort sync was dropped on a MetisLib outage:
    MetisLib would otherwise miss the loan (or keep a returned copy ACTIVE),
    corrupting its circulation analytics and waitlist promotion. Returns the
    number of borrows reconciled.
    """
    from ...models.indie_ebook_borrow import IndieEbook, MetisLibSyncState
    from ...utils.patron_hash import generate_patron_hash
    from ..metislib_client import get_metislib_client

    reconciled = 0
    async with JobExecutionContext(
        job_id="indie_metislib_sync_reconcile",
        job_name="Indie MetisLib Borrow-Sync Reconcile",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            rows = (await db.execute(
                select(IndieEbookBorrow).where(
                    IndieEbookBorrow.metislib_sync_state.in_(
                        (MetisLibSyncState.borrow_failed, MetisLibSyncState.return_failed)
                    )
                )
            )).scalars().all()

            client = get_metislib_client()

            # Commit per row: each remote call is a side effect, so persist its
            # result immediately. A later DB failure then strands only the
            # unprocessed tail instead of replaying every succeeded remote call.
            for borrow in rows:
                try:
                    ebook = await db.get(IndieEbook, borrow.ebook_id)
                    patron = generate_patron_hash(borrow.user_id)
                    if borrow.metislib_sync_state == MetisLibSyncState.borrow_failed:
                        if not ebook or not ebook.metislib_ebook_id:
                            # Local-only title: nothing to mirror.
                            borrow.metislib_sync_state = MetisLibSyncState.not_required
                        else:
                            result = await client.borrow_indie(ebook.metislib_ebook_id, patron)
                            mid = result.get("borrow_id")
                            if not mid:
                                await db.rollback()
                                ctx.record_failure(
                                    error=RuntimeError("MetisLib borrow returned no borrow_id"),
                                    entity_type="indie_ebook_borrow", entity_id=borrow.id,
                                )
                                continue
                            borrow.metislib_borrow_id = mid
                            borrow.metislib_sync_state = MetisLibSyncState.synced
                    else:  # return_failed
                        if borrow.metislib_borrow_id:
                            await client.return_indie(borrow.metislib_borrow_id, patron)
                            borrow.metislib_sync_state = MetisLibSyncState.synced
                        elif not ebook or not ebook.metislib_ebook_id:
                            # Never had a MetisLib borrow -> nothing to return.
                            borrow.metislib_sync_state = MetisLibSyncState.not_required
                        else:
                            # return_failed with no borrow id: can't auto-reconcile;
                            # keep it surfacing rather than silently marking synced.
                            await db.rollback()
                            ctx.record_failure(
                                error=RuntimeError(
                                    "return_failed borrow has no metislib_borrow_id"
                                ),
                                entity_type="indie_ebook_borrow", entity_id=borrow.id,
                            )
                            continue
                    await db.commit()
                    reconciled += 1
                    ctx.record_success()
                except Exception as e:  # noqa: BLE001  # per-borrow resilience boundary; keep going, the job surfaces failures
                    await db.rollback()
                    logger.warning("Reconcile failed for borrow %d: %s", borrow.id, e)
                    ctx.record_failure(
                        error=e, entity_type="indie_ebook_borrow", entity_id=borrow.id,
                    )
    return reconciled


async def sync_indie_opds_catalog() -> None:
    """Nightly owned-catalog refresh from MetisLib's indie OPDS feed.

    Keeps indie_ebooks current so /indie browse (owned-table only, never a
    live MetisLib call) picks up new titles. Gated on the same flag as the
    manual admin trigger (POST /api/v1/admin/indie-import); no-op when off.
    """
    if not get_settings().indie_opds_import_enabled:
        return
    from ..metislib_opds_import_service import MetisLibOpdsImporter

    async with JobExecutionContext(
        job_id="indie_opds_catalog_sync",
        job_name="Indie OPDS Owned-Catalog Sync",
        severity=JobSeverity.MEDIUM,
    ) as ctx:
        async with AsyncSessionLocal() as db:
            try:
                stats = await MetisLibOpdsImporter(db).import_all()
                logger.info("Indie OPDS nightly sync completed: %s", stats)
                ctx.record_success()
            except Exception as e:  # noqa: BLE001  # nightly sync must fail visibly via job-failure surface, not crash the scheduler
                logger.error("Indie OPDS nightly sync failed: %s", e, exc_info=True)
                ctx.record_failure(error=e, entity_type="indie_opds_sync", entity_id=0)
