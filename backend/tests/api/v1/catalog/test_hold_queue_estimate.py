# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Hold-queue wait estimate uses the item type's real loan period.

Pins the fix for the hardcoded ``* 21`` in
``GET /catalog/items/{id}/hold-queue``: the estimate now multiplies by the
generic circulation-policy loan period for the item's type, falling back to
``DEFAULT_LOAN_DAYS`` (21) when no policy covers it.
"""
from __future__ import annotations

from httpx import AsyncClient

from app.models.catalog import (
    CatalogItem,
    CatalogingStatus,
    ItemStatus,
    ItemType,
    SensitivityLevel,
)
from app.models.circulation import Hold, HoldStatus
from app.models.circulation_policy import CirculationPolicy
from app.models.inventory import ItemCopy
from app.models.multi_branch import LibrarySystem
from app.models.user import User, UserRole


async def _seed_queue(db, *, barcode_prefix: str) -> CatalogItem:
    item = CatalogItem(
        title=f"Queued {barcode_prefix}",
        author="A",
        item_type=ItemType.book,
        status=ItemStatus.checked_out,
        cataloging_status=CatalogingStatus.CATALOGED,
        sensitivity_level=SensitivityLevel.PUBLIC,
    )
    db.add(item)
    await db.flush()

    db.add(ItemCopy(catalog_item_id=item.id, barcode=f"{barcode_prefix}-1", copy_number=1))

    # Two distinct patrons: a single user can't hold the same item twice
    # (unique constraint ix_active_user_item_hold).
    for pos in (1, 2):
        user = User(
            email=f"{barcode_prefix}-{pos}@example.com",
            first_name="H",
            last_name="Q",
            role=UserRole.PATRON,
        )
        db.add(user)
        await db.flush()
        db.add(
            Hold(
                user_id=user.id,
                item_id=item.id,
                status=HoldStatus.pending if pos == 1 else HoldStatus.ready,
                position=pos,
            )
        )
    await db.flush()
    return item


async def test_estimate_falls_back_to_default_loan_days(
    public_client: AsyncClient, db_session
):
    item = await _seed_queue(db_session, barcode_prefix="hq-default")
    await db_session.commit()

    resp = await public_client.get(f"/api/v1/catalog/items/{item.id}/hold-queue")
    assert resp.status_code == 200
    body = resp.json()
    assert body["queue_size"] == 2
    assert body["total_copies"] == 1
    # (2 holds / 1 copy) * DEFAULT_LOAN_DAYS(21)
    assert body["estimated_wait_days"] == 42


async def test_estimate_uses_item_type_policy_loan_period(
    public_client: AsyncClient, db_session
):
    system = LibrarySystem(code="HQ", name="Hold Queue System")
    db_session.add(system)
    await db_session.flush()
    db_session.add(
        CirculationPolicy(
            library_system_id=system.id,
            item_type=ItemType.book,
            loan_period_days=7,
            active=True,
        )
    )
    item = await _seed_queue(db_session, barcode_prefix="hq-policy")
    await db_session.commit()

    resp = await public_client.get(f"/api/v1/catalog/items/{item.id}/hold-queue")
    assert resp.status_code == 200
    body = resp.json()
    # (2 holds / 1 copy) * policy loan period (7), not the old hardcoded 21
    assert body["estimated_wait_days"] == 14
