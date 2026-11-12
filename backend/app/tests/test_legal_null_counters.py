# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test: legal view/download/helpful counters must tolerate NULL.

The legal increment helpers did `obj.counter += 1`; seeded legal_topics/forms/
guides rows have NULL counters, so GET /legal/topics/{id} and /forms/{id} (and
the form-download / guide-helpful POSTs) 500'd with
`TypeError: unsupported operand += 'NoneType' and 'int'`. The helpers now use
`(counter or 0) + 1`, matching the policy_service siblings. These endpoints are
anonymous (no auth), so only get_db is overridden.
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.core.database import get_db
from app.main import app


@pytest.fixture
def _override_db(db):
    async def _db():
        yield db

    app.dependency_overrides[get_db] = _db
    app.state.setup_complete = True
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
async def null_topic(db):
    tid = (await db.execute(text(
        "INSERT INTO legal_topics (name, slug, is_active, is_featured, display_order, view_count) "
        "VALUES ('Tenant Rights', 'tenant-rights', true, false, 0, NULL) RETURNING id"
    ))).scalar_one()
    await db.commit()
    return tid


@pytest.fixture
async def null_form(db):
    fid = (await db.execute(text(
        "INSERT INTO legal_forms (title, jurisdiction, status, view_count, download_count) "
        "VALUES ('Eviction Answer', 'Ohio', 'active', NULL, NULL) RETURNING id"
    ))).scalar_one()
    await db.commit()
    return fid


@pytest.fixture
async def form_null_bools(db):
    """download_count present (required int), but the accessibility bool columns
    NULL — exercises the LegalFormResponse None->default coercion."""
    fid = (await db.execute(text(
        "INSERT INTO legal_forms (title, jurisdiction, status, download_count, view_count, "
        " screen_reader_friendly, large_print_available) "
        "VALUES ('Fee Waiver', 'Ohio', 'active', 0, 0, NULL, NULL) RETURNING id"
    ))).scalar_one()
    await db.commit()
    return fid


@pytest.fixture
async def null_guide(db):
    gid = (await db.execute(text(
        "INSERT INTO legal_guides (title, slug, reading_level, is_published, helpful_count, not_helpful_count) "
        "VALUES ('Small Claims 101', 'small-claims-101', 'high_school', true, NULL, NULL) RETURNING id"
    ))).scalar_one()
    await db.commit()
    return gid


@pytest.mark.asyncio
async def test_get_topic_with_null_view_count(_override_db, null_topic):
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        resp = await ac.get(f"/api/v1/legal/topics/{null_topic}")
    assert resp.status_code == 200, resp.text
    assert resp.json()["view_count"] == 1


@pytest.mark.asyncio
async def test_get_form_with_null_bool_fields(_override_db, form_null_bools):
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        resp = await ac.get(f"/api/v1/legal/forms/{form_null_bools}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["screen_reader_friendly"] is False
    assert body["large_print_available"] is False
    assert body["languages_available"] == ["English"]


@pytest.mark.asyncio
async def test_form_download_with_null_download_count(_override_db, null_form):
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        resp = await ac.post(f"/api/v1/legal/forms/{null_form}/download")
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_guide_helpful_with_null_helpful_count(_override_db, null_guide):
    from httpx import AsyncClient, ASGITransport

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://localhost") as ac:
        resp = await ac.post(f"/api/v1/legal/guides/{null_guide}/helpful?was_helpful=true")
    assert resp.status_code == 200, resp.text
