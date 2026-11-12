# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for staff-only admin endpoints on /api/v1/library-agents.

Covers:
  * `GET /library-agents/admin/conversations` returns a paginated list
    with `helpful` filter applied.
  * `GET /library-agents/admin/stats` returns aggregate counts.
  * Patron callers get 403 on both routes.
"""
import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.ai_agents import AgentConversation, LibraryAgent
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded_agent_admin(test_db):
    agent = LibraryAgent(
        name="Admin Test Agent",
        role="Reference",
        department="reference",
        bio="Agent for admin endpoint tests.",
        system_prompt="Be helpful.",
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent


@pytest.fixture
async def seeded_staff_admin(test_db):
    from app.core.security import hash_password

    user = User(
        email="staff-admin@example.test",
        password_hash=hash_password("StaffAdminPwd123!"),
        first_name="Sara",
        last_name="StaffAdmin",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def seeded_patron_admin(test_db):
    from app.core.security import hash_password

    user = User(
        email="patron-admin@example.test",
        password_hash=hash_password("PatronAdminPwd123!"),
        first_name="Pia",
        last_name="PatronAdmin",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def seeded_conversations(test_db, seeded_agent_admin, seeded_patron_admin):
    """Three conversations: one helpful, one not_helpful, one no_feedback."""
    helpful = AgentConversation(
        agent_id=seeded_agent_admin.id,
        user_id=seeded_patron_admin.id,
        session_id="sess-admin-1",
        user_message="Q1",
        agent_response="A1",
        helpful=True,
    )
    not_helpful = AgentConversation(
        agent_id=seeded_agent_admin.id,
        user_id=seeded_patron_admin.id,
        session_id="sess-admin-2",
        user_message="Q2",
        agent_response="A2",
        helpful=False,
    )
    no_feedback = AgentConversation(
        agent_id=seeded_agent_admin.id,
        user_id=seeded_patron_admin.id,
        session_id="sess-admin-3",
        user_message="Q3",
        agent_response="A3",
    )
    test_db.add_all([helpful, not_helpful, no_feedback])
    await test_db.commit()
    return {"helpful": helpful, "not_helpful": not_helpful, "no_feedback": no_feedback}


@pytest.fixture
def staff_admin_client(client, seeded_staff_admin):
    app.dependency_overrides[get_current_user] = lambda: seeded_staff_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_admin_client(client, seeded_patron_admin):
    app.dependency_overrides[get_current_user] = lambda: seeded_patron_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_conversations_lists_all(staff_admin_client, seeded_conversations):
    response = await staff_admin_client.get("/api/v1/library-agents/admin/conversations")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 3
    assert len(body["conversations"]) == 3
    assert all("agent_name" in c for c in body["conversations"])


@pytest.mark.asyncio
async def test_admin_conversations_helpful_filter(
    staff_admin_client, seeded_conversations
):
    response = await staff_admin_client.get(
        "/api/v1/library-agents/admin/conversations?helpful=true"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["conversations"][0]["helpful"] is True

    response = await staff_admin_client.get(
        "/api/v1/library-agents/admin/conversations?helpful=false"
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["conversations"][0]["helpful"] is False


@pytest.mark.asyncio
async def test_admin_stats_aggregates(staff_admin_client, seeded_conversations):
    response = await staff_admin_client.get("/api/v1/library-agents/admin/stats")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_agents"] >= 1
    assert body["total_conversations"] == 3
    assert body["total_feedback"] == 2
    assert body["avg_helpfulness_rate"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_admin_conversations_403_for_patron(
    patron_admin_client, seeded_conversations
):
    response = await patron_admin_client.get("/api/v1/library-agents/admin/conversations")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_stats_403_for_patron(patron_admin_client, seeded_conversations):
    response = await patron_admin_client.get("/api/v1/library-agents/admin/stats")
    assert response.status_code == 403
