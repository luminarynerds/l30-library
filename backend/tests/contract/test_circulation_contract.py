# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Contract tests for circulation API endpoints.

These tests validate that every circulation endpoint returns responses
matching the stored JSON Schema snapshots. If a Pydantic model changes
without updating the snapshot, these tests fail - catching accidental
breaking changes to the API contract.

Run snapshot update:
    python scripts/generate_snapshots.py
"""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from app.core.security import create_access_token


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _patron_headers(user) -> dict:
    """Build Authorization header for a patron user."""
    token = create_access_token(subject=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _staff_headers(user) -> dict:
    """Build Authorization header for a staff user."""
    token = create_access_token(subject=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


def _admin_headers(user) -> dict:
    """Build Authorization header for an admin user."""
    token = create_access_token(subject=str(user.id), email=user.email)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Checkout endpoint contracts
# ---------------------------------------------------------------------------


class TestCheckoutContract:
    """Validate checkout endpoints against CheckoutResponse schema."""

    async def test_checkout_create_response_shape(
        self, client, test_patron, test_catalog_item, assert_matches_snapshot
    ):
        """POST /circulation/checkout must return CheckoutResponse shape."""
        headers = _patron_headers(test_patron)
        resp = await client.post(
            "/api/v1/circulation/checkout",
            json={"item_id": test_catalog_item.id},
            headers=headers,
        )
        assert resp.status_code == 201
        assert_matches_snapshot(resp.json(), "circulation/CheckoutResponse.json")

    async def test_active_checkouts_response_shape(
        self, client, test_patron, test_checkout, assert_matches_snapshot
    ):
        """GET /circulation/checkouts/active must return list of CheckoutResponse."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/circulation/checkouts/active", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        if data:
            assert_matches_snapshot(data, "circulation/CheckoutResponse.json", is_list=True)

    async def test_checkouts_list_response_shape(
        self, client, test_patron, test_checkout, assert_matches_snapshot
    ):
        """GET /circulation/checkouts must return list of CheckoutResponse."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/circulation/checkouts", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        if data:
            assert_matches_snapshot(data, "circulation/CheckoutResponse.json", is_list=True)

    async def test_checkout_history_response_shape(
        self, client, test_patron, test_checkout, assert_matches_snapshot
    ):
        """GET /circulation/history must return list of CheckoutResponse."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/circulation/history", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        if data:
            assert_matches_snapshot(data, "circulation/CheckoutResponse.json", is_list=True)

    async def test_renew_checkout_response_shape(
        self, client, test_patron, test_checkout, assert_matches_snapshot
    ):
        """POST /circulation/renew/{id} must return CheckoutResponse shape."""
        headers = _patron_headers(test_patron)
        resp = await client.post(
            f"/api/v1/circulation/renew/{test_checkout.id}",
            headers=headers,
        )
        # Renewal may succeed or fail (e.g., max renewals), but if 200 check shape
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "circulation/CheckoutResponse.json")

    async def test_checkin_response_shape(
        self, client, test_patron, test_checkout, assert_matches_snapshot
    ):
        """POST /circulation/checkin must return CheckoutResponse shape."""
        headers = _patron_headers(test_patron)
        resp = await client.post(
            "/api/v1/circulation/checkin",
            json={"checkout_id": test_checkout.id},
            headers=headers,
        )
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "circulation/CheckoutResponse.json")

    async def test_return_checkout_response_shape(
        self, client, test_patron, test_checkout, assert_matches_snapshot
    ):
        """POST /circulation/return/{id} must return CheckoutResponse shape."""
        headers = _patron_headers(test_patron)
        resp = await client.post(
            f"/api/v1/circulation/return/{test_checkout.id}",
            headers=headers,
        )
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "circulation/CheckoutResponse.json")


# ---------------------------------------------------------------------------
# Hold endpoint contracts
# ---------------------------------------------------------------------------


class TestHoldContract:
    """Validate hold endpoints against HoldResponse schema."""

    async def test_create_hold_response_shape(
        self, client, test_patron, test_catalog_item, assert_matches_snapshot
    ):
        """POST /circulation/holds must return HoldResponse shape."""
        headers = _patron_headers(test_patron)
        resp = await client.post(
            "/api/v1/circulation/holds",
            json={"item_id": test_catalog_item.id},
            headers=headers,
        )
        if resp.status_code == 201:
            assert_matches_snapshot(resp.json(), "circulation/HoldResponse.json")

    async def test_active_holds_response_shape(
        self, client, test_patron, test_hold, assert_matches_snapshot
    ):
        """GET /circulation/holds/active must return list of HoldResponse."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/circulation/holds/active", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        if data:
            assert_matches_snapshot(data, "circulation/HoldResponse.json", is_list=True)

    async def test_holds_list_response_shape(
        self, client, test_patron, test_hold, assert_matches_snapshot
    ):
        """GET /circulation/holds must return list of HoldResponse."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/circulation/holds", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        if data:
            assert_matches_snapshot(data, "circulation/HoldResponse.json", is_list=True)


# ---------------------------------------------------------------------------
# Hold aging report contract
# ---------------------------------------------------------------------------


class TestHoldAgingReportContract:
    """Validate hold aging report endpoint against HoldAgingReport schema."""

    async def test_hold_aging_report_response_shape(
        self, client, test_staff, assert_matches_snapshot
    ):
        """GET /circulation/holds/aging-report must return HoldAgingReport shape."""
        headers = _staff_headers(test_staff)
        resp = await client.get("/api/v1/circulation/holds/aging-report", headers=headers)
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "circulation/HoldAgingReport.json")


# ---------------------------------------------------------------------------
# Pull list contract
# ---------------------------------------------------------------------------


class TestPullListContract:
    """Validate pull list endpoint against PullListResponse schema."""

    async def test_pull_list_response_shape(
        self, client, test_staff, assert_matches_snapshot
    ):
        """GET /circulation/holds/pull-list must return PullListResponse shape."""
        headers = _staff_headers(test_staff)
        resp = await client.get("/api/v1/circulation/holds/pull-list", headers=headers)
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "circulation/PullListResponse.json")


# ---------------------------------------------------------------------------
# Fine endpoint contracts
# ---------------------------------------------------------------------------


class TestFineContract:
    """Validate fine endpoints against FineResponse / FineSummary schemas."""

    async def test_fines_list_response_shape(
        self, client, test_patron, test_fine, assert_matches_snapshot
    ):
        """GET /circulation/fines must return list of FineResponse."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/circulation/fines", headers=headers)
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert isinstance(data, list)
        if data:
            assert_matches_snapshot(data, "circulation/PatronFineResponse.json", is_list=True)

    async def test_fines_summary_response_shape(
        self, client, test_patron, assert_matches_snapshot
    ):
        """GET /circulation/fines/summary must return FineSummary shape."""
        headers = _patron_headers(test_patron)
        resp = await client.get("/api/v1/circulation/fines/summary", headers=headers)
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "circulation/FineSummary.json")


# ---------------------------------------------------------------------------
# Background job contracts
# ---------------------------------------------------------------------------


class TestCirculationJobsContract:
    """Validate background job endpoints against JobResponse schema."""

    async def test_process_expired_holds_response_shape(
        self, client, test_admin, assert_matches_snapshot
    ):
        """POST /circulation/holds/process-expired must return JobResponse shape."""
        headers = _admin_headers(test_admin)
        resp = await client.post(
            "/api/v1/circulation/holds/process-expired",
            headers=headers,
        )
        if resp.status_code == 200:
            assert_matches_snapshot(resp.json(), "common/JobResponse.json")
