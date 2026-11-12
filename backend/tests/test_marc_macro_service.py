# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for MARC macro engine and permissions."""

import pytest

from app.models.catalog import CatalogItem, ItemType
from app.models.marc_macro import MarcMacro, MarcMacroVisibility
from app.models.user import User, UserRole
from app.schemas.marc_macro import (
    MarcMacroCreate,
    MarcMacroStep,
    MarcMacroUpdate,
)
from app.services.marc_macro_service import (
    MarcMacroForbidden,
    MarcMacroService,
)


def _step(op: str, tag: str, sub: str, **kw) -> MarcMacroStep:
    return MarcMacroStep(op=op, tag=tag, subfield=sub, **kw)


def _user(id_: int, role: UserRole) -> User:
    u = User(email=f"u{id_}@x", password_hash="x", first_name="A", last_name="B")
    u.id = id_
    u.role = role
    return u


# ---------- step engine (no DB) ----------------------------------------

def test_set_replaces_field_value():
    item = CatalogItem(title="Old", item_type=ItemType.book)
    svc = MarcMacroService(db=None)  # type: ignore[arg-type]
    changed, skipped = svc._apply_steps(item, [_step("set", "245", "a", value="New")])
    assert item.title == "New"
    assert changed == ["title"]
    assert skipped == []


def test_set_to_same_value_is_a_skip():
    item = CatalogItem(title="Same", item_type=ItemType.book)
    svc = MarcMacroService(db=None)  # type: ignore[arg-type]
    changed, skipped = svc._apply_steps(item, [_step("set", "245", "a", value="Same")])
    assert changed == []
    assert skipped == ["set 245$a"]


def test_clear_nulls_field():
    item = CatalogItem(title="x", author="Author", item_type=ItemType.book)
    svc = MarcMacroService(db=None)  # type: ignore[arg-type]
    svc._apply_steps(item, [_step("clear", "100", "a")])
    assert item.author is None


def test_find_replace_substitutes_substring():
    item = CatalogItem(title="x", description="The cat sat", item_type=ItemType.book)
    svc = MarcMacroService(db=None)  # type: ignore[arg-type]
    svc._apply_steps(
        item, [_step("find_replace", "520", "a", find="cat", replace="dog")]
    )
    assert item.description == "The dog sat"


def test_append_to_subjects_dedupes():
    item = CatalogItem(title="x", subjects="History", item_type=ItemType.book)
    svc = MarcMacroService(db=None)  # type: ignore[arg-type]
    svc._apply_steps(item, [_step("append", "650", "a", value="Biography")])
    assert item.subjects == "History, Biography"
    # Re-applying the same step is a no-op.
    changed, _ = svc._apply_steps(
        item, [_step("append", "650", "a", value="Biography")]
    )
    assert changed == []


def test_int_field_coerces_string_value():
    item = CatalogItem(title="x", item_type=ItemType.book)
    svc = MarcMacroService(db=None)  # type: ignore[arg-type]
    svc._apply_steps(item, [_step("set", "260", "c", value="c1972")])
    assert item.publication_year == 1972


def test_unknown_target_raises_before_writing():
    svc = MarcMacroService(db=None)  # type: ignore[arg-type]
    with pytest.raises(KeyError):
        # Direct call exercises the SUPPORTED_TARGETS lookup.
        svc._apply_steps(
            CatalogItem(title="x"),
            [_step("set", "999", "a", value="x")],
        )


# ---------- permissions ------------------------------------------------

def test_admin_may_edit_shared_macro():
    macro = MarcMacro(visibility=MarcMacroVisibility.shared, owner_id=None, name="m")
    MarcMacroService._check_write(macro, _user(1, UserRole.ADMIN))


def test_staff_may_not_edit_shared_macro():
    macro = MarcMacro(visibility=MarcMacroVisibility.shared, owner_id=None, name="m")
    with pytest.raises(MarcMacroForbidden):
        MarcMacroService._check_write(macro, _user(2, UserRole.STAFF))


def test_owner_may_edit_their_private_macro():
    macro = MarcMacro(visibility=MarcMacroVisibility.private, owner_id=7, name="m")
    MarcMacroService._check_write(macro, _user(7, UserRole.STAFF))


def test_other_staff_cannot_edit_someone_elses_private_macro():
    macro = MarcMacro(visibility=MarcMacroVisibility.private, owner_id=7, name="m")
    with pytest.raises(MarcMacroForbidden):
        MarcMacroService._check_write(macro, _user(8, UserRole.STAFF))


def test_admin_can_edit_any_private_macro():
    macro = MarcMacro(visibility=MarcMacroVisibility.private, owner_id=7, name="m")
    MarcMacroService._check_write(macro, _user(99, UserRole.ADMIN))


# ---------- DB-backed CRUD --------------------------------------------

@pytest.mark.asyncio
async def test_create_private_macro_assigns_owner(test_db):
    user = User(
        email="cat@x", password_hash="x", first_name="C", last_name="X",
        role=UserRole.STAFF, is_active=True, email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    svc = MarcMacroService(test_db)
    macro = await svc.create_macro(
        MarcMacroCreate(
            name="My subject preset",
            visibility=MarcMacroVisibility.private,
            steps=[_step("append", "650", "a", value="Local history")],
        ),
        user=user,
    )
    await test_db.commit()
    assert macro.owner_id == user.id
    assert macro.visibility == MarcMacroVisibility.private


@pytest.mark.asyncio
async def test_staff_cannot_create_shared_macro(test_db):
    user = User(
        email="cat2@x", password_hash="x", first_name="C", last_name="X",
        role=UserRole.STAFF, is_active=True, email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()

    svc = MarcMacroService(test_db)
    with pytest.raises(MarcMacroForbidden):
        await svc.create_macro(
            MarcMacroCreate(
                name="Library wide", visibility=MarcMacroVisibility.shared, steps=[],
            ),
            user=user,
        )


@pytest.mark.asyncio
async def test_run_macro_applies_steps_to_each_item(test_db):
    user = User(
        email="cat3@x", password_hash="x", first_name="C", last_name="X",
        role=UserRole.ADMIN, is_active=True, email_verified=True,
    )
    test_db.add(user)
    items = [
        CatalogItem(title="One", subjects="History", item_type=ItemType.book),
        CatalogItem(title="Two", subjects=None, item_type=ItemType.book),
    ]
    for item in items:
        test_db.add(item)
    await test_db.commit()
    for item in items:
        await test_db.refresh(item)

    svc = MarcMacroService(test_db)
    macro = await svc.create_macro(
        MarcMacroCreate(
            name="Add local history",
            visibility=MarcMacroVisibility.shared,
            steps=[_step("append", "650", "a", value="Local history")],
        ),
        user=user,
    )
    await test_db.commit()

    results = await svc.run_macro(
        macro.id, [items[0].id, items[1].id], user=user,
    )
    await test_db.commit()

    for it in items:
        await test_db.refresh(it)
    assert items[0].subjects == "History, Local history"
    assert items[1].subjects == "Local history"
    assert all(r["error"] is None for r in results)


@pytest.mark.asyncio
async def test_run_macro_returns_per_item_error_for_missing_id(test_db):
    user = User(
        email="cat4@x", password_hash="x", first_name="C", last_name="X",
        role=UserRole.STAFF, is_active=True, email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()

    svc = MarcMacroService(test_db)
    macro = await svc.create_macro(
        MarcMacroCreate(
            name="No-op",
            visibility=MarcMacroVisibility.private,
            steps=[_step("set", "245", "a", value="Z")],
        ),
        user=user,
    )
    await test_db.commit()

    results = await svc.run_macro(macro.id, [99999], user=user)
    assert results[0]["error"] == "catalog item not found"


@pytest.mark.asyncio
async def test_update_to_shared_requires_admin(test_db):
    staff = User(
        email="s@x", password_hash="x", first_name="S", last_name="T",
        role=UserRole.STAFF, is_active=True, email_verified=True,
    )
    test_db.add(staff)
    await test_db.commit()

    svc = MarcMacroService(test_db)
    macro = await svc.create_macro(
        MarcMacroCreate(
            name="mine", visibility=MarcMacroVisibility.private, steps=[],
        ),
        user=staff,
    )
    await test_db.commit()

    with pytest.raises(MarcMacroForbidden):
        await svc.update_macro(
            macro.id,
            MarcMacroUpdate(visibility=MarcMacroVisibility.shared),
            user=staff,
        )
