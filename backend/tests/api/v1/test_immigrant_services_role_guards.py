# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests for immigrant-services router role guards (issue #438).

The 2026-05-13 audit found zero `require_staff` calls across the 26 write
endpoints in this namespace. This test asserts a patron token gets 403 on a
representative write endpoint, locking that fix in.
"""

import pytest


@pytest.mark.asyncio
async def test_patron_cannot_create_esl_class(test_db, test_patron):
    """A PATRON-role user must not be able to POST a new ESL class."""
    from httpx import AsyncClient, ASGITransport
    from app.core.database import get_db
    from app.api.v1.auth import get_current_user
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
            response = await ac.post(
                "/api/v1/immigrant-services/esl-classes",
                json={
                    "title": "Beginner ESL",
                    "level": "beginner",
                    "start_date": "2026-06-01",
                    "end_date": "2026-08-01",
                },
            )
            assert response.status_code == 403, (
                f"Expected 403 for patron POST to esl-classes, got {response.status_code}: "
                f"{response.text}"
            )
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user, None)
