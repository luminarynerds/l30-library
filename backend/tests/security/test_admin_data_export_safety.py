# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Security tests for the admin data-export endpoints.

Focus: the table-identifier safety helpers. The export endpoint historically
interpolated table names directly into raw SQL. Even with the list of tables
being process-defined today, we want belt-and-suspenders so a future change
that broadens the list (e.g. accepting a query param) is automatically
rejected unless the name passes every check.
"""

from __future__ import annotations

import re

import pytest
from fastapi import HTTPException

from app.api.v1 import admin_data_export


# --- Regex layer ---------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        "users",
        "billing_records",
        "_legacy",
        "T",
        "abc_123",
    ],
)
def test_table_pattern_accepts_valid_identifiers(value: str) -> None:
    assert admin_data_export._TABLE_NAME_PATTERN.match(value)


@pytest.mark.parametrize(
    "value",
    [
        "",
        "1users",  # leading digit
        "users;DROP TABLE users",
        'users" --',
        "users\nselect",
        "users users",  # space
        "users; --",
        "users OR 1=1",
        "users/**/",
        "users--",
        "пользователи",  # non-ASCII
        "users.column",  # dotted
        "users`",  # backtick
        "(select 1)",
    ],
)
def test_table_pattern_rejects_injection_payloads(value: str) -> None:
    assert admin_data_export._TABLE_NAME_PATTERN.match(value) is None


# --- _safe_table_identifier helper ---------------------------------------


class _FakeAsyncSession:
    """Minimal stand-in for AsyncSession.run_sync.

    Returns whatever inspector.get_table_names() would return -- we feed it
    a fixed list and assert the helper consults it.
    """

    def __init__(self, table_names: list[str]) -> None:
        self._table_names = table_names
        self.run_sync_calls = 0

    async def run_sync(self, fn):  # pragma: no cover - trivial passthrough
        self.run_sync_calls += 1

        class _FakeInspector:
            def __init__(self, names):
                self._names = names

            def get_table_names(self):
                return self._names

        class _FakeConn:
            pass

        # The real SQLAlchemy inspect() consumes the connection; our fake
        # version ignores it and returns the predefined names so we can
        # exercise the validation logic without a DB.
        def runner(_conn):
            return _FakeInspector(self._table_names).get_table_names()

        return runner(_FakeConn())


@pytest.fixture(autouse=True)
def _reset_known_tables_cache():
    """Ensure each test gets a fresh cache."""
    admin_data_export._known_tables_cache = None
    yield
    admin_data_export._known_tables_cache = None


@pytest.mark.asyncio
async def test_safe_table_identifier_accepts_known_table() -> None:
    db = _FakeAsyncSession(["users", "branches", "regions"])
    quoted = await admin_data_export._safe_table_identifier(db, "users")
    assert quoted == '"users"'


@pytest.mark.asyncio
async def test_safe_table_identifier_caches_lookup() -> None:
    db = _FakeAsyncSession(["users", "branches"])
    await admin_data_export._safe_table_identifier(db, "users")
    await admin_data_export._safe_table_identifier(db, "branches")
    # Cache populated on first call; second call must not re-inspect.
    assert db.run_sync_calls == 1


@pytest.mark.asyncio
async def test_safe_table_identifier_rejects_unknown_table() -> None:
    db = _FakeAsyncSession(["users", "branches"])
    with pytest.raises(HTTPException) as excinfo:
        await admin_data_export._safe_table_identifier(db, "secrets")
    assert excinfo.value.status_code == 400
    assert "Unknown table identifier" in excinfo.value.detail


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        "users; DROP TABLE users",
        'users" --',
        "users OR 1=1",
        "1users",
        "",
        "users users",
        "users.column",
    ],
)
async def test_safe_table_identifier_rejects_injection_shapes(payload: str) -> None:
    # Even if the malicious value happens to be in the live schema list,
    # the regex must reject it first.
    db = _FakeAsyncSession([payload, "users"])
    with pytest.raises(HTTPException) as excinfo:
        await admin_data_export._safe_table_identifier(db, payload)
    assert excinfo.value.status_code == 400


@pytest.mark.asyncio
async def test_safe_table_identifier_rejects_non_string() -> None:
    db = _FakeAsyncSession(["users"])
    for bad in (None, 1, ["users"], object()):
        with pytest.raises(HTTPException) as excinfo:
            await admin_data_export._safe_table_identifier(db, bad)  # type: ignore[arg-type]
        assert excinfo.value.status_code == 400


# --- _EXPORT_TABLES sanity -------------------------------------------------
# Renamed from _SCOPED_TABLES (list[tuple[label, table]]) to a flat
# list[str] in f12c9d764 (encrypted whole-DB export bundle refactor).


def test_scoped_tables_all_pass_regex() -> None:
    # The static allowlist of tables touched by the manifest builder must
    # itself satisfy the format check -- catches typos and future drift.
    for table in admin_data_export._EXPORT_TABLES:
        assert admin_data_export._TABLE_NAME_PATTERN.match(table), (
            f"_EXPORT_TABLES entry {table!r} fails identifier check"
        )


# --- _EXCLUDE_FIELDS is a frozenset of strings ---------------------------


def test_exclude_fields_are_string_names() -> None:
    # Previously this was a set of bare names that raised NameError at
    # request time. Lock in that it now contains only strings.
    assert isinstance(admin_data_export._EXCLUDE_FIELDS, frozenset)
    assert all(isinstance(v, str) for v in admin_data_export._EXCLUDE_FIELDS)
    # The core auth secrets must always be excluded.
    for required in ("password", "password_hash", "token", "api_key"):
        assert required in admin_data_export._EXCLUDE_FIELDS
