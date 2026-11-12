# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for work relationships and cross-format linking.

Tests all cross-format linking scenarios:
- Manga linked to anime DVD adaptation
- Light novel linked to manga adaptation
- "If you liked the anime, read the manga" suggestions
- Soundtrack CDs linked to series
- Art books linked to main series
- Film novelizations linked to movies
- Cross-format discovery in search results
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bibframe import BibframeWork, WorkType
from app.models.work_relationships import (
    WorkRelationship, RelationshipType, RelationshipDirection,
    FormatSuggestion, CrossFormatDiscovery
)
from app.services.work_relationship_service import WorkRelationshipService


@pytest.mark.asyncio
class TestMangaToAnimeAdaptation:
    """Test manga linked to anime DVD adaptation."""

    async def test_create_manga_to_anime_relationship(
        self, db: AsyncSession
    ):
        """Test creating a manga-to-anime relationship."""
        # Create manga work
        manga = BibframeWork(
            title="Attack on Titan Manga",
            work_type=WorkType.text,
            source="local",
            language="eng"
        )
        db.add(manga)

        # Create anime work
        anime = BibframeWork(
            title="Attack on Titan Anime",
            work_type=WorkType.two_dimensional_moving_image,
            source="local",
            language="eng"
        )
        db.add(anime)
        await db.flush()

        # Create relationship
        relationship = await WorkRelationshipService.create_relationship(
            db,
            source_work_id=manga.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime,
            title="Attack on Titan: Anime Adaptation",
            description="Professional anime adaptation of the manga series",
            is_official=True,
            adaptation_fidelity="faithful"
        )

        await db.commit()

        # Verify
        assert relationship.source_work_id == manga.id
        assert relationship.target_work_id == anime.id
        assert relationship.relationship_type == RelationshipType.manga_to_anime
        assert relationship.is_official is True

    async def test_find_anime_from_manga(
        self, db: AsyncSession
    ):
        """Test finding anime adaptation from manga work."""
        # Setup
        manga = BibframeWork(title="Manga", work_type=WorkType.text)
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db.add(manga)
        db.add(anime)
        await db.flush()

        _ = await WorkRelationshipService.create_relationship(
            db,
            source_work_id=manga.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime
        )
        await db.flush()

        # Find related works
        related = await WorkRelationshipService.find_related_works(
            db, manga.id, [RelationshipType.manga_to_anime]
        )

        # Verify
        assert len(related) == 1
        assert related[0]["target_work_id"] == anime.id
        assert related[0]["relationship_type"] == RelationshipType.manga_to_anime


@pytest.mark.asyncio
class TestLightNovelToMangaAdaptation:
    """Test light novel linked to manga adaptation."""

    async def test_create_light_novel_to_manga_relationship(
        self, db: AsyncSession
    ):
        """Test creating a light novel-to-manga relationship."""
        # Create light novel work
        light_novel = BibframeWork(
            title="That Time I Got Reincarnated as a Slime - Light Novel",
            work_type=WorkType.text,
            language="eng"
        )
        db.add(light_novel)

        # Create manga work
        manga = BibframeWork(
            title="That Time I Got Reincarnated as a Slime - Manga",
            work_type=WorkType.still_image,
            language="eng"
        )
        db.add(manga)
        await db.flush()

        # Create relationship
        relationship = await WorkRelationshipService.create_relationship(
            db,
            source_work_id=light_novel.id,
            target_work_id=manga.id,
            relationship_type=RelationshipType.light_novel_to_manga,
            title="Manga Adaptation",
            adaptation_fidelity="loose"
        )
        await db.flush()

        # Verify
        assert relationship.relationship_type == RelationshipType.light_novel_to_manga

    async def test_find_all_formats_of_series(
        self, db: AsyncSession
    ):
        """Test finding all available formats of a series."""
        # Create multiple formats of same series
        light_novel = BibframeWork(
            title="Series - Light Novel",
            work_type=WorkType.text
        )
        manga = BibframeWork(
            title="Series - Manga",
            work_type=WorkType.still_image
        )
        anime = BibframeWork(
            title="Series - Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db.add_all([light_novel, manga, anime])
        await db.flush()

        # Create relationships
        await WorkRelationshipService.create_relationship(
            db, light_novel.id, manga.id,
            RelationshipType.light_novel_to_manga
        )
        await WorkRelationshipService.create_relationship(
            db, manga.id, anime.id,
            RelationshipType.manga_to_anime
        )
        await db.flush()

        # Get all formats
        formats = await WorkRelationshipService.get_all_formats(db, light_novel.id)

        # Verify - should find manga
        assert RelationshipType.light_novel_to_manga in formats
        assert len(formats[RelationshipType.light_novel_to_manga]) == 1


@pytest.mark.asyncio
class TestFormatSuggestions:
    """Test 'If you liked X, try Y' format suggestions."""

    async def test_create_format_suggestion(self, db: AsyncSession):
        """Test creating a format suggestion."""
        anime = BibframeWork(
            title="Anime Series",
            work_type=WorkType.two_dimensional_moving_image
        )
        manga = BibframeWork(
            title="Manga Series",
            work_type=WorkType.still_image
        )
        db.add_all([anime, manga])
        await db.flush()

        # Create suggestion
        suggestion = await WorkRelationshipService.create_format_suggestion(
            db,
            source_work_id=anime.id,
            target_work_id=manga.id,
            suggestion_text="If you liked the anime, read the manga!",
            confidence_score=85,
            is_global=True
        )
        await db.flush()

        # Verify
        assert suggestion.suggestion_text == "If you liked the anime, read the manga!"
        assert suggestion.confidence_score == 85
        assert suggestion.is_global is True

    async def test_get_suggestions_for_work(self, db: AsyncSession):
        """Test retrieving suggestions for a work."""
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        manga1 = BibframeWork(
            title="Manga 1",
            work_type=WorkType.still_image
        )
        manga2 = BibframeWork(
            title="Manga 2",
            work_type=WorkType.still_image
        )
        db.add_all([anime, manga1, manga2])
        await db.flush()

        # Create multiple suggestions
        await WorkRelationshipService.create_format_suggestion(
            db, anime.id, manga1.id,
            "If you liked the anime, read this manga!",
            confidence_score=90
        )
        await WorkRelationshipService.create_format_suggestion(
            db, anime.id, manga2.id,
            "If you liked the anime, also read this manga!",
            confidence_score=75
        )
        await db.flush()

        # Get suggestions
        suggestions = await WorkRelationshipService.get_suggestions_for_work(
            db, anime.id
        )

        # Verify - should be sorted by confidence score
        assert len(suggestions) == 2
        assert suggestions[0].confidence_score >= suggestions[1].confidence_score


@pytest.mark.asyncio
class TestSoundtrackCDLinkedToSeries:
    """Test soundtrack CDs linked to series."""

    async def test_link_soundtrack_to_series(self, db: AsyncSession):
        """Test linking soundtrack CD to series."""
        # Create series work
        series = BibframeWork(
            title="Attack on Titan Series",
            work_type=WorkType.two_dimensional_moving_image
        )
        db.add(series)

        # Create soundtrack work
        soundtrack = BibframeWork(
            title="Attack on Titan: Original Soundtrack",
            work_type=WorkType.performed_music
        )
        db.add(soundtrack)
        await db.flush()

        # Link soundtrack to series
        relationship = await WorkRelationshipService.create_relationship(
            db,
            source_work_id=series.id,
            target_work_id=soundtrack.id,
            relationship_type=RelationshipType.series_soundtrack,
            title="Official Series Soundtrack"
        )
        await db.flush()

        # Verify
        assert relationship.relationship_type == RelationshipType.series_soundtrack

    async def test_find_soundtracks_for_series(self, db: AsyncSession):
        """Test finding all soundtracks for a series."""
        series = BibframeWork(
            title="Series",
            work_type=WorkType.two_dimensional_moving_image
        )
        soundtrack1 = BibframeWork(
            title="Soundtrack 1",
            work_type=WorkType.performed_music
        )
        soundtrack2 = BibframeWork(
            title="Soundtrack 2",
            work_type=WorkType.performed_music
        )
        db.add_all([series, soundtrack1, soundtrack2])
        await db.flush()

        # Create relationships
        await WorkRelationshipService.create_relationship(
            db, series.id, soundtrack1.id,
            RelationshipType.series_soundtrack
        )
        await WorkRelationshipService.create_relationship(
            db, series.id, soundtrack2.id,
            RelationshipType.series_soundtrack
        )
        await db.flush()

        # Find soundtracks
        soundtracks = await WorkRelationshipService.find_related_works(
            db, series.id, [RelationshipType.series_soundtrack]
        )

        # Verify
        assert len(soundtracks) == 2
        assert all(s["relationship_type"] == RelationshipType.series_soundtrack
                   for s in soundtracks)


@pytest.mark.asyncio
class TestArtbooksLinkedToSeries:
    """Test art books linked to main series."""

    async def test_link_artbook_to_series(self, db: AsyncSession):
        """Test linking art book to series."""
        series = BibframeWork(
            title="Series",
            work_type=WorkType.two_dimensional_moving_image
        )
        artbook = BibframeWork(
            title="Series Official Art Book",
            work_type=WorkType.still_image
        )
        db.add_all([series, artbook])
        await db.flush()

        relationship = await WorkRelationshipService.create_relationship(
            db, series.id, artbook.id,
            RelationshipType.series_artbook,
            title="Official Art Book"
        )
        await db.flush()

        assert relationship.relationship_type == RelationshipType.series_artbook


@pytest.mark.asyncio
class TestFilmNovelsLinkedToMovies:
    """Test film novelizations linked to movies."""

    async def test_link_novelization_to_film(self, db: AsyncSession):
        """Test linking novelization to film."""
        film = BibframeWork(
            title="Film Title",
            work_type=WorkType.three_dimensional_moving_image
        )
        novelization = BibframeWork(
            title="Film Title: The Novel",
            work_type=WorkType.text
        )
        db.add_all([film, novelization])
        await db.flush()

        relationship = await WorkRelationshipService.create_relationship(
            db,
            source_work_id=film.id,
            target_work_id=novelization.id,
            relationship_type=RelationshipType.film_to_novelization,
            direction=RelationshipDirection.forward
        )
        await db.flush()

        assert relationship.relationship_type == RelationshipType.film_to_novelization

    async def test_find_novelization_from_film(self, db: AsyncSession):
        """Test finding novelization from film."""
        film = BibframeWork(
            title="Film",
            work_type=WorkType.three_dimensional_moving_image
        )
        novelization = BibframeWork(
            title="Novelization",
            work_type=WorkType.text
        )
        db.add_all([film, novelization])
        await db.flush()

        await WorkRelationshipService.create_relationship(
            db, film.id, novelization.id,
            RelationshipType.film_to_novelization
        )
        await db.flush()

        # Find novelization
        related = await WorkRelationshipService.find_related_works(
            db, film.id, [RelationshipType.film_to_novelization]
        )

        assert len(related) == 1
        assert related[0]["target_work_id"] == novelization.id


@pytest.mark.asyncio
class TestCrossFormatDiscoveryCache:
    """Test cross-format discovery cache functionality."""

    async def test_update_discovery_cache(self, db: AsyncSession):
        """Test updating cross-format discovery cache."""
        # Create series with multiple formats
        primary = BibframeWork(title="Primary", work_type=WorkType.text)
        format2 = BibframeWork(title="Format 2", work_type=WorkType.still_image)
        format3 = BibframeWork(
            title="Format 3",
            work_type=WorkType.two_dimensional_moving_image
        )
        db.add_all([primary, format2, format3])
        await db.flush()

        # Create relationships
        await WorkRelationshipService.create_relationship(
            db, primary.id, format2.id,
            RelationshipType.light_novel_to_manga
        )
        await WorkRelationshipService.create_relationship(
            db, format2.id, format3.id,
            RelationshipType.manga_to_anime
        )
        await db.flush()

        # Update cache
        cache = await WorkRelationshipService.update_cross_format_discovery_cache(
            db, primary.id
        )

        # Verify cache
        assert cache.primary_work_id == primary.id
        assert "light_novel_to_manga" in cache.format_counts
        assert cache.series_name == "Primary"
        assert len(cache.related_work_ids) > 0

    async def test_search_discovery_by_series_name(self, db: AsyncSession):
        """Test searching discovery by series name."""
        # Create works and cache
        primary = BibframeWork(title="Attack on Titan", work_type=WorkType.text)
        anime = BibframeWork(
            title="Attack on Titan Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db.add_all([primary, anime])
        await db.flush()

        await WorkRelationshipService.create_relationship(
            db, primary.id, anime.id,
            RelationshipType.manga_to_anime
        )
        await db.flush()

        _ = await WorkRelationshipService.update_cross_format_discovery_cache(
            db, primary.id
        )
        await db.flush()

        # Search by series name
        found = await WorkRelationshipService.search_by_format(
            db, "Attack on Titan"
        )

        assert found is not None
        assert found.primary_work_id == primary.id


@pytest.mark.asyncio
class TestBidirectionalRelationships:
    """Test bidirectional relationship queries."""

    async def test_find_bidirectional_relationships(self, db: AsyncSession):
        """Test finding relationships in both directions."""
        work1 = BibframeWork(title="Work 1", work_type=WorkType.text)
        work2 = BibframeWork(title="Work 2", work_type=WorkType.still_image)
        work3 = BibframeWork(
            title="Work 3",
            work_type=WorkType.two_dimensional_moving_image
        )
        db.add_all([work1, work2, work3])
        await db.flush()

        # Create relationships
        # work1 -> work2 (light novel to manga)
        await WorkRelationshipService.create_relationship(
            db, work1.id, work2.id,
            RelationshipType.light_novel_to_manga
        )
        # work3 -> work2 (manga derived from work3)
        await WorkRelationshipService.create_relationship(
            db, work3.id, work2.id,
            RelationshipType.spin_off
        )
        await db.flush()

        # Query work2 - should see relationships in both directions
        related = await WorkRelationshipService.find_related_works_bidirectional(
            db, work2.id
        )

        # work2 is target in both relationships, so should appear in as_target
        assert len(related["as_target"]) == 2
        assert len(related["as_source"]) == 0
