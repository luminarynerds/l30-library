# SPDX-License-Identifier: AGPL-3.0-or-later
import pytest
from sqlalchemy import select
from app.models.user import User, UserRole
from app.models.multi_branch import LibrarySystem
from app.models.circulation_policy import CirculationPolicy
from app.services.setup_progress_service import compute_setup_progress, STEPS


async def _mk_system(db, code: str) -> int:
    sys = LibrarySystem(code=code, name=f"{code} Library")
    db.add(sys)
    await db.flush()
    return sys.id


def _add_user(db, lsid, role, email, is_active=True):
    u = User(email=email, role=role, home_library_system_id=lsid,
             first_name="Test", last_name="User")
    u.is_active = is_active
    db.add(u)
    return u


def _by_id(steps):
    return {s["id"]: s for s in steps}


@pytest.mark.asyncio
async def test_empty_org_all_incomplete(db):
    lsid = await _mk_system(db, "EMPTY")
    steps = await compute_setup_progress(db, lsid)
    assert len(steps) == len(STEPS) == 6
    assert all(s["completed"] is False for s in steps)
    assert _by_id(steps)["add_team"]["count"] == 0


@pytest.mark.asyncio
async def test_add_team_needs_more_than_one_staff(db):
    lsid = await _mk_system(db, "TEAM")
    _add_user(db, lsid, UserRole.ADMIN, "a@x.org")
    await db.flush()
    steps = _by_id(await compute_setup_progress(db, lsid))
    assert steps["add_team"]["completed"] is False
    _add_user(db, lsid, UserRole.STAFF, "b@x.org")
    await db.flush()
    steps = _by_id(await compute_setup_progress(db, lsid))
    assert steps["add_team"]["completed"] is True
    assert steps["add_team"]["count"] == 2


@pytest.mark.asyncio
async def test_set_policies_detects_org_scoped_row(db):
    lsid = await _mk_system(db, "POL")
    db.add(CirculationPolicy(library_system_id=lsid))
    await db.flush()
    steps = _by_id(await compute_setup_progress(db, lsid))
    assert steps["set_policies"]["completed"] is True


@pytest.mark.asyncio
async def test_add_patrons_org_scoped(db):
    lsid = await _mk_system(db, "PAT")
    _add_user(db, lsid, UserRole.PATRON, "p@x.org")
    await db.flush()
    steps = _by_id(await compute_setup_progress(db, lsid))
    assert steps["add_patrons"]["completed"] is True


@pytest.mark.asyncio
async def test_org_scoping_isolates_team_and_patrons(db):
    a = await _mk_system(db, "ORGA")
    b = await _mk_system(db, "ORGB")
    _add_user(db, a, UserRole.ADMIN, "a1@x.org")
    _add_user(db, a, UserRole.STAFF, "a2@x.org")
    _add_user(db, a, UserRole.PATRON, "ap@x.org")
    db.add(CirculationPolicy(library_system_id=a))
    await db.flush()
    steps_b = _by_id(await compute_setup_progress(db, b))
    assert steps_b["add_team"]["completed"] is False
    assert steps_b["add_patrons"]["completed"] is False
    assert steps_b["set_policies"]["completed"] is False

@pytest.mark.asyncio
async def test_add_team_counts_active_staff_only(db):
    lsid = await _mk_system(db, "ACTIVE")
    _add_user(db, lsid, UserRole.ADMIN, "admin@x.org")            # active founding admin (count 1)
    _add_user(db, lsid, UserRole.STAFF, "pending@x.org", is_active=False)  # pending invite, must NOT count
    await db.flush()
    steps = {s["id"]: s for s in await compute_setup_progress(db, lsid)}
    assert steps["add_team"]["completed"] is False   # only 1 ACTIVE staff

    # activate the pending user -> now 2 active staff -> complete
    u = (await db.execute(select(User).where(User.email == "pending@x.org"))).scalar_one()
    u.is_active = True
    await db.flush()
    steps = {s["id"]: s for s in await compute_setup_progress(db, lsid)}
    assert steps["add_team"]["completed"] is True
