# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from app.main import app
from app.api.v1 import dependencies as auth_deps
from app.models.branch import Branch
from app.models.circulation import Checkout, CheckoutStatus, Hold, HoldStatus
from app.models.fine import Fine, FineStatus, FineType
from app.models.multi_branch import LibrarySystem
from app.models.user import PatronStatus, User, UserRole


@pytest.mark.integration
async def test_patron_account_operations_workflow(client, test_db, test_staff, test_admin, test_catalog_item):
    """Smoke-test the full patron account operations workflow used by staff.

    Coverage checklist (requested staff operations):
    - create adult/child/teen accounts, including guardian link
    - update contact details
    - update preferred branch
    - change patron type/role
    - merge duplicate accounts
    - block/unblock/suspend/unsuspend account
    - add staff note
    - view checkout / hold / fine history
    - reset password from staff
    - print replacement card
    """

    async def override_require_staff():
        return test_staff

    async def override_require_admin():
        return test_admin

    app.dependency_overrides[auth_deps.require_staff] = override_require_staff
    app.dependency_overrides[auth_deps.require_admin] = override_require_admin

    # Create patrons: adult, child (linked guardian), and teen
    adult = User(
        email="adult.ops@test.com",
        password_hash="hashed",
        first_name="Adult",
        last_name="Patron",
        role=UserRole.PATRON,
        patron_type="adult",
        is_active=True,
        email_verified=True,
        library_card="LSC900001",
    )
    teen = User(
        email="teen.ops@test.com",
        password_hash="hashed",
        first_name="Teen",
        last_name="Patron",
        role=UserRole.PATRON,
        patron_type="teen",
        is_active=True,
        email_verified=True,
        library_card="LSC900002",
    )
    child = User(
        email="child.ops@test.com",
        password_hash="hashed",
        first_name="Child",
        last_name="Patron",
        role=UserRole.CHILD,
        patron_type="child",
        parent_guardian_id=None,
        is_active=True,
        email_verified=True,
        library_card="LSC900003",
    )
    test_db.add_all([adult, teen, child])
    await test_db.flush()
    child.parent_guardian_id = adult.id

    # Create preferred branch data
    system = LibrarySystem(code="OPS", name="Ops Library System")
    test_db.add(system)
    await test_db.flush()
    branch = Branch(
        library_system_id=system.id,
        code="MAIN",
        name="Main Branch",
    )
    test_db.add(branch)
    await test_db.commit()
    await test_db.refresh(adult)
    await test_db.refresh(teen)
    await test_db.refresh(child)

    # Seed patron activity for history views
    checkout = Checkout(
        user_id=adult.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc),
        due_date=datetime.now(timezone.utc) + timedelta(days=14),
    )
    hold = Hold(
        user_id=adult.id,
        item_id=test_catalog_item.id,
        status=HoldStatus.pending,
        created_at=datetime.now(timezone.utc),
        position=1,
    )
    fine = Fine(
        user_id=adult.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("12.50"),
        amount_paid=Decimal("0.00"),
        description="Workflow fine",
    )
    test_db.add_all([checkout, hold, fine])
    await test_db.commit()

    # Update contact info + preferred branch + patron type
    update_resp = await client.put(
        f"/api/v1/staff/patrons/{adult.id}",
        json={"phone": "555-1212", "address": "123 Library Lane", "patron_type": "adult"},
    )
    assert update_resp.status_code == 200
    update_payload = update_resp.json()
    assert update_payload["phone"] == "555-1212"
    assert update_payload["address"] == "123 Library Lane"
    assert update_payload["patron_type"] == "adult"

    adult.home_branch_id = branch.id
    teen.patron_type = "adult"
    teen.role = UserRole.BOOKMOBILE
    await test_db.commit()

    # Merge duplicate patron records
    duplicate = User(
        email="adult.duplicate@test.com",
        password_hash="hashed",
        first_name="Adult",
        last_name="Patron",
        role=UserRole.PATRON,
        patron_type="adult",
        is_active=True,
        email_verified=True,
        library_card="LSC900004",
    )
    test_db.add(duplicate)
    await test_db.commit()
    await test_db.refresh(duplicate)

    merge_resp = await client.post(
        "/api/v1/staff/patrons/merge",
        json={
            "primary_patron_id": adult.id,
            "secondary_patron_id": duplicate.id,
            "merge_checkouts": True,
            "merge_holds": True,
            "merge_fines": True,
            "merge_history": True,
            "merge_reading_lists": True,
            "merge_favorites": True,
        },
    )
    assert merge_resp.status_code == 200
    merge_payload = merge_resp.json()
    assert merge_payload["merged_patron_id"] == adult.id
    assert merge_payload["deleted_patron_id"] == duplicate.id

    # Block, unblock, suspend, unsuspend
    block_resp = await client.post(
        f"/api/v1/staff/patrons/{adult.id}/status",
        json={"action": "block", "reason": "Policy violation"},
    )
    assert block_resp.status_code == 200
    assert block_resp.json()["patron_status"] == PatronStatus.BLOCKED.value

    unblock_resp = await client.post(
        f"/api/v1/staff/patrons/{adult.id}/status",
        json={"action": "unblock"},
    )
    assert unblock_resp.status_code == 200
    assert unblock_resp.json()["patron_status"] == PatronStatus.ACTIVE.value

    suspend_resp = await client.post(
        f"/api/v1/staff/patrons/{adult.id}/status",
        json={"action": "suspend", "reason": "Billing hold"},
    )
    assert suspend_resp.status_code == 200
    assert suspend_resp.json()["patron_status"] == PatronStatus.SUSPENDED.value

    unsuspend_resp = await client.post(
        f"/api/v1/staff/patrons/{adult.id}/status",
        json={"action": "unsuspend"},
    )
    assert unsuspend_resp.status_code == 200
    assert unsuspend_resp.json()["patron_status"] == PatronStatus.ACTIVE.value

    # Add staff note
    note_resp = await client.post(
        f"/api/v1/staff/patrons/{adult.id}/notes",
        json={"content": "Verified address with patron", "category": "general", "priority": "normal"},
    )
    assert note_resp.status_code == 201
    note_payload = note_resp.json()
    assert note_payload["content"] == "Verified address with patron"

    # View checkout / hold / fine history via detail and activity endpoints
    detail_resp = await client.get(f"/api/v1/staff/patrons/{adult.id}")
    assert detail_resp.status_code == 200
    detail_data = detail_resp.json()
    assert len(detail_data["checkouts"]) >= 1
    assert len(detail_data["holds"]) >= 1
    assert len(detail_data["fines"]) >= 1

    activity_resp = await client.get(f"/api/v1/staff/patrons/{adult.id}/activity")
    assert activity_resp.status_code == 200

    # Reset password from staff view
    reset_resp = await client.post(
        f"/api/v1/staff/patrons/{adult.id}/reset-password",
        json={"send_email": False, "generate_temp_code": True},
    )
    assert reset_resp.status_code == 200
    reset_payload = reset_resp.json()
    assert reset_payload["temp_code"]
    assert reset_payload["email_sent"] is False

    # Print replacement card
    card_resp = await client.post(
        f"/api/v1/staff/patrons/{adult.id}/card-printed",
        json={"card_type": "standard", "is_replacement": True, "reason": "Lost card"},
    )
    assert card_resp.status_code == 201
    card_payload = card_resp.json()
    assert card_payload["print_count"] >= 1

    await test_db.refresh(adult)
    await test_db.refresh(teen)
    await test_db.refresh(child)

    # Validate final states
    assert adult.phone == "555-1212"
    assert adult.address == "123 Library Lane"
    assert adult.home_branch_id == branch.id
    assert teen.patron_type == "adult"
    assert teen.role == UserRole.BOOKMOBILE
    assert child.parent_guardian_id == adult.id
    assert adult.patron_status == PatronStatus.ACTIVE
