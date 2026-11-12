# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""End-to-end behavior of the patron-import CLI."""
import pytest
from sqlalchemy import func, select

from app.models.user import User
from scripts.import_patrons_cli import import_patrons


@pytest.mark.asyncio
async def test_import_creates_users_and_returns_tokens(db_session, tmp_path):
    csv_path = tmp_path / "patrons.csv"
    csv_path.write_text(
        "email,first_name,last_name\n"
        "ada@example.org,Ada,Lovelace\n"
        "grace@example.org,Grace,Hopper\n"
    )
    result = await import_patrons(db_session, csv_path, dry_run=False)
    assert result.created == 2
    assert result.skipped_existing == 0
    assert len(result.tokens) == 2  # (email, plaintext_token) per created row
    count = (await db_session.execute(select(func.count(User.id)))).scalar()
    assert count == 2


@pytest.mark.asyncio
async def test_import_skips_existing_emails(db_session, tmp_path):
    csv_path = tmp_path / "patrons.csv"
    csv_path.write_text("email,first_name,last_name\nada@example.org,Ada,Lovelace\n")
    await import_patrons(db_session, csv_path, dry_run=False)
    result = await import_patrons(db_session, csv_path, dry_run=False)
    assert result.created == 0
    assert result.skipped_existing == 1


@pytest.mark.asyncio
async def test_dry_run_writes_nothing(db_session, tmp_path):
    csv_path = tmp_path / "patrons.csv"
    csv_path.write_text("email,first_name,last_name\nada@example.org,Ada,Lovelace\n")
    result = await import_patrons(db_session, csv_path, dry_run=True)
    assert result.created == 1  # would-create count
    count = (await db_session.execute(select(func.count(User.id)))).scalar()
    assert count == 0, "dry_run must not persist"
