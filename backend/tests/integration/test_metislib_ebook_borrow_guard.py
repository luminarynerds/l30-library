# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Guard tests for shared-catalog ebook borrow/hold idempotency.

The MetisLib coop does not dedupe checkouts and L30 keeps no local state for
shared-catalog borrows, so a patron who already has an ebook out could borrow
it again (or place a hold on what they already hold). These tests pin the
guard that rejects those cases. Regression for the double-checkout bug.

The MetisLib client is patched directly (the METISLIB_MOCK client is not
present in this tree), so these assert L30's own guard logic, not the coop.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient

from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user as _auth_dep


def _fake_patron(user_id=1):
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = "patron@example.com"
    user.role = UserRole.PATRON
    user.is_active = True
    return user


@pytest.fixture
def patron_auth():
    """Override auth to a fake patron and stub out ebook-event logging."""
    from app.main import app
    app.dependency_overrides[_auth_dep] = lambda: _fake_patron()
    with patch("app.api.v1.metislib_ebooks.log_ebook_event", new_callable=AsyncMock):
        yield
    app.dependency_overrides.pop(_auth_dep, None)


def _mock_client(active_checkouts):
    client = AsyncMock()
    client.get_patron_checkouts = AsyncMock(return_value=active_checkouts)
    client.checkout = AsyncMock(return_value={"access_id": 99, "title": "X", "author": "Y"})
    client.place_hold = AsyncMock(return_value={"hold_id": 7, "position": 1})
    return client


@pytest.mark.integration
@pytest.mark.asyncio
class TestEbookBorrowGuard:
    async def test_borrow_rejected_when_already_checked_out(self, client: AsyncClient, patron_auth):
        mock = _mock_client([{"ebook_id": 1, "title": "X"}])
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.post("/api/v1/ebooks/1/borrow")
        assert resp.status_code == 409
        mock.checkout.assert_not_called()

    async def test_borrow_succeeds_when_not_checked_out(self, client: AsyncClient, patron_auth):
        mock = _mock_client([])
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.post("/api/v1/ebooks/1/borrow")
        assert resp.status_code == 200
        mock.checkout.assert_awaited_once()

    async def test_hold_rejected_when_already_checked_out(self, client: AsyncClient, patron_auth):
        mock = _mock_client([{"ebook_id": 5}])
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.post("/api/v1/ebooks/5/hold")
        assert resp.status_code == 409
        mock.place_hold.assert_not_called()

    async def test_hold_succeeds_when_not_checked_out(self, client: AsyncClient, patron_auth):
        mock = _mock_client([])
        with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock):
            resp = await client.post("/api/v1/ebooks/5/hold")
        assert resp.status_code == 200
        mock.place_hold.assert_awaited_once()
