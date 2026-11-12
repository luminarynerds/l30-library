# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Imported patrons must be able to log in via a one-time reset link."""
import pytest
from sqlalchemy import select

from app.models.user import User
from app.services.import_service.service import ImportService
from app.core.security import hash_reset_token


@pytest.mark.asyncio
async def test_create_patron_returns_plaintext_reset_token(db_session):
    user_id, table, reset_token = await ImportService._create_patron(
        db_session,
        {"email": "ada@example.org", "first_name": "Ada", "last_name": "Lovelace"},
    )

    assert table == "users"
    assert reset_token and len(reset_token) >= 32, "must return a usable plaintext token"


@pytest.mark.asyncio
async def test_create_patron_marks_email_verified(db_session):
    user_id, _, _ = await ImportService._create_patron(
        db_session,
        {"email": "grace@example.org", "first_name": "Grace", "last_name": "Hopper"},
    )
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    assert user.email_verified is True, "forgot-password requires email_verified=True"


@pytest.mark.asyncio
async def test_create_patron_persists_hashed_reset_token(db_session):
    user_id, _, reset_token = await ImportService._create_patron(
        db_session,
        {"email": "linus@example.org", "first_name": "Linus", "last_name": "Torvalds"},
    )
    user = (await db_session.execute(select(User).where(User.id == user_id))).scalar_one()
    assert user.reset_token == hash_reset_token(reset_token)
    assert user.reset_token_expires is not None
