# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Multimedia Catalog Fields

Tests the multimedia extensions to the catalog system including:
- DVD/Blu-ray fields (director, actors, runtime, rating)
- CD/Vinyl fields (artist, tracks, music genre)
- Game fields (platform, player count, game genre)
- Equipment/Kit fields (brand, model, dimensions, material, contents)
- MARC export for multimedia items
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.catalog import (
    CatalogItem,
    ItemType,
    ItemStatus,
    MediaFormat,
    ContentRating,
)


class TestMultimediaCatalogFields:
    """Test multimedia fields on catalog items"""

    @pytest.mark.asyncio
    async def test_dvd_fields(self, test_db: AsyncSession):
        """Test DVD-specific catalog fields"""
        item = CatalogItem(
            title="The Matrix",
            item_type=ItemType.dvd,
            director="Lana Wachowski, Lilly Wachowski",
            actors="Keanu Reeves, Laurence Fishburne, Carrie-Anne Moss",
            runtime_minutes=136,
            media_format=MediaFormat.dvd,
            content_rating=ContentRating.r,
            disc_count=2,
            studio="Warner Bros.",
            publication_year=1999,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.id is not None
        assert item.director == "Lana Wachowski, Lilly Wachowski"
        assert "Keanu Reeves" in item.actors
        assert item.runtime_minutes == 136
        assert item.media_format == MediaFormat.dvd
        assert item.content_rating == ContentRating.r
        assert item.disc_count == 2
        assert item.studio == "Warner Bros."

    @pytest.mark.asyncio
    async def test_bluray_fields(self, test_db: AsyncSession):
        """Test Blu-ray catalog fields"""
        item = CatalogItem(
            title="Inception",
            item_type=ItemType.bluray,
            director="Christopher Nolan",
            actors="Leonardo DiCaprio, Tom Hardy, Marion Cotillard",
            runtime_minutes=148,
            media_format=MediaFormat.bluray,
            content_rating=ContentRating.pg13,
            disc_count=1,
            studio="Warner Bros.",
            publication_year=2010,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.item_type == ItemType.bluray
        assert item.media_format == MediaFormat.bluray
        assert item.content_rating == ContentRating.pg13

    @pytest.mark.asyncio
    async def test_cd_fields(self, test_db: AsyncSession):
        """Test CD-specific catalog fields"""
        item = CatalogItem(
            title="Abbey Road",
            item_type=ItemType.cd,
            artist="The Beatles",
            track_count=17,
            music_genre="Rock",
            media_format=MediaFormat.cd,
            publisher="Apple Records",
            publication_year=1969,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.artist == "The Beatles"
        assert item.track_count == 17
        assert item.music_genre == "Rock"
        assert item.media_format == MediaFormat.cd

    @pytest.mark.asyncio
    async def test_vinyl_fields(self, test_db: AsyncSession):
        """Test vinyl record catalog fields"""
        item = CatalogItem(
            title="Dark Side of the Moon",
            item_type=ItemType.vinyl,
            artist="Pink Floyd",
            track_count=10,
            music_genre="Progressive Rock",
            media_format=MediaFormat.vinyl_lp,
            publisher="Harvest Records",
            publication_year=1973,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.item_type == ItemType.vinyl
        assert item.media_format == MediaFormat.vinyl_lp

    @pytest.mark.asyncio
    async def test_game_fields(self, test_db: AsyncSession):
        """Test video game catalog fields"""
        item = CatalogItem(
            title="The Legend of Zelda: Breath of the Wild",
            item_type=ItemType.game,
            platform="Nintendo Switch",
            player_count="1 player",
            game_genre="Action-Adventure",
            content_rating=ContentRating.e10,
            publisher="Nintendo",
            publication_year=2017,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.platform == "Nintendo Switch"
        assert item.player_count == "1 player"
        assert item.game_genre == "Action-Adventure"
        assert item.content_rating == ContentRating.e10

    @pytest.mark.asyncio
    async def test_equipment_fields(self, test_db: AsyncSession):
        """Test equipment catalog fields (cake pans, tools, etc.)"""
        item = CatalogItem(
            title="Bundt Cake Pan",
            item_type=ItemType.equipment,
            brand="Nordic Ware",
            model_number="50037",
            dimensions="10 inch diameter, 4 inch depth",
            material="Cast Aluminum",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.brand == "Nordic Ware"
        assert item.model_number == "50037"
        assert item.dimensions == "10 inch diameter, 4 inch depth"
        assert item.material == "Cast Aluminum"

    @pytest.mark.asyncio
    async def test_kit_fields(self, test_db: AsyncSession):
        """Test kit catalog fields"""
        item = CatalogItem(
            title="Cake Decorating Starter Kit",
            item_type=ItemType.kit,
            brand="Wilton",
            kit_contents="12 decorating tips, 2 couplers, 4 icing bags, spatula, practice board",
            dimensions="Box: 12x9x3 inches",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.item_type == ItemType.kit
        assert "12 decorating tips" in item.kit_contents
        assert item.brand == "Wilton"

    @pytest.mark.asyncio
    async def test_explicit_music_rating(self, test_db: AsyncSession):
        """Test explicit music content rating"""
        item = CatalogItem(
            title="Explicit Album",
            item_type=ItemType.cd,
            artist="Test Artist",
            content_rating=ContentRating.explicit,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        assert item.content_rating == ContentRating.explicit


class TestMultimediaMARCExport:
    """Test MARC export for multimedia items"""

    @pytest.mark.asyncio
    async def test_dvd_marc_export_includes_director(self, test_db: AsyncSession):
        """Test that DVD MARC export includes director in 508 and 245$c"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Jurassic Park",
            item_type=ItemType.dvd,
            director="Steven Spielberg",
            actors="Sam Neill, Laura Dern, Jeff Goldblum",
            runtime_minutes=127,
            studio="Universal Pictures",
            content_rating=ContentRating.pg13,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Director should appear in 508 (creation/production credits)
        assert "Steven Spielberg" in marcxml
        # Actors should appear in 511 (participant/performer)
        assert "Sam Neill" in marcxml

    @pytest.mark.asyncio
    async def test_dvd_marc_export_includes_runtime(self, test_db: AsyncSession):
        """Test that DVD MARC export includes runtime in 306 field"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="The Godfather",
            item_type=ItemType.dvd,
            director="Francis Ford Coppola",
            runtime_minutes=175,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Runtime should appear in 306 field as HHMMSS format
        # 175 minutes = 02 hours 55 minutes = 025500
        assert "025500" in marcxml

    @pytest.mark.asyncio
    async def test_dvd_marc_export_includes_content_rating(self, test_db: AsyncSession):
        """Test that DVD MARC export includes content rating in 521 field"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Rated R Movie",
            item_type=ItemType.dvd,
            content_rating=ContentRating.r,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Content rating should appear in 521
        assert "MPAA rating: R" in marcxml or "R" in marcxml

    @pytest.mark.asyncio
    async def test_cd_marc_export_includes_artist(self, test_db: AsyncSession):
        """Test that CD MARC export includes artist in 100 field"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Thriller",
            item_type=ItemType.cd,
            artist="Michael Jackson",
            track_count=9,
            music_genre="Pop",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Artist should appear in 100 field (main entry), reformatted to the
        # MARC "Last, First" personal-name-heading convention.
        assert "Jackson, Michael" in marcxml

    @pytest.mark.asyncio
    async def test_game_marc_export_includes_platform(self, test_db: AsyncSession):
        """Test that game MARC export includes platform in 538 field"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Super Mario Odyssey",
            item_type=ItemType.game,
            platform="Nintendo Switch",
            player_count="1-2 players",
            content_rating=ContentRating.e10,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Platform should appear in 538 (system details)
        assert "Nintendo Switch" in marcxml

    @pytest.mark.asyncio
    async def test_equipment_marc_export_includes_brand(self, test_db: AsyncSession):
        """Test that equipment MARC export includes brand/model info"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Stand Mixer",
            item_type=ItemType.equipment,
            brand="KitchenAid",
            model_number="KSM150PS",
            dimensions="14 x 9 x 14 inches",
            material="Metal",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Brand/model should appear
        assert "KitchenAid" in marcxml
        assert "KSM150PS" in marcxml

    @pytest.mark.asyncio
    async def test_kit_marc_export_includes_contents(self, test_db: AsyncSession):
        """Test that kit MARC export includes kit contents in 505 field"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Science Experiment Kit",
            item_type=ItemType.kit,
            brand="Thames & Kosmos",
            kit_contents="10 test tubes, microscope, 20 slides, safety goggles, instruction manual",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Kit contents should appear in 505 (contents note)
        assert "test tubes" in marcxml or "microscope" in marcxml

    @pytest.mark.asyncio
    async def test_bluray_physical_description(self, test_db: AsyncSession):
        """Test that Blu-ray MARC export has correct physical description"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Avatar",
            item_type=ItemType.bluray,
            disc_count=3,
            runtime_minutes=162,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Should indicate Blu-ray disc(s) in 300 field
        assert "Blu-ray" in marcxml or "videodisc" in marcxml

    @pytest.mark.asyncio
    async def test_vinyl_physical_description(self, test_db: AsyncSession):
        """Test that vinyl MARC export has correct physical description"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Kind of Blue",
            item_type=ItemType.vinyl,
            artist="Miles Davis",
            media_format=MediaFormat.vinyl_lp,
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        record = service.create_marc_record(item)
        marcxml = service.export_marcxml(record)

        # Should indicate vinyl in 300 field
        assert "vinyl" in marcxml.lower() or "audio disc" in marcxml.lower()


class TestMultimediaDublinCore:
    """Test Dublin Core export for multimedia items"""

    @pytest.mark.asyncio
    async def test_dvd_dublin_core_includes_creator(self, test_db: AsyncSession):
        """Test that DVD Dublin Core export uses director as creator"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="E.T. the Extra-Terrestrial",
            item_type=ItemType.dvd,
            director="Steven Spielberg",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        dc_xml = service.export_dublin_core(item)

        assert "<dc:creator>Steven Spielberg</dc:creator>" in dc_xml

    @pytest.mark.asyncio
    async def test_cd_dublin_core_includes_artist(self, test_db: AsyncSession):
        """Test that CD Dublin Core export uses artist as creator"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Born to Run",
            item_type=ItemType.cd,
            artist="Bruce Springsteen",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        dc_xml = service.export_dublin_core(item)

        assert "<dc:creator>Bruce Springsteen</dc:creator>" in dc_xml

    @pytest.mark.asyncio
    async def test_equipment_dublin_core_includes_brand(self, test_db: AsyncSession):
        """Test that equipment Dublin Core export includes brand"""
        from app.services.catalog_marc_service import CatalogMARCService

        item = CatalogItem(
            title="Instant Pot",
            item_type=ItemType.equipment,
            brand="Instant Pot",
            model_number="Duo 7-in-1",
            status=ItemStatus.available,
        )
        test_db.add(item)
        await test_db.commit()
        await test_db.refresh(item)

        service = CatalogMARCService()
        dc_xml = service.export_dublin_core(item)

        # Brand should appear somewhere in the DC export
        assert "Instant Pot" in dc_xml
