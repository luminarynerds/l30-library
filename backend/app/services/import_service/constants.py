# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import re

from app.models.import_job import ImportJobType

# ── Field definitions per job type ────────────────────────────────────────

PATRON_REQUIRED_FIELDS = {"name", "email"}
PATRON_OPTIONAL_FIELDS = {
    "barcode", "phone", "address", "patron_type", "home_branch",
    "first_name", "last_name", "library_card",
}
PATRON_ALL_FIELDS = PATRON_REQUIRED_FIELDS | PATRON_OPTIONAL_FIELDS

CATALOG_REQUIRED_FIELDS = {"title"}
CATALOG_OPTIONAL_FIELDS = {
    "author", "isbn", "lccn", "oclc_number",
    "publisher", "publication_year", "item_type",
    "description", "call_number", "edition", "series_name", "series_number",
    "dewey_decimal", "lc_classification", "subjects",
}
CATALOG_ALL_FIELDS = CATALOG_REQUIRED_FIELDS | CATALOG_OPTIONAL_FIELDS

HOLDINGS_REQUIRED_FIELDS = {"item_barcode", "catalog_id"}
HOLDINGS_OPTIONAL_FIELDS = {
    "branch", "call_number", "condition", "status", "copy_number",
    "location", "replacement_cost", "acquisition_source",
}
HOLDINGS_ALL_FIELDS = HOLDINGS_REQUIRED_FIELDS | HOLDINGS_OPTIONAL_FIELDS

CIRC_REQUIRED_FIELDS = {"patron_barcode", "item_barcode", "checkout_date"}
CIRC_OPTIONAL_FIELDS = {"return_date"}
CIRC_ALL_FIELDS = CIRC_REQUIRED_FIELDS | CIRC_OPTIONAL_FIELDS

FINES_REQUIRED_FIELDS = {"patron_barcode", "amount", "reason"}
FINES_OPTIONAL_FIELDS = {"date_assessed", "item_barcode", "description"}
FINES_ALL_FIELDS = FINES_REQUIRED_FIELDS | FINES_OPTIONAL_FIELDS

HOLDS_REQUIRED_FIELDS = {"patron_barcode", "catalog_reference"}
HOLDS_OPTIONAL_FIELDS = {"hold_date", "position_in_queue", "pickup_branch", "hold_type"}
HOLDS_ALL_FIELDS = HOLDS_REQUIRED_FIELDS | HOLDS_OPTIONAL_FIELDS

POLICY_DIMENSION_FIELDS = {"role", "item_type", "binding"}
POLICY_KNOB_FIELDS = {
    "loan_period_days", "max_renewals", "overdue_fine_per_day", "max_fine",
    "grace_period_days", "hold_pickup_days", "fine_free",
}
POLICY_ALL_FIELDS = POLICY_DIMENSION_FIELDS | POLICY_KNOB_FIELDS | {"active"}
POLICY_REQUIRED_FIELDS = set()  # no hard-required column; the >=1-knob rule is enforced in validate()

TARGET_FIELDS = {
    ImportJobType.PATRONS: PATRON_ALL_FIELDS,
    ImportJobType.CATALOG_ITEMS: CATALOG_ALL_FIELDS,
    ImportJobType.HOLDINGS: HOLDINGS_ALL_FIELDS,
    ImportJobType.MARC_RECORDS: CATALOG_ALL_FIELDS,
    ImportJobType.CIRCULATION_HISTORY: CIRC_ALL_FIELDS,
    ImportJobType.FINES: FINES_ALL_FIELDS,
    ImportJobType.HOLDS: HOLDS_ALL_FIELDS,
    ImportJobType.POLICIES: POLICY_ALL_FIELDS,
}

REQUIRED_FIELDS = {
    ImportJobType.PATRONS: PATRON_REQUIRED_FIELDS,
    ImportJobType.CATALOG_ITEMS: CATALOG_REQUIRED_FIELDS,
    ImportJobType.HOLDINGS: HOLDINGS_REQUIRED_FIELDS,
    ImportJobType.MARC_RECORDS: set(),  # MARC validation is structural
    ImportJobType.CIRCULATION_HISTORY: CIRC_REQUIRED_FIELDS,
    ImportJobType.FINES: FINES_REQUIRED_FIELDS,
    ImportJobType.HOLDS: HOLDS_REQUIRED_FIELDS,
    ImportJobType.POLICIES: POLICY_REQUIRED_FIELDS,
}

# Simple ISBN-10/13 pattern (digits, optional hyphens, optional X check digit)
ISBN_PATTERN = re.compile(
    r"^(?:\d[\d\-]{8,15}[\dXx]?)$"
)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BARCODE_PATTERN = re.compile(r"^[A-Za-z0-9\-]{3,50}$")
