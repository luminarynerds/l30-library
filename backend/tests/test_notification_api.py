# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the Notification Preferences API endpoints.

These exercise the canonical preferences router (api/v1/notification_preferences.py)
against the UserNotificationPreference model: per-type channel preferences,
digest configuration, and quiet hours.

NOTE: this file was rewritten when PR #1119 removed the dead, shadowed
GET/PUT /notifications/preferences endpoints from api/v1/notifications.py.
The pre-#1119 version asserted the legacy flat ``email_*`` shape (the
NotificationPreferences model) and a ``/notifications/history`` endpoint that
was never implemented in the codebase. Both are gone; these tests target the
shape the app actually serves.

Authenticated tests override ``get_current_user`` (the ``staff_client``
conftest pattern) rather than logging in for real: the test environment has
no Redis, so live JWT verification fails token-revocation lookup and 401s.
"""

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.notification_preference import UserNotificationPreference
from app.services.notification_preferences_service import DEFAULT_NOTIFICATION_TYPES


@pytest.fixture
async def patron_client(test_db, test_patron):
    """Async HTTP client authenticated as the test patron.

    Mirrors the conftest ``staff_client`` fixture: overrides ``get_current_user``
    so the route runs as ``test_patron`` without a real login round-trip.
    """
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_patron

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


class TestNotificationPreferencesAPI:
    """GET/PUT /notifications/preferences against the canonical API."""

    @pytest.mark.asyncio
    async def test_user_can_get_notification_preferences(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """A patron can retrieve full notification settings."""
        response = await patron_client.get("/api/v1/notifications/preferences")

        assert response.status_code == 200
        data = response.json()
        # FullNotificationSettings: preferences + digest + quiet_hours
        assert "preferences" in data
        assert "digest" in data
        assert "quiet_hours" in data
        assert len(data["preferences"]) == len(DEFAULT_NOTIFICATION_TYPES)

    @pytest.mark.asyncio
    async def test_user_can_update_notification_preferences(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """A patron can bulk-update per-type channel preferences."""
        response = await patron_client.put(
            "/api/v1/notifications/preferences",
            json={
                "preferences": [
                    {
                        "notification_type": "checkout_receipt",
                        "label": "Checkout Receipt",
                        "channel_email": False,
                        "channel_in_app": True,
                        "channel_sms": False,
                        "is_digest": False,
                    },
                    {
                        "notification_type": "due_date_reminder",
                        "label": "Due Date Reminder",
                        "channel_email": True,
                        "channel_in_app": True,
                        "channel_sms": False,
                        "is_digest": False,
                    },
                ]
            },
        )

        assert response.status_code == 200
        data = response.json()
        by_type = {p["notification_type"]: p for p in data["preferences"]}
        assert by_type["checkout_receipt"]["channel_email"] is False
        assert by_type["due_date_reminder"]["channel_email"] is True

        # Verify persisted to the canonical model
        result = await test_db.execute(
            select(UserNotificationPreference).where(
                UserNotificationPreference.user_id == test_patron.id
            )
        )
        pref = result.scalar_one()
        assert pref.channel_preferences["checkout_receipt"]["email"] is False

    @pytest.mark.asyncio
    async def test_user_can_opt_out_of_specific_notification_types(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """A patron can turn the email channel off for a single type."""
        response = await patron_client.put(
            "/api/v1/notifications/preferences",
            json={
                "preferences": [
                    {
                        "notification_type": "checkout_receipt",
                        "label": "Checkout Receipt",
                        "channel_email": False,
                        "channel_in_app": True,
                        "channel_sms": False,
                        "is_digest": False,
                    }
                ]
            },
        )

        assert response.status_code == 200
        by_type = {p["notification_type"]: p for p in response.json()["preferences"]}
        assert by_type["checkout_receipt"]["channel_email"] is False
        # Types not in the update keep their defaults.
        assert by_type["due_date_reminder"]["channel_email"] is True

    @pytest.mark.asyncio
    async def test_creates_default_preferences_for_user_with_none(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """A patron with no saved row still gets a full default set."""
        response = await patron_client.get("/api/v1/notifications/preferences")

        assert response.status_code == 200
        data = response.json()
        assert len(data["preferences"]) == len(DEFAULT_NOTIFICATION_TYPES)
        for pref in data["preferences"]:
            assert pref["channel_email"] is True
            assert pref["channel_in_app"] is True
            assert pref["channel_sms"] is False


class TestDigestConfigAPI:
    """GET/PUT /notifications/digest-config."""

    @pytest.mark.asyncio
    async def test_get_digest_config_defaults(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """Digest config defaults to disabled / daily."""
        response = await patron_client.get("/api/v1/notifications/digest-config")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["frequency"] == "daily"

    @pytest.mark.asyncio
    async def test_update_digest_config_persists(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """Updating digest config persists and is retrievable."""
        response = await patron_client.put(
            "/api/v1/notifications/digest-config",
            json={
                "enabled": True,
                "frequency": "weekly",
                "preferred_time": "18:00",
                "preferred_day": 4,
            },
        )
        assert response.status_code == 200
        assert response.json()["frequency"] == "weekly"

        response = await patron_client.get("/api/v1/notifications/digest-config")
        data = response.json()
        assert data["enabled"] is True
        assert data["frequency"] == "weekly"
        assert data["preferred_time"] == "18:00"
        assert data["preferred_day"] == 4


class TestQuietHoursAPI:
    """GET/PUT /notifications/quiet-hours."""

    @pytest.mark.asyncio
    async def test_get_quiet_hours_defaults(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """Quiet hours default to disabled with a 22:00-08:00 window."""
        response = await patron_client.get("/api/v1/notifications/quiet-hours")

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is False
        assert data["start_time"] == "22:00"

    @pytest.mark.asyncio
    async def test_update_quiet_hours_persists(
        self, patron_client, test_db: AsyncSession, test_patron: User
    ):
        """Updating quiet hours persists and is retrievable."""
        response = await patron_client.put(
            "/api/v1/notifications/quiet-hours",
            json={
                "enabled": True,
                "start_time": "23:00",
                "end_time": "07:00",
                "days": [0, 1, 2, 3, 4],
            },
        )
        assert response.status_code == 200

        response = await patron_client.get("/api/v1/notifications/quiet-hours")
        data = response.json()
        assert data["enabled"] is True
        assert data["start_time"] == "23:00"
        assert data["days"] == [0, 1, 2, 3, 4]


class TestNotificationAPIAuthentication:
    """Authentication requirements for the preferences endpoints."""

    @pytest.mark.asyncio
    async def test_requires_authentication_to_access_preferences(self, client):
        """Accessing preferences without a token is rejected."""
        response = await client.get("/api/v1/notifications/preferences")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_requires_authentication_to_update_preferences(self, client):
        """Updating preferences without a token is rejected."""
        response = await client.put(
            "/api/v1/notifications/preferences",
            json={"preferences": []},
        )
        assert response.status_code in (401, 403)
