# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

# Requires explicit trailing L; bare digits-only strings are rejected.
_LEXILE_RE = re.compile(r"^(AD|HL|BR|NC|IG)?(\d{1,4})L$", re.IGNORECASE)
_NUMERIC_MIN = -400
_NUMERIC_MAX = 2000


def parse_lexile(raw: str | None) -> tuple[str | None, int | None]:
    if raw is None:
        return (None, None)
    s = raw.strip().upper()
    if not s:
        return (None, None)

    if s == "NP":
        return ("NP", None)
    if s == "BR":
        return ("BR", 0)

    m = _LEXILE_RE.fullmatch(s)
    if not m:
        raise ValueError(f"Invalid Lexile value: {raw!r}")

    prefix = m.group(1) or ""
    digits = m.group(2)
    numeric = int(digits)

    if prefix == "BR":
        if numeric == 0 or numeric > 400:
            raise ValueError(f"BR Lexile must be 1-400: {raw!r}")
        numeric = -numeric

    if numeric < _NUMERIC_MIN or numeric > _NUMERIC_MAX:
        raise ValueError(f"Lexile out of range: {raw!r}")

    canonical = f"{prefix}{digits}L"
    return (canonical, numeric)
