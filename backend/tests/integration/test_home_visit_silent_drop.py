# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test for parent home-visit update unsupported-field handling.

The frontend `updateHomeVisitStatus` API client previously accepted
`cancelled_reason` and `rescheduled_to` fields that the backend silently
dropped. `ParentHomeVisit` has since grown real `cancelled_reason` and
`rescheduled_to_id` columns (app/models/parent_onboarding.py:731,735),
but `ParentHomeVisitUpdate` (app/schemas/parent_onboarding.py:854) still
does not accept them: it is a StrictInputSchema, which rejects unknown
fields outright (422 extra_forbidden) rather than silently ignoring them
-- the stricter, current, intentional behavior across this codebase's
StrictInputSchema-based schemas. So a PATCH carrying those fields must
fail whole and write nothing.

This test documents the current backend behavior: unknown fields make
the whole PATCH fail validation rather than being silently dropped.
The frontend types were trimmed in a paired change to stop advertising
these fields in the first place.
"""

from datetime import date, timedelta

import pytest

from app.models.parent_onboarding import (
    HomeVisitPurpose,
    HomeVisitStatus,
    ParentHomeVisit,
)


@pytest.fixture
async def test_home_visit(test_db, test_patron, test_staff):
    """Create a scheduled home visit owned by `test_patron`, visitor `test_staff`."""
    visit = ParentHomeVisit(
        patron_id=test_patron.id,
        visitor_id=test_staff.id,
        purpose=HomeVisitPurpose.intake,
        status=HomeVisitStatus.scheduled,
        scheduled_date=date.today() + timedelta(days=7),
        scheduled_time="14:30",
        address="123 Test Lane",
    )
    test_db.add(visit)
    await test_db.commit()
    await test_db.refresh(visit)
    return visit


@pytest.mark.integration
class TestHomeVisitUpdateSilentDrop:
    """Verify PATCH /home-visits/{id} rejects unsupported fields outright."""

    async def test_patch_with_unsupported_fields_returns_200(
        self,
        staff_client,
        test_home_visit,
    ):
        """PATCH with `cancelled_reason` + `rescheduled_to` 422s.

        ParentHomeVisitUpdate is a StrictInputSchema (extra_forbidden), so
        unknown fields fail the whole request rather than being dropped.
        """
        response = await staff_client.patch(
            f"/api/v1/parent-onboarding/home-visits/{test_home_visit.id}",
            json={
                "status": "cancelled",
                "visit_notes": "Family declined visit",
                # Fields the schema doesn't know about - StrictInputSchema
                # rejects the whole request with 422 extra_forbidden.
                "cancelled_reason": "patron_declined",
                "rescheduled_to": "2026-06-01T14:00:00Z",
            },
        )

        assert response.status_code == 422, response.text
        data = response.json()
        fields = {d["field"] for d in data["error"]["details"]}
        assert "body.cancelled_reason" in fields
        assert "body.rescheduled_to" in fields

    async def test_patch_unsupported_fields_not_persisted(
        self,
        staff_client,
        test_db,
        test_home_visit,
    ):
        """Re-fetch after a rejected PATCH to prove nothing was persisted."""
        response = await staff_client.patch(
            f"/api/v1/parent-onboarding/home-visits/{test_home_visit.id}",
            json={
                "status": "cancelled",
                "cancelled_reason": "this should not survive",
                "rescheduled_to": "2026-06-01T14:00:00Z",
            },
        )
        assert response.status_code == 422, response.text

        # Confirm via the model directly - the whole update was rejected,
        # not just the unsupported fields, so status is unchanged.
        await test_db.refresh(test_home_visit)
        assert test_home_visit.status == HomeVisitStatus.scheduled
        # These columns now exist on the model (they were added to fix the
        # silent-drop bug), but ParentHomeVisitUpdate still doesn't accept
        # them, so a PATCH carrying them must leave both unwritten.
        assert test_home_visit.cancelled_reason is None
        assert test_home_visit.rescheduled_to_id is None
