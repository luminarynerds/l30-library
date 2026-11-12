# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD tests: imported and self-registered patrons get home_library_system_id set.

  A. ImportService._create_patron must set home_library_system_id to the
     sole LibrarySystem id when one exists.
  B. POST /api/v1/auth/register must set home_library_system_id on the
     created patron to the sole LibrarySystem id.
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

from app.models.multi_branch import LibrarySystem
from app.models.user import User, UserRole


async def _seed_library_system(db, code="TST"):
    sys = LibrarySystem(code=code, name=f"{code} Library")
    db.add(sys)
    await db.flush()
    return sys.id


@pytest.mark.asyncio
async def test_import_create_patron_sets_home_library_system_id(db):
    """_create_patron must stamp home_library_system_id = the sole system id."""
    from app.services.import_service.service import ImportService

    lsid = await _seed_library_system(db, "IMP")

    patron_data = {
        "email": "imported-patron@example.com",
        "first_name": "Imported",
        "last_name": "Patron",
        "barcode": "IMP-0001",
    }

    user_id, table, _reset_token = await ImportService._create_patron(db, patron_data)
    assert table == "users"

    result = await db.execute(select(User).where(User.id == user_id))
    patron = result.scalar_one()

    assert patron.home_library_system_id == lsid, (
        f"_create_patron must set home_library_system_id={lsid!r}; "
        f"got {patron.home_library_system_id!r}"
    )


@pytest.mark.asyncio
async def test_self_register_sets_home_library_system_id(db, client):
    """POST /api/v1/auth/register must stamp home_library_system_id."""
    lsid = await _seed_library_system(db, "REG")

    with patch(
        "app.api.v1.auth.registration.verify_turnstile",
        new=AsyncMock(return_value=True),
    ):
        resp = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "self-reg-patron@example.com",
                "password": "SecurePass1!",
                "first_name": "Self",
                "last_name": "Reg",
                "turnstile_token": "test-ok",
            },
        )

    assert resp.status_code == 201, resp.text

    result = await db.execute(
        select(User).where(User.email == "self-reg-patron@example.com")
    )
    patron = result.scalar_one()

    assert patron.home_library_system_id == lsid, (
        f"self-registration must set home_library_system_id={lsid!r}; "
        f"got {patron.home_library_system_id!r}"
    )
