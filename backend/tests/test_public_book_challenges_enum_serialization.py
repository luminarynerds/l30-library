# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for /book-challenges/public enum serialization.

The /public endpoint used to coerce SQLAlchemy enum columns with ``str()``,
which for a ``str, Enum`` subclass yields ``"ClassName.MEMBER"`` (e.g.
``"ChallengeReason.POLITICAL_VIEWPOINT"``) and leaks raw repr into the
public intellectual-freedom page. The frontend label maps key on lowercase
values, so the labels silently fell through to the raw repr.

These tests pin the serialization to ``.value`` (lowercase) on the SQLAlchemy
enum, matching the BanReport pattern in ``ban_tracker.py``.

We isolate from the Postgres conftest singleton-engine flake by stubbing
``BookChallengeService.list_public_challenges`` and the feature-flag router
dependency rather than rolling a full async-engine round trip.
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.v1 import book_challenges
from app.models.book_challenge import ChallengeOutcome, ChallengeReason


def _make_challenge_row(
    *,
    primary_reason: ChallengeReason,
    outcome: ChallengeOutcome,
    challenge_id: int = 1,
) -> SimpleNamespace:
    """Build an attribute-accessible row matching the SQLAlchemy shape the
    handler reads. Using ``SimpleNamespace`` avoids touching the ORM session
    and the conftest singleton-engine entirely.
    """
    return SimpleNamespace(
        id=challenge_id,
        catalog_item_id=None,
        public_title=None,
        title="Test Title",
        author="Test Author",
        primary_reason=primary_reason,
        outcome=outcome,
        public_summary=None,
        lessons_learned=None,
        date_received=datetime(2025, 1, 1, tzinfo=timezone.utc),
        date_resolved=None,
    )


@pytest.fixture
def app_with_router() -> FastAPI:
    """Minimal FastAPI app mounting only the book_challenges router.

    The router-level feature-flag dependency is overridden to a no-op so the
    handler runs without an OrganizationFeaturesService roundtrip. The
    handler's own DB dependency is overridden to a dummy object since the
    handler delegates all DB work to the service, which we mock.
    """
    from app.api.v1.feature_guards import require_banned_books_tracking_enabled
    from app.core.database import get_db

    app = FastAPI()
    app.include_router(book_challenges.router, prefix="/api/v1")

    async def _noop_flag():
        return True

    async def _stub_db():
        # The handler passes ``db`` straight to the (mocked) service.
        yield SimpleNamespace()

    app.dependency_overrides[require_banned_books_tracking_enabled] = _noop_flag
    app.dependency_overrides[get_db] = _stub_db
    return app


@pytest.mark.asyncio
async def test_public_list_emits_lowercase_enum_values(app_with_router: FastAPI):
    """Wire-format check: enum columns must serialize to their lowercase
    ``.value``, not ``"ChallengeReason.POLITICAL_VIEWPOINT"`` style repr.
    """
    rows = [
        _make_challenge_row(
            primary_reason=ChallengeReason.POLITICAL_VIEWPOINT,
            outcome=ChallengeOutcome.RETAINED,
            challenge_id=1,
        ),
        _make_challenge_row(
            primary_reason=ChallengeReason.LGBTQ_CONTENT,
            outcome=ChallengeOutcome.PENDING,
            challenge_id=2,
        ),
    ]

    with patch(
        "app.api.v1.book_challenges.BookChallengeService.list_public_challenges",
        new=AsyncMock(return_value=(rows, len(rows))),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_router), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/book-challenges/public?limit=10")

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert len(items) == 2

    # Primary regression guards: lowercase value, no class prefix.
    assert items[0]["primary_reason"] == "political_viewpoint"
    assert items[0]["outcome"] == "retained"
    assert items[1]["primary_reason"] == "lgbtq_content"
    assert items[1]["outcome"] == "pending"

    for item in items:
        assert "ChallengeReason." not in item["primary_reason"]
        assert "ChallengeOutcome." not in item["outcome"]
        # Lowercase invariant (matches frontend CHALLENGE_*_LABELS keys).
        assert item["primary_reason"] == item["primary_reason"].lower()
        assert item["outcome"] == item["outcome"].lower()


@pytest.mark.asyncio
async def test_public_list_handles_raw_string_enum_fallback(app_with_router: FastAPI):
    """Defense check: if the column round-trips as a raw string (some SQLEnum
    configs do this on read), the handler should still emit that string
    unchanged rather than blowing up on missing ``.value``.
    """
    rows = [
        SimpleNamespace(
            id=99,
            catalog_item_id=None,
            public_title=None,
            title="Raw String Title",
            author=None,
            # Simulate the raw-string-from-DB path: not an Enum instance.
            primary_reason="political_viewpoint",
            outcome="retained",
            public_summary=None,
            lessons_learned=None,
            date_received=datetime(2025, 1, 1, tzinfo=timezone.utc),
            date_resolved=None,
        ),
    ]

    with patch(
        "app.api.v1.book_challenges.BookChallengeService.list_public_challenges",
        new=AsyncMock(return_value=(rows, len(rows))),
    ):
        async with AsyncClient(
            transport=ASGITransport(app=app_with_router), base_url="http://test"
        ) as client:
            resp = await client.get("/api/v1/book-challenges/public?limit=10")

    assert resp.status_code == 200, resp.text
    items = resp.json()["items"]
    assert items[0]["primary_reason"] == "political_viewpoint"
    assert items[0]["outcome"] == "retained"
