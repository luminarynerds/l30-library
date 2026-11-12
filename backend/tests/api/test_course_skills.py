# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the Wave 5 course ↔ skill integration.

Covers:
  * Course list responses include `skills: []` by default and the populated
    SkillBrief payload when associations exist.
  * GET /api/v1/learning/skills/{skill_id}/courses returns the right
    `CourseBrief` set, ordered by title, scoped to published / non-deleted.
  * Auth boundary: patrons hit `require_staff` (403); staff (200).

These tests pin the contract the frontend chips and SkillsList disclosure
rely on. If the response shape drifts, both fail loudly.
"""
import pytest
from sqlalchemy import select

from app.api.v1.auth import get_current_user
from app.main import app
from app.models.learning import Course, CourseLifecycleStage, CourseSkill, Skill


# --------------------------------------------------------------------------
# Fixtures / helpers
# --------------------------------------------------------------------------


@pytest.fixture
def staff_client(client, test_staff):
    """Client where get_current_user resolves to a staff caller."""
    app.dependency_overrides[get_current_user] = lambda: test_staff
    yield client
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def patron_client(client, test_patron):
    """Client where get_current_user resolves to a patron."""
    app.dependency_overrides[get_current_user] = lambda: test_patron
    yield client
    app.dependency_overrides.pop(get_current_user, None)


async def _make_course(
    test_db, *, title: str, is_published: bool = True, access: str = "patron"
):
    course = Course(
        title=title,
        description=f"{title} description",
        access_level=access,
        lifecycle_stage=(
            CourseLifecycleStage.PUBLISHED
            if is_published
            else CourseLifecycleStage.DRAFT
        ),
    )
    test_db.add(course)
    await test_db.flush()
    return course


async def _make_skill(test_db, *, name: str, category: str = "library_services"):
    skill = Skill(name=name, description=f"{name} desc", category=category)
    test_db.add(skill)
    await test_db.flush()
    return skill


async def _link(test_db, *, course, skill, level: int = 3):
    cs = CourseSkill(course_id=course.id, skill_id=skill.id, level_taught=level)
    test_db.add(cs)
    await test_db.flush()
    return cs


# --------------------------------------------------------------------------
# Course response shape
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_course_list_includes_empty_skills_by_default(
    staff_client, test_db
):
    """Untagged courses still expose `skills: []` so the chip strip can no-op."""
    await _make_course(test_db, title="Naked Course")
    await test_db.commit()

    response = await staff_client.get("/api/v1/learning/courses")
    assert response.status_code == 200, response.text
    body = response.json()
    target = next((c for c in body if c["title"] == "Naked Course"), None)
    assert target is not None
    # The contract: every course response has a `skills` array (possibly empty).
    assert target["skills"] == []


@pytest.mark.asyncio
async def test_course_list_includes_tagged_skills(staff_client, test_db):
    """Course response embeds `SkillBrief` rows for each tagged skill."""
    course = await _make_course(test_db, title="Reference Desk Basics")
    s1 = await _make_skill(test_db, name="Reference Interview")
    s2 = await _make_skill(test_db, name="Catalog Search", category="technology")
    await _link(test_db, course=course, skill=s1, level=3)
    await _link(test_db, course=course, skill=s2, level=2)
    await test_db.commit()

    response = await staff_client.get("/api/v1/learning/courses")
    assert response.status_code == 200, response.text
    target = next(
        (c for c in response.json() if c["title"] == "Reference Desk Basics"), None
    )
    assert target is not None
    skills = target["skills"]
    assert len(skills) == 2

    by_name = {s["name"]: s for s in skills}
    assert by_name["Reference Interview"]["level_taught"] == 3
    assert by_name["Reference Interview"]["id"] == s1.id
    assert by_name["Catalog Search"]["level_taught"] == 2
    assert by_name["Catalog Search"]["id"] == s2.id


# --------------------------------------------------------------------------
# Reverse lookup: GET /skills/{id}/courses
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_skill_courses_returns_only_tagged_published(
    staff_client, test_db
):
    """Endpoint returns published, non-deleted courses tagged with the skill."""
    skill = await _make_skill(test_db, name="Customer Service")
    other_skill = await _make_skill(test_db, name="Unrelated")
    c1 = await _make_course(test_db, title="Bravo Course")
    c2 = await _make_course(test_db, title="Alpha Course")
    c3 = await _make_course(test_db, title="Unpublished Course", is_published=False)
    untagged = await _make_course(test_db, title="Untagged Course")

    await _link(test_db, course=c1, skill=skill, level=4)
    await _link(test_db, course=c2, skill=skill, level=2)
    await _link(test_db, course=c3, skill=skill, level=1)  # filtered out
    await _link(test_db, course=untagged, skill=other_skill, level=1)
    await test_db.commit()

    response = await staff_client.get(f"/api/v1/learning/skills/{skill.id}/courses")
    assert response.status_code == 200, response.text
    body = response.json()

    titles = [b["title"] for b in body]
    # Sorted by title (case-insensitive); unpublished + other-skill courses excluded.
    assert titles == ["Alpha Course", "Bravo Course"]
    by_title = {b["title"]: b for b in body}
    assert by_title["Alpha Course"]["level_taught"] == 2
    assert by_title["Bravo Course"]["level_taught"] == 4
    # `id` is propagated (frontend uses it for the /learn/course/{id} link).
    assert by_title["Alpha Course"]["id"] == c2.id


@pytest.mark.asyncio
async def test_skill_courses_empty_when_no_associations(staff_client, test_db):
    """A skill with no tagged courses returns 200 + []."""
    skill = await _make_skill(test_db, name="Lonely Skill")
    await test_db.commit()

    response = await staff_client.get(f"/api/v1/learning/skills/{skill.id}/courses")
    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_skill_courses_404_on_missing_skill(staff_client, test_db):
    """Unknown skill id → 404, not silent empty list."""
    # Pick an id that doesn't exist.
    result = await test_db.execute(select(Skill.id).order_by(Skill.id.desc()))
    rows = result.all()
    missing_id = (rows[0][0] + 999) if rows else 9_999_999

    response = await staff_client.get(f"/api/v1/learning/skills/{missing_id}/courses")
    assert response.status_code == 404, response.text


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_patron_cannot_list_courses_for_skill(patron_client, test_db):
    """`require_staff` rejects patrons before any DB work."""
    skill = await _make_skill(test_db, name="Behind The Gate")
    await test_db.commit()

    response = await patron_client.get(f"/api/v1/learning/skills/{skill.id}/courses")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_staff_can_list_courses_for_skill(staff_client, test_db):
    """Staff caller gets 200 (basic happy path mirror of the auth boundary)."""
    skill = await _make_skill(test_db, name="Staff-Visible")
    await test_db.commit()

    response = await staff_client.get(f"/api/v1/learning/skills/{skill.id}/courses")
    assert response.status_code == 200
    assert response.json() == []
