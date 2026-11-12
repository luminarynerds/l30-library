# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditAction, AuditLog
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.patron_communication import PatronNote
from app.models.user import PatronStatus, User, UserRole


async def get_token(client, user_data):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": user_data["email"], "password": user_data["password"]},
    )
    return response.json()["access_token"]


@pytest.fixture
async def secondary_patron(test_db):
    patron = User(
        email="secondary.workflow@example.com",
        password_hash="hashed",
        first_name="Second",
        last_name="Workflow",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        library_card="LSC910099",
    )
    test_db.add(patron)
    await test_db.commit()
    await test_db.refresh(patron)
    return patron


@pytest.mark.integration
class TestPatronDeduplicationWorkflow:
    async def test_detect_duplicates_by_name_address_email_phone(
        self, client, test_db, test_staff, test_staff_data, test_patron
    ):
        test_patron.first_name = "Jordan"
        test_patron.last_name = "Lee"
        test_patron.address = "100 Main St"
        test_patron.phone = "(555) 123-4567"
        test_patron.email = "jordan.lee@example.com"

        same_name_address = User(
            email="different@example.com",
            password_hash="hashed",
            first_name="Jordan",
            last_name="Lee",
            address="100 Main St",
            phone="555-000-0000",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            library_card="LSC910001",
        )
        # NOTE: no "same_email" duplicate here (case-variant of
        # test_patron's email, e.g. "JORDAN.LEE@example.com") -- that
        # scenario is no longer constructible. users.email_hash is a unique
        # blind index computed from the lowercased/stripped email (see
        # app/models/user.py's _recompute_email_hash before_insert/
        # before_update listener), so two DIFFERENT user rows can never
        # share a normalized email; inserting one raises
        # UniqueViolationError on ix_users_email_hash. That also means
        # patrons_account.py's `dup.email.lower() == patron.email.lower()`
        # match_type="email" branch is unreachable for any two live rows --
        # confirmed via full traceback + reading the blind-index event
        # listener. Not a bug to fix here (the uniqueness constraint is the
        # correct, stronger behavior); flagging as a product note: that
        # duplicate-detection branch may be effectively dead code now, or
        # only relevant for legacy pre-constraint data.
        same_phone = User(
            email="phone.match@example.com",
            password_hash="hashed",
            first_name="Taylor",
            last_name="Smith",
            phone="5551234567",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
            library_card="LSC910003",
        )
        test_db.add_all([same_name_address, same_phone])
        await test_db.commit()

        token = await get_token(client, test_staff_data)
        response = await client.get(
            f"/api/v1/staff/patrons/{test_patron.id}/duplicates",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        by_type = {item["match_type"] for item in response.json()["duplicates"]}
        # patrons_account.py's duplicate-match logic only ever produces
        # "name" (first+last match), "email" (exact email match), or
        # "phone" (digits-only match) -- there is no distinct
        # "name_address" match_type.
        assert "name" in by_type
        assert "phone" in by_type

    async def test_merge_preserves_history_notes_flags_and_active_checkouts(
        self, client, test_db, test_admin, test_admin_data, test_patron, test_catalog_item
    ):
        test_patron.patron_status = PatronStatus.ACTIVE
        primary_checkout = Checkout(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=7),
        )
        secondary = User(
            email="secondary.merge@example.com",
            password_hash="hashed",
            first_name="Second",
            last_name="Patron",
            role=UserRole.PATRON,
            patron_status=PatronStatus.BLOCKED,
            is_active=True,
            email_verified=True,
            library_card="LSC910010",
        )
        test_db.add_all([primary_checkout, secondary])
        await test_db.flush()

        secondary_checkout = Checkout(
            user_id=secondary.id,
            item_id=test_catalog_item.id,
            status=CheckoutStatus.active,
            checked_out_at=datetime.now(),
            due_date=datetime.now() + timedelta(days=10),
        )
        secondary_hold = Hold(
            user_id=secondary.id,
            item_id=test_catalog_item.id,
            status=HoldStatus.pending,
            position=1,
        )
        secondary_fine = Fine(
            user_id=secondary.id,
            fine_type=FineType.overdue,
            status=FineStatus.unpaid,
            amount=Decimal("3.50"),
            amount_paid=Decimal("0.00"),
            description="merge-test",
        )
        secondary_note = PatronNote(
            patron_id=secondary.id,
            author_id=None,
            content="Needs large print",
        )
        test_db.add_all([secondary_checkout, secondary_hold, secondary_fine, secondary_note])
        await test_db.commit()

        token = await get_token(client, test_admin_data)
        merge_response = await client.post(
            "/api/v1/staff/patrons/merge",
            json={"primary_patron_id": test_patron.id, "secondary_patron_id": secondary.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert merge_response.status_code == 200
        payload = merge_response.json()
        assert payload["checkouts_transferred"] == 1
        assert payload["holds_transferred"] == 1
        assert payload["fines_transferred"] == 1
        assert payload["history_transferred"] == 1

        await test_db.refresh(test_patron)
        assert test_patron.patron_status == PatronStatus.BLOCKED

        checkout_rows = (
            (await test_db.execute(select(Checkout).where(Checkout.user_id == test_patron.id)))
            .scalars()
            .all()
        )
        assert len(checkout_rows) == 2

        moved_note = (
            await test_db.execute(
                select(PatronNote).where(PatronNote.content == "Needs large print")
            )
        ).scalar_one()
        assert moved_note.patron_id == test_patron.id

    async def test_merge_preview_is_confirmation_step(
        self, client, test_admin, test_admin_data, test_patron, secondary_patron
    ):
        token = await get_token(client, test_admin_data)
        response = await client.post(
            "/api/v1/staff/patrons/merge/preview",
            json={"primary_patron_id": test_patron.id, "secondary_patron_id": secondary_patron.id},
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["primary_patron"]["id"] == test_patron.id
        assert data["secondary_patron"]["id"] == secondary_patron.id

    async def test_merge_is_reversible_via_audit_trail(
        self, client, test_db, test_admin, test_admin_data, test_patron, secondary_patron
    ):
        token = await get_token(client, test_admin_data)
        merge_response = await client.post(
            "/api/v1/staff/patrons/merge",
            json={"primary_patron_id": test_patron.id, "secondary_patron_id": secondary_patron.id},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert merge_response.status_code == 200

        audit_log = (
            await test_db.execute(
                select(AuditLog)
                .where(AuditLog.action == AuditAction.PATRON_MERGE)
                .order_by(AuditLog.id.desc())
            )
        ).scalar_one()

        reversible_response = await client.get(
            f"/api/v1/admin/audit/{audit_log.id}/reversible",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert reversible_response.status_code == 200
        assert reversible_response.json()["is_reversible"] is True

        revert_response = await client.post(
            f"/api/v1/admin/audit/{audit_log.id}/revert",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert revert_response.status_code == 200
        assert revert_response.json()["success"] is True
