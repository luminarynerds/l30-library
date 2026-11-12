# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Smoke test: ORM-driven demo seeder (Task 5).

Exercises `app.seeds.demo_seeder.seed_demo` against a real, freshly
initialized Postgres schema (not SQLite -- the schema uses pgvector,
JSONB, and ARRAY column types the ORM seeder's models depend on
transitively via `Base.metadata`). Reuses the disposable-database fixture
from test_dist_schema_complete.py: create an empty, uniquely-named database,
run the same raw-SQL schema init the real fresh-install path uses, then run
the ORM seeder against it and assert row counts via the ORM (not raw SQL),
per docs/dist-install-characterization.md §6's finding that only ORM-level
inserts reliably honor this schema's ~1,200 Python-side `default=` columns.

Requires a real Postgres reachable at TEST_SCHEMA_DATABASE_URL (or
DATABASE_URL) with the pgvector extension's shared library present -- skips
loudly (does not silently pass) if unreachable.
"""
import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.smoke.test_dist_schema_complete import _run_init, fresh_schema_conn  # noqa: F401

pytestmark = pytest.mark.smoke


async def _seeded_session(fresh_schema_conn, monkeypatch) -> AsyncSession:
    """Init the full schema against the disposable DB, return a bound session."""
    _conn, db_url = fresh_schema_conn
    await _run_init(fresh_schema_conn, monkeypatch)

    engine = create_async_engine(db_url)
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    return session_maker(), engine


async def test_seed_demo_populates(fresh_schema_conn, monkeypatch):
    from app.models.catalog import CatalogItem
    from app.models.circulation import Checkout, Hold
    from app.models.event import Event
    from app.core.security import verify_password
    from app.models.library_branding import LibraryBranding
    from app.models.user import User, UserRole
    from app.seeds.demo_seeder import seed_demo

    session, engine = await _seeded_session(fresh_schema_conn, monkeypatch)
    try:
        # seed_demo is undefined until Task 5's implementation lands --
        # this import + call is the "write the failing test first" step.
        result = await seed_demo(session)
        assert result["skipped"] is False

        async def count(model, *where):
            stmt = select(func.count()).select_from(model)
            for clause in where:
                stmt = stmt.where(clause)
            return (await session.execute(stmt)).scalar_one()

        catalog_count = await count(CatalogItem)
        assert catalog_count >= 2000, f"expected >=2000 catalog items, got {catalog_count}"

        patron_count = await count(User, User.role.in_([UserRole.PATRON, UserRole.CHILD]))
        assert patron_count >= 50, f"expected >=50 fake patrons, got {patron_count}"

        # Different login per role: a patron's password is not a staff's. Default
        # base is "demo-2026" (no DEMO_LOGIN_PASSWORD set in the test env).
        a_patron = (
            await session.execute(select(User).where(User.role == UserRole.PATRON).limit(1))
        ).scalar_one()
        a_staff = (
            await session.execute(select(User).where(User.role == UserRole.STAFF).limit(1))
        ).scalar_one()
        assert verify_password("demo-2026-patron", a_patron.password_hash)
        assert verify_password("demo-2026-staff", a_staff.password_hash)
        # Crucially, the patron credential does NOT unlock a staff account.
        assert not verify_password("demo-2026-patron", a_staff.password_hash)

        # Secure by default: the full-access super_admin demo login must NOT be
        # seeded unless DEMO_SUPERADMIN_PASSWORD is set. A super_admin carrying
        # the repo-known demo password would be a takeover on any public demo.
        superadmin_count = await count(User, User.role == UserRole.SUPER_ADMIN)
        assert superadmin_count == 0, (
            "super_admin demo login must not be seeded without "
            f"DEMO_SUPERADMIN_PASSWORD (got {superadmin_count})"
        )

        event_count = await count(Event)
        assert event_count >= 20, f"expected >=20 events, got {event_count}"

        checkout_count = await count(Checkout)
        assert checkout_count >= 1, "expected at least one active checkout"

        hold_count = await count(Hold)
        assert hold_count >= 1, "expected at least one hold"

        # Every seeded patron must have a populated email_hash -- the exact
        # §6.2 failure mode (NOT NULL / blind-index columns silently unset
        # by hand-written SQL) must not reproduce via the ORM path.
        missing_hash = await count(User, User.email_hash.is_(None))
        assert missing_hash == 0, "every seeded user must have email_hash populated"

        # Default profile is the FICTIONAL Little Schitt Creek universe: a
        # fork's demo load must never seed a real library's identity.
        branding_row = (
            await session.execute(select(LibraryBranding).where(LibraryBranding.id == 1))
        ).scalar_one_or_none()
        assert branding_row is not None
        assert branding_row.library_name == "Little Schitt Creek Library"

        # Re-running must not duplicate the catalog (idempotency gate).
        second = await seed_demo(session)
        assert second["skipped"] is True
        assert await count(CatalogItem) == catalog_count
    finally:
        await session.close()
        await engine.dispose()


async def test_seed_demo_superadmin_optin(fresh_schema_conn, monkeypatch):
    """With DEMO_SUPERADMIN_PASSWORD configured, the full-access super_admin
    demo login is seeded -- with THAT password, never the shared demo hash."""
    from app.core.security import verify_password
    from app.models.user import User, UserRole
    from app.seeds import demo_seeder
    from app.seeds.demo_seeder import seed_demo

    monkeypatch.setattr(demo_seeder, "_DEMO_SUPERADMIN_PASSWORD", "s3cret-operator-pw")

    session, engine = await _seeded_session(fresh_schema_conn, monkeypatch)
    try:
        result = await seed_demo(session)
        assert result["skipped"] is False

        admin = (
            await session.execute(select(User).where(User.role == UserRole.SUPER_ADMIN))
        ).scalar_one()
        assert admin.email == "avery.sinclair@littleschittcreek.example.org"
        # Logs in with the configured private password, not any role's demo
        # password (the super_admin must never share the low-privilege creds).
        assert verify_password("s3cret-operator-pw", admin.password_hash)
        assert not verify_password("demo-2026-admin", admin.password_hash)
        assert not verify_password("demo-2026-staff", admin.password_hash)
    finally:
        await session.close()
        await engine.dispose()


async def test_seed_demo_orange_profile_optin(fresh_schema_conn, monkeypatch):
    """DEMO_PROFILE=orange seeds the Orange Public Library identity (used only
    on orange-demo); every board member comes from the Orange roster."""
    from app.models.board import BoardMember
    from app.models.library_branding import LibraryBranding
    from app.seeds.demo_seeder import ORANGE, seed_demo

    monkeypatch.setenv("DEMO_PROFILE", "orange")

    session, engine = await _seeded_session(fresh_schema_conn, monkeypatch)
    try:
        result = await seed_demo(session)
        assert result["skipped"] is False

        branding_row = (
            await session.execute(select(LibraryBranding).where(LibraryBranding.id == 1))
        ).scalar_one()
        assert branding_row.library_name == "Orange Public Library"
        assert branding_row.card_prefix == "ORPL"

        names = {
            m.full_name
            for m in (await session.execute(select(BoardMember))).scalars()
        }
        assert names == {name for name, _ in ORANGE["board_roster"]}
    finally:
        await session.close()
        await engine.dispose()
