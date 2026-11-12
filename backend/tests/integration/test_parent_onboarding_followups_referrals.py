# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for parent-onboarding session follow-ups + referrals.

Covers the new endpoints introduced in feat/session-followup-referrals:

  POST   /api/v1/parent-onboarding/sessions/{id}/followups
  GET    /api/v1/parent-onboarding/sessions/{id}/followups
  PATCH  /api/v1/parent-onboarding/followups/{id}
  POST   /api/v1/parent-onboarding/followups/{id}/complete
  DELETE /api/v1/parent-onboarding/followups/{id}

  POST   /api/v1/parent-onboarding/sessions/{id}/referrals
  GET    /api/v1/parent-onboarding/sessions/{id}/referrals
  PATCH  /api/v1/parent-onboarding/referrals/{id}
  DELETE /api/v1/parent-onboarding/referrals/{id}

  GET    /api/v1/parent-onboarding/partner-agencies?q=...

Plus the reminder task in parent_onboarding_followup_reminder_tasks.py.

Auth: uses the existing `staff_client` fixture which dependency-overrides
`get_current_user` (see feedback_l30_test_auth_token_revocation -- real
login flows 401 in tests because Redis is absent).
"""
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.parent_onboarding import (
    ParentOnboardingSession, ParentOnboardingStatus,
    ParentOnboardingFollowup, ParentOnboardingReferral, PartnerAgency,
    FollowupStatus, ReferralStatus,
)


@pytest.fixture
async def test_session(test_db, test_patron, test_staff):
    """A scheduled onboarding session that the new follow-ups + referrals
    attach to."""
    session = ParentOnboardingSession(
        patron_id=test_patron.id,
        staff_id=test_staff.id,
        branch_id=1,
        status=ParentOnboardingStatus.scheduled,
        scheduled_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    test_db.add(session)
    await test_db.commit()
    await test_db.refresh(session)
    return session


@pytest.fixture
async def test_agency(test_db):
    agency = PartnerAgency(
        name="Eastside WIC Clinic",
        slug="eastside-wic-clinic",
        agency_type="wic",
        is_active=True,
    )
    test_db.add(agency)
    await test_db.commit()
    await test_db.refresh(agency)
    return agency


@pytest.mark.integration
class TestFollowupRoutes:
    """CRUD on parent_onboarding_followups."""

    async def test_create_returns_201_with_assignee_name(
        self, staff_client, test_db, test_session, test_staff,
    ):
        payload = {
            "title": "Confirm WIC packet",
            "description": "Patron took the printed packet.",
            "assignee_id": test_staff.id,
            "due_date": (date.today() + timedelta(days=7)).isoformat(),
            "priority": "normal",
        }
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/followups",
            json=payload,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        # The compose helper resolves assignee_name from the eager-loaded
        # user object so we don't 500 with MissingGreenlet.
        assert body["assignee_id"] == test_staff.id
        assert body["assignee_name"], "expected assignee_name to be populated"
        assert body["session_id"] == test_session.id
        assert body["status"] == "open"
        assert body["priority"] == "normal"

    async def test_create_on_missing_session_returns_404(
        self, staff_client,
    ):
        response = await staff_client.post(
            "/api/v1/parent-onboarding/sessions/999999/followups",
            json={
                "title": "x",
                "due_date": date.today().isoformat(),
            },
        )
        assert response.status_code == 404, response.text

    async def test_create_rejects_extra_fields(
        self, staff_client, test_session,
    ):
        """StrictInputSchema (extra=forbid) catches typos at request time."""
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/followups",
            json={
                "title": "x",
                "due_date": date.today().isoformat(),
                "bogus_field": "abc",
            },
        )
        assert response.status_code == 422

    async def test_list_returns_session_followups_sorted_by_due(
        self, staff_client, test_db, test_session, test_staff,
    ):
        # Insert three follow-ups out of order.
        late = ParentOnboardingFollowup(
            session_id=test_session.id, title="late",
            due_date=date.today() + timedelta(days=10),
            assignee_id=test_staff.id,
        )
        early = ParentOnboardingFollowup(
            session_id=test_session.id, title="early",
            due_date=date.today() + timedelta(days=1),
            assignee_id=test_staff.id,
        )
        mid = ParentOnboardingFollowup(
            session_id=test_session.id, title="mid",
            due_date=date.today() + timedelta(days=5),
            assignee_id=test_staff.id,
        )
        test_db.add_all([late, early, mid])
        await test_db.commit()

        response = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/followups"
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 3
        titles = [f["title"] for f in body["followups"]]
        assert titles == ["early", "mid", "late"]

    async def test_complete_marks_status_and_records_note(
        self, staff_client, test_db, test_session, test_staff,
    ):
        followup = ParentOnboardingFollowup(
            session_id=test_session.id, title="x",
            due_date=date.today(), assignee_id=test_staff.id,
        )
        test_db.add(followup)
        await test_db.commit()
        await test_db.refresh(followup)
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/followups/{followup.id}/complete",
            json={"completion_note": "Done."},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["status"] == "completed"
        assert body["completion_note"] == "Done."
        assert body["completed_at"] is not None

    async def test_patch_can_change_status_to_in_progress(
        self, staff_client, test_db, test_session, test_staff,
    ):
        followup = ParentOnboardingFollowup(
            session_id=test_session.id, title="x",
            due_date=date.today(), assignee_id=test_staff.id,
        )
        test_db.add(followup)
        await test_db.commit()
        await test_db.refresh(followup)
        response = await staff_client.patch(
            f"/api/v1/parent-onboarding/followups/{followup.id}",
            json={"status": "in_progress"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "in_progress"

    async def test_patch_rejects_bad_status(
        self, staff_client, test_db, test_session, test_staff,
    ):
        followup = ParentOnboardingFollowup(
            session_id=test_session.id, title="x",
            due_date=date.today(), assignee_id=test_staff.id,
        )
        test_db.add(followup)
        await test_db.commit()
        await test_db.refresh(followup)
        response = await staff_client.patch(
            f"/api/v1/parent-onboarding/followups/{followup.id}",
            json={"status": "not_a_real_status"},
        )
        assert response.status_code == 422

    async def test_delete_returns_204(
        self, staff_client, test_db, test_session, test_staff,
    ):
        followup = ParentOnboardingFollowup(
            session_id=test_session.id, title="x",
            due_date=date.today(), assignee_id=test_staff.id,
        )
        test_db.add(followup)
        await test_db.commit()
        await test_db.refresh(followup)
        followup_id = followup.id
        response = await staff_client.delete(
            f"/api/v1/parent-onboarding/followups/{followup_id}"
        )
        assert response.status_code == 204
        # And it really is gone.
        response = await staff_client.patch(
            f"/api/v1/parent-onboarding/followups/{followup_id}",
            json={"title": "ghost"},
        )
        assert response.status_code == 404


@pytest.mark.integration
class TestReferralRoutes:

    async def test_create_with_partner_agency_id(
        self, staff_client, test_session, test_agency,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/referrals",
            json={
                "partner_agency_id": test_agency.id,
                "purpose": "WIC enrollment",
                "warm_handoff": True,
                "patron_consent_to_share": True,
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["partner_agency_id"] == test_agency.id
        # partner_agency_name should be eager-loaded via the response composer.
        assert body["partner_agency_name"] == test_agency.name
        assert body["agency_name_freetext"] is None
        assert body["status"] == "made"

    async def test_create_with_freetext_only(
        self, staff_client, test_session,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/referrals",
            json={
                "agency_name_freetext": "Postpartum Support Network",
                "purpose": "support group referral",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["partner_agency_id"] is None
        assert body["agency_name_freetext"] == "Postpartum Support Network"

    async def test_create_rejects_when_both_agency_fields_blank(
        self, staff_client, test_session,
    ):
        """The model_validator on ReferralCreate enforces the
        (partner_agency_id IS NOT NULL OR agency_name_freetext IS NOT NULL)
        rule at request validation time. The CHECK constraint is the
        belt-and-suspenders defense at the DB layer."""
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/referrals",
            json={"purpose": "x"},
        )
        assert response.status_code == 422

    async def test_create_rejects_unknown_partner_agency_id(
        self, staff_client, test_session,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/referrals",
            json={
                "partner_agency_id": 999999,
                "purpose": "x",
            },
        )
        assert response.status_code == 400

    async def test_list_returns_session_referrals(
        self, staff_client, test_db, test_session, test_agency,
    ):
        r1 = ParentOnboardingReferral(
            session_id=test_session.id,
            partner_agency_id=test_agency.id,
            purpose="WIC",
            status=ReferralStatus.made.value,
        )
        r2 = ParentOnboardingReferral(
            session_id=test_session.id,
            agency_name_freetext="Diaper Bank",
            purpose="diapers",
            status=ReferralStatus.scheduled.value,
        )
        test_db.add_all([r1, r2])
        await test_db.commit()
        response = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/referrals"
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2

    async def test_delete_returns_204(
        self, staff_client, test_db, test_session, test_agency,
    ):
        r = ParentOnboardingReferral(
            session_id=test_session.id,
            partner_agency_id=test_agency.id,
            purpose="x",
        )
        test_db.add(r)
        await test_db.commit()
        await test_db.refresh(r)
        response = await staff_client.delete(
            f"/api/v1/parent-onboarding/referrals/{r.id}"
        )
        assert response.status_code == 204


@pytest.mark.integration
class TestPartnerAgencyAutocomplete:

    async def test_search_returns_only_active(
        self, staff_client, test_db, test_agency,
    ):
        inactive = PartnerAgency(
            name="Defunct Agency",
            slug="defunct",
            is_active=False,
        )
        test_db.add(inactive)
        await test_db.commit()
        response = await staff_client.get(
            "/api/v1/parent-onboarding/partner-agencies?q=agency"
        )
        assert response.status_code == 200, response.text
        body = response.json()
        names = [a["name"] for a in body["agencies"]]
        assert "Defunct Agency" not in names

    async def test_search_ilikes_on_name_or_slug(
        self, staff_client, test_db, test_agency,
    ):
        response = await staff_client.get(
            "/api/v1/parent-onboarding/partner-agencies?q=wic"
        )
        assert response.status_code == 200
        body = response.json()
        slugs = [a["slug"] for a in body["agencies"]]
        assert "eastside-wic-clinic" in slugs


@pytest.mark.integration
class TestReminderTask:
    """Reminder pass groups by assignee + uses distinct Resend tag names.

    Resend `tags` rejects duplicate `name`s in a batch
    (feedback_resend_tag_name_uniqueness); the distinct-tag assertion is
    the regression test for the two-pass design.
    """

    async def test_due_tomorrow_groups_by_assignee_and_uses_correct_tag(
        self, test_db, test_session, test_staff, monkeypatch,
    ):
        from app.services.parent_onboarding_followup_reminder_tasks import (
            run_due_tomorrow_pass, TAG_DUE_TOMORROW,
        )
        # Three follow-ups due tomorrow, all assigned to the same staff.
        # Expect ONE email send (grouped), not three.
        tomorrow = date.today() + timedelta(days=1)
        for title in ("a", "b", "c"):
            test_db.add(ParentOnboardingFollowup(
                session_id=test_session.id, title=title,
                due_date=tomorrow, assignee_id=test_staff.id,
            ))
        await test_db.commit()

        sent: list[dict] = []

        async def _mock_send_email(**kwargs):
            sent.append(kwargs)
            return True

        monkeypatch.setattr(
            "app.services.parent_onboarding_followup_reminder_tasks.send_email",
            _mock_send_email,
        )
        summary = await run_due_tomorrow_pass(test_db, today=date.today())
        assert summary["assignees"] == 1
        assert summary["sent_ok"] == 1
        assert summary["sent_failed"] == 0
        assert len(sent) == 1
        # Distinct tag name: this pass uses parent-onboarding-followup-reminder.
        assert sent[0]["categories"] == [TAG_DUE_TOMORROW]

    async def test_overdue_uses_distinct_tag_from_due_tomorrow(
        self, test_db, test_session, test_staff, monkeypatch,
    ):
        from app.services.parent_onboarding_followup_reminder_tasks import (
            run_overdue_pass, TAG_DUE_TOMORROW, TAG_OVERDUE,
        )
        # Both tags MUST differ (Resend rejects duplicate tag names).
        assert TAG_DUE_TOMORROW != TAG_OVERDUE
        today = date.today()
        test_db.add(ParentOnboardingFollowup(
            session_id=test_session.id, title="x",
            due_date=today, assignee_id=test_staff.id,
        ))
        await test_db.commit()

        sent: list[dict] = []

        async def _mock_send_email(**kwargs):
            sent.append(kwargs)
            return True

        monkeypatch.setattr(
            "app.services.parent_onboarding_followup_reminder_tasks.send_email",
            _mock_send_email,
        )
        summary = await run_overdue_pass(test_db, today=today)
        assert summary["assignees"] == 1
        assert sent[0]["categories"] == [TAG_OVERDUE]

    async def test_completed_followups_not_reminded(
        self, test_db, test_session, test_staff, monkeypatch,
    ):
        from app.services.parent_onboarding_followup_reminder_tasks import (
            run_due_tomorrow_pass,
        )
        tomorrow = date.today() + timedelta(days=1)
        test_db.add(ParentOnboardingFollowup(
            session_id=test_session.id, title="done",
            due_date=tomorrow, assignee_id=test_staff.id,
            status=FollowupStatus.completed.value,
        ))
        await test_db.commit()

        async def _mock_send_email(**kwargs):
            raise AssertionError("should not send for completed follow-ups")

        monkeypatch.setattr(
            "app.services.parent_onboarding_followup_reminder_tasks.send_email",
            _mock_send_email,
        )
        summary = await run_due_tomorrow_pass(test_db, today=date.today())
        assert summary["assignees"] == 0
        assert summary["sent_ok"] == 0

    async def test_session_detail_with_followups_no_missing_greenlet(
        self, staff_client, test_db, test_session, test_staff, test_agency,
    ):
        """feedback_l30_async_property_landmine: response composition that
        reads .assignee.first_name and .partner_agency.name must NOT 500
        with MissingGreenlet when the parent rows are eager-loaded.
        """
        for i in range(5):
            test_db.add(ParentOnboardingFollowup(
                session_id=test_session.id, title=f"f{i}",
                due_date=date.today() + timedelta(days=i),
                assignee_id=test_staff.id,
            ))
        for i in range(10):
            test_db.add(ParentOnboardingReferral(
                session_id=test_session.id,
                partner_agency_id=test_agency.id,
                purpose=f"p{i}",
            ))
        await test_db.commit()

        r1 = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/followups"
        )
        r2 = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/referrals"
        )
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        assert r1.json()["total"] == 5
        assert r2.json()["total"] == 10
        # Names eager-resolved -- no Lazy-load 500.
        assert all(f["assignee_name"] for f in r1.json()["followups"])
        assert all(
            r["partner_agency_name"] == test_agency.name
            for r in r2.json()["referrals"]
        )
