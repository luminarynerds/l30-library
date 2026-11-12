# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regex PII redaction for free-text patron input.

Deliberately narrow scope: email addresses, phone numbers, and L30-issued
library card / barcode numbers. Names in free text are NOT handled (that needs
NER, which the chatbot path has no model for). NEVER describe this as removing
"all" PII.
"""

import re

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")

# NANP-style phone numbers, optional +1 and separators.
# Leading (?<![\w(]) instead of \b so an opening paren is consumed by \(? rather
# than left stranded ("(555) 123-4567" -> "[phone]", not "([phone]").
_PHONE_RE = re.compile(r"(?<![\w(])(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")

# L30-issued card formats (case-insensitive prefix): L30-XXXX-XXXX, L30-XXXXXX,
# LSC######, LSC########, TMP-XXXX-XXXX. Plus the dominant all-uppercase prod
# format: 5 alnum + hyphen + 5 digits (kept uppercase-only so ordinary lowercase
# "word-12345" text isn't mistaken for a card).
_CARD_RE = re.compile(
    r"\b(?:"
    r"(?i:L30|LSC|TMP)[- ]?[A-Za-z0-9]{4,8}(?:-[A-Za-z0-9]{4,6})*"
    r"|[A-Z0-9]{5}-\d{5}"
    r")\b"
)


def redact_pii(text: str) -> str:
    """Replace emails, phone numbers, and card numbers with placeholder tokens.

    Order: email, then card, then phone (card runs are redacted before the phone
    pass so digit groups inside a card number aren't mis-tagged).

    Bare 10-digit numbers are treated as phone numbers (acceptable
    over-redaction toward privacy).
    """
    if not text:
        return text
    text = _EMAIL_RE.sub("[email]", text)
    text = _CARD_RE.sub("[card]", text)
    text = _PHONE_RE.sub("[phone]", text)
    return text
