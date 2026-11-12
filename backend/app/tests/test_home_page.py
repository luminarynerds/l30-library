# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the data-driven home page (PR A — backend)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.models.catalog import CatalogingStatus, CatalogItem, ItemType
from app.models.home import (
    HomeHeroPick,
    HomePageConfig,
    HomeShelf,
    HomeShelfQueryKind,
)
from app.models.staff_picks import StaffPicksItem, StaffPicksList
from app.services.home_page import resolve_home_page


# ---------------------------------------------------------------------------
# Model / enum unit tests (no DB session needed)
# ---------------------------------------------------------------------------


class TestHomeShelfQueryKind:
    def test_values_are_lowercase(self):
        # Per [[feedback_l30_enum_case]] L30 enum values must be lowercase.
        for k in HomeShelfQueryKind:
            assert k.value == k.value.lower()
            assert "_" in k.value or k.value.islower()

    def test_all_kinds_present(self):
        expected = {
            "new_arrivals",
            "staff_picks",
            "subject",
            "format",
            "circulation_top",
            "manual_list",
        }
        assert {k.value for k in HomeShelfQueryKind} == expected


class TestHomeModelsShape:
    def test_hero_picks_tablename(self):
        assert HomeHeroPick.__tablename__ == "home_hero_picks"

    def test_shelves_tablename(self):
        assert HomeShelf.__tablename__ == "home_shelves"

    def test_config_tablename(self):
        assert HomePageConfig.__tablename__ == "home_page_config"

    def test_hero_required_columns(self):
        cols = {c.name for c in HomeHeroPick.__table__.columns}
        assert {
            "id",
            "item_id",
            "annotation_md",
            "cta_label",
            "active_from",
            "active_to",
        }.issubset(cols)

    def test_shelf_required_columns(self):
        cols = {c.name for c in HomeShelf.__table__.columns}
        assert {
            "id",
            "slug",
            "heading",
            "query_kind",
            "query_params",
            "sort_order",
            "is_active",
            "max_items",
        }.issubset(cols)

    def test_catalog_item_has_home_columns(self):
        # PR A adds staff_pick + featured_at to catalog_items.
        cols = {c.name for c in CatalogItem.__table__.columns}
        assert "staff_pick" in cols
        assert "featured_at" in cols


# ---------------------------------------------------------------------------
# Service-level tests against the real PG test DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_resolve_home_page_empty_db(db):
    """Empty DB → empty payload, no crash."""
    payload = await resolve_home_page(db, use_cache=False)
    assert payload.config is None
    assert payload.hero is None
    assert payload.shelves == []


@pytest.mark.asyncio
async def test_resolve_home_page_full_happy_path(db):
    """End-to-end happy path covering hero window + several query_kinds.

    Bundled into one test on purpose: per
    [[feedback_l30_async_pytest_one_at_a_time]] the second async-PG test in a
    session can blow up with "Event loop is closed"; a single rich test
    exercises more behavior with less fixture churn.
    """
    now = datetime.now(timezone.utc)

    # --- Catalog seed -------------------------------------------------------
    items = []
    for i in range(6):
        items.append(
            CatalogItem(
                title=f"Item {i}",
                author=f"Author {i}",
                item_type=ItemType.book,
                subjects="Fiction, Mystery",
                cataloging_status=CatalogingStatus.CATALOGED,
            )
        )
    db.add_all(items)
    await db.commit()
    for it in items:
        await db.refresh(it)

    # --- Staff picks list: feeds the staff-picks shelf (newest added first) -
    sp_list = StaffPicksList(title="Staff Picks", is_active=True)
    db.add(sp_list)
    await db.commit()
    await db.refresh(sp_list)
    db.add_all([
        # items[0] added most recently -> sorts first on the shelf
        StaffPicksItem(list_id=sp_list.id, catalog_item_id=items[1].id, added_at=now - timedelta(hours=1)),
        StaffPicksItem(list_id=sp_list.id, catalog_item_id=items[0].id, added_at=now),
    ])
    await db.commit()

    # --- Page config --------------------------------------------------------
    db.add(
        HomePageConfig(
            id=1,
            eyebrow="From the staff",
            hero_visible=True,
            picks_link_label="See all picks",
            picks_link_href="/picks",
        )
    )
    await db.commit()

    # --- Hero picks: one active, one outside-window -------------------------
    db.add(
        HomeHeroPick(
            item_id=items[0].id,
            annotation_md="**Staff pick** of the week.",
            cta_label="Place hold",
            active_from=now - timedelta(days=1),
            active_to=now + timedelta(days=7),
        )
    )
    db.add(
        HomeHeroPick(
            item_id=items[1].id,
            annotation_md="Old hero.",
            cta_label="Place hold",
            active_from=now - timedelta(days=30),
            active_to=now - timedelta(days=2),
        )
    )
    await db.commit()

    # --- Shelves: new_arrivals, staff_picks, subject (matches), and an
    #             empty subject shelf that should be dropped from the payload.
    db.add_all(
        [
            HomeShelf(
                slug="new-this-week",
                heading="New this week",
                description="Just on the shelf",
                query_kind=HomeShelfQueryKind.new_arrivals.value,
                query_params={},
                sort_order=10,
                is_active=True,
                max_items=4,
            ),
            HomeShelf(
                slug="staff-picks",
                heading="Staff picks",
                description="Hand-picked",
                query_kind=HomeShelfQueryKind.staff_picks.value,
                query_params={},
                sort_order=20,
                is_active=True,
                max_items=6,
            ),
            HomeShelf(
                slug="mystery",
                heading="Mystery",
                description="",
                query_kind=HomeShelfQueryKind.subject.value,
                query_params={"subject": "Mystery"},
                sort_order=30,
                is_active=True,
                max_items=6,
            ),
            HomeShelf(
                slug="no-matches",
                heading="Empty",
                description="",
                query_kind=HomeShelfQueryKind.subject.value,
                query_params={"subject": "SubjectThatMatchesNothing"},
                sort_order=40,
                is_active=True,
                max_items=6,
            ),
            HomeShelf(
                slug="circ-top",
                heading="Most checked out",
                description="",
                query_kind=HomeShelfQueryKind.circulation_top.value,
                query_params={"window_days": 30},
                sort_order=50,
                is_active=True,
                max_items=6,
            ),
            HomeShelf(
                slug="manual",
                heading="Editor's pick",
                description="",
                query_kind=HomeShelfQueryKind.manual_list.value,
                query_params={"item_ids": [items[3].id, items[2].id]},
                sort_order=60,
                is_active=True,
                max_items=6,
            ),
            HomeShelf(
                slug="inactive",
                heading="Hidden",
                description="",
                query_kind=HomeShelfQueryKind.new_arrivals.value,
                query_params={},
                sort_order=70,
                is_active=False,
                max_items=6,
            ),
        ]
    )
    await db.commit()

    payload = await resolve_home_page(db, use_cache=False)

    # Hero: the active-window pick wins.
    assert payload.hero is not None
    assert payload.hero.item.id == items[0].id

    # Config surfaces.
    assert payload.config is not None
    assert payload.config.eyebrow == "From the staff"
    assert payload.config.picks_link_href == "/picks"

    # Empty + circulation_top + inactive shelves all omitted.
    slugs = [s.slug for s in payload.shelves]
    assert "no-matches" not in slugs
    assert "circ-top" not in slugs  # stub returns []
    assert "inactive" not in slugs

    # Ordered by sort_order.
    assert slugs == ["new-this-week", "staff-picks", "mystery", "manual"]

    by_slug = {s.slug: s for s in payload.shelves}

    # new_arrivals respects max_items=4.
    assert len(by_slug["new-this-week"].items) == 4

    # staff_picks shows items from active staff-picks lists, newest added first.
    sp = by_slug["staff-picks"].items
    assert len(sp) == 2
    assert {it.id for it in sp} == {items[0].id, items[1].id}
    assert sp[0].id == items[0].id  # items[0] added most recently

    # subject substring matches all 6 (all have "Mystery" in subjects).
    assert len(by_slug["mystery"].items) == 6

    # manual_list preserves admin-specified order.
    manual = by_slug["manual"].items
    assert [it.id for it in manual] == [items[3].id, items[2].id]


# ---------------------------------------------------------------------------
# Admin RBAC + cache-busting (unit-level, mocked Redis)
# ---------------------------------------------------------------------------


def test_admin_router_is_role_gated():
    """The admin sub-router must require ADMIN or SUPER_ADMIN."""
    from app.api.v1 import home_page as home_routes

    # Router has a router-level dependency that calls require_role(...).
    assert home_routes.admin_router.dependencies, (
        "admin_router must have a role-gating dependency"
    )


@pytest.mark.asyncio
async def test_bust_home_page_cache_calls_redis_delete(monkeypatch):
    """Admin writes must bust the public-page Redis key."""
    from app.services import home_page as svc

    class FakeRedis:
        def __init__(self):
            self.deleted = []

        async def delete(self, key):
            self.deleted.append(key)

    fake = FakeRedis()

    async def fake_get_redis():
        return fake

    monkeypatch.setattr(svc, "get_redis", fake_get_redis)

    await svc.bust_home_page_cache()
    assert fake.deleted == [svc.HOME_PAGE_CACHE_KEY]
