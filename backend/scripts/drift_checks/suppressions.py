# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Load and query .driftignore suppressions."""

from pathlib import Path
from typing import List, Tuple

Rule = Tuple[str, str, str]  # (check_name, rule_type, value)


def load_suppressions(path: str) -> List[Rule]:
    """Parse a .driftignore file into a list of suppression rules."""
    p = Path(path)
    if not p.exists():
        return []
    rules: List[Rule] = []
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split(":", 2)
        if len(parts) == 3:
            rules.append((parts[0], parts[1], parts[2]))
    return rules


def is_suppressed(rules: List[Rule], check: str, rule_type: str, value: str) -> bool:
    """Check if a finding matches any suppression rule."""
    return (check, rule_type, value) in rules
