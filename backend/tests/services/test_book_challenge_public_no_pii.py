# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""The public transparency response must never carry challenger identity.

Encryption protects these fields at rest. It does nothing if the API hands them
to an anonymous caller in plaintext, because the ORM decrypts on read: the
serializer would leak the very thing the column type protects.

The public page is deliberately built from public_title / public_summary, and
this pins that. It is a schema-level assertion rather than a response-body
comparison so it fails at the moment someone widens the model, not once a real
challenge with a real name happens to exist in the fixture data.
"""

from app.schemas.book_challenge import (
    BookChallengeDetailResponse,
    BookChallengePublicResponse,
)

_CHALLENGER_FIELDS = {
    "challenger_name",
    "challenger_contact",
    "challenger_complaint",
    "challenger_is_patron",
}


def test_public_response_exposes_no_challenger_field():
    leaked = _CHALLENGER_FIELDS & set(BookChallengePublicResponse.model_fields)
    assert leaked == set(), f"public schema exposes challenger PII: {sorted(leaked)}"


def test_public_response_still_carries_the_transparency_fields():
    """Control: an empty intersection above must mean 'no PII', not 'no fields'."""
    fields = set(BookChallengePublicResponse.model_fields)
    assert {"public_title", "public_summary", "outcome"} <= fields


def test_the_staff_detail_response_does_carry_them():
    """Second control: the field names are real and spelled correctly.

    Without this, renaming a column would empty _CHALLENGER_FIELDS of anything
    meaningful and the first test would pass by matching nothing.
    """
    fields = set(BookChallengeDetailResponse.model_fields)
    assert {"challenger_name", "challenger_contact"} <= fields
