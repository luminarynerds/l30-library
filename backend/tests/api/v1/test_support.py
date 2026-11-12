# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the patron contact-form additions to POST /api/v1/support/tickets.

PR #725 already covers honeypot + rate limit + staff triage. This file
covers the contact-page-specific behaviours added in PR
"feat: rewire contact page":

- Happy-path patron contact submission populates category/route/sla in
  the response and persists the camelCase-to-enum mapping.
- Anonymous submission server-strips name/email/phone even if the client
  sent values.
- Under-13 / COPPA-safe path with contact_method="none" and no
  identifiers succeeds.
- contact_method="email" without an email value returns 400.
- Escalation-modal backward compatibility: the legacy payload (snake_case
  category, name+email present, no is_anonymous flag) still creates a
  valid ticket.
"""

from datetime import datetime, timezone

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user, get_optional_user
from app.main import app
from app.models.support_ticket import SupportTicket


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def anon_client(client):
    """No auth override: get_optional_user returns None as a real anon would."""
    app.dependency_overrides.pop(get_optional_user, None)
    app.dependency_overrides[get_optional_user] = lambda: None
    yield client
    app.dependency_overrides.pop(get_optional_user, None)


def _base_payload(**overrides):
    payload = {
        "name": "Maria Reader",
        "email": "maria@example.org",
        "issue_description": "Looking for books on Ohio public records law.",
        "contact_method": "email",
        "category": "referenceHelp",
        "is_anonymous": False,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    payload.update(overrides)
    return payload


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_contact_form_happy_path_maps_patron_category_and_returns_sla(
    anon_client, test_db
):
    """A patron-form submit with camelCase ``referenceHelp`` is stored as the
    canonical enum value ``reference``, with response_route + sla_business_days
    surfaced on the response."""
    payload = _base_payload()
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["category"] == "reference"
    assert body["response_route"] == "reference"
    assert body["sla_business_days"] == 1
    assert body["reference_number"].startswith("SUPPORT-")
    assert body["ticket_id"] != "0"

    # DB side: camelCase resolved to canonical enum value
    result = await test_db.execute(
        select(SupportTicket).where(SupportTicket.email == "maria@example.org")
    )
    ticket = result.scalar_one()
    assert ticket.category == "reference"
    assert ticket.response_route == "reference"
    assert ticket.is_anonymous is False
    assert ticket.name == "Maria Reader"


@pytest.mark.asyncio
async def test_anonymous_bookconcern_strips_identifiers_server_side(
    anon_client, test_db
):
    """Even if the client sends name/email/phone with is_anonymous=True, the
    server must null them out before persisting."""
    payload = _base_payload(
        category="bookConcern",
        is_anonymous=True,
        contact_method="none",
        name="Should Be Stripped",
        email="leaky@example.org",
        phone="555-555-5555",
        issue_description="Concern about a YA section book.",
    )
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()

    assert body["category"] == "book_concern"
    assert body["response_route"] == "reconsideration_committee"

    result = await test_db.execute(
        select(SupportTicket).where(SupportTicket.ticket_number == body["reference_number"])
    )
    ticket = result.scalar_one()
    assert ticket.is_anonymous is True
    assert ticket.name is None
    assert ticket.email is None
    assert ticket.phone is None
    assert ticket.issue_description == "Concern about a YA section book."


@pytest.mark.asyncio
async def test_under_13_path_no_identifiers_succeeds(anon_client, test_db):
    """COPPA-safe path: youthFamily + contact_method=none + no name/email is OK."""
    payload = _base_payload(
        category="youthFamily",
        contact_method="none",
        is_anonymous=True,
        name=None,
        email=None,
        phone=None,
        issue_description="Do you have books about dragons?",
    )
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["category"] == "youth"
    assert body["response_route"] == "youth_services"

    result = await test_db.execute(
        select(SupportTicket).where(SupportTicket.ticket_number == body["reference_number"])
    )
    ticket = result.scalar_one()
    assert ticket.name is None
    assert ticket.email is None
    assert ticket.is_anonymous is True


@pytest.mark.asyncio
async def test_email_method_requires_email(anon_client):
    """contact_method=email but email is null/empty returns a 4xx error."""
    payload = _base_payload(email=None)
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    # 400 (our explicit check) or 422 (pydantic validation if it landed)
    assert 400 <= response.status_code < 500
    # Some failure path must mention email
    body_text = response.text.lower()
    assert "email" in body_text


@pytest.mark.asyncio
async def test_escalation_modal_legacy_payload_still_works(anon_client, test_db):
    """The escalation modal (createSupportTicket) sends the pre-PR payload
    shape: snake_case category (``reference``), guide_title + step fields,
    name+email required, no is_anonymous flag. Verify it still persists."""
    payload = {
        "name": "Sam Smith",
        "email": "sam@example.org",
        "phone": "5551231234",
        "guide_title": "How to renew a hold",
        "step_number": 3,
        "total_steps": 5,
        "issue_description": "Stuck on step 3.",
        "contact_method": "email",
        "category": "reference",  # canonical enum, not camelCase
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    response = await anon_client.post("/api/v1/support/tickets", json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["category"] == "reference"
    assert body["sla_business_days"] == 1

    result = await test_db.execute(
        select(SupportTicket).where(SupportTicket.email == "sam@example.org")
    )
    ticket = result.scalar_one()
    assert ticket.guide_title == "How to renew a hold"
    assert ticket.step_number == 3
    assert ticket.is_anonymous is False  # default
