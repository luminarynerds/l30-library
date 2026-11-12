# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test for PO update path eager-loading vendor/fund.

Locks in the fix for the MissingGreenlet 500 on
PATCH /api/v1/acquisition/purchase-orders/{po_id}:

PurchaseOrderResponse.model_validate(po) touches po.vendor.name and
po.fund.name to populate the computed vendor_name/fund_name fields. If
the service fetches the PO without with_relationships=True, those
attributes lazy-load outside the greenlet at serialization time and
raise sqlalchemy.exc.MissingGreenlet, which surfaces as a 500 to the
EditPurchaseOrderModal staff UI.

See: backend/app/services/po_facade_service.py::update_purchase_order
"""

import pytest
from datetime import date
from decimal import Decimal
from sqlalchemy import select

from app.models.acquisition import (
    Fund,
    FundStatus,
    PurchaseOrder,
    PurchaseOrderStatus,
    Vendor,
)
from app.models.user import User, UserRole
from app.schemas.acquisition import PurchaseOrderResponse, PurchaseOrderUpdate
from app.services.po_facade_service import POFacadeService


async def _make_staff_user(db_session) -> User:
    """Get or create a staff user for service-level authorization."""
    result = await db_session.execute(
        select(User).where(User.role == UserRole.STAFF).limit(1)
    )
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        email="po-update-test-staff@example.com",
        password_hash="x",
        role=UserRole.STAFF,
        is_active=True,
        first_name="PO",
        last_name="Tester",
    )
    db_session.add(user)
    await db_session.flush()
    return user


async def _make_vendor(db_session, name: str) -> Vendor:
    result = await db_session.execute(
        select(Vendor).where(Vendor.name == name)
    )
    v = result.scalar_one_or_none()
    if v:
        return v
    v = Vendor(name=name, is_active=True)
    db_session.add(v)
    await db_session.flush()
    return v


async def _make_fund(db_session, code: str, name: str) -> Fund:
    result = await db_session.execute(select(Fund).where(Fund.code == code))
    f = result.scalar_one_or_none()
    if f:
        return f
    f = Fund(
        code=code,
        name=name,
        fiscal_year=2024,
        allocated_amount=Decimal("10000.00"),
        status=FundStatus.ACTIVE,
    )
    db_session.add(f)
    await db_session.flush()
    return f


@pytest.mark.asyncio
async def test_update_purchase_order_populates_vendor_and_fund_name(db_session):
    """
    PATCH update path must return populated vendor_name and fund_name.

    Before the fix (po fetched without with_relationships=True), this
    test would raise sqlalchemy.exc.MissingGreenlet at the final
    PurchaseOrderResponse.model_validate(po) call when the response
    schema reads po.vendor.name / po.fund.name.
    """
    vendor = await _make_vendor(db_session, "Ingram (update-test)")
    fund = await _make_fund(db_session, "UPDATE-TEST-FUND", "Update Test Fund")
    staff = await _make_staff_user(db_session)

    po = PurchaseOrder(
        po_number=f"PO-UPDATE-TEST-{date.today().strftime('%Y%m%d')}",
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        notes="initial notes",
        created_by_id=staff.id,
    )
    db_session.add(po)
    await db_session.commit()
    await db_session.refresh(po)
    po_id = po.id  # capture before expire so we don't lazy-reload outside greenlet
    db_session.expire(po)

    service = POFacadeService(db_session)
    result = await service.update_purchase_order(
        po_id=po_id,
        po_in=PurchaseOrderUpdate(notes="updated notes"),
        current_user=staff,
    )

    assert isinstance(result, PurchaseOrderResponse)
    assert result.notes == "updated notes"
    # The actual regression assertion: response carries non-empty
    # vendor_name and fund_name. Pre-fix this raised MissingGreenlet
    # during model_validate and never returned.
    assert result.vendor_name == "Ingram (update-test)"
    assert result.fund_name == "Update Test Fund"


@pytest.mark.asyncio
async def test_update_purchase_order_reflects_changed_vendor(db_session):
    """
    Switching vendor_id on a draft PO must surface the new vendor name.

    Without refreshing the vendor relationship after commit, the response
    would echo the old vendor name (stale relationship cache).
    """
    vendor_a = await _make_vendor(db_session, "Vendor A (update-test)")
    vendor_b = await _make_vendor(db_session, "Vendor B (update-test)")
    fund = await _make_fund(db_session, "UPDATE-TEST-FUND-2", "Update Test Fund 2")
    staff = await _make_staff_user(db_session)

    po = PurchaseOrder(
        po_number=f"PO-UPDATE-SWAP-{date.today().strftime('%Y%m%d')}",
        vendor_id=vendor_a.id,
        fund_id=fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=staff.id,
    )
    db_session.add(po)
    await db_session.commit()
    await db_session.refresh(po)
    po_id = po.id
    db_session.expire(po)

    service = POFacadeService(db_session)
    result = await service.update_purchase_order(
        po_id=po_id,
        po_in=PurchaseOrderUpdate(vendor_id=vendor_b.id),
        current_user=staff,
    )

    assert result.vendor_name == "Vendor B (update-test)"
    assert result.fund_name == "Update Test Fund 2"


@pytest.mark.asyncio
async def test_update_purchase_order_eager_loads_relationships(db_session, monkeypatch):
    """
    update_purchase_order must fetch the PO with with_relationships=True.

    Locks the fix in place against future regressions. The async lazy-load
    landmine (sqlalchemy.exc.MissingGreenlet) only surfaces against the
    Postgres+asyncpg driver in prod; SQLite+aiosqlite under pytest silently
    lazy-loads in sync context and masks the bug. Asserting the repo call
    signature catches the regression in either driver.
    """
    from app.services.repositories.po_repository import PORepository

    vendor = await _make_vendor(db_session, "Spy Vendor (update-test)")
    fund = await _make_fund(db_session, "SPY-FUND", "Spy Fund")
    staff = await _make_staff_user(db_session)

    po = PurchaseOrder(
        po_number=f"PO-SPY-{date.today().strftime('%Y%m%d')}",
        vendor_id=vendor.id,
        fund_id=fund.id,
        order_date=date.today(),
        status=PurchaseOrderStatus.DRAFT,
        created_by_id=staff.id,
    )
    db_session.add(po)
    await db_session.commit()
    await db_session.refresh(po)
    po_id = po.id

    captured_kwargs: list[dict] = []
    original = PORepository.get_purchase_order_by_id

    async def spy(db, target_po_id, **kwargs):
        captured_kwargs.append(kwargs)
        return await original(db, target_po_id, **kwargs)

    monkeypatch.setattr(
        PORepository,
        "get_purchase_order_by_id",
        staticmethod(spy),
    )

    service = POFacadeService(db_session)
    await service.update_purchase_order(
        po_id=po_id,
        po_in=PurchaseOrderUpdate(notes="spy"),
        current_user=staff,
    )

    # The initial fetch inside update_purchase_order must carry
    # with_relationships=True so PurchaseOrderResponse.model_validate
    # can read po.vendor.name / po.fund.name without a lazy load.
    assert len(captured_kwargs) >= 1, "expected at least one repo fetch"
    first_call = captured_kwargs[0]
    assert first_call.get("with_relationships") is True, (
        "update_purchase_order must call get_purchase_order_by_id with "
        "with_relationships=True to avoid MissingGreenlet on Postgres "
        f"during PurchaseOrderResponse serialization. Got kwargs={first_call}"
    )
