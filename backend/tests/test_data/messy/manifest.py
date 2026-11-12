# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Manifest model for the messy-data import harness (pure, no DB access).

A manifest is the oracle for one dirty fixture file: it records, per source
data row, what defect was seeded and what outcome we expect from the pipeline.
"""

import json
from dataclasses import dataclass, field
from typing import Optional

# Allowed expected outcomes for a row at the end of the pipeline.
VALID_OUTCOMES = {"valid", "warning", "error", "duplicate", "orphan_fk"}


@dataclass
class RowSpec:
    row: int                     # 1-based index over DATA rows (excludes header)
    defect_class: str            # e.g. "encoding_smart_quotes", "ambiguous_date"
    expected_outcome: str        # one of VALID_OUTCOMES
    note: Optional[str] = None   # human description, surfaced in the report


@dataclass
class Manifest:
    job_type: str
    rows: list[RowSpec] = field(default_factory=list)

    def expected_for(self, row_number: int) -> Optional[str]:
        for r in self.rows:
            if r.row == row_number:
                return r.expected_outcome
        return None

    def spec_for(self, row_number: int) -> Optional[RowSpec]:
        for r in self.rows:
            if r.row == row_number:
                return r
        return None


def load_manifest(path: str) -> Manifest:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    rows = []
    for entry in raw["rows"]:
        assert entry["expected_outcome"] in VALID_OUTCOMES, (
            f"bad expected_outcome {entry["expected_outcome"]!r} in {path}"
        )
        rows.append(RowSpec(
            row=entry["row"],
            defect_class=entry["defect_class"],
            expected_outcome=entry["expected_outcome"],
            note=entry.get("note"),
        ))
    return Manifest(job_type=raw["job_type"], rows=rows)
