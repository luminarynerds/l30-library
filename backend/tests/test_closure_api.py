# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for Closure Management API endpoints (backend/app/api/v1/branches.py,
the closure-workflow block at :840-:1000; service in
backend/app/services/closure_management_service.py).

Exercises the real FastAPI app against a live test database (async httpx
client + ASGITransport, per tests/conftest.py's `client` fixture) -- no
mocking of the service or DB layer. The service itself already has focused
mock-based unit coverage in tests/test_closure_management_service.py; this
file is about the HTTP surface: auth gating, request validation, response
shape, and not-found semantics.

Endpoint groups covered, one test class per resource:

- POST   /branches/{id}/closures/close-today
- GET    /branches/{id}/closures/{id}/status
- GET    /branches/{id}/closures/{id}/completion
- GET    /branches/{id}/closures/{id}/affected-patrons
- GET    /branches/{id}/closures/{id}/affected-events
- GET    /branches/{id}/closures/{id}/staff-notifications
- PATCH  /branches/{id}/closures/{id}/external-services
- POST   /branches/{id}/closures/{id}/notify-partners
- POST   /branches/{id}/closures/{id}/schedule-reopening
- GET    /branches/{id}/closures/active

Plus two cross-cutting classes (TestClosureEndpointAuthorization,
TestClosureNotFoundBehavior) that parametrize role-gating and not-found
semantics across every endpoint above, instead of repeating near-identical
auth/404 checks in each resource's own class.

NOTE: this file was previously gutted -- every test built a payload into a
discarded `_ = {...}` with the actual client call and all asserts commented
out, so every test "passed" vacuously with zero real coverage of this API.
Restored 2026-07 against the API as it currently exists. The restoration
surfaced four write routes that returned server errors instead of 404 for a
missing closure/branch id; those routes were fixed alongside this file
(fix/audit-routing), so TestClosureNotFoundBehavior asserts 404 plainly.
"""

from datetime import date, datetime, time, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.circulation import Hold, HoldStatus
from app.models.event import Event
from app.models.multi_branch import Branch, BranchClosure, LibrarySystem
from app.models.user import User, UserRole


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def admin_client(client: AsyncClient, test_admin: User) -> AsyncClient:
    """Async client where get_current_user resolves to an admin user.

    Same dependency-override pattern as the module-level `staff_client`
    fixture in tests/conftest.py and the local `admin_client` fixture in
    tests/test_courses_import.py. Admin satisfies both require_admin and
    require_staff, so this is the default "authorized" client for tests
    that aren't specifically about role boundaries.
    """
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client: AsyncClient, test_patron: User) -> AsyncClient:
    """Async client where get_current_user resolves to a patron user."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def library_system(db: AsyncSession) -> LibrarySystem:
    system = LibrarySystem(
        code="CLOSTEST", name="Closure Test System", timezone="America/New_York"
    )
    db.add(system)
    await db.commit()
    await db.refresh(system)
    return system


@pytest.fixture
async def branch(db: AsyncSession, library_system: LibrarySystem) -> Branch:
    b = Branch(library_system_id=library_system.id, code="MAIN", name="Main Branch")
    db.add(b)
    await db.commit()
    await db.refresh(b)
    return b


@pytest.fixture
async def closure(db: AsyncSession, branch: Branch, test_admin: User) -> BranchClosure:
    """A fresh closure active today, all completion flags at their default (False)."""
    c = BranchClosure(
        branch_id=branch.id,
        start_date=date.today(),
        end_date=date.today(),
        reason="Test Closure",
        created_by_id=test_admin.id,
    )
    db.add(c)
    await db.commit()
    await db.refresh(c)
    return c


# =============================================================================
# CLOSE TODAY
# =============================================================================

class TestCloseTodayEndpoint:
    """POST /branches/{branch_id}/closures/close-today. Admin only."""

    async def test_close_today_success(self, admin_client: AsyncClient, branch: Branch):
        """Full workflow: every opt-in flag true produces every completion flag true."""
        payload = {
            "reason": "Emergency Closure",
            "closure_documentation": "HVAC failure",
            "send_notifications": True,
            "cancel_events": True,
            "update_external_services": True,
            "notify_partner_organizations": True,
        }
        response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/close-today", json=payload
        )
        assert response.status_code == 201
        data = response.json()
        assert data["branch_id"] == branch.id
        assert data["reason"] == "Emergency Closure"
        assert data["closure_documentation"] == "HVAC failure"
        assert data["start_date"] == data["end_date"]
        assert data["patrons_with_holds_notified"] is True
        assert data["staff_notified"] is True
        assert data["events_canceled"] is True
        assert data["programs_rescheduled"] is True
        assert data["website_updated"] is True
        assert data["phone_message_updated"] is True
        assert data["social_media_updated"] is True
        assert data["google_maps_updated"] is True
        assert data["apple_maps_updated"] is True
        assert data["partner_organizations_notified"] is True

    async def test_close_today_requires_reason(self, admin_client: AsyncClient, branch: Branch):
        response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/close-today",
            json={"closure_documentation": "Some doc", "send_notifications": True},
        )
        assert response.status_code == 422
        body = response.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert any("reason" in e["field"] for e in body["error"]["details"])

    async def test_close_today_with_notifications_disabled(
        self, admin_client: AsyncClient, branch: Branch
    ):
        """Opting out of every side effect leaves every completion flag false."""
        payload = {
            "reason": "Maintenance",
            "send_notifications": False,
            "cancel_events": False,
            "update_external_services": False,
            "notify_partner_organizations": False,
        }
        response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/close-today", json=payload
        )
        assert response.status_code == 201
        data = response.json()
        assert data["patrons_with_holds_notified"] is False
        assert data["staff_notified"] is False
        assert data["events_canceled"] is False
        assert data["programs_rescheduled"] is False
        assert data["website_updated"] is False
        assert data["partner_organizations_notified"] is False

    async def test_close_today_nonexistent_branch(self, admin_client: AsyncClient):
        response = await admin_client.post(
            "/api/v1/branches/999999999/closures/close-today",
            json={"reason": "Test"},
        )
        assert response.status_code == 404


# =============================================================================
# CLOSURE STATUS
# =============================================================================

class TestClosureStatusEndpoint:
    """GET /branches/{branch_id}/closures/{closure_id}/status. Staff+."""

    async def test_get_closure_status(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/status"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["closure"]["id"] == closure.id
        assert data["notifications"] == {
            "patrons_with_holds": False,
            "staff": False,
            "partners": False,
        }
        assert data["external_services"] == {
            "website": False,
            "phone_message": False,
            "social_media": False,
            "google_maps": False,
            "apple_maps": False,
        }
        assert data["event_management"] == {
            "events_canceled": False,
            "programs_rescheduled": False,
        }


# =============================================================================
# CLOSURE COMPLETION
# =============================================================================

class TestClosureCompletionEndpoint:
    """GET /branches/{branch_id}/closures/{closure_id}/completion. Staff+."""

    async def test_completion_all_true_after_full_close_today(
        self, admin_client: AsyncClient, branch: Branch
    ):
        create_response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/close-today",
            json={
                "reason": "Full Workflow",
                "send_notifications": True,
                "cancel_events": True,
                "update_external_services": True,
                "notify_partner_organizations": True,
            },
        )
        closure_id = create_response.json()["id"]

        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure_id}/completion"
        )
        assert response.status_code == 200
        data = response.json()
        required_fields = [
            "patrons_notified",
            "staff_notified",
            "partners_notified",
            "website_updated",
            "phone_updated",
            "social_media_updated",
            "maps_updated",
            "events_handled",
            "all_complete",
        ]
        for field in required_fields:
            assert field in data
        assert data["all_complete"] is True

    async def test_completion_false_when_maps_only_partially_updated(
        self, admin_client: AsyncClient, branch: Branch, db: AsyncSession
    ):
        """maps_updated requires BOTH google_maps and apple_maps."""
        partial = BranchClosure(
            branch_id=branch.id,
            start_date=date.today(),
            end_date=date.today(),
            reason="Partial",
            patrons_with_holds_notified=True,
            staff_notified=True,
            google_maps_updated=True,
            apple_maps_updated=False,
        )
        db.add(partial)
        await db.commit()
        await db.refresh(partial)

        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{partial.id}/completion"
        )
        assert response.status_code == 200
        data = response.json()
        assert data["maps_updated"] is False
        assert data["all_complete"] is False


# =============================================================================
# AFFECTED PATRONS
# =============================================================================

class TestAffectedPatronsEndpoint:
    """GET /branches/{branch_id}/closures/{closure_id}/affected-patrons. Staff+."""

    async def test_get_affected_patrons_empty(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/affected-patrons"
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_affected_patrons_with_holds(
        self,
        admin_client: AsyncClient,
        branch: Branch,
        closure: BranchClosure,
        db: AsyncSession,
        test_patron: User,
        test_catalog_item,
    ):
        hold = Hold(
            user_id=test_patron.id,
            item_id=test_catalog_item.id,
            pickup_location_id=branch.id,
            status=HoldStatus.ready,
            position=1,
        )
        db.add(hold)
        await db.commit()

        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/affected-patrons"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        patron = data[0]
        assert patron["patron_id"] == test_patron.id
        assert patron["patron_name"] == test_patron.full_name
        assert patron["patron_email"] == test_patron.email
        assert patron["item_title"] == test_catalog_item.title


# =============================================================================
# AFFECTED EVENTS
# =============================================================================

class TestAffectedEventsEndpoint:
    """GET /branches/{branch_id}/closures/{closure_id}/affected-events. Staff+."""

    async def test_get_affected_events_empty(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/affected-events"
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_get_affected_events_with_event(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure, db: AsyncSession
    ):
        # The service matches events to a closure by Branch.name (free-text),
        # not a branch_id FK -- see closure_management_service.py:397-402.
        event = Event(
            title="Story Time",
            start_time=datetime.combine(closure.start_date, time(10, 0), tzinfo=timezone.utc),
            end_time=datetime.combine(closure.start_date, time(11, 0), tzinfo=timezone.utc),
            location=branch.name,
            category="Story Time",
            audience="Children",
        )
        db.add(event)
        await db.commit()
        await db.refresh(event)

        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/affected-events"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["event_id"] == event.id
        assert data[0]["title"] == "Story Time"
        assert data[0]["location"] == branch.name


# =============================================================================
# STAFF NOTIFICATIONS
# =============================================================================

class TestStaffNotificationsEndpoint:
    """GET /branches/{branch_id}/closures/{closure_id}/staff-notifications. Staff+."""

    async def test_get_staff_notification_list_empty(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/staff-notifications"
        )
        assert response.status_code == 200
        assert response.json() == []

    async def test_staff_list_includes_contact_info(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure, db: AsyncSession
    ):
        staffer = User(
            email="branch.staffer@example.com",
            password_hash="hashed",
            first_name="Branch",
            last_name="Staffer",
            role=UserRole.STAFF,
            is_active=True,
            work_branch_id=branch.id,
        )
        db.add(staffer)
        await db.commit()
        await db.refresh(staffer)

        response = await admin_client.get(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/staff-notifications"
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        member = data[0]
        assert member["staff_id"] == staffer.id
        assert member["name"] == staffer.full_name
        assert member["email"] == "branch.staffer@example.com"
        assert member["role"] == "staff"


# =============================================================================
# EXTERNAL SERVICES
# =============================================================================

class TestExternalServicesEndpoint:
    """PATCH /branches/{branch_id}/closures/{closure_id}/external-services. Admin only."""

    async def test_update_external_services_all(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        payload = {
            "website": True,
            "phone_message": True,
            "social_media": True,
            "google_maps": True,
            "apple_maps": True,
        }
        response = await admin_client.patch(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/external-services",
            json=payload,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["website_updated"] is True
        assert data["phone_message_updated"] is True
        assert data["social_media_updated"] is True
        assert data["google_maps_updated"] is True
        assert data["apple_maps_updated"] is True

    async def test_update_partial_services(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.patch(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/external-services",
            json={"website": True, "social_media": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["website_updated"] is True
        assert data["social_media_updated"] is True
        assert data["phone_message_updated"] is False
        assert data["google_maps_updated"] is False
        assert data["apple_maps_updated"] is False

    async def test_update_maps_only(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.patch(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/external-services",
            json={"google_maps": True, "apple_maps": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["google_maps_updated"] is True
        assert data["apple_maps_updated"] is True
        assert data["website_updated"] is False

    async def test_update_external_services_does_not_unset_flags(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure, db: AsyncSession
    ):
        """The service only ever turns flags on (`if website: closure.website_updated = True`);
        sending False for an already-true flag is a no-op, not a clear. Checklist
        semantics, not a toggle -- locking this in so it isn't "fixed" by accident.
        """
        closure.website_updated = True
        db.add(closure)
        await db.commit()

        response = await admin_client.patch(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/external-services",
            json={"website": False, "social_media": True},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["website_updated"] is True
        assert data["social_media_updated"] is True


# =============================================================================
# PARTNER NOTIFICATIONS
# =============================================================================

class TestPartnerNotificationsEndpoint:
    """POST /branches/{branch_id}/closures/{closure_id}/notify-partners. Admin only."""

    async def test_notify_specific_partners(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/notify-partners",
            json={"partner_list": ["Partner A", "Partner B"]},
        )
        assert response.status_code == 200
        assert response.json()["partner_organizations_notified"] is True

    async def test_notify_all_partners(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        """partner_list=None ("all configured partners") is a stub today -- the
        service sets the same completion flag regardless of list content. Not
        a bug (explicitly a dummy integration point, see
        closure_management_service.py:491-498), just documenting current
        behavior rather than asserting content-based routing that doesn't
        exist yet.
        """
        response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/notify-partners",
            json={"partner_list": None},
        )
        assert response.status_code == 200
        assert response.json()["partner_organizations_notified"] is True


# =============================================================================
# REOPENING
# =============================================================================

class TestReopeningEndpoint:
    """POST /branches/{branch_id}/closures/{closure_id}/schedule-reopening. Admin only."""

    async def test_schedule_reopening(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/schedule-reopening",
            json={"reopening_announcement": "We are happy to reopen!"},
        )
        assert response.status_code == 200
        assert response.json()["reopening_announcement"] == "We are happy to reopen!"

    async def test_schedule_reopening_requires_message(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure
    ):
        response = await admin_client.post(
            f"/api/v1/branches/{branch.id}/closures/{closure.id}/schedule-reopening",
            json={},
        )
        assert response.status_code == 422
        body = response.json()
        assert any("reopening_announcement" in e["field"] for e in body["error"]["details"])


# =============================================================================
# ACTIVE CLOSURES
# =============================================================================

class TestActiveClosuresEndpoint:
    """GET /branches/{branch_id}/closures/active. Staff+."""

    async def test_get_active_closures(
        self, admin_client: AsyncClient, branch: Branch, closure: BranchClosure, db: AsyncSession
    ):
        past = BranchClosure(
            branch_id=branch.id,
            start_date=date.today() - timedelta(days=30),
            end_date=date.today() - timedelta(days=29),
            reason="Old Closure",
        )
        db.add(past)
        await db.commit()

        response = await admin_client.get(f"/api/v1/branches/{branch.id}/closures/active")
        assert response.status_code == 200
        data = response.json()
        ids = [c["id"] for c in data]
        assert closure.id in ids
        assert past.id not in ids

        active = next(c for c in data if c["id"] == closure.id)
        required_fields = [
            "id",
            "branch_id",
            "reason",
            "start_date",
            "end_date",
            "patrons_with_holds_notified",
            "staff_notified",
            "website_updated",
        ]
        for field in required_fields:
            assert field in active

    async def test_get_active_closures_empty_for_fresh_branch(
        self, admin_client: AsyncClient, db: AsyncSession, library_system: LibrarySystem
    ):
        other_branch = Branch(
            library_system_id=library_system.id, code="OTHER", name="Other Branch"
        )
        db.add(other_branch)
        await db.commit()
        await db.refresh(other_branch)

        response = await admin_client.get(
            f"/api/v1/branches/{other_branch.id}/closures/active"
        )
        assert response.status_code == 200
        assert response.json() == []


# =============================================================================
# CROSS-CUTTING: AUTHORIZATION
#
# The original suite never actually exercised auth (every assert was
# commented out). These parametrized checks are new coverage, not a port --
# each endpoint's own class above focuses on response shape instead of
# repeating the same role check nine times.
# =============================================================================

ADMIN_ACTION_ENDPOINTS = [
    ("POST", "/api/v1/branches/{branch_id}/closures/close-today", {"reason": "Test Closure"}),
    (
        "PATCH",
        "/api/v1/branches/{branch_id}/closures/{closure_id}/external-services",
        {"website": True},
    ),
    ("POST", "/api/v1/branches/{branch_id}/closures/{closure_id}/notify-partners", {}),
    (
        "POST",
        "/api/v1/branches/{branch_id}/closures/{closure_id}/schedule-reopening",
        {"reopening_announcement": "Back soon"},
    ),
]
ADMIN_ACTION_IDS = ["close-today", "external-services", "notify-partners", "schedule-reopening"]

STAFF_READ_ENDPOINTS = [
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/status", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/completion", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/affected-patrons", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/affected-events", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/staff-notifications", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/active", None),
]
STAFF_READ_IDS = [
    "status", "completion", "affected-patrons", "affected-events", "staff-notifications", "active",
]

ALL_CLOSURE_ENDPOINTS = ADMIN_ACTION_ENDPOINTS + STAFF_READ_ENDPOINTS
ALL_CLOSURE_IDS = ADMIN_ACTION_IDS + STAFF_READ_IDS


class TestClosureEndpointAuthorization:
    """Every closure-workflow endpoint requires at least staff auth; the
    mutating ones require admin. Verified here for all nine routes at once.
    """

    @pytest.mark.parametrize("method,path_template,payload", ALL_CLOSURE_ENDPOINTS, ids=ALL_CLOSURE_IDS)
    async def test_unauthenticated_requests_rejected(
        self,
        client: AsyncClient,
        branch: Branch,
        closure: BranchClosure,
        method: str,
        path_template: str,
        payload: dict | None,
    ):
        path = path_template.format(branch_id=branch.id, closure_id=closure.id)
        response = await client.request(method, path, json=payload)
        assert response.status_code == 401

    @pytest.mark.parametrize("method,path_template,payload", ADMIN_ACTION_ENDPOINTS, ids=ADMIN_ACTION_IDS)
    async def test_admin_actions_reject_staff_role(
        self,
        staff_client: AsyncClient,
        branch: Branch,
        closure: BranchClosure,
        method: str,
        path_template: str,
        payload: dict | None,
    ):
        path = path_template.format(branch_id=branch.id, closure_id=closure.id)
        response = await staff_client.request(method, path, json=payload)
        assert response.status_code == 403

    @pytest.mark.parametrize("method,path_template,payload", STAFF_READ_ENDPOINTS, ids=STAFF_READ_IDS)
    async def test_staff_reads_reject_patron_role(
        self,
        patron_client: AsyncClient,
        branch: Branch,
        closure: BranchClosure,
        method: str,
        path_template: str,
        payload: dict | None,
    ):
        path = path_template.format(branch_id=branch.id, closure_id=closure.id)
        response = await patron_client.request(method, path, json=payload)
        assert response.status_code == 403


# =============================================================================
# CROSS-CUTTING: NOT-FOUND SEMANTICS
# =============================================================================

READ_404_ENDPOINTS = [
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/status", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/completion", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/affected-patrons", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/affected-events", None),
    ("GET", "/api/v1/branches/{branch_id}/closures/{closure_id}/staff-notifications", None),
]
READ_404_IDS = ["status", "completion", "affected-patrons", "affected-events", "staff-notifications"]

WRITE_404_ENDPOINTS = [
    (
        "PATCH",
        "/api/v1/branches/{branch_id}/closures/{closure_id}/external-services",
        {"website": True},
    ),
    ("POST", "/api/v1/branches/{branch_id}/closures/{closure_id}/notify-partners", {}),
    (
        "POST",
        "/api/v1/branches/{branch_id}/closures/{closure_id}/schedule-reopening",
        {"reopening_announcement": "Back soon"},
    ),
]
WRITE_404_IDS = ["external-services", "notify-partners", "schedule-reopening"]

NONEXISTENT_CLOSURE_ID = 999_999_999


class TestClosureNotFoundBehavior:
    """A missing closure_id must 404 everywhere: every closure route wraps its
    service call in try/except ValueError -> HTTPException(404) (e.g.
    branches.py:879-882). The three write endpoints below lacked that wrap
    until fix/audit-routing added it; these tests hold the line.
    """

    @pytest.mark.parametrize("method,path_template,payload", READ_404_ENDPOINTS, ids=READ_404_IDS)
    async def test_read_endpoints_404_for_missing_closure(
        self,
        admin_client: AsyncClient,
        branch: Branch,
        method: str,
        path_template: str,
        payload: dict | None,
    ):
        path = path_template.format(branch_id=branch.id, closure_id=NONEXISTENT_CLOSURE_ID)
        response = await admin_client.request(method, path, json=payload)
        assert response.status_code == 404
        message = response.json()["error"]["message"]
        assert "not found" in message.lower()

    @pytest.mark.parametrize("method,path_template,payload", WRITE_404_ENDPOINTS, ids=WRITE_404_IDS)
    async def test_write_endpoints_404_for_missing_closure(
        self,
        admin_client: AsyncClient,
        branch: Branch,
        method: str,
        path_template: str,
        payload: dict | None,
    ):
        path = path_template.format(branch_id=branch.id, closure_id=NONEXISTENT_CLOSURE_ID)
        response = await admin_client.request(method, path, json=payload)
        assert response.status_code == 404
