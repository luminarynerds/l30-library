# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for role-list deny-all bugs fixed alongside PR #689/#694.

Three sites had `role in ["ADMIN", ...]` (uppercase string list) against a
`UserRole(str, Enum)` whose values are lowercase. The comparison was always
False, so every caller (including SUPER_ADMIN) was 403'd.

These tests pin the routes as super_admin and assert NOT 403/401.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.auth import get_current_user
from app.core.database import get_db
from app.main import app
from app.models.user import User, UserRole


def _client_for(test_db, user: User) -> AsyncClient:
    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
async def super_admin(test_db):
    from app.core.security import hash_password

    user = User(
        email="super@example.com",
        password_hash=hash_password("SuperPwd123!"),
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPER_ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_support_ticket_detail_allows_super_admin(test_db, super_admin):
    """support.py:241 — super_admin must be able to view any ticket."""
    from datetime import datetime, timezone

    from app.models.support_ticket import SupportTicket, SupportTicketStatus, SupportTicketContactMethod

    ticket = SupportTicket(
        ticket_number=f"T-{uuid.uuid4().hex[:8]}",
        name="Test Patron",
        email="patron@example.com",
        issue_description="test",
        contact_method=SupportTicketContactMethod.EMAIL,
        status=SupportTicketStatus.OPEN,
        submitted_at=datetime.now(timezone.utc),
    )
    test_db.add(ticket)
    await test_db.commit()
    await test_db.refresh(ticket)

    async with _client_for(test_db, super_admin) as client:
        resp = await client.get(f"/api/v1/support/tickets/{ticket.id}")

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code != 403, resp.text
    assert resp.status_code != 401, resp.text


@pytest.mark.asyncio
async def test_library_agents_create_allows_super_admin(test_db, super_admin):
    """library_agents.py:675 — super_admin must be able to create agents."""
    payload = {
        "name": "Test Agent",
        "description": "regression",
        "tone": "friendly",
        "persona": "librarian",
    }

    async with _client_for(test_db, super_admin) as client:
        resp = await client.post("/api/v1/library-agents/", json=payload)

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code != 403, resp.text
    assert resp.status_code != 401, resp.text


@pytest.mark.asyncio
async def test_faq_chatbot_pattern_create_allows_super_admin(test_db, super_admin):
    """faq_chatbot.py:336 — super_admin must be able to create FAQ patterns."""
    async with _client_for(test_db, super_admin) as client:
        resp = await client.post(
            "/api/v1/faq-chatbot/patterns",
            params={
                "faq_id": 999999,
                "pattern_text": "hello",
                "match_type": "keyword",
                "priority": 1,
            },
        )

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_user, None)

    # We don't care whether it succeeds on the FAQ-id check; we care it's not
    # blocked at the authorization gate.
    assert resp.status_code != 403, resp.text
    assert resp.status_code != 401, resp.text
