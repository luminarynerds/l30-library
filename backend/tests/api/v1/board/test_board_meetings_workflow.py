# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""End-to-end tests for the Board Meetings workflow.

Tests the complete lifecycle of a board meeting including:
1. Meeting creation and updates
2. Agenda management
3. Board member setup and attendance tracking
4. Document creation, versioning, publishing, and archiving
5. Vote creation, opening, casting, closing, and tally
6. Meeting cancellation and edge cases
"""

import pytest
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.board import (
    BoardMeeting,
    BoardMember,
    BoardVote,
    BoardVoteCast,
    BoardDocument,
    BoardDocumentVersion,
    AgendaItem,
    MeetingAttendance,
)
from app.models.board.minutes import BoardMinutes


def _error_message(resp) -> str:
    """Extract error message from response, handling custom error format."""
    body = resp.json()
    if "detail" in body:
        return body["detail"]
    if "error" in body and "message" in body["error"]:
        return body["error"]["message"]
    return str(body)


# ============ Fixtures ============


@pytest.fixture
async def admin(test_db: AsyncSession) -> User:
    """Admin user for board operations."""
    user = User(
        email="workflow_admin@example.com",
        password_hash=hash_password("AdminPass123!"),
        first_name="Workflow",
        last_name="Admin",
        role=UserRole.ADMIN,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def staff(test_db: AsyncSession) -> User:
    """Staff user for meeting management."""
    user = User(
        email="workflow_staff@example.com",
        password_hash=hash_password("StaffPass123!"),
        first_name="Workflow",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def member_users(test_db: AsyncSession) -> list[tuple[User, BoardMember]]:
    """Create 5 board member users with linked BoardMember records."""
    members = []
    positions = ["president", "vice_president", "secretary", "treasurer", "member"]
    for i in range(5):
        user = User(
            email=f"wf_member{i}@example.com",
            password_hash=hash_password("MemberPass123!"),
            first_name=f"Member{i}",
            last_name="Board",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        test_db.add(user)
        await test_db.commit()
        await test_db.refresh(user)

        bm = BoardMember(
            user_id=user.id,
            full_name=f"Member{i} Board",
            email=user.email,
            position=positions[i],
            term_start_date=datetime.now(timezone.utc) - timedelta(days=90),
            term_end_date=datetime.now(timezone.utc) + timedelta(days=365),
            is_current=True,
        )
        test_db.add(bm)
        await test_db.commit()
        await test_db.refresh(bm)
        members.append((user, bm))
    return members


class _UserSwitcher:
    """Allows switching the active authenticated user without recreating clients.

    Since FastAPI's dependency_overrides is app-global, we use a mutable
    container that the override closure reads from at call time.
    """

    def __init__(self):
        self._user: User | None = None

    def set(self, user: User):
        self._user = user

    @property
    def user(self) -> User:
        assert self._user is not None, "No user set on _UserSwitcher"
        return self._user


def _setup_test_app(test_db: AsyncSession, switcher: _UserSwitcher) -> None:
    """Configure app dependency overrides for testing."""
    from app.main import app
    from app.core.database import get_db
    from app.api.v1.auth import get_current_user, get_current_user_optional

    async def _override_db():
        yield test_db

    async def _override_user():
        return switcher.user

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_current_user] = _override_user
    # Public board endpoints (GET single/list meeting, search) gate on notice
    # status via get_current_user_optional rather than get_current_user --
    # override both so the switcher's identity is honored everywhere.
    app.dependency_overrides[get_current_user_optional] = _override_user


def _make_client() -> AsyncClient:
    """Create an AsyncClient connected to the app."""
    from app.main import app

    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _make_authed_client(test_db: AsyncSession, user: User) -> AsyncClient:
    """Create an AsyncClient that authenticates as the given user.

    Overrides get_current_user to return the specified user directly,
    bypassing JWT token creation and Redis-based revocation checks.
    """
    switcher = _UserSwitcher()
    switcher.set(user)
    _setup_test_app(test_db, switcher)
    return _make_client()


# ============ End-to-End Workflow Tests ============


@pytest.mark.asyncio
class TestBoardMeetingFullWorkflow:
    """Complete meeting lifecycle: create -> agenda -> attendance -> vote -> minutes."""

    async def test_full_meeting_lifecycle(
        self, test_db: AsyncSession, admin: User, staff: User, member_users
    ):
        """End-to-end test covering the entire board meeting workflow."""

        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()

        try:
            # ─── Step 1: Create a board meeting (via DB — the schema has fields
            # like has_executive_session that the model doesn't support, so
            # creating via API would fail with model_dump() sending defaults) ───
            db_meeting = BoardMeeting(
                meeting_type="regular",
                title="March Regular Board Meeting",
                description="Monthly board meeting to discuss library operations",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
                location="Main Library Board Room",
                is_virtual=False,
                public_comment_enabled=True,
                created_by_id=staff.id,
            )
            test_db.add(db_meeting)
            await test_db.commit()
            await test_db.refresh(db_meeting)
            meeting_id = db_meeting.id

            # Verify the meeting is retrievable via API
            switcher.set(staff)
            resp = await client.get(f"/api/v1/board/meetings/{meeting_id}")
            assert resp.status_code == 200
            meeting = resp.json()
            assert meeting["title"] == "March Regular Board Meeting"
            assert meeting["is_cancelled"] is False

            # ─── Step 2: Update meeting details ───
            switcher.set(staff)
            update_data = {
                "description": "Monthly board meeting - updated with virtual option",
                "is_virtual": True,
                "virtual_meeting_url": "https://meet.example.com/board-march",
            }
            resp = await client.put(f"/api/v1/board/meetings/{meeting_id}", json=update_data)
            assert resp.status_code == 200, f"Failed to update meeting: {resp.text}"
            updated = resp.json()
            assert updated["is_virtual"] is True
            assert updated["virtual_meeting_url"] == "https://meet.example.com/board-march"

            # ─── Step 3: Add agenda items ───
            agenda_items_data = [
                {
                    "item_number": "1",
                    "title": "Call to Order",
                    "description": "President calls the meeting to order",
                    "presenter": "President",
                    "estimated_duration_minutes": 2,
                    "sort_order": 1,
                },
                {
                    "item_number": "2",
                    "title": "Approval of Previous Minutes",
                    "description": "Review and approve minutes from last meeting",
                    "presenter": "Secretary",
                    "estimated_duration_minutes": 5,
                    "sort_order": 2,
                    "requires_action": True,
                    "action_type": "vote",
                },
                {
                    "item_number": "3",
                    "title": "Budget Discussion",
                    "description": "Review Q2 budget proposal",
                    "presenter": "Treasurer",
                    "estimated_duration_minutes": 30,
                    "sort_order": 3,
                    "requires_action": True,
                    "action_type": "vote",
                },
                {
                    "item_number": "4",
                    "title": "Adjournment",
                    "description": "Motion to adjourn",
                    "sort_order": 4,
                },
            ]

            for item_data in agenda_items_data:
                resp = await client.post(
                    f"/api/v1/board/meetings/{meeting_id}/agenda",
                    json=item_data,
                )
                assert resp.status_code == 200, f"Failed to add agenda item: {resp.text}"

            # Verify agenda was created
            resp = await client.get(f"/api/v1/board/meetings/{meeting_id}/agenda")
            assert resp.status_code == 200
            agenda = resp.json()
            assert len(agenda) == 4
            assert agenda[0]["title"] == "Call to Order"

            # ─── Step 4: Check in members ───
            # There's no standalone "create attendance record" endpoint --
            # checkin/checkout/mark-absent each create the MeetingAttendance
            # row as a side effect, keyed by meeting_id + user_id (query
            # params, not a JSON body). See app/api/v1/board/attendance.py.

            # Check in the first 3 members as present
            for user, bm in member_users[:3]:
                resp = await client.post(
                    f"/api/v1/board/meetings/{meeting_id}/attendance/checkin",
                    params={"user_id": user.id, "status_value": "present"},
                )
                assert resp.status_code == 200, f"Failed to check in: {resp.text}"
                assert resp.json()["attendance_status"] == "present"
                assert resp.json()["checked_in_at"] is not None

            # Check in 4th member as tardy
            tardy_user, _tardy_bm = member_users[3]
            resp = await client.post(
                f"/api/v1/board/meetings/{meeting_id}/attendance/checkin",
                params={"user_id": tardy_user.id, "status_value": "tardy"},
            )
            assert resp.status_code == 200
            assert resp.json()["attendance_status"] == "tardy"

            # Mark 5th member as absent (excused)
            absent_user, absent_bm = member_users[4]
            resp = await client.post(
                f"/api/v1/board/meetings/{meeting_id}/attendance/mark-absent",
                params={"user_id": absent_user.id, "excused": "true", "reason": "Family emergency"},
            )
            assert resp.status_code == 200

            # ─── Step 5: Check quorum ───
            resp = await client.get(f"/api/v1/board/meetings/{meeting_id}/quorum")
            assert resp.status_code == 200
            quorum = resp.json()
            assert quorum["total_board_members"] == 5
            assert quorum["present_voting_members"] == 4  # 3 present + 1 tardy
            assert quorum["quorum_met"] is True

            # ─── Step 6: Create and manage a vote ───
            switcher.set(admin)
            vote_data = {
                "title": "Approve Q2 Budget Amendment",
                "description": "Motion to approve the proposed budget amendment for Q2 operations",
                "vote_type": "simple_majority",
                "opens_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
                "closes_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                "quorum_required": 3,
                "meeting_id": meeting_id,
            }
            resp = await client.post("/api/v1/board/votes", json=vote_data)
            assert resp.status_code == 200, f"Failed to create vote: {resp.text}"
            vote = resp.json()
            vote_id = vote["id"]
            assert vote["status"] == "upcoming"
            assert vote["vote_type"] == "simple_majority"

            # Open the vote
            resp = await client.post(f"/api/v1/board/votes/{vote_id}/open")
            assert resp.status_code == 200
            assert resp.json()["message"] == "Vote opened"

            # Cast votes from board members (3 yes, 1 no)
            for i, (user, bm) in enumerate(member_users[:4]):
                switcher.set(user)
                choice = "yes" if i < 3 else "no"
                resp = await client.post(
                    f"/api/v1/board/votes/{vote_id}/cast",
                    json={"choice": choice, "comment": f"Vote from member {i}"},
                )
                assert resp.status_code == 200, f"Failed to cast vote for member {i}: {resp.text}"
                assert resp.json()["choice"] == choice

            # Close the vote and verify tally
            switcher.set(admin)
            resp = await client.post(f"/api/v1/board/votes/{vote_id}/close")
            assert resp.status_code == 200
            result = resp.json()
            assert result["passed"] is True
            assert result["yes"] == 3
            assert result["no"] == 1
            assert result["abstain"] == 0
            assert result["quorum_met"] is True

            # ─── Step 7: Upload, version, publish, and archive documents ───
            switcher.set(staff)

            # Create a document
            doc_data = {
                "document_type": "agenda",
                "title": "March Board Meeting Agenda",
                "description": "Official agenda for the March regular board meeting",
                "filename": "march_agenda.pdf",
                "file_path": "/documents/board/2026/march_agenda.pdf",
                "file_size_bytes": 45000,
                "mime_type": "application/pdf",
                "is_public": True,
                "meeting_id": meeting_id,
            }
            resp = await client.post("/api/v1/board/documents", json=doc_data)
            assert resp.status_code == 201, f"Failed to create document: {resp.text}"
            doc = resp.json()
            doc_id = doc["id"]
            assert doc["status"] == "draft"
            assert doc["document_type"] == "agenda"

            # Update document metadata
            resp = await client.put(
                f"/api/v1/board/documents/{doc_id}",
                json={
                    "title": "March Board Meeting Agenda (Revised)",
                    "description": "Updated agenda",
                },
            )
            assert resp.status_code == 200
            assert resp.json()["title"] == "March Board Meeting Agenda (Revised)"

            # Create a new version
            version_data = {
                "file_url": "/documents/board/2026/march_agenda_v2.pdf",
                "file_size": 48000,
                "file_type": "application/pdf",
                "change_notes": "Added budget discussion section",
            }
            resp = await client.post(
                f"/api/v1/board/documents/{doc_id}/versions",
                json=version_data,
            )
            assert resp.status_code == 201, f"Failed to create version: {resp.text}"
            version = resp.json()
            assert version["version_number"] == 1
            assert version["change_notes"] == "Added budget discussion section"

            # Create second version
            version_data_2 = {
                "file_url": "/documents/board/2026/march_agenda_v3.pdf",
                "file_size": 50000,
                "file_type": "application/pdf",
                "change_notes": "Final version with all corrections",
            }
            resp = await client.post(
                f"/api/v1/board/documents/{doc_id}/versions",
                json=version_data_2,
            )
            assert resp.status_code == 201
            assert resp.json()["version_number"] == 2

            # List versions
            resp = await client.get(f"/api/v1/board/documents/{doc_id}/versions")
            assert resp.status_code == 200
            versions = resp.json()
            assert len(versions) == 2

            # Get specific version
            resp = await client.get(f"/api/v1/board/documents/{doc_id}/versions/1")
            assert resp.status_code == 200
            assert resp.json()["change_notes"] == "Added budget discussion section"

            # Publish the document
            resp = await client.post(f"/api/v1/board/documents/{doc_id}/publish")
            assert resp.status_code == 200, f"Failed to publish document: {resp.text}"
            published = resp.json()
            assert published["status"] == "published"
            assert published["published_date"] is not None

            # Cannot publish again
            resp = await client.post(f"/api/v1/board/documents/{doc_id}/publish")
            assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"
            assert "already published" in _error_message(resp).lower()

            # Archive the document
            resp = await client.post(f"/api/v1/board/documents/{doc_id}/archive")
            assert resp.status_code == 200, f"Failed to archive document: {resp.text}"
            archived = resp.json()
            assert archived["status"] == "archived"

            # Cannot archive again
            resp = await client.post(f"/api/v1/board/documents/{doc_id}/archive")
            assert resp.status_code == 400
            assert "already archived" in _error_message(resp)

            # Cannot update archived document
            resp = await client.put(
                f"/api/v1/board/documents/{doc_id}",
                json={"title": "Should fail"},
            )
            assert resp.status_code == 400
            assert "archived" in _error_message(resp).lower()

            # ─── Step 8: Check out an attendee early ───
            early_leaver, _early_bm = member_users[2]
            resp = await client.post(
                f"/api/v1/board/meetings/{meeting_id}/attendance/checkout",
                params={"user_id": early_leaver.id},
            )
            assert resp.status_code == 200
            checkout_data = resp.json()
            assert checkout_data["checked_out_at"] is not None
            assert checkout_data["attendance_status"] == "left_early"

            # Cannot check out again
            resp = await client.post(
                f"/api/v1/board/meetings/{meeting_id}/attendance/checkout",
                params={"user_id": early_leaver.id},
            )
            assert resp.status_code == 400

            # ─── Step 9: Verify meeting retrieval ───
            resp = await client.get(f"/api/v1/board/meetings/{meeting_id}")
            assert resp.status_code == 200
            final_meeting = resp.json()
            assert final_meeting["id"] == meeting_id
            assert final_meeting["is_virtual"] is True

            # List meetings
            resp = await client.get("/api/v1/board/meetings")
            assert resp.status_code == 200
            meetings_list = resp.json()
            assert any(m["id"] == meeting_id for m in meetings_list)

        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestVotingWorkflows:
    """Test various voting scenarios: simple majority, two-thirds, unanimous."""

    async def _setup_vote(
        self, test_db, admin, client, switcher, vote_type, title, quorum_required=3
    ):
        """Helper to create a meeting and an open vote."""
        meeting = BoardMeeting(
            meeting_type="regular",
            title=f"{title} Meeting",
            scheduled_date=datetime.now(timezone.utc) + timedelta(days=3),
            created_by_id=admin.id,
        )
        test_db.add(meeting)
        await test_db.commit()
        await test_db.refresh(meeting)

        switcher.set(admin)
        vote_data = {
            "title": title,
            "description": f"Testing {vote_type}",
            "vote_type": vote_type,
            "opens_at": (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat(),
            "closes_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            "quorum_required": quorum_required,
            "meeting_id": meeting.id,
        }
        resp = await client.post("/api/v1/board/votes", json=vote_data)
        assert resp.status_code == 200
        vote_id = resp.json()["id"]

        resp = await client.post(f"/api/v1/board/votes/{vote_id}/open")
        assert resp.status_code == 200
        return vote_id

    async def _cast_votes(self, member_users, client, switcher, vote_id, choices):
        """Helper to cast votes from members."""
        for i, choice in enumerate(choices):
            user, bm = member_users[i]
            switcher.set(user)
            resp = await client.post(
                f"/api/v1/board/votes/{vote_id}/cast",
                json={"choice": choice},
            )
            assert resp.status_code == 200, f"Failed to cast vote: {resp.text}"

    async def _close_and_check(self, admin, client, switcher, vote_id):
        """Close a vote and return the result."""
        switcher.set(admin)
        resp = await client.post(f"/api/v1/board/votes/{vote_id}/close")
        assert resp.status_code == 200
        return resp.json()

    async def test_two_thirds_majority_vote_passes(
        self, test_db: AsyncSession, admin: User, member_users
    ):
        """Two-thirds vote passes when enough yes votes (4/5 = 80% > 66.7%)."""
        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()
        try:
            vote_id = await self._setup_vote(
                test_db, admin, client, switcher, "two_thirds", "Bylaws Amendment"
            )
            await self._cast_votes(
                member_users, client, switcher, vote_id, ["yes", "yes", "yes", "yes", "no"]
            )
            result = await self._close_and_check(admin, client, switcher, vote_id)
            assert result["passed"] is True
            assert result["yes"] == 4
            assert result["no"] == 1
        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_two_thirds_majority_vote_fails(
        self, test_db: AsyncSession, admin: User, member_users
    ):
        """Two-thirds vote fails when not enough yes votes (3/5 = 60% < 66.7%)."""
        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()
        try:
            vote_id = await self._setup_vote(
                test_db, admin, client, switcher, "two_thirds", "Controversial Amendment"
            )
            await self._cast_votes(
                member_users, client, switcher, vote_id, ["yes", "yes", "yes", "no", "no"]
            )
            result = await self._close_and_check(admin, client, switcher, vote_id)
            assert result["passed"] is False
            assert result["yes"] == 3
            assert result["no"] == 2
        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_unanimous_vote_passes(self, test_db: AsyncSession, admin: User, member_users):
        """Unanimous vote passes when all vote yes (abstentions don't count as no)."""
        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()
        try:
            vote_id = await self._setup_vote(
                test_db, admin, client, switcher, "unanimous", "Honorary Recognition"
            )
            await self._cast_votes(
                member_users, client, switcher, vote_id, ["yes", "yes", "yes", "yes", "abstain"]
            )
            result = await self._close_and_check(admin, client, switcher, vote_id)
            assert result["passed"] is True
        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_unanimous_vote_fails_with_single_no(
        self, test_db: AsyncSession, admin: User, member_users
    ):
        """Unanimous vote fails when even one member votes no."""
        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()
        try:
            vote_id = await self._setup_vote(
                test_db, admin, client, switcher, "unanimous", "Contentious Recognition"
            )
            await self._cast_votes(
                member_users, client, switcher, vote_id, ["yes", "yes", "yes", "yes", "no"]
            )
            result = await self._close_and_check(admin, client, switcher, vote_id)
            assert result["passed"] is False
        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_vote_fails_quorum(self, test_db: AsyncSession, admin: User, member_users):
        """Vote fails when quorum not met."""
        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()
        try:
            vote_id = await self._setup_vote(
                test_db,
                admin,
                client,
                switcher,
                "simple_majority",
                "Vote Without Quorum",
                quorum_required=4,
            )
            await self._cast_votes(member_users, client, switcher, vote_id, ["yes", "yes"])
            result = await self._close_and_check(admin, client, switcher, vote_id)
            assert result["passed"] is False
            assert result["quorum_met"] is False
        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_vote_twice(self, test_db: AsyncSession, admin: User, member_users):
        """Board member cannot cast the same vote twice."""
        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()
        try:
            vote_id = await self._setup_vote(
                test_db,
                admin,
                client,
                switcher,
                "simple_majority",
                "Double Vote Test",
                quorum_required=1,
            )

            user, bm = member_users[0]
            switcher.set(user)

            # First vote succeeds
            resp = await client.post(
                f"/api/v1/board/votes/{vote_id}/cast",
                json={"choice": "yes"},
            )
            assert resp.status_code == 200

            # Second vote fails
            resp = await client.post(
                f"/api/v1/board/votes/{vote_id}/cast",
                json={"choice": "no"},
            )
            assert resp.status_code == 400
            assert "already voted" in _error_message(resp)
        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_vote_on_closed_vote(
        self, test_db: AsyncSession, admin: User, member_users
    ):
        """Cannot cast vote after vote is closed."""
        switcher = _UserSwitcher()
        _setup_test_app(test_db, switcher)
        client = _make_client()
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Closed Vote Meeting",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=3),
                created_by_id=admin.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            vote = BoardVote(
                meeting_id=meeting.id,
                title="Already Closed",
                description="This vote will be closed",
                vote_type="simple_majority",
                opens_at=datetime.now(timezone.utc) - timedelta(hours=2),
                closes_at=datetime.now(timezone.utc) + timedelta(hours=1),
                status="open",
                quorum_required=1,
                created_by_id=admin.id,
            )
            test_db.add(vote)
            await test_db.commit()
            await test_db.refresh(vote)

            # Close it as admin
            switcher.set(admin)
            resp = await client.post(f"/api/v1/board/votes/{vote.id}/close")
            assert resp.status_code == 200

            # Try to vote as member
            user, bm = member_users[0]
            switcher.set(user)
            resp = await client.post(
                f"/api/v1/board/votes/{vote.id}/cast",
                json={"choice": "yes"},
            )
            assert resp.status_code == 400
            assert "not open" in _error_message(resp)
        finally:
            await client.aclose()
            from app.main import app

            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestVoteStateTransitions:
    """Test vote lifecycle state machine: upcoming -> open -> closed."""

    async def test_cannot_open_already_open_vote(self, test_db: AsyncSession, admin: User):
        """Cannot open a vote that is already open."""
        admin_client = await _make_authed_client(test_db, admin)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="State Transition Meeting",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=3),
                created_by_id=admin.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            vote = BoardVote(
                meeting_id=meeting.id,
                title="State Test Vote",
                description="Testing state transitions",
                vote_type="simple_majority",
                opens_at=datetime.now(timezone.utc) - timedelta(hours=1),
                closes_at=datetime.now(timezone.utc) + timedelta(hours=1),
                status="open",
                quorum_required=1,
                created_by_id=admin.id,
            )
            test_db.add(vote)
            await test_db.commit()
            await test_db.refresh(vote)

            resp = await admin_client.post(f"/api/v1/board/votes/{vote.id}/open")
            assert resp.status_code == 400
            assert "upcoming" in _error_message(resp).lower()
        finally:
            await admin_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_close_upcoming_vote(self, test_db: AsyncSession, admin: User):
        """Cannot close a vote that hasn't been opened yet."""
        admin_client = await _make_authed_client(test_db, admin)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="State Transition Meeting 2",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=3),
                created_by_id=admin.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            vote = BoardVote(
                meeting_id=meeting.id,
                title="Upcoming Vote",
                description="Still upcoming",
                vote_type="simple_majority",
                opens_at=datetime.now(timezone.utc) + timedelta(hours=1),
                closes_at=datetime.now(timezone.utc) + timedelta(hours=2),
                status="upcoming",
                quorum_required=1,
                created_by_id=admin.id,
            )
            test_db.add(vote)
            await test_db.commit()
            await test_db.refresh(vote)

            resp = await admin_client.post(f"/api/v1/board/votes/{vote.id}/close")
            assert resp.status_code == 400
            assert "must be open" in _error_message(resp).lower()
        finally:
            await admin_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_delete_closed_vote(self, test_db: AsyncSession, admin: User):
        """Closed votes cannot be deleted - results must be preserved."""
        admin_client = await _make_authed_client(test_db, admin)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Delete Test Meeting",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=3),
                created_by_id=admin.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            vote = BoardVote(
                meeting_id=meeting.id,
                title="Closed Vote",
                description="This vote is closed",
                vote_type="simple_majority",
                opens_at=datetime.now(timezone.utc) - timedelta(hours=2),
                closes_at=datetime.now(timezone.utc) - timedelta(hours=1),
                status="closed",
                quorum_required=1,
                passed=True,
                final_tally_yes=3,
                final_tally_no=1,
                created_by_id=admin.id,
            )
            test_db.add(vote)
            await test_db.commit()
            await test_db.refresh(vote)

            resp = await admin_client.delete(f"/api/v1/board/votes/{vote.id}")
            assert resp.status_code == 400
            assert "closed" in _error_message(resp).lower()
        finally:
            await admin_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestDocumentLifecycle:
    """Test document lifecycle: draft -> published -> archived."""

    async def test_cannot_archive_draft_document(self, test_db: AsyncSession, staff: User):
        """Cannot archive a document that hasn't been published first."""
        staff_client = await _make_authed_client(test_db, staff)
        try:
            doc_data = {
                "document_type": "policy",
                "title": "Draft Policy Document",
                "description": "A policy in draft state",
                "filename": "draft_policy.pdf",
                "file_path": "/documents/board/draft_policy.pdf",
                "is_public": True,
            }
            resp = await staff_client.post("/api/v1/board/documents", json=doc_data)
            assert resp.status_code == 201
            doc_id = resp.json()["id"]

            # Try to archive directly
            resp = await staff_client.post(f"/api/v1/board/documents/{doc_id}/archive")
            assert resp.status_code == 400
            assert "publish it first" in _error_message(resp).lower()
        finally:
            await staff_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_document_view_count_increments(self, test_db: AsyncSession, staff: User):
        """View count increments each time a document is accessed."""
        doc = BoardDocument(
            document_type="minutes",
            title="Viewable Document",
            filename="viewable.pdf",
            file_path="/documents/board/viewable.pdf",
            status="published",
            is_public=True,
            published_date=datetime.now(timezone.utc),
            created_by_id=staff.id,
        )
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)

        # No auth needed for public document viewing
        from app.main import app
        from app.core.database import get_db

        async def _override_db():
            yield test_db

        app.dependency_overrides[get_db] = _override_db
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        try:
            for expected_count in range(1, 4):
                resp = await client.get(f"/api/v1/board/documents/{doc.id}")
                assert resp.status_code == 200
                assert resp.json()["view_count"] == expected_count
        finally:
            await client.aclose()
            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestMeetingCancellation:
    """Test meeting cancellation and constraints."""

    async def test_cancel_meeting(self, test_db: AsyncSession, admin: User):
        """Test cancelling a meeting with reason."""
        admin_client = await _make_authed_client(test_db, admin)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Meeting To Cancel",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=5),
                created_by_id=admin.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            resp = await admin_client.post(
                f"/api/v1/board/meetings/{meeting.id}/cancel?reason=Inclement%20weather",
            )
            assert resp.status_code == 200

            # Verify meeting is cancelled
            resp = await admin_client.get(f"/api/v1/board/meetings/{meeting.id}")
            assert resp.status_code == 200
            assert resp.json()["is_cancelled"] is True
        finally:
            await admin_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_add_agenda_to_cancelled_meeting(self, test_db: AsyncSession, staff: User):
        """Cannot add agenda items to a cancelled meeting."""
        staff_client = await _make_authed_client(test_db, staff)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Cancelled Meeting",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=5),
                is_cancelled=True,
                cancellation_reason="Test cancellation",
                created_by_id=staff.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/agenda",
                json={
                    "item_number": "1",
                    "title": "Should Not Work",
                    "sort_order": 1,
                },
            )
            assert resp.status_code == 400
            assert "cancelled" in _error_message(resp).lower()
        finally:
            await staff_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_add_attendance_to_cancelled_meeting(
        self, test_db: AsyncSession, staff: User, member_users
    ):
        """Cannot add attendance to a cancelled meeting."""
        staff_client = await _make_authed_client(test_db, staff)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Cancelled Meeting 2",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=5),
                is_cancelled=True,
                cancellation_reason="Test cancellation",
                created_by_id=staff.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            user, bm = member_users[0]
            # There is no plain "POST /attendance" create endpoint -- attendance
            # rows come into being via checkin/checkout/mark-absent, which take
            # user_id as a query param, not a JSON body (see attendance.py).
            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/attendance/checkin",
                params={"user_id": user.id},
            )
            assert resp.status_code == 400
            assert "cancelled" in _error_message(resp).lower()
        finally:
            await staff_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestAttendanceEdgeCases:
    """Test attendance tracking edge cases."""

    async def test_duplicate_attendance_rejected(
        self, test_db: AsyncSession, staff: User, member_users
    ):
        """Cannot check in the same user for the same meeting twice.

        There's no standalone "create attendance record" endpoint (attendance
        rows are created as a side effect of checkin/checkout/mark-absent,
        keyed by meeting_id + user_id -- see attendance.py), so "duplicate
        attendance" surfaces as a duplicate check-in.
        """
        staff_client = await _make_authed_client(test_db, staff)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Duplicate Attendance Meeting",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=5),
                created_by_id=staff.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            user, bm = member_users[0]

            # First check-in succeeds
            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/attendance/checkin",
                params={"user_id": user.id},
            )
            assert resp.status_code == 200

            # Duplicate check-in fails
            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/attendance/checkin",
                params={"user_id": user.id},
            )
            assert resp.status_code == 400
            assert "already checked in" in _error_message(resp).lower()
        finally:
            await staff_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_checkout_before_checkin(
        self, test_db: AsyncSession, staff: User, member_users
    ):
        """Cannot check out an attendee who hasn't checked in."""
        staff_client = await _make_authed_client(test_db, staff)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Checkout Before Checkin Meeting",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=5),
                created_by_id=staff.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            user, bm = member_users[0]
            # checkout_endpoint 404s if no attendance row exists at all, so
            # first create one via mark-absent (no checked_in_at set) rather
            # than checkin, to isolate the "not checked in yet" branch.
            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/attendance/mark-absent",
                params={"user_id": user.id},
            )
            assert resp.status_code == 200

            # Try to checkout without checkin
            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/attendance/checkout",
                params={"user_id": user.id},
            )
            assert resp.status_code == 400
            assert "not checked in" in _error_message(resp).lower()
        finally:
            await staff_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_cannot_double_checkin(self, test_db: AsyncSession, staff: User, member_users):
        """Cannot check in an attendee twice."""
        staff_client = await _make_authed_client(test_db, staff)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Double Checkin Meeting",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=5),
                created_by_id=staff.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            user, bm = member_users[0]

            # First checkin succeeds
            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/attendance/checkin",
                params={"user_id": user.id, "status_value": "present"},
            )
            assert resp.status_code == 200

            # Second checkin fails
            resp = await staff_client.post(
                f"/api/v1/board/meetings/{meeting.id}/attendance/checkin",
                params={"user_id": user.id, "status_value": "present"},
            )
            assert resp.status_code == 400
            assert "already checked in" in _error_message(resp).lower()
        finally:
            await staff_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestAuthorizationGuards:
    """Test that endpoints enforce proper role-based access control."""

    async def test_patron_cannot_create_meeting(self, test_db: AsyncSession, member_users):
        """Regular patron (board member user) cannot create meetings."""
        user, bm = member_users[0]
        patron_client = await _make_authed_client(test_db, user)
        try:
            resp = await patron_client.post(
                "/api/v1/board/meetings",
                json={
                    "meeting_type": "regular",
                    "title": "Unauthorized Meeting",
                    "scheduled_date": (datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
                },
            )
            assert resp.status_code == 403
        finally:
            await patron_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_patron_cannot_create_vote(self, test_db: AsyncSession, member_users):
        """Regular patron cannot create votes."""
        user, bm = member_users[0]
        patron_client = await _make_authed_client(test_db, user)
        try:
            resp = await patron_client.post(
                "/api/v1/board/votes",
                json={
                    "title": "Unauthorized Vote",
                    "description": "Should not work",
                    "vote_type": "simple_majority",
                    "opens_at": datetime.now(timezone.utc).isoformat(),
                    "closes_at": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
                    "quorum_required": 3,
                },
            )
            assert resp.status_code == 403
        finally:
            await patron_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_patron_cannot_upload_document(self, test_db: AsyncSession, member_users):
        """Regular patron cannot upload board documents."""
        user, bm = member_users[0]
        patron_client = await _make_authed_client(test_db, user)
        try:
            resp = await patron_client.post(
                "/api/v1/board/documents",
                json={
                    "document_type": "policy",
                    "title": "Unauthorized Document",
                    "filename": "test.pdf",
                    "file_path": "/test.pdf",
                },
            )
            assert resp.status_code == 403
        finally:
            await patron_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()

    async def test_staff_cannot_delete_meeting(self, test_db: AsyncSession, staff: User):
        """Staff can manage meetings but cannot delete them (admin only)."""
        staff_client = await _make_authed_client(test_db, staff)
        try:
            meeting = BoardMeeting(
                meeting_type="regular",
                title="Cannot Delete",
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=5),
                created_by_id=staff.id,
            )
            test_db.add(meeting)
            await test_db.commit()
            await test_db.refresh(meeting)

            resp = await staff_client.delete(f"/api/v1/board/meetings/{meeting.id}")
            assert resp.status_code == 403
        finally:
            await staff_client.aclose()
            from app.main import app

            app.dependency_overrides.clear()


@pytest.mark.asyncio
class TestMeetingSearch:
    """Test meeting search functionality."""

    async def test_search_meetings_by_title(self, test_db: AsyncSession, admin: User):
        """Search for meetings by title keyword."""
        for title in [
            "Budget Review Meeting",
            "Library Renovation Discussion",
            "Annual Budget Planning",
        ]:
            meeting = BoardMeeting(
                meeting_type="regular",
                title=title,
                scheduled_date=datetime.now(timezone.utc) + timedelta(days=7),
                created_by_id=admin.id,
                # Search is called anonymously below, so only posted/published
                # meetings are visible (see _PUBLIC_NOTICE_STATUSES).
                notice_status="posted",
            )
            test_db.add(meeting)
        await test_db.commit()

        # Search endpoint is public (no auth needed)
        from app.main import app
        from app.core.database import get_db

        async def _override_db():
            yield test_db

        app.dependency_overrides[get_db] = _override_db
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        try:
            resp = await client.get("/api/v1/board/meetings/search?q=Budget")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] >= 2
            titles = [m["title"] for m in data["results"]]
            assert any("Budget" in t for t in titles)
        finally:
            await client.aclose()
            app.dependency_overrides.clear()

    async def test_search_meetings_by_type(self, test_db: AsyncSession, admin: User):
        """Filter meetings by meeting type."""
        special = BoardMeeting(
            meeting_type="special",
            title="Special Emergency Session",
            scheduled_date=datetime.now(timezone.utc) + timedelta(days=3),
            created_by_id=admin.id,
        )
        test_db.add(special)
        await test_db.commit()

        from app.main import app
        from app.core.database import get_db

        async def _override_db():
            yield test_db

        app.dependency_overrides[get_db] = _override_db
        transport = ASGITransport(app=app)
        client = AsyncClient(transport=transport, base_url="http://test")
        try:
            resp = await client.get("/api/v1/board/meetings/search?meeting_type=special")
            assert resp.status_code == 200
            data = resp.json()
            assert all(m["meeting_type"] == "special" for m in data["results"])
        finally:
            await client.aclose()
            app.dependency_overrides.clear()
