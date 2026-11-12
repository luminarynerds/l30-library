# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime, timezone

from app.schemas.board import BoardMeetingResponse


class _MeetingRow:
    def __init__(self):
        now = datetime.now(timezone.utc)
        self.id = 1
        self.meeting_type = "regular"
        self.title = "Monthly Board Meeting"
        self.description = "Discuss library operations"
        self.scheduled_date = now
        self.start_time = now
        self.end_time = now
        self.location = "Main Branch"
        self.is_virtual = False
        self.virtual_meeting_url = None
        self.public_comment_enabled = True
        self.public_comment_instructions = None
        self.accessibility_info = None
        self.has_executive_session = False
        self.executive_session_reason = None
        self.notice_lead_days_required = 2
        self.is_cancelled = False
        self.cancellation_reason = None
        self.quorum_met = True
        self.minutes_approved = False
        self.agenda_published_at = None
        self.agenda_published_by_id = None
        self.notice_status = "draft"
        self.notice_posted_at = None
        self.notice_posted_by_id = None
        self.notice_posting_locations = []
        self.notice_document_id = None
        self.created_at = now
        self.updated_at = now
        self.created_by_id = None


def test_board_meeting_response_allows_null_created_by_id_for_legacy_rows():
    row = _MeetingRow()

    parsed = BoardMeetingResponse.model_validate(row, from_attributes=True)

    assert parsed.id == 1
    assert parsed.created_by_id is None
