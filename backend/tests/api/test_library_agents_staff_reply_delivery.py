# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API tests for patron-facing staff-reply unread tracking.

Covers:
  * `GET /api/v1/library-agents/chat-sessions` returns
    ``unread_staff_reply_count`` per session.
  * `GET /api/v1/library-agents/chat-sessions/{id}/messages`, when called by
    the session owner, marks all unread staff replies as seen.
  * The same messages endpoint, when called by a staff member who does NOT
    own the session, does NOT mark replies seen.
"""
import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.ai_agents import AgentConversation, LibraryAgent
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded_agent(test_db):
    agent = LibraryAgent(
        name="Test Reference Agent",
        role="Reference Librarian",
        department="reference",
        bio="A test agent for unit tests.",
        system_prompt="Be helpful.",
    )
    test_db.add(agent)
    await test_db.commit()
    await test_db.refresh(agent)
    return agent


@pytest.fixture
async def seeded_patron(test_db):
    from app.core.security import hash_password

    user = User(
        email="patron-unread@example.test",
        password_hash=hash_password("UnreadPwd123!"),
        first_name="Una",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def seeded_staff(test_db):
    from app.core.security import hash_password

    user = User(
        email="staff-unread@example.test",
        password_hash=hash_password("StaffPwd123!"),
        first_name="Stan",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def seeded_session(test_db, seeded_agent, seeded_patron):
    """Create a session: one patron message + one unseen staff reply."""
    patron_msg = AgentConversation(
        agent_id=seeded_agent.id,
        user_id=seeded_patron.id,
        session_id="sess-unread-1",
        user_message="When do you open Sunday?",
        agent_response="(initial agent ack)",
    )
    staff_reply = AgentConversation(
        agent_id=seeded_agent.id,
        user_id=seeded_patron.id,
        session_id="sess-unread-1",
        user_message="[Staff reply]",
        agent_response="We open at 1pm on Sundays.",
        conversation_context={"staff_reply": True, "staff_id": 999, "staff_name": "Sam"},
    )
    test_db.add_all([patron_msg, staff_reply])
    await test_db.commit()
    await test_db.refresh(staff_reply)
    return {"patron_msg": patron_msg, "staff_reply": staff_reply, "session_id": "sess-unread-1"}


@pytest.fixture
def patron_client(client, seeded_patron):
    """Client where get_current_user resolves to the seeded patron."""
    app.dependency_overrides[get_current_user] = lambda: seeded_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client(client, seeded_staff):
    """Client where get_current_user resolves to the seeded staff user."""
    app.dependency_overrides[get_current_user] = lambda: seeded_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_chat_sessions_reports_unread_staff_reply_count(
    patron_client, test_db, seeded_session
):
    """GET /chat-sessions exposes unread_staff_reply_count per session."""
    response = await patron_client.get("/api/v1/library-agents/chat-sessions")
    assert response.status_code == 200, response.text
    sessions = response.json()
    target = next(
        (s for s in sessions if s["session_id"] == seeded_session["session_id"]),
        None,
    )
    assert target is not None, f"session not in response: {sessions}"
    assert target["unread_staff_reply_count"] == 1
    assert target["has_staff_reply"] is True


@pytest.mark.asyncio
async def test_get_messages_marks_staff_replies_seen(
    patron_client, test_db, seeded_session
):
    """Patron fetching session messages marks unread staff replies seen."""
    staff_reply_id = seeded_session["staff_reply"].id

    # Sanity check: NULL before request
    pre = await test_db.execute(
        select(AgentConversation.seen_by_patron_at).where(
            AgentConversation.id == staff_reply_id
        )
    )
    assert pre.scalar_one() is None

    response = await patron_client.get(
        f"/api/v1/library-agents/chat-sessions/{seeded_session['session_id']}/messages"
    )
    assert response.status_code == 200, response.text

    # Re-fetch (expire to bypass identity-map cache)
    test_db.expire_all()
    post = await test_db.execute(
        select(AgentConversation.seen_by_patron_at).where(
            AgentConversation.id == staff_reply_id
        )
    )
    assert post.scalar_one() is not None


@pytest.mark.asyncio
async def test_staff_get_messages_does_not_mark_seen(
    staff_client, test_db, seeded_session
):
    """Staff fetching another user's session must NOT mark staff replies seen."""
    staff_reply_id = seeded_session["staff_reply"].id

    response = await staff_client.get(
        f"/api/v1/library-agents/chat-sessions/{seeded_session['session_id']}/messages"
    )
    assert response.status_code == 200, response.text

    test_db.expire_all()
    post = await test_db.execute(
        select(AgentConversation.seen_by_patron_at).where(
            AgentConversation.id == staff_reply_id
        )
    )
    assert post.scalar_one() is None


@pytest.fixture
async def other_patron(test_db):
    from app.core.security import hash_password

    user = User(
        email="other-patron@example.test",
        password_hash=hash_password("OtherPwd123!"),
        first_name="Otto",
        last_name="Other",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def other_patron_client(client, other_patron):
    """Client where get_current_user resolves to a patron who does NOT own the session."""
    app.dependency_overrides[get_current_user] = lambda: other_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_messages_403s_for_non_owner_non_staff(
    test_db, seeded_session, other_patron_client
):
    """A logged-in patron who is not the session owner gets 403, not the messages."""
    sid = seeded_session["session_id"]
    response = await other_patron_client.get(
        f"/api/v1/library-agents/chat-sessions/{sid}/messages"
    )
    assert response.status_code == 403
