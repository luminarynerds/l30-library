# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for fine waiver workflow (Cluster G).

Covers:
- Auto-waive when amount <= $5 (staff role)
- Partial waiver math
- Pending-approval path when amount > $5 (staff role)
- Admin self-auto-waive at any amount
- requires_approval=true forces pending even for small amounts
- Approval flow happy path (admin)
- Approval flow role-gate fail (staff can't approve)
- Reject flow leaves fine untouched
- pii_access_log row created for waive + approve + reject
- Idempotency: 409 on already-fully-waived
- Amount > outstanding -> 400
"""

from datetime import datetime, timezone
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.pii_audit import PIIAccessLog
import time
from app.core.security import _TOKEN_VERIFY_CACHE, _get_token_hash, create_access_token
from app.models.fine import Fine, FineStatus, FineType
from app.models.fine_waiver import FineWaiver, FineWaiverStatus
from app.models.user import User


def _auth(user: User) -> dict[str, str]:
    # subject = user.id is what get_current_user expects; email/role go in
    # their dedicated claims.
    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )
    # Redis is unavailable in the test environment, so is_token_revoked falls
    # back to an in-memory cache and rejects unknown tokens fail-secure.
    # Pre-warm the cache so the freshly-minted test token verifies.
    _TOKEN_VERIFY_CACHE[_get_token_hash(token)] = time.monotonic()
    return {"Authorization": f"Bearer {token}"}


async def _make_fine(
    test_db, patron: User, amount: Decimal, paid: Decimal = Decimal("0.00")
) -> Fine:
    fine = Fine(
        user_id=patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid if paid == 0 else FineStatus.partial,
        amount=amount,
        amount_paid=paid,
        description="Test fine",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)
    return fine


@pytest.mark.asyncio
async def test_auto_waive_small_amount_by_staff(
    client: AsyncClient, test_db, test_patron, test_staff
):
    fine = await _make_fine(test_db, test_patron, Decimal("3.00"))
    resp = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "First-time goodwill"},
        headers=_auth(test_staff),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "waived"
    assert Decimal(body["amount_waived"]) == Decimal("3.00")
    assert Decimal(body["remaining_balance"]) == Decimal("0.00")
    assert body["waived_at"] is not None
    assert body["approved_by"] == test_staff.id

    # DB confirms fine + waiver state.
    refreshed = (
        await test_db.execute(select(Fine).where(Fine.id == fine.id))
    ).scalar_one()
    assert refreshed.status == FineStatus.waived
    assert refreshed.amount_paid == Decimal("3.00")
    waiver = (
        await test_db.execute(
            select(FineWaiver).where(FineWaiver.fine_id == fine.id)
        )
    ).scalar_one()
    assert waiver.status == FineWaiverStatus.waived


@pytest.mark.asyncio
async def test_partial_waiver_leaves_remaining_balance(
    client: AsyncClient, test_db, test_patron, test_staff
):
    fine = await _make_fine(test_db, test_patron, Decimal("4.50"))
    resp = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Half goodwill", "amount": "2.00"},
        headers=_auth(test_staff),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "waived"
    assert Decimal(body["amount_waived"]) == Decimal("2.00")
    assert Decimal(body["remaining_balance"]) == Decimal("2.50")

    refreshed = (
        await test_db.execute(select(Fine).where(Fine.id == fine.id))
    ).scalar_one()
    assert refreshed.status == FineStatus.partial
    assert refreshed.amount_paid == Decimal("2.00")


@pytest.mark.asyncio
async def test_large_amount_by_staff_goes_pending(
    client: AsyncClient, test_db, test_patron, test_staff
):
    fine = await _make_fine(test_db, test_patron, Decimal("12.00"))
    resp = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Damaged but repaired"},
        headers=_auth(test_staff),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "pending_approval"
    assert Decimal(body["remaining_balance"]) == Decimal("12.00")
    assert body["waived_at"] is None

    # Fine row untouched until approved.
    refreshed = (
        await test_db.execute(select(Fine).where(Fine.id == fine.id))
    ).scalar_one()
    assert refreshed.status == FineStatus.unpaid
    assert refreshed.amount_paid == Decimal("0.00")


@pytest.mark.asyncio
async def test_admin_auto_waives_at_any_amount(
    client: AsyncClient, test_db, test_patron, test_admin
):
    fine = await _make_fine(test_db, test_patron, Decimal("25.00"))
    resp = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Director override"},
        headers=_auth(test_admin),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "waived"


@pytest.mark.asyncio
async def test_requires_approval_forces_pending_even_for_small_amount(
    client: AsyncClient, test_db, test_patron, test_staff
):
    fine = await _make_fine(test_db, test_patron, Decimal("2.00"))
    resp = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Need a second look", "requires_approval": True},
        headers=_auth(test_staff),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "pending_approval"


@pytest.mark.asyncio
async def test_approve_flow_admin_happy_path(
    client: AsyncClient, test_db, test_patron, test_staff, test_admin
):
    fine = await _make_fine(test_db, test_patron, Decimal("20.00"))
    pending = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Hardship"},
        headers=_auth(test_staff),
    )
    waiver_id = pending.json()["waiver_id"]

    approved = await client.post(
        f"/api/v1/staff/fine-waivers/{waiver_id}/approve",
        json={"notes": "Looks legit"},
        headers=_auth(test_admin),
    )
    assert approved.status_code == 200, approved.text
    body = approved.json()
    assert body["status"] == "waived"
    assert Decimal(body["remaining_balance"]) == Decimal("0.00")
    assert body["approved_by"] == test_admin.id

    refreshed = (
        await test_db.execute(select(Fine).where(Fine.id == fine.id))
    ).scalar_one()
    assert refreshed.status == FineStatus.waived
    assert refreshed.amount_paid == Decimal("20.00")


@pytest.mark.asyncio
async def test_approve_role_gate_blocks_staff(
    client: AsyncClient, test_db, test_patron, test_staff
):
    fine = await _make_fine(test_db, test_patron, Decimal("10.00"))
    pending = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Big one"},
        headers=_auth(test_staff),
    )
    waiver_id = pending.json()["waiver_id"]
    resp = await client.post(
        f"/api/v1/staff/fine-waivers/{waiver_id}/approve",
        headers=_auth(test_staff),
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_reject_flow_leaves_fine_untouched(
    client: AsyncClient, test_db, test_patron, test_staff, test_admin
):
    fine = await _make_fine(test_db, test_patron, Decimal("15.00"))
    pending = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Suspicious"},
        headers=_auth(test_staff),
    )
    waiver_id = pending.json()["waiver_id"]
    resp = await client.post(
        f"/api/v1/staff/fine-waivers/{waiver_id}/reject",
        json={"notes": "Patron disputed it"},
        headers=_auth(test_admin),
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "rejected"
    assert Decimal(body["remaining_balance"]) == Decimal("15.00")

    refreshed = (
        await test_db.execute(select(Fine).where(Fine.id == fine.id))
    ).scalar_one()
    assert refreshed.status == FineStatus.unpaid
    assert refreshed.amount_paid == Decimal("0.00")


@pytest.mark.asyncio
async def test_pii_access_log_written_on_waive_and_approve(
    client: AsyncClient, test_db, test_patron, test_staff, test_admin
):
    fine = await _make_fine(test_db, test_patron, Decimal("9.00"))
    pending = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Will need approval"},
        headers=_auth(test_staff),
    )
    waiver_id = pending.json()["waiver_id"]
    await client.post(
        f"/api/v1/staff/fine-waivers/{waiver_id}/approve",
        headers=_auth(test_admin),
    )

    rows = (
        await test_db.execute(
            select(PIIAccessLog).order_by(PIIAccessLog.id)
        )
    ).scalars().all()
    waive_rows = [r for r in rows if "/waive" in r.endpoint]
    approve_rows = [r for r in rows if "/approve" in r.endpoint]
    assert len(waive_rows) == 1
    assert len(approve_rows) == 1
    assert waive_rows[0].additional_context["event_type"] == "fine.waive"
    assert (
        approve_rows[0].additional_context["event_type"]
        == "fine.waive_approve"
    )


@pytest.mark.asyncio
async def test_duplicate_waive_against_fully_waived_returns_409(
    client: AsyncClient, test_db, test_patron, test_staff
):
    fine = await _make_fine(test_db, test_patron, Decimal("2.00"))
    first = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Goodwill"},
        headers=_auth(test_staff),
    )
    assert first.status_code == 200
    dup = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Goodwill again"},
        headers=_auth(test_staff),
    )
    assert dup.status_code == 409


@pytest.mark.asyncio
async def test_amount_exceeds_outstanding_returns_400(
    client: AsyncClient, test_db, test_patron, test_staff
):
    fine = await _make_fine(test_db, test_patron, Decimal("4.00"))
    resp = await client.post(
        f"/api/v1/staff/fines/{fine.id}/waive",
        json={"reason": "Generous", "amount": "9.99"},
        headers=_auth(test_staff),
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_pending_queue_lists_only_pending(
    client: AsyncClient, test_db, test_patron, test_staff, test_admin
):
    fine_a = await _make_fine(test_db, test_patron, Decimal("8.00"))
    fine_b = await _make_fine(test_db, test_patron, Decimal("2.00"))
    # A goes pending.
    await client.post(
        f"/api/v1/staff/fines/{fine_a.id}/waive",
        json={"reason": "Needs review"},
        headers=_auth(test_staff),
    )
    # B auto-waives.
    await client.post(
        f"/api/v1/staff/fines/{fine_b.id}/waive",
        json={"reason": "Small fix"},
        headers=_auth(test_staff),
    )
    queue = await client.get(
        "/api/v1/staff/fine-waivers/pending",
        headers=_auth(test_admin),
    )
    assert queue.status_code == 200, queue.text
    body = queue.json()
    assert body["total_count"] == 1
    assert body["waivers"][0]["fine_id"] == fine_a.id
    assert body["waivers"][0]["status"] == "pending_approval"
