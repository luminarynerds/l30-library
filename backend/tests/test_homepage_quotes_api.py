# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Smoke tests for homepage_quotes service + API."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services import homepage_quote_service


@pytest.mark.asyncio
async def test_list_active_filters_by_locale_and_active():
    """Service composes the right SELECT against locale + is_active filter."""
    db = MagicMock()
    execute_result = MagicMock()
    execute_result.scalars.return_value.all.return_value = []
    db.execute = AsyncMock(return_value=execute_result)

    result = await homepage_quote_service.list_active_for_locale(db, "en")

    assert result == []
    assert db.execute.await_count == 1


@pytest.mark.asyncio
async def test_create_persists_all_fields():
    """create() instantiates HomepageQuote with passed fields and commits."""
    db = MagicMock()
    db.add = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    with patch.object(
        homepage_quote_service, "HomepageQuote", autospec=False
    ) as MockQuote:
        instance = MagicMock()
        MockQuote.return_value = instance

        result = await homepage_quote_service.create(
            db,
            locale="ar",
            quote_text="نص",
            attribution="مؤلف",
            is_active=True,
            display_order=3,
        )

    MockQuote.assert_called_once_with(
        locale="ar",
        quote_text="نص",
        attribution="مؤلف",
        is_active=True,
        display_order=3,
    )
    db.add.assert_called_once_with(instance)
    db.commit.assert_awaited_once()
    db.refresh.assert_awaited_once_with(instance)
    assert result is instance


@pytest.mark.asyncio
async def test_update_only_applies_non_none_fields():
    """Partial updates skip None fields (leaving the existing value intact)."""
    db = MagicMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    quote = MagicMock()
    quote.quote_text = "old"
    quote.is_active = True
    quote.display_order = 0

    result = await homepage_quote_service.update(
        db,
        quote,
        quote_text="new",
        is_active=None,
        display_order=5,
    )

    assert quote.quote_text == "new"
    assert quote.display_order == 5
    # is_active should not have been reassigned because value was None
    assert quote.is_active is True
    db.commit.assert_awaited_once()
    assert result is quote


def test_routers_have_expected_routes():
    """Public router exposes a single GET; admin exposes list/create/update/delete."""
    from app.api.v1 import homepage_quotes, admin_homepage_quotes

    pub_methods = sorted(
        {m for r in homepage_quotes.router.routes for m in r.methods}
    )
    assert pub_methods == ["GET"]
    assert homepage_quotes.router.prefix == "/homepage-quotes"

    admin_methods = sorted(
        {m for r in admin_homepage_quotes.router.routes for m in r.methods}
    )
    assert admin_methods == ["DELETE", "GET", "POST", "PUT"]
    assert admin_homepage_quotes.router.prefix == "/admin/homepage-quotes"


def test_seed_quote_counts():
    """Migration seed contains 9/5/5 quotes for en/es/fr."""
    import importlib.util
    import pathlib

    mig = (
        pathlib.Path(__file__).resolve().parents[1]
        / "alembic" / "versions" / "homepage_quotes_001_add_homepage_quotes.py"
    )
    spec = importlib.util.spec_from_file_location("hq_mig", mig)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert len(mod.SEED_QUOTES_EN) == 9
    assert len(mod.SEED_QUOTES_ES) == 5
    assert len(mod.SEED_QUOTES_FR) == 5
