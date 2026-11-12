# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public certificate verification endpoint tests.

Covers the no-auth `/api/v1/learning/certificates/{cert_number}/verify`
endpoint that backs the patron-facing `/verify/:cert_number` page.

Companion to the broader generation/PDF flow in
`backend/tests/integration/test_certificate_generation.py` — the focus here
is the public-share path (invalid + valid lookup without an Authorization
header) plus the privacy-respecting `recipient_first_name` projection.
"""

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
async def _reset_test_engine_pool():
    """Match the dispose-on-exit pattern other public-endpoint tests use.

    Shared L30 test engine pool keeps PG connections alive across tests;
    each pytest-asyncio test gets a fresh event loop. Without dispose the
    next test sees a connection from a dead loop.
    """
    yield
    import tests.conftest as tc
    if tc._engine is not None:
        try:
            await tc._engine.dispose()
        except Exception:
            pass
        tc._engine = None
        tc._session_factory = None


VERIFY_URL = "/api/v1/learning/certificates/{cert_number}/verify"


async def _seed_certificate(test_db: AsyncSession) -> tuple[str, str, str]:
    """Insert a User + Course + Certificate. Returns (cert_number, first_name, course_title)."""
    from app.core.security import hash_password
    from app.models.learning import Certificate, Course, CourseLifecycleStage
    from app.models.user import User, UserRole

    suffix = uuid.uuid4().hex[:8]
    user = User(
        email=f"verify-{suffix}@example.com",
        password_hash=hash_password("VerifyPassword123!"),
        first_name="Ada",
        last_name="Lovelace",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    course = Course(
        title="Public Verify Test Course",
        description="Course used by the public-verify test.",
        access_level="patron",
        lifecycle_stage=CourseLifecycleStage.PUBLISHED,
        difficulty="beginner",
        estimated_minutes=20,
        quiz_passing_threshold=70,
        xp_reward=50,
    )
    test_db.add(course)
    await test_db.commit()
    await test_db.refresh(course)

    cert_number = f"LSC-{uuid.uuid4().hex[:8].upper()}"
    certificate = Certificate(
        user_id=user.id,
        course_id=course.id,
        certificate_number=cert_number,
        issued_at=datetime.now(timezone.utc),
    )
    test_db.add(certificate)
    await test_db.commit()

    return cert_number, user.first_name, course.title


async def test_verify_invalid_returns_404(client: AsyncClient):
    """Unknown cert_number → 404 with a clear detail message."""
    resp = await client.get(VERIFY_URL.format(cert_number="INVALID"))
    assert resp.status_code == 404, resp.text
    data = resp.json()
    error_message = data.get("detail") or data.get("error", {}).get("message", "")
    assert "not found" in error_message.lower()


async def test_verify_valid_no_auth(client: AsyncClient, test_db: AsyncSession):
    """A real cert_number resolves without an Authorization header.

    This is the share-link contract: the URL behind the QR on the PDF and
    behind /verify/:cert_number must be readable by an unauthenticated
    browser (LinkedIn, employer, etc.).
    """
    cert_number, first_name, course_title = await _seed_certificate(test_db)

    resp = await client.get(VERIFY_URL.format(cert_number=cert_number))
    assert resp.status_code == 200, resp.text

    data = resp.json()
    assert data["certificate_number"] == cert_number
    assert data["is_valid"] is True
    assert data["course_title"] == course_title
    # Privacy projection: first name is exposed for the public panel; the
    # legacy user_name field stays populated for back-compat with the authed
    # "My Certificates" list.
    assert data["recipient_first_name"] == first_name
    assert data["user_name"]  # non-empty
