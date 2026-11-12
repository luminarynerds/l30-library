# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for admin data-export bundle — Task 1 scaffold.

Covers:
- require_director_or_super_admin: raises 403 for UserRole.ADMIN
- require_director_or_super_admin: returns user for UserRole.DIRECTOR
- require_director_or_super_admin: returns user for UserRole.SUPER_ADMIN
"""

import pytest

from app.api.v1.dependencies import require_director_or_super_admin
from app.models.user import User, UserRole


def _make_user(role: UserRole) -> User:
    """Construct a transient User with the given role (no DB session needed)."""
    return User(
        email=f"{role.value}@example.com",
        first_name="Test",
        last_name="User",
        role=role,
    )


@pytest.mark.asyncio
async def test_require_director_or_super_admin_blocks_admin():
    from fastapi import HTTPException

    user = _make_user(UserRole.ADMIN)
    with pytest.raises(HTTPException) as exc_info:
        await require_director_or_super_admin(current_user=user)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_require_director_or_super_admin_allows_director():
    user = _make_user(UserRole.DIRECTOR)
    result = await require_director_or_super_admin(current_user=user)
    assert result is user


@pytest.mark.asyncio
async def test_require_director_or_super_admin_allows_super_admin():
    user = _make_user(UserRole.SUPER_ADMIN)
    result = await require_director_or_super_admin(current_user=user)
    assert result is user


# ============================================================================
# Task 2 — serialization + content-hash + encrypted-zip helpers
# ============================================================================

import pyzipper

from app.api.v1.admin_data_export import (
    _build_encrypted_zip,
    _canonical_sha256,
)


def test_canonical_sha256_stable_across_insertion_order():
    """Same files in different insertion order produce the same hash."""
    files_a = {
        "library_system.json": b'{"a": 1}',
        "regions.json": b"[]",
        "users.json": b'[{"id": 1}]',
    }
    # Build an equivalent dict with a different insertion order.
    files_b = {
        "users.json": b'[{"id": 1}]',
        "library_system.json": b'{"a": 1}',
        "regions.json": b"[]",
    }
    assert _canonical_sha256(files_a) == _canonical_sha256(files_b)


def test_canonical_sha256_returns_64_hex_chars():
    digest = _canonical_sha256({"library_system.json": b'{"a": 1}'})
    assert len(digest) == 64
    assert all(c in "0123456789abcdef" for c in digest)


def test_canonical_sha256_changes_with_content():
    a = _canonical_sha256({"users.json": b'[{"id": 1}]'})
    b = _canonical_sha256({"users.json": b'[{"id": 2}]'})
    assert a != b


def test_build_encrypted_zip_namelist_matches_input():
    files = {
        "library_system.json": b'{"a": 1}',
        "users.json": b'[{"id": 1}]',
    }
    buf = _build_encrypted_zip(files, "correct-horse-battery")
    with pyzipper.AESZipFile(buf, "r") as zf:
        assert set(zf.namelist()) == set(files.keys())


def test_build_encrypted_zip_reads_only_with_correct_passphrase():
    """In WZ_AES filenames are cleartext, so opening + namelist always works;
    only reading the *content* requires the passphrase."""
    files = {"users.json": b'[{"id": 1, "secret": "no"}]'}
    passphrase = "correct-horse-battery"
    buf = _build_encrypted_zip(files, passphrase)

    # Correct passphrase -> content decrypts.
    with pyzipper.AESZipFile(buf, "r") as zf:
        zf.setpassword(passphrase.encode("utf-8"))
        assert zf.read("users.json") == files["users.json"]

    # Wrong passphrase -> read raises.
    buf.seek(0)
    with pyzipper.AESZipFile(buf, "r") as zf:
        zf.setpassword(b"wrong-passphrase-xx")
        with pytest.raises(RuntimeError):
            zf.read("users.json")

    # No passphrase -> read raises.
    buf.seek(0)
    with pyzipper.AESZipFile(buf, "r") as zf:
        with pytest.raises(RuntimeError):
            zf.read("users.json")


# ============================================================================
# Task 3 — /bundle endpoint integration tests
# ============================================================================

import json

from app.api.v1.auth import get_current_user
from app.api.v1.admin_data_export import _BUNDLE_FILE_ORDER
from app.api.v1.feature_guards import require_tech_services_enabled
from app.core.security import hash_password
from app.main import app
from app.models.multi_branch import LibrarySystem

_BUNDLE_URL = "/api/v1/admin/data-export/bundle"
_VALID_PASSPHRASE = "correct-horse-battery-staple"


@pytest.fixture
async def seeded_system(test_db):
    """Seed exactly one active LibrarySystem so _resolve_system resolves it."""
    system = LibrarySystem(code="LSC", name="Little Schitt Creek Library", is_active=True)
    test_db.add(system)
    await test_db.commit()
    await test_db.refresh(system)
    return system


async def _make_db_user(test_db, role: UserRole) -> User:
    user = User(
        email=f"{role.value}-bundle@example.com",
        password_hash=hash_password("Sup3rSecret!pass"),
        first_name="Bundle",
        last_name=role.value.title(),
        role=role,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
def _bypass_tech_guard():
    """Disable the router-level tech_services feature guard for the endpoint."""
    app.dependency_overrides[require_tech_services_enabled] = lambda: None
    yield
    app.dependency_overrides.pop(require_tech_services_enabled, None)


def _auth_as(user: User):
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.mark.asyncio
async def test_bundle_short_passphrase_returns_422(
    client, test_db, _bypass_tech_guard
):
    user = await _make_db_user(test_db, UserRole.DIRECTOR)
    _auth_as(user)
    try:
        resp = await client.post(_BUNDLE_URL, json={"passphrase": "short"})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_bundle_empty_body_returns_422(
    client, test_db, _bypass_tech_guard
):
    user = await _make_db_user(test_db, UserRole.DIRECTOR)
    _auth_as(user)
    try:
        resp = await client.post(_BUNDLE_URL, json={})
        assert resp.status_code == 422
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_bundle_admin_role_forbidden(
    client, test_db, seeded_system, _bypass_tech_guard
):
    user = await _make_db_user(test_db, UserRole.ADMIN)
    _auth_as(user)
    try:
        resp = await client.post(_BUNDLE_URL, json={"passphrase": _VALID_PASSPHRASE})
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# --- 200-path tests ---------------------------------------------------------
# Routing the bundle response through httpx's ASGITransport trips the known
# Starlette BaseHTTPMiddleware incompatibility ("Unexpected message received:
# http.request"), a test-transport limitation, not an endpoint bug. So the
# success path is exercised by invoking the endpoint handler directly with a
# real test_db session and reading the returned Response body. The endpoint
# returns a plain Response (full in-memory archive), so the bytes are on
# response.body.


async def _collect_body(response) -> bytes:
    body = response.body
    return bytes(body) if not isinstance(body, (bytes, bytearray)) else bytes(body)


@pytest.mark.asyncio
async def test_bundle_director_role_ok(test_db, seeded_system):
    from app.api.v1.admin_data_export import BundleRequest, export_bundle

    director = await _make_db_user(test_db, UserRole.DIRECTOR)
    response = await export_bundle(
        body=BundleRequest(passphrase=_VALID_PASSPHRASE),
        db=test_db,
        current_user=director,
    )
    assert response.status_code == 200
    assert response.media_type == "application/zip"


@pytest.mark.asyncio
async def test_bundle_super_admin_role_ok(test_db, seeded_system):
    from app.api.v1.admin_data_export import BundleRequest, export_bundle

    admin = await _make_db_user(test_db, UserRole.SUPER_ADMIN)
    response = await export_bundle(
        body=BundleRequest(passphrase=_VALID_PASSPHRASE),
        db=test_db,
        current_user=admin,
    )
    assert response.status_code == 200
    assert response.media_type == "application/zip"


@pytest.mark.asyncio
async def test_bundle_response_headers_and_zip_contents(test_db, seeded_system):
    import io

    from app.api.v1.admin_data_export import BundleRequest, export_bundle

    # Persist a user row so users.json is non-empty and the exclusion bites.
    director = await _make_db_user(test_db, UserRole.DIRECTOR)
    response = await export_bundle(
        body=BundleRequest(passphrase=_VALID_PASSPHRASE),
        db=test_db,
        current_user=director,
    )
    assert response.status_code == 200
    assert response.media_type == "application/zip"

    sha = response.headers["X-Export-SHA256"]
    assert len(sha) == 64
    assert all(c in "0123456789abcdef" for c in sha)

    body = await _collect_body(response)
    with pyzipper.AESZipFile(io.BytesIO(body), "r") as zf:
        names = set(zf.namelist())
        for expected in _BUNDLE_FILE_ORDER:
            assert expected in names, f"missing {expected}"
        assert "manifest.json" in names

        zf.setpassword(_VALID_PASSPHRASE.encode("utf-8"))
        users = json.loads(zf.read("users.json"))
        assert len(users) >= 1
        for u in users:
            assert "password_hash" not in u
            assert "totp_secret" not in u
            assert not any(k.endswith("_token") for k in u)
        # Enum fields must serialize to bare values, not "UserRole.DIRECTOR".
        assert any(u.get("role") == "director" for u in users)


# ============================================================================
# Task 4 — manifest reconciliation: whole-DB counts + sha256 field
# ============================================================================

_EXPECTED_MANIFEST_TABLES = {
    "users",
    "regions",
    "branches",
    "catalog_items",
    "item_copies",
    "branch_item_copies",
    "checkouts",
    "holds",
    "fines",
    "fine_payment_history",
}


@pytest.mark.asyncio
async def test_manifest_whole_table_counts_and_sha256_field(test_db, seeded_system):
    from app.api.v1.admin_data_export import ExportManifest, _build_manifest

    # Seed one user so the users count is verifiably >= 1.
    director = await _make_db_user(test_db, UserRole.DIRECTOR)

    manifest = await _build_manifest(test_db, seeded_system)

    # Correct set of 10 dataset table names.
    assert {c.table for c in manifest.counts} == _EXPECTED_MANIFEST_TABLES

    # Whole-table count: the seeded director must be visible (no WHERE scoping).
    users_count = next(c for c in manifest.counts if c.table == "users")
    assert users_count.rows >= 1

    # sha256 field exists on ExportManifest and defaults to None when not set
    # by _build_manifest (it is set externally by the /bundle endpoint).
    assert manifest.sha256 is None

    # Notes reflect whole-DB wording, not old scoped wording.
    combined_notes = " ".join(manifest.notes)
    assert "whole-table" in combined_notes
    assert "not yet implemented" not in combined_notes
