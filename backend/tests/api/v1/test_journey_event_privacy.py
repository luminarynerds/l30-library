# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for journey event ingest privacy scrubbing and retention.

Content-identifying keys (title, item_id, etc.) must never persist in
journey_instrumentation rows, and rows older than 90 days must be deleted.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.models.journey_instrumentation import JourneyEvent


def _event_payload(**overrides):
    payload = {
        "journey_type": "search_to_hold",
        "session_id": "sess_privacy_test",
        "stage_name": "item_selected",
        "event_sequence": 1,
        "time_since_journey_start_ms": 1200,
    }
    payload.update(overrides)
    return payload


class TestIngestScrubbing:
    """Content-identifying keys are stripped at the ingest boundary."""

    @pytest.mark.asyncio
    async def test_ingest_scrubs_content_identifying_keys(
        self, client: TestClient, db: AsyncSession
    ):
        response = await client.post(
            "/api/v1/analytics/journeys/events",
            json=_event_payload(
                properties={
                    "item_id": 42,
                    "title": "The Secret History",
                    "isbn": "9780140167771",
                    "author": "Donna Tartt",
                    "query": "dark academia",
                    "search_term": "dark academia",
                    "checkout_id": 7,
                    "patron_id": 3,
                    "results_count": 24,
                }
            ),
        )

        assert response.status_code == 202

        result = await db.execute(
            select(JourneyEvent).where(
                JourneyEvent.session_id == "sess_privacy_test"
            )
        )
        event = result.scalar_one()
        assert event.properties == {"results_count": 24}

    @pytest.mark.asyncio
    async def test_ingest_all_keys_scrubbed_stores_null(
        self, client: TestClient, db: AsyncSession
    ):
        response = await client.post(
            "/api/v1/analytics/journeys/events",
            json=_event_payload(
                session_id="sess_privacy_null",
                properties={"item_id": 42, "title": "The Secret History"},
            ),
        )

        assert response.status_code == 202

        result = await db.execute(
            select(JourneyEvent).where(
                JourneyEvent.session_id == "sess_privacy_null"
            )
        )
        event = result.scalar_one()
        assert event.properties is None

    @pytest.mark.asyncio
    async def test_batch_ingest_scrubs_content_identifying_keys(
        self, client: TestClient, db: AsyncSession
    ):
        response = await client.post(
            "/api/v1/analytics/journeys/events/batch",
            json={
                "events": [
                    _event_payload(
                        session_id="sess_privacy_batch",
                        stage_name="search_initiated",
                        properties={"query": "dark academia"},
                    ),
                    _event_payload(
                        session_id="sess_privacy_batch",
                        stage_name="results_displayed",
                        event_sequence=2,
                        properties={"results_count": 24, "title": "leaked"},
                    ),
                ]
            },
        )

        assert response.status_code == 202

        result = await db.execute(
            select(JourneyEvent)
            .where(JourneyEvent.session_id == "sess_privacy_batch")
            .order_by(JourneyEvent.event_sequence)
        )
        events = result.scalars().all()
        assert len(events) == 2
        assert events[0].properties is None
        assert events[1].properties == {"results_count": 24}


class TestJourneyEventRetention:
    """Journey events older than 90 days are deleted."""

    @pytest.mark.asyncio
    async def test_cleanup_deletes_only_old_events(self, db: AsyncSession):
        from app.services.data_retention_service import cleanup_old_journey_events

        now = datetime.now(timezone.utc)
        old_event = JourneyEvent(
            journey_type="search_to_hold",
            session_id="sess_old",
            event_sequence=1,
            stage_name="search_initiated",
            event_timestamp=now - timedelta(days=120),
            time_since_journey_start_ms=0,
        )
        recent_event = JourneyEvent(
            journey_type="search_to_hold",
            session_id="sess_recent",
            event_sequence=1,
            stage_name="search_initiated",
            event_timestamp=now - timedelta(days=5),
            time_since_journey_start_ms=0,
        )
        db.add_all([old_event, recent_event])
        await db.commit()

        deleted = await cleanup_old_journey_events(db)
        await db.commit()

        assert deleted == 1
        result = await db.execute(select(JourneyEvent.session_id))
        remaining = {row[0] for row in result.all()}
        assert "sess_old" not in remaining
        assert "sess_recent" in remaining


class TestScrubbingNormalization:
    """camelCase and hyphenated key variants are caught by normalization."""

    @pytest.mark.asyncio
    async def test_camelcase_keys_are_scrubbed(
        self, client: TestClient, db: AsyncSession
    ):
        response = await client.post(
            "/api/v1/analytics/journeys/events",
            json=_event_payload(
                session_id="sess_camel",
                properties={
                    "itemId": 42,
                    "patronId": 3,
                    "searchTerm": "dragons",
                    "checkoutId": 7,
                    "safe_key": "keep_me",
                },
            ),
        )

        assert response.status_code == 202

        result = await db.execute(
            select(JourneyEvent).where(JourneyEvent.session_id == "sess_camel")
        )
        event = result.scalar_one()
        assert event.properties == {"safe_key": "keep_me"}

    @pytest.mark.asyncio
    async def test_hyphenated_keys_are_scrubbed(
        self, client: TestClient, db: AsyncSession
    ):
        response = await client.post(
            "/api/v1/analytics/journeys/events",
            json=_event_payload(
                session_id="sess_hyphen",
                properties={
                    "patron-id": 5,
                    "item-id": 9,
                    "search-term": "mystery",
                    "results_count": 10,
                },
            ),
        )

        assert response.status_code == 202

        result = await db.execute(
            select(JourneyEvent).where(JourneyEvent.session_id == "sess_hyphen")
        )
        event = result.scalar_one()
        assert event.properties == {"results_count": 10}


class TestScrubbingNested:
    """Denylist keys inside nested dicts and lists-of-dicts are scrubbed recursively."""

    @pytest.mark.asyncio
    async def test_nested_dict_keys_scrubbed(
        self, client: TestClient, db: AsyncSession
    ):
        response = await client.post(
            "/api/v1/analytics/journeys/events",
            json=_event_payload(
                session_id="sess_nested_dict",
                properties={
                    "item": {
                        "item_id": 42,
                        "title": "Dune",
                        "shelf": "SF",
                    },
                    "stage": "selected",
                },
            ),
        )

        assert response.status_code == 202

        result = await db.execute(
            select(JourneyEvent).where(
                JourneyEvent.session_id == "sess_nested_dict"
            )
        )
        event = result.scalar_one()
        assert event.properties == {
            "item": {"shelf": "SF"},
            "stage": "selected",
        }

    @pytest.mark.asyncio
    async def test_list_of_dicts_keys_scrubbed(
        self, client: TestClient, db: AsyncSession
    ):
        response = await client.post(
            "/api/v1/analytics/journeys/events",
            json=_event_payload(
                session_id="sess_nested_list",
                properties={
                    "results": [
                        {"item_id": 1, "title": "A", "format": "book"},
                        {"item_id": 2, "title": "B", "format": "ebook"},
                    ],
                    "count": 2,
                },
            ),
        )

        assert response.status_code == 202

        result = await db.execute(
            select(JourneyEvent).where(
                JourneyEvent.session_id == "sess_nested_list"
            )
        )
        event = result.scalar_one()
        assert event.properties == {
            "results": [{"format": "book"}, {"format": "ebook"}],
            "count": 2,
        }
