# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoint tests for work relationships.

Tests REST API endpoints for:
- Creating work relationships
- Retrieving related works
- Getting format suggestions
- Cross-format discovery
"""

import pytest
from httpx import AsyncClient

from app.models.bibframe import BibframeWork, WorkType
from app.models.work_relationships import RelationshipType


@pytest.fixture
def staff_token(test_staff):
    from app.core.security import create_access_token

    return create_access_token(subject=test_staff.id, email=test_staff.email)


@pytest.fixture
def user_token(test_patron):
    from app.core.security import create_access_token

    return create_access_token(subject=test_patron.id, email=test_patron.email)


@pytest.mark.asyncio
class TestWorkRelationshipsAPI:
    """Test work relationship API endpoints."""

    async def test_create_relationship_endpoint(
        self, client: AsyncClient, staff_token: str, db_session
    ):
        """Test POST /work-relationships endpoint."""
        # Create test works
        manga = BibframeWork(
            title="Manga",
            work_type=WorkType.text
        )
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db_session.add(manga)
        db_session.add(anime)
        await db_session.flush()

        # Create relationship via API
        response = await client.post(
            # Trailing slash matches the route (@router.post("/")); httpx
            # doesn't follow redirects by default, so the bare path would
            # get a 307 instead of the real response.
            "/api/v1/work-relationships/",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={
                "source_work_id": manga.id,
                "target_work_id": anime.id,
                "relationship_type": "manga_to_anime",
                "title": "Anime Adaptation",
                "is_official": True
            }
        )

        # Verify
        assert response.status_code == 201
        data = response.json()
        assert data["relationship_type"] == "manga_to_anime"
        assert data["is_official"] is True

    async def test_get_relationship_endpoint(
        self, client: AsyncClient, db_session
    ):
        """Test GET /work-relationships/{id} endpoint."""
        # Create test relationship
        manga = BibframeWork(title="Manga", work_type=WorkType.text)
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db_session.add(manga)
        db_session.add(anime)
        await db_session.flush()

        from app.models.work_relationships import WorkRelationship
        rel = WorkRelationship(
            source_work_id=manga.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime
        )
        db_session.add(rel)
        await db_session.flush()

        # Get via API
        response = await client.get(
            f"/api/v1/work-relationships/{rel.id}"
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == rel.id
        assert data["relationship_type"] == "manga_to_anime"

    async def test_get_related_works_endpoint(
        self, client: AsyncClient, db_session
    ):
        """Test GET /work-relationships/work/{id}/related endpoint."""
        # Create test data
        manga = BibframeWork(title="Manga", work_type=WorkType.text)
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db_session.add(manga)
        db_session.add(anime)
        await db_session.flush()

        from app.models.work_relationships import WorkRelationship
        rel = WorkRelationship(
            source_work_id=manga.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime
        )
        db_session.add(rel)
        await db_session.flush()

        # Get related works via API
        response = await client.get(
            f"/api/v1/work-relationships/work/{manga.id}/related"
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["work_id"] == manga.id
        assert len(data["related_as_source"]) == 1
        assert data["related_as_source"][0]["work_id"] == anime.id

    async def test_get_all_formats_endpoint(
        self, client: AsyncClient, db_session
    ):
        """Test GET /work-relationships/work/{id}/all-formats endpoint."""
        # Create test series with multiple formats
        light_novel = BibframeWork(
            title="Light Novel",
            work_type=WorkType.text
        )
        manga = BibframeWork(
            title="Manga",
            work_type=WorkType.still_image
        )
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db_session.add_all([light_novel, manga, anime])
        await db_session.flush()

        from app.models.work_relationships import WorkRelationship
        rel1 = WorkRelationship(
            source_work_id=light_novel.id,
            target_work_id=manga.id,
            relationship_type=RelationshipType.light_novel_to_manga
        )
        rel2 = WorkRelationship(
            source_work_id=manga.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime
        )
        db_session.add(rel1)
        db_session.add(rel2)
        await db_session.flush()

        # Get all formats via API
        response = await client.get(
            f"/api/v1/work-relationships/work/{light_novel.id}/all-formats"
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert "formats" in data
        assert "light_novel_to_manga" in data["formats"]

    async def test_create_suggestion_endpoint(
        self, client: AsyncClient, staff_token: str, db_session
    ):
        """Test POST /work-relationships/suggestions endpoint."""
        # Create test works
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        manga = BibframeWork(title="Manga", work_type=WorkType.still_image)
        db_session.add(anime)
        db_session.add(manga)
        await db_session.flush()

        # Create suggestion via API
        response = await client.post(
            "/api/v1/work-relationships/suggestions",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={
                "source_work_id": anime.id,
                "target_work_id": manga.id,
                "suggestion_text": "If you liked the anime, read the manga!",
                "confidence_score": 90
            }
        )

        # Verify
        assert response.status_code == 201
        data = response.json()
        assert "If you liked" in data["suggestion_text"]
        assert data["confidence_score"] == 90

    async def test_get_suggestions_endpoint(
        self, client: AsyncClient, db_session
    ):
        """Test GET /work-relationships/work/{id}/suggestions endpoint."""
        # Create test data
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        manga = BibframeWork(title="Manga", work_type=WorkType.still_image)
        db_session.add(anime)
        db_session.add(manga)
        await db_session.flush()

        from app.models.work_relationships import FormatSuggestion
        suggestion = FormatSuggestion(
            source_work_id=anime.id,
            target_work_id=manga.id,
            suggestion_text="If you liked the anime, read the manga!",
            confidence_score=90,
            is_global=True
        )
        db_session.add(suggestion)
        await db_session.flush()

        # Get suggestions via API
        response = await client.get(
            f"/api/v1/work-relationships/work/{anime.id}/suggestions"
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["suggestion_text"] == "If you liked the anime, read the manga!"

    async def test_discovery_endpoint(
        self, client: AsyncClient, db_session
    ):
        """Test GET /work-relationships/discovery/{series_name} endpoint."""
        # Create test series with cache
        primary = BibframeWork(
            title="Attack on Titan",
            work_type=WorkType.text
        )
        anime = BibframeWork(
            title="Attack on Titan Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db_session.add(primary)
        db_session.add(anime)
        await db_session.flush()

        from app.models.work_relationships import WorkRelationship, CrossFormatDiscovery
        rel = WorkRelationship(
            source_work_id=primary.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime
        )
        db_session.add(rel)
        await db_session.flush()

        cache = CrossFormatDiscovery(
            primary_work_id=primary.id,
            series_name="Attack on Titan",
            series_slug="attack-on-titan",
            format_counts={"manga_to_anime": 1},
            available_formats=["manga_to_anime"],
            related_work_ids=[anime.id],
            relationship_types={"manga_to_anime": [anime.id]}
        )
        db_session.add(cache)
        await db_session.flush()

        # Search via API
        response = await client.get(
            "/api/v1/work-relationships/discovery/Attack on Titan"
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["series_name"] == "Attack on Titan"
        assert "format_counts" in data

    async def test_update_relationship_endpoint(
        self, client: AsyncClient, staff_token: str, db_session
    ):
        """Test PUT /work-relationships/{id} endpoint."""
        # Create test relationship
        manga = BibframeWork(title="Manga", work_type=WorkType.text)
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db_session.add(manga)
        db_session.add(anime)
        await db_session.flush()

        from app.models.work_relationships import WorkRelationship
        rel = WorkRelationship(
            source_work_id=manga.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime,
            is_official=False
        )
        db_session.add(rel)
        await db_session.flush()

        # Update via API
        response = await client.put(
            f"/api/v1/work-relationships/{rel.id}",
            headers={"Authorization": f"Bearer {staff_token}"},
            json={"is_official": True, "verified": True}
        )

        # Verify
        assert response.status_code == 200
        data = response.json()
        assert data["is_official"] is True
        assert data["verified"] is True

    async def test_delete_relationship_endpoint(
        self, client: AsyncClient, staff_token: str, db_session
    ):
        """Test DELETE /work-relationships/{id} endpoint."""
        # Create test relationship
        manga = BibframeWork(title="Manga", work_type=WorkType.text)
        anime = BibframeWork(
            title="Anime",
            work_type=WorkType.two_dimensional_moving_image
        )
        db_session.add(manga)
        db_session.add(anime)
        await db_session.flush()

        from app.models.work_relationships import WorkRelationship
        rel = WorkRelationship(
            source_work_id=manga.id,
            target_work_id=anime.id,
            relationship_type=RelationshipType.manga_to_anime
        )
        db_session.add(rel)
        await db_session.flush()

        # Delete via API
        response = await client.delete(
            f"/api/v1/work-relationships/{rel.id}",
            headers={"Authorization": f"Bearer {staff_token}"}
        )

        # Verify
        assert response.status_code == 204

    async def test_non_staff_cannot_create_relationship(
        self, client: AsyncClient, user_token: str
    ):
        """Test that non-staff users cannot create relationships."""
        response = await client.post(
            # Trailing slash matches the route (@router.post("/")); httpx
            # doesn't follow redirects by default, so the bare path would
            # get a 307 instead of the real response.
            "/api/v1/work-relationships/",
            headers={"Authorization": f"Bearer {user_token}"},
            json={
                "source_work_id": 1,
                "target_work_id": 2,
                "relationship_type": "manga_to_anime"
            }
        )

        # Verify
        assert response.status_code == 403
