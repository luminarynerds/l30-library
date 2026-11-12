# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for manga cataloging efficiency features.

Covers:
- MangaCatalogingTemplate model and CRUD
- MangaVolumeRecord model and CRUD
- Quick add volume with auto-populated fields
- Copy and increment volume records
- ISBN lookup with full metadata auto-fill
- Cover image auto-fetch from ISBN
- Series info auto-population from previous volumes
- Batch create records for multi-volume purchases
- Default values for publisher, genre, format
- Next volume number calculation
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.models.catalog import CatalogItem, ItemType
from app.models.manga_cataloging import MangaCatalogingTemplate, MangaVolumeRecord
from app.schemas.manga_cataloging import (
    BatchCreateMangaVolumesRequest,
    CopyAndIncrementVolumeRequest,
    ISBNLookupResponse,
    MangaCatalogingStats,
    MangaCatalogingTemplateCreate,
    MangaCatalogingTemplateResponse,
    MangaCatalogingTemplateUpdate,
    MangaVolumeRecordCreate,
    MangaVolumeRecordResponse,
    QuickAddMangaVolumeRequest,
    SeriesInfoResponse,
)
from app.services.manga_cataloging_service import MangaCatalogingService


# ============================================================================
# Schema Validation Tests
# ============================================================================


class TestMangaCatalogingTemplateSchemas:
    """Test template schema validation and defaults."""

    def test_template_create_defaults(self):
        """Template create should have manga-specific defaults pre-set."""
        template = MangaCatalogingTemplateCreate(
            name="Naruto Template",
            series_title="Naruto",
        )
        assert template.original_language == "Japanese"
        assert template.genre == "manga,graphic novels"
        assert template.subjects == "manga,graphic novels,Japanese comics"
        assert template.catalog_series_type == "graphic_novel_series"
        assert template.format == "volume"
        assert template.auto_increment_volume is True
        assert template.auto_fetch_cover is True
        assert template.auto_populate_series_info is True
        assert template.covers_color is True

    def test_template_create_custom_values(self):
        """Template create should accept custom overrides."""
        template = MangaCatalogingTemplateCreate(
            name="Custom Template",
            series_title="Attack on Titan",
            publisher="Kodansha Comics",
            original_language="Japanese",
            genre="manga,action,dark fantasy",
            format="omnibus",
            auto_fetch_cover=False,
        )
        assert template.publisher == "Kodansha Comics"
        assert template.genre == "manga,action,dark fantasy"
        assert template.format == "omnibus"
        assert template.auto_fetch_cover is False

    def test_template_update_partial(self):
        """Template update should allow partial field updates."""
        update = MangaCatalogingTemplateUpdate(publisher="VIZ Media")
        data = update.model_dump(exclude_unset=True)
        assert data == {"publisher": "VIZ Media"}
        assert "name" not in data

    def test_template_response_from_attributes(self):
        """Template response should support from_attributes mode."""
        config = MangaCatalogingTemplateResponse.model_config
        assert config.get("from_attributes") is True


class TestQuickAddVolumeSchema:
    """Test quick add volume request schema."""

    def test_quick_add_required_fields(self):
        """Quick add requires series_title, volume_number, and title."""
        request = QuickAddMangaVolumeRequest(
            series_title="One Piece",
            volume_number=1,
            title="One Piece Vol. 1",
        )
        assert request.series_title == "One Piece"
        assert request.volume_number == 1
        assert request.auto_fetch_cover is True

    def test_quick_add_has_original_language(self):
        """Quick add should support original_language field."""
        request = QuickAddMangaVolumeRequest(
            series_title="One Piece",
            volume_number=1,
            title="One Piece Vol. 1",
            original_language="Japanese",
        )
        assert request.original_language == "Japanese"

    def test_quick_add_copy_from_volume(self):
        """Quick add should support copy_from_volume_id for cloning."""
        request = QuickAddMangaVolumeRequest(
            series_title="One Piece",
            volume_number=2,
            title="One Piece Vol. 2",
            copy_from_volume_id=42,
        )
        assert request.copy_from_volume_id == 42

    def test_quick_add_defaults(self):
        """Quick add should have sensible defaults."""
        request = QuickAddMangaVolumeRequest(
            series_title="Test",
            volume_number=1,
            title="Test Vol. 1",
        )
        assert request.author is None
        assert request.isbn is None
        assert request.publisher is None
        assert request.original_language is None
        assert request.publication_date is None
        assert request.template_id is None
        assert request.copy_from_volume_id is None
        assert request.auto_fetch_cover is True


class TestCopyAndIncrementSchema:
    """Test copy and increment request schema."""

    def test_copy_increment_required_fields(self):
        request = CopyAndIncrementVolumeRequest(
            source_volume_id=10,
            new_volume_number=11,
        )
        assert request.source_volume_id == 10
        assert request.new_volume_number == 11
        assert request.isbn is None

    def test_copy_increment_with_isbn(self):
        request = CopyAndIncrementVolumeRequest(
            source_volume_id=10,
            new_volume_number=11,
            isbn="978-1-4215-0011-4",
        )
        assert request.isbn == "978-1-4215-0011-4"


class TestBatchCreateSchema:
    """Test batch create request schema."""

    def test_batch_create_required_fields(self):
        request = BatchCreateMangaVolumesRequest(
            series_title="Dragon Ball",
            volumes=[
                {"volume_number": 1, "title": "Dragon Ball Vol. 1"},
                {"volume_number": 2, "title": "Dragon Ball Vol. 2"},
            ],
        )
        assert request.series_title == "Dragon Ball"
        assert len(request.volumes) == 2
        assert request.start_volume == 1
        assert request.template_id is None

    def test_batch_create_with_template(self):
        request = BatchCreateMangaVolumesRequest(
            series_title="Dragon Ball",
            template_id=5,
            start_volume=3,
            volumes=[{"volume_number": 3, "title": "Dragon Ball Vol. 3"}],
        )
        assert request.template_id == 5
        assert request.start_volume == 3


class TestISBNLookupResponse:
    """Test ISBN lookup response schema."""

    def test_isbn_lookup_found(self):
        resp = ISBNLookupResponse(
            isbn="978-1-4215-0001-5",
            found=True,
            source="open_library",
            title="Naruto Vol. 1",
            author="Masashi Kishimoto",
            publisher="VIZ Media",
            publish_date="2003-08-06",
            page_count=192,
            cover_url="https://covers.openlibrary.org/b/id/12345-M.jpg",
        )
        assert resp.found is True
        assert resp.title == "Naruto Vol. 1"
        assert resp.cover_url is not None

    def test_isbn_lookup_not_found(self):
        resp = ISBNLookupResponse(
            isbn="000-0-0000-0000-0",
            found=False,
        )
        assert resp.found is False
        assert resp.title is None
        assert resp.source is None


class TestSeriesInfoResponse:
    """Test series info response schema."""

    def test_series_info_with_next_volume(self):
        resp = SeriesInfoResponse(
            series_title="Naruto",
            total_volumes=10,
            next_volume_number=11,
            auto_populate_info={
                "publisher": "VIZ Media",
                "genre": "manga,graphic novels",
            },
        )
        assert resp.next_volume_number == 11
        assert resp.total_volumes == 10


class TestMangaCatalogingStatsSchema:
    """Test cataloging statistics schema."""

    def test_stats_schema(self):
        stats = MangaCatalogingStats(
            total_templates=5,
            total_volumes=150,
            total_series=12,
            avg_volumes_per_series=12.5,
            templates_with_auto_cover=4,
        )
        assert stats.total_templates == 5
        assert stats.avg_volumes_per_series == 12.5


# ============================================================================
# Model Tests
# ============================================================================


class TestMangaCatalogingTemplateModel:
    """Test MangaCatalogingTemplate model attributes."""

    def test_template_table_name(self):
        assert MangaCatalogingTemplate.__tablename__ == "manga_cataloging_templates"

    def test_template_has_default_fields(self):
        """Template model should have JSONB default_fields with manga defaults."""
        template = MangaCatalogingTemplate()
        # The default_fields column default includes manga-specific Dewey/LC
        assert hasattr(template, "default_fields")

    def test_template_has_auto_flags(self):
        """Template model should have auto-increment, auto-cover, auto-populate flags."""
        template = MangaCatalogingTemplate()
        assert hasattr(template, "auto_increment_volume")
        assert hasattr(template, "auto_fetch_cover")
        assert hasattr(template, "auto_populate_series_info")

    def test_template_has_series_defaults(self):
        """Template should store series-level defaults."""
        template = MangaCatalogingTemplate()
        assert hasattr(template, "series_title")
        assert hasattr(template, "author")
        assert hasattr(template, "publisher")
        assert hasattr(template, "original_language")
        assert hasattr(template, "genre")
        assert hasattr(template, "subjects")
        assert hasattr(template, "format")
        assert hasattr(template, "isbn_pattern")


class TestMangaVolumeRecordModel:
    """Test MangaVolumeRecord model attributes."""

    def test_volume_table_name(self):
        assert MangaVolumeRecord.__tablename__ == "manga_volume_records"

    def test_volume_has_catalog_item_link(self):
        """Volume should link to a catalog item."""
        vol = MangaVolumeRecord()
        assert hasattr(vol, "catalog_item_id")

    def test_volume_has_previous_volume_link(self):
        """Volume should link to previous volume for copy-increment chain."""
        vol = MangaVolumeRecord()
        assert hasattr(vol, "previous_volume_id")

    def test_volume_has_cover_fields(self):
        """Volume should track cover image URL and source."""
        vol = MangaVolumeRecord()
        assert hasattr(vol, "cover_image_url")
        assert hasattr(vol, "cover_fetch_source")


# ============================================================================
# Service Tests
# ============================================================================


class TestMangaCatalogingServiceCoverFetch:
    """Test cover fetching from ISBN."""

    @pytest.mark.asyncio
    async def test_fetch_cover_returns_none_for_empty_isbn(self):
        result = await MangaCatalogingService.fetch_cover_from_isbn("")
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_cover_returns_none_for_none_isbn(self):
        result = await MangaCatalogingService.fetch_cover_from_isbn(None)
        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_cover_open_library_success(self):
        """Cover fetch should return Open Library URL when available."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"covers": [12345]}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await MangaCatalogingService.fetch_cover_from_isbn("978-1-4215-0001-5")
            assert result == "https://covers.openlibrary.org/b/id/12345-M.jpg"

    @pytest.mark.asyncio
    async def test_fetch_cover_google_books_fallback(self):
        """Cover fetch should fall back to Google Books when Open Library fails."""
        fail_response = MagicMock()
        fail_response.status_code = 404

        google_response = MagicMock()
        google_response.status_code = 200
        google_response.json.return_value = {
            "items": [{
                "volumeInfo": {
                    "imageLinks": {"thumbnail": "https://books.google.com/cover.jpg"}
                }
            }]
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [fail_response, google_response]
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await MangaCatalogingService.fetch_cover_from_isbn("978-1-4215-0001-5")
            assert result == "https://books.google.com/cover.jpg"


class TestMangaCatalogingServiceISBNLookup:
    """Test ISBN metadata lookup for auto-fill."""

    @pytest.mark.asyncio
    async def test_lookup_isbn_empty(self):
        result = await MangaCatalogingService.lookup_isbn_metadata("")
        assert result["found"] is False

    @pytest.mark.asyncio
    async def test_lookup_isbn_open_library_success(self):
        """ISBN lookup should return full metadata from Open Library."""
        isbn_response = MagicMock()
        isbn_response.status_code = 200
        isbn_response.json.return_value = {
            "title": "Naruto Vol. 1",
            "publishers": ["VIZ Media"],
            "number_of_pages": 192,
            "publish_date": "2003-08-06",
            "covers": [12345],
            "authors": [{"key": "/authors/OL123A"}],
        }

        author_response = MagicMock()
        author_response.status_code = 200
        author_response.json.return_value = {"name": "Masashi Kishimoto"}

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [isbn_response, author_response]
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await MangaCatalogingService.lookup_isbn_metadata("978-1-4215-0001-5")

        assert result["found"] is True
        assert result["source"] == "open_library"
        assert result["title"] == "Naruto Vol. 1"
        assert result["publisher"] == "VIZ Media"
        assert result["author"] == "Masashi Kishimoto"
        assert result["page_count"] == 192
        assert "covers.openlibrary.org" in result["cover_url"]

    @pytest.mark.asyncio
    async def test_lookup_isbn_google_books_fallback(self):
        """ISBN lookup should fall back to Google Books."""
        fail_response = MagicMock()
        fail_response.status_code = 404

        google_response = MagicMock()
        google_response.status_code = 200
        google_response.json.return_value = {
            "items": [{
                "volumeInfo": {
                    "title": "One Piece Vol. 1",
                    "authors": ["Eiichiro Oda"],
                    "publisher": "VIZ Media",
                    "publishedDate": "2003-06-01",
                    "pageCount": 208,
                    "language": "en",
                    "categories": ["Comics & Graphic Novels"],
                    "imageLinks": {"thumbnail": "https://books.google.com/cover.jpg"},
                }
            }]
        }

        with patch("httpx.AsyncClient") as MockClient:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [fail_response, google_response]
            mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
            mock_client_instance.__aexit__ = AsyncMock(return_value=False)
            MockClient.return_value = mock_client_instance

            result = await MangaCatalogingService.lookup_isbn_metadata("978-1-56931-901-7")

        assert result["found"] is True
        assert result["source"] == "google_books"
        assert result["title"] == "One Piece Vol. 1"
        assert result["author"] == "Eiichiro Oda"
        assert result["publisher"] == "VIZ Media"
        assert result["language"] == "en"
        assert result["subjects"] == "Comics & Graphic Novels"


class TestMangaCatalogingServiceTemplateDefaults:
    """Test template default values for publisher, genre, format."""

    def test_template_model_default_genre(self):
        """Default genre should be manga,graphic novels."""
        _ = MangaCatalogingTemplate()
        # Column default is set at the database level, but the model
        # defines it. We verify the column definition.
        col = MangaCatalogingTemplate.__table__.columns["genre"]
        assert col.default.arg == "manga,graphic novels"

    def test_template_model_default_subjects(self):
        col = MangaCatalogingTemplate.__table__.columns["subjects"]
        assert col.default.arg == "manga,graphic novels,Japanese comics"

    def test_template_model_default_format(self):
        col = MangaCatalogingTemplate.__table__.columns["format"]
        assert col.default.arg == "volume"

    def test_template_model_default_language(self):
        col = MangaCatalogingTemplate.__table__.columns["original_language"]
        assert col.default.arg == "Japanese"

    def test_template_model_default_item_type(self):
        col = MangaCatalogingTemplate.__table__.columns["item_type"]
        assert col.default.arg == "book"

    def test_template_model_auto_flags_default_true(self):
        for flag_name in ["auto_increment_volume", "auto_fetch_cover", "auto_populate_series_info"]:
            col = MangaCatalogingTemplate.__table__.columns[flag_name]
            assert col.default.arg is True, f"{flag_name} should default to True"

    def test_template_model_default_fields_json(self):
        """default_fields should contain manga-specific Dewey and LC classification."""
        col = MangaCatalogingTemplate.__table__.columns["default_fields"]
        defaults = col.default.arg
        assert defaults["dewey_decimal"] == "741.5952"
        assert defaults["lc_classification"] == "PN1997.2"
        assert defaults["location"] == "Manga Section"


# ============================================================================
# API Endpoint Schema Composition Tests
# ============================================================================


class TestAPIEndpointSchemas:
    """Verify that API endpoint schemas are properly wired."""

    def test_isbn_lookup_response_schema_fields(self):
        """ISBNLookupResponse should have all auto-fill fields."""
        fields = ISBNLookupResponse.model_fields
        expected = [
            "isbn", "found", "source", "title", "author", "publisher",
            "publish_date", "page_count", "cover_url", "description",
            "language", "subjects",
        ]
        for field in expected:
            assert field in fields, f"Missing field: {field}"

    def test_series_info_response_has_next_volume(self):
        """SeriesInfoResponse should include next_volume_number."""
        fields = SeriesInfoResponse.model_fields
        assert "next_volume_number" in fields
        assert "auto_populate_info" in fields

    def test_volume_record_response_has_cover_fields(self):
        """MangaVolumeRecordResponse should have cover image fields."""
        fields = MangaVolumeRecordResponse.model_fields
        assert "cover_image_url" in fields
        assert "cover_fetch_source" in fields
        assert "previous_volume_id" in fields

    def test_template_response_has_all_defaults(self):
        """Template response should expose all default/auto fields."""
        fields = MangaCatalogingTemplateResponse.model_fields
        for field in ["genre", "subjects", "format", "publisher",
                      "auto_increment_volume", "auto_fetch_cover",
                      "auto_populate_series_info", "default_fields"]:
            assert field in fields, f"Missing field: {field}"


class TestQuickAddVolumeEndToEnd:
    """Test quick add volume logic end-to-end (mocked DB)."""

    @pytest.mark.asyncio
    async def test_quick_add_creates_catalog_item_and_volume(self):
        """Quick add should create both a CatalogItem and MangaVolumeRecord."""
        # Mock DB session
        db = AsyncMock()

        # Mock template lookup (returns None first, then creates)
        mock_execute = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_execute.return_value = mock_result
        db.execute = mock_execute

        # Make flush set IDs on added objects
        added_objects = []
        _id_counter = [0]

        def mock_add(obj):
            added_objects.append(obj)

        async def mock_flush():
            for obj in added_objects:
                if not hasattr(obj, "id") or obj.id is None:
                    _id_counter[0] += 1
                    obj.id = _id_counter[0]

        db.add = mock_add
        db.flush = mock_flush
        db.commit = AsyncMock()

        request = QuickAddMangaVolumeRequest(
            series_title="Naruto",
            volume_number=1,
            title="Naruto Vol. 1",
            author="Masashi Kishimoto",
            isbn="978-1-4215-0001-5",
            publisher="VIZ Media",
            auto_fetch_cover=False,  # Skip external calls
        )

        with patch.object(
            MangaCatalogingService,
            "get_series_info_from_previous_volumes",
            return_value={"location": "Manga Section"},
        ):
            result = await MangaCatalogingService.quick_add_manga_volume(
                db, request, cataloger_user_id=1
            )

        assert result["status"] == "created"
        assert result["series_title"] == "Naruto"
        assert result["volume_number"] == 1
        assert result["title"] == "Naruto Vol. 1"

        # Should have created: template, catalog_item, volume_record, series_order
        types_created = {type(obj).__name__ for obj in added_objects}
        assert "MangaCatalogingTemplate" in types_created
        assert "CatalogItem" in types_created
        assert "MangaVolumeRecord" in types_created


class TestBatchCreateVolumes:
    """Test batch volume creation logic."""

    def test_batch_request_accepts_multiple_volumes(self):
        """Batch request should accept a list of volume data."""
        request = BatchCreateMangaVolumesRequest(
            series_title="My Hero Academia",
            volumes=[
                {"volume_number": i, "title": f"My Hero Academia Vol. {i}"}
                for i in range(1, 11)
            ],
        )
        assert len(request.volumes) == 10

    def test_batch_request_with_isbn_list(self):
        """Batch request should support ISBN per volume."""
        request = BatchCreateMangaVolumesRequest(
            series_title="Demon Slayer",
            volumes=[
                {"volume_number": 1, "title": "Vol. 1", "isbn": "978-1-9747-0053-2"},
                {"volume_number": 2, "title": "Vol. 2", "isbn": "978-1-9747-0054-9"},
            ],
        )
        assert request.volumes[0]["isbn"] == "978-1-9747-0053-2"


class TestCopyAndIncrementVolume:
    """Test copy and increment volume logic."""

    def test_copy_request_schema(self):
        """Copy request requires source_volume_id and new_volume_number."""
        request = CopyAndIncrementVolumeRequest(
            source_volume_id=42,
            new_volume_number=43,
            isbn="978-1-4215-0043-5",
        )
        assert request.source_volume_id == 42
        assert request.new_volume_number == 43
