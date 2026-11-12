# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from app.core.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import get_settings
from ..core.email import send_email
from ..models.catalog import CatalogItem, ItemStatus, ItemType
from ..models.notification import (
    PatronNotification,
    PatronNotificationCategory,
)
from ..models.saved_search import SavedSearch
from ..models.user import User
from .catalog_search_service import catalog_search_service
from .organization_features_service import OrganizationFeaturesService
from .notifications.templates import render_saved_search_alert_email

logger = get_logger(__name__)
settings = get_settings()

# How long to wait between alerts for the same saved search. A patron
# who adds 50 matching titles in a single bulk import should still see
# one alert, not fifty.
THROTTLE_WINDOW = timedelta(hours=24)

# Cap the number of items mentioned in any single alert. Email bodies
# stay readable and the in-app preview doesn't blow past its column
# width. The total ``new_count`` in the message reflects everything,
# this just bounds the inline preview.
MAX_PREVIEW_ITEMS = 10


@dataclass
class NotifyResult:

    rows_processed: int = 0
    rows_notified: int = 0
    rows_skipped_no_matches: int = 0
    rows_skipped_throttle: int = 0
    rows_failed: int = 0
    in_app_sent: int = 0
    emails_sent: int = 0
    feature_disabled: bool = False
    errors: List[str] = field(default_factory=list)


def _coerce_item_type(raw: Optional[str]) -> Optional[ItemType]:
    if not raw:
        return None
    try:
        return ItemType(raw)
    except ValueError:
        return None


def _coerce_status(raw: Optional[str]) -> Optional[ItemStatus]:
    if not raw:
        return None
    try:
        return ItemStatus(raw)
    except ValueError:
        return None


async def _new_matches_for_search(
    db: AsyncSession,
    saved: SavedSearch,
) -> List[CatalogItem]:
    filters = saved.filters_json or {}

    items = await catalog_search_service.advanced_search(
        db=db,
        title=saved.query or filters.get("title"),
        author=filters.get("author"),
        subject=filters.get("subject"),
        isbn=filters.get("isbn"),
        publisher=filters.get("publisher"),
        operator=filters.get("operator", "AND"),
        exclude_subject=filters.get("exclude_subject"),
        item_type=_coerce_item_type(filters.get("item_type")),
        status=_coerce_status(filters.get("status")),
        year_min=filters.get("year_min"),
        year_max=filters.get("year_max"),
        location=filters.get("location"),
        min_lexile=filters.get("min_lexile"),
        max_lexile=filters.get("max_lexile"),
        page=1,
        per_page=200,
    )

    if saved.last_notified_item_id is not None:
        items = [i for i in items if i.id > saved.last_notified_item_id]

    items.sort(key=lambda i: i.id, reverse=True)
    return items


async def _record_in_app(
    db: AsyncSession,
    saved: SavedSearch,
    patron: User,
    matches: List[CatalogItem],
) -> bool:
    source_event_id = f"saved_search:{saved.id}:{matches[0].id}"
    existing = await db.execute(
        select(PatronNotification.id).where(
            PatronNotification.source_event_id == source_event_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        return False

    count = len(matches)
    title = (
        f"{count} new items match your saved search \"{saved.name}\""
        if count > 1
        else f"1 new item matches your saved search \"{saved.name}\""
    )
    preview = matches[0].title or "(untitled)"
    if matches[0].author:
        preview = f"{preview} -- {matches[0].author}"
    message = preview[:500]

    notif = PatronNotification(
        patron_id=patron.id,
        category=PatronNotificationCategory.CATALOG_SAVED_SEARCH_MATCH,
        title=title,
        message=message,
        source_event_type="saved_search_match",
        source_event_id=source_event_id,
        action_url=f"/catalog?saved={saved.id}",
        action_label="View matches",
    )
    db.add(notif)
    try:
        await db.commit()
        return True
    except IntegrityError:
        await db.rollback()
        return False


async def _deliver_email(
    saved: SavedSearch,
    patron: User,
    matches: List[CatalogItem],
) -> bool:
    if not (patron.email and patron.email.strip()):
        return False

    library_name = getattr(settings, "library_name", None) or "your library"
    public_base = (
        getattr(settings, "frontend_url", None) or ""
    ).rstrip("/")
    catalog_url = f"{public_base}/catalog?saved={saved.id}"

    subject, html_body = render_saved_search_alert_email(
        patron_name=patron.first_name or "Patron",
        search_name=saved.name,
        items=matches[:MAX_PREVIEW_ITEMS],
        new_count=len(matches),
        catalog_url=catalog_url,
        library_name=library_name,
    )

    try:
        ok = await send_email(
            to_email=patron.email,
            subject=subject,
            html_content=html_body,
        )
    except Exception:
        logger.exception(
            "saved_search_notifier: email send raised for search %s patron %s",
            saved.id,
            patron.id,
        )
        return False
    return bool(ok)


async def notify_saved_searches(db: AsyncSession) -> NotifyResult:
    result = NotifyResult()

    enabled = await OrganizationFeaturesService.is_feature_enabled(
        db, "saved_searches_enabled"
    )
    if not enabled:
        result.feature_disabled = True
        logger.info(
            "saved_search_notifier: saved_searches_enabled flag is off; "
            "skipping nightly run"
        )
        return result

    rows = await db.execute(
        select(SavedSearch).where(SavedSearch.notify_on_new.is_(True))
    )
    saved_searches = list(rows.scalars().all())

    now = datetime.now(timezone.utc)
    throttle_cutoff = now - THROTTLE_WINDOW

    for saved in saved_searches:
        result.rows_processed += 1

        last_run = saved.last_run_at
        if last_run is not None:
            if last_run.tzinfo is None:
                last_run = last_run.replace(tzinfo=timezone.utc)
            if last_run > throttle_cutoff:
                result.rows_skipped_throttle += 1
                logger.debug(
                    "saved_search_notifier: throttled search %s "
                    "(last_run_at=%s)",
                    saved.id,
                    last_run.isoformat(),
                )
                continue

        try:
            matches = await _new_matches_for_search(db, saved)
        except Exception as exc:
            result.rows_failed += 1
            result.errors.append(f"{saved.id}: {exc}")
            logger.exception(
                "saved_search_notifier: search execution failed for %s",
                saved.id,
            )
            continue

        if not matches:
            result.rows_skipped_no_matches += 1
            logger.info(
                "saved_search_notifier: no new matches search_id=%s user_id=%s",
                saved.id,
                saved.user_id,
            )
            continue

        patron = (
            await db.execute(select(User).where(User.id == saved.user_id))
        ).scalar_one_or_none()
        if patron is None:
            result.rows_failed += 1
            logger.warning(
                "saved_search_notifier: patron %s missing for search %s",
                saved.user_id,
                saved.id,
            )
            continue

        delivered = False
        if saved.notify_in_app:
            try:
                if await _record_in_app(db, saved, patron, matches):
                    result.in_app_sent += 1
                delivered = True
            except Exception as exc:
                result.rows_failed += 1
                result.errors.append(f"{saved.id} in_app: {exc}")
                logger.exception(
                    "saved_search_notifier: in-app insert failed for %s",
                    saved.id,
                )
                await db.rollback()
                continue

        if saved.notify_email:
            if await _deliver_email(saved, patron, matches):
                result.emails_sent += 1
                delivered = True

        if not delivered:
            result.rows_failed += 1
            continue

        saved.last_notified_item_id = max(i.id for i in matches)
        saved.last_run_at = now
        try:
            await db.commit()
        except Exception:
            logger.exception(
                "saved_search_notifier: failed to persist high-water mark "
                "for search %s",
                saved.id,
            )
            await db.rollback()
            result.rows_failed += 1
            continue

        result.rows_notified += 1
        logger.info(
            "saved_search_notifier: delivered search_id=%s user_id=%s "
            "matches=%d in_app=%s email=%s new_high_water=%d",
            saved.id,
            saved.user_id,
            len(matches),
            saved.notify_in_app,
            saved.notify_email,
            saved.last_notified_item_id,
        )

    logger.info(
        "saved_search_notifier: run complete processed=%d notified=%d "
        "no_matches=%d throttled=%d failed=%d in_app=%d emails=%d",
        result.rows_processed,
        result.rows_notified,
        result.rows_skipped_no_matches,
        result.rows_skipped_throttle,
        result.rows_failed,
        result.in_app_sent,
        result.emails_sent,
    )
    return result
