# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Slice E: BIBFRAME data-integrity regression tests.

Targets the catalog<->BIBFRAME sync hardening:

- ``delete_from_catalog`` no longer falls back to title-only matching when
  the catalog row has no barcode. Title-only matches can delete an
  unrelated BibframeItem that happens to share a title.
- ``update_from_catalog`` now propagates ``publication_year`` to the
  BibframeInstance; it was silently omitted before.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.catalog_bibframe_sync import CatalogBibframeSync


@pytest.mark.asyncio
async def test_delete_from_catalog_without_barcode_skips_delete(caplog):
    """No barcode -> log warning and return; never call ``db.delete``.

    Previously this path fell through to a title-only ``WHERE`` and would
    happily delete a BibframeItem belonging to a different catalog row.
    """
    db = AsyncMock()
    # ``db.execute`` and ``db.delete`` should never be called when barcode
    # is None -- the function must return early.
    catalog_item = SimpleNamespace(id=42, barcode=None, title="Beloved")

    await CatalogBibframeSync.delete_from_catalog(db, catalog_item)

    db.execute.assert_not_called()
    db.delete.assert_not_called()
    db.flush.assert_not_called()


@pytest.mark.asyncio
async def test_delete_from_catalog_with_barcode_runs_lookup():
    """With a barcode, the lookup must run (regression coverage)."""
    db = AsyncMock()
    # The lookup query should run but find nothing -> no delete call.
    db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    catalog_item = SimpleNamespace(id=42, barcode="L30-0001", title="Beloved")

    await CatalogBibframeSync.delete_from_catalog(db, catalog_item)

    assert db.execute.await_count == 1
    db.delete.assert_not_called()
