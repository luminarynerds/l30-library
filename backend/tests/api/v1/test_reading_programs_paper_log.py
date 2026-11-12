# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for printable paper log / kiosk claim-code endpoints."""

from datetime import date, timedelta

import pytest

from app.models.organization_features import OrganizationFeatures
from app.models.reading import (
    ReadingLogEntry,
    ReadingProgram,
    ReadingProgramType,
    ReadingRegistration,
)
from app.services.organization_features_service import OrganizationFeaturesService


@pytest.fixture
async def features_paper_log_on(test_db):
    feat = OrganizationFeatures(
        reading_programs_enabled=True,
        reading_programs_paper_log_enabled=True,
    )
    test_db.add(feat)
    await test_db.commit()
    await test_db.refresh(feat)
    # Redis caches an org-features snapshot across tests; invalidate so
    # this test's DB row is what gets read/re-cached.
    await OrganizationFeaturesService.invalidate_cache()
    return feat


@pytest.fixture
async def features_paper_log_off(test_db):
    feat = OrganizationFeatures(
        reading_programs_enabled=True,
        reading_programs_paper_log_enabled=False,
    )
    test_db.add(feat)
    await test_db.commit()
    await test_db.refresh(feat)
    await OrganizationFeaturesService.invalidate_cache()
    return feat


@pytest.fixture
async def program(test_db):
    p = ReadingProgram(
        name="Paper Log Test Program",
        description="x",
        program_type=ReadingProgramType.summer,
        start_date=date.today() - timedelta(days=10),
        end_date=date.today() + timedelta(days=20),
        reading_goal_type="books",
        reading_goal_value=10,
        is_active=True,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.fixture
async def expired_program(test_db):
    p = ReadingProgram(
        name="Expired Program",
        description="x",
        program_type=ReadingProgramType.summer,
        start_date=date.today() - timedelta(days=200),
        end_date=date.today() - timedelta(days=60),  # > 30d ago
        is_active=False,
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


@pytest.fixture
async def patron_registration(test_db, test_patron, program):
    reg = ReadingRegistration(
        user_id=test_patron.id, program_id=program.id, goal_target=10
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    return reg


@pytest.fixture
async def staff_registration(test_db, test_staff, program):
    reg = ReadingRegistration(
        user_id=test_staff.id, program_id=program.id, goal_target=10
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    return reg


@pytest.fixture
async def expired_registration(test_db, test_staff, expired_program):
    reg = ReadingRegistration(
        user_id=test_staff.id, program_id=expired_program.id, goal_target=10
    )
    test_db.add(reg)
    await test_db.commit()
    await test_db.refresh(reg)
    return reg


@pytest.mark.asyncio
class TestPaperLogPdf:
    async def test_pdf_returns_application_pdf_bytes(
        self, staff_client, features_paper_log_on, program, staff_registration
    ):
        r = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/log.pdf"
        )
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].startswith("application/pdf")
        assert r.content[:4] == b"%PDF"

    async def test_pdf_idempotent_same_code(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        r1 = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/log.pdf"
        )
        assert r1.status_code == 200
        await test_db.refresh(staff_registration)
        code1 = staff_registration.paper_log_code
        assert code1 and len(code1) == 8

        r2 = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/log.pdf"
        )
        assert r2.status_code == 200
        await test_db.refresh(staff_registration)
        assert staff_registration.paper_log_code == code1

    async def test_flag_off_returns_404(
        self, staff_client, features_paper_log_off, program, staff_registration
    ):
        r = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/log.pdf"
        )
        assert r.status_code == 404


@pytest.mark.asyncio
class TestPaperLogRedeem:
    async def _generate_code(self, staff_client, program, registration):
        r = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{registration.id}/log.pdf"
        )
        assert r.status_code == 200, r.text

    async def test_redeem_creates_entries_and_sets_redeemed_at(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        await self._generate_code(staff_client, program, staff_registration)
        await test_db.refresh(staff_registration)
        code = staff_registration.paper_log_code

        d = (date.today() - timedelta(days=1)).isoformat()
        payload = {
            "code": code,
            "entries": [
                {"entry_date": d, "title": "Book A", "books_read": 1, "minutes_read": 30},
                {"entry_date": d, "title": "Book B", "books_read": 1, "minutes_read": 45},
                {"entry_date": d, "title": "Book C", "books_read": 1, "minutes_read": 60},
            ],
        }
        r = await staff_client.post("/api/v1/reading-programs/redeem", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["entries_created"] == 3
        assert body["total_books"] == 3
        assert body["total_minutes"] == 135
        assert body["goal_percent"] == 30.0

        from sqlalchemy import select

        rows = (
            (
                await test_db.execute(
                    select(ReadingLogEntry).where(
                        ReadingLogEntry.registration_id == staff_registration.id
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 3
        await test_db.refresh(staff_registration)
        assert staff_registration.paper_log_code_redeemed_at is not None

    async def test_already_redeemed_returns_409(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        await self._generate_code(staff_client, program, staff_registration)
        await test_db.refresh(staff_registration)
        code = staff_registration.paper_log_code
        d = (date.today() - timedelta(days=1)).isoformat()
        payload = {"code": code, "entries": [{"entry_date": d, "books_read": 1}]}
        r1 = await staff_client.post("/api/v1/reading-programs/redeem", json=payload)
        assert r1.status_code == 200
        r2 = await staff_client.post("/api/v1/reading-programs/redeem", json=payload)
        assert r2.status_code == 409

    async def test_code_not_found_returns_404(
        self, staff_client, features_paper_log_on
    ):
        d = (date.today() - timedelta(days=1)).isoformat()
        r = await staff_client.post(
            "/api/v1/reading-programs/redeem",
            json={
                "code": "ZZZZZZZZ",
                "entries": [{"entry_date": d, "books_read": 1}],
            },
        )
        assert r.status_code == 404

    async def test_expired_program_returns_410(
        self,
        staff_client,
        features_paper_log_on,
        expired_program,
        expired_registration,
        test_db,
    ):
        # Generate code directly on a registration whose program is expired.
        from app.services.paper_log_service import generate_or_get_code

        code = await generate_or_get_code(test_db, expired_registration)
        d = expired_program.start_date.isoformat()
        r = await staff_client.post(
            "/api/v1/reading-programs/redeem",
            json={
                "code": code,
                "entries": [{"entry_date": d, "books_read": 1}],
            },
        )
        assert r.status_code == 410

    async def test_minutes_over_120_returns_422(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        await self._generate_code(staff_client, program, staff_registration)
        await test_db.refresh(staff_registration)
        d = (date.today() - timedelta(days=1)).isoformat()
        # Pydantic schema enforces <=120 and returns 422 itself.
        r = await staff_client.post(
            "/api/v1/reading-programs/redeem",
            json={
                "code": staff_registration.paper_log_code,
                "entries": [{"entry_date": d, "minutes_read": 200}],
            },
        )
        assert r.status_code == 422

    async def test_entry_date_outside_window_returns_422(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        await self._generate_code(staff_client, program, staff_registration)
        await test_db.refresh(staff_registration)
        future = (program.end_date + timedelta(days=5)).isoformat()
        r = await staff_client.post(
            "/api/v1/reading-programs/redeem",
            json={
                "code": staff_registration.paper_log_code,
                "entries": [{"entry_date": future, "books_read": 1}],
            },
        )
        assert r.status_code == 422

    async def test_flag_off_returns_404(
        self, staff_client, features_paper_log_off
    ):
        d = (date.today() - timedelta(days=1)).isoformat()
        r = await staff_client.post(
            "/api/v1/reading-programs/redeem",
            json={"code": "ABCDEFGH", "entries": [{"entry_date": d, "books_read": 1}]},
        )
        assert r.status_code == 404

    async def test_redeem_persists_entry_date_distinct_from_today(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        """Issue #828: paper-log entries must preserve the patron-written
        reading date, not collapse onto the redemption timestamp."""
        await self._generate_code(staff_client, program, staff_registration)
        await test_db.refresh(staff_registration)
        code = staff_registration.paper_log_code

        day_a = date.today() - timedelta(days=5)
        day_b = date.today() - timedelta(days=2)
        payload = {
            "code": code,
            "entries": [
                {"entry_date": day_a.isoformat(), "books_read": 1, "minutes_read": 20},
                {"entry_date": day_b.isoformat(), "books_read": 1, "minutes_read": 30},
            ],
        }
        r = await staff_client.post("/api/v1/reading-programs/redeem", json=payload)
        assert r.status_code == 200, r.text

        from sqlalchemy import select

        rows = (
            (
                await test_db.execute(
                    select(ReadingLogEntry)
                    .where(ReadingLogEntry.registration_id == staff_registration.id)
                    .order_by(ReadingLogEntry.entry_date)
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 2
        assert rows[0].entry_date == day_a
        assert rows[1].entry_date == day_b
        # logged_at remains the redemption timestamp; entry_date is distinct.
        assert rows[0].entry_date != rows[0].logged_at.date()
        assert rows[1].entry_date != rows[1].logged_at.date()


@pytest.mark.asyncio
class TestResetPaperLogCode:
    async def test_staff_resets_to_new_code(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        r1 = await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/log.pdf"
        )
        assert r1.status_code == 200
        await test_db.refresh(staff_registration)
        old_code = staff_registration.paper_log_code

        r = await staff_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/reset-log-code"
        )
        assert r.status_code == 200
        new_code = r.json()["paper_log_code"]
        assert new_code != old_code
        assert len(new_code) == 8

    async def test_flag_off_returns_404(
        self,
        staff_client,
        features_paper_log_off,
        program,
        staff_registration,
    ):
        r = await staff_client.post(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/reset-log-code"
        )
        assert r.status_code == 404

# === Additional coverage: patron-unowned 403, badge spy ===


@pytest.fixture
async def other_patron(test_db):
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    u = User(
        email="other@example.com",
        password_hash=hash_password("Other123!"),
        first_name="Other",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(u)
    await test_db.commit()
    await test_db.refresh(u)
    return u


@pytest.fixture
async def patron_client(test_db, other_patron):
    """HTTP client authenticated as the `other_patron` (a non-owner)."""
    from httpx import AsyncClient, ASGITransport

    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return other_patron

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.state.setup_complete = True

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
class TestPaperLogOwnership:
    async def test_patron_unowned_code_returns_403_and_does_not_consume(
        self,
        patron_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
    ):
        # Generate code directly via the service (avoid colliding auth overrides).
        # A *different* patron then tries to redeem and must be 403-d.
        from app.services.paper_log_service import generate_or_get_code

        code = await generate_or_get_code(test_db, staff_registration)
        d = (date.today() - timedelta(days=1)).isoformat()
        rp = await patron_client.post(
            "/api/v1/reading-programs/redeem",
            json={"code": code, "entries": [{"entry_date": d, "books_read": 1}]},
        )
        assert rp.status_code == 403
        # Code must remain redeemable.
        await test_db.refresh(staff_registration)
        assert staff_registration.paper_log_code_redeemed_at is None

    async def test_staff_can_redeem_any_code(
        self,
        staff_client,
        features_paper_log_on,
        program,
        patron_registration,
        test_db,
    ):
        # Generate code on the patron's registration (via service directly).
        from app.services.paper_log_service import generate_or_get_code

        code = await generate_or_get_code(test_db, patron_registration)
        d = (date.today() - timedelta(days=1)).isoformat()
        r = await staff_client.post(
            "/api/v1/reading-programs/redeem",
            json={"code": code, "entries": [{"entry_date": d, "books_read": 1}]},
        )
        assert r.status_code == 200
        assert r.json()["entries_created"] == 1


@pytest.mark.asyncio
class TestBadgeCheckFires:
    async def test_redeem_invokes_achievement_service(
        self,
        staff_client,
        features_paper_log_on,
        program,
        staff_registration,
        test_db,
        monkeypatch,
    ):
        from app.services import reading_achievement_service as ras

        calls = {"n": 0}

        async def fake_check(self, user_id, program_id, registration_id):
            calls["n"] += 1
            return []

        monkeypatch.setattr(
            ras.ReadingAchievementService,
            "check_and_award_achievements",
            fake_check,
        )

        # Generate + redeem.
        await staff_client.get(
            f"/api/v1/reading-programs/programs/{program.id}/registrations/{staff_registration.id}/log.pdf"
        )
        await test_db.refresh(staff_registration)
        code = staff_registration.paper_log_code
        d = (date.today() - timedelta(days=1)).isoformat()
        r = await staff_client.post(
            "/api/v1/reading-programs/redeem",
            json={"code": code, "entries": [{"entry_date": d, "books_read": 1}]},
        )
        assert r.status_code == 200
        assert calls["n"] == 1
