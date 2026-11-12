# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for ``courses.created_by_id`` FK + endpoint population.

Wave 1 of the L30 course-authoring friction strip. Verifies:

  1. The column exists, is nullable, and an FK row + a legacy NULL row both
     persist.
  2. ON DELETE SET NULL: deleting the creator user nulls ``created_by_id``
     on courses they created — courses survive.
  3. POST /api/v1/learning/courses stamps the caller's user.id.
  4. POST /api/v1/learning/admin/courses/{id}/clone stamps the CLONER's
     user.id (NOT the source course's creator), so a fresh draft is
     "owned" by whoever triggered the clone.

Async fixture pattern (test_db, test_admin) follows the existing
tests/api/v1/test_learning_admin_clone.py style; ``asyncio_mode = "auto"``
in pyproject.toml means we don't need @pytest.mark.asyncio decorators.

Auth pattern: override ``get_current_user`` in FastAPI's dep map so the
endpoint sees our fixture user, bypassing the JWT/Redis token cache that
otherwise fail-secures as "token revoked" in test envs.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import Course, CourseLifecycleStage
from app.models.user import User, UserRole


# ──────────────────────────────────────────────────────────────────────────
# 1) Column-level: column exists, nullable, ON DELETE SET NULL
# ──────────────────────────────────────────────────────────────────────────


async def test_course_created_by_id_column_exists_and_is_nullable(test_db):
    """New courses accept created_by_id FK; legacy courses tolerate NULL."""
    user = User(
        email="creator@example.com",
        password_hash="x",
        first_name="Creator",
        last_name="User",
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    await test_db.flush()

    c_with = Course(
        title="With creator",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
        created_by_id=user.id,
    )
    c_null = Course(
        title="Legacy",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
    )
    test_db.add_all([c_with, c_null])
    await test_db.commit()
    await test_db.refresh(c_with)
    await test_db.refresh(c_null)

    assert c_with.created_by_id == user.id
    assert c_null.created_by_id is None


async def test_course_creator_set_null_on_user_delete(test_db):
    """ON DELETE SET NULL: deleting the creator nulls created_by_id; course survives.

    Production runs Postgres which enforces FK actions natively. The CI
    fallback runs SQLite with FK enforcement OFF (conftest disables PRAGMA
    foreign_keys during cross-table cleanup), and with the NullPool every
    operation can land on a fresh connection so a session-local PRAGMA
    won't reliably persist. Rather than mock the constraint behavior, this
    test runs only when the bound dialect is Postgres — where the test
    actually exercises the constraint we care about. The schema-level
    presence of the FK (DDL inspectable in init_db / alembic) is already
    asserted indirectly by the column-exists test above.
    """
    bind = test_db.get_bind() if hasattr(test_db, "get_bind") else test_db.bind
    dialect_name = bind.dialect.name
    if dialect_name != "postgresql":
        pytest.skip(
            f"ON DELETE SET NULL enforcement requires Postgres; "
            f"bound dialect is {dialect_name}"
        )

    user = User(
        email="dropme@example.com",
        password_hash="x",
        first_name="Drop",
        last_name="Me",
        role=UserRole.ADMIN,
    )
    test_db.add(user)
    await test_db.flush()

    course = Course(
        title="Owned",
        lifecycle_stage=CourseLifecycleStage.DRAFT,
        created_by_id=user.id,
    )
    test_db.add(course)
    await test_db.commit()
    course_id = course.id

    await test_db.delete(user)
    await test_db.commit()

    # Re-fetch from DB so the ORM doesn't hand back a cached row with the
    # stale FK value; the SET NULL happens at the DB layer.
    test_db.expire_all()
    fresh = (
        await test_db.execute(select(Course).where(Course.id == course_id))
    ).scalar_one()
    assert fresh.created_by_id is None
    assert fresh.id == course_id


# ──────────────────────────────────────────────────────────────────────────
# 2) Endpoint-level: POST /courses and clone populate created_by_id
# ──────────────────────────────────────────────────────────────────────────


@pytest.fixture
def admin_client(client, test_admin):
    """Client where get_current_user resolves to an admin user."""
    app.dependency_overrides[get_current_user] = lambda: test_admin
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def test_post_courses_populates_created_by_id(
    admin_client, test_admin, test_db
):
    resp = await admin_client.post(
        "/api/v1/learning/courses",
        json={
            "title": "Owned by admin",
            "access_level": "patron",
            "difficulty": "beginner",
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["created_by_id"] == test_admin.id

    # Verify DB row reflects the same.
    db_course = (
        await test_db.execute(
            select(Course).where(Course.id == body["id"])
        )
    ).scalar_one()
    assert db_course.created_by_id == test_admin.id


async def test_clone_course_assigns_caller_not_source_creator(
    admin_client, test_admin, test_db
):
    """Cloning a course owned by another user assigns the CLONER as creator."""
    # Seed: a course owned by some other admin (not test_admin).
    other_admin = User(
        email="other-admin@example.com",
        password_hash="x",
        first_name="Other",
        last_name="Admin",
        role=UserRole.ADMIN,
    )
    test_db.add(other_admin)
    await test_db.flush()

    source = Course(
        title="Source course",
        description="Source desc",
        access_level="patron",
        difficulty="beginner",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        created_by_id=other_admin.id,
    )
    test_db.add(source)
    await test_db.commit()
    await test_db.refresh(source)
    source_id = source.id
    other_admin_id = other_admin.id

    cloned = await admin_client.post(
        f"/api/v1/learning/admin/courses/{source_id}/clone",
        json={"new_title": "Source course - clone"},
    )
    assert cloned.status_code == 201, cloned.text
    body = cloned.json()
    # The clone is owned by the caller (test_admin), not the source's creator.
    assert body["created_by_id"] == test_admin.id
    assert body["created_by_id"] != other_admin_id

    # Source course is untouched.
    src_after = (
        await test_db.execute(select(Course).where(Course.id == source_id))
    ).scalar_one()
    assert src_after.created_by_id == other_admin_id
