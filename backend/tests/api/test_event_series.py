# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for /events/series/{series_id} GET + register.

Conventions follow backend/tests/api/test_event_registration.py: HTTP path
tests are Postgres-only (the SQLite fallback round-trips datetimes naive,
which breaks the now()-vs-start_time comparison). Schema-level tests run
on either backend.
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.event import Event
from app.models.event_registration import EventRegistration


def _is_sqlite(db) -> bool:
    try:
        return db.bind.dialect.name == "sqlite"
    except Exception:
        return False


async def _create_series_event(
    test_db,
    *,
    series_id: str,
    series_name: str,
    days_out: int,
    max_attendees: int | None = None,
    registration_required: bool = True,
) -> Event:
    n = datetime.now(timezone.utc)
    if _is_sqlite(test_db):
        n = n.replace(tzinfo=None)
    start = n + timedelta(days=days_out)
    event = Event(
        title=f"{series_name} session",
        description=f"Session {days_out} days out",
        start_time=start,
        end_time=start + timedelta(hours=1),
        is_published=True,
        registration_required=registration_required,
        photos_will_be_taken=False,
        max_attendees=max_attendees,
        series_id=series_id,
        series_name=series_name,
        location="Main branch",
        category="education",
        audience="adults",
    )
    test_db.add(event)
    await test_db.commit()
    await test_db.refresh(event)
    return event


@pytest.mark.asyncio
async def test_get_series_returns_metadata_and_upcoming_ordered(
    test_db, client
):
    """GET /events/series/{series_id} returns 200 with occurrences ordered
    by start_time ascending and metadata derived from the next occurrence."""
    if _is_sqlite(test_db):
        pytest.skip("Series endpoint requires tz-aware datetimes; use Postgres.")

    sid = "tech-help-tuesday"
    # Insert out of order; endpoint should sort.
    await _create_series_event(test_db, series_id=sid, series_name="Tech Help Tuesday", days_out=14)
    await _create_series_event(test_db, series_id=sid, series_name="Tech Help Tuesday", days_out=7)
    await _create_series_event(test_db, series_id=sid, series_name="Tech Help Tuesday", days_out=21)

    resp = await client.get(f"/api/v1/events/series/{sid}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["series_id"] == sid
    assert body["series_name"] == "Tech Help Tuesday"
    assert body["upcoming_count"] == 3
    starts = [o["start_time"] for o in body["occurrences"]]
    assert starts == sorted(starts)


@pytest.mark.asyncio
async def test_get_series_404_for_missing_series(test_db, client):
    """Unknown series_id 404s, not 200-with-empty-occurrences."""
    if _is_sqlite(test_db):
        pytest.skip("Series endpoint requires tz-aware datetimes; use Postgres.")
    resp = await client.get("/api/v1/events/series/does-not-exist-xyz")
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_register_for_series_creates_one_row_per_occurrence(
    test_db, client, monkeypatch
):
    """POST /events/series/{series_id}/register creates one EventRegistration
    per upcoming occurrence."""
    if _is_sqlite(test_db):
        pytest.skip("Register endpoint requires tz-aware datetimes; use Postgres.")
    from app.api.v1 import event_series as series_module

    async def _fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(series_module, "verify_turnstile", _fake_verify)

    sid = "toddler-storytime"
    e1 = await _create_series_event(test_db, series_id=sid, series_name="Toddler Storytime", days_out=3)
    e2 = await _create_series_event(test_db, series_id=sid, series_name="Toddler Storytime", days_out=10)
    e3 = await _create_series_event(test_db, series_id=sid, series_name="Toddler Storytime", days_out=17)

    resp = await client.post(
        f"/api/v1/events/series/{sid}/register",
        json={
            "patron_name": "Series Patron",
            "patron_email": "series.patron@example.com",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["total_upcoming"] == 3
    assert body["registered_count"] == 3
    assert body["already_registered_count"] == 0
    assert {o["event_id"] for o in body["outcomes"]} == {e1.id, e2.id, e3.id}
    assert all(o["status"] == "registered" for o in body["outcomes"])


@pytest.mark.asyncio
async def test_register_for_series_is_idempotent(
    test_db, client, monkeypatch
):
    """Re-running register for the same series + email returns the same
    final state (no duplicate rows; each occurrence reports
    already_registered)."""
    if _is_sqlite(test_db):
        pytest.skip("Register endpoint requires tz-aware datetimes; use Postgres.")
    from app.api.v1 import event_series as series_module
    from sqlalchemy import func, select

    async def _fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(series_module, "verify_turnstile", _fake_verify)

    sid = "cookbook-club"
    await _create_series_event(test_db, series_id=sid, series_name="Cookbook Club", days_out=5)
    await _create_series_event(test_db, series_id=sid, series_name="Cookbook Club", days_out=35)

    payload = {
        "patron_name": "Cookbook Fan",
        "patron_email": "cookbook.fan@example.com",
    }
    first = await client.post(f"/api/v1/events/series/{sid}/register", json=payload)
    assert first.status_code == 201
    assert first.json()["registered_count"] == 2

    second = await client.post(f"/api/v1/events/series/{sid}/register", json=payload)
    assert second.status_code == 201
    body = second.json()
    assert body["registered_count"] == 0
    assert body["already_registered_count"] == 2
    assert all(o["status"] == "already_registered" for o in body["outcomes"])

    count_q = await test_db.execute(
        select(func.count(EventRegistration.id)).where(
            func.lower(EventRegistration.patron_email) == "cookbook.fan@example.com"
        )
    )
    assert count_q.scalar() == 2


@pytest.mark.asyncio
async def test_register_for_series_404_on_missing_series(
    test_db, client, monkeypatch
):
    from app.api.v1 import event_series as series_module

    async def _fake_verify(*_args, **_kwargs):
        return True

    monkeypatch.setattr(series_module, "verify_turnstile", _fake_verify)

    resp = await client.post(
        "/api/v1/events/series/no-such-series/register",
        json={"patron_name": "X", "patron_email": "x@example.com"},
    )
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_series_detail_schema_round_trip():
    """Schema-only sanity check; runs on any backend."""
    from app.schemas.event_series import (
        SeriesDetailResponse,
        SeriesOccurrence,
        SeriesRegistrationResponse,
    )

    occ = SeriesOccurrence(
        event_id=1,
        start_time=datetime.now(timezone.utc),
        is_published=True,
        registration_required=True,
    )
    detail = SeriesDetailResponse(
        series_id="abc",
        series_name="ABC",
        upcoming_count=1,
        occurrences=[occ],
    )
    dump = detail.model_dump()
    assert dump["series_id"] == "abc"
    assert dump["upcoming_count"] == 1
    assert len(dump["occurrences"]) == 1

    reg = SeriesRegistrationResponse(
        series_id="abc",
        series_name="ABC",
        total_upcoming=1,
        registered_count=1,
        already_registered_count=0,
        waitlisted_count=0,
        failed_count=0,
        outcomes=[],
    )
    assert reg.model_dump()["registered_count"] == 1
