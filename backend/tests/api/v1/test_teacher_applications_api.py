# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API tests for /api/v1/teacher-applications endpoints.

Covers:
- POST happy path (201 + confirmation email sent)
- POST when caller already TEACHER -> 409
- POST when caller has a pending app -> 409
- POST when caller has an approved app -> 409
- POST after a denied app -> 201 (re-apply OK)
- POST with invalid school_id -> 400
- GET /me returns latest application
- Staff approve: flips users.role to TEACHER + sets school_id, sends approval email
- Staff approve missing school_id -> 400
- Staff deny: requires denial_reason, sends denial email
- Staff list with status filter
- Schools listing returns active school partners only
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.outreach import OutreachPartner, OutreachPartnerStatus, PartnerType
from app.models.teacher_application import (
    TeacherApplication,
    TeacherApplicationStatus,
)
from app.models.user import UserRole


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def patron_client(client, test_patron):
    """Client authenticated as the patron fixture."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client(client, test_staff):
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
async def test_school(test_db):
    """Create an active SCHOOL outreach_partner for tests."""
    school = OutreachPartner(
        name="Test Elementary",
        partner_type=PartnerType.SCHOOL.value,
        status=OutreachPartnerStatus.ACTIVE.value,
    )
    test_db.add(school)
    await test_db.commit()
    await test_db.refresh(school)
    return school


async def _insert_app(
    test_db,
    user_id: int,
    status: TeacherApplicationStatus,
    *,
    school_id: int | None = None,
    denial_reason: str | None = None,
) -> TeacherApplication:
    row = TeacherApplication(
        user_id=user_id,
        school_id=school_id,
        status=status,
        grade_level="3rd",
        subject="reading",
        denial_reason=denial_reason,
        created_at=datetime.now(timezone.utc),
    )
    test_db.add(row)
    await test_db.commit()
    await test_db.refresh(row)
    return row


# ============================================================================
# Submit endpoint
# ============================================================================


class TestSubmitTeacherApplication:
    @pytest.mark.asyncio
    async def test_submit_happy_path(self, patron_client, test_school):
        with patch(
            "app.api.v1.teacher_applications.send_teacher_application_received",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await patron_client.post(
                "/api/v1/teacher-applications",
                json={
                    "school_id": test_school.id,
                    "grade_level": "K-2",
                    "subject": "reading",
                    "classroom_size": 24,
                    "notes": "I run a literacy program.",
                },
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "pending"
        assert body["school_id"] == test_school.id
        assert body["school_name"] == "Test Elementary"
        assert body["grade_level"] == "K-2"
        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_submit_email_failure_is_nonfatal(self, patron_client, test_school):
        with patch(
            "app.api.v1.teacher_applications.send_teacher_application_received",
            new=AsyncMock(side_effect=RuntimeError("smtp down")),
        ):
            resp = await patron_client.post(
                "/api/v1/teacher-applications",
                json={"school_id": test_school.id},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_submit_already_teacher_returns_409(
        self, patron_client, test_db, test_patron, test_school
    ):
        test_patron.role = UserRole.TEACHER
        test_db.add(test_patron)
        await test_db.commit()
        resp = await patron_client.post(
            "/api/v1/teacher-applications",
            json={"school_id": test_school.id},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_submit_duplicate_pending_returns_409(
        self, patron_client, test_db, test_patron, test_school
    ):
        await _insert_app(test_db, test_patron.id, TeacherApplicationStatus.pending)
        resp = await patron_client.post(
            "/api/v1/teacher-applications",
            json={"school_id": test_school.id},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_submit_when_approved_returns_409(
        self, patron_client, test_db, test_patron, test_school
    ):
        await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.approved,
            school_id=test_school.id,
        )
        resp = await patron_client.post(
            "/api/v1/teacher-applications",
            json={"school_id": test_school.id},
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_submit_after_denied_succeeds(
        self, patron_client, test_db, test_patron, test_school
    ):
        await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.denied,
            denial_reason="missing docs",
        )
        with patch(
            "app.api.v1.teacher_applications.send_teacher_application_received",
            new=AsyncMock(return_value=True),
        ):
            resp = await patron_client.post(
                "/api/v1/teacher-applications",
                json={"school_id": test_school.id},
            )
        assert resp.status_code == 201

    @pytest.mark.asyncio
    async def test_submit_invalid_school_id_returns_400(self, patron_client):
        resp = await patron_client.post(
            "/api/v1/teacher-applications",
            json={"school_id": 999_999},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_submit_without_school_id_ok_for_freetext(
        self, patron_client
    ):
        with patch(
            "app.api.v1.teacher_applications.send_teacher_application_received",
            new=AsyncMock(return_value=True),
        ):
            resp = await patron_client.post(
                "/api/v1/teacher-applications",
                json={
                    "school_name_freetext": "New Hope Academy",
                    "grade_level": "5th",
                },
            )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["school_id"] is None
        assert body["school_name_freetext"] == "New Hope Academy"


# ============================================================================
# /me endpoint
# ============================================================================


class TestGetMyApplication:
    @pytest.mark.asyncio
    async def test_returns_null_when_no_application(self, patron_client):
        resp = await patron_client.get("/api/v1/teacher-applications/me")
        assert resp.status_code == 200
        assert resp.json() is None

    @pytest.mark.asyncio
    async def test_returns_latest_application(
        self, patron_client, test_db, test_patron, test_school
    ):
        await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.denied,
            denial_reason="r",
        )
        latest = await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.pending,
            school_id=test_school.id,
        )
        resp = await patron_client.get("/api/v1/teacher-applications/me")
        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == latest.id
        assert body["status"] == "pending"


# ============================================================================
# Staff approve / deny
# ============================================================================


class TestStaffApprove:
    @pytest.mark.asyncio
    async def test_approve_flips_role_and_school(
        self, staff_client, test_db, test_patron, test_school
    ):
        app_row = await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.pending,
            school_id=test_school.id,
        )
        with patch(
            "app.api.v1.teacher_applications.send_teacher_application_approved",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await staff_client.post(
                f"/api/v1/teacher-applications/staff/{app_row.id}/approve",
                json={"status": "approved", "school_id": test_school.id},
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "approved"
        await test_db.refresh(test_patron)
        assert test_patron.role == UserRole.TEACHER
        assert test_patron.school_id == test_school.id
        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_approve_without_school_id_returns_400(
        self, staff_client, test_db, test_patron
    ):
        # application has NO school_id and reviewer didn't supply one
        app_row = await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.pending,
        )
        resp = await staff_client.post(
            f"/api/v1/teacher-applications/staff/{app_row.id}/approve",
            json={"status": "approved"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_approve_already_decided_returns_400(
        self, staff_client, test_db, test_patron, test_school
    ):
        app_row = await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.approved,
            school_id=test_school.id,
        )
        resp = await staff_client.post(
            f"/api/v1/teacher-applications/staff/{app_row.id}/approve",
            json={"status": "approved", "school_id": test_school.id},
        )
        assert resp.status_code == 400


class TestStaffDeny:
    @pytest.mark.asyncio
    async def test_deny_with_reason_sends_email(
        self, staff_client, test_db, test_patron
    ):
        app_row = await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.pending,
        )
        with patch(
            "app.api.v1.teacher_applications.send_teacher_application_denied",
            new=AsyncMock(return_value=True),
        ) as mock_send:
            resp = await staff_client.post(
                f"/api/v1/teacher-applications/staff/{app_row.id}/deny",
                json={
                    "status": "denied",
                    "denial_reason": "Need verifiable school employment.",
                },
            )
        assert resp.status_code == 200, resp.text
        assert resp.json()["status"] == "denied"
        await test_db.refresh(test_patron)
        # Deny must NOT change role.
        assert test_patron.role == UserRole.PATRON
        mock_send.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_deny_without_reason_422(
        self, staff_client, test_db, test_patron
    ):
        app_row = await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.pending,
        )
        resp = await staff_client.post(
            f"/api/v1/teacher-applications/staff/{app_row.id}/deny",
            json={"status": "denied"},
        )
        assert resp.status_code == 422


# ============================================================================
# Staff list + schools list
# ============================================================================


class TestStaffList:
    @pytest.mark.asyncio
    async def test_filter_by_status(
        self, staff_client, test_db, test_patron, test_school
    ):
        await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.pending,
        )
        await _insert_app(
            test_db, test_patron.id, TeacherApplicationStatus.denied,
            denial_reason="r",
        )
        resp = await staff_client.get(
            "/api/v1/teacher-applications/staff?status=pending"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["applications"][0]["status"] == "pending"


class TestSchoolsList:
    @pytest.mark.asyncio
    async def test_lists_active_school_partners_only(
        self, patron_client, test_db, test_school
    ):
        # Add a non-school partner that should NOT appear
        nonschool = OutreachPartner(
            name="Senior Center A",
            partner_type=PartnerType.SENIOR_CENTER.value,
            status=OutreachPartnerStatus.ACTIVE.value,
        )
        inactive = OutreachPartner(
            name="Closed School",
            partner_type=PartnerType.SCHOOL.value,
            status=OutreachPartnerStatus.INACTIVE.value,
        )
        test_db.add_all([nonschool, inactive])
        await test_db.commit()

        resp = await patron_client.get("/api/v1/teacher-applications/schools")
        assert resp.status_code == 200
        names = {row["name"] for row in resp.json()}
        assert "Test Elementary" in names
        assert "Senior Center A" not in names
        assert "Closed School" not in names
