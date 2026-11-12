# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.api.v1.storytime import _build_caregiver_identifier, _recognition_from_total_sessions
from app.schemas import StorytimeAttendanceCreate


def test_build_caregiver_identifier_prefers_email():
    attendance = StorytimeAttendanceCreate(
        session_id=1,
        attendee_type="child",
        caregiver_email=" Parent@Example.org ",
        caregiver_name="Ignored Name",
    )

    assert _build_caregiver_identifier(attendance) == "parent@example.org"


def test_build_caregiver_identifier_uses_name_and_child_fallback():
    attendance = StorytimeAttendanceCreate(
        session_id=1,
        attendee_type="child",
        caregiver_name="  Jane   Doe ",
        child_name="Sam",
    )

    assert _build_caregiver_identifier(attendance) == "jane doe::sam"


def test_recognition_status_thresholds():
    assert _recognition_from_total_sessions(1)[0] == "regular"
    assert _recognition_from_total_sessions(10)[0] == "frequent"
    assert _recognition_from_total_sessions(25)[0] == "devoted"
    assert _recognition_from_total_sessions(50)[0] == "super_fan"
