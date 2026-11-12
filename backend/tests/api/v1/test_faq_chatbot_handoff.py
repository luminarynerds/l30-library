# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from sqlalchemy import select

from app.models.support_ticket import SupportTicket
from app.models.notification import Notification, NotificationType
from app.models.knowledge_base import FAQChatbotConversation


async def test_handoff_creates_ticket_notifies_and_records(client, db, test_admin):
    payload = {
        "message": "I need help with my account",
        "contact_method": "email",
        "patron_name": "Pat Patron",
        "conversation_context": [
            {"role": "user", "text": "hi"},
            {"role": "bot", "text": "hello"},
            {"role": "user", "text": "still stuck"},
        ],
    }
    resp = await client.post("/api/v1/faq-chatbot/handoff", json=payload)
    assert resp.status_code == 200, resp.text
    assert resp.json()["success"] is True

    ticket = (await db.execute(
        select(SupportTicket).order_by(SupportTicket.id.desc())
    )).scalars().first()
    assert ticket is not None
    assert ticket.subject_line == "Help chat handoff"
    assert "I need help with my account" in ticket.issue_description
    assert "3 help-chat exchange" in ticket.issue_description

    convo = (await db.execute(
        select(FAQChatbotConversation).order_by(FAQChatbotConversation.id.desc())
    )).scalars().first()
    assert convo is not None
    assert convo.escalated_to_support is True
    assert convo.support_ticket_id == ticket.id

    notes = (await db.execute(
        select(Notification).where(
            Notification.notification_type == NotificationType.STAFF_HELP_REQUESTED
        )
    )).scalars().all()
    assert len(notes) >= 1


async def test_handoff_redacts_pii_in_ticket(client, db):
    payload = {
        "message": "reach me at secret@example.com or 555-123-4567",
        "contact_method": "email",
        "conversation_context": [],
    }
    resp = await client.post("/api/v1/faq-chatbot/handoff", json=payload)
    assert resp.status_code == 200, resp.text

    ticket = (await db.execute(
        select(SupportTicket).order_by(SupportTicket.id.desc())
    )).scalars().first()
    assert "secret@example.com" not in ticket.issue_description
    assert "[email]" in ticket.issue_description
    assert "[phone]" in ticket.issue_description


async def test_handoff_maps_in_person_to_visit(client, db):
    from app.models.support_ticket import SupportTicketContactMethod
    payload = {
        "message": "please call me at the desk",
        "contact_method": "in_person",
        "conversation_context": [],
    }
    resp = await client.post("/api/v1/faq-chatbot/handoff", json=payload)
    assert resp.status_code == 200, resp.text
    ticket = (await db.execute(
        select(SupportTicket).order_by(SupportTicket.id.desc())
    )).scalars().first()
    assert ticket.contact_method == SupportTicketContactMethod.VISIT


async def test_handoff_authenticated_puts_identity_on_ticket(test_db, db, test_patron):
    # The authenticated patron's name/email should land on the access-controlled
    # ticket. The handler resolves identity via get_optional_user, so we override
    # that dependency to return the patron (there is no patron-authed client fixture).
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth.helpers import get_optional_user
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_optional_user():
        return test_patron

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_optional_user] = override_get_optional_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            payload = {
                "message": "account question",
                "contact_method": "email",
                "conversation_context": [],
            }
            resp = await ac.post("/api/v1/faq-chatbot/handoff", json=payload)
        assert resp.status_code == 200, resp.text
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_optional_user, None)

    ticket = (await db.execute(
        select(SupportTicket).order_by(SupportTicket.id.desc())
    )).scalars().first()
    assert ticket.email == test_patron.email
    assert ticket.is_anonymous is False


async def test_chat_stores_redacted_question(client, db):
    payload = {
        "question": "email me at leak@example.com",
        "device_type": "web",
        "location": "homepage",
    }
    resp = await client.post("/api/v1/faq-chatbot/chat", json=payload)
    assert resp.status_code == 201, resp.text

    convo = (await db.execute(
        select(FAQChatbotConversation).order_by(FAQChatbotConversation.id.desc())
    )).scalars().first()
    assert convo is not None
    assert "leak@example.com" not in convo.original_question
    assert "[email]" in convo.original_question


def test_chat_response_includes_source_fields():
    from app.api.v1.faq_chatbot import ChatbotResponseData
    fields = ChatbotResponseData.model_fields
    assert "source_title" in fields
    assert "source_id" in fields
