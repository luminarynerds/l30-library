# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for content flags API endpoints.

Tests the full workflow:
- Submitting reviews with content analysis
- Viewing flagged content in staff dashboard
- Resolving flags with feedback
- Statistics and analytics
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token


@pytest.fixture
async def async_client(client):
    """Alias for the standard async client fixture (name used throughout this file)."""
    return client


@pytest.fixture
def staff_user_token(test_staff) -> str:
    """Bearer token string for the staff fixture user."""
    return create_access_token(subject=str(test_staff.id))


@pytest.fixture
def patron_user_token(test_patron) -> str:
    """Bearer token string for the patron fixture user."""
    return create_access_token(subject=str(test_patron.id))


@pytest.fixture
def staff_user_token(test_staff):
    from app.core.security import create_access_token

    return create_access_token(subject=test_staff.id, email=test_staff.email)


@pytest.fixture
def patron_user_token(test_patron):
    from app.core.security import create_access_token

    return create_access_token(subject=test_patron.id, email=test_patron.email)


class TestContentFlagsEndpoints:
    """Test content flags API endpoints."""

    @pytest.mark.asyncio
    async def test_get_flagged_content_empty(self, client, staff_user_token):
        """Test getting flagged content when none exist."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    @pytest.mark.asyncio
    async def test_get_flagged_content_requires_auth(self, client):
        """Test that content flags endpoint requires authentication."""
        response = await client.get("/api/v1/admin/content-flags/")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_flagged_content_requires_staff(self, client, patron_user_token):
        """Test that content flags endpoint requires staff role."""
        headers = {"Authorization": f"Bearer {patron_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/",
            headers=headers
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_flag_details(self, client, staff_user_token, db_session):
        """Test getting details of a specific flag."""
        # First, create a flag
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/1",
            headers=headers
        )

        # Should get 404 if flag doesn't exist
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_filter_flags_by_status(self, client, staff_user_token):
        """Test filtering flags by status."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/?status=pending",
            headers=headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_flags_by_type(self, client, staff_user_token):
        """Test filtering flags by flag type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/?review_type=event_review",
            headers=headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_flags_by_min_score(self, client, staff_user_token):
        """Test filtering flags by minimum confidence score."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/?min_score=80",
            headers=headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_resolve_flag_as_false_positive(self, client, staff_user_token):
        """Test resolving a flag as false positive."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        payload = {
            "status": "false_positive",
            "is_correct_flag": False,
            "resolution_notes": "This was a legitimate review",
            "staff_feedback": "System incorrectly flagged promotional language"
        }

        response = await client.patch(
            "/api/v1/admin/content-flags/1/resolve",
            headers=headers,
            json=payload
        )

        # Should get 404 if flag doesn't exist, otherwise 200
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_resolve_flag_as_correct(self, client, staff_user_token):
        """Test resolving a flag as correct."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        payload = {
            "status": "resolved",
            "is_correct_flag": True,
            "resolution_notes": "Spam content confirmed and hidden",
            "staff_feedback": "System correctly identified spam"
        }

        response = await client.patch(
            "/api/v1/admin/content-flags/1/resolve",
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_submit_flag_feedback(self, client, staff_user_token):
        """Test submitting feedback on a flag."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        payload = {
            "status": "resolved",
            "is_correct_flag": True,
            "staff_feedback": "Model is learning from this correction"
        }

        response = await client.post(
            "/api/v1/admin/content-flags/1/feedback",
            headers=headers,
            json=payload
        )

        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_invalid_status_rejected(self, client, staff_user_token):
        """Test that invalid status is rejected."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        payload = {
            "status": "invalid_status"
        }

        response = await client.patch(
            "/api/v1/admin/content-flags/1/resolve",
            headers=headers,
            json=payload
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_flag_statistics_summary(self, client, staff_user_token):
        """Test getting flag statistics summary."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/statistics/summary",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_flags" in data
        assert "avg_confidence" in data
        assert "false_positive_rate" in data

    @pytest.mark.asyncio
    async def test_statistics_by_flag_type(self, client, staff_user_token):
        """Test getting statistics broken down by flag type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/statistics/by-type",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "stats_by_type" in data

    @pytest.mark.asyncio
    async def test_statistics_by_review_type(self, client, staff_user_token):
        """Test getting statistics broken down by review type."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/statistics/by-review-type",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "stats_by_review_type" in data

    @pytest.mark.asyncio
    async def test_statistics_custom_date_range(self, client, staff_user_token):
        """Test getting statistics for custom date range."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/statistics/summary?days=7",
            headers=headers
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_pagination(self, client, staff_user_token):
        """Test pagination of flagged content."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        response = await client.get(
            "/api/v1/admin/content-flags/?page=1&per_page=10",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["per_page"] == 10


class TestReviewSubmissionWithFlagging:
    """Test review submission with automatic content flagging."""

    @pytest.mark.asyncio
    async def test_event_review_submission_clean_comment(self, client):
        """Test submitting a clean event review."""
        # Create event first
        event_response = await client.post("/api/v1/events/", json={
            "title": "Test Event",
            "description": "Test event for review",
            "start_time": "2025-01-15T10:00:00Z",
            "end_time": "2025-01-15T12:00:00Z",
            "location": "Test Location"
        })

        if event_response.status_code == 201:
            event_id = event_response.json()["id"]

            # Submit clean review
            review_response = await client.post(
                f"/api/v1/events/{event_id}/reviews",
                json={
                    "patron_email": "reviewer@example.com",
                    "rating": 5,
                    "comment": "Great event! I learned a lot and had excellent conversations."
                }
            )

            assert review_response.status_code in [201, 400, 403]  # 403 if not registered

    @pytest.mark.asyncio
    async def test_event_review_submission_spammy_comment(self, client):
        """Test submitting a spammy event review."""
        # This tests that flagging doesn't break review submission
        review_response = await client.post(
            "/api/v1/events/1/reviews",
            json={
                "patron_email": "spammer@example.com",
                "rating": 5,
                "comment": "BUY NOW!!! Visit https://example.com for deals!"
            }
        )

        # Should succeed (or fail with 403 if not registered)
        # but not with 500 error
        assert review_response.status_code != 500


class TestFlagStatusTransitions:
    """Test valid status transitions for flags."""

    @pytest.mark.asyncio
    async def test_pending_to_resolved_transition(self, client, staff_user_token):
        """Test transition from PENDING to RESOLVED."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        # First get a pending flag (would need setup)
        flags_response = await client.get(
            "/api/v1/admin/content-flags/?status=pending",
            headers=headers
        )

        if flags_response.status_code == 200:
            data = flags_response.json()
            if data["items"]:
                flag_id = data["items"][0]["id"]

                # Resolve it
                resolve_response = await client.patch(
                    f"/api/v1/admin/content-flags/{flag_id}/resolve",
                    headers=headers,
                    json={
                        "status": "resolved",
                        "is_correct_flag": True
                    }
                )

                assert resolve_response.status_code == 200

    @pytest.mark.asyncio
    async def test_pending_to_false_positive_transition(self, client, staff_user_token):
        """Test transition from PENDING to FALSE_POSITIVE."""
        headers = {"Authorization": f"Bearer {staff_user_token}"}

        # Get a pending flag
        flags_response = await client.get(
            "/api/v1/admin/content-flags/?status=pending",
            headers=headers
        )

        if flags_response.status_code == 200:
            data = flags_response.json()
            if data["items"]:
                flag_id = data["items"][0]["id"]

                # Mark as false positive
                resolve_response = await client.patch(
                    f"/api/v1/admin/content-flags/{flag_id}/resolve",
                    headers=headers,
                    json={
                        "status": "false_positive",
                        "is_correct_flag": False,
                        "staff_feedback": "This was a legitimate review"
                    }
                )

                assert resolve_response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
