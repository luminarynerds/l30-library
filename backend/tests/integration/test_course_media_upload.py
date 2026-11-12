# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Integration tests for course thumbnail media upload endpoint."""
import io
import time
import pytest

from app.core.security import _TOKEN_VERIFY_CACHE, _get_token_hash, create_access_token
from tests.integration.test_admin_course_management import (  # noqa: F401
    test_admin_user,
    test_regular_user,
    test_course,
)

# Minimal valid 1x1 RGB PNG
_PNG = bytes.fromhex("89504e470d0a1a0a0000000d4948445200000001000000010802000000907753de0000000c49444154789c63f8cfc0000003010100c9fe92ef0000000049454e44ae426082")


def _auth(user) -> dict:
    """Create a Bearer token for user and pre-warm the in-memory revocation cache.

    Redis is unavailable in the test environment; is_token_revoked falls back
    to the in-memory cache and rejects unknown tokens fail-secure. Pre-warming
    makes the freshly-minted test token pass revocation without Redis.
    """
    token = create_access_token(
        subject=str(user.id),
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
    )
    _TOKEN_VERIFY_CACHE[_get_token_hash(token)] = time.monotonic()
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
class TestCourseMediaUpload:
    async def test_admin_uploads_thumbnail(self, client, test_admin_user, test_course):
        """Admin can upload a valid image and gets 201 with media_type + url."""
        resp = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/media?media_type=thumbnail",
            files={"file": ("thumb.png", io.BytesIO(_PNG), "image/png")},
            headers=_auth(test_admin_user),
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["media_type"] == "thumbnail"
        assert body["url"]

    async def test_rejects_non_image(self, client, test_admin_user, test_course):
        """Non-image file type is rejected with 400."""
        resp = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/media?media_type=thumbnail",
            files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
            headers=_auth(test_admin_user),
        )
        assert resp.status_code == 400, resp.text

    async def test_patron_forbidden(self, client, test_regular_user, test_course):
        """Patron gets 403 - endpoint requires staff or above."""
        resp = await client.post(
            f"/api/v1/learning/courses/{test_course.id}/media?media_type=thumbnail",
            files={"file": ("thumb.png", io.BytesIO(_PNG), "image/png")},
            headers=_auth(test_regular_user),
        )
        assert resp.status_code == 403, resp.text

    async def test_missing_course_404(self, client, test_admin_user):
        """Nonexistent course_id returns 404."""
        resp = await client.post(
            "/api/v1/learning/courses/99999999/media?media_type=thumbnail",
            files={"file": ("thumb.png", io.BytesIO(_PNG), "image/png")},
            headers=_auth(test_admin_user),
        )
        assert resp.status_code == 404, resp.text
