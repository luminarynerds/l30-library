# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Backend tests for the nightly saved-search new-arrival notifier.

Covers the contract:

* No new items -> no delivery, no DB writes.
* New items   -> exactly one delivery per channel; high-water mark
                 (``last_notified_item_id``) advances to the max id
                 in the delivered batch.
* 24h throttle: a search whose ``last_run_at`` is within the throttle
  window is silently skipped.
* Feature flag off -> notifier no-ops with ``feature_disabled=True``.
* Result aggregation: rows_processed / rows_notified counters are
  authoritative for downstream monitoring.

Mocks: :func:`send_email` is patched at the notifier's import site so
no real SMTP traffic is generated in CI.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.models.catalog import CatalogItem, ItemStatus, ItemType
from app.models.notification import (
    PatronNotification,
    PatronNotificationCategory,
)
from app.models.saved_search import SavedSearch
from app.models.user import User, UserRole
from app.services.saved_search_notifier import (
    NotifyResult,
    THROTTLE_WINDOW,
    notify_saved_searches,
)
from sqlalchemy import select


# -- helpers ----------------------------------------------------------------


async def _make_patron(
    test_db, email: str = "saved-search-patron@example.com"
) -> User:
    from app.core.security import hash_password

    user = User(
        email=email,
        password_hash=hash_password("Pa$$word123!"),
        first_name="Saved",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def _add_catalog_item(test_db, title: str) -> CatalogItem:
    item = CatalogItem(
        title=title,
        author="Author A",
        item_type=ItemType.book,
        status=ItemStatus.available,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


async def _add_saved_search(
    test_db,
    *,
    user_id: int,
    name: str = "Anything by Author A",
    notify_in_app: bool = True,
    notify_email: bool = False,
    last_notified_item_id: int | None = None,
    last_run_at: datetime | None = None,
    query: str | None = None,
) -> SavedSearch:
    saved = SavedSearch(
        user_id=user_id,
        name=name,
        query=query,
        filters_json={"author": "Author A"},
        notify_on_new=True,
        notify_in_app=notify_in_app,
        notify_email=notify_email,
        last_notified_item_id=last_notified_item_id,
        last_run_at=last_run_at,
    )
    test_db.add(saved)
    await test_db.commit()
    await test_db.refresh(saved)
    return saved


# Shared patch path for the feature-flag check. The notifier reads the
# org flag at the top of every run; we force-enable it for every test
# except the explicit feature-flag-off case.
_FEATURE_FLAG_PATH = (
    "app.services.saved_search_notifier."
    "OrganizationFeaturesService.is_feature_enabled"
)
_SEND_EMAIL_PATH = "app.services.saved_search_notifier.send_email"


# -- tests ------------------------------------------------------------------


class TestNoNewItems:
    """When nothing matches above the high-water mark, the notifier no-ops."""

    @pytest.mark.asyncio
    async def test_no_new_items_no_delivery_and_no_writes(self, test_db):
        patron = await _make_patron(test_db)
        # Catalog has matches, but the high-water mark is already past them.
        item = await _add_catalog_item(test_db, "Older Title")
        saved = await _add_saved_search(
            test_db,
            user_id=patron.id,
            last_notified_item_id=item.id,
        )

        with patch(_FEATURE_FLAG_PATH, new=AsyncMock(return_value=True)), patch(
            _SEND_EMAIL_PATH, new=AsyncMock(return_value=True)
        ) as mock_email:
            result = await notify_saved_searches(test_db)

        assert isinstance(result, NotifyResult)
        assert result.rows_processed == 1
        assert result.rows_notified == 0
        assert result.rows_skipped_no_matches == 1
        assert result.in_app_sent == 0
        assert result.emails_sent == 0
        assert mock_email.await_count == 0

        # No PatronNotification row written.
        notif_count = (
            await test_db.execute(
                select(PatronNotification).where(
                    PatronNotification.patron_id == patron.id
                )
            )
        ).scalars().all()
        assert notif_count == []

        # High-water mark untouched.
        await test_db.refresh(saved)
        assert saved.last_notified_item_id == item.id
        assert saved.last_run_at is None


class TestNewItemsDeliverOncePerChannel:
    """One in-app row + one email per saved search per run; HWM advances."""

    @pytest.mark.asyncio
    async def test_in_app_and_email_each_send_once_and_hwm_advances(
        self, test_db
    ):
        patron = await _make_patron(test_db)
        a = await _add_catalog_item(test_db, "First New Match")
        b = await _add_catalog_item(test_db, "Second New Match")
        saved = await _add_saved_search(
            test_db,
            user_id=patron.id,
            notify_in_app=True,
            notify_email=True,
            last_notified_item_id=None,
        )

        with patch(_FEATURE_FLAG_PATH, new=AsyncMock(return_value=True)), patch(
            _SEND_EMAIL_PATH, new=AsyncMock(return_value=True)
        ) as mock_email:
            result = await notify_saved_searches(test_db)

        assert result.rows_notified == 1
        assert result.in_app_sent == 1
        assert result.emails_sent == 1
        # Exactly one email per saved search per run.
        assert mock_email.await_count == 1

        # Exactly one in-app row, with the expected category.
        notifs = (
            await test_db.execute(
                select(PatronNotification).where(
                    PatronNotification.patron_id == patron.id
                )
            )
        ).scalars().all()
        assert len(notifs) == 1
        assert (
            notifs[0].category
            == PatronNotificationCategory.CATALOG_SAVED_SEARCH_MATCH
        )
        assert notifs[0].action_url == f"/catalog?saved={saved.id}"

        # High-water mark advances to max id of delivered batch.
        await test_db.refresh(saved)
        assert saved.last_notified_item_id == max(a.id, b.id)
        assert saved.last_run_at is not None


class TestThrottle:
    """A search alerted in the last 24h is skipped without re-delivery."""

    @pytest.mark.asyncio
    async def test_throttled_search_is_skipped(self, test_db):
        patron = await _make_patron(test_db)
        await _add_catalog_item(test_db, "Matches but too soon")

        # last_run_at is just inside the throttle window.
        recent = datetime.now(timezone.utc) - (THROTTLE_WINDOW / 2)
        saved = await _add_saved_search(
            test_db,
            user_id=patron.id,
            notify_in_app=True,
            notify_email=False,
            last_run_at=recent,
        )

        with patch(_FEATURE_FLAG_PATH, new=AsyncMock(return_value=True)), patch(
            _SEND_EMAIL_PATH, new=AsyncMock(return_value=True)
        ) as mock_email:
            result = await notify_saved_searches(test_db)

        assert result.rows_processed == 1
        assert result.rows_notified == 0
        assert result.rows_skipped_throttle == 1
        assert mock_email.await_count == 0

        # No notification row created during throttle window.
        notifs = (
            await test_db.execute(
                select(PatronNotification).where(
                    PatronNotification.patron_id == patron.id
                )
            )
        ).scalars().all()
        assert notifs == []

        # last_run_at unchanged (we did not run / advance anything).
        await test_db.refresh(saved)
        assert saved.last_run_at is not None
        # SQLite returns naive datetimes; normalize before comparing.
        actual = saved.last_run_at
        if actual.tzinfo is None:
            actual = actual.replace(tzinfo=timezone.utc)
        assert abs((actual - recent).total_seconds()) < 5


class TestFeatureFlagOff:
    """When the org disables the feature, every row no-ops without I/O."""

    @pytest.mark.asyncio
    async def test_feature_disabled_returns_early(self, test_db):
        patron = await _make_patron(test_db)
        await _add_catalog_item(test_db, "Would have matched")
        saved = await _add_saved_search(
            test_db,
            user_id=patron.id,
            notify_in_app=True,
            notify_email=True,
        )

        with patch(
            _FEATURE_FLAG_PATH, new=AsyncMock(return_value=False)
        ), patch(_SEND_EMAIL_PATH, new=AsyncMock(return_value=True)) as mock_email:
            result = await notify_saved_searches(test_db)

        assert result.feature_disabled is True
        assert result.rows_processed == 0
        assert result.rows_notified == 0
        assert mock_email.await_count == 0

        # State is untouched.
        await test_db.refresh(saved)
        assert saved.last_notified_item_id is None
        assert saved.last_run_at is None
        notifs = (
            await test_db.execute(
                select(PatronNotification).where(
                    PatronNotification.patron_id == patron.id
                )
            )
        ).scalars().all()
        assert notifs == []


class TestResultAggregation:
    """The NotifyResult counters power downstream monitoring."""

    @pytest.mark.asyncio
    async def test_counters_reflect_mixed_outcomes(self, test_db):
        patron = await _make_patron(test_db)
        item = await _add_catalog_item(test_db, "Fresh Title")

        # Three saved searches: one notifies, one no-matches, one throttled.
        await _add_saved_search(
            test_db,
            user_id=patron.id,
            name="Will deliver",
            notify_in_app=True,
        )
        await _add_saved_search(
            test_db,
            user_id=patron.id,
            name="Already caught up",
            notify_in_app=True,
            last_notified_item_id=item.id,
        )
        await _add_saved_search(
            test_db,
            user_id=patron.id,
            name="Throttled",
            notify_in_app=True,
            last_run_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )

        with patch(_FEATURE_FLAG_PATH, new=AsyncMock(return_value=True)), patch(
            _SEND_EMAIL_PATH, new=AsyncMock(return_value=True)
        ):
            result = await notify_saved_searches(test_db)

        assert result.rows_processed == 3
        assert result.rows_notified == 1
        assert result.rows_skipped_no_matches == 1
        assert result.rows_skipped_throttle == 1
        assert result.rows_failed == 0
        assert result.in_app_sent == 1
        assert result.emails_sent == 0
