# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import ast
import re

_DELIMITER = re.compile(r"[,;]")


def parse_subjects_field(raw: str | None) -> list[str]:
    if not raw:
        return []
    text = raw.strip()
    if not text:
        return []

    # Array-literal shape: try ``ast.literal_eval`` first. Fall through to
    # the delimiter split if the literal is malformed (mismatched quotes,
    # nested commas without quoting, etc.) -- callers always get *something*.
    if text.startswith("[") and text.endswith("]"):
        try:
            parsed = ast.literal_eval(text)
        except (ValueError, SyntaxError):
            parsed = None
        if isinstance(parsed, (list, tuple)):
            return [str(s).strip() for s in parsed if str(s).strip()]

    return [s.strip() for s in _DELIMITER.split(text) if s.strip()]
