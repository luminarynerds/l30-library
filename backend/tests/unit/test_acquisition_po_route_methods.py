# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression tests for acquisition purchase-order item route methods."""

from pathlib import Path


def test_item_create_endpoint_is_not_exposed_as_get() -> None:
    """Creating PO line items must not be possible via GET requests."""
    source = Path("app/api/v1/acquisition/po.py").read_text()
    assert '@router.get("/purchase-orders/{po_id}/items"' not in source
    assert '@router.post("/purchase-orders/{po_id}/items"' in source


def test_item_delete_endpoint_is_not_exposed_as_get() -> None:
    """Deleting PO line items must not be possible via GET requests."""
    source = Path("app/api/v1/acquisition/po.py").read_text()
    assert '@router.get("/purchase-orders/{po_id}/items/{item_id}"' not in source
    assert '@router.delete("/purchase-orders/{po_id}/items/{item_id}"' in source
