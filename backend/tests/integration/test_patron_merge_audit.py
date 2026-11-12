# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Integration tests for patron merge audit functionality.

Tests:
- Merge creates proper audit record
- Data is archived before deletion
- Reading lists and favorites are transferred
- Merge history endpoint works correctly
- Audit details endpoint returns archived data
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest


def _error_detail(response) -> str:
    """Error responses are wrapped as {"error": {"message": ...}} by
    app.core.exception_handlers.http_exception_handler, not the FastAPI
    default {"detail": ...}."""
    data = response.json()
    if "detail" in data:
        return str(data["detail"])
    return str(data.get("error", {}).get("message", data))


@pytest.fixture
async def secondary_patron(test_db):
    """Create a secondary patron to be merged."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    user = User(
        email="secondary@example.com",
        password_hash=hash_password("SecondaryPassword123!"),
        first_name="Secondary",
        last_name="Patron",
        role=UserRole.PATRON,
        is_active=True,
        email_verified=True,
        phone="555-1234",
        library_card="SEC-001",
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest.fixture
async def secondary_patron_checkout(test_db, secondary_patron, test_catalog_item):
    """Create a checkout for the secondary patron."""
    from app.models.circulation import Checkout, CheckoutStatus

    checkout = Checkout(
        user_id=secondary_patron.id,
        item_id=test_catalog_item.id,
        status=CheckoutStatus.active,
        checked_out_at=datetime.now(),
        due_date=datetime.now() + timedelta(days=21),
    )
    test_db.add(checkout)
    await test_db.commit()
    await test_db.refresh(checkout)
    return checkout


@pytest.fixture
async def secondary_patron_hold(test_db, secondary_patron):
    """Create a hold for the secondary patron."""
    from app.models.catalog import CatalogItem, ItemStatus
    from app.models.circulation import Hold, HoldStatus

    # Create a separate catalog item for the hold
    item = CatalogItem(
        title="Hold Test Book",
        author="Hold Author",
        isbn="978-0-123456-99-9",
        status=ItemStatus.available,
        call_number="HOLD-001",
    )
    test_db.add(item)
    await test_db.commit()
    await test_db.refresh(item)

    hold = Hold(
        user_id=secondary_patron.id,
        item_id=item.id,
        status=HoldStatus.pending,
        position=1,
    )
    test_db.add(hold)
    await test_db.commit()
    await test_db.refresh(hold)
    return hold


@pytest.fixture
async def secondary_patron_fine(test_db, secondary_patron):
    """Create a fine for the secondary patron."""
    from app.models.fine import Fine, FineStatus, FineType

    fine = Fine(
        user_id=secondary_patron.id,
        fine_type=FineType.overdue,
        status=FineStatus.unpaid,
        amount=Decimal("5.00"),
        amount_paid=Decimal("0.00"),
        description="Test overdue fine",
    )
    test_db.add(fine)
    await test_db.commit()
    await test_db.refresh(fine)
    return fine


@pytest.fixture
async def secondary_patron_reading_list(test_db, secondary_patron, test_catalog_item):
    """Create a reading list for the secondary patron."""
    from app.models.reading_list import ReadingList, ListItem

    reading_list = ReadingList(
        user_id=secondary_patron.id,
        name="Secondary's Reading List",
        description="A test reading list",
    )
    test_db.add(reading_list)
    await test_db.commit()
    await test_db.refresh(reading_list)

    # Add an item to the list
    list_item = ListItem(
        list_id=reading_list.id,
        catalog_item_id=test_catalog_item.id,
    )
    test_db.add(list_item)
    await test_db.commit()
    await test_db.refresh(list_item)

    return reading_list


@pytest.fixture
async def secondary_patron_favorite(test_db, secondary_patron, test_catalog_item):
    """Create a favorite for the secondary patron."""
    from app.models.favorite import Favorite

    favorite = Favorite(
        user_id=secondary_patron.id,
        catalog_item_id=test_catalog_item.id,
    )
    test_db.add(favorite)
    await test_db.commit()
    await test_db.refresh(favorite)
    return favorite


async def get_admin_token(client, test_admin_data):
    """Helper to get admin authentication token."""
    login_data = {
        "username": test_admin_data["email"],
        "password": test_admin_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


async def get_staff_token(client, test_staff_data):
    """Helper to get staff authentication token."""
    login_data = {
        "username": test_staff_data["email"],
        "password": test_staff_data["password"],
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    return response.json()["access_token"]


@pytest.mark.integration
class TestPatronMergeAudit:
    """Test patron merge audit functionality."""

    async def test_merge_creates_audit_record(
        self,
        client,
        test_admin,
        test_admin_data,
        test_patron,
        secondary_patron,
    ):
        """Test that merging patrons creates an audit record."""
        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["merged_patron_id"] == test_patron.id
        assert data["deleted_patron_id"] == secondary_patron.id
        assert data["audit_log_id"] is not None

    async def test_merge_archives_secondary_patron_data(
        self,
        client,
        test_db,
        test_admin,
        test_admin_data,
        test_patron,
        secondary_patron,
        secondary_patron_checkout,
        secondary_patron_fine,
    ):
        """Test that merge archives secondary patron's data."""
        from app.models.patron_merge_audit import PatronMergeAudit
        from sqlalchemy import select

        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        audit_id = response.json()["audit_log_id"]

        # Verify audit record contains archived data
        result = await test_db.execute(
            select(PatronMergeAudit).where(PatronMergeAudit.id == audit_id)
        )
        audit = result.scalar_one()

        assert audit.data_archived is not None
        assert "user" in audit.data_archived
        assert audit.data_archived["user"]["email"] == secondary_patron.email
        assert audit.data_archived["user"]["first_name"] == secondary_patron.first_name
        assert len(audit.data_archived["checkouts"]) == 1
        assert len(audit.data_archived["fines"]) == 1

    async def test_merge_transfers_checkouts(
        self,
        client,
        test_db,
        test_admin,
        test_admin_data,
        test_patron,
        secondary_patron,
        secondary_patron_checkout,
    ):
        """Test that merge transfers checkouts to primary patron."""
        from app.models.circulation import Checkout
        from sqlalchemy import select

        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
            "merge_checkouts": True,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["checkouts_transferred"] == 1

        # Verify checkout now belongs to primary patron
        result = await test_db.execute(
            select(Checkout).where(Checkout.id == secondary_patron_checkout.id)
        )
        checkout = result.scalar_one()
        assert checkout.user_id == test_patron.id

    async def test_merge_transfers_reading_lists(
        self,
        client,
        test_db,
        test_admin,
        test_admin_data,
        test_patron,
        secondary_patron,
        secondary_patron_reading_list,
    ):
        """Test that merge transfers reading lists to primary patron."""
        from app.models.reading_list import ReadingList
        from sqlalchemy import select

        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
            "merge_reading_lists": True,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        assert response.json()["reading_lists_transferred"] == 1

        # Verify reading list now belongs to primary patron and has "(merged)" suffix
        result = await test_db.execute(
            select(ReadingList).where(ReadingList.id == secondary_patron_reading_list.id)
        )
        reading_list = result.scalar_one()
        assert reading_list.user_id == test_patron.id
        assert "(merged)" in reading_list.name

    async def test_merge_transfers_favorites_without_duplicates(
        self,
        client,
        test_db,
        test_admin,
        test_admin_data,
        test_patron,
        secondary_patron,
        secondary_patron_favorite,
        test_catalog_item,
    ):
        """Test that merge transfers favorites but avoids duplicates."""
        from app.models.favorite import Favorite
        from sqlalchemy import select, func

        # First, create the same favorite for the primary patron
        existing_favorite = Favorite(
            user_id=test_patron.id,
            catalog_item_id=test_catalog_item.id,
        )
        test_db.add(existing_favorite)
        await test_db.commit()

        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
            "merge_favorites": True,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        # No favorites transferred because primary already has the same item
        assert response.json()["favorites_transferred"] == 0

        # Verify only one favorite exists for primary patron
        result = await test_db.execute(
            select(func.count(Favorite.id)).where(
                Favorite.user_id == test_patron.id,
                Favorite.catalog_item_id == test_catalog_item.id
            )
        )
        count = result.scalar()
        assert count == 1

    async def test_merge_preview_includes_all_counts(
        self,
        client,
        test_admin,
        test_admin_data,
        test_patron,
        secondary_patron,
        secondary_patron_checkout,
        secondary_patron_hold,
        secondary_patron_fine,
        secondary_patron_reading_list,
        secondary_patron_favorite,
    ):
        """Test that merge preview shows correct counts for all data types."""
        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge/preview",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["checkouts_to_transfer"] == 1
        assert data["holds_to_transfer"] == 1
        assert data["fines_to_transfer"] == 1
        assert data["reading_lists_to_transfer"] == 1
        assert data["favorites_to_transfer"] == 1

    async def test_merge_history_endpoint(
        self,
        client,
        test_db,
        test_admin,
        test_admin_data,
        test_staff,
        test_staff_data,
        test_patron,
        secondary_patron,
    ):
        """Test merge history endpoint returns merge records."""
        # First, perform a merge
        admin_token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
        }

        merge_response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert merge_response.status_code == 200

        # Now check merge history for primary patron
        staff_token = await get_staff_token(client, test_staff_data)
        history_response = await client.get(
            f"/api/v1/staff/patrons/{test_patron.id}/merge-history",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert history_response.status_code == 200
        data = history_response.json()
        assert data["patron_id"] == test_patron.id
        assert len(data["as_primary"]) == 1
        assert len(data["as_secondary"]) == 0
        assert data["total_merges"] == 1

        # Verify the merge record details
        merge_record = data["as_primary"][0]
        assert merge_record["primary_patron_id"] == test_patron.id
        assert merge_record["secondary_patron_id"] == secondary_patron.id
        assert merge_record["has_archived_data"] is True

    async def test_merge_audit_details_endpoint(
        self,
        client,
        test_admin,
        test_admin_data,
        test_patron,
        secondary_patron,
        secondary_patron_checkout,
    ):
        """Test merge audit details endpoint returns full archived data."""
        token = await get_admin_token(client, test_admin_data)

        # First, perform a merge
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
        }

        merge_response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )
        assert merge_response.status_code == 200
        audit_id = merge_response.json()["audit_log_id"]

        # Get audit details
        details_response = await client.get(
            f"/api/v1/staff/patrons/merge-audit/{audit_id}",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert details_response.status_code == 200
        data = details_response.json()

        assert data["id"] == audit_id
        assert data["primary_patron_id"] == test_patron.id
        assert data["secondary_patron_id"] == secondary_patron.id
        assert data["data_archived"] is not None
        assert data["data_transferred"] is not None
        assert data["checkouts_transferred"] == 1

    async def test_merge_history_for_deleted_patron(
        self,
        client,
        test_admin,
        test_admin_data,
        test_staff,
        test_staff_data,
        test_patron,
        secondary_patron,
    ):
        """Test that merge history can be retrieved for a deleted patron ID."""
        secondary_id = secondary_patron.id

        # Perform the merge
        admin_token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_id,
        }

        merge_response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert merge_response.status_code == 200

        # Now check merge history for the deleted patron
        staff_token = await get_staff_token(client, test_staff_data)
        history_response = await client.get(
            f"/api/v1/staff/patrons/{secondary_id}/merge-history",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert history_response.status_code == 200
        data = history_response.json()
        assert data["patron_id"] == secondary_id
        assert len(data["as_primary"]) == 0
        assert len(data["as_secondary"]) == 1
        assert data["total_merges"] == 1

    async def test_merge_requires_admin(
        self,
        client,
        test_staff,
        test_staff_data,
        test_patron,
        secondary_patron,
    ):
        """Test that merge requires admin privileges."""
        token = await get_staff_token(client, test_staff_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 403

    async def test_merge_audit_details_requires_admin(
        self,
        client,
        test_admin,
        test_admin_data,
        test_staff,
        test_staff_data,
        test_patron,
        secondary_patron,
    ):
        """Test that merge audit details endpoint requires admin."""
        # First perform merge as admin
        admin_token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": secondary_patron.id,
        }

        merge_response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert merge_response.status_code == 200
        audit_id = merge_response.json()["audit_log_id"]

        # Try to get audit details as staff (should fail)
        staff_token = await get_staff_token(client, test_staff_data)
        details_response = await client.get(
            f"/api/v1/staff/patrons/merge-audit/{audit_id}",
            headers={"Authorization": f"Bearer {staff_token}"},
        )

        assert details_response.status_code == 403

    async def test_cannot_merge_patron_with_itself(
        self,
        client,
        test_admin,
        test_admin_data,
        test_patron,
    ):
        """Test that merging a patron with itself is rejected."""
        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": test_patron.id,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 400
        assert "itself" in _error_detail(response).lower()

    async def test_merge_nonexistent_patron(
        self,
        client,
        test_admin,
        test_admin_data,
        test_patron,
    ):
        """Test that merging with a nonexistent patron returns 404."""
        token = await get_admin_token(client, test_admin_data)
        merge_data = {
            "primary_patron_id": test_patron.id,
            "secondary_patron_id": 99999,
        }

        response = await client.post(
            "/api/v1/staff/patrons/merge",
            json=merge_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 404
