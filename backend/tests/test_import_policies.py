# SPDX-License-Identifier: AGPL-3.0-or-later
from app.models.import_job import ImportJobType
from app.services.import_service.constants import REQUIRED_FIELDS, TARGET_FIELDS
from app.services.import_service.templates import TEMPLATES


def test_policies_job_type_registered():
    assert ImportJobType.POLICIES.value == "policies"
    assert ImportJobType.POLICIES in TARGET_FIELDS
    assert ImportJobType.POLICIES in REQUIRED_FIELDS
    assert ImportJobType.POLICIES in TEMPLATES
    cols = TEMPLATES[ImportJobType.POLICIES]["columns"]
    assert "loan_period_days" in cols and "role" in cols and "item_type" in cols


import pytest


def _make_csv(*rows):
    """Build minimal CSV bytes from a list of dicts."""
    import csv, io
    if not rows:
        return b""
    fieldnames = list(rows[0].keys())
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue().encode()


@pytest.mark.asyncio
async def test_validate_policies_good_row(test_db):
    """A valid row with one knob produces no errors."""
    from app.services.import_service import ImportService
    from app.models.import_job import ImportJobType, DuplicateAction

    content = _make_csv({"role": "patron", "item_type": "book", "loan_period_days": "21"})
    job = await ImportService.upload(
        db=test_db,
        file_content=content,
        filename="policies.csv",
        job_type=ImportJobType.POLICIES,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=100.0,
        created_by_id=None,
    )
    job = await ImportService.validate(test_db, job)
    errors = job.validation_report["errors"]
    row1_errors = [e for e in errors if e["row"] == 1]
    assert row1_errors == [], f"Expected no errors for row 1, got: {row1_errors}"


@pytest.mark.asyncio
async def test_validate_policies_bad_role(test_db):
    """A row with an invalid role enum value produces a row error on field 'role'."""
    from app.services.import_service import ImportService
    from app.models.import_job import ImportJobType, DuplicateAction

    content = _make_csv({"role": "not_a_role", "loan_period_days": "7"})
    job = await ImportService.upload(
        db=test_db,
        file_content=content,
        filename="policies.csv",
        job_type=ImportJobType.POLICIES,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=100.0,
        created_by_id=None,
    )
    job = await ImportService.validate(test_db, job)
    errors = job.validation_report["errors"]
    row1_errors = [e for e in errors if e["row"] == 1]
    assert any(e["field"] == "role" for e in row1_errors), (
        f"Expected error on field 'role', got: {row1_errors}"
    )


@pytest.mark.asyncio
async def test_validate_policies_no_knobs(test_db):
    """A row with no knob columns produces a row error."""
    from app.services.import_service import ImportService
    from app.models.import_job import ImportJobType, DuplicateAction

    content = _make_csv({"role": "patron"})
    job = await ImportService.upload(
        db=test_db,
        file_content=content,
        filename="policies.csv",
        job_type=ImportJobType.POLICIES,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=100.0,
        created_by_id=None,
    )
    job = await ImportService.validate(test_db, job)
    errors = job.validation_report["errors"]
    row1_errors = [e for e in errors if e["row"] == 1]
    assert row1_errors, f"Expected error for row with no knobs, got none"


@pytest.mark.asyncio
async def test_validate_policies_non_integer_knob(test_db):
    """A row with a non-integer loan_period_days produces a row error."""
    from app.services.import_service import ImportService
    from app.models.import_job import ImportJobType, DuplicateAction

    content = _make_csv({"loan_period_days": "abc"})
    job = await ImportService.upload(
        db=test_db,
        file_content=content,
        filename="policies.csv",
        job_type=ImportJobType.POLICIES,
        duplicate_action=DuplicateAction.SKIP,
        error_threshold=100.0,
        created_by_id=None,
    )
    job = await ImportService.validate(test_db, job)
    errors = job.validation_report["errors"]
    row1_errors = [e for e in errors if e["row"] == 1]
    assert row1_errors, f"Expected error for non-integer loan_period_days, got none"
    # Should flag the field specifically
    fields = [e["field"] for e in row1_errors]
    assert "loan_period_days" in fields, f"Expected error on loan_period_days, got fields: {fields}"


import pytest
from sqlalchemy import select, func
from app.services.import_service.service import ImportService
from app.models.multi_branch import LibrarySystem
from app.models.circulation_policy import CirculationPolicy
from app.models.user import UserRole
from app.models.catalog import ItemType


@pytest.mark.asyncio
async def test_create_policy_persists_with_org_and_fields(db):
    db.add(LibrarySystem(code="X", name="X Lib"))
    await db.flush()
    await ImportService._create_policy(db, {"role": "patron", "item_type": "book", "loan_period_days": "14"})
    await db.flush()
    pol = (await db.execute(select(CirculationPolicy))).scalars().all()[-1]
    assert pol.role == UserRole.PATRON and pol.item_type == ItemType.book
    assert pol.loan_period_days == 14 and pol.library_system_id is not None


@pytest.mark.asyncio
async def test_create_policy_skips_identical(db):
    db.add(LibrarySystem(code="Y", name="Y Lib"))
    await db.flush()
    row = {"role": "patron", "item_type": "book", "loan_period_days": "14"}
    await ImportService._create_policy(db, row)
    await db.flush()
    n1 = (await db.execute(select(func.count()).select_from(CirculationPolicy))).scalar()
    await ImportService._create_policy(db, row)
    await db.flush()
    n2 = (await db.execute(select(func.count()).select_from(CirculationPolicy))).scalar()
    assert n2 == n1  # identical dimensions -> no duplicate
