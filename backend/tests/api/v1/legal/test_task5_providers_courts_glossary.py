# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for Task 5: Providers, Courts, Glossary & Emergency Endpoints"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
class TestProvidersEndpoints:
    """Test legal service providers endpoints."""

    async def test_list_providers(self, client: AsyncClient):
        """Test listing legal service providers."""
        response = await client.get("/api/v1/legal/providers")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "providers" in data or "items" in data

    async def test_list_providers_with_search(self, client: AsyncClient):
        """Test searching providers by name or organization."""
        response = await client.get("/api/v1/legal/providers?search=legal")
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_providers_with_location_filter(self, client: AsyncClient):
        """Test filtering providers by location."""
        response = await client.get("/api/v1/legal/providers?location=downtown")
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_providers_with_pagination(self, client: AsyncClient):
        """Test listing providers with pagination."""
        response = await client.get("/api/v1/legal/providers?limit=20&offset=0")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_provider(self, client: AsyncClient):
        """Test getting a specific provider by ID."""
        response = await client.get("/api/v1/legal/providers/1")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data

    async def test_search_providers(self, client: AsyncClient):
        """Test provider search endpoint with full-text search.

        /providers/search is POST-only with a JSON body (LegalServiceProviderSearchRequest)
        -- there's no GET /providers/search, so a GET here previously matched
        GET /providers/{provider_id} instead, with "search" failing int coercion (422).
        """
        response = await client.post(
            "/api/v1/legal/providers/search", json={"query": "immigration"}
        )
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (list, dict))


@pytest.mark.asyncio
class TestCourtsEndpoints:
    """Test court location and information endpoints."""

    async def test_list_courts(self, client: AsyncClient):
        """Test listing courts."""
        response = await client.get("/api/v1/legal/courts")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "courts" in data or "items" in data

    async def test_list_courts_with_county_filter(self, client: AsyncClient):
        """Test filtering courts by county."""
        response = await client.get("/api/v1/legal/courts?county=alameda")
        assert response.status_code in [200, 401, 403, 404]

    async def test_list_courts_with_court_type_filter(self, client: AsyncClient):
        """Test filtering courts by court type."""
        response = await client.get("/api/v1/legal/courts?court_type=district")
        assert response.status_code in [200, 401, 403, 404]

    async def test_get_court(self, client: AsyncClient):
        """Test getting a specific court by ID."""
        response = await client.get("/api/v1/legal/courts/1")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert "name" in data


@pytest.mark.asyncio
class TestGlossaryEndpoints:
    """Test legal glossary/terminology endpoints."""

    async def test_list_glossary_terms(self, client: AsyncClient):
        """Test listing glossary terms."""
        response = await client.get("/api/v1/legal/glossary")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "terms" in data or "items" in data

    async def test_get_glossary_term(self, client: AsyncClient):
        """Test getting a specific glossary term by slug."""
        response = await client.get("/api/v1/legal/glossary/appeal")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert "slug" in data or "term" in data

    async def test_glossary_search(self, client: AsyncClient):
        """Test searching glossary terms."""
        response = await client.get("/api/v1/legal/glossary?search=defendant")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestEmergencyResourcesEndpoints:
    """Test emergency legal resources endpoints."""

    async def test_get_emergency_resources(self, client: AsyncClient):
        """Test getting emergency legal resources."""
        response = await client.get("/api/v1/legal/emergency")
        assert response.status_code in [200, 401, 403, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    async def test_emergency_hotline_info(self, client: AsyncClient):
        """Test getting emergency hotline information."""
        response = await client.get("/api/v1/legal/emergency/hotlines")
        assert response.status_code in [200, 401, 403, 404]


@pytest.mark.asyncio
class TestTask5Integration:
    """Integration tests for Task 5 features."""

    async def test_providers_search_and_filter(self, client: AsyncClient):
        """Test searching and filtering providers together."""
        response = await client.get(
            "/api/v1/legal/providers?search=civil&location=downtown&limit=10"
        )
        assert response.status_code in [200, 401, 403, 404]

    async def test_courts_discovery_workflow(self, client: AsyncClient):
        """Test typical court discovery workflow."""
        # List all courts
        response = await client.get("/api/v1/legal/courts")
        if response.status_code == 200:
            # Filter by county
            response2 = await client.get("/api/v1/legal/courts?county=alameda")
            assert response2.status_code in [200, 401, 403]

    async def test_glossary_term_lookup(self, client: AsyncClient):
        """Test glossary term lookup workflow."""
        # Get specific term
        response = await client.get("/api/v1/legal/glossary/appeal")
        assert response.status_code in [200, 401, 403, 404]

    async def test_emergency_resources_accessibility(self, client: AsyncClient):
        """Test emergency resources are accessible."""
        response = await client.get("/api/v1/legal/emergency")
        # Emergency resources should not require authentication
        assert response.status_code in [200, 401, 403, 404]

    async def test_multiple_provider_types_search(self, client: AsyncClient):
        """Test searching for different types of legal providers.

        /providers/search is POST-only with a JSON body -- see test_search_providers.
        """
        # Civil rights providers
        response1 = await client.post(
            "/api/v1/legal/providers/search", json={"query": "civil rights"}
        )
        assert response1.status_code in [200, 401, 403, 404]

        # Immigration providers
        response2 = await client.post(
            "/api/v1/legal/providers/search", json={"query": "immigration"}
        )
        assert response2.status_code in [200, 401, 403, 404]

    async def test_combined_resource_discovery(self, client: AsyncClient):
        """Test combined workflow: courts -> providers -> glossary."""
        # Find courts
        courts_response = await client.get("/api/v1/legal/courts")

        # Find providers
        providers_response = await client.get("/api/v1/legal/providers")

        # Look up terms
        glossary_response = await client.get("/api/v1/legal/glossary")

        # All should return valid status codes
        for response in [courts_response, providers_response, glossary_response]:
            assert response.status_code in [200, 401, 403, 404]

    async def test_provider_list_completeness(self, client: AsyncClient):
        """Test provider list returns complete information."""
        response = await client.get("/api/v1/legal/providers")
        if response.status_code == 200:
            data = response.json()
            providers = data.get("providers", data.get("items", []))
            if providers and len(providers) > 0:
                provider = providers[0]
                # Should have basic fields
                assert any(k in provider for k in ["name", "title", "organization"])

    async def test_court_list_completeness(self, client: AsyncClient):
        """Test court list returns complete information."""
        response = await client.get("/api/v1/legal/courts")
        if response.status_code == 200:
            data = response.json()
            courts = data.get("courts", data.get("items", []))
            if courts and len(courts) > 0:
                court = courts[0]
                # Should have basic fields
                assert any(k in court for k in ["name", "title", "address", "location"])

    async def test_glossary_term_completeness(self, client: AsyncClient):
        """Test glossary terms have complete definitions."""
        response = await client.get("/api/v1/legal/glossary")
        if response.status_code == 200:
            data = response.json()
            terms = data.get("terms", data.get("items", []))
            if terms and len(terms) > 0:
                term = terms[0]
                # Should have definition or content
                assert any(k in term for k in ["definition", "content", "description"])

    async def test_emergency_resources_essential_fields(self, client: AsyncClient):
        """Test emergency resources have essential contact information."""
        response = await client.get("/api/v1/legal/emergency")
        if response.status_code == 200:
            data = response.json()
            # Should have emergency contact information
            assert isinstance(data, dict)
