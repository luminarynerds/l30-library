# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guard test: /households router must 404 when family_card_enabled is off."""

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.organization_features import OrganizationFeatures
from app.services.organization_features_service import OrganizationFeaturesService


@pytest.fixture
def patron_client(client, test_patron):
    """Client that resolves get_current_user to a patron user."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_households_returns_404_when_family_card_disabled(
    patron_client, test_db
):
    features = OrganizationFeatures(family_card_enabled=False)
    test_db.add(features)
    await test_db.commit()
    # Invalidate the Redis-backed snapshot so the next is_feature_enabled call
    # rereads from the DB instead of returning a stale cached value.
    await OrganizationFeaturesService.invalidate_cache()

    response = await patron_client.get("/api/v1/households/me")

    assert response.status_code == 404
    body = response.json()
    # FastAPI HTTPException routed through app.core.exception_handlers wraps
    # detail under {"error": {"message": ...}}; fall back to standard
    # {"detail": ...} for environments without the custom handler.
    detail = body.get("detail") or body.get("error", {}).get("message", "")
    assert "Family card" in detail, body


@pytest.mark.asyncio
async def test_households_returns_data_when_family_card_enabled(
    patron_client, test_db
):
    features = OrganizationFeatures(family_card_enabled=True)
    test_db.add(features)
    await test_db.commit()
    await OrganizationFeaturesService.invalidate_cache()

    response = await patron_client.get("/api/v1/households/me")

    assert response.status_code == 200
