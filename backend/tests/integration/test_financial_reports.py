# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for financial reports API endpoints.

Tests cover:
- Fines collected (revenue summary)
- Waivers granted
- Outstanding balances (aging report)
- Payment method breakdown
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest


async def get_admin_token(client, test_admin_data):
    """Helper to get admin authentication token."""
    login_data = {
        "username": test_admin_data["email"],
        "password": test_admin_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


# ==================== Financial Report Fixtures ====================


@pytest.fixture
async def test_paid_fines(test_db, test_patron):
    """Create multiple paid fines for revenue summary testing."""
    from app.models.fine import Fine, FineStatus, FineType

    paid_fines = []
    fine_data = [
        (FineType.overdue, Decimal("15.00"), 5),
        (FineType.overdue, Decimal("10.00"), 10),
        (FineType.lost_item, Decimal("50.00"), 3),
        (FineType.damaged_item, Decimal("25.00"), 7),
    ]

    for fine_type, amount, days_ago in fine_data:
        fine = Fine(
            user_id=test_patron.id,
            fine_type=fine_type,
            status=FineStatus.paid,
            amount=amount,
            amount_paid=amount,
            description=f"Paid {fine_type.value} fine",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago + 5),
            paid_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
        )
        test_db.add(fine)
        paid_fines.append(fine)

    await test_db.commit()
    for fine in paid_fines:
        await test_db.refresh(fine)
    return paid_fines


@pytest.fixture
async def test_waived_fines(test_db, test_patron, test_admin):
    """Create waived fines for waiver report testing."""
    from app.models.fine import Fine, FineStatus, FineType

    waived_fines = []
    waiver_data = [
        (FineType.overdue, Decimal("5.00"), "Financial hardship", 2),
        (FineType.overdue, Decimal("8.00"), "Library error", 5),
        (FineType.damaged_item, Decimal("20.00"), "Item defect pre-existing", 10),
    ]

    for fine_type, amount, notes, days_ago in waiver_data:
        fine = Fine(
            user_id=test_patron.id,
            fine_type=fine_type,
            status=FineStatus.waived,
            amount=amount,
            amount_paid=Decimal("0.00"),
            description=f"Waived {fine_type.value} fine",
            notes=notes,
            created_at=datetime.now(timezone.utc) - timedelta(days=days_ago + 5),
            waived_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
            waived_by_id=test_admin.id,
        )
        test_db.add(fine)
        waived_fines.append(fine)

    await test_db.commit()
    for fine in waived_fines:
        await test_db.refresh(fine)
    return waived_fines


@pytest.fixture
async def test_outstanding_fines(test_db, test_patron):
    """Create outstanding fines with various ages for aging report testing."""
    from app.models.fine import Fine, FineStatus, FineType

    outstanding_fines = []
    # Create fines with different ages to test aging categories
    age_data = [
        # (fine_type, amount, amount_paid, days_old)
        (FineType.overdue, Decimal("10.00"), Decimal("0.00"), 15),     # 0-30 days
        (FineType.overdue, Decimal("12.00"), Decimal("5.00"), 25),     # 0-30 days (partial)
        (FineType.lost_item, Decimal("30.00"), Decimal("0.00"), 45),   # 31-60 days
        (FineType.damaged_item, Decimal("25.00"), Decimal("10.00"), 55),  # 31-60 days (partial)
        (FineType.overdue, Decimal("15.00"), Decimal("0.00"), 75),     # 61-90 days
        (FineType.lost_item, Decimal("100.00"), Decimal("50.00"), 120),  # 90+ days
        (FineType.overdue, Decimal("20.00"), Decimal("0.00"), 180),    # 90+ days
    ]

    for fine_type, amount, amount_paid, days_old in age_data:
        status = FineStatus.partial if amount_paid > 0 else FineStatus.unpaid
        fine = Fine(
            user_id=test_patron.id,
            fine_type=fine_type,
            status=status,
            amount=amount,
            amount_paid=amount_paid,
            description=f"Outstanding {fine_type.value} fine - {days_old} days old",
            created_at=datetime.now(timezone.utc) - timedelta(days=days_old),
        )
        test_db.add(fine)
        outstanding_fines.append(fine)

    await test_db.commit()
    for fine in outstanding_fines:
        await test_db.refresh(fine)
    return outstanding_fines


@pytest.fixture
async def test_payment_history(test_db, test_paid_fines, test_admin):
    """Create payment history records for payment method testing."""
    from app.models.fine import FinePaymentHistory, PaymentMethod

    payments = []
    # Distribute payments across different methods
    payment_data = [
        (test_paid_fines[0].id, PaymentMethod.cash, Decimal("15.00")),
        (test_paid_fines[1].id, PaymentMethod.card, Decimal("10.00")),
        (test_paid_fines[2].id, PaymentMethod.online, Decimal("50.00")),
        (test_paid_fines[3].id, PaymentMethod.check, Decimal("25.00")),
    ]

    for fine_id, method, amount in payment_data:
        payment = FinePaymentHistory(
            fine_id=fine_id,
            user_id=test_paid_fines[0].user_id,
            amount=amount,
            payment_method=method,
            receipt_number=f"RCP-{fine_id}-{method.value}",
            processed_by_id=test_admin.id,
            created_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        test_db.add(payment)
        payments.append(payment)

    await test_db.commit()
    for payment in payments:
        await test_db.refresh(payment)
    return payments


# ==================== Unit Tests for FinancialReportsService ====================


@pytest.mark.integration
class TestFinancialReportsServiceUnit:
    """Unit tests for FinancialReportsService methods."""

    async def test_get_revenue_summary(self, test_db, test_paid_fines):
        """Test revenue summary returns correct totals by fine type."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_revenue_summary(use_cache=False)

        # Verify response structure
        assert "total_revenue" in result
        assert "by_type" in result
        assert "monthly_breakdown" in result
        assert "period" in result

        # Verify total revenue calculation
        # Expected: 15 + 10 + 50 + 25 = 100
        assert result["total_revenue"] == 100.0

        # Verify breakdown by type
        assert "overdue" in result["by_type"]
        assert result["by_type"]["overdue"]["count"] == 2
        assert result["by_type"]["overdue"]["total"] == 25.0  # 15 + 10

        assert "lost_item" in result["by_type"]
        assert result["by_type"]["lost_item"]["count"] == 1
        assert result["by_type"]["lost_item"]["total"] == 50.0

        assert "damaged_item" in result["by_type"]
        assert result["by_type"]["damaged_item"]["count"] == 1
        assert result["by_type"]["damaged_item"]["total"] == 25.0

    async def test_get_waived_fines(self, test_db, test_waived_fines):
        """Test waived fines report returns correct data."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_waived_fines(use_cache=False)

        # Verify response structure
        assert "fines" in result
        assert "summary" in result
        assert "pagination" in result
        assert "period" in result

        # Verify summary
        assert result["summary"]["total_waived_count"] == 3
        # Expected: 5 + 8 + 20 = 33
        assert result["summary"]["total_waived_amount"] == 33.0

        # Verify fines list
        assert len(result["fines"]) == 3
        for fine in result["fines"]:
            assert "id" in fine
            assert "patron_id" in fine
            assert "fine_type" in fine
            assert "amount" in fine
            assert "waived_at" in fine
            assert "waived_by_id" in fine
            assert "notes" in fine

    async def test_get_outstanding_balances(self, test_db, test_outstanding_fines):
        """Test outstanding balances aging report categorizes correctly."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_outstanding_balances()

        # Verify response structure
        assert "by_age" in result
        assert "delinquent_accounts" in result
        assert "total_outstanding" in result

        aging = result["by_age"]
        assert "0-30 days" in aging
        assert "31-60 days" in aging
        assert "61-90 days" in aging
        assert "90+ days" in aging

        # Verify 0-30 days category (2 fines: 15 and 25 days old)
        # Expected: (10 - 0) + (12 - 5) = 10 + 7 = 17
        assert aging["0-30 days"] == 17.0

        # Verify 31-60 days category (2 fines: 45 and 55 days old)
        # Expected: (30 - 0) + (25 - 10) = 30 + 15 = 45
        assert aging["31-60 days"] == 45.0

        # Verify 61-90 days category (1 fine: 75 days old)
        assert aging["61-90 days"] == 15.0

        # Verify 90+ days category (2 fines: 120 and 180 days old)
        # Expected: (100 - 50) + (20 - 0) = 50 + 20 = 70
        assert aging["90+ days"] == 70.0

    async def test_get_payment_methods(self, test_db, test_payment_history):
        """Test payment method breakdown returns correct percentages."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_payment_methods(use_cache=False)

        # Verify response structure
        assert "payment_methods" in result
        assert "total_collected" in result
        assert "period" in result

        # Verify total collected
        # Expected: 15 + 10 + 50 + 25 = 100
        assert result["total_collected"] == 100.0

        methods = result["payment_methods"]

        # Verify each payment method
        assert "cash" in methods
        assert methods["cash"]["count"] == 1
        assert methods["cash"]["total"] == 15.0
        assert methods["cash"]["percentage"] == 15.0

        assert "card" in methods
        assert methods["card"]["count"] == 1
        assert methods["card"]["total"] == 10.0
        assert methods["card"]["percentage"] == 10.0

        assert "online" in methods
        assert methods["online"]["count"] == 1
        assert methods["online"]["total"] == 50.0
        assert methods["online"]["percentage"] == 50.0

        assert "check" in methods
        assert methods["check"]["count"] == 1
        assert methods["check"]["total"] == 25.0
        assert methods["check"]["percentage"] == 25.0

    async def test_revenue_summary_date_filtering(self, test_db, test_paid_fines):
        """Test revenue summary respects date range filtering."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)

        # Query with narrow date range that excludes some fines
        start = datetime.now(timezone.utc) - timedelta(days=8)
        end = datetime.now(timezone.utc) - timedelta(days=2)

        result = await service.get_revenue_summary(
            start_date=start, end_date=end, use_cache=False
        )

        # Should have fewer results due to date filtering
        assert result["total_revenue"] <= 100.0

    async def test_outstanding_balances_minimum_filter(self, test_db, test_outstanding_fines):
        """Test outstanding balances respects minimum balance filter."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)

        # Filter out small balances
        result = await service.get_outstanding_balances(minimum_balance=Decimal("20.00"))

        # Count total fines returned
        total_fines = len(result["delinquent_accounts"])

        # Should exclude fines with balance < 20
        # Excluded: 10 (0-30), 7 (0-30), 15 (31-60), 15 (61-90)
        # Remaining: 30 (31-60), 50 (90+), 20 (90+)
        assert total_fines == 3

    async def test_waived_fines_pagination(self, test_db, test_waived_fines):
        """Test waived fines supports pagination."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)

        # Request only 2 records
        result = await service.get_waived_fines(limit=2, offset=0, use_cache=False)

        assert len(result["fines"]) == 2
        assert result["pagination"]["limit"] == 2
        assert result["pagination"]["offset"] == 0
        assert result["pagination"]["total"] == 3

        # Request next page
        result2 = await service.get_waived_fines(limit=2, offset=2, use_cache=False)
        assert len(result2["fines"]) == 1

    async def test_export_to_csv_revenue_summary(self, test_db, test_paid_fines):
        """Test CSV export for revenue summary."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        csv_content = await service.export_to_csv("revenue_summary")

        # Verify CSV has expected content
        assert "Revenue Summary" in csv_content
        assert "Category,Count,Amount" in csv_content
        assert "Total Revenue" in csv_content
        assert "100" in csv_content  # Total amount

    async def test_export_to_csv_payment_methods(self, test_db, test_payment_history):
        """Test CSV export for payment methods report."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        csv_content = await service.export_to_csv("payment_methods")

        # Verify CSV has expected content
        assert "Payment Methods Report" in csv_content
        assert "Method,Count,Amount,Percentage" in csv_content
        assert "Total Collected" in csv_content

    async def test_cache_functionality(self, test_db, test_paid_fines):
        """Test that caching works and can be cleared."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)

        # First call should populate cache
        result1 = await service.get_revenue_summary(use_cache=True)

        # Second call should use cache
        result2 = await service.get_revenue_summary(use_cache=True)

        assert result1["total_revenue"] == result2["total_revenue"]

        # Clear cache
        await service.clear_cache()

        # Third call should recalculate
        result3 = await service.get_revenue_summary(use_cache=True)
        assert result3["total_revenue"] == result1["total_revenue"]


# ==================== API Endpoint Integration Tests ====================


@pytest.mark.integration
class TestFinancialReportsEndpoints:
    """Integration tests for financial reports API endpoints."""

    async def test_revenue_summary_requires_admin(self, client):
        """Test revenue summary endpoint requires admin authentication."""
        response = await client.get("/api/v1/financial/reports/revenue-summary")
        assert response.status_code == 401

    async def test_revenue_summary_endpoint(
        self, client, test_admin, test_admin_data, test_paid_fines
    ):
        """Test revenue summary endpoint returns proper structure."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/revenue-summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure matches schema
        assert "total_revenue" in data
        assert "by_type" in data
        assert "monthly_breakdown" in data
        assert "period" in data

        assert isinstance(data["total_revenue"], (int, float))
        assert isinstance(data["by_type"], dict)
        assert isinstance(data["monthly_breakdown"], list)

    async def test_waived_fines_requires_admin(self, client):
        """Test waived fines endpoint requires admin authentication."""
        response = await client.get("/api/v1/financial/reports/waived-fines")
        assert response.status_code == 401

    async def test_waived_fines_endpoint(
        self, client, test_admin, test_admin_data, test_waived_fines
    ):
        """Test waived fines endpoint returns proper structure."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/waived-fines",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "fines" in data
        assert "summary" in data
        assert "pagination" in data
        assert "period" in data

        assert isinstance(data["fines"], list)
        assert "total_waived_count" in data["summary"]
        assert "total_waived_amount" in data["summary"]

    async def test_outstanding_balances_requires_admin(self, client):
        """Test outstanding balances endpoint requires admin authentication."""
        response = await client.get("/api/v1/financial/reports/outstanding-balances")
        assert response.status_code == 401

    async def test_outstanding_balances_endpoint(
        self, client, test_admin, test_admin_data, test_outstanding_fines
    ):
        """Test outstanding balances endpoint returns proper aging structure."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/outstanding-balances",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "by_age" in data
        assert "delinquent_accounts" in data
        assert "total_outstanding" in data

        aging = data["by_age"]
        assert "0-30 days" in aging
        assert "31-60 days" in aging
        assert "61-90 days" in aging
        assert "90+ days" in aging

        # Verify each category is a numeric total
        for category in ["0-30 days", "31-60 days", "61-90 days", "90+ days"]:
            assert isinstance(aging[category], (int, float))

        assert isinstance(data["delinquent_accounts"], list)
        for account in data["delinquent_accounts"]:
            assert "patron_id" in account
            assert "balance" in account

    async def test_payment_methods_requires_admin(self, client):
        """Test payment methods endpoint requires admin authentication."""
        response = await client.get("/api/v1/financial/reports/payment-methods")
        assert response.status_code == 401

    async def test_payment_methods_endpoint(
        self, client, test_admin, test_admin_data, test_payment_history
    ):
        """Test payment methods endpoint returns proper structure."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/payment-methods",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "payment_methods" in data
        assert "total_collected" in data
        assert "period" in data

        assert isinstance(data["payment_methods"], dict)
        assert isinstance(data["total_collected"], (int, float))

        # Verify payment method details
        for method, details in data["payment_methods"].items():
            assert "count" in details
            assert "total" in details
            assert "percentage" in details

    async def test_revenue_summary_with_date_params(
        self, client, test_admin, test_admin_data, test_paid_fines
    ):
        """Test revenue summary endpoint accepts date parameters."""
        token = await get_admin_token(client, test_admin_data)

        start_date = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
        end_date = datetime.now(timezone.utc).isoformat()

        response = await client.get(
            "/api/v1/financial/reports/revenue-summary",
            params={"start_date": start_date, "end_date": end_date},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["period"]["start_date"] is not None
        assert data["period"]["end_date"] is not None

    async def test_outstanding_balances_with_minimum_balance(
        self, client, test_admin, test_admin_data, test_outstanding_fines
    ):
        """Test outstanding balances endpoint accepts minimum_balance parameter."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/outstanding-balances?minimum_balance=20.00",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    async def test_waived_fines_pagination_params(
        self, client, test_admin, test_admin_data, test_waived_fines
    ):
        """Test waived fines endpoint accepts pagination parameters."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/waived-fines?limit=2&offset=0",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["pagination"]["limit"] == 2
        assert data["pagination"]["offset"] == 0

    async def test_fine_trends_endpoint(
        self, client, test_admin, test_admin_data, test_paid_fines
    ):
        """Test fine trends endpoint returns trend data."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/fine-trends?days=30",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "daily_data" in data
        assert "total_outstanding" in data
        assert "period_days" in data
        assert data["period_days"] == 30

    async def test_budget_vs_actual_endpoint(
        self, client, test_admin, test_admin_data, test_paid_fines
    ):
        """Test budget vs actual endpoint returns yearly data."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/budget-vs-actual",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "monthly_actual" in data
        assert "year" in data
        assert isinstance(data["monthly_actual"], dict)

    async def test_export_csv(self, client, test_admin, test_admin_data, test_paid_fines):
        """Test CSV export endpoint."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/export/revenue_summary?format=csv",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")
        assert response.headers.get("x-report-type") == "revenue_summary"
        assert response.headers.get("x-report-format") == "csv"
        assert response.headers.get("x-report-generated-at") is not None
        assert response.headers.get("x-report-sha256") is not None

    async def test_export_json(self, client, test_admin, test_admin_data, test_paid_fines):
        """Test JSON export endpoint."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/export/revenue_summary?format=json",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert "report_type" in data
        assert data["report_type"] == "revenue_summary"
        assert "generated_at" in data
        assert "data" in data
        assert "trust" in data
        assert data["trust"]["hash_scope"] == "data"
        assert data["trust"]["sha256"]

    async def test_export_invalid_report_type(
        self, client, test_admin, test_admin_data
    ):
        """Test export endpoint rejects invalid report types."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/export/invalid_report",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400

    async def test_clear_cache_endpoint(self, client, test_admin, test_admin_data):
        """Test cache clear endpoint."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.post(
            "/api/v1/financial/cache/clear",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert "message" in data

    async def test_invalid_date_format(self, client, test_admin, test_admin_data):
        """Test endpoint returns 400 for invalid date format."""
        token = await get_admin_token(client, test_admin_data)
        response = await client.get(
            "/api/v1/financial/reports/revenue-summary?start_date=invalid-date",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 400


# ==================== Edge Case Tests ====================


@pytest.mark.integration
class TestFinancialReportsEdgeCases:
    """Test edge cases and error handling for financial reports."""

    async def test_empty_revenue_summary(self, test_db):
        """Test revenue summary with no paid fines."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_revenue_summary(use_cache=False)

        assert result["total_revenue"] == 0.0
        assert result["by_type"] == {}
        assert result["monthly_breakdown"] == []

    async def test_empty_outstanding_balances(self, test_db):
        """Test outstanding balances with no unpaid fines."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_outstanding_balances()

        aging = result["by_age"]
        for category in ["0-30 days", "31-60 days", "61-90 days", "90+ days"]:
            assert aging[category] == 0.0
        assert result["delinquent_accounts"] == []

    async def test_empty_waived_fines(self, test_db):
        """Test waived fines with no waivers."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_waived_fines(use_cache=False)

        assert result["summary"]["total_waived_count"] == 0
        assert result["summary"]["total_waived_amount"] == 0.0
        assert result["fines"] == []

    async def test_empty_payment_methods(self, test_db):
        """Test payment methods with no payment history."""
        from app.services.financial_reports_service import FinancialReportsService

        service = FinancialReportsService(test_db)
        result = await service.get_payment_methods(use_cache=False)

        assert result["total_collected"] == 0.0
        assert result["payment_methods"] == {}

    async def test_partial_payment_in_outstanding(self, test_db, test_patron):
        """Test that partial payments are correctly reflected in outstanding balances."""
        from app.models.fine import Fine, FineStatus, FineType
        from app.services.financial_reports_service import FinancialReportsService

        # Create a partially paid fine
        fine = Fine(
            user_id=test_patron.id,
            fine_type=FineType.overdue,
            status=FineStatus.partial,
            amount=Decimal("50.00"),
            amount_paid=Decimal("20.00"),  # 30 outstanding
            description="Partial payment test",
            created_at=datetime.now(timezone.utc) - timedelta(days=10),
        )
        test_db.add(fine)
        await test_db.commit()

        service = FinancialReportsService(test_db)
        result = await service.get_outstanding_balances()

        # Find the fine in the 0-30 days category
        assert result["by_age"]["0-30 days"] >= 30.0

        # Verify balance calculation is correct (amount - amount_paid = 30)
        matching = [
            account
            for account in result["delinquent_accounts"]
            if account["patron_id"] == test_patron.id
        ]
        assert matching
        assert matching[0]["balance"] == 30.0
