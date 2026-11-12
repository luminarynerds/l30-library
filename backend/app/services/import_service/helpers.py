# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from difflib import SequenceMatcher
from typing import Optional

from app.models.import_job import ImportFileFormat

def _detect_file_format(filename: str) -> ImportFileFormat:
    lower = filename.lower()
    if lower.endswith(".csv"):
        return ImportFileFormat.CSV
    if lower.endswith(".mrc") or lower.endswith(".marc"):
        return ImportFileFormat.MARC21
    if lower.endswith(".xml") or lower.endswith(".marcxml"):
        return ImportFileFormat.MARCXML
    if lower.endswith(".json"):
        return ImportFileFormat.JSON
    return ImportFileFormat.CSV


def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _parse_date(value: str) -> Optional[datetime]:
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None


# ═══════════════════════════════════════════════════════════════════════════
# Import Service
# ═══════════════════════════════════════════════════════════════════════════

