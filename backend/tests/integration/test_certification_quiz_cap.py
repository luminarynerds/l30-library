# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests for the 3-attempt cap on makerspace certification quizzes.

After 3 failed quiz attempts the certification status becomes expired.
A passing attempt before the cap activates the certification normally.
An expired certification is rejected before reaching the service layer.
"""

from datetime import datetime, timezone

import pytest

from app.models.makerspace import (
    CertificationStatus,
    MakerspaceCertification,
    MakerspaceCertificationType,
)
from app.services.makerspace.certification_service import CertificationService

PASSING_SCORE = 80
FAILING_SCORE = 70


@pytest.fixture
async def cert_type(test_db):
    ct = MakerspaceCertificationType(
        name="Laser Safety Quiz Cap Test",
        passing_score=PASSING_SCORE,
        validity_months=12,
        is_active=True,
    )
    test_db.add(ct)
    await test_db.commit()
    await test_db.refresh(ct)
    return ct


@pytest.fixture
async def pending_cert(test_db, test_patron, cert_type):
    cert = MakerspaceCertification(
        user_id=test_patron.id,
        certification_type_id=cert_type.id,
        status=CertificationStatus.pending,
        training_completed_at=datetime.now(timezone.utc),
    )
    test_db.add(cert)
    await test_db.commit()
    await test_db.refresh(cert)
    return cert


@pytest.fixture
async def patron_client(test_db, test_patron):
    from httpx import AsyncClient, ASGITransport
    from app.api.v1.auth.helpers import get_current_user
    from app.core.database import get_db
    from app.main import app

    async def override_get_db():
        yield test_db

    async def override_get_current_user():
        return test_patron

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


class TestQuizAttemptCap:
    """CertificationService.submit_quiz enforces a 3-attempt cap."""

    async def test_first_failed_attempt_stays_pending(self, test_db, pending_cert):
        cert, passed = await CertificationService.submit_quiz(test_db, pending_cert, FAILING_SCORE)
        assert not passed
        assert cert.status == CertificationStatus.pending
        assert cert.quiz_attempts == 1

    async def test_second_failed_attempt_stays_pending(self, test_db, pending_cert):
        await CertificationService.submit_quiz(test_db, pending_cert, FAILING_SCORE)
        cert, passed = await CertificationService.submit_quiz(test_db, pending_cert, FAILING_SCORE)
        assert not passed
        assert cert.status == CertificationStatus.pending
        assert cert.quiz_attempts == 2

    async def test_third_failed_attempt_expires_certification(self, test_db, pending_cert):
        await CertificationService.submit_quiz(test_db, pending_cert, FAILING_SCORE)
        await CertificationService.submit_quiz(test_db, pending_cert, FAILING_SCORE)
        cert, passed = await CertificationService.submit_quiz(test_db, pending_cert, FAILING_SCORE)
        assert not passed
        assert cert.status == CertificationStatus.expired
        assert cert.quiz_attempts == 3

    async def test_passing_attempt_activates_certification(self, test_db, pending_cert):
        cert, passed = await CertificationService.submit_quiz(test_db, pending_cert, PASSING_SCORE)
        assert passed
        assert cert.status == CertificationStatus.active
        assert cert.certified_at is not None
        assert cert.quiz_attempts == 1

    async def test_pass_after_one_failure_activates_certification(self, test_db, pending_cert):
        await CertificationService.submit_quiz(test_db, pending_cert, FAILING_SCORE)
        cert, passed = await CertificationService.submit_quiz(test_db, pending_cert, PASSING_SCORE)
        assert passed
        assert cert.status == CertificationStatus.active
        assert cert.quiz_attempts == 2


class TestExpiredCertRouteGate:
    """Expired certification is rejected at the route layer (status != pending check)."""

    async def test_expired_cert_submit_quiz_returns_400(
        self, patron_client, test_db, test_patron, cert_type
    ):
        expired_cert = MakerspaceCertification(
            user_id=test_patron.id,
            certification_type_id=cert_type.id,
            status=CertificationStatus.expired,
            training_completed_at=datetime.now(timezone.utc),
        )
        test_db.add(expired_cert)
        await test_db.commit()
        await test_db.refresh(expired_cert)

        resp = await patron_client.post(
            f"/api/v1/makerspace/certifications/{expired_cert.id}/submit-quiz",
            json={"answers": {"q1": 1}},
        )
        assert resp.status_code == 400
        # L30 wraps HTTPException as {"error": {"message": "..."}}
        message = resp.json().get("error", {}).get("message", "")
        assert "not pending" in message.lower()
