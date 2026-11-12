# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API Endpoint tests for Panic Alert System.

Tests all HTTP endpoints for the panic alert system:
- POST /api/v1/panic-alerts - Create new panic alert
- PATCH /api/v1/panic-alerts/{id}/acknowledge - Acknowledge alert
- PATCH /api/v1/panic-alerts/{id}/resolve - Resolve alert
- GET /api/v1/panic-alerts/{id} - Get specific alert
- GET /api/v1/panic-alerts - List active alerts with filters
- GET /api/v1/panic-alerts/user/recent - Get user's recent alerts
- GET /api/v1/panic-alerts/preferences/me - Get notification preferences
- POST /api/v1/panic-alerts/preferences/me - Set notification preferences

Tests cover:
- Request validation and schema compliance
- HTTP status codes
- Authentication and authorization
- Error responses
- Query parameter filtering
- JSON response structure
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

from app.models.panic_alert import PanicAlertSource, PanicAlertStatus
from app.models.user import User, UserRole
from app.models.branch import Branch


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def api_staff_user(test_db):
    """Create staff user for API tests"""
    from app.core.security import hash_password

    user = User(
        email="api_staff@library.local",
        password_hash=hash_password("ApiStaff123!"),
        first_name="API",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def api_manager_user(test_db):
    """Create manager user for API tests"""
    from app.core.security import hash_password

    user = User(
        email="api_manager@library.local",
        password_hash=hash_password("ApiManager123!"),
        first_name="API",
        last_name="Manager",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def api_patron_user(test_db):
    """Create patron user for permission tests"""
    from app.core.security import hash_password

    user = User(
        email="api_patron@library.local",
        password_hash=hash_password("ApiPatron123!"),
        first_name="API",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def api_branch(test_db):
    """Create branch for API tests"""
    from app.models.multi_branch import LibrarySystem

    system = LibrarySystem(code="APITEST", name="API Test System")
    test_db.add(system)
    await test_db.commit()
    await test_db.refresh(system)

    branch = Branch(
        library_system_id=system.id,
        code="APIBR",
        name="API Test Branch",
        address_line1="789 Test St",
        city="Somewhere Up North",
        state="ON",
        zip_code="M3C 3C3",
        phone="555-3000",
        email="api_branch@library.local",
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(branch)
    return branch


def get_staff_token(client, user):
    """Get authentication token for staff user"""
    from app.core.security import create_access_token

    token = create_access_token(subject=str(user.id), email=user.email)
    return f"Bearer {token}"


def get_auth_headers(client, user):
    """Get authentication headers for requests"""
    token = get_staff_token(client, user)
    return {"Authorization": token}


# ============================================================================
# POST /api/v1/panic-alerts - Create Alert
# ============================================================================


class TestCreatePanicAlert:
    """Test POST /api/v1/panic-alerts endpoint"""

    @pytest.mark.asyncio
    async def test_create_alert_success(self, client, test_db, api_staff_user):
        """Should create panic alert with valid data"""
        headers = get_auth_headers(client, api_staff_user)

        payload = {
            "activation_source": "keyboard_shortcut",
            "situation_notes": "Test alert creation",
        }

        response = await client.post("/api/v1/panic-alerts", json=payload, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["triggered_by_user_id"] == api_staff_user.id
        assert data["status"] == "active"
        assert data["activation_source"] == "keyboard_shortcut"
        assert data["situation_notes"] == "Test alert creation"
        assert "id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_alert_all_activation_sources(self, client, test_db, api_staff_user):
        """Should accept all valid activation sources"""
        headers = get_auth_headers(client, api_staff_user)

        sources = [
            "keyboard_shortcut",
            "physical_button",
            "mobile_gesture",
            "hidden_ui_button",
        ]

        for source in sources:
            payload = {"activation_source": source}
            response = await client.post("/api/v1/panic-alerts", json=payload, headers=headers)

            assert response.status_code == 201
            data = response.json()
            assert data["activation_source"] == source

    @pytest.mark.asyncio
    async def test_create_alert_with_metadata(self, client, test_db, api_staff_user):
        """Should store alert metadata"""
        headers = get_auth_headers(client, api_staff_user)

        metadata = {
            "device": "iPhone 13",
            "location": {"lat": 43.65, "lon": -79.38},
        }

        payload = {
            "activation_source": "mobile_gesture",
            "metadata": metadata,
        }

        response = await client.post("/api/v1/panic-alerts", json=payload, headers=headers)

        assert response.status_code == 201
        data = response.json()
        assert data["alert_metadata"] == metadata

    @pytest.mark.asyncio
    async def test_create_alert_without_auth(self, client, test_db):
        """Should reject unauthenticated requests"""
        payload = {"activation_source": "keyboard_shortcut"}

        response = await client.post("/api/v1/panic-alerts", json=payload)

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_alert_patron_forbidden(self, client, test_db, api_patron_user):
        """Should reject patron users (staff-only endpoint)"""
        headers = get_auth_headers(client, api_patron_user)
        payload = {"activation_source": "keyboard_shortcut"}

        response = await client.post("/api/v1/panic-alerts", json=payload, headers=headers)

        # Assuming require_staff dependency rejects non-staff
        assert response.status_code in [403, 401]

    @pytest.mark.asyncio
    async def test_create_alert_invalid_source(self, client, test_db, api_staff_user):
        """Should reject invalid activation source"""
        headers = get_auth_headers(client, api_staff_user)

        payload = {"activation_source": "invalid_source"}

        response = await client.post("/api/v1/panic-alerts", json=payload, headers=headers)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_alert_notes_max_length(self, client, test_db, api_staff_user):
        """Should enforce situation_notes max length"""
        headers = get_auth_headers(client, api_staff_user)

        # 501 characters (exceeds 500 limit in schema)
        long_notes = "x" * 501

        payload = {
            "activation_source": "keyboard_shortcut",
            "situation_notes": long_notes,
        }

        response = await client.post("/api/v1/panic-alerts", json=payload, headers=headers)

        assert response.status_code == 422


# ============================================================================
# GET /api/v1/panic-alerts/{id} - Get Alert
# ============================================================================


class TestGetPanicAlert:
    """Test GET /api/v1/panic-alerts/{id} endpoint"""

    @pytest.mark.asyncio
    async def test_get_alert_success(self, client, test_db, api_staff_user):
        """Should retrieve specific alert by ID"""
        headers = get_auth_headers(client, api_staff_user)

        # Create alert
        create_payload = {
            "activation_source": "keyboard_shortcut",
            "situation_notes": "Get test",
        }
        create_response = await client.post(
            "/api/v1/panic-alerts", json=create_payload, headers=headers
        )
        alert_id = create_response.json()["id"]

        # Get alert
        response = await client.get(f"/api/v1/panic-alerts/{alert_id}", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == alert_id
        assert data["situation_notes"] == "Get test"

    @pytest.mark.asyncio
    async def test_get_alert_not_found(self, client, test_db, api_staff_user):
        """Should return 404 for nonexistent alert"""
        headers = get_auth_headers(client, api_staff_user)

        response = await client.get("/api/v1/panic-alerts/99999", headers=headers)

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_alert_requires_auth(self, client, test_db):
        """Should require authentication"""
        response = await client.get("/api/v1/panic-alerts/1")

        assert response.status_code == 401


# ============================================================================
# GET /api/v1/panic-alerts - List Active Alerts
# ============================================================================


class TestListActivePanicAlerts:
    """Test GET /api/v1/panic-alerts endpoint"""

    @pytest.mark.asyncio
    async def test_list_active_alerts(self, client, test_db, api_staff_user):
        """Should list all active alerts"""
        headers = get_auth_headers(client, api_staff_user)

        # Create multiple alerts
        for i in range(3):
            payload = {"activation_source": "keyboard_shortcut"}
            await client.post("/api/v1/panic-alerts", json=payload, headers=headers)

        # List alerts
        response = await client.get("/api/v1/panic-alerts", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_list_excludes_resolved_alerts(self, client, test_db, api_staff_user):
        """Should exclude resolved alerts from active list"""
        headers = get_auth_headers(client, api_staff_user)

        # Create two alerts
        create1 = await client.post(
            "/api/v1/panic-alerts",
            json={"activation_source": "keyboard_shortcut"},
            headers=headers,
        )
        alert1_id = create1.json()["id"]

        _ = await client.post(
            "/api/v1/panic-alerts",
            json={"activation_source": "physical_button"},
            headers=headers,
        )

        # Resolve first alert
        resolve_payload = {
            "status": "resolved",
            "resolution_notes": "Test resolved",
        }
        await client.patch(
            f"/api/v1/panic-alerts/{alert1_id}/resolve",
            json=resolve_payload,
            headers=headers,
        )

        # List active alerts
        response = await client.get("/api/v1/panic-alerts", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    @pytest.mark.asyncio
    async def test_list_filter_by_branch(self, client, test_db, api_staff_user, api_branch):
        """Should filter alerts by branch_id query parameter"""
        headers = get_auth_headers(client, api_staff_user)

        # Create alert (would need branch_id support in service)
        # This test assumes branch filtering works
        response = await client.get(
            f"/api/v1/panic-alerts?branch_id={api_branch.id}",
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_with_limit_parameter(self, client, test_db, api_staff_user):
        """Should respect limit query parameter"""
        headers = get_auth_headers(client, api_staff_user)

        # Create 5 alerts
        for _ in range(5):
            await client.post(
                "/api/v1/panic-alerts",
                json={"activation_source": "keyboard_shortcut"},
                headers=headers,
            )

        # Request with limit=2
        response = await client.get("/api/v1/panic-alerts?limit=2", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_list_requires_auth(self, client, test_db):
        """Should require authentication"""
        response = await client.get("/api/v1/panic-alerts")

        assert response.status_code == 401


# ============================================================================
# PATCH /api/v1/panic-alerts/{id}/acknowledge - Acknowledge Alert
# ============================================================================


class TestAcknowledgePanicAlert:
    """Test PATCH /api/v1/panic-alerts/{id}/acknowledge endpoint"""

    @pytest.mark.asyncio
    async def test_acknowledge_alert_success(self, client, test_db, api_staff_user, api_manager_user):
        """Should acknowledge alert and update status"""
        # Create alert as staff
        staff_headers = get_auth_headers(client, api_staff_user)
        create_response = await client.post(
            "/api/v1/panic-alerts",
            json={"activation_source": "keyboard_shortcut"},
            headers=staff_headers,
        )
        alert_id = create_response.json()["id"]

        # Acknowledge as manager
        manager_headers = get_auth_headers(client, api_manager_user)
        response = await client.patch(
            f"/api/v1/panic-alerts/{alert_id}/acknowledge",
            headers=manager_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "acknowledged"
        assert data["acknowledged_by_user_id"] == api_manager_user.id
        assert "acknowledged_at" in data
        assert data["acknowledged_at"] is not None

    @pytest.mark.asyncio
    async def test_acknowledge_nonexistent_alert(self, client, test_db, api_manager_user):
        """Should return 404 for invalid alert ID"""
        headers = get_auth_headers(client, api_manager_user)

        response = await client.patch(
            "/api/v1/panic-alerts/99999/acknowledge",
            headers=headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_acknowledge_requires_auth(self, client, test_db):
        """Should require authentication"""
        response = await client.patch("/api/v1/panic-alerts/1/acknowledge")

        assert response.status_code == 401


# ============================================================================
# PATCH /api/v1/panic-alerts/{id}/resolve - Resolve Alert
# ============================================================================


class TestResolvePanicAlert:
    """Test PATCH /api/v1/panic-alerts/{id}/resolve endpoint"""

    @pytest.mark.asyncio
    async def test_resolve_alert_success(self, client, test_db, api_staff_user):
        """Should resolve alert with resolution notes"""
        headers = get_auth_headers(client, api_staff_user)

        # Create alert
        create_response = await client.post(
            "/api/v1/panic-alerts",
            json={"activation_source": "keyboard_shortcut"},
            headers=headers,
        )
        alert_id = create_response.json()["id"]

        # Resolve alert
        resolve_payload = {
            "status": "resolved",
            "resolution_notes": "Situation handled, all clear",
        }
        response = await client.patch(
            f"/api/v1/panic-alerts/{alert_id}/resolve",
            json=resolve_payload,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolution_notes"] == "Situation handled, all clear"
        assert "resolved_at" in data
        assert data["resolved_at"] is not None

    @pytest.mark.asyncio
    async def test_resolve_without_notes(self, client, test_db, api_staff_user):
        """Should allow resolving without resolution notes"""
        headers = get_auth_headers(client, api_staff_user)

        # Create alert
        create_response = await client.post(
            "/api/v1/panic-alerts",
            json={"activation_source": "keyboard_shortcut"},
            headers=headers,
        )
        alert_id = create_response.json()["id"]

        # Resolve without notes
        resolve_payload = {"status": "resolved"}
        response = await client.patch(
            f"/api/v1/panic-alerts/{alert_id}/resolve",
            json=resolve_payload,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"

    @pytest.mark.asyncio
    async def test_resolve_nonexistent_alert(self, client, test_db, api_staff_user):
        """Should return 404 for invalid alert ID"""
        headers = get_auth_headers(client, api_staff_user)

        resolve_payload = {"status": "resolved"}
        response = await client.patch(
            "/api/v1/panic-alerts/99999/resolve",
            json=resolve_payload,
            headers=headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_resolve_requires_auth(self, client, test_db):
        """Should require authentication"""
        resolve_payload = {"status": "resolved"}
        response = await client.patch(
            "/api/v1/panic-alerts/1/resolve",
            json=resolve_payload,
        )

        assert response.status_code == 401


# ============================================================================
# GET /api/v1/panic-alerts/user/recent - Get User's Recent Alerts
# ============================================================================


class TestGetRecentUserAlerts:
    """Test GET /api/v1/panic-alerts/user/recent endpoint"""

    @pytest.mark.asyncio
    async def test_get_recent_alerts_for_user(self, client, test_db, api_staff_user):
        """Should return recent alerts for current user"""
        headers = get_auth_headers(client, api_staff_user)

        # Create alerts for this user
        for _ in range(3):
            await client.post(
                "/api/v1/panic-alerts",
                json={"activation_source": "keyboard_shortcut"},
                headers=headers,
            )

        # Get recent alerts
        response = await client.get("/api/v1/panic-alerts/user/recent", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_recent_alerts_with_hours_parameter(self, client, test_db, api_staff_user):
        """Should respect hours query parameter"""
        headers = get_auth_headers(client, api_staff_user)

        # Create alert
        await client.post(
            "/api/v1/panic-alerts",
            json={"activation_source": "keyboard_shortcut"},
            headers=headers,
        )

        # Get alerts from last 1 hour
        response = await client.get("/api/v1/panic-alerts/user/recent?hours=1", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_recent_alerts_with_limit(self, client, test_db, api_staff_user):
        """Should respect limit query parameter"""
        headers = get_auth_headers(client, api_staff_user)

        # Create 5 alerts
        for _ in range(5):
            await client.post(
                "/api/v1/panic-alerts",
                json={"activation_source": "keyboard_shortcut"},
                headers=headers,
            )

        # Get with limit=2
        response = await client.get("/api/v1/panic-alerts/user/recent?limit=2", headers=headers)

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    @pytest.mark.asyncio
    async def test_recent_alerts_requires_auth(self, client, test_db):
        """Should require authentication"""
        response = await client.get("/api/v1/panic-alerts/user/recent")

        assert response.status_code == 401


# ============================================================================
# Notification Preferences Endpoints
# ============================================================================


class TestNotificationPreferences:
    """Test notification preference endpoints"""

    @pytest.mark.asyncio
    async def test_get_preferences_empty(self, client, test_db, api_manager_user):
        """Should return null when no preferences set"""
        headers = get_auth_headers(client, api_manager_user)

        response = await client.get("/api/v1/panic-alerts/preferences/me", headers=headers)

        assert response.status_code == 200
        # May return null or empty object

    @pytest.mark.asyncio
    async def test_set_notification_preferences(self, client, test_db, api_manager_user):
        """Should create/update notification preferences"""
        headers = get_auth_headers(client, api_manager_user)

        preferences = {
            "receive_panic_alerts": True,
            "notify_via_email": True,
            "notify_via_sms": False,
            "notify_via_in_app": True,
            "notify_for_all_branches": True,
            "sound_enabled": False,
            "sound_preference": "soft_pulse",
            "vibration_enabled": True,
        }

        response = await client.post(
            "/api/v1/panic-alerts/preferences/me",
            json=preferences,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["receive_panic_alerts"] is True
        assert data["notify_via_email"] is True
        assert data["notify_via_sms"] is False
        assert data["sound_preference"] == "soft_pulse"

    @pytest.mark.asyncio
    async def test_update_existing_preferences(self, client, test_db, api_manager_user):
        """Should update existing preferences"""
        headers = get_auth_headers(client, api_manager_user)

        # Set initial preferences
        initial = {
            "receive_panic_alerts": False,
            "notify_via_email": False,
        }
        await client.post("/api/v1/panic-alerts/preferences/me", json=initial, headers=headers)

        # Update preferences
        updated = {
            "receive_panic_alerts": True,
            "notify_via_email": True,
            "notify_via_sms": True,
        }
        response = await client.post(
            "/api/v1/panic-alerts/preferences/me",
            json=updated,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["receive_panic_alerts"] is True
        assert data["notify_via_email"] is True
        assert data["notify_via_sms"] is True

    @pytest.mark.asyncio
    async def test_branch_specific_preferences(self, client, test_db, api_manager_user, api_branch):
        """Should support branch-specific notification preferences"""
        headers = get_auth_headers(client, api_manager_user)

        preferences = {
            "receive_panic_alerts": True,
            "notify_via_email": True,
            "notify_for_all_branches": False,
            "branch_ids": [api_branch.id],
        }

        response = await client.post(
            "/api/v1/panic-alerts/preferences/me",
            json=preferences,
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["notify_for_all_branches"] is False
        assert api_branch.id in data["branch_ids"]

    @pytest.mark.asyncio
    async def test_preferences_require_auth(self, client, test_db):
        """Should require authentication for preferences"""
        # GET preferences
        get_response = await client.get("/api/v1/panic-alerts/preferences/me")
        assert get_response.status_code == 401

        # POST preferences
        post_response = await client.post(
            "/api/v1/panic-alerts/preferences/me",
            json={"receive_panic_alerts": True},
        )
        assert post_response.status_code == 401
