# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Privacy / response-shape integration test for confidential groups.

This is the merge-gate test for spec property #1, #2, #3: when a non-staff
caller fetches a confidential group, the response JSON must OMIT (not null)
facilitator_id, facilitator_name, current_members, member_count, members.

These tests exercise the serializer directly rather than the FastAPI client,
because the project-wide async test_db fixture has a known collision with
dependency_overrides + httpx that PR #861 also worked around. The serializer
IS the contract; if it leaks, the API leaks.
"""
from datetime import date

import pytest

from app.api.v1.parent_onboarding.connection_groups import _serialize_group, _CONFIDENTIAL_STRIPPED_KEYS
from app.models.parent_onboarding import (
    ConnectionGroupType,
    GroupMemberStatus,
    MeetingFrequency,
    ParentConnectionGroup,
    ParentConnectionGroupMember,
)


def _make_group(*, confidential: bool) -> ParentConnectionGroup:
    g = ParentConnectionGroup(
        id=42,
        name="Tuesday Crew",
        description="Default description",
        confidential_card_description="Welcome and safe",
        confidential_approval_message="Staff will reply soon",
        estimated_response_window_hours=48,
        facilitator_id=7,
        branch_id=1,
        group_type=ConnectionGroupType.teen_parents,
        max_members=12,
        meeting_frequency=MeetingFrequency.weekly,
        meeting_day_of_week=None,
        meeting_time=None,
        location=None,
        languages=["en"],
        is_active=True,
        confidential=confidential,
    )
    g.members = [
        ParentConnectionGroupMember(
            id=1, group_id=42, patron_id=100,
            joined_date=date.today(), status=GroupMemberStatus.active,
            attendance_count=0, capacity_override=False,
        )
    ]
    return g


def test_confidential_to_patron_omits_sensitive_keys():
    g = _make_group(confidential=True)
    body = _serialize_group(g, is_staff_caller=False)
    for k in _CONFIDENTIAL_STRIPPED_KEYS:
        assert k not in body, f"key {k} leaked to non-staff caller"
    # Confidentiality config still surfaces so the patron card can render.
    assert body["confidential"] is True
    assert body["confidential_card_description"] == "Welcome and safe"
    assert body["estimated_response_window_hours"] == 48
    # Description is swapped to the sanitized version.
    assert body["description"] == "Welcome and safe"


def test_confidential_to_staff_keeps_all_keys():
    g = _make_group(confidential=True)
    body = _serialize_group(g, is_staff_caller=True)
    # Of the stripped set, the serializer actually emits these two — assert
    # both are present for staff. The others (facilitator_name, members,
    # current_members) aren't produced by this serializer at all (they live
    # on the members drawer / EnrollMember responses), but our strip-set
    # covers them defensively if added later.
    assert body["facilitator_id"] == 7
    assert body["member_count"] == 1


def test_non_confidential_to_patron_keeps_all_keys():
    g = _make_group(confidential=False)
    body = _serialize_group(g, is_staff_caller=False)
    assert body["facilitator_id"] == 7
    assert body["member_count"] == 1
    assert body["confidential"] is False


def test_no_key_leakage_via_null_collapse():
    """Spec property #1: omit keys, do NOT set them to None.

    Catches the classic mistake of returning a key with value None which
    still leaks the SHAPE of the API even if the value is empty.
    """
    g = _make_group(confidential=True)
    body = _serialize_group(g, is_staff_caller=False)
    keys = set(body.keys())
    for k in _CONFIDENTIAL_STRIPPED_KEYS:
        assert k not in keys
