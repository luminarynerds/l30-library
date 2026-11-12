# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Patron first_name / last_name encryption at rest + blind-index name search.

Commit 1 of the patron-PII-at-rest series. These tests are the deliverable:
do not weaken or skip them to go green.
"""

import pytest
from sqlalchemy import select, text

from app.models.user import (
    User,
    UserRole,
    name_blind_hash,
    last_name_prefix_hashes,
    name_search_clause,
)

# These assertions are only meaningful with encryption actually on; the deploy
# gate runs the suite with PII_ENCRYPTION_ENABLED=false.
from tests.pii_encryption_fixture import pii_encryption_on  # noqa: F401

pytestmark = pytest.mark.usefixtures("pii_encryption_on")


async def _make_patron(db, first, last, email):
    user = User(
        email=email,
        first_name=first,
        last_name=last,
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.mark.asyncio
async def test_names_are_ciphertext_at_rest(db_session):
    user = await _make_patron(db_session, "Ada", "Lovelace", "ada@example.org")

    row = (
        await db_session.execute(
            text("SELECT first_name, last_name FROM users WHERE id = :id"),
            {"id": user.id},
        )
    ).one()
    raw_first, raw_last = row

    # The literal plaintext must NOT be what is stored on disk.
    assert raw_first != "Ada"
    assert raw_last != "Lovelace"
    # Fernet ciphertext is a non-trivial base64 token, much longer than the name.
    assert len(raw_first) > len("Ada")
    assert raw_first.startswith("gAAAAA")
    assert raw_last.startswith("gAAAAA")


@pytest.mark.asyncio
async def test_name_roundtrip_decrypts(db_session):
    user = await _make_patron(db_session, "Grace", "Hopper", "grace@example.org")
    db_session.expunge(user)

    reloaded = (await db_session.execute(select(User).where(User.id == user.id))).scalar_one()
    assert reloaded.first_name == "Grace"
    assert reloaded.last_name == "Hopper"
    assert reloaded.full_name == "Grace Hopper"


@pytest.mark.asyncio
async def test_name_blind_index_populated_on_insert(db_session):
    user = await _make_patron(db_session, "Ada", "Lovelace", "ada2@example.org")

    assert user.first_name_hash == name_blind_hash("ada")
    assert user.last_name_hash == name_blind_hash("lovelace")
    # Every 1..N prefix of the last name is present.
    assert name_blind_hash("lov") in user.last_name_prefix_hash
    assert name_blind_hash("lovelace") in user.last_name_prefix_hash


@pytest.mark.asyncio
async def test_exact_last_name_lookup_via_blind_index(db_session):
    # Collision-proof surnames: the shared test DB session can carry leftover
    # rows from other suites (e.g. an "Alex Smith" seed), which would perturb
    # exclusive-match assertions on common names.
    await _make_patron(db_session, "Ada", "Qixlovelace", "a@example.org")
    await _make_patron(db_session, "Charles", "Qixbabbage", "b@example.org")

    target = name_blind_hash("qixlovelace")
    rows = (
        (await db_session.execute(select(User).where(User.last_name_hash == target)))
        .scalars()
        .all()
    )
    assert len(rows) == 1
    assert rows[0].first_name == "Ada"


@pytest.mark.asyncio
async def test_last_name_prefix_lookup_via_blind_index(db_session):
    await _make_patron(db_session, "Ada", "Lovelace", "a2@example.org")
    await _make_patron(db_session, "Charles", "Babbage", "b2@example.org")

    prefix_hash = name_blind_hash("lov")
    rows = (
        (
            await db_session.execute(
                select(User).where(User.last_name_prefix_hash.op("?")(prefix_hash))
            )
        )
        .scalars()
        .all()
    )
    assert {r.last_name for r in rows} == {"Lovelace"}


@pytest.mark.asyncio
async def test_full_name_lookup_via_search_clause(db_session):
    await _make_patron(db_session, "Qalex", "Qzsmith", "alex@example.org")
    await _make_patron(db_session, "Qsam", "Qzsmyth", "sam@example.org")

    rows = (
        (await db_session.execute(select(User).where(name_search_clause("Qalex Qzsmith"))))
        .scalars()
        .all()
    )
    assert {r.email for r in rows} == {"alex@example.org"}


@pytest.mark.asyncio
async def test_last_name_prefix_via_search_clause(db_session):
    await _make_patron(db_session, "Qalex", "Qzsmith", "alex2@example.org")
    await _make_patron(db_session, "Qsam", "Qzsmyth", "sam2@example.org")

    rows = (
        (await db_session.execute(select(User).where(name_search_clause("Qzsmi")))).scalars().all()
    )
    # "Qzsmi" is a prefix of Qzsmith but not Qzsmyth.
    assert {r.email for r in rows} == {"alex2@example.org"}


@pytest.mark.asyncio
async def test_substring_anywhere_no_longer_matches(db_session):
    """Intentional behavior change: 'lace' no longer finds 'Lovelace'.
    Substring-anywhere search was dropped with encryption (maintainer decision)."""
    await _make_patron(db_session, "Ada", "Lovelace", "a3@example.org")

    prefix_hash = name_blind_hash("lace")
    rows = (
        (
            await db_session.execute(
                select(User).where(User.last_name_prefix_hash.op("?")(prefix_hash))
            )
        )
        .scalars()
        .all()
    )
    assert rows == []
