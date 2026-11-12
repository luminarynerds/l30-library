# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for CatalogBibframeSync.

Regression coverage for PR #239: the sync service was writing to
nonexistent columns (shelf_mark, held_by, status, location, isbn),
which SQLAlchemy rejects with TypeError. The service's broad
try/except swallowed the error and returned None, so catalog
operations succeeded but no BIBFRAME row was written.

These tests would have caught that bug at the model layer (schema
invariants) and at the service layer (return value + db.add calls).
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.bibframe import (
    BibframeInstance,
    BibframeItem,
    BibframeWork,
    CarrierType,
    InstanceType,
    MediaType,
)
from app.models.catalog import CatalogItem, ItemStatus, ItemType
from app.services.catalog_bibframe_sync import CatalogBibframeSync, _split_isbn


# ============================================================================
# Schema invariants — model accepts the kwargs the sync service writes
# ============================================================================


@pytest.mark.unit
class TestBibframeSchemaInvariants:
    """Lock down the column names the sync service depends on."""

    def test_bibframe_item_accepts_sync_service_kwargs(self):
        item = BibframeItem(
            instance_id=1,
            barcode="TEST001",
            call_number="813.54 SMI",
            circulation_status="available",
            library_branch="Main",
            shelving_location="STK-A12",
        )
        assert item.call_number == "813.54 SMI"
        assert item.circulation_status == "available"
        assert item.library_branch == "Main"
        assert item.shelving_location == "STK-A12"

    def test_bibframe_work_accepts_summary_kwarg(self):
        work = BibframeWork(title="t", summary="A book about things")
        assert work.summary == "A book about things"

    @pytest.mark.parametrize("model_cls,bad_kwarg", [
        (BibframeItem, "description"),
        (BibframeInstance, "description"),
    ])
    def test_description_is_not_a_column_on_item_or_instance(self, model_cls, bad_kwarg):
        """Catalog description must route to BibframeWork.summary, not Item/Instance.description."""
        with pytest.raises(TypeError, match=bad_kwarg):
            model_cls(**{bad_kwarg: "x"})

    def test_bibframe_instance_accepts_isbn_13_kwarg(self):
        # `language` belongs to BibframeWork (bf:language), not
        # BibframeInstance -- it was never a valid kwarg here.
        instance = BibframeInstance(
            work_id=1,
            title="Test",
            isbn_13="9780123456789",
            instance_type=InstanceType.print,
            carrier_type=CarrierType.volume,
            media_type=MediaType.unmediated,
        )
        assert instance.isbn_13 == "9780123456789"

    @pytest.mark.parametrize("bad_kwarg", ["shelf_mark", "held_by", "status", "location"])
    def test_bibframe_item_rejects_legacy_column_names(self, bad_kwarg):
        with pytest.raises(TypeError, match=bad_kwarg):
            BibframeItem(instance_id=1, **{bad_kwarg: "x"})

    def test_bibframe_instance_rejects_legacy_isbn_kwarg(self):
        with pytest.raises(TypeError, match="isbn"):
            BibframeInstance(work_id=1, title="t", isbn="9780123456789")


# ============================================================================
# Service-level — create_from_catalog
# ============================================================================


def _make_catalog_item(**overrides):
    """Build a CatalogItem with sensible defaults for sync tests."""
    defaults = dict(
        id=42,
        title="Test Book",
        author="Smith, Jane",
        item_type=ItemType.book,
        status=ItemStatus.available,
        isbn="9780123456789",
        publisher="Test Press",
        publication_year=2024,
        description="A test description",
        barcode="BC-42",
        call_number="813.54 SMI",
        location="STK-A12",
        subjects="Fiction",
    )
    defaults.update(overrides)
    return CatalogItem(**defaults)


def _mock_db_session():
    """Async DB session that returns None for both work and instance lookups."""
    db = AsyncMock()
    no_result = MagicMock()
    no_result.scalar_one_or_none = MagicMock(return_value=None)
    db.execute = AsyncMock(return_value=no_result)
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.mark.unit
class TestCreateFromCatalog:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("item_type", list(ItemType))
    async def test_returns_bibframe_item_for_every_real_item_type(self, item_type):
        """Earlier versions referenced ItemType.music/audiobook_cd/comic_book/graphic_novel/board_game
        which don't exist; type_map dict construction raised AttributeError on every call,
        was caught by the broad except, and the sync silently returned None for ALL types."""
        db = _mock_db_session()
        catalog_item = _make_catalog_item(item_type=item_type)

        with patch.object(CatalogBibframeSync, "_sync_contributors", new=AsyncMock()), \
             patch.object(CatalogBibframeSync, "_sync_subjects", new=AsyncMock()):
            result = await CatalogBibframeSync.create_from_catalog(db, catalog_item)

        assert result is not None, f"sync swallowed an error for ItemType.{item_type.name}"
        assert isinstance(result, BibframeItem)

    @pytest.mark.asyncio
    async def test_populates_correct_item_columns(self):
        db = _mock_db_session()
        catalog_item = _make_catalog_item(call_number="FIC SMI", location="NEW-01")

        with patch.object(CatalogBibframeSync, "_sync_contributors", new=AsyncMock()), \
             patch.object(CatalogBibframeSync, "_sync_subjects", new=AsyncMock()):
            result = await CatalogBibframeSync.create_from_catalog(db, catalog_item)

        assert result.call_number == "FIC SMI"
        assert result.shelving_location == "NEW-01"
        assert result.library_branch == "Main"
        assert result.circulation_status == "available"
        assert result.barcode == "BC-42"

    @pytest.mark.asyncio
    async def test_writes_isbn_to_isbn_13_field_and_description_to_work_summary(self):
        db = _mock_db_session()
        catalog_item = _make_catalog_item(
            isbn="9780062315007",
            description="The book's blurb",
        )
        added_works = []
        added_instances = []
        def capture(obj):
            if isinstance(obj, BibframeWork):
                added_works.append(obj)
            elif isinstance(obj, BibframeInstance):
                added_instances.append(obj)
        db.add.side_effect = capture

        with patch.object(CatalogBibframeSync, "_sync_contributors", new=AsyncMock()), \
             patch.object(CatalogBibframeSync, "_sync_subjects", new=AsyncMock()):
            await CatalogBibframeSync.create_from_catalog(db, catalog_item)

        assert len(added_instances) == 1
        assert added_instances[0].isbn_13 == "9780062315007"
        assert len(added_works) == 1
        assert added_works[0].summary == "The book's blurb"

    @pytest.mark.asyncio
    async def test_falls_back_to_main_when_location_missing(self):
        db = _mock_db_session()
        catalog_item = _make_catalog_item(location=None)

        with patch.object(CatalogBibframeSync, "_sync_contributors", new=AsyncMock()), \
             patch.object(CatalogBibframeSync, "_sync_subjects", new=AsyncMock()):
            result = await CatalogBibframeSync.create_from_catalog(db, catalog_item)

        assert result.shelving_location == "Main"


# ============================================================================
# Service-level — update_from_catalog
# ============================================================================


@pytest.mark.unit
class TestUpdateFromCatalog:
    @pytest.mark.asyncio
    async def test_mutates_correct_attributes_on_existing_item(self):
        existing_work = MagicMock(spec=BibframeWork)
        existing_instance = MagicMock(spec=BibframeInstance)
        existing_instance.work = existing_work
        existing_item = MagicMock(spec=BibframeItem)
        existing_item.instance = existing_instance

        db = AsyncMock()
        result_obj = MagicMock()
        result_obj.scalar_one_or_none = MagicMock(return_value=existing_item)
        db.execute = AsyncMock(return_value=result_obj)
        db.flush = AsyncMock()

        catalog_item = _make_catalog_item(
            call_number="900 NEW",
            location="RES-02",
            description="Updated blurb",
        )

        result = await CatalogBibframeSync.update_from_catalog(db, catalog_item)

        assert result is existing_item
        assert existing_item.call_number == "900 NEW"
        assert existing_item.shelving_location == "RES-02"
        assert existing_item.circulation_status == "available"
        assert existing_instance.isbn_13 == "9780123456789"
        assert existing_work.summary == "Updated blurb"


# ---------------------------------------------------------------------------
# _split_isbn helper tests
# ---------------------------------------------------------------------------

class TestIsbnRouting:
    def test_thirteen_digit_isbn_routes_to_isbn_13(self):
        assert _split_isbn("9780062315007") == (None, "9780062315007")

    def test_ten_digit_numeric_isbn_routes_to_isbn_10(self):
        assert _split_isbn("0062315005") == ("0062315005", None)

    def test_ten_digit_isbn_with_x_check_digit(self):
        assert _split_isbn("006231500X") == ("006231500X", None)

    def test_ten_digit_isbn_lowercase_x_is_normalized(self):
        # Lowercase 'x' should still be accepted and normalized to uppercase.
        assert _split_isbn("006231500x") == ("006231500X", None)

    def test_hyphenated_isbn_13_is_normalized(self):
        assert _split_isbn("978-0-06-231500-7") == (None, "9780062315007")

    def test_hyphenated_isbn_10_is_normalized(self):
        assert _split_isbn("0-06-231500-5") == ("0062315005", None)

    def test_spaces_are_stripped(self):
        assert _split_isbn("  978 0062315007 ") == (None, "9780062315007")

    def test_none_returns_both_none(self):
        assert _split_isbn(None) == (None, None)

    def test_empty_string_returns_both_none(self):
        assert _split_isbn("") == (None, None)

    def test_whitespace_only_returns_both_none(self):
        assert _split_isbn("   ") == (None, None)

    def test_junk_string_returns_both_none(self):
        assert _split_isbn("not-an-isbn") == (None, None)

    def test_wrong_length_returns_both_none(self):
        # 12 digits is neither 10 nor 13.
        assert _split_isbn("123456789012") == (None, None)

    def test_ten_chars_with_letter_other_than_x_returns_both_none(self):
        # Only 'X' is allowed as a non-digit, and only in the check position.
        assert _split_isbn("00623150A5") == (None, None)

    def test_thirteen_chars_with_letters_returns_both_none(self):
        # ISBN-13 must be all digits.
        assert _split_isbn("978006231500X") == (None, None)


# ---------------------------------------------------------------------------
# create_from_catalog integration with helper
# ---------------------------------------------------------------------------

# NOTE: An end-to-end create_from_catalog integration test would normally live
# here ("10-digit ISBN -> BibframeInstance.isbn_10 populated"), but on
# origin/main the service crashes before reaching the ISBN assignment due to
# two latent bugs (invalid ItemType members referenced in the type-map dicts,
# and a `language=` kwarg passed to BibframeInstance which has no such column).
# Both are fixed in PR #244. The end-to-end ISBN-routing assertion will be
# added there once the broader sync flow is repairable in tests.
