# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from sqlalchemy import select

from app.models.catalog import CatalogItem, ItemType
from app.models.circulation_policy import CirculationPolicy
from app.models.multi_branch import LibrarySystem
from app.models.user import User, UserRole
from app.services.circulation_policy import resolve
from app.services.import_service.service import ImportService


@pytest.mark.asyncio
async def test_imported_policy_resolves_at_lookup(db):
    """End-to-end: policy created via ImportService._create_policy is returned
    by the live circulation resolver for a matching user + item."""
    # 1. Create the sole LibrarySystem so get_default_library_system_id returns it.
    sys = LibrarySystem(code="E2E", name="E2E Lib")
    db.add(sys)
    await db.flush()

    # 2. Import a policy through the real create path (org-stamps via default lsid).
    await ImportService._create_policy(
        db, {"role": "staff", "item_type": "book", "loan_period_days": "7"}
    )
    await db.flush()

    # Confirm the row landed with the correct library_system_id.
    policy = (await db.execute(select(CirculationPolicy))).scalars().first()
    assert policy is not None, "_create_policy did not persist a row"
    assert policy.library_system_id == sys.id, (
        f"Policy stamped lsid={policy.library_system_id}, expected sys.id={sys.id}"
    )

    # 3. Build a matching User (staff, homed to the same system).
    staff = User(
        email="e2e-staff@x.org",
        first_name="E",
        last_name="2E",
        role=UserRole.STAFF,
        is_active=True,
        home_library_system_id=sys.id,
    )
    staff.password_hash = "x"
    db.add(staff)

    # 4. Build a matching CatalogItem (book, no binding).
    item = CatalogItem(title="E2E Book", item_type=ItemType.book)
    db.add(item)
    await db.flush()

    # 5. Call the live resolver; user has home_library_system_id, resolver picks it up.
    rp = await resolve(user=staff, item=item, db=db)
    assert rp.loan_period_days == 7, (
        f"Expected loan_period_days=7 from imported policy, got {rp.loan_period_days}"
    )
