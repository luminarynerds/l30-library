# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
from dataclasses import dataclass, field

# Fields we know how to scope. Anything else stays in the residue as a
# bare term (see test_unknown_field_falls_through_to_residue).
SUPPORTED_FIELDS: frozenset[str] = frozenset(
    {"title", "author", "subject", "series", "isbn"}
)

# Order matters: the quoted variant must run first so we don't greedily
# eat ``author:"bell hooks"`` as ``author:"bell`` + stray ``hooks"``.
_QUOTED_FIELD_RE = re.compile(r'(\w+):"([^"]+)"')
_BARE_FIELD_RE = re.compile(r'(\w+):(\S+)')


@dataclass
class ParsedQuery:

    residue: str = ""
    scoped: dict[str, list[str]] = field(default_factory=dict)
    isbn: str | None = None

    @property
    def is_empty(self) -> bool:
        return not self.residue.strip() and not self.scoped and not self.isbn


def _looks_like_isbn(token: str) -> bool:
    digits = re.sub(r"[- ]", "", token)
    if len(digits) == 10 and re.fullmatch(r"\d{9}[\dX]", digits, re.IGNORECASE):
        return True
    if len(digits) == 13 and digits.isdigit():
        return True
    return False


def parse(q: str | None) -> ParsedQuery:
    if not q:
        return ParsedQuery()
    q = q.strip()
    if not q:
        return ParsedQuery()

    # Short-circuit: a bare ISBN goes straight to the isbn bucket. We
    # check the whole-input case before touching the field-token pass so
    # ``978-0-446-31078-9`` doesn't get treated as a series of bare tokens.
    if _looks_like_isbn(q):
        return ParsedQuery(isbn=re.sub(r"[- ]", "", q))

    scoped: dict[str, list[str]] = {}
    isbn: str | None = None

    def _consume(match: re.Match[str]) -> str:
        # Both regexes are (field, value); the quoted variant strips its
        # surrounding quotes thanks to the capture group.
        nonlocal isbn
        f_name = match.group(1).lower()
        f_value = match.group(2)
        if f_name not in SUPPORTED_FIELDS:
            # Leave unknown ``foo:bar`` alone; degrade to a bare term.
            return match.group(0)
        if f_name == "isbn":
            # An explicit ``isbn:`` always wins, even over a bare ISBN
            # later in the input.
            isbn = re.sub(r"[- ]", "", f_value)
            return ""
        scoped.setdefault(f_name, []).append(f_value)
        return ""

    residue = _QUOTED_FIELD_RE.sub(_consume, q)
    residue = _BARE_FIELD_RE.sub(_consume, residue)

    # Collapse any whitespace we introduced from substitution.
    residue = re.sub(r"\s+", " ", residue).strip()

    # Final bare-ISBN check on the residue alone: e.g. patron typed
    # ``9780446310789 author:hooks`` -- the digits should still route
    # to the ISBN short-circuit, but we keep scoped predicates too.
    if residue and _looks_like_isbn(residue) and isbn is None:
        isbn = re.sub(r"[- ]", "", residue)
        residue = ""

    return ParsedQuery(residue=residue, scoped=scoped, isbn=isbn)
