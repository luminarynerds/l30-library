# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for MigrationWizardService P0 bug fixes (2026-05-25)."""

import pytest

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.migration_job import MigrationJob, MigrationJobStatus, MigrationSourceSystem
from app.models.patron_category import PatronCategory
from app.models.user import User, UserRole
from app.services.migration_wizard_service import MigrationWizardService


@pytest.fixture
async def wizard_db(test_db):
    """Use the standard Postgres test database.

    This file used to spin up its own in-memory sqlite engine and manually
    create only the tables each test needed (User, MigrationJob, PatronCategory,
    and ad hoc Branch tables). That broke once `users` gained a JSONB column
    sqlite can't render, and it never enforced the real FK constraints
    (e.g. branches.library_system_id) postgres does. Riding the shared
    postgres test_db fixture gets the full, already-migrated schema for free.
    """
    return test_db


@pytest.fixture
async def staff_user(wizard_db):
    """Persisted staff user to own migration jobs."""
    user = User(
        email="staff@example.com",
        password_hash="x",
        first_name="Staff",
        last_name="One",
        role=UserRole.STAFF,
        is_active=True,
    )
    wizard_db.add(user)
    await wizard_db.commit()
    await wizard_db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_get_job_returns_existing_job(wizard_db, staff_user):
    """get_job must accept cls as @classmethod requires."""
    job = MigrationJob(
        status=MigrationJobStatus.READY,
        source_system=MigrationSourceSystem.KOHA,
        original_filename="t.csv",
        file_path="/tmp/t.csv",
        file_size_bytes=10,
        created_by_id=staff_user.id,
    )
    wizard_db.add(job)
    await wizard_db.commit()
    await wizard_db.refresh(job)

    # Before the cls-parameter fix, db was bound to cls and this crashed.
    fetched = await MigrationWizardService.get_job(wizard_db, job.id)
    assert fetched is not None
    assert fetched.id == job.id


@pytest.mark.asyncio
async def test_get_job_returns_none_for_missing(wizard_db):
    fetched = await MigrationWizardService.get_job(wizard_db, 999_999)
    assert fetched is None


@pytest.mark.asyncio
async def test_upload_does_not_double_commit(wizard_db, staff_user, monkeypatch, tmp_path):
    """upload() must not call db.commit() after analyze() already did.

    Counts commits via a spy; expected count is 1 (from analyze()).
    A count of 2 indicates the bug; post-fix it is 1.
    """
    commit_count = {"n": 0}
    original_commit = wizard_db.commit

    async def counting_commit():
        commit_count["n"] += 1
        await original_commit()

    monkeypatch.setattr(wizard_db, "commit", counting_commit)

    # Koha CSV with mappable columns so analyze runs through.
    csv_bytes = b"surname,firstname,email\nDoe,Jane,jane@example.com\n"

    # Redirect TEMP_DIR so the test does not litter /tmp on the VPS.
    monkeypatch.setattr(MigrationWizardService, "TEMP_DIR", tmp_path)

    await MigrationWizardService.upload(
        wizard_db,
        content=csv_bytes,
        filename="patrons.csv",
        source_system=MigrationSourceSystem.KOHA,
        user_id=staff_user.id,
    )
    assert commit_count["n"] == 1, f"expected 1 commit, got {commit_count['n']}"


def test_koha_mapping_uses_cardnumber_not_borrowernumber():
    """cardnumber is the patron-facing barcode in Koha; borrowernumber is the PK."""
    columns = ["cardnumber", "surname", "firstname", "email"]
    mapping = MigrationWizardService._koha_field_mapping(columns)
    assert mapping.get("cardnumber") == "barcode", (
        f"expected cardnumber -> barcode, got mapping={mapping}"
    )


def test_koha_mapping_does_not_map_borrowernumber_to_barcode():
    """borrowernumber is Koha's internal PK; it must not become the L30 barcode."""
    columns = ["borrowernumber", "surname"]
    mapping = MigrationWizardService._koha_field_mapping(columns)
    assert mapping.get("borrowernumber") != "barcode", (
        f"borrowernumber must not map to barcode, got mapping={mapping}"
    )


def test_koha_mapping_matches_prefixed_columns():
    """Real Koha exports prefix columns ('patron.surname'); strict equality drops them."""
    columns = ["patron.cardnumber", "patron.surname", "patron.firstname", "patron.email"]
    mapping = MigrationWizardService._koha_field_mapping(columns)
    assert mapping.get("patron.cardnumber") == "barcode"
    assert mapping.get("patron.surname") == "last_name"
    assert mapping.get("patron.firstname") == "first_name"
    assert mapping.get("patron.email") == "email"


def test_parse_koha_csv_strips_utf8_bom():
    """Koha exports often carry a UTF-8 BOM; the first column name must not include it."""
    bom = b"\xef\xbb\xbf"
    content = bom + b"cardnumber,surname,firstname\n12345,Doe,Jane\n"
    rows, columns = MigrationWizardService._parse_koha_csv(content)
    assert columns[0] == "cardnumber", f"BOM not stripped: {columns[0]!r}"
    assert rows[0]["cardnumber"] == "12345"


def test_parse_koha_csv_detects_semicolon_delimiter():
    """Koha exports use ; in locales where csv was generated by sqlreport."""
    content = b"cardnumber;surname;firstname\n12345;Doe;Jane\n"
    rows, columns = MigrationWizardService._parse_koha_csv(content)
    assert columns == ["cardnumber", "surname", "firstname"], (
        f"semicolon delimiter not detected: columns={columns!r}"
    )
    assert rows[0]["cardnumber"] == "12345"


def test_parse_koha_csv_still_handles_plain_comma_csv():
    """Regression guard: vanilla UTF-8 comma CSV must still parse."""
    content = b"cardnumber,surname\n12345,Doe\n"
    rows, columns = MigrationWizardService._parse_koha_csv(content)
    assert columns == ["cardnumber", "surname"]
    assert rows[0] == {"cardnumber": "12345", "surname": "Doe"}


@pytest.fixture
async def staff_user_for_cascade(db_session):
    """Staff user persisted via the conftest db_session (full DB)."""
    from app.models.user import User, UserRole
    user = User(
        email="cascade_staff@example.com",
        password_hash="x",
        first_name="Cascade",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
async def test_rollback_cascades_to_children(db_session, staff_user_for_cascade):
    """Rollback must use db.delete(obj) so cascade='all, delete-orphan' fires.

    Uses conftest's db_session fixture (full DB with all tables) because
    CatalogItem cascades to 7+ tables that the lightweight wizard_db
    fixture does not create.
    """
    from datetime import datetime, timedelta
    from app.models.catalog import CatalogItem, ItemType, ItemStatus
    from app.models.review import Review

    item = CatalogItem(
        title="Cascade Test Title",
        item_type=ItemType.book,
        status=ItemStatus.available,
    )
    db_session.add(item)
    await db_session.flush()

    review = Review(
        catalog_item_id=item.id,
        user_id=staff_user_for_cascade.id,
        rating=5,
        body="ok",
    )
    db_session.add(review)
    await db_session.commit()
    await db_session.refresh(review)
    item_id = item.id
    review_id = review.id

    job = MigrationJob(
        status=MigrationJobStatus.COMPLETED,
        source_system=MigrationSourceSystem.KOHA,
        original_filename="cascade.csv",
        file_path="/tmp/cascade.csv",
        file_size_bytes=10,
        created_by_id=staff_user_for_cascade.id,
        rollback_available_until=datetime.utcnow() + timedelta(hours=1),
        options={
            "_created_records": [{"id": item_id, "table": "catalog_items"}],
        },
    )
    db_session.add(job)
    await db_session.commit()

    await MigrationWizardService.rollback(db_session, job)

    # Parent gone
    fetched_item = await db_session.get(CatalogItem, item_id)
    assert fetched_item is None, "CatalogItem not deleted by rollback"
    # Cascade fired — child gone too
    fetched_review = await db_session.get(Review, review_id)
    assert fetched_review is None, (
        "Cascade did not fire; bulk SQL delete left an orphan Review row"
    )


@pytest.mark.asyncio
async def test_import_patron_populates_phone_hash(wizard_db):
    """ImportService._create_patron must populate phone_hash for search-by-phone."""
    from app.services.import_service import ImportService
    from app.core.encryption import hash_pii

    data = {
        "email": "phonecheck@example.com",
        "name": "Phone Check",
        "phone": "555-867-5309",
        "barcode": "L-PHONE-1",
        "patron_type": "patron",
    }
    user_id, table, _token = await ImportService._create_patron(wizard_db, data)
    await wizard_db.commit()
    assert table == "users"

    fetched = await wizard_db.get(User, user_id)
    # Blind index must be populated; matches the hash of the normalized number.
    expected_hash = hash_pii("5558675309", field="phone")
    assert fetched.phone_hash == expected_hash, (
        f"phone_hash not populated; got {fetched.phone_hash!r}, expected {expected_hash!r}"
    )
    assert fetched.phone_last4 == "5309"


@pytest.mark.asyncio
async def test_import_patron_resolves_home_branch_code_to_id(wizard_db):
    """_create_patron must look up home_branch (Branch.code) and set home_branch_id."""
    from app.services.import_service import ImportService
    from app.models.multi_branch import Branch, LibrarySystem

    # branches.library_system_id is a real NOT NULL FK on postgres.
    system = LibrarySystem(code="MWTEST", name="Migration Wizard Test System")
    wizard_db.add(system)
    await wizard_db.flush()

    branch = Branch(
        library_system_id=system.id,
        code="MAIN",
        name="Main Branch",
    )
    wizard_db.add(branch)
    await wizard_db.commit()
    await wizard_db.refresh(branch)

    data = {
        "email": "branchtest@example.com",
        "name": "Branch Test",
        "barcode": "L-BR-1",
        "patron_type": "patron",
        "home_branch": "MAIN",
    }
    user_id, table, _token = await ImportService._create_patron(wizard_db, data)
    await wizard_db.commit()

    from app.models.user import User
    fetched = await wizard_db.get(User, user_id)
    assert fetched.home_branch_id == branch.id, (
        f"home_branch=MAIN should resolve to Branch.id={branch.id}; got home_branch_id={fetched.home_branch_id!r}"
    )


@pytest.mark.asyncio
async def test_import_patron_unknown_home_branch_does_not_crash(wizard_db):
    """Unknown home_branch should leave home_branch_id=None, not raise."""
    from app.services.import_service import ImportService

    data = {
        "email": "nobranch@example.com",
        "name": "No Branch",
        "barcode": "L-NB-1",
        "patron_type": "patron",
        "home_branch": "GHOST",
    }
    user_id, _table, _token = await ImportService._create_patron(wizard_db, data)
    await wizard_db.commit()

    from app.models.user import User
    fetched = await wizard_db.get(User, user_id)
    assert fetched.home_branch_id is None


@pytest.mark.asyncio
async def test_import_patron_home_branch_is_case_insensitive(wizard_db):
    """Lowercase home_branch in CSV must resolve same as uppercase (parity with _create_hold)."""
    from app.services.import_service import ImportService
    from app.models.multi_branch import Branch, LibrarySystem

    system = LibrarySystem(code="MWTEST2", name="Migration Wizard Test System 2")
    wizard_db.add(system)
    await wizard_db.flush()

    branch = Branch(
        library_system_id=system.id,
        code="MAIN",
        name="Main Branch",
    )
    wizard_db.add(branch)
    await wizard_db.commit()
    await wizard_db.refresh(branch)

    data = {
        "email": "lower@example.com",
        "name": "Lower Case",
        "barcode": "L-LC-1",
        "patron_type": "patron",
        "home_branch": "main",  # lowercase deliberately
    }
    user_id, _table, _token = await ImportService._create_patron(wizard_db, data)
    await wizard_db.commit()

    from app.models.user import User
    fetched = await wizard_db.get(User, user_id)
    assert fetched.home_branch_id == branch.id, (
        f"lowercase main should resolve to Branch.id={branch.id}; got home_branch_id={fetched.home_branch_id!r}"
    )


@pytest.mark.asyncio
async def test_circulation_import_preserves_explicit_due_date(db_session, monkeypatch):
    from datetime import date
    from app.services.import_service import ImportService
    from app.models.catalog import CatalogItem, ItemType, ItemStatus
    from app.models.inventory import ItemCopy, ItemCondition
    from app.models.circulation import Checkout
    from app.models.user import User, UserRole

    user = User(
        email="circ@example.com",
        password_hash="x",
        first_name="Circ",
        last_name="User",
        role=UserRole.PATRON,
        is_active=True,
        library_card="CIRC-1",
    )
    db_session.add(user)
    item = CatalogItem(title="T", item_type=ItemType.book, status=ItemStatus.available)
    db_session.add(item)
    await db_session.flush()
    copy = ItemCopy(
        catalog_item_id=item.id,
        barcode="COPY-CIRC-1",
        condition=ItemCondition.GOOD,
        copy_number=1,
    )
    db_session.add(copy)
    await db_session.commit()

    data = {
        "patron_barcode": "CIRC-1",
        "item_barcode": "COPY-CIRC-1",
        "checkout_date": "2024-01-15",
        "due_date": "2024-01-29",  # explicit 14-day loan
        "return_date": "2024-01-25",
    }
    checkout_id, table = await ImportService._create_circulation(db_session, data)
    await db_session.commit()
    assert table == "checkouts"

    fetched = await db_session.get(Checkout, checkout_id)
    assert fetched.due_date.date() == date(2024, 1, 29), (
        "explicit due_date 2024-01-29 should be preserved; got " + repr(fetched.due_date)
    )


@pytest.mark.asyncio
async def test_circulation_import_falls_back_to_policy_when_due_date_missing(
    db_session, monkeypatch
):
    from datetime import date
    from app.services.import_service import ImportService
    from app.models.catalog import CatalogItem, ItemType, ItemStatus
    from app.models.inventory import ItemCopy, ItemCondition
    from app.models.circulation import Checkout
    from app.models.user import User, UserRole

    user = User(
        email="circ2@example.com",
        password_hash="x",
        first_name="Circ",
        last_name="Two",
        role=UserRole.PATRON,
        is_active=True,
        library_card="CIRC-2",
    )
    db_session.add(user)
    item = CatalogItem(title="T2", item_type=ItemType.book, status=ItemStatus.available)
    db_session.add(item)
    await db_session.flush()
    copy = ItemCopy(
        catalog_item_id=item.id,
        barcode="COPY-CIRC-2",
        condition=ItemCondition.GOOD,
        copy_number=1,
    )
    db_session.add(copy)
    await db_session.commit()

    async def fake_loan_period(user, item, db, collection_id=None):
        return 14
    monkeypatch.setattr(
        "app.services.circulation_policy.get_loan_period_days",
        fake_loan_period,
    )

    data = {
        "patron_barcode": "CIRC-2",
        "item_barcode": "COPY-CIRC-2",
        "checkout_date": "2024-01-15",
    }
    checkout_id, _table = await ImportService._create_circulation(db_session, data)
    await db_session.commit()

    fetched = await db_session.get(Checkout, checkout_id)
    assert fetched.due_date.date() == date(2024, 1, 29), (
        "policy fallback should give 2024-01-29 (14 days from 2024-01-15); got " + repr(fetched.due_date)
    )


@pytest.mark.asyncio
async def test_circulation_import_math_does_not_clip_at_day_28(
    db_session, monkeypatch
):
    from datetime import date
    from app.services.import_service import ImportService
    from app.models.catalog import CatalogItem, ItemType, ItemStatus
    from app.models.inventory import ItemCopy, ItemCondition
    from app.models.circulation import Checkout
    from app.models.user import User, UserRole

    user = User(
        email="circ3@example.com",
        password_hash="x",
        first_name="Circ",
        last_name="Three",
        role=UserRole.PATRON,
        is_active=True,
        library_card="CIRC-3",
    )
    db_session.add(user)
    item = CatalogItem(title="T3", item_type=ItemType.book, status=ItemStatus.available)
    db_session.add(item)
    await db_session.flush()
    copy = ItemCopy(
        catalog_item_id=item.id,
        barcode="COPY-CIRC-3",
        condition=ItemCondition.GOOD,
        copy_number=1,
    )
    db_session.add(copy)
    await db_session.commit()

    async def fake_loan_period(user, item, db, collection_id=None):
        return 21
    monkeypatch.setattr(
        "app.services.circulation_policy.get_loan_period_days",
        fake_loan_period,
    )

    data = {
        "patron_barcode": "CIRC-3",
        "item_barcode": "COPY-CIRC-3",
        "checkout_date": "2024-01-10",  # +21 days = 2024-01-31, NOT 2024-01-28
    }
    checkout_id, _table = await ImportService._create_circulation(db_session, data)
    await db_session.commit()

    fetched = await db_session.get(Checkout, checkout_id)
    assert fetched.due_date.date() == date(2024, 1, 31), (
        "2024-01-10 + 21 days should be 2024-01-31; got " + repr(fetched.due_date) + ". The min(day+21, 28) bug returns 2024-01-28."
    )


@pytest.mark.asyncio
async def test_create_catalog_item_unknown_type_populates_local_type(db_session):
    """When source item_type doesnt match the enum, fall back to other + local_type."""
    from app.services.import_service import ImportService
    from app.models.catalog import CatalogItem, ItemType

    data = {
        "title": "Local History Microfiche Collection",
        "author": "Various",
        "item_type": "microfiche",  # NOT in L30s 13-value enum
    }
    item_id, table = await ImportService._create_catalog_item(db_session, data)
    await db_session.commit()
    assert table == "catalog_items"

    fetched = await db_session.get(CatalogItem, item_id)
    assert fetched.item_type == ItemType.other, (
        f"unknown item_type should collapse to other; got {fetched.item_type!r}"
    )
    assert fetched.local_type == "microfiche", (
        f"local_type should preserve original microfiche; got {fetched.local_type!r}"
    )


@pytest.mark.asyncio
async def test_create_catalog_item_known_type_leaves_local_type_null(db_session):
    """When source item_type matches the enum, local_type stays NULL."""
    from app.services.import_service import ImportService
    from app.models.catalog import CatalogItem, ItemType

    data = {
        "title": "Ordinary Book",
        "author": "An Author",
        "item_type": "book",
    }
    item_id, _table = await ImportService._create_catalog_item(db_session, data)
    await db_session.commit()

    fetched = await db_session.get(CatalogItem, item_id)
    assert fetched.item_type == ItemType.book
    assert fetched.local_type is None, (
        f"local_type should be None when item_type fits the enum; got {fetched.local_type!r}"
    )


@pytest.mark.asyncio
async def test_create_fine_unknown_reason_populates_local_fine_type(db_session):
    """Unknown source fine reason -> collapse to 'other' + preserve in local_fine_type."""
    from app.services.import_service import ImportService
    from app.models.fine import Fine, FineType
    from app.models.user import User, UserRole

    user = User(
        email="finetest@example.com",
        password_hash="x",
        first_name="Fine",
        last_name="Test",
        role=UserRole.PATRON,
        is_active=True,
        library_card="FINE-1",
    )
    db_session.add(user)
    await db_session.commit()

    data = {
        "patron_barcode": "FINE-1",
        "amount": "5.00",
        "reason": "PROCESSING_FEE",  # NOT in L30's 4-value FineType
    }
    fine_id, table = await ImportService._create_fine(db_session, data)
    await db_session.commit()
    assert table == "fines"

    fetched = await db_session.get(Fine, fine_id)
    assert fetched.fine_type == FineType.other
    assert fetched.local_fine_type == "PROCESSING_FEE", (
        f"local_fine_type should preserve 'PROCESSING_FEE' (original case); "
        f"got {fetched.local_fine_type!r}"
    )


@pytest.mark.asyncio
async def test_create_fine_known_reason_leaves_local_fine_type_null(db_session):
    """Known reasons leave local_fine_type NULL."""
    from app.services.import_service import ImportService
    from app.models.fine import Fine, FineType
    from app.models.user import User, UserRole

    user = User(
        email="finetest2@example.com",
        password_hash="x",
        first_name="Fine",
        last_name="Test2",
        role=UserRole.PATRON,
        is_active=True,
        library_card="FINE-2",
    )
    db_session.add(user)
    await db_session.commit()

    data = {
        "patron_barcode": "FINE-2",
        "amount": "2.50",
        "reason": "overdue",
    }
    fine_id, _table = await ImportService._create_fine(db_session, data)
    await db_session.commit()

    fetched = await db_session.get(Fine, fine_id)
    assert fetched.fine_type == FineType.overdue
    assert fetched.local_fine_type is None


@pytest.mark.asyncio
async def test_create_catalog_item_preserves_local_type_case(db_session):
    """local_type must preserve the source's original case (Koha 'Microfiche', Sirsi 'ARCHIVE').

    The enum lookup is case-insensitive, but the preserved label keeps
    librarian-facing casing so display UIs show 'Microfiche (other)' not
    'microfiche (other)'.
    """
    from app.services.import_service import ImportService
    from app.models.catalog import CatalogItem, ItemType

    data = {
        "title": "Mixed-Case Microfiche",
        "item_type": "Microfiche",  # mixed case deliberately
    }
    item_id, _table = await ImportService._create_catalog_item(db_session, data)
    await db_session.commit()

    fetched = await db_session.get(CatalogItem, item_id)
    assert fetched.item_type == ItemType.other
    assert fetched.local_type == "Microfiche", (
        f"local_type should preserve 'Microfiche' (original case); "
        f"got {fetched.local_type!r}"
    )


@pytest.mark.asyncio
async def test_create_patron_resolves_patron_category_code_to_id(wizard_db):
    """_create_patron must look up patron_category by code and set FK."""
    from app.services.import_service import ImportService
    from app.models.patron_category import PatronCategory
    from app.models.user import User

    category = PatronCategory(id=10, code="STUDENT", label="Student", is_active=True)
    wizard_db.add(category)
    await wizard_db.commit()

    data = {
        "email": "pctest@example.com",
        "name": "PC Test",
        "barcode": "PC-1",
        "patron_type": "patron",
        "patron_category": "STUDENT",
    }
    user_id, _table, _token = await ImportService._create_patron(wizard_db, data)
    await wizard_db.commit()

    fetched = await wizard_db.get(User, user_id)
    assert fetched.patron_category_id == 10, (
        f"patron_category='STUDENT' should resolve to id=10; "
        f"got patron_category_id={fetched.patron_category_id!r}"
    )


@pytest.mark.asyncio
async def test_create_patron_unknown_patron_category_does_not_crash(wizard_db):
    """Unknown patron_category should leave the FK NULL, not raise."""
    from app.services.import_service import ImportService
    from app.models.user import User

    data = {
        "email": "pctest2@example.com",
        "name": "PC Test2",
        "barcode": "PC-2",
        "patron_type": "patron",
        "patron_category": "GHOST",
    }
    user_id, _table, _token = await ImportService._create_patron(wizard_db, data)
    await wizard_db.commit()

    fetched = await wizard_db.get(User, user_id)
    assert fetched.patron_category_id is None
