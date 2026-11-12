"""
SPDX-FileCopyrightText: 2026 Luminary Nerds
SPDX-License-Identifier: AGPL-3.0-or-later

Regression test for the admin book-club list response shape.

The admin endpoint GET /api/v1/book-clubs/ previously serialized its list
under the key `book_clubs`, while the frontend (both staff admin page and
the patron client) read `clubs`. The mismatch silently presented as an
empty admin list. We now normalize the admin schema to `clubs` so the
two surfaces share one contract.
"""
from app.schemas.book_club import BookClubListResponse


def test_book_club_list_response_uses_clubs_key():
    fields = BookClubListResponse.model_fields
    assert "clubs" in fields, "BookClubListResponse must expose 'clubs'"
    assert "book_clubs" not in fields, (
        "Legacy 'book_clubs' key must not be reintroduced; the admin and patron "
        "frontends both read response.clubs."
    )


def test_book_club_list_response_serializes_clubs():
    resp = BookClubListResponse(total=0, clubs=[])
    dumped = resp.model_dump()
    assert dumped == {"total": 0, "clubs": []}
