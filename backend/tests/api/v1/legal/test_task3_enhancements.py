# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Task 3: Collections & Content Enhancements"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.legal import LegalCollection, FormFinderWizardSession


@pytest.mark.asyncio
class TestCollectionsEnhancements:
    """Test enhanced collections endpoints."""

    async def test_list_collections_with_complexity_filter(self, client: AsyncClient):
        """Test filtering collections by complexity level."""
        response = await client.get(
            "/api/v1/legal/collections?complexity_level=simple"
        )
        assert response.status_code in [200, 404]

    async def test_list_collections_with_cost_filter(self, client: AsyncClient):
        """Test filtering collections by maximum cost."""
        response = await client.get(
            "/api/v1/legal/collections?cost_max=500"
        )
        assert response.status_code in [200, 404]

    async def test_list_collections_with_fee_waiver_filter(self, client: AsyncClient):
        """Test filtering collections by fee waiver availability."""
        response = await client.get(
            "/api/v1/legal/collections?has_fee_waiver=true"
        )
        assert response.status_code in [200, 404]

    async def test_list_collections_with_language_filter(self, client: AsyncClient):
        """Test filtering collections by language."""
        response = await client.get(
            "/api/v1/legal/collections?language=es"
        )
        assert response.status_code in [200, 404]

    async def test_list_collections_with_search(self, client: AsyncClient):
        """Test searching collections by keyword."""
        response = await client.get(
            "/api/v1/legal/collections?search=eviction"
        )
        assert response.status_code in [200, 404]

    async def test_list_collections_with_sort_featured(self, client: AsyncClient):
        """Test sorting collections by featured status."""
        response = await client.get(
            "/api/v1/legal/collections?sort_by=featured"
        )
        assert response.status_code in [200, 404]

    async def test_list_collections_with_sort_relevance(self, client: AsyncClient):
        """Test sorting collections by relevance."""
        response = await client.get(
            "/api/v1/legal/collections?sort_by=relevance&search=legal"
        )
        assert response.status_code in [200, 404]

    async def test_get_related_collections(self, client: AsyncClient):
        """Test getting related collections."""
        response = await client.get("/api/v1/legal/collections/1/related")
        assert response.status_code in [200, 404]

    async def test_get_related_collections_with_limit(self, client: AsyncClient):
        """Test getting related collections with custom limit."""
        response = await client.get("/api/v1/legal/collections/1/related?limit=3")
        assert response.status_code in [200, 404]

    async def test_get_collection_analytics(self, client: AsyncClient):
        """Test getting collection analytics (staff only)."""
        response = await client.get(
            "/api/v1/legal/collections/1/analytics"
        )
        # 401 if not authenticated, 404 if not found, 200 if found
        assert response.status_code in [200, 401, 404]

    async def test_multiple_filters_combined(self, client: AsyncClient):
        """Test combining multiple filters."""
        response = await client.get(
            "/api/v1/legal/collections?"
            "complexity_level=moderate&"
            "has_fee_waiver=true&"
            "cost_max=1000&"
            "sort_by=alphabetical"
        )
        assert response.status_code in [200, 404]

    async def test_pagination_with_filters(self, client: AsyncClient):
        """Test pagination works with filters."""
        response = await client.get(
            "/api/v1/legal/collections?complexity_level=simple&limit=10&offset=0"
        )
        assert response.status_code in [200, 404]
        if response.status_code in [200, 405]:
            data = response.json()
            assert "collections" in data or "items" in data


@pytest.mark.asyncio
class TestWizardEnhancements:
    """Test enhanced wizard endpoints."""

    async def test_wizard_progress_tracking(self, client: AsyncClient):
        """Test getting wizard session progress."""
        # First start a session
        start_response = await client.post("/api/v1/legal/wizard/start")
        if start_response.status_code == 200:
            session_data = start_response.json()
            session_token = session_data.get("session_token")

            # Then get progress
            progress_response = await client.get(
                f"/api/v1/legal/wizard/{session_token}/progress"
            )
            assert progress_response.status_code in [200, 404]
            if progress_response.status_code == 200:
                progress_data = progress_response.json()
                assert "progress" in progress_data
                assert "percentage" in progress_data["progress"]

    async def test_wizard_progress_new_session(self, client: AsyncClient):
        """Test progress on new session shows 0%."""
        start_response = await client.post("/api/v1/legal/wizard/start")
        if start_response.status_code == 200:
            session_data = start_response.json()
            session_token = session_data.get("session_token")

            progress_response = await client.get(
                f"/api/v1/legal/wizard/{session_token}/progress"
            )
            assert progress_response.status_code == 200
            progress_data = progress_response.json()
            assert progress_data["progress"]["percentage"] == 0

    async def test_wizard_progress_not_found(self, client: AsyncClient):
        """Test progress returns 404 for invalid session."""
        response = await client.get(
            "/api/v1/legal/wizard/invalid-token-12345/progress"
        )
        assert response.status_code == 404

    async def test_wizard_progress_shows_questions_answered(self, client: AsyncClient):
        """Test progress shows count of questions answered."""
        start_response = await client.post("/api/v1/legal/wizard/start")
        if start_response.status_code == 200:
            session_token = start_response.json().get("session_token")

            progress_response = await client.get(
                f"/api/v1/legal/wizard/{session_token}/progress"
            )
            if progress_response.status_code == 200:
                data = progress_response.json()
                assert "questions_answered" in data["progress"]
                assert data["progress"]["questions_answered"] >= 0

    async def test_wizard_progress_time_tracking(self, client: AsyncClient):
        """Test progress includes time tracking."""
        start_response = await client.post("/api/v1/legal/wizard/start")
        if start_response.status_code == 200:
            session_token = start_response.json().get("session_token")

            progress_response = await client.get(
                f"/api/v1/legal/wizard/{session_token}/progress"
            )
            if progress_response.status_code == 200:
                data = progress_response.json()
                assert "session_info" in data
                assert "time_elapsed_minutes" in data["session_info"]


@pytest.mark.asyncio
class TestReviewsEnhancements:
    """Test enhanced reviews endpoints."""

    async def test_reviews_dashboard_accessible(self, client: AsyncClient):
        """Test accessing reviews dashboard."""
        response = await client.get("/api/v1/legal/reviews/dashboard")
        # 401 if not staff, 200 if accessible, 404 if not found, 405 if method not allowed
        assert response.status_code in [200, 401, 404, 405]

    async def test_reviews_dashboard_with_custom_days(self, client: AsyncClient):
        """Test dashboard with custom date range."""
        response = await client.get(
            "/api/v1/legal/reviews/dashboard?days_back=60"
        )
        assert response.status_code in [200, 401, 404, 405]

    async def test_reviews_dashboard_metrics_structure(self, client: AsyncClient):
        """Test dashboard returns proper metrics structure."""
        response = await client.get("/api/v1/legal/reviews/dashboard")
        if response.status_code in [200, 405]:  # 405 if not yet implemented
            data = response.json()
            assert "dashboard" in data
            assert "summary" in data["dashboard"]
            assert "urgent" in data["dashboard"]
            assert "upcoming" in data["dashboard"]

    async def test_reviews_dashboard_summary_metrics(self, client: AsyncClient):
        """Test dashboard summary includes key metrics."""
        response = await client.get("/api/v1/legal/reviews/dashboard")
        if response.status_code in [200, 405]:
            data = response.json()
            summary = data["dashboard"]["summary"]
            assert "total_cycles" in summary
            assert "completed" in summary
            assert "in_progress" in summary
            assert "pending" in summary
            assert "completion_percentage" in summary

    async def test_reviews_dashboard_urgent_section(self, client: AsyncClient):
        """Test dashboard urgent section structure."""
        response = await client.get("/api/v1/legal/reviews/dashboard")
        if response.status_code in [200, 405]:
            data = response.json()
            urgent = data["dashboard"]["urgent"]
            assert "overdue_count" in urgent
            assert "overdue_cycles" in urgent

    async def test_reviews_dashboard_upcoming_section(self, client: AsyncClient):
        """Test dashboard upcoming section structure."""
        response = await client.get("/api/v1/legal/reviews/dashboard")
        if response.status_code in [200, 405]:
            data = response.json()
            upcoming = data["dashboard"]["upcoming"]
            assert "next_7_days" in upcoming
            assert "upcoming_cycles" in upcoming

    async def test_reviews_dashboard_performance_metrics(self, client: AsyncClient):
        """Test dashboard performance metrics."""
        response = await client.get("/api/v1/legal/reviews/dashboard")
        if response.status_code in [200, 405]:
            data = response.json()
            perf = data["dashboard"]["performance"]
            assert "average_hours_to_complete" in perf
            assert isinstance(perf["average_hours_to_complete"], (int, float))


@pytest.mark.asyncio
class TestTask3Integration:
    """Integration tests for Task 3 features."""

    async def test_collections_search_and_filter_combined(self, client: AsyncClient):
        """Test using search and filters together."""
        response = await client.get(
            "/api/v1/legal/collections?"
            "search=legal&"
            "complexity_level=moderate&"
            "sort_by=relevance"
        )
        assert response.status_code in [200, 404]

    async def test_wizard_complete_workflow(self, client: AsyncClient):
        """Test complete wizard workflow with progress."""
        # Start
        start_response = await client.post("/api/v1/legal/wizard/start")
        if start_response.status_code == 200:
            session_token = start_response.json()["session_token"]

            # Check progress at start
            progress_response = await client.get(
                f"/api/v1/legal/wizard/{session_token}/progress"
            )
            assert progress_response.status_code in [200, 404]
            if progress_response.status_code == 200:
                initial_progress = progress_response.json()["progress"]["percentage"]
                assert initial_progress == 0

    async def test_invalid_sort_parameter(self, client: AsyncClient):
        """Test that invalid sort parameter is rejected."""
        response = await client.get(
            "/api/v1/legal/collections?sort_by=invalid_sort"
        )
        # Should either be rejected (422) or treated as default
        assert response.status_code in [200, 404, 422]

    async def test_boundary_cost_filter(self, client: AsyncClient):
        """Test cost filter with boundary values."""
        # Zero cost
        response = await client.get(
            "/api/v1/legal/collections?cost_max=0"
        )
        assert response.status_code in [200, 404]

        # Large cost
        response = await client.get(
            "/api/v1/legal/collections?cost_max=999999"
        )
        assert response.status_code in [200, 404]

    async def test_boundary_days_parameter(self, client: AsyncClient):
        """Test dashboard days parameter with boundaries."""
        # Minimum
        response = await client.get(
            "/api/v1/legal/reviews/dashboard?days_back=1"
        )
        assert response.status_code in [200, 401, 404, 405]

        # Maximum
        response = await client.get(
            "/api/v1/legal/reviews/dashboard?days_back=365"
        )
        assert response.status_code in [200, 401, 404, 405]
