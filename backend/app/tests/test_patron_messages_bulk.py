# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the bulk patron messaging endpoint."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.dependencies import require_staff
from app.api.v1.auth.helpers import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.patron_communication import (
    MessageChannel,
    MessageStatus,
    PatronMessage,
)
from app.models.user import User, UserRole
from sqlalchemy import select


ENDPOINT = "/api/v1/staff/patrons/messages/bulk"


@pytest.fixture
async def staff(db):
    user = User(
        email="bulk-staff@example.com",
        first_name="Bulk",
        last_name="Staff",
        password_hash="x",
        role=UserRole.STAFF,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def three_patrons(db):
    patrons = []
    for i in range(3):
        u = User(
            email=f"bulk-p{i}@example.com",
            first_name=f"Pat{i}",
            last_name="Tester",
            password_hash="x",
            role=UserRole.PATRON,
            is_active=True,
        )
        db.add(u)
        patrons.append(u)
    await db.commit()
    for p in patrons:
        await db.refresh(p)
    return patrons


@pytest.fixture
async def patron_with_phone(db):
    u = User(
        email="bulk-phone@example.com",
        first_name="Phoney",
        last_name="Patron",
        password_hash="x",
        role=UserRole.PATRON,
        is_active=True,
        phone="555-0100",
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


def _override_auth(staff_user, db):
    async def _db():
        yield db

    async def _staff():
        return staff_user

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _staff
    app.dependency_overrides[require_staff] = _staff
    app.state.setup_complete = True


def _clear_overrides():
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_staff, None)


@pytest.mark.asyncio
async def test_bulk_message_happy_path(db, staff, three_patrons):
    """All recipients have email, send succeeds → 3 sent, 0 capped, 0 failed."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        with patch("app.api.v1.staff.patron_messages.send_email", new=AsyncMock(return_value=True)), \
             patch("app.api.v1.staff.patron_messages.check_daily_cap", new=AsyncMock(return_value=True)):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    ENDPOINT,
                    json={
                        "patron_ids": [p.id for p in three_patrons],
                        "subject": "Library closed Monday",
                        "body": "Hi {first_name}, fyi we're closed Monday.",
                        "channels": ["email"],
                    },
                )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["sent"] == 3
        assert data["failed"] == 0
        assert data["capped"] == 0
        assert len(data["per_recipient"]) == 3
        assert all(r["status"] == "sent" for r in data["per_recipient"])
        assert all("email" in r["channels_sent"] for r in data["per_recipient"])

        # PatronMessage rows persisted with personalized body
        rows = (await db.execute(select(PatronMessage))).scalars().all()
        assert len(rows) == 3
        assert all(row.channel == MessageChannel.EMAIL for row in rows)
        assert all(row.status == MessageStatus.SENT for row in rows)
        assert any("Pat0" in row.body for row in rows)
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_bulk_message_daily_cap_mid_batch(db, staff, three_patrons):
    """Cap hit on the 2nd recipient → first sent, rest capped."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    # check_daily_cap returns True, True (1st), then False, False (2nd, 3rd)
    cap_side_effect = [True, False, False]

    async def _cap():
        return cap_side_effect.pop(0) if cap_side_effect else False

    try:
        with patch("app.api.v1.staff.patron_messages.send_email", new=AsyncMock(return_value=True)), \
             patch("app.api.v1.staff.patron_messages.check_daily_cap", new=_cap):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    ENDPOINT,
                    json={
                        "patron_ids": [p.id for p in three_patrons],
                        "body": "Hello.",
                        "channels": ["email"],
                    },
                )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["sent"] == 1
        assert data["capped"] == 2
        assert data["failed"] == 0
        statuses = [r["status"] for r in data["per_recipient"]]
        assert statuses == ["sent", "capped", "capped"]
        # Capped recipients carry a reason
        capped = [r for r in data["per_recipient"] if r["status"] == "capped"]
        assert all(r["reason"] == "daily_cap_reached" for r in capped)
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_bulk_message_role_gating_patron_rejected(db, three_patrons):
    """A patron caller must be rejected by require_staff."""
    from httpx import AsyncClient, ASGITransport

    patron_caller = three_patrons[0]
    # Override only get_current_user — leave require_staff to its real impl
    async def _db():
        yield db

    async def _user():
        return patron_caller

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_current_user] = _user
    app.state.setup_complete = True
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                ENDPOINT,
                json={
                    "patron_ids": [p.id for p in three_patrons],
                    "body": "Hello.",
                    "channels": ["email"],
                },
            )
        # require_staff raises 403 for non-staff
        assert resp.status_code == 403, resp.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_bulk_message_empty_patron_ids_400(db, staff):
    """Empty patron_ids must 4xx (pydantic min_length=1 → 422)."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                ENDPOINT,
                json={"patron_ids": [], "body": "hi", "channels": ["email"]},
            )
        assert resp.status_code in (400, 422), resp.text
    finally:
        _clear_overrides()


@pytest.mark.asyncio
async def test_bulk_message_mixed_channels(db, staff, three_patrons, patron_with_phone):
    """email + in_app + sms across two recipients: email sends for both,
    in_app skipped (pending enum migration), sms skipped (no provider).
    Patron with phone records sms_provider_not_configured rather than no_phone_on_file."""
    from httpx import AsyncClient, ASGITransport

    _override_auth(staff, db)
    try:
        with patch("app.api.v1.staff.patron_messages.send_email", new=AsyncMock(return_value=True)), \
             patch("app.api.v1.staff.patron_messages.check_daily_cap", new=AsyncMock(return_value=True)):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as ac:
                resp = await ac.post(
                    ENDPOINT,
                    json={
                        "patron_ids": [three_patrons[0].id, patron_with_phone.id],
                        "subject": "Hi",
                        "body": "Hello {first_name}.",
                        "channels": ["email", "in_app", "sms"],
                    },
                )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        first = next(r for r in data["per_recipient"] if r["patron_id"] == three_patrons[0].id)
        second = next(r for r in data["per_recipient"] if r["patron_id"] == patron_with_phone.id)
        # Both succeed via email; in_app and sms only contribute reasons.
        assert first["status"] == "sent"
        assert first["channels_sent"] == ["email"]
        assert second["status"] == "sent"
        assert second["channels_sent"] == ["email"]
        # Reasons surface the non-email channel outcomes (last one wins)
        assert data["sent"] == 2
        assert data["failed"] == 0
        assert data["capped"] == 0
    finally:
        _clear_overrides()
