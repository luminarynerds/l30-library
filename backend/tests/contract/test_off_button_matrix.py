# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
The OFF-button contract.

L30's differentiator is that any org feature module can be switched off
without taking anything else down with it. This asserts that contract as
a property, parametrized over every toggle on `OrganizationFeatures` so
newly added flags are automatically exercised without editing this file.

Two properties per flag:

1. No-cascade disable: disabling flag X causes no failure in unrelated
   parts of the app -- the app still boots (health check), an
   authenticated patron can still reach their own profile, and the
   public catalog can still be browsed.
2. Always-export: the patron data-portability export
   (GET /api/v1/privacy/export) still succeeds and still returns the
   patron's real data, regardless of which single flag is off.

Row set source: `OrganizationFeatures` (backend/app/models/organization_features.py)
is the canonical, code-level definition of every toggleable module -- it
requires no running Redis to enumerate (Redis only caches a snapshot of
these same columns; see OrganizationFeaturesService). This is a superset
of `FEATURE_REGISTRY` in app/api/v1/feature_guards.py, which only lists
flags that registered an HTTP guard via `_make_feature_guard` -- three
model columns (`front_desk_enabled`, `home_visit_safety_enabled`,
`home_visit_day_plan_enabled`) are gated by hand-written guards elsewhere
and never call that factory, so they're invisible to FEATURE_REGISTRY.
Reflecting the model instead of importing FEATURE_REGISTRY keeps this
suite's coverage complete even though the two lists disagree.
"""

from __future__ import annotations

import pytest

from app.core.security import create_access_token
from app.models.favorite import Favorite
from app.models.organization_features import OrganizationFeatures
from app.services.organization_features_service import OrganizationFeaturesService

# Every boolean toggle column on the model -- the matrix's row set.
ALL_FLAGS: list[str] = sorted(
    column.name
    for column in OrganizationFeatures.__table__.columns
    if column.name.endswith("_enabled")
)

assert len(ALL_FLAGS) >= 60, (
    f"Expected dozens of org feature flags, found {len(ALL_FLAGS)}. "
    "If OrganizationFeatures was refactored, update this guard."
)


def _patron_headers(user) -> dict:
    token = create_access_token(subject=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
async def _fresh_redis_client_per_test():
    """`app.core.cache.get_redis()` caches its client at module scope,
    bound to whichever event loop was running when it was first created.
    pytest-asyncio's default per-test event loop means a client created
    in one parametrized case is already dead in the next; the resulting
    `RuntimeError: Event loop is closed` isn't a RedisError, so the cache
    layer's `except (RedisError, TypeError)` doesn't catch it and it
    blows up the test instead of failing open like it would in prod
    (prod has one long-lived event loop, so this never triggers there).
    Reset the cached client so every test in this module gets a fresh
    connection bound to its own loop.
    """
    import app.core.cache as cache_module

    cache_module.redis_client = None
    yield
    cache_module.redis_client = None


async def _disable_flag(db, admin, flag_key: str) -> None:
    """Disable exactly one flag via the canonical service path (not a
    direct DB write) so cache invalidation behaves like it would in
    production -- see feedback_l30_feature_flag_add_checklist."""
    await OrganizationFeaturesService.update_features(
        db,
        {flag_key: False, "reason": "off-button contract test"},
        admin,
    )


# ---------------------------------------------------------------------------
# Property 1: no-cascade disable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag_key", ALL_FLAGS)
@pytest.mark.asyncio
async def test_disabling_flag_causes_no_cascade_failure(
    client, test_db, test_admin, test_patron, test_catalog_item, flag_key
):
    await _disable_flag(test_db, test_admin, flag_key)

    # Sanity: the toggle actually took effect. If this fails, the test
    # below would be vacuous (asserting nothing was broken by a flag that
    # was never really off).
    assert (
        await OrganizationFeaturesService.is_feature_enabled(test_db, flag_key)
        is False
    ), f"{flag_key} did not read back as disabled after update_features()"

    # Anchor 1: the app still boots and answers health checks.
    health = await client.get("/api/v1/health")
    assert health.status_code == 200, (
        f"disabling {flag_key} broke /api/v1/health: {health.status_code} {health.text}"
    )
    assert health.json()["status"] == "ok"

    # Anchor 2: an unrelated authenticated patron endpoint still works.
    me = await client.get("/api/v1/users/me", headers=_patron_headers(test_patron))
    assert me.status_code == 200, (
        f"disabling {flag_key} broke GET /users/me: {me.status_code} {me.text}"
    )
    assert me.json()["email"] == test_patron.email

    # Anchor 3: catalog lookup still works and still queries real data
    # (not a short-circuited empty/error response). Staff auth avoids the
    # unrelated (by design) cataloging_status/sensitivity_level visibility
    # filters that public/patron requests are subject to -- this anchor is
    # about the module boundary, not catalog visibility rules. The lookup
    # is keyed by item id (unique per test), so it can't read a stale
    # cached response left behind by an earlier parametrized case.
    admin_headers = _patron_headers(test_admin)
    catalog = await client.get(
        f"/api/v1/catalog/items/{test_catalog_item.id}", headers=admin_headers
    )
    assert catalog.status_code == 200, (
        f"disabling {flag_key} broke GET /catalog/items/{{id}}: "
        f"{catalog.status_code} {catalog.text}"
    )
    assert catalog.json()["id"] == test_catalog_item.id


# ---------------------------------------------------------------------------
# Property 2: always-export
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("flag_key", ALL_FLAGS)
@pytest.mark.asyncio
async def test_export_always_succeeds_with_flag_disabled(
    client,
    test_db,
    test_admin,
    test_patron,
    test_catalog_item,
    test_checkout,
    test_hold,
    test_fine,
    flag_key,
):
    await _disable_flag(test_db, test_admin, flag_key)

    favorite = Favorite(user_id=test_patron.id, catalog_item_id=test_catalog_item.id)
    test_db.add(favorite)
    await test_db.commit()

    resp = await client.get(
        "/api/v1/privacy/export", headers=_patron_headers(test_patron)
    )
    assert resp.status_code == 200, (
        f"disabling {flag_key} broke GET /privacy/export: {resp.status_code} {resp.text}"
    )

    data = resp.json()
    assert data["profile"]["email"] == test_patron.email
    assert len(data["checkouts"]) == 1, f"checkout missing from export with {flag_key} off"
    assert len(data["holds"]) == 1, f"hold missing from export with {flag_key} off"
    assert len(data["fines"]) == 1, f"fine missing from export with {flag_key} off"
    assert len(data["favorites"]) == 1, f"favorite missing from export with {flag_key} off"
