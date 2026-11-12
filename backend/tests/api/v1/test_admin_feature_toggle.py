# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for admin feature toggle endpoints.

Covers:
- GET /api/v1/organization-features (public, no auth)
- PUT /api/v1/organization-features (admin-only update)
- PATCH /api/v1/organization-features (admin-only partial update)
- GET /api/v1/organization-features/check/{feature_name} (public feature check)
- Authorization: admin required for PUT/PATCH, non-admin blocked
- Service layer: default creation, singleton pattern, feature checking
"""

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.organization_features import OrganizationFeatures
from app.models.user import User, UserRole


# ==================== Auth Override Fixtures ====================
# Override get_current_user to avoid Redis dependency for token revocation.


@pytest.fixture
def admin_client(client, test_admin):
    """Client that resolves get_current_user to the admin user."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    """Client that resolves get_current_user to a patron user."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client(client, test_staff):
    """Client that resolves get_current_user to a staff user."""
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def seeded_features(test_db):
    """Seed the organization_features table with a known row."""
    features = OrganizationFeatures(
        gamification_enabled=True,
        reading_programs_enabled=True,
        board_features_enabled=True,
        training_modules_enabled=True,
        community_features_enabled=True,
        email_notifications_enabled=True,
        banned_books_tracking_enabled=True,
        patron_portal_enabled=True,
        self_checkout_enabled=True,
        enabled_focus_modes=["pomodoro", "zen", "timed"],
        enabled_themes=["light", "dark", "high-contrast"],
        enabled_fonts=["default", "dyslexia-friendly", "large"],
        default_daily_goal_minutes=30,
        max_holds_per_patron=10,
        max_checkouts_per_patron=5,
        configuration={},
    )
    test_db.add(features)
    await test_db.commit()
    await test_db.refresh(features)
    return features


# ==================== GET /organization-features (Public) ====================


class TestGetOrganizationFeatures:
    """GET endpoint is public – no auth required."""

    @pytest.mark.asyncio
    async def test_get_features_returns_defaults_when_empty(self, client):
        """When no row exists, the service auto-creates defaults."""
        response = await client.get("/api/v1/organization-features")
        assert response.status_code == 200

        data = response.json()
        # Check default boolean toggles
        assert data["gamification_enabled"] is True
        assert data["reading_programs_enabled"] is True
        assert data["board_features_enabled"] is True
        assert data["training_modules_enabled"] is True
        assert data["community_features_enabled"] is True
        assert data["email_notifications_enabled"] is True
        assert data["banned_books_tracking_enabled"] is True
        assert data["patron_portal_enabled"] is True
        assert data["self_checkout_enabled"] is True

    @pytest.mark.asyncio
    async def test_get_features_returns_numeric_defaults(self, client):
        response = await client.get("/api/v1/organization-features")
        assert response.status_code == 200

        data = response.json()
        assert data["default_daily_goal_minutes"] == 30
        assert data["max_holds_per_patron"] == 10
        assert data["max_checkouts_per_patron"] == 5

    @pytest.mark.asyncio
    async def test_get_features_returns_seeded_data(self, client, seeded_features):
        """When a row exists, return it."""
        response = await client.get("/api/v1/organization-features")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == seeded_features.id
        assert data["enabled_themes"] == ["light", "dark", "high-contrast"]

    @pytest.mark.asyncio
    async def test_get_features_no_auth_required(self, client):
        """Endpoint should work without any Authorization header."""
        response = await client.get("/api/v1/organization-features")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_features_has_metadata_fields(self, client, seeded_features):
        response = await client.get("/api/v1/organization-features")
        data = response.json()

        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "updated_by_id" in data


# ==================== PUT /organization-features (Admin Only) ====================


class TestPutOrganizationFeatures:
    """PUT endpoint requires admin authentication."""

    @pytest.mark.asyncio
    async def test_admin_can_update_single_toggle(self, admin_client, test_admin, seeded_features):
        """Admin can toggle a single feature off."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={"gamification_enabled": False},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["gamification_enabled"] is False
        # Other toggles remain unchanged
        assert data["reading_programs_enabled"] is True
        assert data["board_features_enabled"] is True

    @pytest.mark.asyncio
    async def test_admin_can_update_multiple_toggles(
        self, admin_client, test_admin, seeded_features
    ):
        """Admin can toggle multiple features at once."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={
                "gamification_enabled": False,
                "email_notifications_enabled": False,
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["gamification_enabled"] is False
        assert data["email_notifications_enabled"] is False

    @pytest.mark.asyncio
    async def test_admin_can_update_numeric_config(self, admin_client, test_admin, seeded_features):
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={
                "default_daily_goal_minutes": 60,
                "max_holds_per_patron": 20,
                "max_checkouts_per_patron": 10,
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["default_daily_goal_minutes"] == 60
        assert data["max_holds_per_patron"] == 20
        assert data["max_checkouts_per_patron"] == 10

    @pytest.mark.asyncio
    async def test_admin_can_update_array_configs(self, admin_client, test_admin, seeded_features):
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={
                "enabled_themes": ["light", "dark", "ocean", "forest"],
                "enabled_focus_modes": ["pomodoro"],
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["enabled_themes"] == ["light", "dark", "ocean", "forest"]
        assert data["enabled_focus_modes"] == ["pomodoro"]

    @pytest.mark.asyncio
    async def test_admin_update_sets_audit_fields(self, admin_client, test_admin, seeded_features):
        """Update should record who made the change."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={"gamification_enabled": False, "reason": "Testing audit trail"},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["updated_by_id"] == test_admin.id
        assert data["updated_at"] is not None

    @pytest.mark.asyncio
    async def test_patron_cannot_put_features(self, patron_client, test_patron, seeded_features):
        """Non-admin users should be blocked with 403."""
        response = await patron_client.put(
            "/api/v1/organization-features",
            json={"gamification_enabled": False},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_staff_cannot_put_features(self, staff_client, test_staff, seeded_features):
        """Staff (non-admin) users should also be blocked."""
        response = await staff_client.put(
            "/api/v1/organization-features",
            json={"gamification_enabled": False},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_put_returns_401(self, client):
        """No token at all should return 401."""
        response = await client.put(
            "/api/v1/organization-features",
            json={"gamification_enabled": False},
        )
        assert response.status_code == 401


# ==================== PATCH /organization-features (Admin Only) ====================


class TestPatchOrganizationFeatures:
    """PATCH endpoint - same auth as PUT, partial update."""

    @pytest.mark.asyncio
    async def test_admin_can_patch_single_feature(self, admin_client, test_admin, seeded_features):
        response = await admin_client.patch(
            "/api/v1/organization-features",
            json={"banned_books_tracking_enabled": False},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["banned_books_tracking_enabled"] is False
        # Unmodified fields stay the same
        assert data["gamification_enabled"] is True

    @pytest.mark.asyncio
    async def test_patron_cannot_patch_features(self, patron_client, test_patron, seeded_features):
        response = await patron_client.patch(
            "/api/v1/organization-features",
            json={"gamification_enabled": False},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_unauthenticated_patch_returns_401(self, client):
        response = await client.patch(
            "/api/v1/organization-features",
            json={"gamification_enabled": False},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_customer_display_default_off_and_admin_can_enable(
        self, admin_client, test_admin, seeded_features
    ):
        # Default OFF: most desks have no second monitor (opt-in per library).
        get_resp = await admin_client.get("/api/v1/organization-features")
        assert get_resp.status_code == 200
        assert get_resp.json()["customer_display_enabled"] is False

        # Admin can flip it on; PATCH persists the change.
        patch_resp = await admin_client.patch(
            "/api/v1/organization-features",
            json={"customer_display_enabled": True},
            headers={"Authorization": "Bearer fake"},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["customer_display_enabled"] is True


# ==================== GET /organization-features/check/{feature_name} ====================


class TestCheckFeatureEnabled:
    """Public endpoint for quick single-feature checks."""

    @pytest.mark.asyncio
    async def test_check_enabled_feature(self, client, seeded_features):
        response = await client.get("/api/v1/organization-features/check/gamification_enabled")
        assert response.status_code == 200

        data = response.json()
        assert data["feature_name"] == "gamification_enabled"
        assert data["enabled"] is True

    @pytest.mark.asyncio
    async def test_check_unknown_feature_returns_false(self, client, seeded_features):
        """Unknown feature names fail open (getattr default is True) -- see
        OrganizationFeaturesService.is_feature_enabled, which deliberately
        defaults to True in both the DB-lookup and table-missing fallback
        paths so an undeclared/unmigrated feature check never accidentally
        disables a feature."""
        response = await client.get("/api/v1/organization-features/check/nonexistent_feature")
        assert response.status_code == 200
        assert response.json()["enabled"] is True

    @pytest.mark.asyncio
    async def test_check_no_auth_required(self, client, seeded_features):
        """Feature check is public."""
        response = await client.get("/api/v1/organization-features/check/gamification_enabled")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_check_reflects_admin_update(self, admin_client, test_admin, seeded_features):
        """After admin toggles a feature off, check endpoint should reflect it."""
        await admin_client.patch(
            "/api/v1/organization-features",
            json={"gamification_enabled": False},
            headers={"Authorization": "Bearer fake"},
        )

        response = await admin_client.get(
            "/api/v1/organization-features/check/gamification_enabled"
        )
        assert response.status_code == 200
        assert response.json()["enabled"] is False


# ==================== Edge Cases & Validation ====================


class TestFeatureToggleEdgeCases:
    """Edge cases and validation."""

    @pytest.mark.asyncio
    async def test_empty_update_body_succeeds(self, admin_client, test_admin, seeded_features):
        """An empty update should succeed (no fields changed)."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_with_reason_field(self, admin_client, test_admin, seeded_features):
        """The 'reason' field should be accepted but not stored as a column."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={
                "gamification_enabled": False,
                "reason": "Disabling for maintenance",
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["gamification_enabled"] is False
        # 'reason' is not a model field, so not in response
        assert "reason" not in data

    @pytest.mark.asyncio
    async def test_all_boolean_toggles_can_be_set(self, admin_client, test_admin, seeded_features):
        """Verify every boolean toggle can be explicitly set to False."""
        all_false = {
            "gamification_enabled": False,
            "reading_programs_enabled": False,
            "board_features_enabled": False,
            "training_modules_enabled": False,
            "community_features_enabled": False,
            "email_notifications_enabled": False,
            "banned_books_tracking_enabled": False,
            "patron_portal_enabled": False,
            "self_checkout_enabled": False,
        }

        response = await admin_client.put(
            "/api/v1/organization-features",
            json=all_false,
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        for key, expected in all_false.items():
            assert data[key] is expected, f"{key} should be {expected}"

    @pytest.mark.asyncio
    async def test_all_boolean_toggles_can_be_reenabled(
        self, admin_client, test_admin, seeded_features
    ):
        """After setting all to False, re-enable all."""
        all_false = {
            "gamification_enabled": False,
            "reading_programs_enabled": False,
            "board_features_enabled": False,
            "training_modules_enabled": False,
            "community_features_enabled": False,
            "email_notifications_enabled": False,
            "banned_books_tracking_enabled": False,
            "patron_portal_enabled": False,
            "self_checkout_enabled": False,
        }
        await admin_client.put(
            "/api/v1/organization-features",
            json=all_false,
            headers={"Authorization": "Bearer fake"},
        )

        all_true = {k: True for k in all_false}
        response = await admin_client.put(
            "/api/v1/organization-features",
            json=all_true,
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        for key in all_true:
            assert data[key] is True, f"{key} should be True after re-enable"

    @pytest.mark.asyncio
    async def test_numeric_config_boundary_min(self, admin_client, test_admin, seeded_features):
        """Test minimum boundary values for numeric configs."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={
                "default_daily_goal_minutes": 0,
                "max_holds_per_patron": 1,
                "max_checkouts_per_patron": 1,
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["default_daily_goal_minutes"] == 0
        assert data["max_holds_per_patron"] == 1
        assert data["max_checkouts_per_patron"] == 1

    @pytest.mark.asyncio
    async def test_numeric_config_boundary_max(self, admin_client, test_admin, seeded_features):
        """Test maximum boundary values for numeric configs."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={
                "default_daily_goal_minutes": 480,
                "max_holds_per_patron": 50,
                "max_checkouts_per_patron": 20,
            },
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 200

        data = response.json()
        assert data["default_daily_goal_minutes"] == 480
        assert data["max_holds_per_patron"] == 50
        assert data["max_checkouts_per_patron"] == 20

    @pytest.mark.asyncio
    async def test_numeric_config_over_max_rejected(
        self, admin_client, test_admin, seeded_features
    ):
        """Values above maximum should be rejected by Pydantic validation."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={"default_daily_goal_minutes": 999},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_numeric_config_below_min_rejected(
        self, admin_client, test_admin, seeded_features
    ):
        """Values below minimum should be rejected by Pydantic validation."""
        response = await admin_client.put(
            "/api/v1/organization-features",
            json={"max_holds_per_patron": 0},
            headers={"Authorization": "Bearer fake"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_singleton_pattern_returns_same_row(self, client, seeded_features):
        """Multiple GET calls should return the same row id."""
        resp1 = await client.get("/api/v1/organization-features")
        resp2 = await client.get("/api/v1/organization-features")

        assert resp1.json()["id"] == resp2.json()["id"]
