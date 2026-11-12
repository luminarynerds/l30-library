# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Drift check: verify lazy-imported router modules resolve and expose every
router attribute the registry actually references (not just `.router`)."""

import importlib
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

backend_dir = str(Path(__file__).parent.parent.parent)
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from drift_checks.suppressions import Rule, is_suppressed

_LAZY_PATTERN = re.compile(
    r"(?P<local>[A-Za-z_][A-Za-z0-9_]*)\s*=\s*_lazy_import\(['\"](?P<module>[^'\"]+)['\"]\)"
)
_INCLUDE_ROUTER_PATTERN = re.compile(
    r"include_router\(\s*(?P<local>[A-Za-z_][A-Za-z0-9_]*)\.(?P<attr>[A-Za-z_][A-Za-z0-9_]*)"
)

REGISTRY_PATH = Path(__file__).parent.parent.parent / "app" / "api" / "v1" / "registry.py"


def parse_registry(content: str) -> Dict[str, Set[str]]:
    """Map module path -> set of attribute names referenced by include_router calls.

    Falls back to {"router"} for modules that are lazy-imported but never seen in
    an `include_router(local.attr, ...)` call (defensive — should be rare).
    """
    local_to_module: Dict[str, str] = {
        m.group("local"): m.group("module") for m in _LAZY_PATTERN.finditer(content)
    }
    expected: Dict[str, Set[str]] = {mod: set() for mod in local_to_module.values()}
    for m in _INCLUDE_ROUTER_PATTERN.finditer(content):
        module = local_to_module.get(m.group("local"))
        if module is not None:
            expected[module].add(m.group("attr"))
    for module, attrs in expected.items():
        if not attrs:
            attrs.add("router")
    return expected


async def check_import_health(rules: List[Rule]) -> list:
    """Verify every lazy-imported router module resolves and exposes the
    attribute(s) the registry references."""
    findings = []

    registry_path = REGISTRY_PATH
    if not registry_path.exists():
        findings.append({
            "level": "error",
            "msg": f"Registry file not found: {registry_path}",
        })
        return findings

    content = registry_path.read_text()
    expected_attrs = parse_registry(content)

    if not expected_attrs:
        findings.append({
            "level": "warning",
            "msg": "No lazy imports found in registry.py",
        })
        return findings

    for module_path in sorted(expected_attrs):
        if is_suppressed(rules, "import_health", "ignore_module", module_path):
            continue

        try:
            mod = importlib.import_module(module_path)
        except (ModuleNotFoundError, ImportError) as exc:
            findings.append({
                "level": "error",
                "msg": f"Cannot import '{module_path}': {exc}",
            })
            continue

        for attr in sorted(expected_attrs[module_path]):
            if not hasattr(mod, attr):
                findings.append({
                    "level": "error",
                    "msg": f"Module '{module_path}' has no .{attr} attribute "
                           f"(referenced by include_router in registry.py)",
                })

    return findings
