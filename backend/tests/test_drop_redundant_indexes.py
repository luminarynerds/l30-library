# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""AST tests for the drop_redundant_indexes_001 migration.

These are static checks that guard the contract of the migration:
  * upgrade() drops EXACTLY the expected 8 indexes, no more, no less.
  * downgrade() recreates the same 8 indexes.
  * down_revision points at the current single head when the migration
    was written (bc_waitlist_001).

The test reads the migration file with ``ast.parse`` and walks the
AST -- it never imports or runs the alembic migration against a DB.
"""
from __future__ import annotations

import ast
from pathlib import Path


MIGRATION_PATH = (
    Path(__file__).resolve().parent.parent
    / "alembic"
    / "versions"
    / "20260520_drop_redundant_indexes_001_drop_redundant_indexes.py"
)

EXPECTED_INDEXES = {
    "ix_catalog_items_subjects",
    "ix_catalog_items_artist",
    "ix_catalog_items_binding",
    "ix_catalog_items_sequence_in_set",
    "ix_job_execution_logs_id",
    "ix_job_execution_logs_job_id",
    "ix_job_exec_recent",
    "ix_job_exec_job_success",
}


def _function_def(tree: ast.AST, name: str) -> ast.FunctionDef:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"function {name!r} not found in migration")


def _collect_op_calls(func: ast.FunctionDef, attr_name: str) -> list[ast.Call]:
    """Return every ``op.<attr_name>(...)`` Call node inside ``func``."""
    out: list[ast.Call] = []
    for sub in ast.walk(func):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == attr_name
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "op"
        ):
            out.append(sub)
    return out


def _first_string_arg(call: ast.Call) -> str:
    assert call.args, "expected at least one positional arg"
    first = call.args[0]
    assert isinstance(first, ast.Constant) and isinstance(first.value, str), (
        f"expected first arg to be a string literal, got {ast.dump(first)}"
    )
    return first.value


class TestDropRedundantIndexesMigration:
    def setup_method(self) -> None:
        self.source = MIGRATION_PATH.read_text(encoding="utf-8")
        self.tree = ast.parse(self.source)

    def test_migration_file_exists(self) -> None:
        assert MIGRATION_PATH.exists(), f"missing migration: {MIGRATION_PATH}"

    def test_down_revision_is_bc_waitlist_001(self) -> None:
        """The migration must chain directly off the head at write-time."""
        for node in ast.walk(self.tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "down_revision"
            ):
                assert isinstance(node.value, ast.Constant)
                assert node.value.value == "bc_waitlist_001", (
                    f"down_revision is {node.value.value!r}, expected 'bc_waitlist_001'"
                )
                return
        raise AssertionError("down_revision assignment not found")

    def test_revision_id_matches(self) -> None:
        for node in ast.walk(self.tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "revision"
            ):
                assert isinstance(node.value, ast.Constant)
                assert node.value.value == "drop_redundant_indexes_001"
                return
        raise AssertionError("revision assignment not found")

    def test_upgrade_drops_exact_expected_set(self) -> None:
        upgrade = _function_def(self.tree, "upgrade")
        drop_calls = _collect_op_calls(upgrade, "drop_index")
        dropped = {_first_string_arg(c) for c in drop_calls}
        assert dropped == EXPECTED_INDEXES, (
            f"upgrade() drop_index set mismatch.\n"
            f"  unexpected drops: {sorted(dropped - EXPECTED_INDEXES)}\n"
            f"  missing drops:    {sorted(EXPECTED_INDEXES - dropped)}"
        )

    def test_upgrade_only_calls_drop_index(self) -> None:
        """upgrade() must not perform any other op.* calls (no data writes,
        no DDL beyond the listed drops)."""
        upgrade = _function_def(self.tree, "upgrade")
        other_ops: list[str] = []
        for sub in ast.walk(upgrade):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id == "op"
                and sub.func.attr != "drop_index"
            ):
                other_ops.append(sub.func.attr)
        assert not other_ops, (
            f"upgrade() contains unexpected op.* calls: {sorted(set(other_ops))}"
        )

    def test_downgrade_recreates_exact_expected_set(self) -> None:
        downgrade = _function_def(self.tree, "downgrade")
        create_calls = _collect_op_calls(downgrade, "create_index")
        created = {_first_string_arg(c) for c in create_calls}
        assert created == EXPECTED_INDEXES, (
            f"downgrade() create_index set mismatch.\n"
            f"  unexpected creates: {sorted(created - EXPECTED_INDEXES)}\n"
            f"  missing creates:    {sorted(EXPECTED_INDEXES - created)}"
        )

    def test_downgrade_only_calls_create_index(self) -> None:
        downgrade = _function_def(self.tree, "downgrade")
        other_ops: list[str] = []
        for sub in ast.walk(downgrade):
            if (
                isinstance(sub, ast.Call)
                and isinstance(sub.func, ast.Attribute)
                and isinstance(sub.func.value, ast.Name)
                and sub.func.value.id == "op"
                and sub.func.attr != "create_index"
            ):
                other_ops.append(sub.func.attr)
        assert not other_ops, (
            f"downgrade() contains unexpected op.* calls: {sorted(set(other_ops))}"
        )

    def test_binding_recreate_preserves_partial_predicate(self) -> None:
        """The original ix_catalog_items_binding is a partial index
        (WHERE binding IS NOT NULL); the recreate must preserve that."""
        downgrade = _function_def(self.tree, "downgrade")
        create_calls = _collect_op_calls(downgrade, "create_index")
        for call in create_calls:
            if not call.args:
                continue
            name_arg = call.args[0]
            if (
                isinstance(name_arg, ast.Constant)
                and name_arg.value == "ix_catalog_items_binding"
            ):
                where_kw = next(
                    (kw for kw in call.keywords if kw.arg == "postgresql_where"),
                    None,
                )
                assert where_kw is not None, (
                    "downgrade ix_catalog_items_binding must pass postgresql_where"
                )
                assert isinstance(where_kw.value, ast.Constant)
                assert "binding IS NOT NULL" in where_kw.value.value
                return
        raise AssertionError("ix_catalog_items_binding recreate not found in downgrade")

    def test_drops_use_if_exists(self) -> None:
        """Every drop_index call should pass if_exists=True for safe replay."""
        upgrade = _function_def(self.tree, "upgrade")
        drop_calls = _collect_op_calls(upgrade, "drop_index")
        for call in drop_calls:
            kw = next((k for k in call.keywords if k.arg == "if_exists"), None)
            assert kw is not None, (
                f"drop_index({_first_string_arg(call)!r}) missing if_exists"
            )
            assert isinstance(kw.value, ast.Constant) and kw.value.value is True
