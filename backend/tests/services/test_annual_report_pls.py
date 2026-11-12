# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for annual report PLS financial data — ensures fabricated figures are not shipped.

Note: tests call _get_financial_data directly because _get_circulation_data has a
pre-existing COALESCE enum/varchar type mismatch that aborts the transaction on the
test DB, cascading all subsequent sections to return {} — making integration-path
assertions vacuous. That unrelated bug is out of scope here.
"""

import pytest
from datetime import date
from decimal import Decimal

from app.models.acquisition import Fund, FundStatus
from app.services.annual_report_service import AnnualReportService


@pytest.mark.asyncio
async def test_financial_fields_not_fabricated(db_session):
    """Finance fields derived from GL become None; only the real fines figure survives."""
    # Seed a Fund with a meaningful allocated_amount.
    # fiscal_year on Fund uses start_date.year; for FY2025 that is 2024 (July 2024 - June 2025).
    fund = Fund(
        code="TEST-GENERAL-2024",
        name="General Fund FY2025",
        fiscal_year=2024,
        allocated_amount=Decimal("500000.00"),
        status=FundStatus.ACTIVE,
    )
    db_session.add(fund)
    await db_session.commit()

    svc = AnnualReportService(db_session)
    fiscal_start = date(2024, 7, 1)
    fiscal_end = date(2025, 6, 30)

    result = await svc._get_financial_data(fiscal_start, fiscal_end)

    # The fabricated-equal revenue==expenditure==budget pattern must not appear
    revenue = result.get("total_operating_revenue")
    expenditure = result.get("total_operating_expenditure")
    assert not (
        revenue is not None
        and revenue != Decimal("0")
        and revenue == expenditure
    ), (
        f"revenue must not be fabricated as == expenditure == budget; "
        f"got revenue={revenue}, expenditure={expenditure}"
    )

    # No hardcoded ratio split for collections in expenditure_by_category
    exp_cat = result.get("expenditure_by_category") or {}
    assert exp_cat.get("collections") is None, (
        f"expenditure_by_category['collections'] must be None, got {exp_cat.get('collections')}"
    )

    # No contradiction: collection_expenditure must not be a fabricated 0
    assert result.get("collection_expenditure") is None, (
        f"collection_expenditure must be None (manual entry required), "
        f"got {result.get('collection_expenditure')}"
    )


@pytest.mark.asyncio
async def test_circulation_section_runs_on_postgres(db_session):
    """_get_circulation_data must not raise on Postgres due to COALESCE enum/varchar mismatch.

    Seeds a CatalogItem with a non-null item_type so COALESCE(enum, varchar) is
    actually evaluated by Postgres.  Without the cast(item_type, String) fix,
    Postgres raises "COALESCE types itemtype and character varying cannot be matched".
    """
    from app.models.catalog import CatalogItem, ItemType, ItemStatus, CatalogingStatus
    from app.models.inventory import ItemCopy
    from app.models.circulation import Checkout, CheckoutStatus
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    from datetime import datetime, timezone

    # Minimal user
    user = User(
        email="circ_test_user@example.com",
        password_hash=hash_password("TestPass123!"),
        first_name="Circ",
        last_name="Test",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    # CatalogItem with a non-null item_type (triggers the COALESCE type check on Postgres)
    item = CatalogItem(
        title="COALESCE Test Book",
        author="Test Author",
        status=ItemStatus.checked_out,
        item_type=ItemType.book,
        cataloging_status=CatalogingStatus.CATALOGED,
    )
    db_session.add(item)
    await db_session.flush()

    copy = ItemCopy(
        catalog_item_id=item.id,
        barcode="COALESCE-TEST-001",
        copy_number=1,
        condition="good",
    )
    db_session.add(copy)
    await db_session.flush()

    checkout = Checkout(
        user_id=user.id,
        item_id=item.id,          # legacy NOT NULL FK to catalog_items
        item_copy_id=copy.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime(2025, 6, 1, tzinfo=timezone.utc),
        due_date=datetime(2025, 6, 22, tzinfo=timezone.utc),
    )
    db_session.add(checkout)
    await db_session.commit()

    svc = AnnualReportService(db_session)
    data = await svc._get_circulation_data(date(2025, 1, 1), date(2025, 12, 31))
    # Without the cast fix the COALESCE error is swallowed and {} is returned.
    # Verify the section actually ran — the key is present in a successful run.
    assert "total_checkouts" in data, (
        f"_get_circulation_data returned {{}} — likely COALESCE enum/varchar error "
        f"was swallowed. Got: {data!r}"
    )


@pytest.mark.asyncio
async def test_program_section_runs_on_postgres(db_session):
    """_get_program_data must not raise UnboundLocalError (shadowing local import of Program).

    The bug: a local `from app.models.programs import Program` inside _get_program_data
    causes Python to treat Program as local throughout the function, so the earlier
    reference at `select(Program).where(...)` raises UnboundLocalError, which is
    swallowed and returns {}.  After the fix, the section must return a dict with
    the expected reporting keys.
    """
    svc = AnnualReportService(db_session)
    data = await svc._get_program_data(date(2025, 1, 1), date(2025, 12, 31))
    assert isinstance(data, dict), f"_get_program_data returned non-dict: {data!r}"
    assert "total_programs_offered" in data, (
        f"_get_program_data returned {{}} — likely UnboundLocalError on Program was "
        f"swallowed by the section except handler. Got: {data!r}"
    )


@pytest.mark.asyncio
async def test_generate_annual_report_persists_end_to_end(db_session):
    svc = AnnualReportService(db_session)
    report = await svc.generate_annual_report(
        fiscal_year=2025, state_code="OH", library_name="LSC", user_id=None
    )
    # Constructor must not crash (was raising TypeError: 'data_source_financial' invalid kwarg)
    assert report.id is not None
    # The invalid key must not exist on the model class
    assert not hasattr(type(report), "data_source_financial")
    # Finance section returns None for GL-sourced totals; ORM column default=0 applies
    # after flush so the persisted value may be Decimal("0") — that's fine, it was not
    # fabricated from a budget ratio. The important thing: it didn't crash.
    assert report.total_operating_revenue == Decimal("0") or report.total_operating_revenue is None


# ---------------------------------------------------------------------------
# Phase 0/1 — circulation definitions + ILL
# ---------------------------------------------------------------------------

async def _make_checkout(db_session, *, item_type, checked_out_at, renewal_count=0,
                         barcode, audience=None):
    """Seed a CatalogItem + ItemCopy + Checkout of the given item_type."""
    from app.models.catalog import CatalogItem, ItemType, ItemStatus, CatalogingStatus
    from app.models.inventory import ItemCopy
    from app.models.circulation import Checkout, CheckoutStatus
    from app.models.user import User, UserRole
    from app.core.security import hash_password
    from datetime import timedelta

    user = User(
        email=f"circ_{barcode}@example.com",
        password_hash=hash_password("TestPass123!"),
        first_name="Circ", last_name="Test", role=UserRole.PATRON,
        is_active=True, email_verified=True,
    )
    db_session.add(user)
    await db_session.flush()

    item = CatalogItem(
        title=f"Item {barcode}", author="A",
        status=ItemStatus.checked_out, item_type=item_type,
        cataloging_status=CatalogingStatus.CATALOGED, audience=audience,
    )
    db_session.add(item)
    await db_session.flush()

    copy = ItemCopy(catalog_item_id=item.id, barcode=barcode, copy_number=1, condition="good")
    db_session.add(copy)
    await db_session.flush()

    checkout = Checkout(
        user_id=user.id, item_id=item.id, item_copy_id=copy.id,
        status=CheckoutStatus.active, checked_out_at=checked_out_at,
        due_date=checked_out_at + timedelta(days=21), renewal_count=renewal_count,
    )
    db_session.add(checkout)
    await db_session.flush()
    return checkout


@pytest.mark.asyncio
async def test_total_circulation_includes_renewals(db_session):
    """PLS total circulation = checkouts + renewals (renewed checkouts counted once)."""
    from app.models.catalog import ItemType
    from datetime import datetime, timezone
    fy = datetime(2025, 3, 1, tzinfo=timezone.utc)
    await _make_checkout(db_session, item_type=ItemType.book, checked_out_at=fy, barcode="TC-1")
    await _make_checkout(db_session, item_type=ItemType.book, checked_out_at=fy,
                         renewal_count=2, barcode="TC-2")
    await db_session.commit()

    svc = AnnualReportService(db_session)
    data = await svc._get_circulation_data(date(2024, 7, 1), date(2025, 6, 30))

    assert data["total_checkouts"] == 2
    assert data["total_renewals"] == 1
    assert data["total_circulation"] == data["total_checkouts"] + data["total_renewals"]
    assert data["total_circulation"] == 3


@pytest.mark.asyncio
async def test_electronic_vs_physical_circulation(db_session):
    """Electronic circulation = ebook checkouts; physical = the rest."""
    from app.models.catalog import ItemType
    from datetime import datetime, timezone
    fy = datetime(2025, 3, 1, tzinfo=timezone.utc)
    for i in range(2):
        await _make_checkout(db_session, item_type=ItemType.ebook, checked_out_at=fy, barcode=f"EC-E{i}")
    for i in range(3):
        await _make_checkout(db_session, item_type=ItemType.book, checked_out_at=fy, barcode=f"EC-P{i}")
    await db_session.commit()

    svc = AnnualReportService(db_session)
    data = await svc._get_circulation_data(date(2024, 7, 1), date(2025, 6, 30))

    assert data["electronic_circulation"] == 2
    assert data["physical_circulation"] == 3


@pytest.mark.asyncio
async def test_ill_counts_by_type(db_session):
    """ILL loaned/borrowed = ILLRequests by request_type with completed_at inside the FY."""
    from app.models.interlibrary_loan import ILLRequest, ILLRequestType, ILLRequestStatus
    from datetime import datetime, timezone

    def ill(rtype, completed):
        return ILLRequest(request_type=rtype, title="ILL Item",
                          status=ILLRequestStatus.completed, completed_at=completed)

    in_fy = datetime(2025, 3, 1, tzinfo=timezone.utc)
    out_fy = datetime(2023, 1, 1, tzinfo=timezone.utc)
    db_session.add_all([
        ill(ILLRequestType.lend, in_fy),
        ill(ILLRequestType.lend, in_fy),
        ill(ILLRequestType.borrow, in_fy),
        ill(ILLRequestType.borrow, in_fy),
        ill(ILLRequestType.borrow, in_fy),
        ill(ILLRequestType.borrow, out_fy),  # outside FY — must not count
    ])
    await db_session.commit()

    svc = AnnualReportService(db_session)
    data = await svc._get_ill_data(date(2024, 7, 1), date(2025, 6, 30))

    assert data["items_loaned_to_other_libraries"] == 2
    assert data["items_borrowed_from_other_libraries"] == 3


# ---------------------------------------------------------------------------
# Phase 2 — children's circulation + MLS-librarian FTE
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_childrens_circulation(db_session):
    """Children's circulation counts only checkouts of audience=children items."""
    from app.models.catalog import ItemType, Audience
    from datetime import datetime, timezone
    fy = datetime(2025, 3, 1, tzinfo=timezone.utc)
    for i in range(3):
        await _make_checkout(db_session, item_type=ItemType.book, checked_out_at=fy,
                             barcode=f"CH-{i}", audience=Audience.children)
    for i in range(2):  # adult items must not count
        await _make_checkout(db_session, item_type=ItemType.book, checked_out_at=fy,
                             barcode=f"AD-{i}", audience=Audience.adult)
    await db_session.commit()

    svc = AnnualReportService(db_session)
    data = await svc._get_circulation_data(date(2024, 7, 1), date(2025, 6, 30))
    assert data["childrens_circulation"] == 3


async def _make_staff_shift(db_session, *, has_mls, hours, barcode):
    from app.models.user import User, UserRole
    from app.models.staff_schedule_fairness import StaffShift, FairnessShiftType, ShiftStatus
    from app.core.security import hash_password
    from datetime import date as _date, time
    u = User(
        email=f"staff_{barcode}@example.com", password_hash=hash_password("TestPass123!"),
        first_name="S", last_name=barcode, role=UserRole.STAFF,
        is_active=True, email_verified=True, has_mls=has_mls,
    )
    db_session.add(u)
    await db_session.flush()
    shift = StaffShift(
        branch_id=1, staff_id=u.id, shift_date=_date(2025, 3, 1),
        shift_type=FairnessShiftType.FULL_DAY, status=ShiftStatus.COMPLETED,
        scheduled_start=time(9, 0), scheduled_end=time(17, 0),
        scheduled_hours=hours, actual_hours=hours,
    )
    db_session.add(shift)
    await db_session.flush()
    return u


@pytest.mark.asyncio
async def test_mls_librarian_fte_is_subset(db_session):
    """MLS-librarian FTE counts only has_mls staff and is < total librarian FTE."""
    await _make_staff_shift(db_session, has_mls=True, hours=2080.0, barcode="MLS")
    await _make_staff_shift(db_session, has_mls=False, hours=1040.0, barcode="NON")
    await db_session.commit()

    svc = AnnualReportService(db_session)
    data = await svc._get_staff_data(date(2024, 7, 1), date(2025, 6, 30))
    assert data["mls_librarian_fte"] is not None
    assert float(data["mls_librarian_fte"]) == 1.0          # 2080 / 2080 divisor
    assert data["mls_librarian_fte"] < data["librarian_fte"]  # subset of 1.5


# ---------------------------------------------------------------------------
# Phase 0 Task 0.4 — definition pins for visits / reference / attendance
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_total_library_visits_from_door_count_source(db_session):
    """PLS visits = in-person door count (VisitStatistics.total_visits), not web traffic."""
    from app.models.usage_statistics import VisitStatistics
    from datetime import date as _date
    db_session.add(VisitStatistics(
        period_start=_date(2024, 7, 1), period_end=_date(2025, 6, 30),
        period_type="annual", total_visits=4321,
    ))
    await db_session.commit()
    svc = AnnualReportService(db_session)
    data = await svc._get_visitor_data(_date(2024, 7, 1), _date(2025, 6, 30))
    assert data["total_library_visits"] == 4321


@pytest.mark.asyncio
async def test_reference_questions_from_reference_stats(db_session):
    """PLS reference = ReferenceStatistics.total_questions."""
    from app.models.usage_statistics import ReferenceStatistics
    from datetime import date as _date
    db_session.add(ReferenceStatistics(
        period_start=_date(2024, 7, 1), period_end=_date(2025, 6, 30),
        period_type="annual", total_questions=210,
    ))
    await db_session.commit()
    svc = AnnualReportService(db_session)
    data = await svc._get_visitor_data(_date(2024, 7, 1), _date(2025, 6, 30))
    assert data["reference_questions_answered"] == 210


@pytest.mark.asyncio
async def test_program_attendance_counts_by_program_date(db_session):
    """PLS attendance counts attended registrations for programs HELD in the FY,
    not by when the patron registered (created_at)."""
    from app.models.program import (
        Program, ProgramRegistration, LibraryProgramType,
        ProgramAudience, ProgramStatus, ProgramRegistrationStatus,
    )
    from datetime import date as _date, time
    prog = Program(
        title="Storytime", program_type=LibraryProgramType.STORYTIME,
        audience=ProgramAudience.CHILDREN, program_date=_date(2025, 3, 1),
        start_time=time(10, 0), status=ProgramStatus.COMPLETED,
    )
    db_session.add(prog)
    await db_session.flush()
    # 2 attended (created_at defaults to "now", outside FY2025 — must still count)
    for _ in range(2):
        db_session.add(ProgramRegistration(
            program_id=prog.id, attended=True,
            status=ProgramRegistrationStatus.ATTENDED,
        ))
    # a no-show must not count
    db_session.add(ProgramRegistration(
        program_id=prog.id, attended=False,
        status=ProgramRegistrationStatus.REGISTERED,
    ))
    await db_session.commit()
    svc = AnnualReportService(db_session)
    data = await svc._get_program_data(_date(2024, 7, 1), _date(2025, 6, 30))
    assert data["total_program_attendance"] == 2
