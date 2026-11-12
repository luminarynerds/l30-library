# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for backend/scripts/check_alembic_idempotent.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Make scripts/ importable
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from scripts.check_alembic_idempotent import (  # noqa: E402
    ALLOWLISTED_REVISIONS,
    find_violations,
    main,
    scan_directory,
)


def _write_migration(
    tmp_path: Path,
    *,
    name: str,
    revision: str,
    body: str,
) -> Path:
    """Write a minimal synthetic migration file and return its path."""
    src = (
        '"""synthetic migration for tests."""\n'
        "from typing import Sequence, Union\n"
        "from alembic import op\n"
        "import sqlalchemy as sa\n"
        "\n"
        f'revision: str = "{revision}"\n'
        'down_revision: Union[str, None] = None\n'
        'branch_labels: Union[str, Sequence[str], None] = None\n'
        'depends_on: Union[str, Sequence[str], None] = None\n'
        "\n"
        "def upgrade() -> None:\n"
        f"{body}\n"
        "\n"
        "def downgrade() -> None:\n"
        "    pass\n"
    )
    f = tmp_path / name
    f.write_text(src, encoding="utf-8")
    return f


class TestFindViolations:
    def test_flags_op_create_table_in_new_migration(self, tmp_path):
        f = _write_migration(
            tmp_path,
            name="20990101_new.py",
            revision="new_unallowlisted_001",
            body=(
                "    op.create_table(\n"
                '        "widgets",\n'
                "        sa.Column('id', sa.Integer(), primary_key=True),\n"
                "    )"
            ),
        )
        violations = find_violations(f)
        assert len(violations) == 1
        path, lineno, revision, op_name = violations[0]
        assert path == f
        assert revision == "new_unallowlisted_001"
        assert lineno > 0
        assert op_name == "op.create_table"

    def test_ignores_op_execute_create_table_if_not_exists(self, tmp_path):
        f = _write_migration(
            tmp_path,
            name="20990101_new.py",
            revision="new_unallowlisted_002",
            body=(
                "    op.execute(\n"
                '        "CREATE TABLE IF NOT EXISTS widgets (id SERIAL PRIMARY KEY)"\n'
                "    )"
            ),
        )
        assert find_violations(f) == []

    def test_allowlisted_revision_with_op_create_table_is_ignored(self, tmp_path):
        # Pick any historical allowlisted revision
        historical = next(iter(ALLOWLISTED_REVISIONS))
        f = _write_migration(
            tmp_path,
            name="20260101_legacy.py",
            revision=historical,
            body=(
                "    op.create_table(\n"
                '        "ancient_thing",\n'
                "        sa.Column('id', sa.Integer(), primary_key=True),\n"
                "    )"
            ),
        )
        assert find_violations(f) == []

    def test_missing_revision_is_flagged_conservatively(self, tmp_path):
        """A file with no `revision = ...` and an op.create_table is still flagged."""
        src = (
            '"""no revision line."""\n'
            "from alembic import op\n"
            'op.create_table("x")\n'
        )
        f = tmp_path / "weird.py"
        f.write_text(src, encoding="utf-8")
        violations = find_violations(f)
        assert len(violations) == 1
        assert violations[0][2] is None  # revision is None

    def test_other_create_table_method_calls_ignored(self, tmp_path):
        """Only `op.create_table` (Attribute on Name 'op') counts."""
        src = (
            '"""no alembic op."""\n'
            "from typing import Union\n"
            'revision: str = "other_001"\n'
            "def upgrade():\n"
            "    something_else.create_table('x')\n"
            "    helpers.create_table('y')\n"
        )
        f = tmp_path / "other.py"
        f.write_text(src, encoding="utf-8")
        assert find_violations(f) == []

    def test_rename_table_call_is_flagged_in_new_migration(self, tmp_path):
        f = _write_migration(
            tmp_path,
            name="20990101_rename_new.py",
            revision="new_unallowlisted_rename_001",
            body='    op.rename_table("old_widgets", "widgets")',
        )
        violations = find_violations(f)
        assert len(violations) == 1
        path, lineno, revision, op_name = violations[0]
        assert path == f
        assert revision == "new_unallowlisted_rename_001"
        assert lineno > 0
        assert op_name == "op.rename_table"

    def test_rename_table_call_is_ignored_in_allowlisted_migration(self, tmp_path):
        # rename_event_program_partners_001 is in the historical allowlist
        # because it already ran on prod via the manual workaround.
        assert "rename_event_program_partners_001" in ALLOWLISTED_REVISIONS
        f = _write_migration(
            tmp_path,
            name="20260515_legacy_rename.py",
            revision="rename_event_program_partners_001",
            body='    op.rename_table("old_widgets", "widgets")',
        )
        assert find_violations(f) == []

    def test_idempotent_rename_pattern_passes(self, tmp_path):
        """The raw-SQL DROP-IF-EXISTS + ALTER RENAME pattern is not flagged."""
        f = _write_migration(
            tmp_path,
            name="20990101_idempotent_rename.py",
            revision="new_unallowlisted_rename_002",
            body=(
                "    op.execute('DROP TABLE IF EXISTS \"widgets\"')\n"
                "    op.execute('ALTER TABLE \"old_widgets\" RENAME TO \"widgets\"')"
            ),
        )
        assert find_violations(f) == []


class TestScanDirectory:
    def test_repo_versions_dir_has_no_violations(self):
        """The real backend/alembic/versions/ must pass after this PR.

        This guards against regression: any NEW migration that introduces
        op.create_table() will fail this test, forcing the author to either
        rewrite to IF NOT EXISTS or explicitly allowlist (rarely correct).
        """
        versions_dir = BACKEND_DIR / "alembic" / "versions"
        violations = scan_directory(versions_dir)
        assert violations == [], (
            "Unexpected op.create_table / op.rename_table calls in non-allowlisted migrations:\n"
            + "\n".join(
                f"  {p}:{lineno} {op_name} (revision={rev!r})"
                for p, lineno, rev, op_name in violations
            )
        )


class TestMainExitCode:
    def test_exits_zero_when_clean(self, tmp_path, capsys):
        _write_migration(
            tmp_path,
            name="20990101_clean.py",
            revision="clean_001",
            body=(
                "    op.execute(\n"
                '        "CREATE TABLE IF NOT EXISTS widgets (id SERIAL PRIMARY KEY)"\n'
                "    )"
            ),
        )
        rc = main(["--versions-dir", str(tmp_path)])
        assert rc == 0

    def test_exits_nonzero_on_violation(self, tmp_path, capsys):
        _write_migration(
            tmp_path,
            name="20990101_bad.py",
            revision="bad_001",
            body=(
                "    op.create_table(\n"
                '        "widgets",\n'
                "        sa.Column('id', sa.Integer(), primary_key=True),\n"
                "    )"
            ),
        )
        rc = main(["--versions-dir", str(tmp_path)])
        assert rc == 1
        out = capsys.readouterr().out
        assert "op.create_table" in out
        assert "bad_001" in out

    def test_exits_two_on_missing_dir(self, tmp_path, capsys):
        rc = main(["--versions-dir", str(tmp_path / "does-not-exist")])
        assert rc == 2
