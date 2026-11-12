# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the librarian-notification wiring on 7 teacher actions.

The 7 routes live in ``backend/app/api/v1/school_reading/family_engagement.py``:

  1. POST   /schools/{school_id}/reading-lists/{list_id}/request  (reading list request)
  2. POST   /consultation-slots/{slot_id}/register                (consultation book)
  3. DELETE /consultation-slots/{slot_id}/unregister              (consultation cancel)
  4. POST   /library-visits/request                               (library visit request)
  5. DELETE /library-visits/requests/{request_id}                 (library visit cancel)
  6. POST   /family-challenges/{challenge_id}/register            (family challenge join)
  7. POST   /training-modules/{module_id}/complete                (quiz submit / training complete)

Strategy mirrors ``test_teacher_card.py``:
- Pure unit tests, MagicMock-based, no DB.
- Patch the notification helper at its import site in ``family_engagement``
  and assert each route handler awaits it exactly once on success.
- Helper-level tests cover recipient resolution and the cancel-grace
  window, and prove that a helper failure does NOT 500 the caller.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.school_reading import _notifications
from app.api.v1.school_reading._notifications import (
    NOTIFY_CANCEL_GRACE_SECONDS,
    _notify_librarian_of_teacher_action,
    is_within_cancel_grace,
)
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user(role: UserRole, *, user_id: int = 1, email: str = "t@example.com") -> User:
    u = MagicMock(spec=User)
    u.id = user_id
    u.role = role
    u.email = email
    u.is_active = True
    u.full_name = "Test Teacher"
    u.school_id = 42
    return u


def _make_db_mock(*, recipients=None, school=None) -> AsyncMock:
    """Build an AsyncSession mock whose .execute() returns scalars()
    matching the caller's intent. Each call advances the queue.
    """
    db = AsyncMock()

    # Queue of result objects -- each db.execute returns the next one.
    results_queue: list = []

    def _next_result():
        # Helper-internal calls only need scalar_one_or_none / scalars().all().
        return results_queue.pop(0) if results_queue else MagicMock()

    db.execute = AsyncMock(side_effect=lambda *a, **kw: _next_result())
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# is_within_cancel_grace
# ---------------------------------------------------------------------------


class TestCancelGrace:
    def test_none_returns_false(self):
        assert is_within_cancel_grace(None) is False

    def test_just_now_returns_true(self):
        assert is_within_cancel_grace(datetime.now(timezone.utc)) is True

    def test_within_grace_returns_true(self):
        booked = datetime.now(timezone.utc) - timedelta(seconds=NOTIFY_CANCEL_GRACE_SECONDS - 5)
        assert is_within_cancel_grace(booked) is True

    def test_after_grace_returns_false(self):
        booked = datetime.now(timezone.utc) - timedelta(seconds=NOTIFY_CANCEL_GRACE_SECONDS + 5)
        assert is_within_cancel_grace(booked) is False

    def test_naive_datetime_coerced_to_utc(self):
        # A naive datetime within grace is still treated as within grace.
        booked = datetime.utcnow() - timedelta(seconds=10)
        assert is_within_cancel_grace(booked) is True


# ---------------------------------------------------------------------------
# Helper-level: recipient resolution + skip-noise + failure isolation
# ---------------------------------------------------------------------------


class TestHelperBehavior:
    """Direct tests of ``_notify_librarian_of_teacher_action``."""

    @pytest.mark.asyncio
    async def test_cancel_within_grace_skips_dispatch(self):
        teacher = _user(UserRole.TEACHER)
        db = _make_db_mock()
        booked = datetime.now(timezone.utc) - timedelta(seconds=10)

        await _notify_librarian_of_teacher_action(
            db,
            teacher=teacher,
            school_id=42,
            action_type="consultation_cancel",
            booked_at=booked,
        )

        # Skip-noise: no recipient query, no in-app row, no commit.
        db.execute.assert_not_called()
        db.add.assert_not_called()
        db.commit.assert_not_called()

    @pytest.mark.asyncio
    async def test_cancel_outside_grace_dispatches(self):
        teacher = _user(UserRole.TEACHER)
        booked = datetime.now(timezone.utc) - timedelta(
            seconds=NOTIFY_CANCEL_GRACE_SECONDS + 30
        )
        recipients_mock = AsyncMock(return_value=[])
        with patch.object(_notifications, "_resolve_recipients", new=recipients_mock):
            with patch.object(_notifications, "_resolve_school", new=AsyncMock(return_value=None)):
                db = _make_db_mock()
                await _notify_librarian_of_teacher_action(
                    db,
                    teacher=teacher,
                    school_id=42,
                    action_type="library_visit_cancel",
                    booked_at=booked,
                )
            # Recipients were fetched -- skip-noise did not fire.
            recipients_mock.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_recipients_returns_silently(self):
        teacher = _user(UserRole.TEACHER)
        db = _make_db_mock()
        with patch.object(_notifications, "_resolve_recipients", new=AsyncMock(return_value=[])):
            with patch.object(_notifications, "_resolve_school", new=AsyncMock(return_value=None)):
                await _notify_librarian_of_teacher_action(
                    db,
                    teacher=teacher,
                    school_id=42,
                    action_type="reading_list_request",
                )
        # No in-app rows added, no email sent.
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_helper_failure_does_not_raise(self):
        """Recipient query blowing up must NOT bubble out of the helper.
        This is what protects the caller's 200 response.
        """
        teacher = _user(UserRole.TEACHER)
        db = _make_db_mock()
        with patch.object(
            _notifications,
            "_resolve_recipients",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            # Must not raise.
            await _notify_librarian_of_teacher_action(
                db,
                teacher=teacher,
                school_id=42,
                action_type="library_visit_request",
            )

    @pytest.mark.asyncio
    async def test_target_user_id_overrides_broadcast(self):
        """When target_user_id is passed, only that user is fetched -- no
        broadcast query.
        """
        teacher = _user(UserRole.TEACHER)

        # First execute() = single-user lookup; scalar_one_or_none returns a user.
        librarian = _user(UserRole.STAFF, user_id=99, email="l@example.com")
        single_lookup = MagicMock()
        single_lookup.scalar_one_or_none.return_value = librarian
        # Second execute() = school lookup (returns None is fine).
        school_lookup = MagicMock()
        school_lookup.scalar_one_or_none.return_value = None

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[single_lookup, school_lookup])
        db.commit = AsyncMock()
        db.add = MagicMock()

        with patch.object(_notifications, "send_email", create=True, new=AsyncMock(return_value=True)):
            with patch("app.api.v1.school_reading._notifications.send_email", create=True, new=AsyncMock(return_value=True)):
                # send_email is lazy-imported; patch the import path too
                with patch("app.core.email.send_email", new=AsyncMock(return_value=True)):
                    await _notify_librarian_of_teacher_action(
                        db,
                        teacher=teacher,
                        school_id=42,
                        action_type="consultation_book",
                        target_user_id=99,
                    )

        # Two db.execute calls only: single-user + school. Not a broadcast.
        assert db.execute.await_count == 2
        # One in-app notification row added.
        db.add.assert_called_once()


# ---------------------------------------------------------------------------
# Route-level: each handler invokes the helper exactly once on success
# ---------------------------------------------------------------------------


# Path used to patch the helper *at its import site* in family_engagement.
HELPER_PATH = "app.api.v1.school_reading.family_engagement._notify_librarian_of_teacher_action"


class TestRouteWiring:
    """Each handler must call the helper exactly once on the success path.
    These are micro-integration tests: we exercise the handler functions
    directly with mock db sessions, bypassing FastAPI's DI machinery.
    """

    @pytest.mark.asyncio
    async def test_create_reading_list_request_notifies(self):
        from app.api.v1.school_reading.family_engagement import (
            create_reading_list_request,
        )
        from app.schemas.reading import ReadingListRequestCreate

        teacher = _user(UserRole.TEACHER)

        # Mock chain:
        # 1) get_or_404(school)  -> handled via patch of get_or_404
        # 2) select(SharedReadingList) -> returns a reading list row
        # 3) select(ReadingListRequest with reading_list eager) -> returns a row
        reading_list = MagicMock()
        reading_list.id = 7
        reading_list.partner_id = 42
        reading_list.name = "Spring Picks"

        new_row = MagicMock()
        new_row.id = 1001
        new_row.reading_list = reading_list
        new_row.copies = 5

        rl_lookup = MagicMock()
        rl_lookup.scalar_one_or_none.return_value = reading_list
        post_insert = MagicMock()
        post_insert.scalar_one.return_value = new_row

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[rl_lookup, post_insert])
        db.add = MagicMock()
        db.commit = AsyncMock()

        with patch(
            "app.api.v1.school_reading.family_engagement.get_or_404",
            new=AsyncMock(return_value=MagicMock()),
        ):
            with patch(HELPER_PATH, new=AsyncMock()) as helper:
                with patch(
                    "app.api.v1.school_reading.family_engagement._serialize_reading_list_request",
                    return_value={"id": 1001},
                ):
                    await create_reading_list_request(
                        request=MagicMock(),
                        school_id=42,
                        list_id=7,
                        payload=ReadingListRequestCreate(copies=5),
                        current_user=teacher,
                        db=db,
                    )

        helper.assert_awaited_once()
        kwargs = helper.await_args.kwargs
        assert kwargs["action_type"] == "reading_list_request"
        assert kwargs["school_id"] == 42

    @pytest.mark.asyncio
    async def test_register_for_consultation_notifies(self):
        from app.api.v1.school_reading.family_engagement import (
            register_for_consultation,
        )

        teacher = _user(UserRole.TEACHER)
        teacher.school_id = 42

        slot = MagicMock()
        slot.id = 10
        slot.partner_id = 42
        slot.librarian_id = 99
        slot.title = "Curriculum Planning"
        slot.scheduled_date = datetime(2026, 6, 1, tzinfo=timezone.utc).date()
        slot.start_time = "14:00"
        slot.current_participants = 0
        slot.max_participants = 5
        slot.is_booked = False
        slot.is_completed = False

        attendee_lookup = MagicMock()
        attendee_lookup.scalar_one_or_none.return_value = None  # not yet registered

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[attendee_lookup])
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        with patch(
            "app.api.v1.school_reading.family_engagement.get_or_404",
            new=AsyncMock(return_value=slot),
        ):
            with patch(
                "app.api.v1.school_reading.family_engagement.assert_teacher_access_to_school"
            ):
                with patch(HELPER_PATH, new=AsyncMock()) as helper:
                    await register_for_consultation(
                        request=MagicMock(),
                        slot_id=10,
                        current_user=teacher,
                        db=db,
                    )
        helper.assert_awaited_once()
        kwargs = helper.await_args.kwargs
        assert kwargs["action_type"] == "consultation_book"
        assert kwargs["target_user_id"] == 99
        assert kwargs["school_id"] == 42

    @pytest.mark.asyncio
    async def test_unregister_from_consultation_notifies_cancel(self):
        from app.api.v1.school_reading.family_engagement import (
            unregister_from_consultation,
        )

        teacher = _user(UserRole.TEACHER, user_id=1)

        slot = MagicMock()
        slot.id = 10
        slot.partner_id = 42
        slot.librarian_id = 99
        slot.title = "Reading Strategies"
        slot.current_participants = 1
        slot.is_completed = False
        slot.is_booked = True

        attendee = MagicMock()
        attendee.user_id = 1
        attendee.registered_at = datetime.now(timezone.utc) - timedelta(minutes=30)

        attendee_lookup = MagicMock()
        attendee_lookup.scalar_one_or_none.return_value = attendee

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[attendee_lookup])
        db.delete = AsyncMock()
        db.commit = AsyncMock()

        with patch(
            "app.api.v1.school_reading.family_engagement.get_or_404",
            new=AsyncMock(return_value=slot),
        ):
            with patch(HELPER_PATH, new=AsyncMock()) as helper:
                await unregister_from_consultation(
                    request=MagicMock(),
                    slot_id=10,
                    current_user=teacher,
                    db=db,
                )
        helper.assert_awaited_once()
        kwargs = helper.await_args.kwargs
        assert kwargs["action_type"] == "consultation_cancel"
        assert kwargs["booked_at"] == attendee.registered_at
        assert kwargs["target_user_id"] == 99

    @pytest.mark.asyncio
    async def test_create_library_visit_request_notifies(self):
        from app.api.v1.school_reading.family_engagement import (
            create_library_visit_request,
        )
        from app.schemas.reading import LibraryVisitRequestCreate

        teacher = _user(UserRole.TEACHER)
        teacher.school_id = 42

        new_row = MagicMock()
        new_row.id = 501
        new_row.school_id = 42
        new_row.requested_date = datetime(2026, 6, 1, tzinfo=timezone.utc)
        new_row.number_of_students = 25
        new_row.grade_level = "3rd"
        new_row.school = MagicMock(name="School42")

        post_insert = MagicMock()
        post_insert.scalar_one.return_value = new_row

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[post_insert])
        db.add = MagicMock()
        db.commit = AsyncMock()

        payload = LibraryVisitRequestCreate(
            school_id=42,
            teacher_name="Ms Smith",
            requested_date=datetime(2026, 6, 1, tzinfo=timezone.utc),
            number_of_students=25,
            grade_level="3rd",
            purpose="Library tour",
        )

        with patch(
            "app.api.v1.school_reading.family_engagement.get_or_404",
            new=AsyncMock(return_value=MagicMock()),
        ):
            with patch(
                "app.api.v1.school_reading.family_engagement.assert_teacher_access_to_school"
            ):
                with patch(
                    "app.api.v1.school_reading.family_engagement._serialize_visit",
                    return_value={"id": 501},
                ):
                    with patch(HELPER_PATH, new=AsyncMock()) as helper:
                        await create_library_visit_request(
                            request=MagicMock(),
                            payload=payload,
                            current_user=teacher,
                            db=db,
                        )
        helper.assert_awaited_once()
        kwargs = helper.await_args.kwargs
        assert kwargs["action_type"] == "library_visit_request"
        assert kwargs["school_id"] == 42

    @pytest.mark.asyncio
    async def test_cancel_library_visit_request_notifies_cancel(self):
        from app.api.v1.school_reading.family_engagement import (
            cancel_library_visit_request,
        )

        teacher = _user(UserRole.TEACHER, user_id=1)

        row = MagicMock()
        row.id = 501
        row.school_id = 42
        row.teacher_user_id = 1
        row.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        row.status = "pending"

        db = AsyncMock()
        db.commit = AsyncMock()

        with patch(
            "app.api.v1.school_reading.family_engagement.get_or_404",
            new=AsyncMock(return_value=row),
        ):
            with patch(HELPER_PATH, new=AsyncMock()) as helper:
                await cancel_library_visit_request(
                    request=MagicMock(),
                    request_id=501,
                    current_user=teacher,
                    db=db,
                )
        helper.assert_awaited_once()
        kwargs = helper.await_args.kwargs
        assert kwargs["action_type"] == "library_visit_cancel"
        assert kwargs["booked_at"] == row.created_at

    @pytest.mark.asyncio
    async def test_register_family_in_challenge_notifies(self):
        from app.api.v1.school_reading.family_engagement import (
            register_family_in_challenge,
        )
        from app.schemas.reading import FamilyChallengeRegistrationCreate

        teacher = _user(UserRole.TEACHER)

        challenge = MagicMock()
        challenge.id = 77
        challenge.program = MagicMock()
        challenge.program.partner_id = 42

        challenge_lookup = MagicMock()
        challenge_lookup.scalar_one_or_none.return_value = challenge

        db = AsyncMock()
        db.execute = AsyncMock(side_effect=[challenge_lookup])
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        payload = FamilyChallengeRegistrationCreate(
            schoolId=42, familyName="The Smiths", studentAge=8
        )

        with patch(HELPER_PATH, new=AsyncMock()) as helper:
            await register_family_in_challenge(
                request=MagicMock(),
                challenge_id=77,
                registration_data=payload,
                current_user=teacher,
                db=db,
            )
        helper.assert_awaited_once()
        kwargs = helper.await_args.kwargs
        assert kwargs["action_type"] == "family_challenge_join"
        assert kwargs["school_id"] == 42

    @pytest.mark.asyncio
    async def test_complete_training_module_notifies(self):
        from app.api.v1.school_reading.family_engagement import (
            CompleteTrainingModuleRequest,
            complete_training_module,
        )

        teacher = _user(UserRole.TEACHER)

        module = MagicMock()
        module.id = 5
        module.partner_id = 42
        module_lookup = MagicMock()
        module_lookup.scalar_one_or_none.return_value = module

        completion = MagicMock()
        completion.status = "in_progress"
        completion.passed_assessment = False
        completion_lookup = MagicMock()
        completion_lookup.scalar_one_or_none.return_value = completion

        # Third execute is the partner_id re-fetch inside the route's notify block.
        module_partner_lookup = MagicMock()
        module_partner_lookup.scalar_one_or_none.return_value = module

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[module_lookup, completion_lookup, module_partner_lookup]
        )
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        with patch(HELPER_PATH, new=AsyncMock()) as helper:
            await complete_training_module(
                request=MagicMock(),
                module_id=5,
                body=CompleteTrainingModuleRequest(partnerId=42, assessmentScore=85),
                current_user=teacher,
                db=db,
            )
        helper.assert_awaited_once()
        kwargs = helper.await_args.kwargs
        assert kwargs["action_type"] == "training_module_complete"
        assert kwargs["school_id"] == 42
        assert kwargs["payload"]["passed"] is True

    @pytest.mark.asyncio
    async def test_complete_training_module_without_score_passes(self):
        # Modules have no quiz content; omitting assessmentScore must record
        # an attendance-based pass (quiz_score null, passed True), not 422.
        from app.api.v1.school_reading.family_engagement import (
            CompleteTrainingModuleRequest,
            complete_training_module,
        )

        teacher = _user(UserRole.TEACHER)

        module = MagicMock()
        module.id = 5
        module.partner_id = 42
        module_lookup = MagicMock()
        module_lookup.scalar_one_or_none.return_value = module

        completion = MagicMock()
        completion.status = "in_progress"
        completion.passed_assessment = False
        completion_lookup = MagicMock()
        completion_lookup.scalar_one_or_none.return_value = completion

        module_partner_lookup = MagicMock()
        module_partner_lookup.scalar_one_or_none.return_value = module

        db = AsyncMock()
        db.execute = AsyncMock(
            side_effect=[module_lookup, completion_lookup, module_partner_lookup]
        )
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()

        with patch(HELPER_PATH, new=AsyncMock()) as helper:
            await complete_training_module(
                request=MagicMock(),
                module_id=5,
                body=CompleteTrainingModuleRequest(partnerId=42),
                current_user=teacher,
                db=db,
            )
        assert completion.quiz_score is None
        assert completion.passed_assessment is True
        kwargs = helper.await_args.kwargs
        assert kwargs["payload"]["quiz_score"] is None
        assert kwargs["payload"]["passed"] is True


# ---------------------------------------------------------------------------
# Helper failure does not bubble (route-level)
# ---------------------------------------------------------------------------


class TestRouteResilience:
    """Production helper swallows internal errors so a notify failure can't
    500 a user action. This proves the contract end-to-end against the
    REAL helper -- not a patched mock.
    """

    @pytest.mark.asyncio
    async def test_real_helper_swallows_recipient_query_failure(self):
        teacher = _user(UserRole.TEACHER)
        db = AsyncMock()
        # Any execute call raises -- recipient resolution should fail.
        db.execute = AsyncMock(side_effect=RuntimeError("DB exploded"))
        db.commit = AsyncMock()
        db.add = MagicMock()

        # Real helper -- must NOT raise.
        await _notify_librarian_of_teacher_action(
            db,
            teacher=teacher,
            school_id=42,
            action_type="library_visit_request",
        )

    @pytest.mark.asyncio
    async def test_real_helper_swallows_email_failure(self):
        teacher = _user(UserRole.TEACHER)
        librarian = _user(UserRole.STAFF, user_id=99, email="l@example.com")

        with patch.object(
            _notifications, "_resolve_recipients", new=AsyncMock(return_value=[librarian])
        ):
            with patch.object(
                _notifications, "_resolve_school", new=AsyncMock(return_value=None)
            ):
                with patch(
                    "app.core.email.send_email",
                    new=AsyncMock(side_effect=RuntimeError("Resend down")),
                ):
                    db = AsyncMock()
                    db.execute = AsyncMock()
                    db.commit = AsyncMock()
                    db.add = MagicMock()

                    # Real helper -- must NOT raise even when send_email errors.
                    await _notify_librarian_of_teacher_action(
                        db,
                        teacher=teacher,
                        school_id=42,
                        action_type="reading_list_request",
                    )
