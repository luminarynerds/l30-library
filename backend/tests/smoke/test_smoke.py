# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""L30 smoke suite -- broad + shallow.

One happy-path assertion per major flow ("is this surface alive?") across four
groups: core patron+circ, staff operations, programs+reading, content surfaces.
Plus the ebook borrow invariant as the sharp edge (regression for the
shared-catalog double-checkout).

Runs in-process against the fresh l30_test DB via the project pytest harness.
Empty DB is fine: every endpoint here is a list/collection that should 200 with
an empty payload. If a flow's primary endpoint stops serving, exactly one smoke
test goes red and names it.
"""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock

from app.models.user import User, UserRole
from app.api.v1.auth import get_current_user as _auth_dep

pytestmark = [pytest.mark.smoke, pytest.mark.asyncio]


# --------------------------------------------------------------------------
# Group 1: core patron + circulation
# --------------------------------------------------------------------------
class TestSmokeCore:
    async def test_health(self, public_client):
        resp = await public_client.get("/api/v1/health")
        assert resp.status_code == 200

    async def test_catalog_search(self, public_client):
        resp = await public_client.get("/api/v1/catalog/search", params={"q": "the"})
        assert resp.status_code == 200

    async def test_circulation_checkouts(self, staff_client):
        resp = await staff_client.get("/api/v1/circulation/checkouts")
        assert resp.status_code == 200

    async def test_circulation_holds(self, staff_client):
        resp = await staff_client.get("/api/v1/circulation/holds")
        assert resp.status_code == 200

    async def test_patron_account(self, patron_client):
        resp = await patron_client.get("/api/v1/patron/account")
        assert resp.status_code == 200

    async def test_ebook_borrow_invariant(self, client):
        """Sharp edge: borrowing a shared-catalog ebook you already have out is rejected."""
        fake = MagicMock(spec=User)
        fake.id = 1
        fake.role = UserRole.PATRON
        fake.is_active = True

        from app.main import app
        app.dependency_overrides[_auth_dep] = lambda: fake
        mock = AsyncMock()
        mock.get_patron_checkouts = AsyncMock(return_value=[{"ebook_id": 1}])
        mock.checkout = AsyncMock(return_value={"access_id": 9})
        try:
            with patch("app.api.v1.metislib_ebooks._require_metislib", return_value=mock), \
                    patch("app.api.v1.metislib_ebooks.log_ebook_event", new_callable=AsyncMock):
                resp = await client.post("/api/v1/ebooks/1/borrow")
            assert resp.status_code == 409
            mock.checkout.assert_not_called()
        finally:
            app.dependency_overrides.pop(_auth_dep, None)


# --------------------------------------------------------------------------
# Group 2: staff operations
# --------------------------------------------------------------------------
class TestSmokeStaff:
    async def test_acquisition_vendors(self, staff_client):
        resp = await staff_client.get("/api/v1/acquisition/vendors")
        assert resp.status_code == 200

    async def test_acquisition_purchase_orders(self, staff_client):
        resp = await staff_client.get("/api/v1/acquisition/purchase-orders")
        assert resp.status_code == 200

    async def test_financial_revenue_report(self, admin_client):
        resp = await admin_client.get("/api/v1/financial/reports/revenue-summary")
        assert resp.status_code == 200

    async def test_board_reports(self, admin_client):
        resp = await admin_client.get("/api/v1/board/reports")
        assert resp.status_code == 200


# --------------------------------------------------------------------------
# Group 3: programs + reading
# --------------------------------------------------------------------------
class TestSmokePrograms:
    async def test_reading_activity(self, patron_client):
        resp = await patron_client.get("/api/v1/reading-activity")
        assert resp.status_code == 200

    async def test_reading_lists_me(self, patron_client):
        resp = await patron_client.get("/api/v1/reading-lists/me")
        assert resp.status_code == 200

    async def test_book_clubs(self, public_client):
        resp = await public_client.get("/api/v1/book-clubs")
        assert resp.status_code == 200

    async def test_program_partners(self, staff_client):
        resp = await staff_client.get("/api/v1/program-partners")
        assert resp.status_code == 200


# --------------------------------------------------------------------------
# Group 4: content surfaces
# --------------------------------------------------------------------------
class TestSmokeContent:
    async def test_blog_posts(self, public_client):
        resp = await public_client.get("/api/v1/blog/posts")
        assert resp.status_code == 200

    async def test_blog_feed(self, public_client):
        resp = await public_client.get("/api/v1/blog/feed")
        assert resp.status_code == 200

    async def test_public_records_disclosure_log(self, public_client):
        resp = await public_client.get("/api/v1/public-records/public/disclosure-log")
        assert resp.status_code == 200

    async def test_staff_knowledge_articles(self, staff_client):
        resp = await staff_client.get("/api/v1/staff-knowledge/articles")
        assert resp.status_code == 200
