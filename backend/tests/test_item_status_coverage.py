# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Tests to verify all required item statuses exist and are correctly defined.

Covers the 12 core statuses required for LSC catalog and staff views:
AVAILABLE, CHECKED_OUT, ON_HOLD, IN_TRANSIT, ON_ORDER, IN_PROCESSING,
MISSING, LOST, DAMAGED, WITHDRAWN, REFERENCE, RESTRICTED.
"""

import pytest

from app.models.catalog import CatalogItem, ItemStatus


# The 12 required item statuses
REQUIRED_STATUSES = [
    ("available", "AVAILABLE", "ready for checkout"),
    ("checked_out", "CHECKED_OUT", "currently on loan"),
    ("on_hold", "ON_HOLD", "on hold shelf waiting for patron"),
    ("in_transit", "IN_TRANSIT", "between branches"),
    ("on_order", "ON_ORDER", "ordered but not received"),
    ("in_processing", "IN_PROCESSING", "being cataloged"),
    ("missing", "MISSING", "can't be located"),
    ("lost", "LOST", "declared lost"),
    ("damaged", "DAMAGED", "needs repair"),
    ("withdrawn", "WITHDRAWN", "removed from collection"),
    ("reference", "REFERENCE", "non-circulating"),
    ("restricted", "RESTRICTED", "special access required"),
]


@pytest.mark.unit
class TestItemStatusEnum:
    """Verify ItemStatus enum has all required values."""

    @pytest.mark.parametrize(
        "status_value,status_name,description",
        REQUIRED_STATUSES,
        ids=[s[1] for s in REQUIRED_STATUSES],
    )
    def test_status_exists_in_enum(self, status_value, status_name, description):
        """Each required status must exist as an ItemStatus enum member."""
        status = ItemStatus(status_value)
        assert status.value == status_value

    def test_all_twelve_required_statuses_present(self):
        """All 12 required statuses must be present in ItemStatus."""
        required_values = {s[0] for s in REQUIRED_STATUSES}
        enum_values = {s.value for s in ItemStatus}
        missing = required_values - enum_values
        assert not missing, f"Missing required statuses: {missing}"

    def test_status_is_string_enum(self):
        """ItemStatus must inherit from str for JSON serialization."""
        assert issubclass(ItemStatus, str)

    def test_status_values_are_snake_case(self):
        """All status values should be lowercase snake_case."""
        for status in ItemStatus:
            assert status.value == status.value.lower(), (
                f"Status {status.name} has non-lowercase value: {status.value}"
            )
            assert " " not in status.value, (
                f"Status {status.name} has spaces in value: {status.value}"
            )


@pytest.mark.unit
class TestItemStatusOnModel:
    """Verify statuses can be assigned to CatalogItem model instances."""

    @pytest.mark.parametrize(
        "status_value,status_name,description",
        REQUIRED_STATUSES,
        ids=[s[1] for s in REQUIRED_STATUSES],
    )
    def test_catalog_item_accepts_status(self, status_value, status_name, description):
        """CatalogItem.status field must accept each required status."""
        item = CatalogItem(
            title=f"Test Item - {status_name}",
            author="Test Author",
            status=ItemStatus(status_value),
        )
        assert item.status == ItemStatus(status_value)
        assert item.status.value == status_value

    def test_default_status_column_default(self):
        """ItemStatus column default should be 'available'."""
        status_col = CatalogItem.__table__.columns["status"]
        assert status_col.default.arg == ItemStatus.available


@pytest.mark.unit
class TestItemStatusSerialization:
    """Verify statuses serialize correctly for API responses."""

    @pytest.mark.parametrize(
        "status_value,status_name,description",
        REQUIRED_STATUSES,
        ids=[s[1] for s in REQUIRED_STATUSES],
    )
    def test_status_serializes_to_string(self, status_value, status_name, description):
        """ItemStatus values must serialize to their string value."""
        status = ItemStatus(status_value)
        # str(enum) should work for JSON serialization
        assert str(status.value) == status_value

    def test_status_schema_includes_all_required(self):
        """Pydantic schema should accept all 12 required statuses."""
        from app.schemas.catalog import CatalogItemUpdate

        for status_value, _, _ in REQUIRED_STATUSES:
            update = CatalogItemUpdate(status=ItemStatus(status_value))
            assert update.status == ItemStatus(status_value)

    def test_status_searchable_in_params(self):
        """CatalogSearchParams should accept all required statuses."""
        from app.schemas.catalog import CatalogSearchParams

        for status_value, _, _ in REQUIRED_STATUSES:
            params = CatalogSearchParams(status=ItemStatus(status_value))
            assert params.status == ItemStatus(status_value)
