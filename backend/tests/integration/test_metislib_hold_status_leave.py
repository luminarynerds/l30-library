# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the shared-catalog hold status + leave routes.

These let the ebook detail page show a persistent "you're #N / ready" state
and a "leave the queue" action. The leave route auto-detects catalog vs indie
holds (indie leaves by ebook id, catalog by hold id).
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user as _auth_dep
from app.services.metislib_errors import MetisLibNotFound


def _fake_patron(user_id=1):
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = "patron@example.com"
    user.role = UserRole.PATRON
    user.is_active = True
    return user


@pytest.fixture
def patron_auth():
    from app.main import app
    app.dependency_overrides[_auth_dep] = lambda: _fake_patron()
    yield
    app.dependency_overrides.pop(_auth_dep, None)


@pytest.mark.integration
@pytest.mark.asyncio
class TestHoldStatusAndLeave:
    async def test_status_reports_on_hold(self, client: AsyncClient, patron_auth):
        mock = AsyncMock()
        mock.hold_status = AsyncMock(return_value={
            "hold_id": 7, "position": 3, "total_waiting": 5, "status": "waiting",
        })
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.get("/api/v1/ebooks/5/hold/status")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["on_hold"] is True
        assert body["position"] == 3
        assert body["total_waiting"] == 5

    async def test_status_reports_not_on_hold(self, client: AsyncClient, patron_auth):
        mock = AsyncMock()
        mock.hold_status = AsyncMock(side_effect=MetisLibNotFound("no hold"))
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.get("/api/v1/ebooks/5/hold/status")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"on_hold": False}

    async def test_leave_catalog_hold_uses_hold_id(self, client: AsyncClient, patron_auth):
        mock = AsyncMock()
        mock.hold_status = AsyncMock(return_value={"hold_id": 42, "position": 1, "status": "waiting"})
        mock.cancel_hold = AsyncMock(return_value={"status": "cancelled"})
        mock.leave_indie_hold = AsyncMock()
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.delete("/api/v1/ebooks/5/hold")
        assert resp.status_code == 200, resp.text
        mock.cancel_hold.assert_awaited_once()
        assert mock.cancel_hold.await_args.args[0] == 42  # the hold id
        mock.leave_indie_hold.assert_not_called()

    async def test_leave_indie_hold_uses_ebook_id(self, client: AsyncClient, patron_auth):
        mock = AsyncMock()
        mock.hold_status = AsyncMock(return_value={
            "hold_id": 9, "position": 1, "status": "ready", "kind": "indie",
        })
        mock.leave_indie_hold = AsyncMock(return_value={"status": "left"})
        mock.cancel_hold = AsyncMock()
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.delete("/api/v1/ebooks/5/hold")
        assert resp.status_code == 200, resp.text
        # ebook id from the path (5), not the hold id.
        assert mock.leave_indie_hold.await_args.args[0] == 5
        mock.cancel_hold.assert_not_called()

    async def test_leave_without_hold_is_404(self, client: AsyncClient, patron_auth):
        mock = AsyncMock()
        mock.hold_status = AsyncMock(side_effect=MetisLibNotFound("no hold"))
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.delete("/api/v1/ebooks/5/hold")
        assert resp.status_code == 404, resp.text
