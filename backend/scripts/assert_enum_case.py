#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Startup assertion: crash if any enum has uppercase values.

Run during container startup (after init_schema, before uvicorn).
Catches enum drift that slipped past pre-commit hooks.
"""
import importlib
import inspect
import sys
from enum import Enum
from pathlib import Path

backend_dir = str(Path(__file__).parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)


def assert_enum_case():
    models_dir = Path(backend_dir) / "app" / "models"
    violations = []

    for py_file in sorted(models_dir.rglob("*.py")):
        if py_file.name.startswith("_"):
            continue
        rel = py_file.relative_to(Path(backend_dir))
        module_path = str(rel).replace("/", ".").removesuffix(".py")
        try:
            mod = importlib.import_module(module_path)
        except Exception:
            continue

        for attr_name, attr in inspect.getmembers(mod, inspect.isclass):
            if (
                issubclass(attr, Enum)
                and issubclass(attr, str)
                and attr.__module__ == mod.__name__
                and attr_name != "SIP2CommandType"
            ):
                for member in attr:
                    if member.value != member.value.lower():
                        violations.append(
                            f"  {attr.__name__}.{member.name} = \"{member.value}\" "
                            f"(should be \"{member.value.lower()}\") "
                            f"in {rel}"
                        )

    if violations:
        print("\n\u274c ENUM CASE VIOLATION \u2014 container refusing to start\n")
        print(f"Found {len(violations)} uppercase enum values:\n")
        for v in violations[:20]:
            print(v)
        if len(violations) > 20:
            print(f"  ... and {len(violations) - 20} more")
        print("\nFix: enum VALUES must be lowercase.")
        print("  BAD:  ACTIVE = \"ACTIVE\"")
        print("  GOOD: ACTIVE = \"active\"")
        print("\nSee CLAUDE.md 'Enum Rules' section.")
        sys.exit(1)

    print("\u2705 Enum case assertion passed")


if __name__ == "__main__":
    assert_enum_case()
