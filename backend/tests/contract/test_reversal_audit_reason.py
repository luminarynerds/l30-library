# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression guard: destructive-reversal audit trail must record the
staff-supplied reason, not a hardcoded literal.

Four error-recovery operations (undo_checkout, reverse_return,
undo_fine_waiver, restore_deactivated_patron) accepted a `reason` on
the request, returned an audit_log_id, but the reversal *strategy*
layer hardcoded a canned string into AuditLog.details["reason"] and
took no `reason` parameter -- so the staffer's justification could
never reach the audit trail. Working siblings in the same files
(revert_item_status_change, reverse_fine_payment, unblock_patron)
already thread `reason` correctly; this asserts the four laggards now
match that proven pattern.

Pure AST (no import, no DB) -- immune to the conftest/asyncio traps.
"""
from __future__ import annotations

import ast
from pathlib import Path

_REVERSAL_DIR = Path(__file__).resolve().parents[2] / "app" / "services" / "reversal"

# Methods that MUST thread a `reason` param into AuditLog.details["reason"].
_MUST_THREAD: dict[str, list[str]] = {
    "circulation_strategy.py": ["undo_checkout", "reverse_return"],
    "fine_strategy.py": ["undo_fine_waiver"],
    "patron_strategy.py": ["restore_deactivated_patron"],
}
# Working siblings -- positive control: the parser must already see these as
# correct, or the parser itself is wrong.
_POSITIVE_CONTROLS: dict[str, list[str]] = {
    "circulation_strategy.py": ["revert_item_status_change"],
    "fine_strategy.py": ["reverse_fine_payment"],
    "patron_strategy.py": ["unblock_patron"],
}


def _method(tree: ast.AST, name: str) -> ast.AsyncFunctionDef | ast.FunctionDef:
    for n in ast.walk(tree):
        if isinstance(n, (ast.AsyncFunctionDef, ast.FunctionDef)) and n.name == name:
            return n
    raise AssertionError(f"method {name!r} not found (refactor? update this guard)")


def _reason_audit_violations(
    fn: ast.AsyncFunctionDef | ast.FunctionDef,
) -> list[str]:
    """Return human-readable problems for one method, [] if it correctly
    threads `reason` into AuditLog.details["reason"]."""
    problems: list[str] = []

    params = {
        a.arg
        for a in (fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs)
    }
    if "reason" not in params:
        problems.append("no `reason` parameter")

    seen_reason_key = False
    for call in ast.walk(fn):
        if not (isinstance(call, ast.Call)):
            continue
        fname = (
            call.func.id if isinstance(call.func, ast.Name)
            else call.func.attr if isinstance(call.func, ast.Attribute)
            else None
        )
        if fname != "AuditLog":
            continue
        for kw in call.keywords:
            if kw.arg != "details" or not isinstance(kw.value, ast.Dict):
                continue
            for k, v in zip(kw.value.keys, kw.value.values):
                if isinstance(k, ast.Constant) and k.value == "reason":
                    seen_reason_key = True
                    if isinstance(v, ast.Constant):
                        problems.append(
                            f'AuditLog.details["reason"] is the hardcoded '
                            f'literal {v.value!r}, not the `reason` param'
                        )
                    elif not (isinstance(v, ast.Name) and v.id == "reason"):
                        problems.append(
                            'AuditLog.details["reason"] is not wired to the '
                            f"`reason` param (got {ast.dump(v)[:60]})"
                        )
    if not seen_reason_key:
        problems.append(
            'no AuditLog(..., details={..., "reason": ...}) found '
            "(structure changed -- update this guard)"
        )
    return problems


def test_reversal_strategies_record_supplied_reason() -> None:
    """The four destructive-reversal strategies thread the staff `reason`
    into the audit log, exactly as their working siblings already do."""
    failures: list[str] = []

    for fname, methods in _MUST_THREAD.items():
        tree = ast.parse((_REVERSAL_DIR / fname).read_text(), filename=fname)
        for m in methods:
            for p in _reason_audit_violations(_method(tree, m)):
                failures.append(f"{fname}::{m}: {p}")

    # Positive control: the proven-good siblings must pass the same check;
    # if they don't, the parser is broken, not the code.
    control_failures: list[str] = []
    for fname, methods in _POSITIVE_CONTROLS.items():
        tree = ast.parse((_REVERSAL_DIR / fname).read_text(), filename=fname)
        for m in methods:
            for p in _reason_audit_violations(_method(tree, m)):
                control_failures.append(f"{fname}::{m}: {p}")

    assert not control_failures, (
        "POSITIVE CONTROL FAILED -- the parser is wrong, not the code:\n  "
        + "\n  ".join(control_failures)
    )
    assert not failures, (
        "Destructive-reversal audit trail drops the staff-supplied reason "
        "(silent-drop class). Thread `reason` through to "
        'AuditLog.details["reason"] like the working siblings:\n  '
        + "\n  ".join(failures)
    )


if __name__ == "__main__":
    try:
        test_reversal_strategies_record_supplied_reason()
        print("PASS: all four reversal strategies thread `reason` to the audit log")
    except AssertionError as e:
        print("FAIL:\n" + str(e))
