# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for public (unauthenticated) public-records endpoints.

POST /api/v1/public-records/public/submit
GET  /api/v1/public-records/public/disclosure-log

Note: These tests share the l30_test PostgreSQL DB and depend on the
test_db fixture for cleanup. Each test gets its own event loop (asyncio_mode=auto).
"""

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.board import BoardMeeting
from app.models.public_records_request import (
    PublicRecordsAuditLog,
    PublicRecordsRequest,
    PublicRecordsRequestStatus,
)


pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
async def _reset_test_engine_pool():
    """Workaround for asyncpg cross-event-loop pool errors in this file.
    Shared L30 test engine pool keeps PG connections alive across tests; each
    pytest-asyncio test gets a fresh event loop, but the pooled connection
    from the prior loop is invalid. Disposing forces a fresh pool.
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


SUBMIT_URL = "/api/v1/public-records/public/submit"
LOG_URL = "/api/v1/public-records/public/disclosure-log"

VALID_PAYLOAD = {
    "requester_name": "Jane Doe",
    "requester_email": "jane@example.com",
    "description": "I am requesting all board meeting minutes from January 2026.",
    "preferred_format": "digital",
    "turnstile_token": "valid-mock-token",
}


@pytest.fixture
def mock_bt():
    """Mock BackgroundTasks.add_task so no real async tasks are scheduled."""
    with patch("fastapi.BackgroundTasks.add_task", new=MagicMock()) as m:
        yield m


async def test_public_submit_creates_request(client: AsyncClient, test_db: AsyncSession, mock_bt):
    """Happy path: POST creates a row in public_records_requests."""
    with patch(
        "app.api.v1.public_records.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(SUBMIT_URL, json=VALID_PAYLOAD)

    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert "tracking_number" in data
    assert "response_deadline" in data

    result = await test_db.execute(
        select(PublicRecordsRequest).where(
            PublicRecordsRequest.tracking_number == data["tracking_number"]
        )
    )
    prr = result.scalar_one_or_none()
    assert prr is not None
    assert prr.submitted_via == "public_form"


async def test_public_submit_creates_request_with_meeting_link(
    client: AsyncClient, test_db: AsyncSession, mock_bt
):
    """POST with meeting_id stores the value on the row."""
    meeting = BoardMeeting(
        meeting_type="regular",
        title="Meeting Link Test Meeting",
        scheduled_date=datetime.now(timezone.utc),
        is_cancelled=False,
    )
    test_db.add(meeting)
    await test_db.commit()
    await test_db.refresh(meeting)

    payload = {**VALID_PAYLOAD, "meeting_id": meeting.id}
    with patch(
        "app.api.v1.public_records.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(SUBMIT_URL, json=payload)

    assert resp.status_code == 201, resp.text
    data = resp.json()

    result = await test_db.execute(
        select(PublicRecordsRequest).where(
            PublicRecordsRequest.tracking_number == data["tracking_number"]
        )
    )
    prr = result.scalar_one_or_none()
    assert prr is not None
    assert prr.submitted_via == "public_form"


async def test_public_submit_requires_turnstile(client: AsyncClient, mock_bt):
    """Turnstile failure returns 400."""
    with patch(
        "app.api.v1.public_records.verify_turnstile",
        new=AsyncMock(return_value=False),
    ):
        resp = await client.post(SUBMIT_URL, json=VALID_PAYLOAD)

    assert resp.status_code == 400


async def test_public_submit_validates_description_length_min(client: AsyncClient):
    """Description under 10 chars returns 422."""
    payload = {**VALID_PAYLOAD, "description": "short"}
    resp = await client.post(SUBMIT_URL, json=payload)
    assert resp.status_code == 422


async def test_public_submit_validates_description_length_max(client: AsyncClient):
    """Description over 4000 chars returns 422."""
    payload = {**VALID_PAYLOAD, "description": "x" * 4001}
    resp = await client.post(SUBMIT_URL, json=payload)
    assert resp.status_code == 422


async def test_public_submit_records_ip_and_ua(
    client: AsyncClient, test_db: AsyncSession, mock_bt
):
    """IP/UA are recorded on the audit log entry for the new request."""
    with patch(
        "app.api.v1.public_records.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            SUBMIT_URL,
            json=VALID_PAYLOAD,
            headers={"User-Agent": "TestBrowser/3.0"},
        )

    assert resp.status_code == 201
    data = resp.json()

    result = await test_db.execute(
        select(PublicRecordsRequest).where(
            PublicRecordsRequest.tracking_number == data["tracking_number"]
        )
    )
    prr = result.scalar_one_or_none()
    assert prr is not None
    log_result = await test_db.execute(
        select(PublicRecordsAuditLog).where(
            PublicRecordsAuditLog.request_id == prr.id
        )
    )
    audit = log_result.scalar_one_or_none()
    assert audit is not None
    assert audit.user_agent == "TestBrowser/3.0"


async def test_public_disclosure_log_no_auth_required(client: AsyncClient):
    """GET disclosure-log is accessible with no auth."""
    resp = await client.get(LOG_URL)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


async def test_public_disclosure_log_excludes_pii(
    client: AsyncClient, test_db: AsyncSession
):
    """Disclosure log response has no requester_email, phone, or address keys."""
    prr = PublicRecordsRequest(
        tracking_number="PRR-2026-PIITEST2",
        request_type="state_open_records",
        jurisdiction="ohio",
        requester_name="Public Person",
        requester_email="secret@example.com",
        requester_phone="555-1234",
        requester_address="123 Main St",
        is_media=False,
        is_commercial=False,
        date_received=datetime(2026, 1, 15, tzinfo=timezone.utc),
        description="Request for board minutes from January 2026 meeting.",
        response_deadline=datetime(2026, 2, 5).date(),
        status=PublicRecordsRequestStatus.COMPLETED,
        submitted_via="public_form",
    )
    test_db.add(prr)
    await test_db.commit()

    resp = await client.get(LOG_URL + "?year=2026")
    assert resp.status_code == 200
    entries = resp.json()

    pii_entry = [e for e in entries if e.get("tracking_number") == "PRR-2026-PIITEST2"]
    assert len(pii_entry) == 1

    entry = pii_entry[0]
    assert "requester_email" not in entry
    assert "requester_phone" not in entry
    assert "requester_address" not in entry
    assert "requester_name" in entry


async def test_public_disclosure_log_excludes_pending(
    client: AsyncClient, test_db: AsyncSession
):
    """Disclosure log only returns completed/denied rows, not pending."""
    prr = PublicRecordsRequest(
        tracking_number="PRR-2026-PENDTEST2",
        request_type="state_open_records",
        jurisdiction="ohio",
        requester_name="Pending Person",
        requester_email="pending@example.com",
        is_media=False,
        is_commercial=False,
        date_received=datetime(2026, 3, 1, tzinfo=timezone.utc),
        description="This is a pending request that should not appear in the public log.",
        response_deadline=datetime(2026, 3, 21).date(),
        status=PublicRecordsRequestStatus.RECEIVED,
        submitted_via="public_form",
    )
    test_db.add(prr)
    await test_db.commit()

    resp = await client.get(LOG_URL + "?year=2026")
    assert resp.status_code == 200

    tracking_numbers = [e["tracking_number"] for e in resp.json()]
    assert "PRR-2026-PENDTEST2" not in tracking_numbers
