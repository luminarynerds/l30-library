# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Optional


# Canonical map. Keep in sync with backfill_branch_id_phase2.sql.
_BRANCH_LABEL_MAP: dict[str, int] = {
    "Main": 7,
    "Main Branch": 7,
    "Main Library": 7,
    "Main Circulation Desk": 7,
    "Elmdale": 8,
    "Elmdale Branch": 8,
    "Community Annex": 9,
    "Annex": 9,
    "Bookmobile": 10,
}


def label_to_branch_id(label: Optional[str]) -> Optional[int]:
    if not label:
        return None
    label = label.strip()
    if not label:
        return None
    if label in _BRANCH_LABEL_MAP:
        return _BRANCH_LABEL_MAP[label]
    # Compound shelving labels like 'Main - Tech', 'Main - Children'.
    if label.startswith("Main - "):
        return 7
    if label.startswith("Elmdale"):
        return 8
    if label.startswith("Community Annex") or label.startswith("Annex "):
        return 9
    return None


# Canonical labels per id (reverse lookup). Prefers the longer form
# ('Main Branch' over 'Main') so generated rows carry the full name
# returned by the branches.name column.
_BRANCH_CANONICAL_LABEL: dict[int, str] = {
    7: "Main Branch",
    8: "Elmdale Branch",
    9: "Community Annex",
    10: "Bookmobile",
}


def branch_id_to_label(branch_id: Optional[int]) -> Optional[str]:
    if branch_id is None:
        return None
    return _BRANCH_CANONICAL_LABEL.get(branch_id)

