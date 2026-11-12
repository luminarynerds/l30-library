# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Schema<->persistence contract for the staff/patron endpoints.

A recurring L30 bug class: a field is declared on a request schema (and
often input-validated), the endpoint returns 200, and the field is never
read or persisted -- silently dropped. This guard parses the staff/patron
source with `ast` (no app import, no DB, no event loop -- immune to the
conftest/asyncio test traps) and flags any request-body field that is
never referenced in its handler.

It is a ratchet, not a pass/fail snapshot: KNOWN_SILENT_DROPS records the
debt that exists today. The test fails when a *new* drop appears, or when
a *known* one is fixed (so the ledger stays honest -- delete the line).

To regenerate the current finding set for the ledger:
    python tests/contract/test_schema_persistence_contract.py
"""
from __future__ import annotations

import ast
import os
from pathlib import Path

# Decorators whose presence marks a function as a route handler.
_HTTP_DECORATORS = {"get", "post", "put", "patch", "delete"}
# Accessing one of these on the body param consumes the whole object; we
# cannot prove per-field use statically, so we treat every field as used
# (deliberately false-negative rather than false-positive -- noise kills
# the test's credibility; the runtime field-count guardian covers the rest).
_BULK_ESCAPE_ATTRS = {"dict", "model_dump", "model_dump_json", "json", "copy"}

_STAFF_DIR = Path(
    os.environ.get(
        "L30_STAFF_DIR",
        Path(__file__).resolve().parents[2] / "app" / "api" / "v1" / "staff",
    )
)

# ---------------------------------------------------------------------------
# Ledger of accepted/known silent-drops. Identifier: "file::handler::Schema.field".
# REAL = confirmed defect, tracked for fix.  KNOWN = documented behaviour.
# Removing a fixed entry is required (the test enforces it).
# ---------------------------------------------------------------------------
KNOWN_SILENT_DROPS: dict[str, str] = {
    # REAL -- staff set per-patron limits; endpoint returns 200, persists
    # neither; GET hands back hardcoded 25/10. (Audit 2026-05-19)
    "patrons_account.py::update_patron_account_settings::AccountSettingsUpdate.checkout_limit":
        "REAL: limit accepted+validated, never persisted",
    "patrons_account.py::update_patron_account_settings::AccountSettingsUpdate.hold_limit":
        "REAL: limit accepted+validated, never persisted",
    # REAL -- docstring says "templated message"; template_id is ignored.
    "patron_messages.py::bulk_send_patron_message::BulkMessageRequest.template_id":
        "REAL: templated bulk-send never reads the template id",
    # REAL -- merge honours checkouts/holds/fines/reading_lists but not history.
    "patrons_account.py::merge_patron_records::MergeRequest.merge_history":
        "REAL: merge_history toggle silently ignored by the merge",
    # KNOWN -- preview is an unconditional dry-run: it counts every category
    # regardless of the per-category toggles. Low severity (no write), but the
    # preview does not reflect the scope the staffer selected.
    "patrons_account.py::preview_patron_merge::MergeRequest.merge_checkouts":
        "KNOWN: preview counts are unconditional, toggles not reflected",
    "patrons_account.py::preview_patron_merge::MergeRequest.merge_holds":
        "KNOWN: preview counts are unconditional, toggles not reflected",
    "patrons_account.py::preview_patron_merge::MergeRequest.merge_fines":
        "KNOWN: preview counts are unconditional, toggles not reflected",
    "patrons_account.py::preview_patron_merge::MergeRequest.merge_history":
        "KNOWN: preview counts are unconditional, toggles not reflected",
    "patrons_account.py::preview_patron_merge::MergeRequest.merge_reading_lists":
        "KNOWN: preview counts are unconditional, toggles not reflected",
    "patrons_account.py::preview_patron_merge::MergeRequest.merge_favorites":
        "KNOWN: preview counts are unconditional, toggles not reflected",
    # FIXED 2026-05-19 (branch fix/error-recovery-audit-reason): the four
    # destructive-reversal endpoints (undo_accidental_checkout,
    # reverse_mistaken_return, undo_fine_waiver_endpoint,
    # restore_patron_endpoint) now thread `request.reason` through to
    # AuditLog.details["reason"]; guarded by test_reversal_audit_reason.py.
    # Entries removed per the ratchet rule (delete when fixed).
    # REAL -- emergency resolution notes are accepted but not persisted.
    "medical_emergency_alerts.py::resolve_emergency::ResolveEmergencyRequest.notes":
        "REAL: emergency resolution notes never persisted",
    # KNOWN -- redundant schema fields; the handler sources the value elsewhere
    # (path param / action_type) so the body field carries no lost data.
    "medical_emergency_alerts.py::call_911_for_emergency::CallEmergencyServicesRequest.alert_id":
        "KNOWN: alert_id taken from {alert_id} path param; body field redundant",
    "error_recovery.py::confirm_destructive_action::DestructiveActionConfirmation.resource_type":
        "KNOWN: read-only pre-check; resource_type redundant with action_type",
}


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------
def _ann_name(node: ast.expr | None) -> str | None:
    """Resolve a param annotation to one class name, unwrapping Optional[X]
    and `X | None`. Returns None for list[X]/dict[...]/complex annotations
    (those are not a single request body -- skip the field check)."""
    if node is None:
        return None
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value  # forward reference "Schema"
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
        for side in (node.left, node.right):
            if isinstance(side, ast.Constant) and side.value is None:
                continue
            return _ann_name(side)
        return None
    if isinstance(node, ast.Subscript):
        base = node.value.id if isinstance(node.value, ast.Name) else None
        return _ann_name(node.slice) if base == "Optional" else None
    return None


def _collect_schemas(files: list[Path]) -> dict[str, dict]:
    """{class: {all_fields: set, bases: [...]}} for every class that
    transitively derives from BaseModel, with inherited fields folded in."""
    raw: dict[str, dict] = {}
    for f in files:
        tree = ast.parse(f.read_text(), filename=str(f))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            fields = set()
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    name = stmt.target.id
                    if name.startswith("_") or name == "model_config":
                        continue
                    ann = stmt.annotation
                    if (
                        isinstance(ann, ast.Subscript)
                        and isinstance(ann.value, ast.Name)
                        and ann.value.id == "ClassVar"
                    ):
                        continue
                    fields.add(name)
            raw[node.name] = {
                "fields": fields,
                "bases": [b.id for b in node.bases if isinstance(b, ast.Name)],
            }

    def is_schema(name: str, seen: set) -> bool:
        if name in seen or name not in raw:
            return False
        seen.add(name)
        return any(
            b == "BaseModel" or is_schema(b, seen) for b in raw[name]["bases"]
        )

    schemas = {n: i for n, i in raw.items() if is_schema(n, set())}
    for info in schemas.values():
        acc, stack = set(info["fields"]), list(info["bases"])
        while stack:
            b = stack.pop()
            if b in schemas:
                acc |= schemas[b]["fields"]
                stack.extend(schemas[b]["bases"])
        info["all_fields"] = acc
    return schemas


def _arg_defaults(fn: ast.FunctionDef | ast.AsyncFunctionDef) -> dict[str, ast.expr]:
    """Map arg name -> its default expr (positional tail + keyword-only)."""
    out: dict[str, ast.expr] = {}
    pos = fn.args.posonlyargs + fn.args.args
    for a, d in zip(pos[len(pos) - len(fn.args.defaults):], fn.args.defaults):
        out[a.arg] = d
    for a, d in zip(fn.args.kwonlyargs, fn.args.kw_defaults):
        if d is not None:
            out[a.arg] = d
    return out


def _parent_map(tree: ast.AST) -> dict[int, ast.AST]:
    pm: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            pm[id(child)] = parent
    return pm


def find_silent_drops(staff_dir: Path) -> dict[str, str]:
    """Return {identifier: field} for every request-body field never
    referenced in its handler. identifier = file::handler::Schema.field."""
    # Skip dot-prefixed files (e.g. macOS AppleDouble "._x.py" companions,
    # which are binary metadata, not source).
    files = sorted(
        f for f in staff_dir.glob("*.py") if not f.name.startswith(".")
    )
    schemas = _collect_schemas(files)
    found: dict[str, str] = {}

    for f in files:
        tree = ast.parse(f.read_text(), filename=str(f))
        pm = _parent_map(tree)
        for fn in ast.walk(tree):
            if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if not any(
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and d.func.attr in _HTTP_DECORATORS
                for d in fn.decorator_list
            ):
                continue
            defaults = _arg_defaults(fn)
            for arg in fn.args.posonlyargs + fn.args.args + fn.args.kwonlyargs:
                cls = _ann_name(arg.annotation)
                if cls is None or cls not in schemas:
                    continue
                dflt = defaults.get(arg.arg)
                if (
                    isinstance(dflt, ast.Call)
                    and isinstance(dflt.func, ast.Name)
                    and dflt.func.id == "Depends"
                ):
                    continue  # dependency-injected, not a request body

                pname, used, escaped = arg.arg, set(), False
                for n in ast.walk(fn):
                    if not (isinstance(n, ast.Name) and n.id == pname):
                        continue
                    par = pm.get(id(n))
                    if isinstance(par, ast.Attribute) and par.value is n:
                        if par.attr in _BULK_ESCAPE_ATTRS:
                            escaped = True
                        else:
                            used.add(par.attr)
                    elif isinstance(par, ast.keyword) and par.arg is None:
                        escaped = True  # **param
                    else:
                        escaped = True  # whole-object use
                if escaped:
                    continue
                for fld in sorted(schemas[cls]["all_fields"] - used):
                    found[f"{f.name}::{fn.name}::{cls}.{fld}"] = fld
    return found


# ---------------------------------------------------------------------------
# The contract
# ---------------------------------------------------------------------------
def test_no_unaccounted_silent_drops() -> None:
    """Every accepted request-body field is read by its handler, OR is
    listed in KNOWN_SILENT_DROPS with a reason."""
    current = set(find_silent_drops(_STAFF_DIR))
    ledger = set(KNOWN_SILENT_DROPS)

    new = sorted(current - ledger)
    fixed = sorted(ledger - current)

    msg = []
    if new:
        msg.append(
            "NEW silent-drop(s): a request field is accepted but never "
            "referenced in its handler. Wire it up, or -- if intentional -- "
            "add it to KNOWN_SILENT_DROPS with a reason:\n  "
            + "\n  ".join(new)
        )
    if fixed:
        msg.append(
            "FIXED silent-drop(s) still in the ledger. Delete these lines "
            "from KNOWN_SILENT_DROPS so it stays honest:\n  "
            + "\n  ".join(fixed)
        )
    assert not msg, "\n\n".join(msg)


if __name__ == "__main__":
    drops = find_silent_drops(_STAFF_DIR)
    print(f"staff dir: {_STAFF_DIR}")
    print(f"request-body fields silently dropped: {len(drops)}\n")
    for ident in sorted(drops):
        flag = KNOWN_SILENT_DROPS.get(ident, "*** UNLEDGERED ***")
        print(f"  {ident}\n      {flag}")
