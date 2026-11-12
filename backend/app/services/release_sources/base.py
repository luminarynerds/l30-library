# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
from datetime import date, datetime

_ISBN13_RE = re.compile(r"(97[89]\d{10})")


def clean_isbn13(raw: str | None) -> str | None:
    """Return a bare 13-digit ISBN/EAN (978/979) or None."""
    if not raw:
        return None
    digits = re.sub(r"[^0-9]", "", str(raw))
    match = _ISBN13_RE.search(digits)
    return match.group(1) if match else None


def parse_us_date(raw: str | None) -> date | None:
    """Parse a US M/D/YYYY date string; return None on empty/unparseable."""
    if not raw:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return datetime.strptime(text, "%m/%d/%Y").date()
    except ValueError:
        return None


def normalize_author_name(raw: str | None) -> str | None:
    """Convert a "Last, First" name to "First Last"; pass through names without a comma. None/empty -> None."""
    if not raw:
        return None
    text = raw.strip()
    if not text:
        return None
    if "," in text:
        last, rest = text.split(",", 1)
        first = rest.strip()
        last = last.strip()
        return f"{first} {last}".strip() if first else last
    return text
