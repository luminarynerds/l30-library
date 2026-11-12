# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.api.v1.inventory import (
    create_audit,
    create_copy,
    log_condition_change,
    scan_item,
    update_copy,
    withdraw_copy,
)
from app.models.catalog import ItemStatus
from app.models.circulation import Checkout, CheckoutStatus
from app.models.inventory import ConditionChange, ItemCondition, ItemCopy
from app.services.branch_service import BranchService
from app.services.call_number_service import CallNumberService
from app.schemas.inventory import (
    AuditCreate,
    AuditScanCreate,
    ConditionChangeCreate,
    ItemCopyCreate,
    ItemCopyUpdate,
    WithdrawRequest,
)


@pytest.mark.integration
async def test_item_copy_operations_workflow(test_db, test_staff, test_catalog_item, test_patron):
    """Validate core item-copy operations so each copy remains accurately tracked."""

    branch_service = BranchService(test_db)

    # Branch setup for assignment + transfer workflows
    system = await branch_service.create_library_system(code="CPY", name="Copy Workflow System")
    home_branch = await branch_service.create_branch(
        library_system_id=system.id,
        code="HOME",
        name="Home Branch",
    )
    destination_branch = await branch_service.create_branch(
        library_system_id=system.id,
        code="EAST",
        name="East Branch",
    )

    # 1) Add a new copy and assign it to a branch
    created_copy = await create_copy(
        ItemCopyCreate(
            catalog_item_id=test_catalog_item.id,
            barcode="COPY-OPS-001",
            condition=ItemCondition.GOOD,
            location="Adult Fiction A-1",
        ),
        db=test_db,
        current_user=test_staff,
    )
    assignment = await branch_service.assign_item_to_branch(
        item_copy_id=created_copy.id,
        branch_id=home_branch.id,
        shelving_location="Aisle 3 / Shelf B",
    )
    assert assignment.current_branch_id == home_branch.id
    assert assignment.shelving_location == "Aisle 3 / Shelf B"

    # 2) Transfer copy between branches + edit shelving location
    moved = await branch_service.update_item_location(
        item_copy_id=created_copy.id,
        current_branch_id=destination_branch.id,
        shelving_location="Aisle 1 / Shelf D",
        circulated=True,
    )
    assert moved is not None
    assert moved.current_branch_id == destination_branch.id
    assert moved.last_circulated_branch_id == destination_branch.id
    assert moved.shelving_location == "Aisle 1 / Shelf D"

    # 3) Change copy status/condition and ensure history is tracked
    await update_copy(
        created_copy.id,
        ItemCopyUpdate(condition=ItemCondition.FAIR, location="Adult Fiction A-2"),
        db=test_db,
        current_user=test_staff,
    )
    damage_change = await log_condition_change(
        created_copy.id,
        ConditionChangeCreate(
            new_condition=ItemCondition.DAMAGED,
            damage_description="Cover detached during check-in",
        ),
        db=test_db,
        current_user=test_staff,
    )
    assert damage_change.new_condition == ItemCondition.DAMAGED

    condition_history = await test_db.execute(
        select(ConditionChange)
        .where(ConditionChange.item_copy_id == created_copy.id)
        .order_by(ConditionChange.id.asc())
    )
    change_states = [row.new_condition for row in condition_history.scalars().all()]
    assert ItemCondition.FAIR in change_states
    assert ItemCondition.DAMAGED in change_states

    # 4) Edit call number (bib-level field backing copy labels/discovery)
    test_catalog_item.call_number = "GN NARUTO v.12"
    await test_db.commit()
    spine_label = CallNumberService.format_manga_spine_label(test_catalog_item.call_number)
    assert spine_label == "GN\nNARUTO\nv.12"

    # 5) "Print" barcode label validation by ensuring copy barcode stays lookup-ready
    refreshed_copy = await test_db.get(ItemCopy, created_copy.id)
    assert refreshed_copy is not None
    assert refreshed_copy.barcode == "COPY-OPS-001"

    # 6) View circulation history tied to this exact copy
    checkout_1 = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        item_copy_id=created_copy.id,
        status=CheckoutStatus.returned,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=14),
        due_date=datetime.now(timezone.utc) - timedelta(days=7),
        returned_at=datetime.now(timezone.utc) - timedelta(days=8),
    )
    checkout_2 = Checkout(
        user_id=test_patron.id,
        item_id=test_catalog_item.id,
        item_copy_id=created_copy.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(timezone.utc) - timedelta(days=2),
        due_date=datetime.now(timezone.utc) + timedelta(days=19),
    )
    test_db.add_all([checkout_1, checkout_2])
    await test_db.commit()

    history_result = await test_db.execute(
        select(Checkout)
        .where(Checkout.item_copy_id == created_copy.id)
        .order_by(Checkout.checked_out_at.asc())
    )
    history = history_result.scalars().all()
    assert len(history) == 2
    assert history[0].status == CheckoutStatus.returned
    assert history[1].status == CheckoutStatus.active

    # 7) Mark withdrawn + replace lost copy with new barcode on same bib
    withdrawn_copy = await withdraw_copy(
        created_copy.id,
        WithdrawRequest(reason="Lost during annual inventory"),
        db=test_db,
        current_user=test_staff,
    )
    assert withdrawn_copy.condition == ItemCondition.WITHDRAWN

    replacement_copy = await create_copy(
        ItemCopyCreate(
            catalog_item_id=test_catalog_item.id,
            barcode="COPY-OPS-002",
            condition=ItemCondition.GOOD,
            location="Adult Fiction A-2",
        ),
        db=test_db,
        current_user=test_staff,
    )
    assert replacement_copy.catalog_item_id == test_catalog_item.id
    assert replacement_copy.barcode == "COPY-OPS-002"

    # 8) Inventory scan check-off on replacement copy
    audit = await create_audit(
        AuditCreate(name="Copy Ops Inventory", location_filter="Adult Fiction"),
        db=test_db,
        current_user=test_staff,
    )
    scan = await scan_item(
        audit.id,
        AuditScanCreate(barcode="COPY-OPS-002", found_at_location="Adult Fiction A-2"),
        db=test_db,
        current_user=test_staff,
    )
    assert scan.item_copy_id == replacement_copy.id

    await test_db.refresh(audit)
    assert audit.items_found >= 1

    # Final tracking assertion: both original and replacement copies are preserved with accurate states
    all_copies_result = await test_db.execute(
        select(ItemCopy)
        .where(ItemCopy.catalog_item_id == test_catalog_item.id)
        .order_by(ItemCopy.copy_number.asc())
    )
    all_copies = all_copies_result.scalars().all()
    assert [copy.barcode for copy in all_copies] == ["COPY-OPS-001", "COPY-OPS-002"]
    assert all_copies[0].condition == ItemCondition.WITHDRAWN
    assert all_copies[1].condition == ItemCondition.GOOD

    # Catalog-level status can still be maintained independently (e.g., missing/available at title level)
    test_catalog_item.status = ItemStatus.missing
    await test_db.commit()
    test_catalog_item.status = ItemStatus.available
    await test_db.commit()
