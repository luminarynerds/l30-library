# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test for finding C4 (2026-07-04 Fernet/PII audit).

`sealed_sections_encrypted` on BoardMinutes was dead: never read or written
anywhere, with a comment falsely claiming "Fernet-encrypted JSON" protection
that was never implemented. Maintainer call: whole-document `is_sealed` is the
intended and sufficient protection -- the column and its misleading comment
were deleted, not wired up.
"""

import pathlib

import pytest

BACKEND = pathlib.Path(__file__).resolve().parents[2]


@pytest.mark.unit
class TestSealedSectionsEncryptedColumnRemoved:
    def test_column_not_on_model(self):
        from sqlalchemy import inspect as sa_inspect

        from app.models.board.minutes import BoardMinutes

        columns = {col.key for col in sa_inspect(BoardMinutes).columns}
        assert "sealed_sections_encrypted" not in columns

    def test_is_sealed_protection_still_present(self):
        """The intended protection (whole-document seal) must stay intact."""
        from sqlalchemy import inspect as sa_inspect

        from app.models.board.minutes import BoardMinutes

        columns = {col.key for col in sa_inspect(BoardMinutes).columns}
        assert "is_sealed" in columns

    def test_no_references_left_anywhere_in_app(self):
        """Regression guard: nothing in app/ should reference the removed
        column again without also re-adding it to the model + a migration."""
        for path in (BACKEND / "app").rglob("*.py"):
            assert "sealed_sections_encrypted" not in path.read_text(), (
                f"{path} references the removed sealed_sections_encrypted column"
            )

    def test_drop_migration_is_idempotent_safe(self):
        """The drop migration must use IF EXISTS/IF NOT EXISTS -- init_db.py
        auto-creates tables from current model metadata at container startup,
        so a fresh install's board_minutes never had this column, and a bare
        DROP COLUMN (no IF EXISTS) would fail there."""
        migration = (
            BACKEND / "alembic" / "versions" / "board_seal_002_drop_sealed_sections_encrypted.py"
        )
        assert migration.exists()
        src = migration.read_text()
        assert "DROP COLUMN IF EXISTS sealed_sections_encrypted" in src
        assert "ADD COLUMN IF NOT EXISTS sealed_sections_encrypted" in src
