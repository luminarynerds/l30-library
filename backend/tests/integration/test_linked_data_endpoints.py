# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for BIBFRAME and Linked Data API endpoints.

Tests cover:
- BIBFRAME Work, Instance, Item CRUD operations
- Content negotiation (JSON-LD, Turtle)
- SPARQL endpoint
- Schema.org markup endpoints
- Authority linking
"""

import pytest
from datetime import datetime
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def test_bibframe_work(test_db):
    """Create a test BIBFRAME work."""
    from app.models.bibframe import BibframeWork, WorkType

    work = BibframeWork(
        title="Test BIBFRAME Work",
        subtitle="A Subtitle",
        work_type=WorkType.text,
        language="eng",
        summary="A test work for integration testing.",
        dewey_classification="005.133",
        lc_classification="QA76.73.P98",
    )
    test_db.add(work)
    await test_db.commit()
    await test_db.refresh(work)
    return work


@pytest.fixture
async def test_bibframe_instance(test_db, test_bibframe_work):
    """Create a test BIBFRAME instance."""
    from app.models.bibframe import BibframeInstance, InstanceType, CarrierType, MediaType

    instance = BibframeInstance(
        work_id=test_bibframe_work.id,
        title="Test BIBFRAME Instance",
        instance_type=InstanceType.print,
        carrier_type=CarrierType.volume,
        media_type=MediaType.unmediated,
        isbn_13="9780123456789",
        publisher="Test Publisher",
        publication_year=2024,
        page_count=350,
    )
    test_db.add(instance)
    await test_db.commit()
    await test_db.refresh(instance)
    return instance


@pytest.fixture
async def test_bibframe_item(test_db, test_bibframe_instance):
    """Create a test BIBFRAME item."""
    from app.models.bibframe import BibframeItem

    item = BibframeItem(
        instance_id=test_bibframe_instance.id,
        barcode="BF-TEST-001",
        call_number="QA76.73.P98 T47 2024",
        library_branch="Main",
        shelving_location="Stacks",
        circulation_status="available",
        copy_number=1,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def test_bibframe_contributor(test_db):
    """Create a test BIBFRAME contributor."""
    from app.models.bibframe import BibframeContributor

    contributor = BibframeContributor(
        name="Test Author",
        contributor_type="person",
        name_inverted="Author, Test",
        given_name="Test",
        family_name="Author",
        viaf_id="12345678",
    )
    test_db.add(contributor)
    await test_db.commit()
    await test_db.refresh(contributor)
    return contributor


@pytest.fixture
async def test_bibframe_subject(test_db):
    """Create a test BIBFRAME subject."""
    from app.models.bibframe import BibframeSubject

    subject = BibframeSubject(
        label="Computer programming",
        subject_type="topic",
        lcsh_id="sh85029533",
    )
    test_db.add(subject)
    await test_db.commit()
    await test_db.refresh(subject)
    return subject


# ============================================================================
# Work Endpoint Tests
# ============================================================================


@pytest.mark.integration
class TestLinkedDataWorkEndpoints:
    """Test BIBFRAME Work API endpoints."""

    async def test_list_works(self, client, test_bibframe_work):
        """Test listing BIBFRAME works."""
        response = await client.get("/api/v1/linked-data/works")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_work_json(self, client, test_bibframe_work):
        """Test getting a work as JSON."""
        response = await client.get(
            f"/api/v1/linked-data/works/{test_bibframe_work.id}",
            headers={"Accept": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test BIBFRAME Work"
        assert data["work_type"] == "text"

    async def test_get_work_jsonld(self, client, test_bibframe_work):
        """Test getting a work as JSON-LD."""
        response = await client.get(
            f"/api/v1/linked-data/works/{test_bibframe_work.id}",
            headers={"Accept": "application/ld+json"},
        )

        assert response.status_code == 200
        assert "application/ld+json" in response.headers["content-type"]
        data = response.json()
        assert "@context" in data
        assert "@type" in data
        # @type can carry multiple BIBFRAME classes now (e.g. ["bf:Work"])
        type_value = data["@type"]
        if isinstance(type_value, list):
            assert "bf:Work" in type_value
        else:
            assert type_value == "bf:Work"

    async def test_get_work_turtle(self, client, test_bibframe_work):
        """Test getting a work as Turtle RDF."""
        response = await client.get(
            f"/api/v1/linked-data/works/{test_bibframe_work.id}",
            headers={"Accept": "text/turtle"},
        )

        assert response.status_code == 200
        assert "text/turtle" in response.headers["content-type"]
        content = response.text
        assert "@prefix" in content or "PREFIX" in content
        assert "bf:" in content

    async def test_get_nonexistent_work(self, client):
        """Test getting a nonexistent work returns 404."""
        response = await client.get("/api/v1/linked-data/works/99999")

        assert response.status_code == 404

    async def test_search_works_by_title(self, client, test_bibframe_work):
        """Test searching works by title."""
        response = await client.get(
            "/api/v1/linked-data/works",
            params={"title": "BIBFRAME"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_search_works_by_language(self, client, test_bibframe_work):
        """Test searching works by language."""
        response = await client.get(
            "/api/v1/linked-data/works",
            params={"language": "eng"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


# ============================================================================
# Instance Endpoint Tests
# ============================================================================


@pytest.mark.integration
class TestLinkedDataInstanceEndpoints:
    """Test BIBFRAME Instance API endpoints."""

    async def test_list_instances(self, client, test_bibframe_instance):
        """Test listing BIBFRAME instances."""
        response = await client.get("/api/v1/linked-data/instances")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    async def test_get_instance_json(self, client, test_bibframe_instance):
        """Test getting an instance as JSON."""
        response = await client.get(
            f"/api/v1/linked-data/instances/{test_bibframe_instance.id}",
            headers={"Accept": "application/json"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test BIBFRAME Instance"
        assert data["isbn_13"] == "9780123456789"

    async def test_search_instances_by_isbn(self, client, test_bibframe_instance):
        """Test searching instances by ISBN."""
        response = await client.get(
            "/api/v1/linked-data/instances",
            params={"isbn": "9780123456789"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_get_instances_by_work(self, client, test_bibframe_instance, test_bibframe_work):
        """Test getting instances for a specific work."""
        response = await client.get(
            "/api/v1/linked-data/instances",
            params={"work_id": test_bibframe_work.id},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


# ============================================================================
# Item Endpoint Tests
# ============================================================================


@pytest.mark.integration
class TestLinkedDataItemEndpoints:
    """Test BIBFRAME Item API endpoints."""

    async def test_list_items(self, client, test_bibframe_item):
        """Test listing BIBFRAME items."""
        response = await client.get("/api/v1/linked-data/items")

        assert response.status_code == 200
        data = response.json()
        assert "items" in data

    async def test_get_item_json(self, client, test_bibframe_item):
        """Test getting an item as JSON."""
        response = await client.get(f"/api/v1/linked-data/items/{test_bibframe_item.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["barcode"] == "BF-TEST-001"
        assert data["library_branch"] == "Main"

    async def test_search_items_by_barcode(self, client, test_bibframe_item):
        """Test searching items by barcode."""
        response = await client.get(
            "/api/v1/linked-data/items",
            params={"barcode": "BF-TEST-001"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    async def test_search_items_by_branch(self, client, test_bibframe_item):
        """Test searching items by branch."""
        response = await client.get(
            "/api/v1/linked-data/items",
            params={"branch": "Main"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1


# ============================================================================
# SPARQL Endpoint Tests
# ============================================================================


@pytest.mark.integration
class TestSparqlEndpoint:
    """Test SPARQL query endpoint."""

    async def test_sparql_get_query(self, client, test_bibframe_work):
        """Test SPARQL query via GET."""
        query = "SELECT ?title WHERE { ?work bf:title ?title } LIMIT 5"
        response = await client.get(
            "/api/v1/sparql/query",
            params={"query": query},
        )

        assert response.status_code == 200
        data = response.json()
        assert "head" in data
        assert "results" in data
        assert "vars" in data["head"]

    async def test_sparql_post_query(self, client, test_bibframe_work):
        """Test SPARQL query via POST."""
        query = "SELECT ?work ?title WHERE { ?work a bf:Work . ?work bf:title ?title } LIMIT 10"
        response = await client.post(
            "/api/v1/sparql/query",
            content=query,
            headers={"Content-Type": "application/sparql-query"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "head" in data
        assert "results" in data

    async def test_sparql_json_results(self, client, test_bibframe_work):
        """Test SPARQL query returns JSON results."""
        query = "SELECT ?title WHERE { ?work bf:title ?title } LIMIT 1"
        response = await client.get(
            "/api/v1/sparql/query",
            params={"query": query, "format": "json"},
            headers={"Accept": "application/sparql-results+json"},
        )

        assert response.status_code == 200
        assert "application/sparql-results+json" in response.headers["content-type"]

    async def test_sparql_xml_results(self, client, test_bibframe_work):
        """Test SPARQL query returns XML results."""
        query = "SELECT ?title WHERE { ?work bf:title ?title } LIMIT 1"
        response = await client.get(
            "/api/v1/sparql/query",
            params={"query": query, "format": "xml"},
        )

        assert response.status_code == 200
        assert "xml" in response.headers["content-type"]
        assert "<?xml" in response.text

    async def test_sparql_csv_results(self, client, test_bibframe_work):
        """Test SPARQL query returns CSV results."""
        query = "SELECT ?title WHERE { ?work bf:title ?title } LIMIT 1"
        response = await client.get(
            "/api/v1/sparql/query",
            params={"query": query, "format": "csv"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]

    async def test_sparql_invalid_query(self, client):
        """Test SPARQL endpoint handles invalid query."""
        response = await client.get(
            "/api/v1/sparql/query",
            params={"query": "INVALID QUERY SYNTAX"},
        )

        assert response.status_code == 400

    async def test_sparql_service_description(self, client):
        """Test SPARQL service description endpoint."""
        response = await client.get("/api/v1/sparql")

        assert response.status_code == 200

    async def test_sparql_prefixes(self, client):
        """Test SPARQL prefixes endpoint."""
        response = await client.get("/api/v1/sparql/prefixes")

        assert response.status_code == 200
        data = response.json()
        assert "prefixes" in data
        assert "bf" in data["prefixes"]

    async def test_sparql_examples(self, client):
        """Test SPARQL examples endpoint."""
        response = await client.get("/api/v1/sparql/examples")

        assert response.status_code == 200
        data = response.json()
        assert "examples" in data
        assert len(data["examples"]) > 0


# ============================================================================
# Schema.org Endpoint Tests
# ============================================================================


@pytest.mark.integration
class TestSchemaOrgEndpoints:
    """Test Schema.org markup endpoints."""

    async def test_work_schema_org(self, client, test_bibframe_work):
        """Test getting Schema.org markup for a work."""
        response = await client.get(f"/api/v1/linked-data/schema-org/work/{test_bibframe_work.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["@context"] == "https://schema.org"
        assert data["@type"] in ["Book", "CreativeWork"]
        assert data["name"] == "Test BIBFRAME Work"

    async def test_instance_schema_org(self, client, test_bibframe_instance):
        """Test getting Schema.org markup for an instance."""
        response = await client.get(
            f"/api/v1/linked-data/schema-org/instance/{test_bibframe_instance.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["@context"] == "https://schema.org"
        assert "isbn" in data or "identifier" in data

    async def test_library_schema_org(self, client):
        """Test getting Schema.org markup for the library."""
        response = await client.get("/api/v1/linked-data/schema-org/library")

        assert response.status_code == 200
        data = response.json()
        assert data["@context"] == "https://schema.org"
        # @type can carry multiple Schema.org classes now (e.g.
        # ["Library", "LocalBusiness"])
        type_value = data["@type"]
        if isinstance(type_value, list):
            assert "Library" in type_value
        else:
            assert type_value == "Library"


# ============================================================================
# Contributor and Subject Endpoint Tests
# ============================================================================


@pytest.mark.integration
class TestContributorSubjectEndpoints:
    """Test Contributor and Subject API endpoints."""

    async def test_get_contributor(self, client, test_bibframe_contributor):
        """Test getting a contributor."""
        response = await client.get(
            f"/api/v1/linked-data/contributors/{test_bibframe_contributor.id}"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Author"
        assert data["viaf_id"] == "12345678"

    async def test_get_subject(self, client, test_bibframe_subject):
        """Test getting a subject."""
        response = await client.get(f"/api/v1/linked-data/subjects/{test_bibframe_subject.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["label"] == "Computer programming"
        assert data["lcsh_id"] == "sh85029533"


# ============================================================================
# Authority Link Tests
# ============================================================================


@pytest.mark.integration
class TestAuthorityLinkEndpoints:
    """Test Authority Link API endpoints."""

    async def test_lookup_authority_viaf(self, client, test_bibframe_contributor):
        """Test looking up a VIAF authority."""
        response = await client.get(
            f"/api/v1/linked-data/authority-links/lookup/viaf/{test_bibframe_contributor.viaf_id}"
        )

        # May return 200 or 404 depending on whether links exist
        assert response.status_code in [200, 404]


# ============================================================================
# Content Negotiation Tests
# ============================================================================


@pytest.mark.integration
class TestContentNegotiation:
    """Test content negotiation for different RDF formats."""

    async def test_default_to_json(self, client, test_bibframe_work):
        """Test default response is JSON."""
        response = await client.get(f"/api/v1/linked-data/works/{test_bibframe_work.id}")

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

    async def test_accept_jsonld(self, client, test_bibframe_work):
        """Test Accept: application/ld+json returns JSON-LD."""
        response = await client.get(
            f"/api/v1/linked-data/works/{test_bibframe_work.id}",
            headers={"Accept": "application/ld+json"},
        )

        assert response.status_code == 200
        assert "ld+json" in response.headers["content-type"]
        data = response.json()
        assert "@context" in data

    async def test_accept_turtle(self, client, test_bibframe_work):
        """Test Accept: text/turtle returns Turtle."""
        response = await client.get(
            f"/api/v1/linked-data/works/{test_bibframe_work.id}",
            headers={"Accept": "text/turtle"},
        )

        assert response.status_code == 200
        assert "turtle" in response.headers["content-type"]
        assert "@prefix" in response.text or "PREFIX" in response.text

    async def test_accept_with_quality(self, client, test_bibframe_work):
        """Test Accept header with quality values."""
        response = await client.get(
            f"/api/v1/linked-data/works/{test_bibframe_work.id}",
            headers={"Accept": "text/turtle;q=0.9, application/ld+json;q=1.0"},
        )

        assert response.status_code == 200
        # Should prefer JSON-LD due to higher quality value
        assert "json" in response.headers["content-type"]


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
class TestLinkedDataErrorHandling:
    """Test error handling for Linked Data endpoints."""

    async def test_work_not_found(self, client):
        """Test 404 for nonexistent work."""
        response = await client.get("/api/v1/linked-data/works/99999")
        assert response.status_code == 404

    async def test_instance_not_found(self, client):
        """Test 404 for nonexistent instance."""
        response = await client.get("/api/v1/linked-data/instances/99999")
        assert response.status_code == 404

    async def test_item_not_found(self, client):
        """Test 404 for nonexistent item."""
        response = await client.get("/api/v1/linked-data/items/99999")
        assert response.status_code == 404

    async def test_invalid_work_id(self, client):
        """Test invalid work ID format."""
        response = await client.get("/api/v1/linked-data/works/invalid")
        assert response.status_code == 422
