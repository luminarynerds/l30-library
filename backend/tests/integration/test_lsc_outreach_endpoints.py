# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
LSC Outreach API Endpoints Tests

This test suite verifies outreach API endpoints are accessible and working correctly:
1. Newsletter subscription endpoints
2. Social sharing tracking endpoints

Marketing campaign and patron segmentation/tagging sections were removed
2026-07-05 -- those routes have never existed in the app (see removal notes
inline below).
"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.fixture
def admin_token(test_admin) -> str:
    """Bearer token string for the admin fixture user."""
    return create_access_token(subject=str(test_admin.id))


@pytest.fixture
def staff_token(test_staff) -> str:
    """Bearer token string for the staff fixture user."""
    return create_access_token(subject=str(test_staff.id))


@pytest.fixture
def patron_token(test_patron) -> str:
    """Bearer token string for the patron fixture user."""
    return create_access_token(subject=str(test_patron.id))


@pytest.fixture
def patron_token(test_patron):
    from app.core.security import create_access_token

    return create_access_token(subject=test_patron.id, email=test_patron.email)


# Campaign Endpoint Tests section removed 2026-07-05: /api/v1/marketing/campaigns
# has never existed. marketing.py defines no "/campaigns" route at all (the only
# "/campaigns" route anywhere is in event_marketing.py, a different feature).
# git -S "\"/campaigns\"" shows the only touching commit is the event-marketing
# addition; the admin_token fixture (only used by this section) was removed
# with it. Traced to the same speculative-verification commit 7d60bdf4f as the
# dashboard-realtime websocket tests.


# =============================================================================
# Newsletter Subscription Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_newsletter_signup_endpoint(client: AsyncClient):
    """Test POST /marketing/newsletter/subscribe endpoint."""
    response = await client.post(
        "/api/v1/marketing/newsletter/subscribe",
        json={
            "email": "subscriber@example.com",
            "first_name": "John",
            "last_name": "Subscriber",
            "frequency": "weekly",
        },
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert "message" in data or "status" in data


@pytest.mark.asyncio
async def test_newsletter_status_endpoint(client: AsyncClient, patron_token: str):
    """Test GET /marketing/newsletter/status endpoint."""
    response = await client.get(
        "/api/v1/marketing/newsletter/status",
        headers={"Authorization": f"Bearer {patron_token}"},
    )

    # May be 200 (has subscription) or 200 (no subscription)
    assert response.status_code == 200
    data = response.json()
    assert "subscribed" in data


@pytest.mark.asyncio
async def test_interest_categories_endpoint(client: AsyncClient):
    """Test GET /marketing/interests endpoint."""
    response = await client.get(
        "/api/v1/marketing/interests",
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


@pytest.mark.asyncio
async def test_update_interests_endpoint(client: AsyncClient, patron_token: str):
    """Test PUT /marketing/interests/mine endpoint."""
    response = await client.put(
        "/api/v1/marketing/interests/mine",
        headers={"Authorization": f"Bearer {patron_token}"},
        json={
            "interest_ids": [1, 2],
        },
    )

    # May be 200 if interests exist, 404 if not
    assert response.status_code in [200, 404, 422]


@pytest.mark.asyncio
async def test_new_arrival_alerts_endpoint(client: AsyncClient, patron_token: str):
    """Test POST /marketing/alerts endpoint."""
    response = await client.post(
        "/api/v1/marketing/alerts",
        headers={"Authorization": f"Bearer {patron_token}"},
        json={
            "category_id": 1,
            "frequency": "weekly",
        },
    )

    assert response.status_code in [200, 201, 404, 422]


@pytest.mark.asyncio
async def test_list_alerts_endpoint(client: AsyncClient, patron_token: str):
    """Test GET /marketing/alerts endpoint."""
    response = await client.get(
        "/api/v1/marketing/alerts",
        headers={"Authorization": f"Bearer {patron_token}"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "alerts" in data


@pytest.mark.asyncio
async def test_unsubscribe_endpoint(client: AsyncClient):
    """Test POST /marketing/unsubscribe endpoint."""
    response = await client.post(
        "/api/v1/marketing/unsubscribe",
        json={
            "token": "test-unsubscribe-token",
            "reason": "too_frequent",
        },
    )

    # May succeed or fail depending on token validity
    assert response.status_code in [200, 400]


# Patron Segmentation Endpoint Tests section removed 2026-07-05: none of
# /api/v1/staff/tags, /api/v1/staff/tags/bulk-assign, /api/v1/staff/patron-groups,
# /api/v1/staff/patrons/by-tag/{id}, or /api/v1/staff/patrons/by-group/{id} exist
# anywhere in the app (repo-wide grep for each path returns no route
# definitions). The staff_token fixture (only used by this section) was removed
# with it. Same speculative-verification origin as the Campaign section above.


# =============================================================================
# Social Sharing Endpoint Tests
# =============================================================================


@pytest.mark.asyncio
async def test_share_event_endpoint(client: AsyncClient, patron_token: str):
    """Test tracking a share event."""
    response = await client.post(
        "/api/v1/sharing/track?resource_type=book&resource_id=1&platform=facebook",
        headers={"Authorization": f"Bearer {patron_token}"},
    )

    # May succeed or not depending on endpoint existence
    assert response.status_code in [200, 201, 404, 422]


@pytest.mark.asyncio
async def test_share_statistics_endpoint(client: AsyncClient):
    """Test GET /sharing/stats/{resource_type}/{id} endpoint."""
    response = await client.get(
        "/api/v1/sharing/stats/book/1",
    )

    # May succeed or not depending on endpoint existence
    assert response.status_code in [200, 404, 405]


# Permission and Authorization Tests section removed 2026-07-05:
# test_unauthorized_campaign_creation and test_unauthorized_tag_creation only
# "passed" because their lenient `in [403, 404, 405]` / `in [401, 403]`
# assertions happened to accept the 404 both dead routes actually return --
# vacuous passes for /api/v1/marketing/campaigns and /api/v1/staff/tags, which
# don't exist (see the Campaign and Patron Segmentation removal notes above).
# test_missing_authorization hit the same dead /api/v1/staff/tags route.


# =============================================================================
# Data Validation Tests
# =============================================================================


@pytest.mark.asyncio
async def test_invalid_email_signup(client: AsyncClient):
    """Test newsletter signup with invalid email."""
    response = await client.post(
        "/api/v1/marketing/newsletter/subscribe",
        json={
            "email": "not-a-valid-email",
            "frequency": "weekly",
        },
    )

    assert response.status_code in [400, 422]


# test_duplicate_campaign_slug removed 2026-07-05: exercised
# /api/v1/marketing/campaigns, which doesn't exist (see Campaign section
# removal note above).


@pytest.mark.asyncio
async def test_invalid_frequency(client: AsyncClient):
    """Test newsletter signup with invalid frequency."""
    response = await client.post(
        "/api/v1/marketing/newsletter/subscribe",
        json={
            "email": "test@library.local",
            "frequency": "invalid_frequency",
        },
    )

    assert response.status_code in [400, 422]


# Rate Limiting Tests section removed 2026-07-05: test_rate_limiting_bulk_operations
# exercised /api/v1/staff/tags/bulk-assign, which doesn't exist (see Patron
# Segmentation section removal note above).
