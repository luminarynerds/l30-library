# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the staff list-all library-visits endpoint.

Covers:
- GET /school-partnerships/library-visits/requests   (staff sees all pending)
- 403 for non-staff users
- Optional ?status=pending,scheduled filter

Depends on the LibraryVisitRequest model + table that PR #501 introduces.
If that model isn't present yet (e.g. when this branch is rebased onto an
origin/main that doesn't have #501 merged), the whole module is skipped so
the test suite stays green.
"""

import pytest

try:
    from app.models.reading import LibraryVisitRequest as VisitReq  # noqa: F401
except ImportError:
    pytest.skip(
        "LibraryVisitRequest model missing -- waiting on PR #501 merge",
        allow_module_level=True,
    )

from datetime import datetime, timezone, timedelta

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.outreach import OutreachPartner
from app.models.reading import LibraryVisitRequest


@pytest.fixture
async def school(test_db):
    s = OutreachPartner(
        name="Maple Elementary",
        partner_type="school",
        status="active",
    )
    test_db.add(s)
    await test_db.commit()
    await test_db.refresh(s)
    return s


@pytest.fixture
async def two_pending_requests(test_db, school):
    base = datetime.now(timezone.utc) + timedelta(days=7)
    rows = []
    for i in range(2):
        row = LibraryVisitRequest(
            school_id=school.id,
            teacher_user_id=None,
            teacher_name=f"Teacher {i}",
            requested_date=base + timedelta(days=i),
            number_of_students=20 + i,
            grade_level=f"{i + 1}rd",
            purpose=f"Purpose {i}",
            status="pending",
        )
        test_db.add(row)
        rows.append(row)
    await test_db.commit()
    return rows


@pytest.fixture(autouse=True)
def _bypass_first_boot():
    app.state.setup_complete = True
    yield


@pytest.fixture
def staff_client(client, test_staff):
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


# ==================== GET /library-visits/requests ====================


@pytest.mark.asyncio
async def test_staff_can_list_all_requests(staff_client, two_pending_requests):
    """A user with STAFF role sees every pending request across schools."""
    resp = await staff_client.get(
        "/api/v1/school-partnerships/library-visits/requests"
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert "requests" in payload
    assert len(payload["requests"]) == 2
    assert {r["status"] for r in payload["requests"]} == {"pending"}


@pytest.mark.asyncio
async def test_patron_is_forbidden(patron_client, two_pending_requests):
    """A patron (non-staff) gets 403."""
    resp = await patron_client.get(
        "/api/v1/school-partnerships/library-visits/requests"
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_status_filter_query_param(staff_client, school, two_pending_requests, test_db):
    """status=pending only returns pending rows even when scheduled rows exist."""
    scheduled = LibraryVisitRequest(
        school_id=school.id,
        teacher_user_id=None,
        teacher_name="Already Scheduled",
        requested_date=datetime.now(timezone.utc),
        scheduled_date=datetime.now(timezone.utc) + timedelta(days=2),
        number_of_students=10,
        grade_level="K",
        purpose="Already scheduled",
        status="scheduled",
    )
    test_db.add(scheduled)
    await test_db.commit()

    resp = await staff_client.get(
        "/api/v1/school-partnerships/library-visits/requests?status=pending"
    )
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert len(payload["requests"]) == 2
    assert all(r["status"] == "pending" for r in payload["requests"])


@pytest.mark.asyncio
async def test_literal_route_not_shadowed_by_param_route(staff_client, two_pending_requests):
    """Regression: the literal /library-visits/requests route must not be
    shadowed by the per-school /library-visits/requests/{school_id} route from
    school_reading_partnerships.py (see feedback_l30_fastapi_router_shadowing).
    """
    resp = await staff_client.get(
        "/api/v1/school-partnerships/library-visits/requests"
    )
    # If shadowed, FastAPI would try to coerce "requests" into school_id:int
    # and return 422.
    assert resp.status_code != 422, resp.text
    assert resp.status_code == 200
