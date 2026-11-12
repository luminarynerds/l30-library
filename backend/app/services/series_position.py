# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Derive a numeric reading-order position from a freeform series enumeration.

``CatalogItem.series_number`` is a freeform string sourced from MARC 490 $v /
800 $v (RDA series enumeration), so it carries values like ``"Book 4"``,
``"Vol. 3"``, ``"#2"``, ``"Issue 28"``, or a bare ``"1"``. There is no
guarantee it is numeric, and many records have no enumeration at all.

This module extracts a single integer position for the common cases so the
catalog item page can show reading-order context ("Book 4 in The Expanse")
with prev/next links. It is deliberately conservative: when the string does
not contain exactly one unambiguous integer, it returns ``None`` and the UI
falls back to the plain "Part of [series]" treatment. We never fabricate a
position.
"""

import re

# One run of digits, optionally with a leading sign-less decimal we ignore.
# We pull the FIRST standalone integer in the string. This handles:
#   "1", "Book 4", "Vol. 3", "#2", "Issue 28", "no. 7", "v.12"
# and rejects strings with no digits ("Omnibus", "Suppl.", "Index").
_INT_RE = re.compile(r"\d+")

# Decimal "in-between" numbers (e.g. "2.5" for a novella) and ranges
# ("1-3" for an omnibus) are intentionally NOT collapsed to one position;
# they are ambiguous as a single reading-order slot, so we return None.
_DECIMAL_RE = re.compile(r"\d+\.\d+")
_RANGE_RE = re.compile(r"\d+\s*[-–—]\s*\d+")

_MAX_POSITION = 100_000


def parse_series_position(series_number: str | None) -> int | None:
    """Return the reading-order integer for ``series_number``, or ``None``.

    None when the value is empty, has no digits, or is ambiguous (a decimal
    like "2.5" or a range like "1-3"). The returned int is the first integer
    run in the string.
    """
    if not series_number:
        return None
    s = series_number.strip()
    if not s:
        return None

    # Ambiguous shapes: a single slot can't honestly represent these.
    if _DECIMAL_RE.search(s) or _RANGE_RE.search(s):
        return None

    m = _INT_RE.search(s)
    if not m:
        return None

    value = int(m.group(0))
    # Guard against absurd values from junk data (e.g. a stray barcode).
    if value < 0 or value > _MAX_POSITION:
        return None
    return value
