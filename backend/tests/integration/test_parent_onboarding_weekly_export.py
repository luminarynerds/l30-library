# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for GET /api/v1/parent-onboarding/reports/weekly-summary.

This endpoint backs the staff dashboard's "Export weekly summary" menu.
The CSV that ships includes patron-derived data redacted to initials,
so the test suite must lock the redaction guarantees: no full names,
no patron ids, no leakage of small-cell counts.
"""
from __future__ import annotations

import re
import uuid
from datetime import date, datetime, time, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.parent_onboarding import (
    CareCoordinatorAssignment,
    CareCoordinatorCheckIn,
    EnrollmentFacilitationStatus,
    HomeVisitPurpose,
    HomeVisitStatus,
    ParentHomeVisit,
    ParentOnboardingSession,
    ParentOnboardingStatus,
    ServiceEnrollmentFacilitation,
)
from app.models.parent_onboarding_export_log import ParentOnboardingExportLog
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


async def _make_user(test_db, role: UserRole, *, first: str = "Test", last: str = "User") -> User:
    unique = uuid.uuid4().hex[:8]
    u = User(
        email=f"{role.value}-{unique}@po-weekly-test.local",
        password_hash="x",
        first_name=first,
        last_name=last,
        role=role,
        is_active=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


@pytest.fixture
async def staff_user(test_db):
    return await _make_user(test_db, UserRole.STAFF, first="Coord", last="Lopez")


@pytest.fixture
async def admin_user(test_db):
    return await _make_user(test_db, UserRole.ADMIN, first="Admin", last="Carter")


@pytest.fixture
async def patron_user(test_db):
    return await _make_user(test_db, UserRole.PATRON, first="Patient", last="Patron")


@pytest.fixture
async def mia_garcia(test_db):
    return await _make_user(test_db, UserRole.PATRON, first="Mia", last="Garcia")


def _override_user(user):
    """Helper to swap get_current_user; the calling test restores."""
    from app.api.v1.auth import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: user
    return get_current_user


def _restore_overrides(*keys):
    from app.main import app

    for k in keys:
        app.dependency_overrides.pop(k, None)


# ---------------------------------------------------------------------------
# Role gating
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_patron_role_is_rejected(client, test_db, patron_user):
    """A PATRON token must not be able to fetch the weekly export."""
    dep = _override_user(patron_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=csv"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code in (403, 404), resp.text


@pytest.mark.integration
async def test_staff_can_fetch(client, test_db, staff_user):
    """STAFF can fetch the CSV; response is text/csv with attachment disposition."""
    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=csv"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200, resp.text
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    assert "parent-onboarding-weekly-" in resp.headers["content-disposition"]


# ---------------------------------------------------------------------------
# Format validation
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_invalid_format_rejected(client, test_db, staff_user):
    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=html"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
async def test_pdf_format_returns_422_until_weasyprint_arrives(
    client, test_db, staff_user
):
    """PDF is in the spec but blocked until weasyprint lands in the image."""
    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=pdf"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 422, resp.text


@pytest.mark.integration
async def test_future_end_date_rejected(client, test_db, staff_user):
    """Guard against far-future dates."""
    far_future = (date.today() + timedelta(days=5)).isoformat()
    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            f"/api/v1/parent-onboarding/reports/weekly-summary?format=csv&end_date={far_future}"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_csv_contains_initials_not_full_names(
    client, test_db, staff_user, mia_garcia
):
    """A session with Mia Garcia in the window appears as 'M.G.' and never as 'Mia' or 'Garcia'."""
    now = datetime.now(timezone.utc)
    # Completed 2 days ago — solidly inside the 7-day window.
    sess = ParentOnboardingSession(
        patron_id=mia_garcia.id,
        staff_id=staff_user.id,
        branch_id=1,
        status=ParentOnboardingStatus.completed.value,
        scheduled_at=now - timedelta(days=2, hours=1),
        completed_at=now - timedelta(days=2),
    )
    test_db.add(sess)
    await test_db.commit()

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=csv"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200, resp.text
    body = resp.text

    assert "M.G." in body, "Initials missing from CSV"
    # Full names must never appear.
    assert "Mia" not in body, "Patron first name leaked"
    assert "Garcia" not in body, "Patron last name leaked"


@pytest.mark.integration
async def test_missing_first_name_preserves_positional_dot(
    client, test_db, staff_user
):
    """``.S.`` not ``S.`` for a patron with only last_name."""
    # users.first_name is NOT NULL in the schema; the redaction rule
    # treats empty string the same as NULL (both yield positional dot).
    smith = User(
        email=f"smith-{uuid.uuid4().hex[:8]}@po-weekly-test.local",
        password_hash="x",
        first_name="",
        last_name="Smith",
        role=UserRole.PATRON,
        is_active=True,
    )
    test_db.add(smith)
    await test_db.commit()
    await test_db.refresh(smith)

    now = datetime.now(timezone.utc)
    sess = ParentOnboardingSession(
        patron_id=smith.id,
        staff_id=staff_user.id,
        branch_id=1,
        status=ParentOnboardingStatus.completed.value,
        scheduled_at=now - timedelta(days=3, hours=1),
        completed_at=now - timedelta(days=3),
    )
    test_db.add(sess)
    await test_db.commit()

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=csv"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200, resp.text
    body = resp.text
    assert ".S." in body
    assert "Smith" not in body


@pytest.mark.integration
async def test_no_patron_ids_appear_in_csv_body(
    client, test_db, staff_user, mia_garcia
):
    """Patron IDs (likely 4-7 digit integers) must not appear unless they are date components."""
    now = datetime.now(timezone.utc)
    sess = ParentOnboardingSession(
        patron_id=mia_garcia.id,
        staff_id=staff_user.id,
        branch_id=1,
        status=ParentOnboardingStatus.completed.value,
        scheduled_at=now - timedelta(days=1, hours=1),
        completed_at=now - timedelta(days=1),
    )
    test_db.add(sess)
    await test_db.commit()

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=csv"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200, resp.text
    body = resp.text
    # No literal "patron_id" or "patron-id" labels anywhere.
    assert not re.search(r"\bpatron[_-]?id\b", body, re.IGNORECASE)
    # The specific patron's id should not appear as an isolated token.
    # We use a word-boundary search to avoid colliding with dates like 2026.
    pid = str(mia_garcia.id)
    if not pid.startswith("20"):  # avoid masking year tokens 2024-2099
        assert not re.search(rf"\b{pid}\b", body)


# ---------------------------------------------------------------------------
# Window boundary
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_record_exactly_at_lower_bound_is_included(
    client, test_db, staff_user, mia_garcia
):
    """A session completed at end_date - 7 days 00:00:00 UTC is in scope."""
    end_date = date(2026, 5, 18)
    start_dt = datetime.combine(end_date - timedelta(days=7), time.min, tzinfo=timezone.utc)
    sess = ParentOnboardingSession(
        patron_id=mia_garcia.id,
        staff_id=staff_user.id,
        branch_id=1,
        status=ParentOnboardingStatus.completed.value,
        scheduled_at=start_dt - timedelta(hours=1),
        completed_at=start_dt,
    )
    test_db.add(sess)
    await test_db.commit()

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            f"/api/v1/parent-onboarding/reports/weekly-summary?format=csv&end_date={end_date.isoformat()}"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200
    assert "M.G." in resp.text


@pytest.mark.integration
async def test_record_one_second_before_window_is_excluded(
    client, test_db, staff_user, mia_garcia
):
    """A session completed at start_dt - 1s is outside the window."""
    end_date = date(2026, 5, 18)
    start_dt = datetime.combine(end_date - timedelta(days=7), time.min, tzinfo=timezone.utc)
    sess = ParentOnboardingSession(
        patron_id=mia_garcia.id,
        staff_id=staff_user.id,
        branch_id=1,
        status=ParentOnboardingStatus.completed.value,
        scheduled_at=start_dt - timedelta(hours=2),
        completed_at=start_dt - timedelta(seconds=1),
    )
    test_db.add(sess)
    await test_db.commit()

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            f"/api/v1/parent-onboarding/reports/weekly-summary?format=csv&end_date={end_date.isoformat()}"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200
    # No M.G. row: the only record we added was out of window.
    assert "M.G." not in resp.text


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_audit_log_row_written_on_success(
    client, test_db, staff_user, mia_garcia
):
    """Each successful CSV export persists one parent_onboarding_export_log row."""
    now = datetime.now(timezone.utc)
    sess = ParentOnboardingSession(
        patron_id=mia_garcia.id,
        staff_id=staff_user.id,
        branch_id=1,
        status=ParentOnboardingStatus.completed.value,
        scheduled_at=now - timedelta(days=2, hours=1),
        completed_at=now - timedelta(days=2),
    )
    test_db.add(sess)
    await test_db.commit()

    before = (
        await test_db.execute(select(ParentOnboardingExportLog))
    ).scalars().all()
    n_before = len(before)

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=csv"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200

    after = (
        await test_db.execute(select(ParentOnboardingExportLog))
    ).scalars().all()
    assert len(after) == n_before + 1
    row = after[-1]
    assert row.exported_by_id == staff_user.id
    assert row.format == "csv"
    assert row.row_count >= 1


@pytest.mark.integration
async def test_audit_log_not_written_on_4xx(client, test_db, staff_user):
    """4xx paths (bad format) must not pollute the audit log."""
    before = (
        await test_db.execute(select(ParentOnboardingExportLog))
    ).scalars().all()
    n_before = len(before)

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=html"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 422

    after = (
        await test_db.execute(select(ParentOnboardingExportLog))
    ).scalars().all()
    assert len(after) == n_before


# ---------------------------------------------------------------------------
# Coordinator scope
# ---------------------------------------------------------------------------


@pytest.mark.integration
async def test_coordinator_me_scopes_activity(
    client, test_db, staff_user, mia_garcia
):
    """coordinator_id=me restricts the activity log to the requester's records."""
    other_staff = await _make_user(test_db, UserRole.STAFF, first="Other", last="Tester")
    now = datetime.now(timezone.utc)
    # Other staff session, in window — should NOT appear when scope=me
    sess_other = ParentOnboardingSession(
        patron_id=mia_garcia.id,
        staff_id=other_staff.id,
        branch_id=1,
        status=ParentOnboardingStatus.completed.value,
        scheduled_at=now - timedelta(days=2, hours=1),
        completed_at=now - timedelta(days=2),
    )
    test_db.add(sess_other)
    await test_db.commit()

    dep = _override_user(staff_user)
    try:
        resp = await client.get(
            "/api/v1/parent-onboarding/reports/weekly-summary?format=csv&coordinator_id=me"
        )
    finally:
        _restore_overrides(dep)
    assert resp.status_code == 200
    # The other staff's session was the only record in window; with scope=me,
    # the activity log must not include it.
    body = resp.text
    assert "M.G." not in body
