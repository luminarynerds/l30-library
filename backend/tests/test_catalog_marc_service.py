# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD Tests for MARC Export Service

Tests the catalog_marc_service module for generating MARC21, MARCXML, and Dublin Core exports.
These tests follow TDD principles - write tests first, implement service second.
"""

import pytest
from datetime import datetime
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import CatalogItem, ItemType, ItemStatus
from app.models.user import User, UserRole


class TestMARCExportFormats:
    """Test MARC export format generation"""

    @pytest.mark.asyncio
    async def test_generates_valid_marc21_binary_format(self, test_db: AsyncSession, test_catalog_item: CatalogItem):
        """Test that MARC21 binary format is generated correctly"""
        from app.services.catalog_marc_service import CatalogMARCService

        # The service builds a pymarc Record from an already-loaded item, then
        # serializes it -- it doesn't take (db, item_id) or do its own lookup.
        service = CatalogMARCService()
        record = service.create_marc_record(test_catalog_item)
        marc_binary = service.export_marc21(record)

        # MARC21 binary starts with record length (5 digits) and status byte
        assert marc_binary is not None
        assert len(marc_binary) > 0
        # Leader should be 24 bytes
        assert marc_binary[0:5].decode('ascii').isdigit()  # First 5 bytes are record length
        # Field terminator is 0x1E, record terminator is 0x1D
        assert b'\x1e' in marc_binary or b'\x1d' in marc_binary

    @pytest.mark.asyncio
    async def test_generates_valid_marcxml_format(self, test_db: AsyncSession, test_catalog_item: CatalogItem):
        """Test that MARCXML format is generated correctly"""
        from app.services.catalog_marc_service import CatalogMARCService

        service = CatalogMARCService()
        record = service.create_marc_record(test_catalog_item)
        marcxml = service.export_marcxml(record)

        assert marcxml is not None
        assert '<?xml version="1.0"' in marcxml
        assert '<record' in marcxml
        assert '<leader>' in marcxml
        assert '<controlfield' in marcxml or '<datafield' in marcxml
        assert '</record>' in marcxml

    @pytest.mark.asyncio
    async def test_generates_valid_dublin_core_format(self, test_db: AsyncSession, test_catalog_item: CatalogItem):
        """Test that Dublin Core XML format is generated correctly"""
        from app.services.catalog_marc_service import CatalogMARCService

        # export_dublin_core takes the item directly -- no MARC record needed.
        service = CatalogMARCService()
        dc_xml = service.export_dublin_core(test_catalog_item)

        assert dc_xml is not None
        # lxml's serializer emits single-quoted attributes in the XML
        # declaration (unlike pymarc's MARCXML writer, which uses double
        # quotes -- see test_generates_valid_marcxml_format above).
        assert "<?xml version='1.0'" in dc_xml
        assert 'xmlns:dc="http://purl.org/dc/elements/1.1/"' in dc_xml
        assert '<dc:title>' in dc_xml
        assert test_catalog_item.title in dc_xml


class TestMARCFieldMapping:
    """Test MARC field mapping from catalog items"""

    @pytest.mark.asyncio
    async def test_maps_all_catalog_item_fields_correctly(self, test_db: AsyncSession):
        """Test that all catalog item fields are mapped to MARC fields"""
        from app.services.catalog_marc_service import CatalogMARCService

        # Create a catalog item with all fields populated
        item = CatalogItem(
            title="Complete Test Book",
            author="Test Author, Jane",
            isbn="978-0-123456-78-9",
            publisher="Test Publisher",
            publication_year=2024,
            description="A complete test book with all fields",
            subjects="Fiction; Adventure; Science Fiction",
            call_number="813.54 AUT",
            dewey_decimal="813.54",
            lc_classification="PS3551.U8",
            page_count=350,
            item_type=ItemType.book,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Check key MARC fields
        assert item.title in marcxml  # 245 - Title
        assert item.author in marcxml  # 100/700 - Author
        # 020 $a preserves the ISBN as stored (hyphens included), it isn't
        # normalized on export.
        assert item.isbn in marcxml  # 020 - ISBN
        assert item.publisher in marcxml  # 260 - Publication
        assert str(item.publication_year) in marcxml  # 260 - Year
        assert item.call_number in marcxml  # 050/082 - Call number

    @pytest.mark.asyncio
    async def test_handles_missing_fields_gracefully(self, test_db: AsyncSession):
        """Test that MARC export handles missing optional fields"""
        from app.services.catalog_marc_service import CatalogMARCService

        # Create minimal catalog item with only required fields
        item = CatalogItem(
            title="Minimal Test Book",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()

        # Should not raise exception
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)
        assert marcxml is not None
        assert '<dc:title>Minimal Test Book</dc:title>' in service.export_dublin_core(item)

    @pytest.mark.asyncio
    async def test_handles_multiple_subjects(self, test_db: AsyncSession):
        """Test that multiple subjects are properly split and mapped"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Multi-Subject Book",
            subjects="Fiction; Adventure; Mystery; Thriller",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Each subject should appear in separate 650 field
        assert 'Fiction' in marcxml
        assert 'Adventure' in marcxml
        assert 'Mystery' in marcxml


class TestMARCExportAPI:
    """Test MARC export API endpoints"""

    @pytest.mark.asyncio
    async def test_export_single_record_via_api_binary(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem, staff_client
    ):
        """Test exporting single record in MARC21 binary format via API.

        Uses the shared staff_client fixture (overrides get_current_user
        directly, no real login needed) rather than a manually built
        AsyncClient(transport=ASGITransport(app=app)): the latter falls
        through to the app's real get_db, whose pooled connection can bind
        to a stale event loop from an earlier test in this module and raise
        "RuntimeError: Event loop is closed" when other test files share the
        run.
        """
        response = await staff_client.get(
            f"/api/v1/catalog/{test_catalog_item.id}/marc",
            params={"format": "binary"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/marc"
        assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_export_single_record_via_api_marcxml(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem, staff_client
    ):
        """Test exporting single record in MARCXML format via API"""
        # Export MARCXML -- the route's format values are "binary",
        # "marcxml", or "dc" (not "xml"), and it returns media_type
        # "application/xml" for marcxml (see export_item_marc).
        response = await staff_client.get(
            f"/api/v1/catalog/{test_catalog_item.id}/marc",
            params={"format": "marcxml"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        assert b'<record' in response.content

    @pytest.mark.asyncio
    async def test_export_single_record_via_api_dublin_core(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem, staff_client
    ):
        """Test exporting single record in Dublin Core format via API"""
        response = await staff_client.get(
            f"/api/v1/catalog/{test_catalog_item.id}/marc",
            params={"format": "dc"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/xml"
        assert b'xmlns:dc="http://purl.org/dc/elements/1.1/"' in response.content

    @pytest.mark.asyncio
    async def test_export_batch_records_via_api(
        self, test_db: AsyncSession, staff_client
    ):
        """Test exporting batch records via API.

        The batch export route (GET /catalog/export/marc, see
        export_catalog_marc_batch) filters by item_type/status/location/limit
        -- there is no POST .../marc/batch by-item_ids endpoint, so this
        exercises the location filter instead of an explicit id list.
        """
        # Create multiple catalog items sharing a distinguishing location
        items = []
        for i in range(5):
            item = CatalogItem(
                title=f"Test Book {i+1}",
                author=f"Author {i+1}",
                isbn=f"978-0-12345-{i:03d}-{i}",
                location="Batch API Test Location",
                status=ItemStatus.available,
            )
            test_db.add(item)
            items.append(item)
        await test_db.commit()

        response = await staff_client.get(
            "/api/v1/catalog/export/marc",
            params={
                "format": "marcxml",
                "location": "Batch API Test Location",
                "limit": 10,
            },
        )

        assert response.status_code == 200, response.text
        content = response.content.decode('utf-8')
        assert '<collection' in content
        # Should have 5 records
        assert content.count('<record') == 5

    @pytest.mark.asyncio
    async def test_export_respects_max_limit_1000_records(
        self, test_db: AsyncSession, staff_client
    ):
        """Test that batch export rejects a limit above 1000.

        limit is a query param validated by FastAPI (Query(..., le=1000)),
        so exceeding it is a 422 validation error, not a custom 400.
        """
        # Export batch should reject a limit over 1000
        response = await staff_client.get(
            "/api/v1/catalog/export/marc",
            params={"format": "marcxml", "limit": 1501},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_returns_404_for_nonexistent_item(
        self, test_db: AsyncSession, staff_client
    ):
        """Test that exporting non-existent item returns 404.

        Uses the shared staff_client fixture rather than a manually built
        AsyncClient(transport=ASGITransport(app=app)): the latter falls
        through to the app's real get_db, whose pooled connection can bind
        to a stale event loop from an earlier test in this module and raise
        "RuntimeError: Event loop is closed".
        """
        # Export non-existent item
        response = await staff_client.get(
            "/api/v1/catalog/999999/marc",
            params={"format": "binary"},
        )

        assert response.status_code == 404


class TestMARCExportAuthentication:
    """Test MARC export authentication requirements"""

    @pytest.mark.asyncio
    async def test_requires_staff_authentication(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem, client
    ):
        """Test that MARC export requires staff authentication.

        Uses the shared client fixture (overrides get_db to reuse this
        test's own engine/session) rather than a manually built
        AsyncClient(transport=ASGITransport(app=app)): the latter falls
        through to the app's real get_db, whose pooled connection can bind
        to a stale event loop from an earlier test when other test files
        share the run ("RuntimeError: Event loop is closed").
        """
        # Try without authentication
        response = await client.get(
            f"/api/v1/catalog/{test_catalog_item.id}/marc",
            params={"format": "binary"}
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_patron_cannot_export_marc(
        self, test_db: AsyncSession, test_catalog_item: CatalogItem, test_patron: User, client
    ):
        """Test that patrons cannot export MARC records"""
        # Login as patron
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": test_patron.email, "password": "TestPassword123!"}
        )
        token = login_response.json()["access_token"]

        # Try to export MARC
        response = await client.get(
            f"/api/v1/catalog/{test_catalog_item.id}/marc",
            params={"format": "binary"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
