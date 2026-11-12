# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import time

import pytest

from app.core.security import hash_password
from app.models.user import User, UserRole


async def _create_staff_user(db):
    staff = User(
        email="search.staff@test.com",
        password_hash=hash_password("StaffPassword123!"),
        first_name="Search",
        last_name="Staff",
        role=UserRole.STAFF,
        is_active=True,
        email_verified=True,
    )
    db.add(staff)
    await db.commit()
    await db.refresh(staff)
    return staff


async def _auth_headers(client, email: str, password: str):
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _seed_patron(db, **kwargs):
    patron = User(
        password_hash=hash_password("PatronPassword123!"),
        role=UserRole.PATRON,
        is_active=kwargs.pop("is_active", True),
        email_verified=True,
        **kwargs,
    )
    db.add(patron)
    await db.commit()
    await db.refresh(patron)
    return patron


@pytest.mark.asyncio
async def test_patron_search_matrix(client, db):
    staff = await _create_staff_user(db)
    headers = await _auth_headers(client, staff.email, "StaffPassword123!")

    alpha = await _seed_patron(
        db,
        email="alex.smith@example.com",
        first_name="Alex",
        last_name="Smith",
        library_card="CARD-1001",
        phone="(555) 123-4567",
        address="123 Main Street",
        city="Lakeside",
    )
    await _seed_patron(
        db,
        email="sam.smyth@example.com",
        first_name="Sam",
        last_name="Smyth",
        library_card="CARD-1002",
        phone="5559876543",
        address="321 Oak Avenue",
        city="Hillview",
    )
    await _seed_patron(
        db,
        email="common.one@example.com",
        first_name="Chris",
        last_name="Common",
        library_card="CARD-2001",
        address="44 Shared Rd",
    )
    await _seed_patron(
        db,
        email="common.two@example.com",
        first_name="Chris",
        last_name="Campbell",
        library_card="CARD-2002",
        address="45 Shared Rd",
    )
    special = await _seed_patron(
        db,
        email="ana.o@example.com",
        first_name="Ana María",
        last_name="O'Connor",
        library_card="CARD-3001",
        address="88 Elm St",
    )
    hyphen = await _seed_patron(
        db,
        email="jordan.lee@example.com",
        first_name="Jordan",
        last_name="Lee-Santos",
        library_card="CARD-3002",
        address="89 Elm St",
    )

    scenarios = [
        ("exact name", "Alex Smith", alpha.id),
        # Name search is now exact-first/exact-last/last-name-PREFIX via blind
        # index (encryption-at-rest dropped substring-anywhere). A last-name
        # prefix matches; a first-name partial like "Ale" no longer does.
        ("last-name prefix", "Smi", alpha.id),
        ("phone", "5551234567", alpha.id),
        ("email", "alex.smith@example.com", alpha.id),
        ("card", "CARD-1001", alpha.id),
        # No "address" scenario, and that is CORRECT -- not a gap.
        #
        # A 2026-07-13 triage pass called this a product bug, reasoning that
        # _address (models/user.py:140) is "a plain unencrypted Text column".
        # It is not. user.py:141 binds address = EncryptedPIIField(_address),
        # so the column stores ciphertext, exactly like name/email/phone. ILIKE
        # cannot match a substring inside ciphertext, which is precisely why
        # _build_patron_search_filter excludes it, and why searchable plaintext
        # proxies exist instead: phone_last4, city, state, zip_code, plus the
        # name blind index and the email hash.
        #
        # Adding User.address to the ILIKE list would silently match nothing.
        # Street-level search would need its own blind index -- that is a
        # feature, not a fix. Do not "restore" this scenario.
        ("fuzzy misspelling", "Smth", alpha.id),
        ("special characters", "O'Connor", special.id),
        ("hyphenated", "Lee-Santos", hyphen.id),
    ]

    for label, query, expected_id in scenarios:
        resp = await client.get(
            "/api/v1/staff/patrons",
            params={"search": query, "limit": 25},
            headers=headers,
        )
        assert resp.status_code == 200, label
        patron_ids = {p["id"] for p in resp.json()["patrons"]}
        assert expected_id in patron_ids, f"{label} should include expected patron"

    common_resp = await client.get(
        "/api/v1/staff/patrons",
        params={"search": "Chris", "limit": 25},
        headers=headers,
    )
    assert common_resp.status_code == 200
    assert common_resp.json()["total_count"] >= 2

    empty_resp = await client.get(
        "/api/v1/staff/patrons",
        params={"search": "NoSuchPatron-999999"},
        headers=headers,
    )
    assert empty_resp.status_code == 200
    assert empty_resp.json()["total_count"] == 0


@pytest.mark.asyncio
async def test_patron_search_sorting_and_combined_filters(client, db):
    staff = await _create_staff_user(db)
    headers = await _auth_headers(client, staff.email, "StaffPassword123!")

    await _seed_patron(
        db,
        email="sort.zed@example.com",
        first_name="Zed",
        last_name="Last",
        library_card="SORT-1",
        is_active=True,
    )
    await _seed_patron(
        db,
        email="sort.anna@example.com",
        first_name="Anna",
        last_name="First",
        library_card="SORT-2",
        is_active=True,
    )
    await _seed_patron(
        db,
        email="sort.inactive@example.com",
        first_name="Inactive",
        last_name="First",
        library_card="SORT-3",
        is_active=False,
    )

    sort_resp = await client.get(
        "/api/v1/staff/patrons",
        params={"sort_by": "name", "sort_direction": "asc", "limit": 10},
        headers=headers,
    )
    assert sort_resp.status_code == 200
    names = [(p["last_name"], p["first_name"]) for p in sort_resp.json()["patrons"][:2]]
    assert names == sorted(names)

    combined_resp = await client.get(
        "/api/v1/staff/patrons",
        params={
            "search": "First",
            "is_active": "true",
            "sort_by": "name",
            "sort_direction": "asc",
            "limit": 10,
        },
        headers=headers,
    )
    assert combined_resp.status_code == 200
    patrons = combined_resp.json()["patrons"]
    assert patrons
    assert all(p["is_active"] for p in patrons)
    assert all("First" in p["last_name"] for p in patrons)


@pytest.mark.asyncio
async def test_patron_search_returns_in_under_three_seconds(client, db):
    staff = await _create_staff_user(db)
    headers = await _auth_headers(client, staff.email, "StaffPassword123!")

    # Bulk-insert with one commit, not 700 sequential round-trips (each with
    # its own commit + blind-index hash computation via _seed_patron) --
    # that setup alone blew past the 120s pytest-timeout before the timed
    # search request under test ever ran.
    #
    # Hash the password ONCE and reuse it across all 700 rows. bcrypt is
    # deliberately slow (~250ms/hash), so calling it per-row cost ~175s and
    # blew the timeout on its own. Nothing here authenticates as a patron --
    # only `staff` logs in -- so 700 identical (real) hashes are equivalent
    # for this test, which measures search latency, not hashing.
    patron_password_hash = hash_password("PatronPassword123!")
    patrons = [
        User(
            email=f"perf{i}@example.com",
            password_hash=patron_password_hash,
            first_name=f"Patron{i}",
            last_name="Performance",
            library_card=f"PERF-{10000 + i}",
            address=f"{i} Benchmark Lane",
            role=UserRole.PATRON,
            is_active=True,
            email_verified=True,
        )
        for i in range(700)
    ]
    db.add_all(patrons)
    await db.commit()

    start = time.perf_counter()
    resp = await client.get(
        "/api/v1/staff/patrons",
        params={"search": "Patron699", "limit": 10},
        headers=headers,
    )
    elapsed = time.perf_counter() - start

    assert resp.status_code == 200
    assert elapsed < 3.0, f"Search took {elapsed:.3f}s"
