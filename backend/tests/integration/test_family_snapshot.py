# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for the parent-onboarding family-snapshot pane.

Covers the new endpoints introduced in feat/session-family-snapshot:

  GET  /api/v1/parent-onboarding/sessions/{session_id}/family-snapshot
  POST /api/v1/parent-onboarding/sessions/{session_id}/family-snapshot/reveal
  GET  /api/v1/parent-onboarding/patrons/{patron_id}/consent/family-snapshot
  POST /api/v1/parent-onboarding/patrons/{patron_id}/consent/family-snapshot

Auth: uses ``staff_client`` (dependency-overrides ``get_current_user``;
see ``feedback_l30_test_auth_token_revocation``).
"""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models.parent_onboarding import ParentOnboardingSession
from app.models.patron_consent import PatronConsent
from app.models.pii_access_log import PIIAccessLog
from app.models.program_family import ProgramFamilyGroup, ProgramFamilyMember


@pytest.fixture
async def fs_session(test_db, test_patron, test_staff):
    """A scheduled onboarding session anchored to ``test_patron``."""
    session = ParentOnboardingSession(
        patron_id=test_patron.id,
        staff_id=test_staff.id,
        branch_id=1,
        status="scheduled",
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
        baby_age_months=7,
        family_situation_notes=(
            "Two adults, two children. Infant on visit form. "
            "Patron mentioned grandmother lives next door and helps "
            "with childcare on weekday mornings."
        ),
    )
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)
    return session


@pytest.fixture
async def fs_family_group(test_db, test_patron):
    """A ProgramFamilyGroup with one parent + two children rows."""
    group = ProgramFamilyGroup(
        parent_user_id=test_patron.id,
        name="Test Family",
    )
    test_db.add(group)
    await test_db.flush()

    members = [
        ProgramFamilyMember(
            family_group_id=group.id,
            first_name="Test",
            age_range="0-5",
            is_parent=True,
        ),
        ProgramFamilyMember(
            family_group_id=group.id,
            first_name="Mia",
            age_range="0-5",
            is_parent=False,
        ),
        ProgramFamilyMember(
            family_group_id=group.id,
            first_name="Eli",
            age_range="6-8",
            is_parent=False,
        ),
    ]
    for m in members:
        test_db.add(m)
    await test_db.commit()
    await test_db.refresh(group)
    return group


@pytest.fixture
async def fs_active_consent(test_db, test_patron, test_staff):
    """Active granted family-snapshot consent on the test patron."""
    row = PatronConsent(
        patron_id=test_patron.id,
        consent_type="family_snapshot",
        granted=True,
        recorded_by_staff_id=test_staff.id,
    )
    test_db.add(row)
    await test_db.commit()
    await test_db.refresh(row)
    return row


@pytest.mark.integration
class TestFamilySnapshotRead:
    """``GET /sessions/{id}/family-snapshot`` -- the redacted path."""

    async def test_returns_consent_missing_payload_when_no_consent(
        self, staff_client, test_db, test_patron, fs_session,
    ):
        # Patron has language_preference set but no consent row.
        test_patron.language_preference = "es"
        await test_db.commit()

        response = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{fs_session.id}/family-snapshot"
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["consent_status"] == "not_requested"
        assert body["sensitive_fields_hidden"] is True
        # Language travels regardless of consent -- needed for the convo.
        assert body["language_preference"] == "es"
        assert body["language_preference_label"] == "Español"
        # Sensitive fields are omitted.
        assert body["household_size"] is None
        assert body["household_members"] == []
        assert body["household_notes_summary"] is None
        assert body["baby_age_months"] is None

    async def test_returns_redacted_payload_with_consent_and_family(
        self,
        staff_client,
        test_db,
        test_patron,
        fs_session,
        fs_family_group,
        fs_active_consent,
    ):
        response = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{fs_session.id}/family-snapshot"
        )
        assert response.status_code == 200, response.text
        body = response.json()

        assert body["consent_status"] == "granted"
        assert body["sensitive_fields_hidden"] is True
        # Children present but first names are initial-redacted (M. / E.).
        names = [m["first_name_revealed"] for m in body["household_members"]]
        assert "M." in names
        assert "E." in names
        # No raw first names leaked.
        assert "Mia" not in names
        assert "Eli" not in names
        # Household size includes patron + 2 children + 1 parent-in-group.
        assert body["household_size"] is not None
        assert body["household_size"] >= 3
        # Notes are summarized -- truncated to keep screenshot-safe.
        assert body["household_notes_summary"] is not None
        assert len(body["household_notes_summary"]) <= 64  # 60 + ellipsis margin
        assert body["baby_age_months"] == 7

    async def test_404_when_session_id_unknown(self, staff_client):
        response = await staff_client.get(
            "/api/v1/parent-onboarding/sessions/9999999/family-snapshot"
        )
        assert response.status_code == 404

    async def test_writes_pii_access_log_row(
        self,
        staff_client,
        test_db,
        test_patron,
        test_staff,
        fs_session,
        fs_active_consent,
    ):
        response = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{fs_session.id}/family-snapshot"
        )
        assert response.status_code == 200

        result = await test_db.execute(
            select(PIIAccessLog).where(
                PIIAccessLog.subject_type == "parent_onboarding.family_snapshot",
                PIIAccessLog.patron_id == test_patron.id,
                PIIAccessLog.action == "read",
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) >= 1
        row = rows[-1]
        assert row.user_id == test_staff.id
        assert row.subject_id == fs_session.id


@pytest.mark.integration
class TestFamilySnapshotReveal:
    """``POST /family-snapshot/reveal`` -- the unredacted path."""

    async def test_403_when_no_consent_on_file(
        self, staff_client, test_db, fs_session,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{fs_session.id}"
            "/family-snapshot/reveal",
            json=None,
        )
        assert response.status_code == 403

    async def test_full_first_names_returned_when_consent_granted(
        self,
        staff_client,
        test_db,
        fs_session,
        fs_family_group,
        fs_active_consent,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{fs_session.id}"
            "/family-snapshot/reveal",
            json=None,
        )
        assert response.status_code == 200, response.text
        body = response.json()

        names = [m["first_name_revealed"] for m in body["household_members"]]
        assert "Mia" in names
        assert "Eli" in names
        assert body["sensitive_fields_hidden"] is False
        # Notes come back at full length on the reveal payload.
        assert body["household_notes_summary"] is not None
        assert "grandmother" in body["household_notes_summary"]

    async def test_writes_reveal_audit_row(
        self,
        staff_client,
        test_db,
        test_patron,
        test_staff,
        fs_session,
        fs_active_consent,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{fs_session.id}"
            "/family-snapshot/reveal",
            json=None,
        )
        assert response.status_code == 200

        result = await test_db.execute(
            select(PIIAccessLog).where(
                PIIAccessLog.subject_type
                == "parent_onboarding.family_snapshot.reveal",
                PIIAccessLog.patron_id == test_patron.id,
                PIIAccessLog.action == "reveal",
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) >= 1
        assert rows[-1].user_id == test_staff.id


@pytest.mark.integration
class TestPatronConsent:
    """Consent endpoints under ``/patrons/{id}/consent/family-snapshot``."""

    async def test_get_returns_not_requested_when_no_row(
        self, staff_client, test_patron,
    ):
        response = await staff_client.get(
            f"/api/v1/parent-onboarding/patrons/{test_patron.id}"
            "/consent/family-snapshot"
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["consent_status"] == "not_requested"
        assert body["consent_recorded_at"] is None

    async def test_record_granted_creates_row_and_returns_201(
        self, staff_client, test_db, test_patron, test_staff,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/patrons/{test_patron.id}"
            "/consent/family-snapshot",
            json={"granted": True, "notes": "verbal consent in session"},
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["granted"] is True
        assert body["recorded_by_staff_id"] == test_staff.id
        assert body["revoked_at"] is None

        # And the GET now reflects granted.
        status_resp = await staff_client.get(
            f"/api/v1/parent-onboarding/patrons/{test_patron.id}"
            "/consent/family-snapshot"
        )
        assert status_resp.status_code == 200
        assert status_resp.json()["consent_status"] == "granted"

    async def test_revoke_then_regrant_creates_new_row(
        self, staff_client, test_db, test_patron, fs_active_consent,
    ):
        # First, revoke.
        revoke = await staff_client.post(
            f"/api/v1/parent-onboarding/patrons/{test_patron.id}"
            "/consent/family-snapshot",
            json={"granted": False},
        )
        assert revoke.status_code == 201

        get1 = await staff_client.get(
            f"/api/v1/parent-onboarding/patrons/{test_patron.id}"
            "/consent/family-snapshot"
        )
        assert get1.json()["consent_status"] == "revoked"

        # Re-grant.
        regrant = await staff_client.post(
            f"/api/v1/parent-onboarding/patrons/{test_patron.id}"
            "/consent/family-snapshot",
            json={"granted": True},
        )
        assert regrant.status_code == 201

        get2 = await staff_client.get(
            f"/api/v1/parent-onboarding/patrons/{test_patron.id}"
            "/consent/family-snapshot"
        )
        assert get2.json()["consent_status"] == "granted"

    async def test_404_when_patron_unknown(self, staff_client):
        response = await staff_client.post(
            "/api/v1/parent-onboarding/patrons/9999999"
            "/consent/family-snapshot",
            json={"granted": True},
        )
        assert response.status_code == 404
