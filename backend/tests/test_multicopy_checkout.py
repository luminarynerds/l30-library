"""Multi-copy concurrent checkout (fix/multicopy-checkout).

The desk checkout path (unified_circulation_service.checkout_item) treated
availability at the TITLE level: an app guard blocked a 2nd active checkout of
the same item_id, and item.status flipped to checked_out on the first copy. So a
multi-copy title could only be checked out once. These tests assert copy-count
availability: every physical copy can be out concurrently; status flips to
checked_out only when the LAST copy goes out; a single-copy title still blocks a
second checkout; a patron can't take two copies of the same title.
"""
import pytest

pytestmark = pytest.mark.asyncio


async def _item_with_copies(db, barcodes, title):
    from app.models.catalog import CatalogItem, ItemStatus
    from app.models.inventory import ItemCopy

    item = CatalogItem(title=title, author="A", status=ItemStatus.available, call_number="MC")
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


async def _patron(db, email):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    u = User(
        email=email, password_hash=hash_password("TestPassword123!"),
        first_name="P", last_name="Q", role=UserRole.PATRON,
        is_active=True, email_verified=True,
    )
    db.add(u)
    await db.commit()
    await db.refresh(u)
    return u


async def _co(client, patron_id, barcode):
    return await client.post(
        f"/api/v1/staff/patrons/{patron_id}/quick-checkout", json={"barcode": barcode}
    )


async def _status(db, item_id):
    from sqlalchemy import select
    from app.models.catalog import CatalogItem
    return (await db.execute(select(CatalogItem.status).where(CatalogItem.id == item_id))).scalar()


async def test_two_copies_one_title_both_checkout(staff_client, test_db):
    """A 3-copy title can be checked out to 3 patrons; status flips to
    checked_out only when the last copy goes out."""
    from app.models.catalog import ItemStatus

    item, (c1, c2, c3) = await _item_with_copies(test_db, ["MCK-1", "MCK-2", "MCK-3"], "Bestseller")
    pa = await _patron(test_db, "mck_a@example.com")
    pb = await _patron(test_db, "mck_b@example.com")
    pc = await _patron(test_db, "mck_c@example.com")

    r1 = await _co(staff_client, pa.id, "MCK-1")
    assert r1.status_code == 201, r1.text
    assert await _status(test_db, item.id) == ItemStatus.available, "copies remain -> still available"

    r2 = await _co(staff_client, pb.id, "MCK-2")
    assert r2.status_code == 201, r2.text
    assert await _status(test_db, item.id) == ItemStatus.available, "1 copy left -> still available"

    r3 = await _co(staff_client, pc.id, "MCK-3")
    assert r3.status_code == 201, r3.text
    assert await _status(test_db, item.id) == ItemStatus.checked_out, "last copy out -> checked_out"


async def test_single_copy_blocks_second_checkout(staff_client, test_db):
    """A single-copy title still cannot go out twice."""
    item, (c1,) = await _item_with_copies(test_db, ["SCK-1"], "Only Copy")
    pa = await _patron(test_db, "sck_a@example.com")
    pb = await _patron(test_db, "sck_b@example.com")

    assert (await _co(staff_client, pa.id, "SCK-1")).status_code == 201
    r2 = await _co(staff_client, pb.id, "SCK-1")
    assert r2.status_code >= 400, "second checkout of the only copy must be blocked"


async def test_same_patron_cannot_take_two_copies(staff_client, test_db):
    """One patron cannot hold two copies of the same title."""
    item, (c1, c2) = await _item_with_copies(test_db, ["DCK-1", "DCK-2"], "Two Copies")
    pa = await _patron(test_db, "dck_a@example.com")

    assert (await _co(staff_client, pa.id, "DCK-1")).status_code == 201
    r2 = await _co(staff_client, pa.id, "DCK-2")
    assert r2.status_code >= 400, "same patron taking a 2nd copy of the title must be blocked"


# ---------------------------------------------------------------------------
# Holds x multi-copy (fix/holds-multicopy): a ready hold reserves exactly ONE
# copy; the remaining copies keep circulating, and the title status is derived
# from copies - loans - reservations instead of being frozen by place_hold.
# ---------------------------------------------------------------------------


async def _place_hold(db, patron, item):
    from sqlalchemy import select

    from app.models.circulation import Hold
    from app.services.unified_circulation_service import place_hold

    hold_response, _ = await place_hold(patron, item.id, db)
    await db.commit()
    return (
        await db.execute(select(Hold).where(Hold.id == hold_response.id))
    ).scalar_one()


async def test_hold_on_multicopy_title_keeps_other_copies_available(test_db):
    """A ready hold reserves one copy; the others circulate until none is free."""
    from app.core.error_codes import ErrorCode
    from app.core.exceptions import ConflictError
    from app.models.catalog import ItemStatus
    from app.models.circulation import HoldStatus
    from app.services.checkout_service import create_checkout

    item, _copies = await _item_with_copies(test_db, ["HMC-1", "HMC-2", "HMC-3"], "Held Bestseller")
    holder = await _patron(test_db, "hmc_holder@example.com")
    pa = await _patron(test_db, "hmc_a@example.com")
    pb = await _patron(test_db, "hmc_b@example.com")
    pc = await _patron(test_db, "hmc_c@example.com")

    hold = await _place_hold(test_db, holder, item)
    assert hold.status == HoldStatus.ready, "free copy exists -> hold readies immediately"
    assert await _status(test_db, item.id) == ItemStatus.available, "2 free copies remain"

    await create_checkout(pa, item.id, test_db)
    await test_db.commit()
    assert await _status(test_db, item.id) == ItemStatus.available, "1 free copy remains"

    await create_checkout(pb, item.id, test_db)
    await test_db.commit()
    assert await _status(test_db, item.id) == ItemStatus.on_hold, "only the reserved copy is left"

    with pytest.raises(ConflictError) as exc_info:
        await create_checkout(pc, item.id, test_db)
    assert exc_info.value.code == ErrorCode.ITEM_ON_HOLD, "remaining copy is reserved for the hold"
    await test_db.rollback()


async def test_ready_hold_reserves_the_last_copy_for_its_owner(test_db):
    """A single-copy title with a ready hold blocks walk-ins but not the owner."""
    from app.core.exceptions import ConflictError
    from app.models.catalog import ItemStatus
    from app.models.circulation import HoldStatus
    from app.services.checkout_service import create_checkout

    item, _ = await _item_with_copies(test_db, ["HSC-1"], "Single Held")
    holder = await _patron(test_db, "hsc_holder@example.com")
    walkin = await _patron(test_db, "hsc_walkin@example.com")

    hold = await _place_hold(test_db, holder, item)
    assert hold.status == HoldStatus.ready
    assert await _status(test_db, item.id) == ItemStatus.on_hold, "only copy reserved -> on_hold"

    with pytest.raises(ConflictError):
        await create_checkout(walkin, item.id, test_db)
    # Rollback expires committed ORM instances; refresh before reuse.
    await test_db.rollback()
    await test_db.refresh(holder)
    await test_db.refresh(item)
    await test_db.refresh(hold)

    await create_checkout(holder, item.id, test_db)
    await test_db.commit()
    await test_db.refresh(hold)
    assert hold.status == HoldStatus.fulfilled, "owner checkout fulfills their ready hold"
    assert await _status(test_db, item.id) == ItemStatus.checked_out


async def test_return_releases_copy_to_circulation_while_hold_captures_one(test_db):
    """3 copies all out + 1 pending hold: the first return captures a copy for
    the hold; the second return frees a copy for general circulation."""
    from app.models.catalog import ItemStatus
    from app.models.circulation import HoldStatus
    from app.services.checkout_service import create_checkout, return_checkout

    item, _ = await _item_with_copies(test_db, ["HRT-1", "HRT-2", "HRT-3"], "All Out")
    pa = await _patron(test_db, "hrt_a@example.com")
    pb = await _patron(test_db, "hrt_b@example.com")
    pc = await _patron(test_db, "hrt_c@example.com")
    waiting = await _patron(test_db, "hrt_wait@example.com")

    co_a = await create_checkout(pa, item.id, test_db)
    co_b = await create_checkout(pb, item.id, test_db)
    await create_checkout(pc, item.id, test_db)
    await test_db.commit()
    assert await _status(test_db, item.id) == ItemStatus.checked_out

    hold = await _place_hold(test_db, waiting, item)
    assert hold.status == HoldStatus.pending, "no free copy -> hold queues"

    await return_checkout(co_a.checkout, test_db, pa)
    await test_db.commit()
    await test_db.refresh(hold)
    assert hold.status == HoldStatus.ready, "first return captures the copy for the hold"
    assert await _status(test_db, item.id) == ItemStatus.on_hold, "captured copy + 2 out -> nothing free"

    await return_checkout(co_b.checkout, test_db, pb)
    await test_db.commit()
    assert await _status(test_db, item.id) == ItemStatus.available, "second return frees a circulating copy"


async def test_staff_placed_hold_readies_when_copy_free(staff_client, test_db):
    """A staff-placed hold on an on-shelf copy readies immediately instead of
    sitting pending forever, and the other copy keeps circulating."""
    from sqlalchemy import select

    from app.models.catalog import ItemStatus
    from app.models.circulation import Hold, HoldStatus

    item, _ = await _item_with_copies(test_db, ["SPH-1", "SPH-2"], "Staff Held")
    patron = await _patron(test_db, "sph_patron@example.com")

    resp = await staff_client.post(
        f"/api/v1/staff/patrons/{patron.id}/place-hold", json={"item_id": item.id}
    )
    assert resp.status_code == 201, resp.text
    hold = (
        await test_db.execute(
            select(Hold).where(Hold.user_id == patron.id, Hold.item_id == item.id)
        )
    ).scalar_one()
    assert hold.status == HoldStatus.ready
    assert await _status(test_db, item.id) == ItemStatus.available, "second copy still circulates"
