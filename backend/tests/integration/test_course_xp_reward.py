# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression test: xp_reward must be accepted on PUT /courses/{id}."""
import time
import pytest

from app.core.security import _TOKEN_VERIFY_CACHE, _get_token_hash, create_access_token
from tests.integration.test_admin_course_management import (  # noqa: F401
    test_admin_user,
    test_regular_user,
    test_course,
)


def _auth(user) -> dict:
    """Create a Bearer token and pre-warm the in-memory revocation cache."""
    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )
    _TOKEN_VERIFY_CACHE[_get_token_hash(token)] = time.monotonic()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
class TestCourseXpReward:
    async def test_xp_reward_accepted_on_put(self, client, test_admin_user, test_course):
        """PUT /courses/{id} with xp_reward must return 200, not 422.

        Before the schema fix (adding xp_reward to CourseUpdate), this
        request was rejected with 422 Unprocessable Entity because the field
        was unknown/extra and StrictInputSchema forbids extra fields.
        """
        headers = _auth(test_admin_user)

        # PUT with xp_reward — this is the failing request pre-fix.
        resp = await client.put(
            f"/api/v1/learning/courses/{test_course.id}",
            json={"title": test_course.title, "xp_reward": 250},
            headers=headers,
        )
        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"

        # GET and confirm the value persisted.
        resp = await client.get(
            f"/api/v1/learning/courses/{test_course.id}",
            headers=headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["xp_reward"] == 250
