#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Lint check: alembic migrations must not use ``op.create_table`` or ``op.rename_table``.

L30's ``init_db.py`` (via ``scripts/init_schema_async_raw_sql.py``) auto-creates
new tables from SQLAlchemy models at backend startup. If a new alembic migration
then calls ``op.create_table(...)``, that fails with::

    DuplicateTableError: relation "..." already exists

The same trap applies to ``op.rename_table(old, new)``: init_db has already
pre-created the *destination* table from the renamed SQLAlchemy model, so the
rename collides with the pre-existing target.

The fix is to use raw SQL instead. For new tables::

    op.execute("CREATE TABLE IF NOT EXISTS ... (...)")

For renames::

    op.execute('DROP TABLE IF EXISTS "<new>"')  # remove init_db's pre-created target
    op.execute('ALTER TABLE "<old>" RENAME TO "<new>"')

Historical migrations that already shipped and ran against existing installs
are grandfathered via :data:`ALLOWLISTED_REVISIONS`; rewriting them buys nothing
because their tables already exist on every running install.

Exit codes:
  0 — all checks pass
  1 — at least one new migration uses ``op.create_table`` or ``op.rename_table``

Usage:
  python backend/scripts/check_alembic_idempotent.py
  python backend/scripts/check_alembic_idempotent.py --versions-dir path/to/versions
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# Migrations that pre-date this lint rule. They already ran on every install,
# so rewriting them to be idempotent serves no purpose. Identified by their
# ``revision: str = "..."`` value (Alembic revision identifier).
ALLOWLISTED_REVISIONS: frozenset[str] = frozenset({
    "20260512_pay_rates",
    "acquisition_rationales_001",
    "api_keys_001",
    "archival_collections_001",
    "authority_terms_001",
    "behavior_tags_001",
    "beta_feedback_restore_001",
    "beta_redemptions_001",
    "remove_beta_invites_001",
    "blog_author_fk_001",
    "editorial_rss_001",
    "blog_ver_001",
    "blog_views_001",
    "board_amendments_001",
    "board_coi_001",
    "board_compliance_001",
    "board_recusal_001",
    "board_retention_001",
    "book_club_member_imports_001",
    "branding_001",
    "carbon_metrics_001",
    "catalog_state_events_001",
    "cms_restore_001",
    "collection_archival_001",
    "course_lifecycle_001",
    "course_skills_001",
    "engagement_001",
    "event_waitlist_001",
    "fine_waivers_001",
    "home_page_001",
    "home_visit_day_plan_001",
    "home_visit_mutations_001",
    "homepage_quotes_001",
    "indie_prefs_progress_001",
    "legal_002",
    "legal_005",
    "library_visits_001",
    "local_authorities_001",
    "lp_cohort_001",
    "marc_macros_001",
    "mood_categories_001",
    "multipart_sets_001",
    "notification_digest_queue_001",
    "nudges_001",
    "parent_onboarding_export_log_001",
    "pii_access_log_001",
    "program_family_001",
    "reading_list_requests_001",
    "rename_event_program_partners_001",
    "rp_event_credit_001",
    "rpt_sched_001",
    "saved_searches_001",
    "schema_sync_001",
    "schema_sync_003",
    "schema_sync_004",
    "schema_sync_005",
    "staff_presence_001",
    "staff_time_entry_001",
    "subjects_join_001",
    "support_agent_001",
    "sushi_cred_001",
    "tech_facilities_001",
})


def _is_op_create_table(node: ast.AST) -> bool:
    """Return True if ``node`` is a call to ``op.create_table(...)``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr != "create_table":
        return False
    value = func.value
    return isinstance(value, ast.Name) and value.id == "op"


def _is_op_rename_table(node: ast.AST) -> bool:
    """Return True if ``node`` is a call to ``op.rename_table(...)``."""
    if not isinstance(node, ast.Call):
        return False
    func = node.func
    if not isinstance(func, ast.Attribute):
        return False
    if func.attr != "rename_table":
        return False
    value = func.value
    return isinstance(value, ast.Name) and value.id == "op"


def _extract_revision(tree: ast.Module) -> str | None:
    """Extract the value of the top-level ``revision`` assignment, if any."""
    for stmt in tree.body:
        # ``revision: str = "abc"`` is an AnnAssign; ``revision = "abc"`` an Assign.
        target_name = None
        value = None
        if isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name):
                target_name = stmt.target.id
                value = stmt.value
        elif isinstance(stmt, ast.Assign):
            if len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
                target_name = stmt.targets[0].id
                value = stmt.value
        if target_name != "revision":
            continue
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            return value.value
    return None


def find_violations(
    path: Path,
    allowlist: frozenset[str] = ALLOWLISTED_REVISIONS,
) -> list[tuple[Path, int, str | None, str]]:
    """Return ``(file, line, revision, op_name)`` for every disallowed call.

    Detects both ``op.create_table`` and ``op.rename_table`` calls. A call is
    disallowed if it appears in a migration whose revision identifier is NOT
    in ``allowlist``. Migrations with no detectable revision identifier are
    conservatively included (so brand-new files get flagged immediately).
    """
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []
    revision = _extract_revision(tree)
    if revision is not None and revision in allowlist:
        return []
    violations: list[tuple[Path, int, str | None, str]] = []
    for node in ast.walk(tree):
        if _is_op_create_table(node):
            violations.append((path, node.lineno, revision, "op.create_table"))
        elif _is_op_rename_table(node):
            violations.append((path, node.lineno, revision, "op.rename_table"))
    return violations


def scan_directory(
    versions_dir: Path,
    allowlist: frozenset[str] = ALLOWLISTED_REVISIONS,
) -> list[tuple[Path, int, str | None, str]]:
    """Scan every ``*.py`` in ``versions_dir`` and return all violations."""
    out: list[tuple[Path, int, str | None, str]] = []
    for path in sorted(versions_dir.glob("*.py")):
        out.extend(find_violations(path, allowlist=allowlist))
    return out


def _default_versions_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "alembic" / "versions"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Flag alembic migrations using op.create_table() or "
            "op.rename_table() — use op.execute(\"CREATE TABLE IF NOT "
            "EXISTS ...\") / op.execute(\"DROP TABLE IF EXISTS ...; "
            "ALTER TABLE ... RENAME TO ...\") instead so the migration is "
            "idempotent against init_db.py auto-creation."
        )
    )
    parser.add_argument(
        "--versions-dir",
        type=Path,
        default=_default_versions_dir(),
        help="Path to alembic versions/ directory (default: backend/alembic/versions)",
    )
    args = parser.parse_args(argv)

    versions_dir: Path = args.versions_dir
    if not versions_dir.is_dir():
        print(f"error: {versions_dir} is not a directory", file=sys.stderr)
        return 2

    violations = scan_directory(versions_dir)
    if not violations:
        print(
            f"OK: no disallowed op.create_table() / op.rename_table() in {versions_dir}"
        )
        return 0

    print(
        "FAIL: op.create_table() and op.rename_table() are not allowed in new migrations.\n"
        "      For new tables, use op.execute(\"CREATE TABLE IF NOT EXISTS ...\").\n"
        "      For renames, use:\n"
        "          op.execute('DROP TABLE IF EXISTS \"<new>\"')\n"
        "          op.execute('ALTER TABLE \"<old>\" RENAME TO \"<new>\"')\n"
        "      Both patterns are idempotent against init_db.py, which auto-creates\n"
        "      tables from SQLAlchemy models at backend startup.\n"
        "      See backend/scripts/check_alembic_idempotent.py.\n"
    )
    for path, lineno, revision, op_name in violations:
        rev_part = f" (revision={revision!r})" if revision else ""
        print(f"  {path}:{lineno}: {op_name}{rev_part}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
