# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the public Transparency Log endpoint.

GET /api/v1/book-challenges/public

Covers:
- Pagination metadata correctness.
- Year filter (year extracted from date_received).
- Outcome filter.
- Reason filter.
- Combined filters.
- Author suppression when public_title is set (anonymity policy).
- available_years on the stats endpoint.

Pattern: mock-at-route-boundary for the feature gate, real DB writes via
``test_db`` for the rows under test. Mirrors
``test_public_records_public.py``'s engine-pool reset fixture so each test
gets a fresh asyncpg pool tied to its own event loop.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book_challenge import (
    BookChallenge,
    ChallengeOutcome,
    ChallengeReason,
    ChallengeStatus,
)


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def _reset_test_engine_pool():
    """Workaround for asyncpg cross-event-loop pool errors in this file.

    Shared L30 test engine pool keeps PG connections alive across tests;
    each pytest-asyncio test gets a fresh event loop, but the pooled
    connection from the prior loop is invalid. Disposing forces a fresh
    pool.
    """
    yield
    import tests.conftest as tc
    if tc._engine is not None:
        try:
            await tc._engine.dispose()
        except Exception:
            pass
        tc._engine = None
        tc._session_factory = None


@pytest.fixture(autouse=True)
def _bypass_feature_gate():
    """The public endpoint guards on ``banned_books_tracking_enabled``.

    Mock the check at the route boundary so tests don't need to seed an
    organization_features row.
    """
    with patch(
        "app.api.v1.feature_guards.OrganizationFeaturesService.is_feature_enabled",
        new=AsyncMock(return_value=True),
    ):
        yield


PUBLIC_URL = "/api/v1/book-challenges/public"
STATS_URL = "/api/v1/book-challenges/public/stats"


def _make_challenge(
    *,
    title: str,
    year: int,
    outcome: ChallengeOutcome,
    reason: ChallengeReason,
    is_public: bool = True,
    author: str | None = "Some Author",
    public_title: str | None = None,
) -> BookChallenge:
    """Build (but do not persist) a BookChallenge row."""
    return BookChallenge(
        title=title,
        author=author,
        isbn=None,
        status=ChallengeStatus.RESOLVED_RETAINED,
        primary_reason=reason,
        outcome=outcome,
        date_received=datetime(year, 6, 1, tzinfo=timezone.utc),
        date_resolved=datetime(year, 7, 1, tzinfo=timezone.utc),
        is_public=is_public,
        public_title=public_title,
        public_summary="Public summary text.",
        lessons_learned=None,
    )


async def _seed(test_db: AsyncSession, rows: list[BookChallenge]) -> None:
    for row in rows:
        test_db.add(row)
    await test_db.commit()
    for row in rows:
        await test_db.refresh(row)


async def test_pagination_envelope_shape(
    client: AsyncClient, test_db: AsyncSession
):
    """Response is the paginated envelope, not a bare list."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title=f"Book {i}",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            )
            for i in range(3)
        ],
    )
    resp = await client.get(PUBLIC_URL)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body.keys()) >= {"items", "total", "page", "per_page", "pages"}
    assert isinstance(body["items"], list)
    assert body["total"] == 3
    assert body["page"] == 1
    assert body["pages"] == 1


async def test_pagination_metadata_with_multiple_pages(
    client: AsyncClient, test_db: AsyncSession
):
    """per_page=2 across 5 rows -> pages=3, page=2 returns 2 items."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title=f"Title {i}",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            )
            for i in range(5)
        ],
    )
    resp = await client.get(f"{PUBLIC_URL}?page=2&per_page=2")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 5
    assert body["page"] == 2
    assert body["per_page"] == 2
    assert body["pages"] == 3
    assert len(body["items"]) == 2


async def test_only_public_rows_returned(
    client: AsyncClient, test_db: AsyncSession
):
    """Rows with is_public=False are excluded from the public endpoint."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title="Visible",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
                is_public=True,
            ),
            _make_challenge(
                title="Hidden",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
                is_public=False,
            ),
        ],
    )
    resp = await client.get(PUBLIC_URL)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    titles = {item["title"] for item in body["items"]}
    assert "Hidden" not in titles


async def test_year_filter(client: AsyncClient, test_db: AsyncSession):
    """year=2023 returns only the 2023 row."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title="From 2022",
                year=2022,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            ),
            _make_challenge(
                title="From 2023",
                year=2023,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            ),
            _make_challenge(
                title="From 2024",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            ),
        ],
    )
    resp = await client.get(f"{PUBLIC_URL}?year=2023")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "From 2023"


async def test_outcome_filter(client: AsyncClient, test_db: AsyncSession):
    """outcome=removed returns only the REMOVED row."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title="Kept",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            ),
            _make_challenge(
                title="Pulled",
                year=2024,
                outcome=ChallengeOutcome.REMOVED,
                reason=ChallengeReason.LANGUAGE,
            ),
        ],
    )
    resp = await client.get(f"{PUBLIC_URL}?outcome=removed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Pulled"
    assert body["items"][0]["outcome"] == "removed"


async def test_reason_filter(client: AsyncClient, test_db: AsyncSession):
    """reason=lgbtq_content returns only that row."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title="Language one",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            ),
            _make_challenge(
                title="LGBTQ one",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LGBTQ_CONTENT,
            ),
        ],
    )
    resp = await client.get(f"{PUBLIC_URL}?reason=lgbtq_content")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "LGBTQ one"


async def test_combined_filters(client: AsyncClient, test_db: AsyncSession):
    """year + outcome + reason narrow correctly."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title="Match",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.VIOLENCE,
            ),
            _make_challenge(
                title="Wrong year",
                year=2023,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.VIOLENCE,
            ),
            _make_challenge(
                title="Wrong outcome",
                year=2024,
                outcome=ChallengeOutcome.REMOVED,
                reason=ChallengeReason.VIOLENCE,
            ),
            _make_challenge(
                title="Wrong reason",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
            ),
        ],
    )
    resp = await client.get(
        f"{PUBLIC_URL}?year=2024&outcome=retained&reason=violence"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["title"] == "Match"


async def test_author_suppressed_when_public_title_set(
    client: AsyncClient, test_db: AsyncSession
):
    """Anonymity policy: rows with public_title set return author=null.

    A patron should not be able to Google the author + outcome and
    identify the title in seconds when the library has chosen a public
    alias instead of the real title.
    """
    await _seed(
        test_db,
        [
            _make_challenge(
                title="Real Internal Title",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
                author="Famous Author",
                public_title="YA Nonfiction Challenge -- Retained",
            ),
            _make_challenge(
                title="Always Public Title",
                year=2024,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
                author="Other Author",
                public_title=None,
            ),
        ],
    )
    resp = await client.get(f"{PUBLIC_URL}?per_page=10")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2

    by_title = {item.get("public_title") or item["title"]: item for item in body["items"]}
    suppressed = by_title["YA Nonfiction Challenge -- Retained"]
    assert suppressed["author"] is None, (
        "Author must be suppressed when public_title is set"
    )
    visible = by_title["Always Public Title"]
    assert visible["author"] == "Other Author"


async def test_stats_includes_available_years(
    client: AsyncClient, test_db: AsyncSession
):
    """Stats expose distinct years that have at least one public row."""
    await _seed(
        test_db,
        [
            _make_challenge(
                title=f"{year}",
                year=year,
                outcome=ChallengeOutcome.RETAINED,
                reason=ChallengeReason.LANGUAGE,
                is_public=year != 2021,  # 2021 row exists but is non-public
            )
            for year in (2021, 2022, 2023, 2024, 2024)  # duplicate 2024
        ],
    )
    resp = await client.get(STATS_URL)
    assert resp.status_code == 200
    body = resp.json()
    assert "available_years" in body
    years = body["available_years"]
    # Only public years, distinct, sorted desc.
    assert years == [2024, 2023, 2022]
