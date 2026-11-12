# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for parent-onboarding session resource handouts.

Covers the endpoints introduced in feat/session-catalog-handout:

  GET    /api/v1/parent-onboarding/handouts
  GET    /api/v1/parent-onboarding/sessions/{id}/handouts
  POST   /api/v1/parent-onboarding/sessions/{id}/handouts
  DELETE /api/v1/parent-onboarding/sessions/{id}/handouts/{assignment_id}
  POST   /api/v1/parent-onboarding/sessions/{id}/handouts/print-packet  (501)

Auth: uses the existing ``staff_client`` fixture which dependency-overrides
``get_current_user`` (per feedback_l30_test_auth_token_revocation -- real
login flows 401 in tests because Redis is absent).
"""
from datetime import datetime, timedelta, timezone

import pytest

from app.models.community_resource import CommunityResourceLink
from app.models.parent_onboarding import (
    ParentOnboardingSession, ParentOnboardingSessionHandout,
    ParentOnboardingStatus, ResourceHandout,
)


@pytest.fixture
async def test_session(test_db, test_patron, test_staff):
    """A scheduled onboarding session that the new handouts attach to."""
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
async def test_wic_handout_en(test_db):
    h = ResourceHandout(
        slug="wic-eligibility",
        title="WIC Eligibility",
        category="wic",
        language="en",
        description="WIC eligibility flyer with income limits.",
        file_path="wic-eligibility-en.pdf",
        page_count=2,
        is_active=True,
    )
    test_db.add(h)
    await test_db.commit()
    await test_db.refresh(h)
    return h


@pytest.fixture
async def test_wic_handout_es(test_db):
    h = ResourceHandout(
        slug="wic-eligibility",
        title="WIC Eligibility - Espanol",
        category="wic",
        language="es",
        description="Folleto de elegibilidad WIC.",
        file_path="wic-eligibility-es.pdf",
        page_count=2,
        is_active=True,
    )
    test_db.add(h)
    await test_db.commit()
    await test_db.refresh(h)
    return h


@pytest.fixture
async def test_snap_handout_es(test_db):
    h = ResourceHandout(
        slug="snap-walkthrough",
        title="SNAP Walkthrough - Espanol",
        category="snap",
        language="es",
        description="SNAP application steps in Spanish.",
        file_path="snap-walkthrough-es.pdf",
        page_count=4,
        is_active=True,
    )
    test_db.add(h)
    await test_db.commit()
    await test_db.refresh(h)
    return h


@pytest.fixture
async def test_inactive_handout(test_db):
    """A retired catalog row, used to verify the default is_active filter."""
    h = ResourceHandout(
        slug="old-flyer",
        title="Retired Flyer",
        category="misc",
        language="en",
        file_path="old.pdf",
        is_active=False,
    )
    test_db.add(h)
    await test_db.commit()
    await test_db.refresh(h)
    return h


@pytest.fixture
async def test_community_link(test_db):
    link = CommunityResourceLink(
        category="food",
        category_label="Food Resources",
        page_contexts=["parent_onboarding"],
        name="Diaper Bank Hours and Address",
        url="https://example.org/diaper-bank",
        sort_order=10,
        is_active=True,
        source="manual",
    )
    test_db.add(link)
    await test_db.commit()
    await test_db.refresh(link)
    return link


# ---------------------------------------------------------------------------
# Catalog: GET /handouts
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestHandoutCatalog:

    async def test_list_returns_active_by_default(
        self,
        staff_client,
        test_wic_handout_en,
        test_wic_handout_es,
        test_inactive_handout,
    ):
        response = await staff_client.get(
            "/api/v1/parent-onboarding/handouts",
        )
        assert response.status_code == 200, response.text
        body = response.json()
        slugs = [(h["slug"], h["language"]) for h in body["handouts"]]
        assert ("wic-eligibility", "en") in slugs
        assert ("wic-eligibility", "es") in slugs
        assert all(h["is_active"] for h in body["handouts"])
        # Inactive handout is filtered out by default.
        assert all(
            h["slug"] != "old-flyer" for h in body["handouts"]
        )

    async def test_filter_by_language(
        self,
        staff_client,
        test_wic_handout_en,
        test_wic_handout_es,
        test_snap_handout_es,
    ):
        response = await staff_client.get(
            "/api/v1/parent-onboarding/handouts?language=es",
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        langs = {h["language"] for h in body["handouts"]}
        assert langs == {"es"}

    async def test_filter_by_category(
        self,
        staff_client,
        test_wic_handout_en,
        test_snap_handout_es,
    ):
        response = await staff_client.get(
            "/api/v1/parent-onboarding/handouts?category=snap",
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["handouts"][0]["category"] == "snap"

    async def test_combined_filters_language_and_category(
        self,
        staff_client,
        test_wic_handout_en,
        test_wic_handout_es,
        test_snap_handout_es,
    ):
        response = await staff_client.get(
            "/api/v1/parent-onboarding/handouts?language=es&category=wic",
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 1
        assert body["handouts"][0]["language"] == "es"
        assert body["handouts"][0]["category"] == "wic"

    async def test_file_url_composed_from_static_prefix(
        self, staff_client, test_wic_handout_es,
    ):
        response = await staff_client.get(
            "/api/v1/parent-onboarding/handouts?language=es",
        )
        body = response.json()
        # Static prefix is fixed at /static/handouts; file_path is relative.
        urls = [h["file_url"] for h in body["handouts"]]
        assert any(
            u.endswith("/wic-eligibility-es.pdf") for u in urls
        ), urls


# ---------------------------------------------------------------------------
# Session assignments: POST/GET/DELETE
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestSessionHandouts:

    async def test_create_with_resource_handout_returns_201(
        self,
        staff_client,
        test_session,
        test_wic_handout_es,
        test_staff,
    ):
        payload = {
            "resource_handout_id": test_wic_handout_es.id,
            "given_in_language": "es",
            "delivery_method": "printed",
            "notes": "Patron took two copies.",
        }
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
            json=payload,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["resource_handout_id"] == test_wic_handout_es.id
        assert body["community_resource_link_id"] is None
        assert body["display_title"] == "WIC Eligibility - Espanol"
        assert body["given_in_language"] == "es"
        assert body["delivery_method"] == "printed"
        # given_by is the staff user from the override; the composer should
        # surface a non-None given_by_id without MissingGreenlet.
        assert body["given_by_id"] == test_staff.id

    async def test_create_with_community_resource_link_returns_201(
        self, staff_client, test_session, test_community_link,
    ):
        payload = {
            "community_resource_link_id": test_community_link.id,
            "given_in_language": "en",
            "delivery_method": "linked",
        }
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
            json=payload,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["resource_handout_id"] is None
        assert body["community_resource_link_id"] == test_community_link.id
        assert body["display_title"] == "Diaper Bank Hours and Address"
        assert body["delivery_method"] == "linked"

    async def test_create_rejects_both_targets_null(
        self, staff_client, test_session,
    ):
        """The model_validator on SessionHandoutCreate enforces that at
        least one target FK is set. The DB CHECK constraint is the
        belt-and-suspenders defense."""
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
            json={"given_in_language": "en", "delivery_method": "printed"},
        )
        assert response.status_code == 422, response.text

    async def test_create_rejects_both_targets_set(
        self,
        staff_client,
        test_session,
        test_wic_handout_es,
        test_community_link,
    ):
        """Exactly one target is allowed -- both is ambiguous and the CHECK
        constraint would reject the row anyway."""
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
            json={
                "resource_handout_id": test_wic_handout_es.id,
                "community_resource_link_id": test_community_link.id,
                "given_in_language": "es",
            },
        )
        assert response.status_code == 422

    async def test_create_rejects_extra_fields(
        self, staff_client, test_session, test_wic_handout_es,
    ):
        """StrictInputSchema rejects unknown fields at request time."""
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
            json={
                "resource_handout_id": test_wic_handout_es.id,
                "given_in_language": "es",
                "bogus_field": "abc",
            },
        )
        assert response.status_code == 422

    async def test_create_rejects_unknown_handout(
        self, staff_client, test_session,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
            json={
                "resource_handout_id": 999_999,
                "given_in_language": "es",
            },
        )
        assert response.status_code == 400

    async def test_create_on_missing_session_returns_404(
        self, staff_client, test_wic_handout_es,
    ):
        response = await staff_client.post(
            "/api/v1/parent-onboarding/sessions/999999/handouts",
            json={
                "resource_handout_id": test_wic_handout_es.id,
                "given_in_language": "es",
            },
        )
        assert response.status_code == 404

    async def test_list_returns_session_handouts(
        self,
        staff_client,
        test_db,
        test_session,
        test_wic_handout_es,
        test_snap_handout_es,
        test_staff,
    ):
        a = ParentOnboardingSessionHandout(
            session_id=test_session.id,
            resource_handout_id=test_wic_handout_es.id,
            given_in_language="es",
            delivery_method="printed",
            given_by_id=test_staff.id,
        )
        b = ParentOnboardingSessionHandout(
            session_id=test_session.id,
            resource_handout_id=test_snap_handout_es.id,
            given_in_language="es",
            delivery_method="printed",
            given_by_id=test_staff.id,
        )
        test_db.add_all([a, b])
        await test_db.commit()

        response = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["total"] == 2
        # display_title is composed from the eager-loaded resource_handout.
        titles = sorted(h["display_title"] for h in body["handouts"])
        assert titles == [
            "SNAP Walkthrough - Espanol",
            "WIC Eligibility - Espanol",
        ]

    async def test_list_no_missing_greenlet_with_many_handouts(
        self,
        staff_client,
        test_db,
        test_session,
        test_wic_handout_es,
        test_staff,
    ):
        """Smoke test for the async-property landmine: 10 handouts on one
        session must serialize without MissingGreenlet on the relationships
        accessed by the response composer (resource_handout, community_
        resource_link, given_by). The service eager-loads all three.
        """
        rows = [
            ParentOnboardingSessionHandout(
                session_id=test_session.id,
                resource_handout_id=test_wic_handout_es.id,
                given_in_language="es",
                delivery_method="printed",
                given_by_id=test_staff.id,
                notes=f"copy {i}",
            )
            for i in range(10)
        ]
        test_db.add_all(rows)
        await test_db.commit()

        response = await staff_client.get(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}/handouts",
        )
        assert response.status_code == 200, response.text
        assert response.json()["total"] == 10

    async def test_delete_removes_row_only(
        self,
        staff_client,
        test_db,
        test_session,
        test_wic_handout_es,
    ):
        a = ParentOnboardingSessionHandout(
            session_id=test_session.id,
            resource_handout_id=test_wic_handout_es.id,
            given_in_language="es",
            delivery_method="printed",
        )
        test_db.add(a)
        await test_db.commit()
        await test_db.refresh(a)

        response = await staff_client.delete(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}"
            f"/handouts/{a.id}",
        )
        assert response.status_code == 204

        # The catalog handout itself is untouched.
        response = await staff_client.get(
            f"/api/v1/parent-onboarding/handouts?language=es",
        )
        body = response.json()
        slugs = [h["slug"] for h in body["handouts"]]
        assert "wic-eligibility" in slugs

    async def test_delete_misrouted_to_wrong_session_returns_404(
        self,
        staff_client,
        test_db,
        test_session,
        test_wic_handout_es,
    ):
        """An assignment_id that exists but belongs to a different session
        must 404, not silently delete the wrong row."""
        # Session A's assignment.
        assignment = ParentOnboardingSessionHandout(
            session_id=test_session.id,
            resource_handout_id=test_wic_handout_es.id,
            given_in_language="es",
            delivery_method="printed",
        )
        test_db.add(assignment)
        await test_db.commit()
        await test_db.refresh(assignment)

        response = await staff_client.delete(
            f"/api/v1/parent-onboarding/sessions/{test_session.id + 9999}"
            f"/handouts/{assignment.id}",
        )
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Print packet: 501 stub
# ---------------------------------------------------------------------------


@pytest.mark.integration
class TestPrintPacketStub:

    async def test_returns_501_with_dependent_spec_pointer(
        self, staff_client, test_session,
    ):
        response = await staff_client.post(
            f"/api/v1/parent-onboarding/sessions/{test_session.id}"
            f"/handouts/print-packet",
        )
        assert response.status_code == 501, response.text
        body = response.json()
        # FE renders "Print packet (not available yet)" on this signal.
        assert body["dependent_spec"] == (
            "2026-05-18-l30-resources-print-handout-mode"
        )

    async def test_404_on_missing_session(self, staff_client):
        response = await staff_client.post(
            "/api/v1/parent-onboarding/sessions/999999/handouts/print-packet",
        )
        assert response.status_code == 404
