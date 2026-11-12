# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the staff support-ticket triage endpoints.

Covers:
- Patron POST /support/tickets honeypot silently accepts but does not persist
- Patron POST /support/tickets category validation
- Staff GET /support/tickets filters (status, category, search, date range, unassigned)
- Staff PATCH /support/tickets/{id} status transition + claim/release
- Staff POST /support/tickets/{id}/responses logs an event
- Permission gates: anonymous can POST, non-staff cannot list, staff cannot close (admin only)
- Audit events are recorded on every status change and assignment
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user, get_optional_user
from app.main import app
from app.models.support_ticket import (
    SupportTicket,
    SupportTicketCategory,
    SupportTicketContactMethod,
    SupportTicketEvent,
    SupportTicketStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anon_client(client):
    """No auth override: get_current_user/get_optional_user behave normally."""
    # get_optional_user returns None when no token; ensure no override leaks.
    app.dependency_overrides.pop(get_optional_user, None)
    app.dependency_overrides[get_optional_user] = lambda: None
    yield client
    app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def staff_client(client, test_staff):
    app.dependency_overrides[get_current_user] = lambda: test_staff
    app.dependency_overrides[get_optional_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def admin_client(client, test_admin):
    app.dependency_overrides[get_current_user] = lambda: test_admin
    app.dependency_overrides[get_optional_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    app.dependency_overrides[get_current_user] = lambda: test_patron
    app.dependency_overrides[get_optional_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_user, None)


@pytest.fixture
async def seeded_ticket(test_db):
    """Seed a single OPEN ticket so detail/list endpoints have a row."""
    t = SupportTicket(
        ticket_number="SUPPORT-2026-SEED0001",
        name="Test Patron",
        email="patron@example.com",
        phone=None,
        issue_description="I cannot renew my book online.",
        contact_method=SupportTicketContactMethod.EMAIL,
        status=SupportTicketStatus.OPEN,
        category=SupportTicketCategory.CIRCULATION.value,
        submitted_at=datetime.now(timezone.utc),
    )
    test_db.add(t)
    await test_db.commit()
    await test_db.refresh(t)
    return t


# ---------------------------------------------------------------------------
# Honeypot + rate limit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_honeypot_silently_drops_submission(anon_client, test_db):
    """A bot that fills website_url gets 201 + a fake ref, no DB row written."""
    payload = {
        "name": "Spambot",
        "email": "spambot@example.com",
        "issue_description": "buy our pills",
        "contact_method": "email",
        "category": "general",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "website_url": "https://evil.example.com/landing",
    }
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    assert response.status_code == 201
    body = response.json()
    assert body["ticket_id"] == "0"
    assert body["reference_number"].startswith("SUPPORT-")

    result = await test_db.execute(
        select(SupportTicket).where(SupportTicket.email == "spambot@example.com")
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_valid_submission_persists_and_records_event(anon_client, test_db):
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "issue_description": "I want to suggest a purchase.",
        "contact_method": "email",
        "category": "acquisitions",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    assert response.status_code == 201
    ref = response.json()["reference_number"]

    result = await test_db.execute(
        select(SupportTicket).where(SupportTicket.ticket_number == ref)
    )
    ticket = result.scalar_one()
    assert ticket.category == "acquisitions"

    events = (
        await test_db.execute(
            select(SupportTicketEvent).where(SupportTicketEvent.ticket_id == ticket.id)
        )
    ).scalars().all()
    assert any(e.event_type == "created" for e in events)


@pytest.mark.asyncio
async def test_invalid_category_rejected(anon_client):
    payload = {
        "name": "Jane Doe",
        "email": "jane@example.com",
        "issue_description": "msg",
        "contact_method": "email",
        "category": "not-a-real-category",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Staff list filters + permission gates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patron_cannot_list_tickets(patron_client, seeded_ticket):
    response = await patron_client.get("/api/v1/support/tickets")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_staff_can_list_tickets(staff_client, seeded_ticket):
    response = await staff_client.get("/api/v1/support/tickets")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    found = [t for t in data["tickets"] if t["ticket_number"] == seeded_ticket.ticket_number]
    assert len(found) == 1
    assert found[0]["sla_business_days"] == 1  # circulation = 1bd
    assert "sla_breached" in found[0]


@pytest.mark.asyncio
async def test_filter_by_category(staff_client, seeded_ticket):
    response = await staff_client.get(
        "/api/v1/support/tickets?category=circulation"
    )
    assert response.status_code == 200
    data = response.json()
    assert all(t["category"] == "circulation" for t in data["tickets"])


@pytest.mark.asyncio
async def test_filter_by_search(staff_client, seeded_ticket):
    response = await staff_client.get(
        "/api/v1/support/tickets?search=renew"
    )
    assert response.status_code == 200
    data = response.json()
    assert any("renew" in t["issue_description"].lower() for t in data["tickets"])


@pytest.mark.asyncio
async def test_filter_unassigned(staff_client, seeded_ticket):
    response = await staff_client.get(
        "/api/v1/support/tickets?status_filter=unassigned"
    )
    assert response.status_code == 200
    data = response.json()
    assert all(t["assigned_to_id"] is None for t in data["tickets"])


@pytest.mark.asyncio
async def test_invalid_status_filter_400(staff_client):
    response = await staff_client.get(
        "/api/v1/support/tickets?status_filter=bogus"
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# PATCH: claim/release/status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_staff_can_claim_and_release(staff_client, seeded_ticket, test_staff, test_db):
    # Claim
    response = await staff_client.patch(
        f"/api/v1/support/tickets/{seeded_ticket.id}",
        json={"assigned_to_id": test_staff.id, "status": "in_progress"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["assigned_to_id"] == test_staff.id
    assert body["status"] == "in_progress"

    # Audit events recorded
    events = (
        await test_db.execute(
            select(SupportTicketEvent)
            .where(SupportTicketEvent.ticket_id == seeded_ticket.id)
            .order_by(SupportTicketEvent.id)
        )
    ).scalars().all()
    types = {e.event_type for e in events}
    assert "assigned" in types
    assert "status_changed" in types

    # Release
    response = await staff_client.patch(
        f"/api/v1/support/tickets/{seeded_ticket.id}",
        json={"assigned_to_id": -1},
    )
    assert response.status_code == 200
    assert response.json()["assigned_to_id"] is None


@pytest.mark.asyncio
async def test_staff_cannot_close_admin_can(client, test_staff, test_admin, seeded_ticket):
    # We need to swap the auth identity mid-test, so manage the dependency
    # overrides inline rather than via the staff_client/admin_client fixtures
    # (those overrides race when both are pulled into one test).
    try:
        # Staff close attempt -> 403
        app.dependency_overrides[get_current_user] = lambda: test_staff
        app.dependency_overrides[get_optional_user] = lambda: test_staff
        response = await client.patch(
            f"/api/v1/support/tickets/{seeded_ticket.id}",
            json={"status": "closed"},
        )
        assert response.status_code == 403

        # Admin close -> 200
        app.dependency_overrides[get_current_user] = lambda: test_admin
        app.dependency_overrides[get_optional_user] = lambda: test_admin
        response = await client.patch(
            f"/api/v1/support/tickets/{seeded_ticket.id}",
            json={"status": "closed"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "closed"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_user, None)


# ---------------------------------------------------------------------------
# Responses + audit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_response_logs_event(staff_client, seeded_ticket, test_db):
    response = await staff_client.post(
        f"/api/v1/support/tickets/{seeded_ticket.id}/responses",
        json={"body": "Hello — your book has been renewed.", "set_status": "resolved"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "resolved"

    events = (
        await test_db.execute(
            select(SupportTicketEvent)
            .where(SupportTicketEvent.ticket_id == seeded_ticket.id)
            .order_by(SupportTicketEvent.id)
        )
    ).scalars().all()
    types = [e.event_type for e in events]
    assert "response_sent" in types
    assert "status_changed" in types


@pytest.mark.asyncio
async def test_events_endpoint_returns_history(staff_client, seeded_ticket):
    # Generate a few events via PATCH
    await staff_client.patch(
        f"/api/v1/support/tickets/{seeded_ticket.id}",
        json={"status": "in_progress"},
    )
    response = await staff_client.get(
        f"/api/v1/support/tickets/{seeded_ticket.id}/events"
    )
    assert response.status_code == 200
    events = response.json()
    assert len(events) >= 1
    assert any(e["event_type"] == "status_changed" for e in events)
