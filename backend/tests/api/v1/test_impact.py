# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the impact measurement layer — Phase 1 governance endpoints."""
from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.models.audit_log import AuditAction, AuditLog
from app.models.impact import OutcomeIndicator, TheoryOfChangeClaim
from app.models.organization_features import OrganizationFeatures
from app.models.program import Program
from app.models.user import User, UserRole
from app.services.organization_features_service import OrganizationFeaturesService


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
async def impact_features_on(test_db):
    """Enable the impact_measurement_enabled feature flag for the test org."""
    feat = OrganizationFeatures(impact_measurement_enabled=True)
    test_db.add(feat)
    await test_db.commit()
    await test_db.refresh(feat)
    # The service caches an org-features snapshot in Redis across tests;
    # invalidate so this test's DB row is what gets read/re-cached.
    await OrganizationFeaturesService.invalidate_cache()
    return feat


@pytest.fixture
async def test_director(test_db):
    """A user with DIRECTOR role for authorization tests."""
    user = User(
        email="director@test.local",
        password_hash="x",
        first_name="Dir",
        last_name="Ector",
        role=UserRole.DIRECTOR,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def director_client(test_db, test_director, impact_features_on):
    """Async HTTP client authenticated as a DIRECTOR user.

    Also pre-enables the impact-measurement feature flag so router-level
    guards don't 404 the requests.
    """
    from httpx import ASGITransport, AsyncClient

    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_director

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


@pytest.fixture
async def staff_client_impact(test_db, test_staff, impact_features_on):
    """staff_client equivalent that pre-enables the impact feature flag."""
    from httpx import ASGITransport, AsyncClient

    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_staff

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


@pytest.fixture
async def sample_program(test_db):
    """A bare ``programs`` row usable as a claim's contributing program."""
    from datetime import time

    p = Program(
        title="Adult literacy circle",
        description="Weekly tutoring",
        program_type="literacy",
        audience="adults",
        program_date=date.today(),
        start_time=time(10, 0),
    )
    test_db.add(p)
    await test_db.commit()
    await test_db.refresh(p)
    return p


def _indicator_payload(**overrides) -> dict:
    base = {
        "slug": "adult_literacy_rate_county",
        "name": "Adult literacy rate (county)",
        "description": "Share of adults with basic prose literacy.",
        "unit": "%",
        "direction_better": "up",
        "cadence": "annual",
        "geographic_scope_type": "county",
        "primary_source": "ACS 5yr S1501",
        "source_url": "https://data.census.gov/...",
        "requires_board_approval": False,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------
# OutcomeIndicator
# ---------------------------------------------------------------------


class TestOutcomeIndicatorCreate:
    async def test_staff_can_create_draft(self, staff_client_impact):
        r = await staff_client_impact.post(
            "/api/v1/impact/indicators", json=_indicator_payload()
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["slug"] == "adult_literacy_rate_county"
        assert body["approved_at"] is None
        assert body["is_active"] is True

    async def test_duplicate_slug_409(self, staff_client_impact):
        r1 = await staff_client_impact.post(
            "/api/v1/impact/indicators", json=_indicator_payload()
        )
        assert r1.status_code == 201
        r2 = await staff_client_impact.post(
            "/api/v1/impact/indicators", json=_indicator_payload()
        )
        assert r2.status_code == 409

    async def test_invalid_direction_better_422(self, staff_client_impact):
        r = await staff_client_impact.post(
            "/api/v1/impact/indicators",
            json=_indicator_payload(direction_better="sideways"),
        )
        assert r.status_code == 422

    async def test_create_writes_audit_row(
        self, staff_client_impact, test_db, test_staff
    ):
        r = await staff_client_impact.post(
            "/api/v1/impact/indicators", json=_indicator_payload()
        )
        assert r.status_code == 201
        indicator_id = r.json()["id"]

        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.action == AuditAction.OUTCOME_INDICATOR_CREATED,
                AuditLog.admin_id == test_staff.id,
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) == 1
        assert rows[0].details["resource_id"] == indicator_id
        assert rows[0].details["resource_type"] == "outcome_indicator"
        assert rows[0].details["slug"] == "adult_literacy_rate_county"


class TestOutcomeIndicatorApprove:
    async def test_staff_cannot_approve(self, staff_client_impact, test_db):
        # Staff create the draft, but should be 403 on approve.
        ind = OutcomeIndicator(
            slug="staff_blocked_test",
            name="x",
            description="x",
            unit="%",
            direction_better="up",
            cadence="annual",
            geographic_scope_type="county",
        )
        test_db.add(ind)
        await test_db.commit()
        await test_db.refresh(ind)

        r = await staff_client_impact.post(
            f"/api/v1/impact/indicators/{ind.id}/approve", json={}
        )
        assert r.status_code == 403

    async def test_director_can_approve_and_audit_written(
        self, director_client, test_db, test_director
    ):
        ind = OutcomeIndicator(
            slug="director_can_approve",
            name="x",
            description="x",
            unit="%",
            direction_better="up",
            cadence="annual",
            geographic_scope_type="county",
        )
        test_db.add(ind)
        await test_db.commit()
        await test_db.refresh(ind)

        r = await director_client.post(
            f"/api/v1/impact/indicators/{ind.id}/approve", json={}
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["approved_at"] is not None
        assert body["approved_by_user_id"] == test_director.id

        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.action == AuditAction.OUTCOME_INDICATOR_APPROVED,
                AuditLog.admin_id == test_director.id,
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) == 1
        assert rows[0].details["resource_id"] == ind.id

    async def test_requires_board_approval_needs_link(
        self, director_client, test_db
    ):
        ind = OutcomeIndicator(
            slug="needs_board",
            name="x",
            description="x",
            unit="%",
            direction_better="up",
            cadence="annual",
            geographic_scope_type="county",
            requires_board_approval=True,
        )
        test_db.add(ind)
        await test_db.commit()
        await test_db.refresh(ind)

        # Without board_decision_link_id → 422.
        r1 = await director_client.post(
            f"/api/v1/impact/indicators/{ind.id}/approve", json={}
        )
        assert r1.status_code == 422, r1.text
        # FastAPI HTTPException(detail=str) renders as {"detail": str};
        # tolerate either shape so a future tightening of the schema
        # (which would emit Pydantic's {"detail": [...]} shape) does not
        # break this test.
        body = r1.json()
        rendered = str(body.get("detail", body)).lower()
        assert "board" in rendered


# ---------------------------------------------------------------------
# TheoryOfChangeClaim
# ---------------------------------------------------------------------


@pytest.fixture
async def approved_indicator(test_db):
    ind = OutcomeIndicator(
        slug="approved_indicator_for_claims",
        name="x",
        description="x",
        unit="%",
        direction_better="up",
        cadence="annual",
        geographic_scope_type="county",
    )
    test_db.add(ind)
    await test_db.commit()
    await test_db.refresh(ind)
    return ind


class TestClaimCreate:
    async def test_create_with_program_succeeds_and_sets_next_review(
        self, staff_client_impact, approved_indicator, sample_program
    ):
        payload = {
            "outcome_indicator_id": approved_indicator.id,
            "contributing_program_id": sample_program.id,
            "mechanism_short": "Tutoring builds reading fluency.",
            "mechanism_detail": "Eight 60-minute sessions per learner.",
        }
        r = await staff_client_impact.post("/api/v1/impact/claims", json=payload)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["evidence_strength"] == "theoretical"
        assert body["contributing_program_id"] == sample_program.id
        assert body["contributing_initiative_id"] is None

        # next_review_due should land 365±1 days in the future.
        nrd = date.fromisoformat(body["next_review_due"])
        expected = date.today() + timedelta(days=365)
        assert abs((nrd - expected).days) <= 1

    async def test_both_program_and_initiative_set_rejected(
        self, staff_client_impact, approved_indicator, sample_program
    ):
        payload = {
            "outcome_indicator_id": approved_indicator.id,
            "contributing_program_id": sample_program.id,
            "contributing_initiative_id": 999999,
            "mechanism_short": "x",
            "mechanism_detail": "x",
        }
        r = await staff_client_impact.post("/api/v1/impact/claims", json=payload)
        assert r.status_code == 422

    async def test_neither_program_nor_initiative_rejected(
        self, staff_client_impact, approved_indicator
    ):
        payload = {
            "outcome_indicator_id": approved_indicator.id,
            "mechanism_short": "x",
            "mechanism_detail": "x",
        }
        r = await staff_client_impact.post("/api/v1/impact/claims", json=payload)
        assert r.status_code == 422

    async def test_create_writes_audit_row(
        self,
        staff_client_impact,
        test_db,
        test_staff,
        approved_indicator,
        sample_program,
    ):
        payload = {
            "outcome_indicator_id": approved_indicator.id,
            "contributing_program_id": sample_program.id,
            "mechanism_short": "x",
            "mechanism_detail": "x",
        }
        r = await staff_client_impact.post("/api/v1/impact/claims", json=payload)
        assert r.status_code == 201
        claim_id = r.json()["id"]
        result = await test_db.execute(
            select(AuditLog).where(
                AuditLog.action == AuditAction.CLAIM_CREATED,
                AuditLog.admin_id == test_staff.id,
            )
        )
        rows = list(result.scalars().all())
        assert len(rows) == 1
        assert rows[0].details["resource_id"] == claim_id


class TestClaimPromote:
    async def test_promote_to_quasi_experimental_requires_board_link(
        self,
        director_client,
        test_db,
        approved_indicator,
        sample_program,
    ):
        claim = TheoryOfChangeClaim(
            outcome_indicator_id=approved_indicator.id,
            contributing_program_id=sample_program.id,
            mechanism_short="x",
            mechanism_detail="x",
            evidence_strength="theoretical",
            next_review_due=date.today() + timedelta(days=365),
        )
        test_db.add(claim)
        await test_db.commit()
        await test_db.refresh(claim)

        # Without board_decision_link_id → 422 for board-attested rung.
        r1 = await director_client.patch(
            f"/api/v1/impact/claims/{claim.id}/evidence",
            json={"evidence_strength": "quasi_experimental"},
        )
        assert r1.status_code == 422, r1.text
        rendered = str(r1.json().get("detail", r1.json()))
        assert "board_decision_link_id" in rendered

    async def test_promote_below_board_rung_no_link_needed(
        self,
        director_client,
        test_db,
        approved_indicator,
        sample_program,
    ):
        claim = TheoryOfChangeClaim(
            outcome_indicator_id=approved_indicator.id,
            contributing_program_id=sample_program.id,
            mechanism_short="x",
            mechanism_detail="x",
            evidence_strength="theoretical",
            next_review_due=date.today() + timedelta(days=365),
        )
        test_db.add(claim)
        await test_db.commit()
        await test_db.refresh(claim)

        r = await director_client.patch(
            f"/api/v1/impact/claims/{claim.id}/evidence",
            json={"evidence_strength": "outcome_correlated"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["evidence_strength"] == "outcome_correlated"


class TestClaimReview:
    async def test_review_advances_next_review_due(
        self, director_client, test_db, approved_indicator, sample_program
    ):
        claim = TheoryOfChangeClaim(
            outcome_indicator_id=approved_indicator.id,
            contributing_program_id=sample_program.id,
            mechanism_short="x",
            mechanism_detail="x",
            next_review_due=date.today() - timedelta(days=5),
        )
        test_db.add(claim)
        await test_db.commit()
        await test_db.refresh(claim)

        r = await director_client.post(
            f"/api/v1/impact/claims/{claim.id}/review",
            json={"notes": "Annual review — no changes."},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        nrd = date.fromisoformat(body["next_review_due"])
        assert nrd > date.today() + timedelta(days=360)


# ---------------------------------------------------------------------
# Feature-flag gate
# ---------------------------------------------------------------------


class TestFeatureFlagGate:
    async def test_router_404s_when_feature_off(self, test_db, test_staff):
        """When organization_features.impact_measurement_enabled is FALSE the
        router-level feature guard returns 404 (not 403) — consistent
        with L30's 'hidden feature' posture for org-disabled modules.
        """
        from httpx import ASGITransport, AsyncClient

        from app.api.v1.auth.helpers import get_current_user
        from app.core.database import get_db
        from app.main import app

        feat = OrganizationFeatures(impact_measurement_enabled=False)
        test_db.add(feat)
        await test_db.commit()
        await OrganizationFeaturesService.invalidate_cache()

        async def override_get_db():
            yield test_db

        async def override_get_current_user():
            return test_staff

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        app.state.setup_complete = True
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as ac:
                r = await ac.get("/api/v1/impact/indicators")
            assert r.status_code == 404
        finally:
            app.dependency_overrides.pop(get_db, None)
            app.dependency_overrides.pop(get_current_user, None)
