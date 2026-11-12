# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guard test: user accessibility/UI preferences must NOT sit behind the
learning-platform feature gate.

Regression for the staff sidebar "won't collapse / flickers" bug: the
/api/v1/learning/preferences GET+PUT used to live on the learning-platform-gated
router, so disabling that org feature 404'd every preference save. The frontend
optimistically collapsed the sidebar, the PUT 404'd, and the rollback flickered
it back open. Preferences now mount on an ungated router (auth-only) while the
rest of the learning router stays gated.

The preferences-routing assertion is a pure route-table check (no DB) so it is
robust across SQLAlchemy versions — the prefs handler itself is pre-existing,
unchanged code. The companion test confirms a genuinely learning-gated endpoint
still 404s, proving only preferences were ungated.
"""

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.organization_features import OrganizationFeatures
from app.services.organization_features_service import OrganizationFeaturesService

PREFERENCES_PATH = "/api/v1/learning/preferences"


def test_preferences_routes_are_not_behind_learning_guard():
    """GET and PUT /api/v1/learning/preferences must carry no learning-platform
    guard dependency (they are global per-user settings, auth-only)."""
    by_method = {}
    for route in app.routes:
        if getattr(route, "path", "") != PREFERENCES_PATH:
            continue
        dep_names = [
            getattr(d.call, "__name__", "") for d in route.dependant.dependencies
        ]
        for method in route.methods or []:
            by_method[method] = dep_names

    for method in ("GET", "PUT"):
        assert method in by_method, f"{method} {PREFERENCES_PATH} not registered"
        learning_guards = [
            name for name in by_method[method] if "learning_platform" in name
        ]
        assert not learning_guards, (
            f"{method} {PREFERENCES_PATH} is still gated by {learning_guards}; "
            "preferences must be ungated so they persist when the learning "
            "platform feature is off."
        )


@pytest.fixture
def patron_client(client, test_patron):
    """Client that resolves get_current_user to a patron user."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def learning_disabled(test_db):
    """Turn the learning platform feature OFF for the org under test."""
    features = OrganizationFeatures(learning_platform_enabled=False)
    test_db.add(features)
    await test_db.commit()
    # Drop the Redis-backed snapshot so is_feature_enabled rereads from the DB.
    await OrganizationFeaturesService.invalidate_cache()
    yield
    await OrganizationFeaturesService.invalidate_cache()


@pytest.mark.asyncio
async def test_learning_lessons_still_gated_when_disabled(
    patron_client, learning_disabled
):
    """Only preferences were ungated; the rest of the learning router must
    still 404 when the feature is off."""
    response = await patron_client.get("/api/v1/learning/lessons/1/complete")
    assert response.status_code == 404, response.text
    body = response.json()
    detail = body.get("detail") or body.get("error", {}).get("message", "")
    assert "Learning platform" in detail, body
