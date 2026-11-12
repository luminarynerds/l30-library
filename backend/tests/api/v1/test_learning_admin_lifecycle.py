# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the admin course-lifecycle API surface (3-state: draft/published/archived).

Covers:

  POST /api/v1/learning/admin/courses/{id}/transition
  GET  /api/v1/learning/admin/courses/review-queue
  GET  /api/v1/learning/admin/courses        (stage / review_due filters)
  PATCH /api/v1/learning/admin/courses/{id}/publish   (deprecated shim)

Uses the isolated-SQLite test-DB pattern from PRs #846 and #864:

    PYTHONPATH=. PII_ENCRYPTION_ENABLED=false \\
        TEST_DATABASE_URL='sqlite+aiosqlite:////tmp/lsc_test_lifecycle_api.db' \\
        /opt/l30/backend/.venv/bin/python -m pytest \\
        backend/tests/api/v1/test_learning_admin_lifecycle.py -q

(rm -f the test DB file before each pytest invocation; conftest
``ensure_tables_created`` also nukes it on first run.)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import (
    Course,
    CourseLifecycleStage,
    CourseStageTransition,
    Enrollment,
    Lesson,
    Module,
)
from sqlalchemy import select


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


@pytest.fixture
def admin_client(client, test_admin):
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def staff_client(client, test_staff):
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


# --------------------------------------------------------------------------
# Seed helpers
# --------------------------------------------------------------------------


async def _make_course(
    test_db,
    *,
    title: str,
    lifecycle_stage: CourseLifecycleStage = CourseLifecycleStage.DRAFT,
    review_due_at=None,
    last_reviewed_at=None,
) -> Course:
    course = Course(
        title=title,
        description=f"{title} description",
        access_level="staff",
        lifecycle_stage=lifecycle_stage,
        review_due_at=review_due_at,
        last_reviewed_at=last_reviewed_at,
    )
    test_db.add(course)
    await test_db.flush()
    await test_db.commit()
    return course


async def _add_module_with_lesson(test_db, course: Course) -> None:
    module = Module(course_id=course.id, title=f"{course.title} M", sort_order=0)
    test_db.add(module)
    await test_db.flush()
    lesson = Lesson(
        module_id=module.id,
        title=f"{course.title} L",
        lesson_type="text",
        content={"body": "x"},
        sort_order=0,
    )
    test_db.add(lesson)
    await test_db.flush()
    await test_db.commit()


# --------------------------------------------------------------------------
# Transition: happy path — draft -> published
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_draft_to_published(admin_client, test_db):
    """Happy path: draft -> published in one step (no review stage required)."""
    course = await _make_course(test_db, title="C1")
    await _add_module_with_lesson(test_db, course)

    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "published"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == course.id
    assert body["lifecycle_stage"] == "published"
    assert body["is_published"] is True
    assert body["is_review_due"] is False
    assert body["last_reviewed_at"] is not None
    assert body["review_due_at"] is not None
    assert body["last_reviewed_by"] is not None
    assert "enrollment_count" in body
    assert "completion_count" in body
    assert "in_progress_count" in body


# --------------------------------------------------------------------------
# Transition: published -> draft (Unpublish)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_published_to_draft_unpublish(admin_client, test_db):
    """Published -> draft is now a direct legal transition (Unpublish verb)."""
    course = await _make_course(
        test_db, title="Unpublish Me", lifecycle_stage=CourseLifecycleStage.PUBLISHED
    )

    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "draft"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["lifecycle_stage"] == "draft"
    assert body["is_published"] is False


# --------------------------------------------------------------------------
# Transition: published -> archived (Archive)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_published_to_archived(admin_client, test_db):
    """Published -> archived with confirm=true on an enrolled course."""
    course = await _make_course(
        test_db, title="Archive Me", lifecycle_stage=CourseLifecycleStage.PUBLISHED
    )

    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "archived", "confirm": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["lifecycle_stage"] == "archived"


# --------------------------------------------------------------------------
# Transition: archived -> draft (Restore)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_archived_to_draft_restore(admin_client, test_db):
    """Archived -> draft is the only way out of archived."""
    course = await _make_course(
        test_db, title="Restore Me", lifecycle_stage=CourseLifecycleStage.ARCHIVED
    )

    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "draft"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["lifecycle_stage"] == "draft"


# --------------------------------------------------------------------------
# Transition: disallowed — archived cannot go directly to published
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_disallowed_includes_allowed_targets(admin_client, test_db):
    """Archived cannot jump straight to published; FE needs the allowed list."""
    course = await _make_course(
        test_db, title="DirectJump", lifecycle_stage=CourseLifecycleStage.ARCHIVED
    )
    await _add_module_with_lesson(test_db, course)

    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "published"},
    )
    assert r.status_code == 400, r.text
    msg = r.json()["error"]["message"]
    assert isinstance(msg, dict)
    assert "allowed_targets" in msg
    assert "draft" in msg["allowed_targets"]
    assert "published" not in msg["allowed_targets"]
    assert msg["current_stage"] == "archived"


# --------------------------------------------------------------------------
# Transition: archive-with-enrollments confirm gate
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_archive_with_enrollments_requires_confirm(
    admin_client, test_db, test_patron
):
    """Archiving a course with enrollments without confirm -> 400 +
    enrollment_count; with confirm: true -> 200."""
    course = await _make_course(
        test_db, title="Archive Me", lifecycle_stage=CourseLifecycleStage.PUBLISHED
    )
    test_db.add(
        Enrollment(course_id=course.id, user_id=test_patron.id)
    )
    await test_db.commit()

    # Without confirm
    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "archived"},
    )
    assert r.status_code == 400, r.text
    msg = r.json()["error"]["message"]
    assert isinstance(msg, dict)
    assert msg["enrollment_count"] == 1
    assert msg["requires_confirm"] is True

    # With confirm
    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "archived", "confirm": True},
    )
    assert r.status_code == 200, r.text
    assert r.json()["lifecycle_stage"] == "archived"


# --------------------------------------------------------------------------
# Transition: empty-course publish guard
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_empty_course_returns_400(admin_client, test_db):
    """Publishing a draft course with no lessons raises EmptyCourseError -> 400."""
    course = await _make_course(test_db, title="Empty Shell")

    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "published"},
    )
    assert r.status_code == 400, r.text
    msg = r.json()["error"]["message"]
    assert isinstance(msg, str)
    assert "empty course" in msg.lower()


# --------------------------------------------------------------------------
# Transition: auth
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_non_admin_is_forbidden(staff_client, test_db):
    course = await _make_course(test_db, title="StaffOnly")
    r = await staff_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "published"},
    )
    assert r.status_code == 403


# --------------------------------------------------------------------------
# Transition: old stage values are rejected by the enum
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transition_to_in_review_is_rejected(admin_client, test_db):
    """in_review is no longer a valid stage; the API should 422 on it."""
    course = await _make_course(test_db, title="OldStage")
    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "in_review"},
    )
    assert r.status_code == 422, r.text


@pytest.mark.asyncio
async def test_transition_to_needs_revision_is_rejected(admin_client, test_db):
    """needs_revision is no longer a valid stage; the API should 422."""
    course = await _make_course(test_db, title="OldStage2")
    r = await admin_client.post(
        f"/api/v1/learning/admin/courses/{course.id}/transition",
        json={"to_stage": "needs_revision"},
    )
    assert r.status_code == 422, r.text


# --------------------------------------------------------------------------
# List endpoint: stage filter
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_filters_by_stage(admin_client, test_db):
    """?stage=published returns only published courses."""
    await _make_course(
        test_db, title="A", lifecycle_stage=CourseLifecycleStage.PUBLISHED
    )
    await _make_course(
        test_db, title="B", lifecycle_stage=CourseLifecycleStage.DRAFT
    )
    await _make_course(
        test_db, title="C", lifecycle_stage=CourseLifecycleStage.PUBLISHED
    )

    r = await admin_client.get(
        "/api/v1/learning/admin/courses?stage=published"
    )
    assert r.status_code == 200, r.text
    titles = sorted(c["title"] for c in r.json())
    assert titles == ["A", "C"]
    for c in r.json():
        assert c["lifecycle_stage"] == "published"


@pytest.mark.asyncio
async def test_list_filters_by_review_due(admin_client, test_db):
    """?review_due=true returns only stale published courses."""
    now = datetime.now(timezone.utc)
    past = now - timedelta(days=10)
    future = now + timedelta(days=30)

    await _make_course(
        test_db,
        title="Fresh",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        review_due_at=future,
        last_reviewed_at=now,
    )
    await _make_course(
        test_db,
        title="Stale",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        review_due_at=past,
        last_reviewed_at=past - timedelta(days=365),
    )
    await _make_course(
        test_db,
        title="DraftIgnored",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
        review_due_at=past,
    )

    r = await admin_client.get(
        "/api/v1/learning/admin/courses?review_due=true"
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    titles = [c["title"] for c in rows]
    assert titles == ["Stale"]
    assert rows[0]["is_review_due"] is True


# --------------------------------------------------------------------------
# Review queue endpoint
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_queue_matches_list_review_due(admin_client, test_db):
    now = datetime.now(timezone.utc)
    past_far = now - timedelta(days=60)
    past_near = now - timedelta(days=5)
    future = now + timedelta(days=10)

    await _make_course(
        test_db,
        title="StaleFar",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        review_due_at=past_far,
    )
    await _make_course(
        test_db,
        title="StaleNear",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        review_due_at=past_near,
    )
    await _make_course(
        test_db,
        title="NotDue",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        review_due_at=future,
    )

    list_r = await admin_client.get(
        "/api/v1/learning/admin/courses?review_due=true"
    )
    queue_r = await admin_client.get(
        "/api/v1/learning/admin/courses/review-queue"
    )
    assert list_r.status_code == 200
    assert queue_r.status_code == 200, queue_r.text

    list_titles = sorted(c["title"] for c in list_r.json())
    queue_body = queue_r.json()
    queue_titles_sorted = sorted(c["title"] for c in queue_body["courses"])
    assert list_titles == queue_titles_sorted == ["StaleFar", "StaleNear"]
    assert queue_body["due_count"] == 2
    assert [c["title"] for c in queue_body["courses"]] == [
        "StaleFar",
        "StaleNear",
    ]
    assert queue_body["soonest_due_at"] is not None


# --------------------------------------------------------------------------
# Deprecated publish-toggle: still works + emits Deprecation header
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_legacy_publish_toggle_publishes_and_emits_deprecation(
    admin_client, test_db
):
    """PATCH /admin/courses/{id}/publish with is_published=true now works
    from DRAFT directly (no in_review intermediate needed)."""
    course = await _make_course(
        test_db, title="LegacyPub", lifecycle_stage=CourseLifecycleStage.DRAFT
    )
    await _add_module_with_lesson(test_db, course)

    r = await admin_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={"is_published": True},
    )
    assert r.status_code == 200, r.text
    assert r.headers.get("Deprecation") == "true"
    assert "transition" in r.headers.get("Link", "")
    body = r.json()
    assert body["is_published"] is True
    await test_db.refresh(course)
    assert course.lifecycle_stage == CourseLifecycleStage.PUBLISHED


@pytest.mark.asyncio
async def test_legacy_publish_toggle_unpublish_routes_to_draft(
    admin_client, test_db
):
    """is_published=false drives PUBLISHED -> DRAFT directly."""
    course = await _make_course(
        test_db,
        title="LegacyUnpub",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
    )
    r = await admin_client.patch(
        f"/api/v1/learning/admin/courses/{course.id}/publish",
        json={"is_published": False},
    )
    assert r.status_code == 200, r.text
    await test_db.refresh(course)
    assert course.lifecycle_stage == CourseLifecycleStage.DRAFT


# --------------------------------------------------------------------------
# Audit log: one row per transition
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_each_transition_writes_one_audit_row(admin_client, test_db):
    course = await _make_course(test_db, title="Audit")
    await _add_module_with_lesson(test_db, course)

    # draft -> published -> draft -> archived
    transitions = [
        ("published", None),
        ("draft", None),
        ("archived", True),
    ]
    for to_stage, confirm in transitions:
        payload = {"to_stage": to_stage}
        if confirm:
            payload["confirm"] = True
        r = await admin_client.post(
            f"/api/v1/learning/admin/courses/{course.id}/transition",
            json=payload,
        )
        assert r.status_code == 200, (to_stage, r.text)

    rows = (
        await test_db.execute(
            select(CourseStageTransition).where(
                CourseStageTransition.course_id == course.id
            )
        )
    ).scalars().all()
    assert len(rows) == 3
    stages = [r.to_stage for r in rows]
    assert stages == [
        CourseLifecycleStage.PUBLISHED,
        CourseLifecycleStage.DRAFT,
        CourseLifecycleStage.ARCHIVED,
    ]


# --------------------------------------------------------------------------
# GET /admin/courses/{id}/transitions  (stage-history panel)
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_history_returns_rows_newest_first(admin_client, test_db):
    """History endpoint lists transitions reverse-chronologically with actor."""
    course = await _make_course(test_db, title="HistC")
    await _add_module_with_lesson(test_db, course)

    for to_stage in ("published", "draft", "archived"):
        payload: dict[str, object] = {"to_stage": to_stage, "note": f"-> {to_stage}"}
        if to_stage == "archived":
            payload["confirm"] = True
        r = await admin_client.post(
            f"/api/v1/learning/admin/courses/{course.id}/transition",
            json=payload,
        )
        assert r.status_code == 200, (to_stage, r.text)

    r = await admin_client.get(
        f"/api/v1/learning/admin/courses/{course.id}/transitions"
    )
    assert r.status_code == 200, r.text
    history = r.json()
    assert [h["to_stage"] for h in history] == ["archived", "draft", "published"]
    newest = history[0]
    assert newest["from_stage"] == "draft"
    assert newest["note"] == "-> archived"
    assert newest["actor"] is not None
    assert newest["actor"]["id"]
    assert "display_name" in newest["actor"]


@pytest.mark.asyncio
async def test_stage_history_empty_for_untouched_course(admin_client, test_db):
    course = await _make_course(test_db, title="NoHist")
    r = await admin_client.get(
        f"/api/v1/learning/admin/courses/{course.id}/transitions"
    )
    assert r.status_code == 200, r.text
    assert r.json() == []


@pytest.mark.asyncio
async def test_stage_history_non_admin_forbidden(staff_client, test_db):
    course = await _make_course(test_db, title="HistAuth")
    r = await staff_client.get(
        f"/api/v1/learning/admin/courses/{course.id}/transitions"
    )
    assert r.status_code == 403, r.text


# --------------------------------------------------------------------------
# Pure-function transition matrix (no DB required)
# --------------------------------------------------------------------------


def test_transition_matrix_draft():
    from app.services.course_lifecycle_service import ALLOWED_TRANSITIONS
    allowed = ALLOWED_TRANSITIONS[CourseLifecycleStage.DRAFT]
    assert CourseLifecycleStage.PUBLISHED in allowed
    assert CourseLifecycleStage.ARCHIVED in allowed
    assert CourseLifecycleStage.DRAFT not in allowed


def test_transition_matrix_published():
    from app.services.course_lifecycle_service import ALLOWED_TRANSITIONS
    allowed = ALLOWED_TRANSITIONS[CourseLifecycleStage.PUBLISHED]
    assert CourseLifecycleStage.DRAFT in allowed
    assert CourseLifecycleStage.ARCHIVED in allowed
    assert CourseLifecycleStage.PUBLISHED not in allowed


def test_transition_matrix_archived():
    from app.services.course_lifecycle_service import ALLOWED_TRANSITIONS
    allowed = ALLOWED_TRANSITIONS[CourseLifecycleStage.ARCHIVED]
    assert CourseLifecycleStage.DRAFT in allowed
    assert CourseLifecycleStage.PUBLISHED not in allowed
    assert CourseLifecycleStage.ARCHIVED not in allowed


def test_all_stages_covered():
    from app.services.course_lifecycle_service import ALLOWED_TRANSITIONS
    assert set(ALLOWED_TRANSITIONS.keys()) == {
        CourseLifecycleStage.DRAFT,
        CourseLifecycleStage.PUBLISHED,
        CourseLifecycleStage.ARCHIVED,
    }


def test_old_stages_not_in_enum():
    """in_review and needs_revision must not exist in the enum."""
    stage_values = {s.value for s in CourseLifecycleStage}
    assert "in_review" not in stage_values
    assert "needs_revision" not in stage_values
