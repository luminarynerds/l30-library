# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for book_challenges + acquisition_rationales.

Covers Task 10 of the L30 Acquisition Rationale plan: the GET handler
must expose the rationale on every challenge response (or null), and the
PUT resolution must write lessons_learned back into the rationale's
weeding signal note so future workflows can see what we learned.

Uses the unauthenticated ``client`` fixture and overrides ``get_current_user``
with a non-DB-bound ``User`` instance to dodge the conftest's
``test_staff`` cross-loop flake (see task notes). The User object lives
purely in Python -- accessing ``current_user.role`` never roundtrips DB.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.acquisition_rationale import (
    AcquisitionRationale,
    BehaviorTag,
    SignalType,
    WeedingCondition,
)
from app.models.book_challenge import (
    BookChallenge,
    ChallengeOutcome,
    ChallengeReason,
    ChallengeStatus,
)
from app.models.catalog import CatalogItem
from app.models.user import User, UserRole
from app.services.organization_features_service import OrganizationFeaturesService


def _make_in_memory_staff() -> User:
    """Build a User instance that exists only in Python.

    No session binding -> no lazy DB fetch when the route reads .role.
    Bypasses the conftest test_staff fixture entirely.
    """
    return User(
        id=999_001,
        email="in-memory-staff@example.test",
        first_name="In",
        last_name="Memory",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )


@pytest.fixture
async def staff_overridden_client(client: AsyncClient, test_db: AsyncSession):
    """Wrap the unauthenticated ``client`` fixture with an in-memory staff
    override for ``get_current_user``. Cleaned up after the test.

    Also persists the staff user via ``test_db`` so that FK constraints
    (e.g. book_challenges.resolved_by_id) are satisfied on PUT/resolve.
    Uses a distinct email each run to avoid conflicting with leftover
    rows the conftest cleanup may have failed to drain.
    """
    import uuid

    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    staff = _make_in_memory_staff()
    # Re-randomise email + drop ORM-bound id so test_db can persist a fresh row.
    staff.id = None
    staff.email = f"in-memory-staff-{uuid.uuid4().hex[:8]}@example.test"
    test_db.add(staff)
    await test_db.commit()
    await test_db.refresh(staff)
    staff_id = staff.id
    staff_role = staff.role
    # Detach the ORM object: the route handler accesses .role on
    # current_user and we don't want that to trigger a lazy reload that
    # crosses event loops (the conftest cross-loop flake). A fresh
    # in-memory User with the persisted id satisfies both the FK and
    # the route's attribute access.
    detached = User(
        id=staff_id,
        email=staff.email,
        first_name=staff.first_name,
        last_name=staff.last_name,
        role=staff_role,
        is_active=True,
        email_verified=True,
    )

    async def override_get_current_user():
        return detached

    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        yield client
    finally:
        app.dependency_overrides.pop(get_current_user, None)


async def _ensure_features(test_db: AsyncSession) -> None:
    """Materialise OrganizationFeatures so the route handler's
    is_feature_enabled lookup doesn't trigger an internal commit on the
    test_db session.
    """
    await OrganizationFeaturesService.get_or_create_features(test_db)


async def _seed_tag(test_db: AsyncSession, slug: str = "identity_exploration") -> None:
    """Idempotent seed -- tolerates leftover rows from prior tests when
    the conftest cleanup couldn't fully drain a referenced lookup table.
    """
    from sqlalchemy import select

    existing = await test_db.execute(
        select(BehaviorTag).where(BehaviorTag.slug == slug)
    )
    if existing.scalar_one_or_none() is not None:
        return
    tag = BehaviorTag(slug=slug, label=slug, category="life_stage")
    test_db.add(tag)
    await test_db.flush()


async def _seed_item(test_db: AsyncSession, **overrides) -> CatalogItem:
    defaults = {"title": "Some Title", "author": "A", "item_type": "book"}
    defaults.update(overrides)
    item = CatalogItem(**defaults)
    test_db.add(item)
    await test_db.flush()
    return item


async def _seed_rationale(
    test_db: AsyncSession,
    *,
    catalog_item_id: int,
    **overrides,
) -> AcquisitionRationale:
    base = dict(
        catalog_item_id=catalog_item_id,
        signal_type=SignalType.GAP_IN_COLLECTION,
        primary_use_case_slug="identity_exploration",
        weeding_condition=WeedingCondition.SIGNAL_PERSISTENCE,
    )
    base.update(overrides)
    rat = AcquisitionRationale(**base)
    test_db.add(rat)
    await test_db.flush()
    return rat


async def _seed_challenge(
    test_db: AsyncSession,
    *,
    catalog_item_id: int | None,
    status: ChallengeStatus = ChallengeStatus.UNDER_REVIEW,
) -> BookChallenge:
    challenge = BookChallenge(
        catalog_item_id=catalog_item_id,
        title="Some Title",
        status=status,
        primary_reason=ChallengeReason.LGBTQ_CONTENT,
        outcome=ChallengeOutcome.PENDING,
    )
    test_db.add(challenge)
    await test_db.flush()
    return challenge


@pytest.mark.asyncio
async def test_challenge_get_includes_acquisition_rationale(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """GET /book-challenges/{id} surfaces the linked rationale verbatim."""
    await _ensure_features(test_db)
    await _seed_tag(test_db)
    item = await _seed_item(test_db)
    await _seed_rationale(test_db, catalog_item_id=item.id)
    challenge = await _seed_challenge(test_db, catalog_item_id=item.id)
    await test_db.commit()

    resp = await staff_overridden_client.get(
        f"/api/v1/book-challenges/{challenge.id}"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "acquisition_rationale" in body
    assert body["acquisition_rationale"] is not None
    assert (
        body["acquisition_rationale"]["primary_use_case_slug"]
        == "identity_exploration"
    )
    assert body["acquisition_rationale"]["signal_type"] == "gap_in_collection"


@pytest.mark.asyncio
async def test_challenge_get_handles_missing_rationale(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """Catalog item without a rationale still serializes; field is null."""
    await _ensure_features(test_db)
    item = await _seed_item(test_db)
    challenge = await _seed_challenge(test_db, catalog_item_id=item.id)
    await test_db.commit()

    resp = await staff_overridden_client.get(
        f"/api/v1/book-challenges/{challenge.id}"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("acquisition_rationale") is None


@pytest.mark.asyncio
async def test_challenge_get_no_catalog_link_yields_null_rationale(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """Challenges without a catalog_item_id (e.g. patron-submitted) get null."""
    await _ensure_features(test_db)
    challenge = await _seed_challenge(test_db, catalog_item_id=None)
    await test_db.commit()

    resp = await staff_overridden_client.get(
        f"/api/v1/book-challenges/{challenge.id}"
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body.get("acquisition_rationale") is None


@pytest.mark.asyncio
async def test_resolve_challenge_appends_lessons_to_rationale(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """PUT with lessons_learned + outcome writes back to rationale signal note."""
    await _ensure_features(test_db)
    await _seed_tag(test_db)
    item = await _seed_item(test_db)
    rat = await _seed_rationale(test_db, catalog_item_id=item.id)
    challenge = await _seed_challenge(test_db, catalog_item_id=item.id)
    await test_db.commit()

    resp = await staff_overridden_client.put(
        f"/api/v1/book-challenges/{challenge.id}",
        json={
            "status": "resolved_retained",
            "outcome": "retained",
            "resolution_summary": "Board confirmed retention.",
            "lessons_learned": (
                "Anticipated challenge category was correct; "
                "rationale held up."
            ),
        },
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(rat)
    assert rat.weeding_signal_note is not None
    note = rat.weeding_signal_note
    assert "rationale held up" in note.lower()
    assert f"#{challenge.id}" in note
    assert "retained" in note.lower()


@pytest.mark.asyncio
async def test_resolve_challenge_without_lessons_skips_writeback(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """Resolution without lessons_learned must not touch the rationale."""
    await _ensure_features(test_db)
    await _seed_tag(test_db)
    item = await _seed_item(test_db)
    rat = await _seed_rationale(
        test_db,
        catalog_item_id=item.id,
        weeding_signal_note="original-untouched-note",
    )
    challenge = await _seed_challenge(test_db, catalog_item_id=item.id)
    await test_db.commit()

    resp = await staff_overridden_client.put(
        f"/api/v1/book-challenges/{challenge.id}",
        json={
            "status": "resolved_retained",
            "outcome": "retained",
            "resolution_summary": "Resolved without surfacing lessons.",
        },
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(rat)
    assert rat.weeding_signal_note == "original-untouched-note"


@pytest.mark.asyncio
async def test_resolve_challenge_appends_to_existing_signal_note(
    test_db: AsyncSession, staff_overridden_client: AsyncClient,
):
    """Existing weeding_signal_note text is preserved; lesson is appended."""
    await _ensure_features(test_db)
    await _seed_tag(test_db)
    item = await _seed_item(test_db)
    rat = await _seed_rationale(
        test_db,
        catalog_item_id=item.id,
        weeding_signal_note="prior signal observation",
    )
    challenge = await _seed_challenge(test_db, catalog_item_id=item.id)
    await test_db.commit()

    resp = await staff_overridden_client.put(
        f"/api/v1/book-challenges/{challenge.id}",
        json={
            "status": "resolved_retained",
            "outcome": "retained",
            "lessons_learned": "new lesson appended",
        },
    )
    assert resp.status_code == 200, resp.text

    await test_db.refresh(rat)
    note = rat.weeding_signal_note or ""
    assert note.startswith("prior signal observation")
    assert "new lesson appended" in note
    assert f"#{challenge.id}" in note
