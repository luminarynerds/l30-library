"""Regression tests for multi-copy check-in (MultipleResultsFound crash) and
the quick-checkout copy-binding that causes it.

See fix/circ-checkin-multiple-rows. checkin_by_barcode used to resolve the active
checkout by item_id (the title), so a multi-copy title with >1 copy out returned
multiple rows and scalar_one_or_none() raised MultipleResultsFound. The companion
defect: quick-checkout never recorded item_copy_id, producing the ambiguous data.
"""
from datetime import datetime, timedelta, timezone

import pytest

pytestmark = pytest.mark.asyncio


async def _make_item_with_copies(db, barcodes, title="Multi Copy Title"):
    from app.models.catalog import CatalogItem, ItemStatus
    from app.models.inventory import ItemCopy

    item = CatalogItem(
        title=title,
        author="Test Author",
        status=ItemStatus.available,
        call_number="MC-TEST",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    copies = []
    for i, bc in enumerate(barcodes, start=1):
        c = ItemCopy(catalog_item_id=item.id, barcode=bc, copy_number=i, condition="good")
        db.add(c)
        copies.append(c)
    await db.commit()
    for c in copies:
        await db.refresh(c)
    return item, copies


async def _make_patron(db, email):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    u = User(
        email=email,
        password_hash=hash_password("TestPassword123!"),
        first_name="Pat",
        last_name="Ron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _make_checkout(db, user_id, item_id, item_copy_id, status=None, days_out=0, due_in=21):
    from app.models.circulation import Checkout, CheckoutStatus

    st = status or CheckoutStatus.active
    out = datetime.now(timezone.utc) - timedelta(days=days_out)
    co = Checkout(
        user_id=user_id,
        item_id=item_id,
        item_copy_id=item_copy_id,
        status=st,
        checked_out_at=out,
        due_date=out + timedelta(days=due_in),
    )
    db.add(co)
    await db.commit()
    await db.refresh(co)
    return co


async def test_checkin_multicopy_title_does_not_crash(staff_client, test_db):
    """Two copies of one title both out: checking in one barcode must not raise
    MultipleResultsFound, and must close THAT copy's checkout only."""
    from app.models.circulation import CheckoutStatus

    item, (copy1, copy2) = await _make_item_with_copies(test_db, ["MC-1", "MC-2"])
    pa = await _make_patron(test_db, "mc_a@example.com")
    pb = await _make_patron(test_db, "mc_b@example.com")
    # Mirror prod: the active-only partial unique index ix_active_item_checkout
    # permits at most one ACTIVE checkout per title, so the second copy is out
    # as OVERDUE. Both are status IN (active, overdue), which is what check-in
    # scans -- the source of the MultipleResultsFound crash.
    co1 = await _make_checkout(test_db, pa.id, item.id, copy1.id, status=CheckoutStatus.active)
    co2 = await _make_checkout(
        test_db, pb.id, item.id, copy2.id,
        status=CheckoutStatus.overdue, days_out=30, due_in=21,
    )

    resp = await staff_client.post(
        "/api/v1/staff/checkin-barcode", params={"barcode": "MC-1"}
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(co1)
    await test_db.refresh(co2)
    assert co1.status == CheckoutStatus.returned, "scanned copy should be returned"
    assert co2.status == CheckoutStatus.overdue, "the other copy must be untouched"


async def test_checkin_legacy_null_bound_checkout(staff_client, test_db):
    """A pre-fix checkout with item_copy_id NULL must still be checkin-able
    (fallback path), not 'No active checkout'."""
    item, (copy1,) = await _make_item_with_copies(test_db, ["NB-1"], title="Single Copy")
    pa = await _make_patron(test_db, "nb_a@example.com")
    co = await _make_checkout(test_db, pa.id, item.id, None)  # legacy NULL binding

    resp = await staff_client.post(
        "/api/v1/staff/checkin-barcode", params={"barcode": "NB-1"}
    )
    assert resp.status_code == 200, resp.text

    from app.models.circulation import CheckoutStatus

    await test_db.refresh(co)
    assert co.status == CheckoutStatus.returned


async def test_quick_checkout_binds_item_copy_id(staff_client, test_db):
    """Quick checkout must record which physical copy went out, so check-in can
    later resolve the exact copy."""
    item, (copy1,) = await _make_item_with_copies(test_db, ["QC-1"], title="Bind Copy")
    pa = await _make_patron(test_db, "qc_a@example.com")

    resp = await staff_client.post(
        f"/api/v1/staff/patrons/{pa.id}/quick-checkout", json={"barcode": "QC-1"}
    )
    assert resp.status_code == 201, resp.text

    from sqlalchemy import select
    from app.models.circulation import Checkout, CheckoutStatus

    row = (
        await test_db.execute(
            select(Checkout).where(
                Checkout.user_id == pa.id,
                Checkout.status == CheckoutStatus.active,
            )
        )
    ).scalar_one()
    assert row.item_copy_id == copy1.id
