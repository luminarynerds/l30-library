# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Multi-select author + series filter facets (PR 2 of catalog filter rollout).

Tests cover:
  - OR-within-group filter semantics for author + series
  - AND-across-groups (e.g. author + item_type)
  - 21-element list returns 400 on both params
  - Empty arrays are no-ops
  - NULL/empty author + series rows are excluded from facet aggregation
  - Own-predicate exclusion: selecting an author still shows other authors
    in the author facet output (the standard drill-down semantic)
"""
import pytest
from httpx import AsyncClient

from app.core.cache import invalidate_catalog_cache
from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)


pytestmark = pytest.mark.asyncio


async def _seed_item(
    db,
    *,
    title: str,
    author: str | None = "Author",
    series_name: str | None = None,
    item_type: ItemType = ItemType.book,
) -> CatalogItem:
    """Seed a publicly-visible catalog item."""
    item = CatalogItem(
        title=title,
        author=author,
        series_name=series_name,
        item_type=item_type,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )
    db.add(item)
    await db.flush()
    return item


# ---------------------------------------------------------------------------
# author_facets
# ---------------------------------------------------------------------------


async def test_author_facets_or_within_group(client: AsyncClient, db_session):
    """Selecting two authors returns items by either (distinct)."""
    await _seed_item(db_session, title="A", author="Spiegelman")
    await _seed_item(db_session, title="B", author="Satrapi")
    await _seed_item(db_session, title="C", author="Bechdel")
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("author_facets", "Spiegelman"), ("author_facets", "Satrapi")],
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"A", "B"}


async def test_author_facets_and_across_groups(client: AsyncClient, db_session):
    """`author_facets=X` AND `item_type=book` intersects correctly."""
    await _seed_item(db_session, title="Book", author="X", item_type=ItemType.book)
    await _seed_item(db_session, title="Dvd", author="X", item_type=ItemType.dvd)
    await _seed_item(db_session, title="OtherBook", author="Y", item_type=ItemType.book)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params={"author_facets": "X", "item_type": "book"},
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"Book"}


async def test_author_facets_length_cap_returns_400(client: AsyncClient):
    """More than 20 entries returns 400 (DoS guard)."""
    params = [("author_facets", f"A{i}") for i in range(21)]
    resp = await client.get("/api/v1/catalog/search", params=params)
    assert resp.status_code == 400
    assert "author_facets" in resp.json()["error"]["message"].lower()


async def test_author_facets_empty_array_is_noop(client: AsyncClient, db_session):
    await _seed_item(db_session, title="A", author="Spiegelman")
    await db_session.commit()
    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("author_facets", "")],
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# series_facets
# ---------------------------------------------------------------------------


async def test_series_facets_or_within_group(client: AsyncClient, db_session):
    await _seed_item(db_session, title="Maus I", series_name="Maus")
    await _seed_item(db_session, title="Persepolis 1", series_name="Persepolis")
    await _seed_item(db_session, title="Fun Home", series_name=None)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("series_facets", "Maus"), ("series_facets", "Persepolis")],
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"Maus I", "Persepolis 1"}


async def test_series_facets_and_across_groups(client: AsyncClient, db_session):
    await _seed_item(db_session, title="Maus book", series_name="Maus", item_type=ItemType.book)
    await _seed_item(db_session, title="Maus dvd", series_name="Maus", item_type=ItemType.dvd)
    await _seed_item(db_session, title="Other book", series_name="Other", item_type=ItemType.book)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params={"series_facets": "Maus", "item_type": "book"},
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"Maus book"}


async def test_series_facets_length_cap_returns_400(client: AsyncClient):
    params = [("series_facets", f"S{i}") for i in range(21)]
    resp = await client.get("/api/v1/catalog/search", params=params)
    assert resp.status_code == 400
    assert "series_facets" in resp.json()["error"]["message"].lower()


async def test_series_facets_empty_array_is_noop(client: AsyncClient, db_session):
    await _seed_item(db_session, title="A", series_name="Maus")
    await db_session.commit()
    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("series_facets", "")],
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1


# ---------------------------------------------------------------------------
# facet aggregation (own-predicate-excluded + null/empty exclusion)
# ---------------------------------------------------------------------------


async def test_author_facet_aggregation_excludes_null_and_empty(
    client: AsyncClient, db_session
):
    """The author facet output skips NULL + whitespace-only authors."""
    await _seed_item(db_session, title="A", author="Spiegelman")
    await _seed_item(db_session, title="B", author="Spiegelman")
    await _seed_item(db_session, title="C", author=None)
    await _seed_item(db_session, title="D", author="   ")
    await db_session.commit()
    # The search endpoint caches its response (including facets) in Redis
    # keyed by query params; since tests write directly via the ORM
    # (bypassing the API create path that normally invalidates this cache
    # on writes), a same-shaped request from an earlier test can return a
    # stale cached facets payload. Invalidate before requesting.
    await invalidate_catalog_cache()

    resp = await client.get(
        "/api/v1/catalog/search", params={"include_facets": "true"}
    )
    assert resp.status_code == 200, resp.text
    facets = resp.json().get("facets") or {}
    author_facet = facets.get("author") or []
    values = {row["value"] for row in author_facet}
    assert "Spiegelman" in values
    assert None not in values
    assert "" not in values
    assert "   " not in values


async def test_series_facet_aggregation_excludes_null_and_empty(
    client: AsyncClient, db_session
):
    await _seed_item(db_session, title="A", series_name="Maus")
    await _seed_item(db_session, title="B", series_name="Maus")
    await _seed_item(db_session, title="C", series_name=None)
    await _seed_item(db_session, title="D", series_name=" ")
    await db_session.commit()
    # See test_author_facet_aggregation_excludes_null_and_empty above: this
    # test issues the identical request (same query params -> same cache
    # key), so without invalidating first it can be served the other
    # test's stale cached facets response.
    await invalidate_catalog_cache()

    resp = await client.get(
        "/api/v1/catalog/search", params={"include_facets": "true"}
    )
    assert resp.status_code == 200, resp.text
    facets = resp.json().get("facets") or {}
    series_facet = facets.get("series") or []
    values = {row["value"] for row in series_facet}
    assert "Maus" in values
    assert None not in values
    assert "" not in values
    assert " " not in values


async def test_author_facet_own_predicate_excluded(
    client: AsyncClient, db_session
):
    """Selecting an author still shows other authors in the author facet.

    Drill-down semantic: the author facet output must not collapse to just
    the selected author — patrons need to see what else is selectable.
    """
    await _seed_item(db_session, title="A", author="Spiegelman")
    await _seed_item(db_session, title="B", author="Satrapi")
    await _seed_item(db_session, title="C", author="Bechdel")
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("author_facets", "Spiegelman"), ("include_facets", "true")],
    )
    assert resp.status_code == 200, resp.text
    facets = resp.json().get("facets") or {}
    values = {row["value"] for row in (facets.get("author") or [])}
    # Selected author still appears, AND the other authors are still
    # surfaced so the patron can swap selection.
    assert {"Spiegelman", "Satrapi", "Bechdel"}.issubset(values)


async def test_series_facet_own_predicate_excluded(
    client: AsyncClient, db_session
):
    await _seed_item(db_session, title="A", series_name="Maus")
    await _seed_item(db_session, title="B", series_name="Persepolis")
    await _seed_item(db_session, title="C", series_name="Fun Home")
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("series_facets", "Maus"), ("include_facets", "true")],
    )
    assert resp.status_code == 200, resp.text
    facets = resp.json().get("facets") or {}
    values = {row["value"] for row in (facets.get("series") or [])}
    assert {"Maus", "Persepolis", "Fun Home"}.issubset(values)
