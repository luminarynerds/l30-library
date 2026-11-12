# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for MetisLib AMA proxy endpoints (/api/v1/amas/*).

AMA routes are gated by the ama_enabled feature flag and proxy to MetisLib.
Tests mock the feature guard, MetisLib client, and auth as needed.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user as _auth_dep


def _fake_user(user_id=1, role=UserRole.PATRON):
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = "patron@example.com"
    user.first_name = "Test"
    user.last_name = "Patron"
    user.role = role
    user.is_active = True
    return user


def _fake_staff(user_id=2):
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = "staff@example.com"
    user.first_name = "Staff"
    user.last_name = "Member"
    user.role = UserRole.STAFF
    user.is_active = True
    return user


def _mock_ama_client():
    """Build a mock MetisLib client with AMA method stubs."""
    mock = AsyncMock()
    mock.ama_list_sessions.return_value = {
        "items": [
            {"id": 1, "title": "AMA with Sage Holloway", "status": "upcoming"},
            {"id": 2, "title": "AMA with Ren Takahashi", "status": "live"},
        ],
        "total": 2, "page": 1, "pages": 1,
    }
    mock.ama_get_session_detail.return_value = {
        "id": 1, "title": "AMA with Sage Holloway", "status": "upcoming",
        "questions": [], "total_questions": 0,
    }
    mock.ama_submit_question.return_value = {
        "id": 101, "question_text": "How do you find inspiration?",
        "status": "pending_moderation", "upvotes": 0,
    }
    mock.ama_toggle_upvote.return_value = {"id": 101, "upvotes": 1, "patron_has_upvoted": True}
    mock.ama_get_my_questions.return_value = {
        "items": [{"id": 101, "question_text": "How do you find inspiration?", "status": "approved"}],
        "total": 1,
    }
    mock.ama_create_session.return_value = {"id": 3, "title": "New AMA Session", "status": "upcoming"}
    mock.ama_update_session.return_value = {"id": 1, "title": "Updated AMA"}
    mock.ama_transition_status.return_value = {"id": 1, "status": "live"}
    mock.ama_delete_session.return_value = None
    mock.ama_get_moderation_queue.return_value = {
        "items": [{"id": 102, "question_text": "Flagged question", "status": "pending_moderation"}],
        "total": 1,
    }
    mock.ama_moderate_question.return_value = {"id": 102, "status": "approved"}
    mock.ama_toggle_feature.return_value = {"id": 101, "is_featured": True}
    return mock


@pytest.fixture
def bypass_ama_guard():
    """Bypass the ama_enabled feature guard for testing."""
    with patch(
        "app.api.v1.feature_guards._make_feature_guard",
    ):
        # Directly override the guard dependency
        from app.api.v1.feature_guards import require_ama_enabled
        from app.main import app

        async def _noop():
            pass

        app.dependency_overrides[require_ama_enabled] = _noop
        yield
        app.dependency_overrides.pop(require_ama_enabled, None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAMAPublic:
    """Public AMA endpoints (no auth)."""

    async def test_list_sessions(self, client: AsyncClient, bypass_ama_guard):
        mock = _mock_ama_client()
        with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
            resp = await client.get("/api/v1/amas/sessions")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert len(data["items"]) == 2

    async def test_list_sessions_with_status_filter(self, client: AsyncClient, bypass_ama_guard):
        mock = _mock_ama_client()
        with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
            resp = await client.get("/api/v1/amas/sessions", params={"status": "live"})
        assert resp.status_code == 200
        mock.ama_list_sessions.assert_called_once_with(status="live", page=1, limit=20)

    async def test_get_session_detail_unauthenticated(self, client: AsyncClient, bypass_ama_guard):
        mock = _mock_ama_client()
        with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
            resp = await client.get("/api/v1/amas/sessions/1")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 1
        mock.ama_get_session_detail.assert_called_once_with(1, patron_hash=None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAMAPatron:
    """Patron AMA endpoints (auth required)."""

    async def test_submit_question_requires_auth(self, client: AsyncClient, bypass_ama_guard):
        resp = await client.post("/api/v1/amas/sessions/1/questions", json={
            "question_text": "Test question",
        })
        assert resp.status_code in (401, 403)

    async def test_submit_question(self, client: AsyncClient, bypass_ama_guard):
        fake_user = _fake_user()
        mock = _mock_ama_client()
        from app.main import app
        app.dependency_overrides[_auth_dep] = lambda: fake_user
        try:
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.post(
                    "/api/v1/amas/sessions/1/questions",
                    json={"question_text": "How do you find inspiration?"},
                )
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == 101
            assert data["status"] == "pending_moderation"
            call_args = mock.ama_submit_question.call_args
            assert call_args[0][1] is not None  # patron_hash
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_toggle_upvote(self, client: AsyncClient, bypass_ama_guard):
        fake_user = _fake_user()
        mock = _mock_ama_client()
        from app.main import app
        app.dependency_overrides[_auth_dep] = lambda: fake_user
        try:
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.post("/api/v1/amas/questions/101/upvote")
            assert resp.status_code == 200
            assert resp.json()["upvotes"] == 1
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_get_my_questions(self, client: AsyncClient, bypass_ama_guard):
        fake_user = _fake_user()
        mock = _mock_ama_client()
        from app.main import app
        app.dependency_overrides[_auth_dep] = lambda: fake_user
        try:
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.get("/api/v1/amas/sessions/1/my-questions")
            assert resp.status_code == 200
            assert resp.json()["total"] == 1
        finally:
            app.dependency_overrides.pop(_auth_dep, None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAMAStaff:
    """Staff AMA endpoints (staff role required)."""

    def _staff_override(self):
        fake_staff = _fake_staff()
        from app.main import app
        app.dependency_overrides[_auth_dep] = lambda: fake_staff
        return app, fake_staff

    async def test_create_session_requires_staff(self, client: AsyncClient, bypass_ama_guard):
        fake_patron = _fake_user(role=UserRole.PATRON)
        from app.main import app
        app.dependency_overrides[_auth_dep] = lambda: fake_patron
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.post("/api/v1/amas/sessions", json={"title": "New AMA"})
            assert resp.status_code == 403
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_create_session_as_staff(self, client: AsyncClient, bypass_ama_guard):
        app, _ = self._staff_override()
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.post("/api/v1/amas/sessions", json={"title": "New AMA"})
            assert resp.status_code == 201
            assert resp.json()["id"] == 3
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_update_session_as_staff(self, client: AsyncClient, bypass_ama_guard):
        app, _ = self._staff_override()
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.put("/api/v1/amas/sessions/1", json={"title": "Updated"})
            assert resp.status_code == 200
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_transition_session_status(self, client: AsyncClient, bypass_ama_guard):
        app, _ = self._staff_override()
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.put("/api/v1/amas/sessions/1/status", json={"status": "live"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "live"
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_delete_session(self, client: AsyncClient, bypass_ama_guard):
        app, _ = self._staff_override()
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.delete("/api/v1/amas/sessions/1")
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_moderation_queue(self, client: AsyncClient, bypass_ama_guard):
        app, _ = self._staff_override()
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.get("/api/v1/amas/sessions/1/moderate")
            assert resp.status_code == 200
            assert resp.json()["total"] == 1
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_moderate_question(self, client: AsyncClient, bypass_ama_guard):
        app, _ = self._staff_override()
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.post("/api/v1/amas/questions/102/moderate", json={"action": "approve"})
            assert resp.status_code == 200
            assert resp.json()["status"] == "approved"
        finally:
            app.dependency_overrides.pop(_auth_dep, None)

    async def test_toggle_featured(self, client: AsyncClient, bypass_ama_guard):
        app, _ = self._staff_override()
        try:
            mock = _mock_ama_client()
            with patch("app.api.v1.metislib_amas.get_metislib_client", return_value=mock):
                resp = await client.post("/api/v1/amas/questions/101/feature")
            assert resp.status_code == 200
            assert resp.json()["is_featured"] is True
        finally:
            app.dependency_overrides.pop(_auth_dep, None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestAMAServiceDisabled:
    """Test behavior when MetisLib is disabled."""

    async def test_list_returns_503_when_disabled(self, client: AsyncClient, bypass_ama_guard):
        from app.core.config import get_settings
        original = get_settings()
        with patch.object(original, "metislib_enabled", False):
            resp = await client.get("/api/v1/amas/sessions")
        assert resp.status_code == 503
