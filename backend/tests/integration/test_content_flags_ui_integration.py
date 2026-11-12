# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Content Flags UI endpoints.

Tests verify that the Content Flags moderation page frontend can successfully
communicate with the backend endpoints for content moderation features.
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
async def admin_token(client, test_admin, test_admin_data):
    """Get admin access token for testing."""
    login_data = {
        "username": test_admin_data["email"],
        "password": test_admin_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def staff_token(client, test_staff, test_staff_data):
    """Get staff access token for testing."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
async def patron_token(client, test_patron, test_user_data):
    """Get patron access token for testing."""
    login_data = {
        "username": test_user_data["email"],
        "password": test_user_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def db_session(test_db):
    """Alias for test_db to match test naming."""
    return test_db


@pytest.mark.integration
@pytest.mark.asyncio
class TestContentFlagsUIIntegration:
    """Test content flags API endpoints called by frontend."""

    async def test_content_flags_list(self, client, admin_token):
        """Frontend can list content flags."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get("/api/v1/admin/content-flags/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data
        assert isinstance(data["items"], list)

    async def test_content_flags_list_with_filters(self, client, admin_token):
        """Frontend can list content flags with filters."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        params = {
            "page": 1,
            "per_page": 10,
            "status": "pending",  # StrEnum wire values are lowercase
            "min_score": 80
        }
        response = await client.get(
            "/api/v1/admin/content-flags/",
            params=params,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert data["page"] == 1
        assert data["per_page"] == 10

    async def test_content_flags_get_details(self, client, admin_token, db_session):
        """Frontend can get single flag details."""
        from app.models.content_flag import ContentFlag, FlagType, FlagStatus

        # Create a test flag
        flag = ContentFlag(
            review_id=1,
            review_type="event_review",
            flag_type=FlagType.SPAM,
            confidence_score=85,
            analysis_details={"reason": "test"},
            status=FlagStatus.PENDING
        )
        db_session.add(flag)
        await db_session.commit()
        await db_session.refresh(flag)

        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get(
            f"/api/v1/admin/content-flags/{flag.id}",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == flag.id
        assert data["review_type"] == "event_review"
        assert data["flag_type"] == "spam"  # StrEnum wire values are lowercase
        assert data["confidence_score"] == 85
        assert data["status"] == "pending"  # StrEnum wire values are lowercase

    async def test_content_flags_get_nonexistent(self, client, admin_token):
        """Frontend handles non-existent flag gracefully."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get(
            "/api/v1/admin/content-flags/999999",
            headers=headers
        )
        assert response.status_code == 404

    async def test_content_flags_submit_feedback(self, client, staff_token, db_session):
        """Frontend can submit feedback on a flag."""
        from app.models.content_flag import ContentFlag, FlagType, FlagStatus

        # Create a test flag
        flag = ContentFlag(
            review_id=1,
            review_type="event_review",
            flag_type=FlagType.HATE_SPEECH,
            confidence_score=90,
            analysis_details={"reason": "test"},
            status=FlagStatus.PENDING
        )
        db_session.add(flag)
        await db_session.commit()
        await db_session.refresh(flag)

        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "status": "resolved",
            "is_correct_flag": True,
            "resolution_notes": "Removed offensive content",
            "staff_feedback": "Flag was accurate"
        }
        response = await client.post(
            f"/api/v1/admin/content-flags/{flag.id}/feedback",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == flag.id
        assert data["is_correct_flag"] is True
        assert data["staff_feedback"] == "Flag was accurate"

    async def test_content_flags_resolve_flag(self, client, staff_token, db_session):
        """Frontend can resolve a content flag."""
        from app.models.content_flag import ContentFlag, FlagType, FlagStatus

        # Create a test flag
        flag = ContentFlag(
            review_id=2,
            review_type="event_review",
            flag_type=FlagType.SPAM,
            confidence_score=75,
            analysis_details={"reason": "test"},
            status=FlagStatus.PENDING
        )
        db_session.add(flag)
        await db_session.commit()
        await db_session.refresh(flag)

        headers = {"Authorization": f"Bearer {staff_token}"}
        payload = {
            "status": "false_positive",
            "is_correct_flag": False,
            "resolution_notes": "This was not spam",
            "staff_feedback": "Flag was incorrect"
        }
        response = await client.patch(
            f"/api/v1/admin/content-flags/{flag.id}/resolve",
            json=payload,
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == flag.id
        assert data["status"] == "false_positive"  # StrEnum wire values are lowercase
        assert data["is_correct_flag"] is False
        assert data["resolution_notes"] == "This was not spam"

    async def test_content_flags_statistics_summary(self, client, admin_token):
        """Frontend can get content flagging statistics summary."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get(
            "/api/v1/admin/content-flags/statistics/summary?days=30",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_flags" in data
        assert "avg_confidence" in data
        assert "high_confidence_flags" in data
        assert "false_positives" in data
        assert "false_negatives" in data
        assert "false_positive_rate" in data

    async def test_content_flags_statistics_by_type(self, client, admin_token):
        """Frontend can get statistics by flag type."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get(
            "/api/v1/admin/content-flags/statistics/by-type?days=30",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "stats_by_type" in data
        assert "period_days" in data
        assert data["period_days"] == 30

    async def test_content_flags_statistics_by_review_type(self, client, admin_token):
        """Frontend can get statistics by review type."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get(
            "/api/v1/admin/content-flags/statistics/by-review-type?days=30",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert "stats_by_review_type" in data
        assert "period_days" in data
        assert data["period_days"] == 30

    async def test_content_flags_patron_access_denied(self, client, patron_token):
        """Patrons cannot access content flags endpoints."""
        headers = {"Authorization": f"Bearer {patron_token}"}

        # Try to list flags
        response = await client.get("/api/v1/admin/content-flags/", headers=headers)
        assert response.status_code == 403

        # Try to get flag details
        response = await client.get("/api/v1/admin/content-flags/1", headers=headers)
        assert response.status_code == 403

        # Try to get statistics
        response = await client.get(
            "/api/v1/admin/content-flags/statistics/summary",
            headers=headers
        )
        assert response.status_code == 403

    async def test_content_flags_unauthenticated_denied(self, client):
        """Unauthenticated users cannot access content flags."""
        # Try without authorization header
        response = await client.get("/api/v1/admin/content-flags/")
        assert response.status_code == 401

        response = await client.get("/api/v1/admin/content-flags/1")
        assert response.status_code == 401

        response = await client.get("/api/v1/admin/content-flags/statistics/summary")
        assert response.status_code == 401

    async def test_staff_can_access_content_flags(self, client, staff_token):
        """Staff users can access content flags endpoints."""
        headers = {"Authorization": f"Bearer {staff_token}"}
        response = await client.get("/api/v1/admin/content-flags/", headers=headers)
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
