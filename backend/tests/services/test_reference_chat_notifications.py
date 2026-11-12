# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the reference-chat staff-reply notification dispatcher.

The dispatcher fans a staff reply out to:
  * an in-app PatronNotification (only if the chat session has a user_id), and
  * an email (to the patron account email OR the session followup_email).

It must be idempotent on `source_event_id = staff_reply:<conv_id>`, and a no-op
for fully anonymous sessions (no user, no followup email).
"""
import pytest
from sqlalchemy import select

from app.models.ai_agents import AgentConversation, LibraryAgent
from app.models.notification import (
    PatronNotification,
    PatronNotificationCategory,
)
from app.models.user import User, UserRole
from app.services.notifications.reference_chat import send_staff_reply_notification


# ---------------------------------------------------------------------------
# Local fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def seeded_agent(test_db):
    """Create a minimal LibraryAgent for FK-satisfying conversation rows."""
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
    """Create a logged-in patron with an email."""
    from app.core.security import hash_password

    user = User(
        email="patron-ref-chat@example.test",
        password_hash=hash_password("RefChatPwd123!"),
        first_name="Refa",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


async def _make_session(
    db,
    *,
    agent_id: int,
    session_id: str,
    user_id: int | None,
    user_message: str,
    agent_response: str,
    conversation_context: dict | None = None,
    patron_followup_email: str | None = None,
) -> AgentConversation:
    row = AgentConversation(
        agent_id=agent_id,
        user_id=user_id,
        session_id=session_id,
        user_message=user_message,
        agent_response=agent_response,
        conversation_context=conversation_context,
        patron_followup_email=patron_followup_email,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_creates_patron_notification_when_user_present(
    test_db, seeded_agent, seeded_patron, monkeypatch
):
    sent = []

    async def fake_send_email(**kwargs):
        sent.append(kwargs)
        return True

    monkeypatch.setattr(
        "app.services.notifications.reference_chat.send_email",
        fake_send_email,
    )

    # Original patron question
    await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-logged-in",
        user_id=seeded_patron.id,
        user_message="When do you open on Sunday?",
        agent_response="(initial agent ack)",
    )
    staff_reply = await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-logged-in",
        user_id=seeded_patron.id,
        user_message="(staff reply)",
        agent_response="We open at 1pm on Sundays.",
        conversation_context={"staff_reply": True, "staff_name": "Sam"},
    )

    await send_staff_reply_notification(test_db, staff_reply)

    notif = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.patron_id == seeded_patron.id
            )
        )
    ).scalar_one()

    assert notif.category == PatronNotificationCategory.REFERENCE_CHAT_REPLY
    assert notif.source_event_id == f"staff_reply:{staff_reply.id}"
    assert notif.action_url is not None
    assert "sess-logged-in" in notif.action_url
    # Email sent to the patron account email
    assert len(sent) == 1
    assert sent[0]["to_email"] == seeded_patron.email


async def test_idempotent_on_replay(
    test_db, seeded_agent, seeded_patron, monkeypatch
):
    async def fake_send_email(**kwargs):
        return True

    monkeypatch.setattr(
        "app.services.notifications.reference_chat.send_email",
        fake_send_email,
    )

    await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-idem",
        user_id=seeded_patron.id,
        user_message="What hours today?",
        agent_response="(initial agent ack)",
    )
    staff_reply = await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-idem",
        user_id=seeded_patron.id,
        user_message="(staff reply)",
        agent_response="We close at 6pm tonight.",
        conversation_context={"staff_reply": True, "staff_name": "Sam"},
    )

    await send_staff_reply_notification(test_db, staff_reply)
    await send_staff_reply_notification(test_db, staff_reply)

    rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.source_event_id == f"staff_reply:{staff_reply.id}"
            )
        )
    ).scalars().all()
    assert len(rows) == 1


async def test_anonymous_with_followup_email_dispatches_email_only(
    test_db, seeded_agent, monkeypatch
):
    sent = []

    async def fake_send_email(**kwargs):
        sent.append(kwargs)
        return True

    monkeypatch.setattr(
        "app.services.notifications.reference_chat.send_email",
        fake_send_email,
    )

    # Original anonymous question with followup_email opt-in
    await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-anon-followup",
        user_id=None,
        user_message="Do you have French novels?",
        agent_response="(initial agent ack)",
        patron_followup_email="anon-patron@example.test",
    )
    staff_reply = await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-anon-followup",
        user_id=None,
        user_message="(staff reply)",
        agent_response="Yes, in our world languages collection.",
        conversation_context={"staff_reply": True, "staff_name": "Sam"},
    )

    await send_staff_reply_notification(test_db, staff_reply)

    # Email goes out
    assert len(sent) == 1
    assert sent[0]["to_email"] == "anon-patron@example.test"

    # No PatronNotification (no user to attach to)
    notifs = (
        await test_db.execute(select(PatronNotification))
    ).scalars().all()
    assert notifs == []


async def test_anonymous_without_email_is_noop(
    test_db, seeded_agent, monkeypatch
):
    sent = []

    async def fake_send_email(**kwargs):
        sent.append(kwargs)
        return True

    monkeypatch.setattr(
        "app.services.notifications.reference_chat.send_email",
        fake_send_email,
    )

    await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-anon-noemail",
        user_id=None,
        user_message="just curious",
        agent_response="(initial agent ack)",
    )
    staff_reply = await _make_session(
        test_db,
        agent_id=seeded_agent.id,
        session_id="sess-anon-noemail",
        user_id=None,
        user_message="(staff reply)",
        agent_response="Happy to help anytime.",
        conversation_context={"staff_reply": True, "staff_name": "Sam"},
    )

    # Should not raise
    await send_staff_reply_notification(test_db, staff_reply)

    assert sent == []
    notif_rows = (
        await test_db.execute(
            select(PatronNotification).where(
                PatronNotification.source_event_id == f"staff_reply:{staff_reply.id}"
            )
        )
    ).all()
    assert notif_rows == []
