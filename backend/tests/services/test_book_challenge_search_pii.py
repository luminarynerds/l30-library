# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Staff challenge search after challenger_name became encrypted.

ilike against Fernet ciphertext can never match, so leaving the clause in place
would give staff a name search that silently returned nothing while looking as
though it worked. The clause is removed instead, and the capability removal is
asserted here rather than left implicit.

The API accepts a `search` param but the staff UI never sends one, so no
shipped capability is lost. A blind index can be added later if staff ask.
"""

import re

import pytest

from app.models.book_challenge import BookChallenge, ChallengeReason
from app.services.book_challenge_service import BookChallengeService

from tests.pii_encryption_fixture import pii_encryption_on  # noqa: F401

pytestmark = pytest.mark.usefixtures("pii_encryption_on")


async def _challenge(db, title, author, isbn, challenger):
    row = BookChallenge(
        title=title,
        author=author,
        isbn=isbn,
        primary_reason=ChallengeReason.OTHER,
        challenger_name=challenger,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def _search(db, term):
    rows, _total = await BookChallengeService.list_challenges(db, search=term)
    return [r.id for r in rows]


@pytest.mark.asyncio
async def test_search_still_matches_title(db_session):
    row = await _challenge(db_session, "Gender Queer", "Kobabe", "111", "Dana Reyes")
    assert row.id in await _search(db_session, "Gender Queer")


@pytest.mark.asyncio
async def test_search_still_matches_author(db_session):
    row = await _challenge(db_session, "Lawn Boy", "Evison", "222", "Dana Reyes")
    assert row.id in await _search(db_session, "Evison")


@pytest.mark.asyncio
async def test_search_still_matches_isbn(db_session):
    row = await _challenge(db_session, "Beloved", "Morrison", "9780333", "Dana Reyes")
    assert row.id in await _search(db_session, "9780333")


@pytest.mark.asyncio
async def test_searching_a_challenger_name_no_longer_matches(db_session):
    """Deliberate capability removal, asserted so it cannot regress silently."""
    row = await _challenge(db_session, "The Bluest Eye", "Morrison", "333", "Wilhelmina Fontaine")
    assert row.id not in await _search(db_session, "Wilhelmina Fontaine")


@pytest.mark.asyncio
async def test_the_search_sql_no_longer_filters_on_challenger_name(db_session):
    """Structural, because behaviour cannot tell the two states apart.

    Once challenger_name is ciphertext the ilike stops matching whether or not
    the clause is still there, so every behavioural test above passes either
    way. That is exactly the situation the clause was removed to avoid: a
    filter that looks like a working feature and silently returns nothing.
    Asserting on the emitted SQL is the only thing that catches its return.
    """
    seen: list[str] = []
    original = db_session.execute

    async def spy(statement, *args, **kwargs):
        try:
            seen.append(str(statement.compile(compile_kwargs={"literal_binds": True})))
        except Exception:  # noqa: BLE001 - non-compilable statements are not the target
            seen.append(str(statement))
        return await original(statement, *args, **kwargs)

    db_session.execute = spy  # type: ignore[method-assign]
    try:
        await BookChallengeService.list_challenges(db_session, search="anything")
    finally:
        db_session.execute = original  # type: ignore[method-assign]

    assert seen, "no SQL was captured, so this test proves nothing"
    # challenger_name still appears in the SELECT list, because the query loads
    # the whole entity. Only the WHERE clause is in question here. Split on the
    # keyword rather than " WHERE ": the compiler puts it at a line start.
    wheres = [
        re.split(r"\bWHERE\b", sql, maxsplit=1)[1] for sql in seen if re.search(r"\bWHERE\b", sql)
    ]
    assert wheres, "no WHERE clause was captured, so this test proves nothing"
    joined = "\n".join(wheres)
    assert "challenger_name" not in joined
    # Control: a clause that must survive is visibly present, so an empty or
    # malformed capture cannot masquerade as a pass.
    assert "title" in joined
