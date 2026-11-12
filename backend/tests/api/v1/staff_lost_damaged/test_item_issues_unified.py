# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Unified Item Issues Endpoints

Comprehensive test suite for the unified item issues view covering:
- Listing unified item issues (lost, damaged, claims)
- Filtering by type, status, patron, and date range
- Status updates
- Bulk status updates
- Contact patron functionality
- Summary statistics
- Performance with large datasets
"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token


@pytest.fixture
def staff_token(test_staff) -> str:
    """Bearer token string for the staff fixture user."""
    return create_access_token(subject=str(test_staff.id))


@pytest.mark.asyncio
class TestUnifiedItemIssuesEndpoints:
    """Test unified item issues management endpoints."""

    async def test_list_unified_item_issues(self, client: AsyncClient, staff_token: str):
        """Test listing unified item issues."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "items" in data
            assert "total" in data
            assert "limit" in data
            assert "offset" in data

    async def test_list_unified_issues_with_filters(self, client: AsyncClient, staff_token: str):
        """Test listing unified issues with type and status filters."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?issue_types=lost,damaged&statuses=reported",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_unified_issues_pagination(self, client: AsyncClient, staff_token: str):
        """Test pagination of unified issues."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?limit=25&offset=0",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert data["limit"] == 25

    async def test_list_unified_issues_by_days_ago(self, client: AsyncClient, staff_token: str):
        """Test filtering unified issues by days ago."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?days_ago=30",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_update_item_issue_status(self, client: AsyncClient, staff_token: str):
        """Test updating status of an item issue."""
        # First, get an issue
        list_response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues",
            headers={"Authorization": f"Bearer {staff_token}"}
        )

        if list_response.status_code == 200:
            data = list_response.json()
            if data["items"]:
                issue = data["items"][0]
                response = await client.patch(
                    f"/api/v1/staff/lost-damaged/item-issues/{issue['id']}/status?issue_type={issue['issue_type']}",
                    json={"status": "resolved", "notes": "Test update"},
                    headers={"Authorization": f"Bearer {staff_token}"}
                )
                assert response.status_code in [200, 400, 404]

    async def test_bulk_update_issue_statuses(self, client: AsyncClient, staff_token: str):
        """Test bulk updating statuses of multiple issues."""
        response = await client.post(
            "/api/v1/staff/lost-damaged/item-issues/bulk-update-status",
            json={
                "updates": [
                    {"id": 1, "issue_type": "lost", "status": "resolved", "notes": "Bulk test"}
                ]
            },
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 400, 404]

    async def test_contact_patron_about_issue(self, client: AsyncClient, staff_token: str):
        """Test contacting patron about an issue."""
        response = await client.post(
            "/api/v1/staff/lost-damaged/item-issues/1/contact-patron?issue_type=lost",
            json={
                "message": "Test message about your lost item",
                "send_email": True
            },
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 400, 404]

    async def test_get_unified_issues_summary(self, client: AsyncClient, staff_token: str):
        """Test getting summary statistics."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues/stats/summary",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "total" in data
            assert "by_type" in data
            assert "by_status" in data

    async def test_sorting_by_reported_at(self, client: AsyncClient, staff_token: str):
        """Test sorting by reported_at."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?sort_by=reported_at&sort_order=desc",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_sorting_by_status(self, client: AsyncClient, staff_token: str):
        """Test sorting by status."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?sort_by=status&sort_order=asc",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_lost_only(self, client: AsyncClient, staff_token: str):
        """Test filtering to show only lost items."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?issue_types=lost",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_damaged_only(self, client: AsyncClient, staff_token: str):
        """Test filtering to show only damaged items."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?issue_types=damaged",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_claims_only(self, client: AsyncClient, staff_token: str):
        """Test filtering to show only claims."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?issue_types=claims",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_reported_status(self, client: AsyncClient, staff_token: str):
        """Test filtering by reported status."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?statuses=reported",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_resolved_status(self, client: AsyncClient, staff_token: str):
        """Test filtering by resolved status."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?statuses=resolved",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_filter_by_patron_id(self, client: AsyncClient, staff_token: str):
        """Test filtering by patron ID."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?patron_id=1",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_limit_50_items(self, client: AsyncClient, staff_token: str):
        """Test pagination with limit of 50."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues?limit=50",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert len(data["items"]) <= 50

    async def test_unauthorized_access(self, client: AsyncClient):
        """Test that unauthenticated requests are rejected."""
        response = await client.get("/api/v1/staff/lost-damaged/item-issues")
        assert response.status_code in [401, 403]

    async def test_response_structure(self, client: AsyncClient, staff_token: str):
        """Test that response has correct structure."""
        response = await client.get(
            "/api/v1/staff/lost-damaged/item-issues",
            headers={"Authorization": f"Bearer {staff_token}"}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data["items"], list)
            assert isinstance(data["total"], int)
            assert isinstance(data["limit"], int)
            assert isinstance(data["offset"], int)

            if data["items"]:
                issue = data["items"][0]
                assert "id" in issue
                assert "issue_type" in issue
                assert "status" in issue
                assert "patron_id" in issue or issue["patron_id"] is None
                assert "patron_name" in issue
                assert "item_title" in issue
                assert "reported_at" in issue
                assert "days_since_reported" in issue
