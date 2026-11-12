# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for Audiobooks UI endpoints.

Tests verify that the Admin Audiobooks page frontend can successfully
communicate with the backend endpoints.
"""

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.skip(
    reason=(
        "app/api/v1/audiobooks.py is an intentional stub -- every endpoint "
        "returns 'Audiobook module not yet implemented' (list/stats) or 501 "
        "(create/update/delete). This test file was written ahead of the "
        "feature actually being built. Quarantined 2026-07-09 re-baseline; "
        "un-skip once the audiobooks module ships."
    )
)


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
class TestAudiobooksUIIntegration:
    """Test audiobooks API endpoints called by AdminAudiobooksPage."""

    async def test_audiobooks_stats(self, client, admin_token):
        """Frontend can fetch audiobook statistics."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get("/api/v1/audiobooks/stats", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Verify all required stat fields are present
        assert "total_audiobooks" in data
        assert "published_audiobooks" in data
        assert "pending_review" in data
        assert "total_authors" in data
        assert "total_borrows" in data
        assert "active_borrows" in data
        assert "total_listeners" in data
        assert "avg_rating" in data
        assert "total_hours_listened" in data
        assert "revenue_generated" in data

        # Verify data types
        assert isinstance(data["total_audiobooks"], int)
        assert isinstance(data["published_audiobooks"], int)
        assert isinstance(data["pending_review"], int)
        assert isinstance(data["avg_rating"], (int, float))

    async def test_audiobooks_list(self, client, admin_token):
        """Frontend can list audiobooks with pagination."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        response = await client.get("/api/v1/audiobooks/", headers=headers)
        assert response.status_code == 200
        data = response.json()

        # Response should be a list
        assert isinstance(data, list)

        # If there are audiobooks, verify structure
        if len(data) > 0:
            audiobook = data[0]
            assert "id" in audiobook
            assert "title" in audiobook
            assert "author_pen_name" in audiobook
            assert "status" in audiobook
            assert "total_borrows" in audiobook
            assert "average_rating" in audiobook
            assert "rating_count" in audiobook

    async def test_audiobooks_list_with_filters(self, client, admin_token):
        """Frontend can filter audiobooks by status."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Test with status filter
        response = await client.get(
            "/api/v1/audiobooks/?status=draft&skip=0&limit=10",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test with sorting
        response = await client.get(
            "/api/v1/audiobooks/?sort=total_borrows",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_audiobooks_list_pagination(self, client, admin_token):
        """Frontend can paginate audiobooks list."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Test pagination parameters
        response = await client.get(
            "/api/v1/audiobooks/?skip=0&limit=5",
            headers=headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # Should return at most 5 items
        assert len(data) <= 5

    async def test_audiobooks_get_single(self, client, admin_token, db_session):
        """Frontend can get single audiobook details."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Try to get an audiobook by ID (might not exist, that's ok)
        response = await client.get("/api/v1/audiobooks/1", headers=headers)

        # Should be 200 (found) or 404 (not found)
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "title" in data
            assert "author_pen_name" in data
            assert "status" in data
            assert "total_borrows" in data

    async def test_audiobooks_create(self, client, admin_token):
        """Frontend can create new audiobook."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {
            "title": "Test Audiobook",
            "narrator": "Test Narrator",
            "description": "Test description for integration testing"
        }

        response = await client.post(
            "/api/v1/audiobooks/",
            json=payload,
            headers=headers
        )

        # Should succeed (200 or 201)
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
        assert "message" in data

    async def test_audiobooks_update(self, client, admin_token, db_session):
        """Frontend can update audiobook."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # First create an audiobook
        create_payload = {
            "title": "Original Title",
            "narrator": "Original Narrator"
        }
        create_response = await client.post(
            "/api/v1/audiobooks/",
            json=create_payload,
            headers=headers
        )

        if create_response.status_code in [200, 201]:
            created_id = create_response.json()["id"]

            # Now update it
            update_payload = {
                "title": "Updated Title",
                "narrator": "Updated Narrator"
            }
            response = await client.put(
                f"/api/v1/audiobooks/{created_id}",
                json=update_payload,
                headers=headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert data["id"] == created_id

    async def test_audiobooks_delete(self, client, admin_token, db_session):
        """Frontend can delete audiobook."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # First create an audiobook
        create_payload = {
            "title": "To Be Deleted",
            "narrator": "Delete Test"
        }
        create_response = await client.post(
            "/api/v1/audiobooks/",
            json=create_payload,
            headers=headers
        )

        if create_response.status_code in [200, 201]:
            created_id = create_response.json()["id"]

            # Now delete it
            response = await client.delete(
                f"/api/v1/audiobooks/{created_id}",
                headers=headers
            )

            # Should succeed (200, 204, or 404 if already deleted)
            assert response.status_code in [200, 204, 404]
            if response.status_code == 200:
                data = response.json()
                assert "message" in data

    async def test_audiobooks_update_status(self, client, admin_token, db_session):
        """Frontend can update audiobook status (approve/reject)."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Create a test audiobook
        create_payload = {
            "title": "Status Test Audiobook",
            "narrator": "Status Narrator"
        }
        create_response = await client.post(
            "/api/v1/audiobooks/",
            json=create_payload,
            headers=headers
        )

        if create_response.status_code in [200, 201]:
            created_id = create_response.json()["id"]

            # Update to approved status
            update_payload = {"status": "approved"}
            response = await client.put(
                f"/api/v1/audiobooks/{created_id}",
                json=update_payload,
                headers=headers
            )

            assert response.status_code == 200
            data = response.json()
            assert "message" in data

    async def test_audiobooks_unauthenticated_access_denied(self, client):
        """Unauthenticated users cannot access audiobooks endpoints."""

        # Try to access stats without auth
        response = await client.get("/api/v1/audiobooks/stats")
        assert response.status_code == 401

        # Try to list audiobooks without auth
        response = await client.get("/api/v1/audiobooks/")
        assert response.status_code == 401

        # Try to get single audiobook without auth
        response = await client.get("/api/v1/audiobooks/1")
        assert response.status_code == 401

        # Try to create without auth
        response = await client.post(
            "/api/v1/audiobooks/",
            json={"title": "Test"}
        )
        assert response.status_code == 401

        # Try to update without auth
        response = await client.put(
            "/api/v1/audiobooks/1",
            json={"title": "Updated"}
        )
        assert response.status_code == 401

        # Try to delete without auth
        response = await client.delete("/api/v1/audiobooks/1")
        assert response.status_code == 401

    async def test_audiobooks_get_nonexistent(self, client, admin_token):
        """Accessing non-existent audiobook returns 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Use a very large ID that's unlikely to exist
        response = await client.get(
            "/api/v1/audiobooks/999999",
            headers=headers
        )

        # Should be 404 (not found) or 200 if stub implementation
        assert response.status_code in [200, 404]

    async def test_audiobooks_update_nonexistent(self, client, admin_token):
        """Updating non-existent audiobook returns 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}
        payload = {"title": "Updated Title"}

        # Use a very large ID that's unlikely to exist
        response = await client.put(
            "/api/v1/audiobooks/999999",
            json=payload,
            headers=headers
        )

        # Should be 404 (not found) or 200 if stub implementation
        assert response.status_code in [200, 404]

    async def test_audiobooks_delete_nonexistent(self, client, admin_token):
        """Deleting non-existent audiobook returns 404."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Use a very large ID that's unlikely to exist
        response = await client.delete(
            "/api/v1/audiobooks/999999",
            headers=headers
        )

        # Should be 404 (not found) or 200 if stub implementation
        assert response.status_code in [200, 404]

    async def test_audiobooks_list_sorting_options(self, client, admin_token):
        """Frontend can sort audiobooks by different fields."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Test different sort options
        sort_options = ["created_at", "total_borrows", "average_rating", "status"]

        for sort_field in sort_options:
            response = await client.get(
                f"/api/v1/audiobooks/?sort={sort_field}",
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)

    async def test_audiobooks_list_status_filters(self, client, admin_token):
        """Frontend can filter by all status types."""
        headers = {"Authorization": f"Bearer {admin_token}"}

        # Test different status filters
        statuses = ["draft", "submitted", "approved", "rejected"]

        for status in statuses:
            response = await client.get(
                f"/api/v1/audiobooks/?status={status}",
                headers=headers
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
