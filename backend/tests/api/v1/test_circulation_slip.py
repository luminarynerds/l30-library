# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the staff circulation slip email endpoint.

Verifies:
- Auth + feature-flag overrides land an HTTP 200 with sent=True when the
  email service accepts the message
- A daily-cap miss (send_email returns False) surfaces as 200 with
  sent=False, never as a hard error -- the print path must not depend
  on email success
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1.auth import get_current_user
from app.api.v1.feature_guards import require_circulation_print_slip_enabled
from app.main import app
from app.models.catalog import CatalogItem
from app.models.circulation import Checkout, CheckoutStatus


@pytest.fixture
def slip_app_overrides(test_staff):
    """Bypass auth + feature guard for the slip endpoint."""
    app.dependency_overrides[get_current_user] = lambda: test_staff
    app.dependency_overrides[require_circulation_print_slip_enabled] = lambda: None
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(require_circulation_print_slip_enabled, None)


@pytest.fixture
async def seeded_checkout(test_db, test_patron):
    """Create a CatalogItem + Checkout owned by the test patron."""
    item = CatalogItem(
        title="The Library Book",
        author="Susan Orlean",
        isbn="9781476740195",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    now = datetime.now(timezone.utc)
    checkout = Checkout(
        user_id=test_patron.id,
        item_id=item.id,
        status=CheckoutStatus.active,
        checked_out_at=now,
        due_date=now + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.mark.asyncio
async def test_email_slip_sends_when_email_service_accepts(
    client, slip_app_overrides, seeded_checkout, monkeypatch
):
    """Happy path: send_email returns True -> response sent=True."""
    captured: dict = {}

    async def fake_send_email(**kwargs):
        captured.update(kwargs)
        return True

    monkeypatch.setattr(
        "app.api.v1.staff.circulation_slip.send_email", fake_send_email
    )

    response = await client.post(
        "/api/v1/staff/circulation/email-slip",
        json={"checkout_id": seeded_checkout.id},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sent"] is True
    assert "emailed" in body["message"].lower()
    # Verify we sent to the patron's address, not a masked variant, and
    # tagged the send so safeguards can dedup.
    assert captured["to_email"] == "testuser@example.com"
    assert captured["notification_type"] == "checkout_slip"
    assert captured["categories"] == ["checkout_slip"]
    assert "Library Book" in captured["html_content"]


@pytest.mark.asyncio
async def test_email_slip_returns_200_when_daily_cap_blocks_send(
    client, slip_app_overrides, seeded_checkout, monkeypatch
):
    """Cap-hit path: send_email returns False -> still 200, sent=False.

    The print side of the slip must not be blocked by transient email
    failures, so this endpoint never surfaces a cap miss as a 5xx.
    """
    async def fake_send_email(**_kwargs):
        return False

    monkeypatch.setattr(
        "app.api.v1.staff.circulation_slip.send_email", fake_send_email
    )

    response = await client.post(
        "/api/v1/staff/circulation/email-slip",
        json={"checkout_id": seeded_checkout.id},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["sent"] is False
    assert "print" in body["message"].lower()
