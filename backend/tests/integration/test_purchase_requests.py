# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for patron purchase request API endpoints.

Tests the full request/response cycle for:
- Patron: submit, list, view, cancel requests
- Staff: review queue, approve, decline, bulk ops
- Staff: link-to-order, mark-received
- Staff: fulfillment stats
- Decline reason template CRUD
- Duplicate detection
- Authorization checks
"""

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token
from app.models.catalog import CatalogItem, ItemStatus
from app.models.purchase_request import (
    DeclineReasonTemplate,
    PatronPurchaseRequest,
    PurchaseRequestStatus,
    RequestMaterialType,
)
from app.models.user import User, UserRole


# ============ Helpers ============


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


def patron_token(user: User) -> dict:
    """Build Authorization headers for a user."""
    token = create_access_token(subject=str(user.id), email=user.email, role=user.role.value)
    return {"Authorization": f"Bearer {token}"}


def auth_headers(user: User) -> dict:
    return patron_token(user)


# ============ Fixtures ============


@pytest.fixture
async def catalog_book(test_db):
    """A catalog item to trigger duplicate detection."""
    item = CatalogItem(
        title="The Great Gatsby",
        author="F. Scott Fitzgerald",
        isbn="9780743273565",
        description="A classic novel",
        status=ItemStatus.available,
        call_number="FIC-GAT-001",
        publication_year=1925,
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)
    return item


@pytest.fixture
async def purchase_request(test_db, test_patron):
    """A pre-existing pending purchase request."""
    req = PatronPurchaseRequest(
        patron_id=test_patron.id,
        title="New Science Book",
        author="Jane Doe",
        material_type=RequestMaterialType.BOOK,
        status=PurchaseRequestStatus.PENDING,
        duplicate_check_done=True,
    )
    test_db.add(req)
    await test_db.commit()
    await test_db.refresh(req)
    return req


@pytest.fixture
async def approved_request(test_db, test_patron, test_staff):
    """An approved purchase request ready for ordering."""
    req = PatronPurchaseRequest(
        patron_id=test_patron.id,
        title="Advanced Mathematics",
        author="Prof Smith",
        material_type=RequestMaterialType.BOOK,
        status=PurchaseRequestStatus.APPROVED,
        reviewed_by_id=test_staff.id,
        duplicate_check_done=True,
    )
    test_db.add(req)
    await test_db.commit()
    await test_db.refresh(req)
    return req


@pytest.fixture
async def purchase_order(test_db, test_staff):
    """A minimal real PurchaseOrder row. patron_purchase_requests.purchase_order_id
    has a FK to purchase_orders.id -- link-order/mark-received need a row
    that actually exists, a literal int no longer satisfies the constraint."""
    from app.models.acquisition import PurchaseOrder

    po = PurchaseOrder(
        po_number="PO-TEST-0001",
        created_by_id=test_staff.id,
    )
    test_db.add(po)
    await test_db.commit()
    await test_db.refresh(po)
    return po


@pytest.fixture
async def decline_template(test_db, test_staff):
    """A pre-existing decline reason template."""
    tpl = DeclineReasonTemplate(
        label="Budget Constraints",
        message="We are unable to fulfill this request due to budget constraints this fiscal year.",
        created_by_id=test_staff.id,
    )
    test_db.add(tpl)
    await test_db.commit()
    await test_db.refresh(tpl)
    return tpl


# ============ Patron: Submit ============


class TestPatronSubmitRequest:
    """Tests for POST /api/v1/purchase-requests"""

    @pytest.mark.asyncio
    async def test_submit_minimal(self, client: AsyncClient, test_patron):
        """Patron can submit a request with just a title."""
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={"title": "A Brand New Book"},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["title"] == "A Brand New Book"
        assert data["status"] == "pending"
        assert data["material_type"] == "book"
        assert data["id"] is not None

    @pytest.mark.asyncio
    async def test_submit_full_details(self, client: AsyncClient, test_patron):
        """Patron can submit a request with all optional fields."""
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={
                "title": "Deep Learning with Python",
                "author": "François Chollet",
                "isbn": "9781617294433",
                "material_type": "book",
                "publisher": "Manning",
                "publication_year": 2021,
                "patron_notes": "Needed for my ML studies",
            },
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["author"] == "François Chollet"
        assert data["isbn"] == "9781617294433"
        assert data["publisher"] == "Manning"
        assert data["publication_year"] == 2021
        assert data["patron_notes"] == "Needed for my ML studies"

    @pytest.mark.asyncio
    async def test_submit_duplicate_request_blocked(
        self, client: AsyncClient, test_patron, purchase_request
    ):
        """Submitting a request for the same title while one is pending is blocked."""
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={"title": "New Science Book", "author": "Jane Doe"},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 409
        assert "already have an active request" in _error_detail(resp)

    @pytest.mark.asyncio
    async def test_submit_requires_auth(self, client: AsyncClient):
        """Unauthenticated users cannot submit requests."""
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={"title": "Some Book"},
        )
        assert resp.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_submit_with_duplicate_detection(
        self, client: AsyncClient, test_patron, catalog_book
    ):
        """Submitting a request for an item already in the catalog flags the duplicate."""
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={"title": "The Great Gatsby", "author": "F. Scott Fitzgerald"},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 201
        # The request is still created but flagged internally

    @pytest.mark.asyncio
    async def test_submit_different_material_types(self, client: AsyncClient, test_patron):
        """Requests can specify various material types."""
        for mat_type in ["audiobook", "ebook", "dvd", "cd", "magazine", "other"]:
            resp = await client.post(
                "/api/v1/purchase-requests",
                json={"title": f"Test {mat_type} item", "material_type": mat_type},
                headers=auth_headers(test_patron),
            )
            assert resp.status_code == 201, f"Failed for material_type={mat_type}"
            assert resp.json()["material_type"] == mat_type


# ============ Patron: List My Requests ============


class TestPatronListRequests:
    """Tests for GET /api/v1/purchase-requests/mine"""

    @pytest.mark.asyncio
    async def test_list_empty(self, client: AsyncClient, test_patron):
        """Returns empty list when patron has no requests."""
        resp = await client.get(
            "/api/v1/purchase-requests/mine",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_own_requests(self, client: AsyncClient, test_patron, purchase_request):
        """Patron sees their own requests."""
        resp = await client.get(
            "/api/v1/purchase-requests/mine",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["items"][0]["id"] == purchase_request.id

    @pytest.mark.asyncio
    async def test_list_filter_by_status(self, client: AsyncClient, test_patron, purchase_request):
        """Filter requests by status."""
        resp = await client.get(
            "/api/v1/purchase-requests/mine?status=pending",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        resp = await client.get(
            "/api/v1/purchase-requests/mine?status=approved",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_does_not_show_other_users(
        self, client: AsyncClient, test_staff, purchase_request
    ):
        """Staff user doesn't see patron's requests via /mine endpoint."""
        resp = await client.get(
            "/api/v1/purchase-requests/mine",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# ============ Patron: Get Single Request ============


class TestPatronGetRequest:
    """Tests for GET /api/v1/purchase-requests/mine/{id}"""

    @pytest.mark.asyncio
    async def test_get_own_request(self, client: AsyncClient, test_patron, purchase_request):
        """Patron can view their own request details."""
        resp = await client.get(
            f"/api/v1/purchase-requests/mine/{purchase_request.id}",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == purchase_request.id
        assert data["title"] == "New Science Book"

    @pytest.mark.asyncio
    async def test_cannot_view_others_request(
        self, client: AsyncClient, test_staff, purchase_request
    ):
        """Users cannot view another user's request via /mine endpoint."""
        resp = await client.get(
            f"/api/v1/purchase-requests/mine/{purchase_request.id}",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_get_nonexistent(self, client: AsyncClient, test_patron):
        """404 for nonexistent request."""
        resp = await client.get(
            "/api/v1/purchase-requests/mine/99999",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 404


# ============ Patron: Cancel ============


class TestPatronCancelRequest:
    """Tests for POST /api/v1/purchase-requests/mine/{id}/cancel"""

    @pytest.mark.asyncio
    async def test_cancel_pending(self, client: AsyncClient, test_patron, purchase_request):
        """Patron can cancel a pending request."""
        resp = await client.post(
            f"/api/v1/purchase-requests/mine/{purchase_request.id}/cancel",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cannot_cancel_approved(self, client: AsyncClient, test_patron, approved_request):
        """Cannot cancel an already-approved request."""
        resp = await client.post(
            f"/api/v1/purchase-requests/mine/{approved_request.id}/cancel",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 400
        assert "Cannot cancel" in _error_detail(resp)

    @pytest.mark.asyncio
    async def test_cannot_cancel_others(self, client: AsyncClient, test_staff, purchase_request):
        """Cannot cancel another user's request."""
        resp = await client.post(
            f"/api/v1/purchase-requests/mine/{purchase_request.id}/cancel",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 403


# ============ Patron: Duplicate Check ============


class TestDuplicateCheck:
    """Tests for GET /api/v1/purchase-requests/check-duplicate"""

    @pytest.mark.asyncio
    async def test_no_duplicate(self, client: AsyncClient, test_patron):
        """No duplicate found for a unique title."""
        resp = await client.get(
            "/api/v1/purchase-requests/check-duplicate?title=Some Unique Book",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_duplicate"] is False
        assert data["catalog_item_id"] is None

    @pytest.mark.asyncio
    async def test_duplicate_by_isbn(self, client: AsyncClient, test_patron, catalog_book):
        """Duplicate detected via ISBN match."""
        resp = await client.get(
            "/api/v1/purchase-requests/check-duplicate?title=Gatsby&isbn=9780743273565",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_duplicate"] is True
        assert data["catalog_item_id"] == catalog_book.id
        assert data["match_type"] == "isbn"

    @pytest.mark.asyncio
    async def test_duplicate_by_title_author(self, client: AsyncClient, test_patron, catalog_book):
        """Duplicate detected via case-insensitive title+author match."""
        resp = await client.get(
            "/api/v1/purchase-requests/check-duplicate?title=the great gatsby&author=f. scott fitzgerald",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_duplicate"] is True
        assert data["catalog_item_id"] == catalog_book.id


# ============ Staff: Review Queue ============


class TestStaffReviewQueue:
    """Tests for GET /api/v1/purchase-requests/queue"""

    @pytest.mark.asyncio
    async def test_queue_requires_staff(self, client: AsyncClient, test_patron):
        """Patrons cannot access the review queue."""
        resp = await client.get(
            "/api/v1/purchase-requests/queue",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_queue_lists_all_requests(
        self, client: AsyncClient, test_staff, purchase_request
    ):
        """Staff can see all requests in queue."""
        resp = await client.get(
            "/api/v1/purchase-requests/queue",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(r["id"] == purchase_request.id for r in data["items"])

    @pytest.mark.asyncio
    async def test_queue_filter_by_status(self, client: AsyncClient, test_staff, purchase_request):
        """Staff can filter queue by status."""
        resp = await client.get(
            "/api/v1/purchase-requests/queue?status=pending",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 1

        resp = await client.get(
            "/api/v1/purchase-requests/queue?status=received",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_queue_includes_patron_name(
        self, client: AsyncClient, test_staff, purchase_request
    ):
        """Staff view includes patron_name."""
        resp = await client.get(
            "/api/v1/purchase-requests/queue",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        pr = next(r for r in items if r["id"] == purchase_request.id)
        assert pr["patron_name"] is not None


# ============ Staff: Get Single Request ============


class TestStaffGetRequest:
    """Tests for GET /api/v1/purchase-requests/queue/{id}"""

    @pytest.mark.asyncio
    async def test_get_staff_view(self, client: AsyncClient, test_staff, purchase_request):
        """Staff can view full details of any request."""
        resp = await client.get(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == purchase_request.id
        assert "patron_id" in data
        assert "duplicate_check_done" in data

    @pytest.mark.asyncio
    async def test_staff_get_nonexistent(self, client: AsyncClient, test_staff):
        """404 for nonexistent request in staff view."""
        resp = await client.get(
            "/api/v1/purchase-requests/queue/99999",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_patron_cannot_access_staff_view(
        self, client: AsyncClient, test_patron, purchase_request
    ):
        """Patrons cannot use the staff endpoint."""
        resp = await client.get(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 403


# ============ Staff: Approve ============


class TestStaffApprove:
    """Tests for POST /api/v1/purchase-requests/queue/{id}/approve"""

    @pytest.mark.asyncio
    async def test_approve_pending(self, client: AsyncClient, test_staff, purchase_request):
        """Staff can approve a pending request."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/approve",
            json={},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "approved"
        assert data["reviewed_by_id"] == test_staff.id

    @pytest.mark.asyncio
    async def test_approve_with_notes(self, client: AsyncClient, test_staff, purchase_request):
        """Staff can add notes when approving."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/approve",
            json={"staff_notes": "Good choice, adding to collection"},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["staff_notes"] == "Good choice, adding to collection"

    @pytest.mark.asyncio
    async def test_cannot_approve_already_approved(
        self, client: AsyncClient, test_staff, approved_request
    ):
        """Cannot approve an already-approved request."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{approved_request.id}/approve",
            json={},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 400
        assert "Cannot approve" in _error_detail(resp)

    @pytest.mark.asyncio
    async def test_patron_cannot_approve(self, client: AsyncClient, test_patron, purchase_request):
        """Patrons cannot approve requests."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/approve",
            json={},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 403


# ============ Staff: Decline ============


class TestStaffDecline:
    """Tests for POST /api/v1/purchase-requests/queue/{id}/decline"""

    @pytest.mark.asyncio
    async def test_decline_with_reason(self, client: AsyncClient, test_staff, purchase_request):
        """Staff can decline a request with a reason."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/decline",
            json={"decline_reason": "We already own a similar title"},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "declined"
        assert data["decline_reason"] == "We already own a similar title"
        assert data["reviewed_by_id"] == test_staff.id

    @pytest.mark.asyncio
    async def test_decline_requires_reason(self, client: AsyncClient, test_staff, purchase_request):
        """Decline requires a non-empty reason."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/decline",
            json={},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 422  # validation error

    @pytest.mark.asyncio
    async def test_decline_with_staff_notes(
        self, client: AsyncClient, test_staff, purchase_request
    ):
        """Staff can add internal notes when declining."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/decline",
            json={
                "decline_reason": "Out of scope",
                "staff_notes": "This is a specialized academic text",
            },
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["staff_notes"] == "This is a specialized academic text"

    @pytest.mark.asyncio
    async def test_cannot_decline_approved(self, client: AsyncClient, test_staff, approved_request):
        """Cannot decline an already-approved request."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{approved_request.id}/decline",
            json={"decline_reason": "Changed our mind"},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 400


# ============ Staff: Bulk Operations ============


class TestStaffBulkOps:
    """Tests for bulk approve/decline endpoints."""

    @pytest.fixture
    async def multiple_requests(self, test_db, test_patron):
        """Create multiple pending requests for bulk testing."""
        reqs = []
        for i in range(3):
            req = PatronPurchaseRequest(
                patron_id=test_patron.id,
                title=f"Bulk Test Book {i}",
                author=f"Author {i}",
                material_type=RequestMaterialType.BOOK,
                status=PurchaseRequestStatus.PENDING,
                duplicate_check_done=True,
            )
            test_db.add(req)
            reqs.append(req)
        await test_db.commit()
        for r in reqs:
            await test_db.refresh(r)
        return reqs

    @pytest.mark.asyncio
    async def test_bulk_approve(self, client: AsyncClient, test_staff, multiple_requests):
        """Staff can bulk approve multiple requests."""
        ids = [r.id for r in multiple_requests]
        resp = await client.post(
            "/api/v1/purchase-requests/queue/bulk-approve",
            json={"request_ids": ids},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requested"] == 3
        assert data["succeeded"] == 3
        assert data["failed"] == 0

    @pytest.mark.asyncio
    async def test_bulk_approve_partial_failure(
        self, client: AsyncClient, test_staff, multiple_requests
    ):
        """Bulk approve handles mix of valid and invalid IDs."""
        ids = [multiple_requests[0].id, 99999]
        resp = await client.post(
            "/api/v1/purchase-requests/queue/bulk-approve",
            json={"request_ids": ids},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["succeeded"] == 1
        assert data["failed"] == 1

    @pytest.mark.asyncio
    async def test_bulk_decline(self, client: AsyncClient, test_staff, multiple_requests):
        """Staff can bulk decline with a reason."""
        ids = [r.id for r in multiple_requests]
        resp = await client.post(
            "/api/v1/purchase-requests/queue/bulk-decline",
            json={
                "request_ids": ids,
                "decline_reason": "Budget exhausted for this quarter",
            },
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["succeeded"] == 3
        assert data["failed"] == 0

    @pytest.mark.asyncio
    async def test_bulk_patron_forbidden(self, client: AsyncClient, test_patron, multiple_requests):
        """Patrons cannot perform bulk operations."""
        ids = [r.id for r in multiple_requests]
        resp = await client.post(
            "/api/v1/purchase-requests/queue/bulk-approve",
            json={"request_ids": ids},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 403


# ============ Staff: Link to Order & Mark Received ============


class TestStaffOrderWorkflow:
    """Tests for link-order and mark-received endpoints."""

    @pytest.mark.asyncio
    async def test_link_to_order(
        self, client: AsyncClient, test_staff, approved_request, purchase_order
    ):
        """Staff can link an approved request to a PO."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{approved_request.id}/link-order",
            json={"purchase_order_id": purchase_order.id},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ordered"
        assert data["purchase_order_id"] == purchase_order.id

    @pytest.mark.asyncio
    async def test_cannot_link_pending(self, client: AsyncClient, test_staff, purchase_request):
        """Cannot link a pending request to an order."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/link-order",
            json={"purchase_order_id": 42},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_mark_received(
        self, client: AsyncClient, test_db, test_staff, approved_request, purchase_order
    ):
        """Staff can mark an ordered request as received."""
        # First, set to ordered
        approved_request.status = PurchaseRequestStatus.ORDERED
        approved_request.purchase_order_id = purchase_order.id
        await test_db.commit()

        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{approved_request.id}/mark-received",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    @pytest.mark.asyncio
    async def test_mark_received_from_approved(
        self, client: AsyncClient, test_staff, approved_request
    ):
        """Staff can mark an approved request directly as received (skip ordered)."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{approved_request.id}/mark-received",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    @pytest.mark.asyncio
    async def test_cannot_mark_pending_received(
        self, client: AsyncClient, test_staff, purchase_request
    ):
        """Cannot mark a pending request as received."""
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{purchase_request.id}/mark-received",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 400


# ============ Staff: Fulfillment Stats ============


class TestFulfillmentStats:
    """Tests for GET /api/v1/purchase-requests/stats"""

    @pytest.mark.asyncio
    async def test_stats_empty(self, client: AsyncClient, test_staff):
        """Stats work with no requests."""
        resp = await client.get(
            "/api/v1/purchase-requests/stats",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requests"] == 0
        assert data["fulfillment_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_stats_with_data(
        self, client: AsyncClient, test_staff, purchase_request, approved_request
    ):
        """Stats reflect the current state of requests."""
        resp = await client.get(
            "/api/v1/purchase-requests/stats",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_requests"] == 2
        assert data["pending_count"] == 1
        assert data["approved_count"] == 1

    @pytest.mark.asyncio
    async def test_stats_patron_forbidden(self, client: AsyncClient, test_patron):
        """Patrons cannot access fulfillment stats."""
        resp = await client.get(
            "/api/v1/purchase-requests/stats",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 403


# ============ Decline Reason Templates ============


class TestDeclineTemplates:
    """Tests for decline reason template CRUD."""

    @pytest.mark.asyncio
    async def test_create_template(self, client: AsyncClient, test_staff):
        """Staff can create a decline template."""
        resp = await client.post(
            "/api/v1/purchase-requests/decline-templates",
            json={
                "label": "Out of Scope",
                "message": "This material is outside our collection scope.",
            },
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["label"] == "Out of Scope"
        assert data["is_active"] is True
        assert data["usage_count"] == 0

    @pytest.mark.asyncio
    async def test_list_templates(self, client: AsyncClient, test_staff, decline_template):
        """Staff can list active templates."""
        resp = await client.get(
            "/api/v1/purchase-requests/decline-templates",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(t["id"] == decline_template.id for t in data)

    @pytest.mark.asyncio
    async def test_create_duplicate_label(self, client: AsyncClient, test_staff, decline_template):
        """Cannot create template with duplicate label."""
        resp = await client.post(
            "/api/v1/purchase-requests/decline-templates",
            json={
                "label": "Budget Constraints",
                "message": "Different message",
            },
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 409

    @pytest.mark.asyncio
    async def test_update_template(self, client: AsyncClient, test_staff, decline_template):
        """Staff can update a template."""
        resp = await client.put(
            f"/api/v1/purchase-requests/decline-templates/{decline_template.id}",
            json={"message": "Updated message for budget issues."},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Updated message for budget issues."

    @pytest.mark.asyncio
    async def test_deactivate_template(self, client: AsyncClient, test_staff, decline_template):
        """Staff can deactivate a template."""
        resp = await client.put(
            f"/api/v1/purchase-requests/decline-templates/{decline_template.id}",
            json={"is_active": False},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_delete_template(self, client: AsyncClient, test_staff, decline_template):
        """Staff can delete a template."""
        resp = await client.delete(
            f"/api/v1/purchase-requests/decline-templates/{decline_template.id}",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 204

    @pytest.mark.asyncio
    async def test_template_patron_forbidden(self, client: AsyncClient, test_patron):
        """Patrons cannot manage decline templates."""
        resp = await client.get(
            "/api/v1/purchase-requests/decline-templates",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 403


# ============ Full Workflow Integration ============


class TestFullWorkflow:
    """End-to-end workflow tests."""

    @pytest.mark.asyncio
    async def test_submit_approve_order_receive(
        self, client: AsyncClient, test_patron, test_staff, purchase_order
    ):
        """Full lifecycle: submit -> approve -> link order -> mark received."""
        # 1. Patron submits
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={"title": "Workflow Test Book", "author": "Test Author"},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 201
        req_id = resp.json()["id"]

        # 2. Patron sees it in their list
        resp = await client.get(
            "/api/v1/purchase-requests/mine",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        assert any(r["id"] == req_id for r in resp.json()["items"])

        # 3. Staff approves
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{req_id}/approve",
            json={"staff_notes": "Great pick"},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "approved"

        # 4. Staff links to purchase order
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{req_id}/link-order",
            json={"purchase_order_id": purchase_order.id},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ordered"

        # 5. Staff marks as received
        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{req_id}/mark-received",
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

        # 6. Patron sees updated status
        resp = await client.get(
            f"/api/v1/purchase-requests/mine/{req_id}",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "received"

    @pytest.mark.asyncio
    async def test_submit_and_cancel(self, client: AsyncClient, test_patron):
        """Patron submits then cancels a request."""
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={"title": "Cancel Test Book"},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 201
        req_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/purchase-requests/mine/{req_id}/cancel",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_submit_and_decline(self, client: AsyncClient, test_patron, test_staff):
        """Patron submits, staff declines with reason."""
        resp = await client.post(
            "/api/v1/purchase-requests",
            json={"title": "Decline Test Book"},
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 201
        req_id = resp.json()["id"]

        resp = await client.post(
            f"/api/v1/purchase-requests/queue/{req_id}/decline",
            json={"decline_reason": "Not in our collection scope"},
            headers=auth_headers(test_staff),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "declined"

        # Patron sees the decline reason
        resp = await client.get(
            f"/api/v1/purchase-requests/mine/{req_id}",
            headers=auth_headers(test_patron),
        )
        assert resp.status_code == 200
        assert resp.json()["decline_reason"] == "Not in our collection scope"
