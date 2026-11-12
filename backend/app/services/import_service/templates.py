# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from typing import Any

from app.core.branding import branding
from app.models.import_job import ImportJobType

# ── CSV template definitions ─────────────────────────────────────────────

TEMPLATES: dict[ImportJobType, dict[str, Any]] = {
    ImportJobType.PATRONS: {
        "filename": "patron_import_template.csv",
        "description": "Import patron accounts with contact information",
        "columns": [
            "name", "email", "barcode", "phone", "address",
            "patron_type", "home_branch",
        ],
        "sample_row": {
            "name": "Jane Doe",
            "email": "jane.doe@example.com",
            "barcode": f"{branding.CARD_PREFIX}-1234-5678",
            "phone": "555-0100",
            "address": "123 Main St, Anytown, ST 12345",
            "patron_type": "patron",
            "home_branch": "MAIN",
        },
    },
    ImportJobType.CATALOG_ITEMS: {
        "filename": "catalog_import_template.csv",
        "description": "Import catalog / bibliographic records",
        "columns": [
            "title", "author", "isbn", "publisher", "publication_year",
            "item_type", "description", "call_number",
        ],
        "sample_row": {
            "title": "The Great Gatsby",
            "author": "F. Scott Fitzgerald",
            "isbn": "978-0-7432-7356-5",
            "publisher": "Scribner",
            "publication_year": "1925",
            "item_type": "book",
            "description": "A novel set in the Jazz Age",
            "call_number": "FIC FIT",
        },
    },
    ImportJobType.HOLDINGS: {
        "filename": "holdings_import_template.csv",
        "description": "Import physical item copies / holdings",
        "columns": [
            "item_barcode", "catalog_id", "branch", "call_number",
            "condition", "status", "copy_number", "location",
        ],
        "sample_row": {
            "item_barcode": "COPY-0001",
            "catalog_id": "1",
            "branch": "MAIN",
            "call_number": "FIC FIT",
            "condition": "new",
            "status": "available",
            "copy_number": "1",
            "location": "Fiction A-G",
        },
    },
    ImportJobType.CIRCULATION_HISTORY: {
        "filename": "circulation_history_template.csv",
        "description": "Import historical checkout / return records",
        "columns": [
            "patron_barcode", "item_barcode", "checkout_date", "return_date",
        ],
        "sample_row": {
            "patron_barcode": f"{branding.CARD_PREFIX}-1234-5678",
            "item_barcode": "COPY-0001",
            "checkout_date": "2024-01-15",
            "return_date": "2024-02-05",
        },
    },
    ImportJobType.FINES: {
        "filename": "fines_import_template.csv",
        "description": "Import patron fines and fees",
        "columns": [
            "patron_barcode", "amount", "reason", "date_assessed",
            "item_barcode", "description",
        ],
        "sample_row": {
            "patron_barcode": f"{branding.CARD_PREFIX}-1234-5678",
            "amount": "5.50",
            "reason": "overdue",
            "date_assessed": "2024-03-01",
            "item_barcode": "COPY-0001",
            "description": "Overdue fine for 11 days",
        },
    },
    ImportJobType.HOLDS: {
        "filename": "holds_import_template.csv",
        "description": "Import patron hold requests",
        "columns": [
            "patron_barcode", "catalog_reference", "hold_date",
            "position_in_queue", "pickup_branch", "hold_type",
        ],
        "sample_row": {
            "patron_barcode": f"{branding.CARD_PREFIX}-1234-5678",
            "catalog_reference": "978-0-7432-7356-5",
            "hold_date": "2024-03-01",
            "position_in_queue": "1",
            "pickup_branch": "MAIN",
            "hold_type": "pending",
        },
    },
    ImportJobType.POLICIES: {
        "filename": "circulation_policies_template.csv",
        "description": (
            "Import circulation policies (per role / item type / binding). "
            "loan_period_days is enforced today; overdue_fine_per_day, max_fine and "
            "max_renewals are stored but NOT yet enforced (the library is fine-free)."
        ),
        "columns": [
            "role", "item_type", "binding",
            "loan_period_days", "max_renewals", "overdue_fine_per_day",
            "max_fine", "grace_period_days", "hold_pickup_days", "fine_free", "active",
        ],
        "sample_row": {
            "role": "patron", "item_type": "book", "binding": "",
            "loan_period_days": "21", "max_renewals": "2", "overdue_fine_per_day": "",
            "max_fine": "", "grace_period_days": "0", "hold_pickup_days": "7",
            "fine_free": "true", "active": "true",
        },
    },
}
