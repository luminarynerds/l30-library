# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the FTS stopword detection helper.

The catalog search layer falls through to an unfiltered browse when a
query consists entirely of English stopwords (e.g. ?q=the, ?q=of+the).
This file pins the helper's behavior so future changes don't silently
break the empty-state UX.
"""
import pytest

from app.api.v1.catalog.helpers import _FTS_STOPWORDS, _is_all_stopwords


@pytest.mark.parametrize(
    "query, expected",
    [
        # Single stopword -- the original reported bug (?q=the)
        ("the", True),
        ("a", True),
        ("of", True),
        # Case insensitivity
        ("THE", True),
        ("And", True),
        # Multiple stopwords -- still all-stopwords
        ("the of", True),
        ("the the of", True),
        ("And or", True),
        # Mixed: at least one content word -> NOT all-stopwords
        ("the giver", False),
        ("of mice and men", False),  # "mice", "men" are content words
        ("giver", False),
        # No query / empty -- not all-stopwords (existing browse path)
        ("", False),
        ("   ", False),
        # Operator/punct only -- not all-stopwords (degenerate query)
        ("*", False),
        ("()!&", False),
        # Content words only
        ("xyzzyflurb", False),
        ("python", False),
    ],
)
def test_is_all_stopwords(query, expected):
    assert _is_all_stopwords(query) is expected


def test_stopword_set_covers_reported_patron_cases():
    """Smoke-test that the patron-facing examples are caught.

    These are the exact words pulled from live walkthroughs at l30.org/catalog
    where patrons typed a common word and saw "0 items found".
    """
    for word in ("the", "of", "and", "a", "an", "is", "to", "for"):
        assert word in _FTS_STOPWORDS, f"missing patron-facing stopword: {word}"
