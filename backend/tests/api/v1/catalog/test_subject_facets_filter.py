# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Multi-select subject filter (`subject_facets`) -- completes PR #607.

Tests cover:
  - OR-within-group filter semantics via the join table
  - AND-across-groups with item_type
  - Length cap at 20 (returns 400)
  - Legacy `subject: str` ILIKE param still works (regression)
  - Empty array is a no-op
"""
import pytest
from httpx import AsyncClient

from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from app.models.subject import CatalogItemSubject, Subject


pytestmark = pytest.mark.asyncio


async def _seed_subjects(db, *labels: str) -> list[Subject]:
    subjects = [Subject(label=lbl, slug=lbl.lower().strip()) for lbl in labels]
    db.add_all(subjects)
    await db.flush()
    return subjects


async def _seed_item(
    db,
    *,
    title: str,
    author: str = "Author",
    item_type: ItemType = ItemType.book,
) -> CatalogItem:
    """Seed a publicly-visible catalog item for search-endpoint tests."""
    item = CatalogItem(
        title=title,
        author=author,
        item_type=item_type,
        status=ItemStatus.available,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )
    db.add(item)
    await db.flush()
    return item


async def _link(db, item: CatalogItem, *subjects: Subject) -> None:
    for i, s in enumerate(subjects):
        db.add(
            CatalogItemSubject(
                catalog_item_id=item.id, subject_id=s.id, position=i
            )
        )
    await db.flush()


async def test_subject_facets_or_within_group(
    client: AsyncClient, db_session
):
    """Selecting two subjects returns items matching EITHER (distinct)."""
    fic, hist, sci = await _seed_subjects(
        db_session, "Fiction", "History", "Science"
    )
    a = await _seed_item(db_session, title="A")
    b = await _seed_item(db_session, title="B")
    c = await _seed_item(db_session, title="C")
    await _link(db_session, a, fic)
    await _link(db_session, b, hist)
    await _link(db_session, c, sci)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("subject_facets", "Fiction"), ("subject_facets", "History")],
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"A", "B"}


async def test_subject_facets_and_across_groups(
    client: AsyncClient, db_session
):
    """`subject_facets=Fiction` AND `item_type=book` intersects correctly."""
    (fic,) = await _seed_subjects(db_session, "Fiction")
    book = await _seed_item(db_session, title="Book", item_type=ItemType.book)
    dvd = await _seed_item(
        db_session, title="Dvd", item_type=ItemType.dvd
    )
    other_book = await _seed_item(db_session, title='OtherBook', author='A', item_type=ItemType.book)
    await _link(db_session, book, fic)
    await _link(db_session, dvd, fic)
    # other_book intentionally has no subjects -- proves subject_facets is enforced
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search",
        params={"subject_facets": "Fiction", "item_type": "book"},
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert titles == {"Book"}


async def test_subject_facets_length_cap_returns_400(client: AsyncClient):
    """More than 20 entries returns 400 (DoS guard)."""
    params = [("subject_facets", f"S{i}") for i in range(21)]
    resp = await client.get("/api/v1/catalog/search", params=params)
    assert resp.status_code == 400
    assert "subject_facets" in resp.json()["error"]["message"].lower()


async def test_legacy_subject_param_still_works(
    client: AsyncClient, db_session
):
    """Regression: legacy `subject: str` param continues to work via ILIKE."""
    (fic,) = await _seed_subjects(db_session, "Historical Fiction")
    a = await _seed_item(db_session, title="A")
    await _link(db_session, a, fic)
    await db_session.commit()

    resp = await client.get(
        "/api/v1/catalog/search", params={"subject": "histor"}
    )
    assert resp.status_code == 200, resp.text
    titles = {row["title"] for row in resp.json()["items"]}
    assert "A" in titles


async def test_subject_facets_empty_array_is_noop(
    client: AsyncClient, db_session
):
    """Passing no `subject_facets` returns the full set (no filter applied)."""
    await _seed_item(db_session, title="A")
    await db_session.commit()
    resp = await client.get(
        "/api/v1/catalog/search",
        params=[("subject_facets", "")],
    )
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
