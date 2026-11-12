# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for multi-volume / multi-part set support.

Covers:
- MultiPartSet creation
- CatalogItem ↔ MultiPartSet relationship and ordered sibling lookup
- Volume fields (volume_number, volume_label, sequence_in_set) persistence
- ItemCopy.volume_override persistence
- ON DELETE SET NULL on multipart_set_id
- Pydantic schema validation
"""
import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import CatalogItem, ItemType
from app.models.inventory import ItemCopy
from app.models.multipart import MultiPartSet, MultiPartSetType
from app.schemas.catalog import (
    CatalogItemCreate,
    MultiPartSetCreate,
    MultiPartSetUpdate,
)


class TestMultiPartSetModel:
    @pytest.mark.asyncio
    async def test_create_set(self, test_db: AsyncSession):
        s = MultiPartSet(
            title="The Decline and Fall of the Roman Empire",
            set_type=MultiPartSetType.multivolume,
            total_parts=6,
            publisher="Strahan & Cadell",
            editor="Edward Gibbon",
        )
        test_db.add(s)
        await test_db.commit()
        await test_db.refresh(s)

        assert s.id is not None
        assert s.set_type == MultiPartSetType.multivolume
        assert s.total_parts == 6

    @pytest.mark.asyncio
    async def test_total_parts_must_be_positive(self, test_db: AsyncSession):
        s = MultiPartSet(title="Invalid", total_parts=0)
        test_db.add(s)
        with pytest.raises(Exception):
            await test_db.commit()
        await test_db.rollback()


class TestCatalogItemVolumeFields:
    @pytest.mark.asyncio
    async def test_link_volumes_to_set(self, test_db: AsyncSession):
        s = MultiPartSet(
            title="Lord of the Rings",
            set_type=MultiPartSetType.multivolume,
            total_parts=3,
        )
        test_db.add(s)
        await test_db.flush()

        v3 = CatalogItem(
            title="The Return of the King",
            author="J.R.R. Tolkien",
            item_type=ItemType.book,
            multipart_set_id=s.id,
            volume_number="3",
            volume_label="Vol. 3: The Return of the King",
            sequence_in_set=3,
        )
        v1 = CatalogItem(
            title="The Fellowship of the Ring",
            author="J.R.R. Tolkien",
            item_type=ItemType.book,
            multipart_set_id=s.id,
            volume_number="1",
            volume_label="Vol. 1: The Fellowship of the Ring",
            sequence_in_set=1,
        )
        v2 = CatalogItem(
            title="The Two Towers",
            author="J.R.R. Tolkien",
            item_type=ItemType.book,
            multipart_set_id=s.id,
            volume_number="2",
            volume_label="Vol. 2: The Two Towers",
            sequence_in_set=2,
        )
        test_db.add_all([v3, v1, v2])
        await test_db.commit()

        result = await test_db.execute(
            select(MultiPartSet)
            .where(MultiPartSet.id == s.id)
            .options(selectinload(MultiPartSet.items))
        )
        loaded = result.scalar_one()
        sequences = [i.sequence_in_set for i in loaded.items]
        assert sequences == [1, 2, 3], "items must be ordered by sequence_in_set"
        assert loaded.items[0].volume_number == "1"
        assert loaded.items[2].title == "The Return of the King"

    @pytest.mark.asyncio
    async def test_non_integer_volume_number(self, test_db: AsyncSession):
        s = MultiPartSet(title="Encyclopedia", set_type=MultiPartSetType.numbered_set)
        test_db.add(s)
        await test_db.flush()

        item = CatalogItem(
            title="Encyclopedia, Supplement A",
            item_type=ItemType.book,
            multipart_set_id=s.id,
            volume_number="Suppl. A",
            sequence_in_set=27,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)
        assert item.volume_number == "Suppl. A"

    @pytest.mark.asyncio
    async def test_sequence_must_be_positive(self, test_db: AsyncSession):
        s = MultiPartSet(title="X")
        test_db.add(s)
        await test_db.flush()

        item = CatalogItem(
            title="Bad", item_type=ItemType.book,
            multipart_set_id=s.id, sequence_in_set=0,
        )
        test_db.add(item)
        with pytest.raises(Exception):
            await test_db.commit()
        await test_db.rollback()

    @pytest.mark.asyncio
    async def test_set_deletion_nulls_fk(self, test_db: AsyncSession):
        s = MultiPartSet(title="Temporary set")
        test_db.add(s)
        await test_db.flush()

        item = CatalogItem(
            title="Orphan-to-be",
            item_type=ItemType.book,
            multipart_set_id=s.id,
            volume_number="1",
            sequence_in_set=1,
        )
        test_db.add(item)
        await test_db.commit()

        await test_db.delete(s)
        await test_db.commit()

        await test_db.refresh(item)
        assert item.multipart_set_id is None
        assert item.volume_number == "1", "volume metadata survives set deletion"


class TestItemCopyVolumeOverride:
    @pytest.mark.asyncio
    async def test_omnibus_copy_override(self, test_db: AsyncSession):
        item = CatalogItem(
            title="Omnibus Edition",
            item_type=ItemType.book,
            volume_number="1",
        )
        test_db.add(item)
        await test_db.flush()

        copy = ItemCopy(
            catalog_item_id=item.id,
            barcode="OMNI-0001",
            copy_number=1,
            volume_override="1-3",
        )
        test_db.add(copy)
        await test_db.commit()
        await test_db.refresh(copy)
        assert copy.volume_override == "1-3"

    @pytest.mark.asyncio
    async def test_override_defaults_null(self, test_db: AsyncSession):
        item = CatalogItem(title="Plain", item_type=ItemType.book)
        test_db.add(item)
        await test_db.flush()

        copy = ItemCopy(
            catalog_item_id=item.id, barcode="PLAIN-0001", copy_number=1,
        )
        test_db.add(copy)
        await test_db.commit()
        await test_db.refresh(copy)
        assert copy.volume_override is None


class TestSchemas:
    def test_multipart_set_create_defaults(self):
        s = MultiPartSetCreate(title="A Set")
        assert s.set_type == MultiPartSetType.multivolume
        assert s.total_parts is None

    def test_multipart_set_total_parts_must_be_positive(self):
        with pytest.raises(ValidationError):
            MultiPartSetCreate(title="X", total_parts=0)

    def test_catalog_item_sequence_must_be_positive(self):
        with pytest.raises(ValidationError):
            CatalogItemCreate(title="X", sequence_in_set=0)

    def test_catalog_item_accepts_volume_fields(self):
        c = CatalogItemCreate(
            title="V1",
            multipart_set_id=42,
            volume_number="1A",
            volume_label="Vol. 1A",
            sequence_in_set=1,
        )
        assert c.volume_number == "1A"
        assert c.sequence_in_set == 1

    def test_multipart_set_update_partial(self):
        u = MultiPartSetUpdate(total_parts=12)
        assert u.title is None
        assert u.total_parts == 12


class TestMultiPartMARCExport:
    """MARC fields surfaced from MultiPartSet membership and volume metadata."""

    @pytest.mark.asyncio
    async def test_volume_number_emitted_in_245_n(self, test_db: AsyncSession):
        from app.services.catalog_marc_service import catalog_marc_service

        item = CatalogItem(
            title="The Two Towers",
            author="J.R.R. Tolkien",
            item_type=ItemType.book,
            volume_number="2",
            volume_label="The Two Towers",
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        record = catalog_marc_service.create_marc_record(item)
        f245 = record["245"]
        assert f245 is not None
        assert f245["n"] == "2"
        assert f245["p"] == "The Two Towers"

    @pytest.mark.asyncio
    async def test_set_emits_490_and_traced_830(self, test_db: AsyncSession):
        from app.services.catalog_marc_service import catalog_marc_service

        s = MultiPartSet(
            title="The Lord of the Rings",
            set_type=MultiPartSetType.multivolume,
            total_parts=3,
        )
        test_db.add(s)
        await test_db.flush()

        item = CatalogItem(
            title="The Fellowship of the Ring",
            author="J.R.R. Tolkien",
            item_type=ItemType.book,
            multipart_set_id=s.id,
            volume_number="1",
            sequence_in_set=1,
        )
        test_db.add(item)
        await test_db.commit()

        result = await test_db.execute(
            select(CatalogItem)
            .options(selectinload(CatalogItem.multipart_set))
            .where(CatalogItem.id == item.id)
        )
        loaded = result.scalar_one()

        record = catalog_marc_service.create_marc_record(loaded)

        f490 = record["490"]
        assert f490 is not None
        assert f490["a"] == "The Lord of the Rings"
        assert f490["v"] == "1"
        assert f490.indicators[0] == "1"  # traced

        f830 = record["830"]
        assert f830 is not None, "490 ind1=1 must be paired with an 830 added entry"
        assert f830["a"] == "The Lord of the Rings"
        assert f830["v"] == "1"

    @pytest.mark.asyncio
    async def test_no_set_falls_back_to_series_name(self, test_db: AsyncSession):
        from app.services.catalog_marc_service import catalog_marc_service

        item = CatalogItem(
            title="Standalone",
            author="Some Author",
            item_type=ItemType.book,
            series_name="Loose Series",
            series_number="3",
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        record = catalog_marc_service.create_marc_record(item)
        f490 = record["490"]
        assert f490 is not None
        assert f490["a"] == "Loose Series"
        assert f490["v"] == "3"
        assert record.get_fields("830") == []  # no traced entry without a set

    @pytest.mark.asyncio
    async def test_unloaded_relationship_does_not_crash(self, test_db: AsyncSession):
        """If a caller forgets to eager-load multipart_set, fall through cleanly."""
        from app.services.catalog_marc_service import catalog_marc_service

        s = MultiPartSet(title="Some Set", set_type=MultiPartSetType.multivolume)
        test_db.add(s)
        await test_db.flush()

        item = CatalogItem(
            title="V1",
            item_type=ItemType.book,
            multipart_set_id=s.id,
            volume_number="1",
            sequence_in_set=1,
        )
        test_db.add(item)
        await test_db.commit()

        # Re-fetch WITHOUT selectinload — relationship should be unloaded.
        result = await test_db.execute(
            select(CatalogItem).where(CatalogItem.id == item.id)
        )
        loaded = result.scalar_one()

        # Should not raise MissingGreenlet despite unloaded relationship.
        record = catalog_marc_service.create_marc_record(loaded)
        # 245 $n is still present (scalar field, no relationship needed).
        assert record["245"]["n"] == "1"
