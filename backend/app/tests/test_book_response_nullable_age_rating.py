"""
SPDX-FileCopyrightText: 2026 Luminary Nerds
SPDX-License-Identifier: AGPL-3.0-or-later

Regression test for the librarian releases list 500.

backend/app/api/v1/releases.py:449 (and :372) calls
BookResponse.model_validate(book). BookResponse inherited age_rating
from BookBase as a non-nullable str, but tracker_books.age_rating is
nullable in the DB. Any row with age_rating=NULL raised pydantic
ValidationError and 500'd the entire list endpoint.

The default frontend filter (status=upcoming) hits an empty bucket on
prod, so the bug was masked; filtering to released or announced was
broken for any librarian who clicked through.

Fix overrides age_rating on BookResponse to str | None so the
serializer accepts null while keeping BookCreate strict.
"""
from datetime import datetime
from uuid import uuid4

from app.schemas.release_tracker import BookCreate, BookResponse


def test_book_response_accepts_null_age_rating():
    """BookResponse must serialize rows with age_rating=None without 500ing."""
    payload = {
        "id": uuid4(),
        "author_id": uuid4(),
        "title": "Untagged Title",
        "status": "released",
        "age_rating": None,
        "is_date_exact": True,
        "raw_categories": [],
        "created_at": datetime.utcnow(),
    }
    response = BookResponse.model_validate(payload)
    assert response.age_rating is None

    dumped = response.model_dump()
    assert dumped["age_rating"] is None


def test_book_response_field_is_optional():
    """Schema-level guard: confirm age_rating accepts None type."""
    field = BookResponse.model_fields["age_rating"]
    annotation = field.annotation
    # Either Optional[str] or str | None — both stringify to include NoneType.
    assert annotation is not None
    assert "None" in str(annotation), (
        f"BookResponse.age_rating must be Optional/Nullable; got {annotation!r}. "
        "tracker_books.age_rating is nullable in the DB and list endpoints 500 "
        "when this is required."
    )


def test_book_create_remains_strict():
    """BookCreate must keep its default age_rating='adult'; we only relaxed BookResponse."""
    payload = {
        "author_id": uuid4(),
        "title": "New Tracked Book",
        "is_date_exact": True,
        "raw_categories": [],
    }
    create = BookCreate.model_validate(payload)
    # Default still applies on input
    assert create.age_rating == "adult"
