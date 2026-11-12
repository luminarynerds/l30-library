# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Pure row validation for bulk imports."""

from datetime import datetime

from app.models.catalog import ItemType
from app.models.circulation import HoldStatus
from app.models.fine import FineType
from app.models.user import UserRole

from .constants import BARCODE_PATTERN, EMAIL_PATTERN, ISBN_PATTERN
from .helpers import _parse_date


def _validate_patron_row(
    row: dict,
    row_num: int,
    errors: list[dict],
    warnings: list[dict],
) -> tuple[list[dict], list[dict]]:
    email = row.get("email", "").strip()
    if email and not EMAIL_PATTERN.match(email):
        errors.append({"field": "email", "message": f"Invalid email format: '{email}'"})

    barcode = row.get("barcode", "").strip()
    if barcode and not BARCODE_PATTERN.match(barcode):
        errors.append({"field": "barcode", "message": f"Invalid barcode format: '{barcode}'"})

    patron_type = row.get("patron_type", "").strip().lower()
    if patron_type:
        valid_types = {r.value for r in UserRole}
        if patron_type not in valid_types:
            warnings.append(
                {
                    "field": "patron_type",
                    "message": f"Unknown patron type '{patron_type}', will default to patron",
                }
            )

    return errors, warnings


def _validate_catalog_row(
    row: dict,
    row_num: int,
    errors: list[dict],
    warnings: list[dict],
) -> tuple[list[dict], list[dict]]:
    isbn = row.get("isbn", "").strip()
    if isbn and not ISBN_PATTERN.match(isbn.replace("-", "")):
        warnings.append({"field": "isbn", "message": f"ISBN format may be invalid: '{isbn}'"})

    pub_year = row.get("publication_year", "").strip()
    if pub_year:
        try:
            y = int(pub_year)
            if y < 1000 or y > datetime.now().year + 2:
                warnings.append({"field": "publication_year", "message": f"Unusual year: {y}"})
        except ValueError:
            errors.append(
                {"field": "publication_year", "message": f"Not a valid year: '{pub_year}'"}
            )

    item_type = row.get("item_type", "").strip().lower()
    if item_type:
        valid = {t.value for t in ItemType}
        if item_type not in valid:
            warnings.append(
                {
                    "field": "item_type",
                    "message": f"Unknown item type '{item_type}', will default to 'book'",
                }
            )

    return errors, warnings


def _validate_holdings_row(
    row: dict,
    row_num: int,
    errors: list[dict],
    warnings: list[dict],
) -> tuple[list[dict], list[dict]]:
    barcode = row.get("item_barcode", "").strip()
    if barcode and not BARCODE_PATTERN.match(barcode):
        errors.append({"field": "item_barcode", "message": f"Invalid barcode: '{barcode}'"})

    catalog_id = row.get("catalog_id", "").strip()
    if catalog_id:
        try:
            int(catalog_id)
        except ValueError:
            errors.append(
                {
                    "field": "catalog_id",
                    "message": f"catalog_id must be an integer: '{catalog_id}'",
                }
            )

    condition = row.get("condition", "").strip().lower()
    if condition:
        from app.models.inventory import ItemCondition

        valid = {c.value for c in ItemCondition}
        if condition not in valid:
            warnings.append(
                {
                    "field": "condition",
                    "message": f"Unknown condition '{condition}', will default to 'good'",
                }
            )

    return errors, warnings


def _validate_circ_row(
    row: dict,
    row_num: int,
    errors: list[dict],
    warnings: list[dict],
) -> tuple[list[dict], list[dict]]:
    checkout_date = row.get("checkout_date", "").strip()
    if checkout_date and _parse_date(checkout_date) is None:
        errors.append(
            {"field": "checkout_date", "message": f"Cannot parse date: '{checkout_date}'"}
        )

    return_date = row.get("return_date", "").strip()
    if return_date and _parse_date(return_date) is None:
        errors.append({"field": "return_date", "message": f"Cannot parse date: '{return_date}'"})

    return errors, warnings


def _validate_fines_row(
    row: dict,
    row_num: int,
    errors: list[dict],
    warnings: list[dict],
) -> tuple[list[dict], list[dict]]:
    patron_barcode = row.get("patron_barcode", "").strip()
    if patron_barcode and not BARCODE_PATTERN.match(patron_barcode):
        errors.append(
            {
                "field": "patron_barcode",
                "message": f"Invalid barcode format: '{patron_barcode}'",
            }
        )

    amount = row.get("amount", "").strip()
    if amount:
        try:
            val = float(amount)
            if val <= 0:
                errors.append(
                    {"field": "amount", "message": f"Amount must be positive, got: '{amount}'"}
                )
        except ValueError:
            errors.append(
                {"field": "amount", "message": f"Amount is not a valid number: '{amount}'"}
            )

    reason = row.get("reason", "").strip().lower()
    if reason:
        valid_reasons = {t.value for t in FineType}
        if reason not in valid_reasons:
            warnings.append(
                {
                    "field": "reason",
                    "message": f"Unknown fine reason '{reason}', will default to 'other'",
                }
            )

    date_assessed = row.get("date_assessed", "").strip()
    if date_assessed and _parse_date(date_assessed) is None:
        errors.append(
            {"field": "date_assessed", "message": f"Cannot parse date: '{date_assessed}'"}
        )

    item_barcode = row.get("item_barcode", "").strip()
    if item_barcode and not BARCODE_PATTERN.match(item_barcode):
        warnings.append(
            {
                "field": "item_barcode",
                "message": f"Invalid item barcode format: '{item_barcode}'",
            }
        )

    return errors, warnings


def _validate_holds_row(
    row: dict,
    row_num: int,
    errors: list[dict],
    warnings: list[dict],
) -> tuple[list[dict], list[dict]]:
    patron_barcode = row.get("patron_barcode", "").strip()
    if patron_barcode and not BARCODE_PATTERN.match(patron_barcode):
        errors.append(
            {
                "field": "patron_barcode",
                "message": f"Invalid barcode format: '{patron_barcode}'",
            }
        )

    catalog_ref = row.get("catalog_reference", "").strip()
    if not catalog_ref:
        errors.append({"field": "catalog_reference", "message": "catalog_reference is required"})

    hold_date = row.get("hold_date", "").strip()
    if hold_date and _parse_date(hold_date) is None:
        errors.append({"field": "hold_date", "message": f"Cannot parse date: '{hold_date}'"})

    position = row.get("position_in_queue", "").strip()
    if position:
        try:
            pos_val = int(position)
            if pos_val < 1:
                errors.append(
                    {
                        "field": "position_in_queue",
                        "message": f"Position must be >= 1, got: '{position}'",
                    }
                )
        except ValueError:
            errors.append(
                {
                    "field": "position_in_queue",
                    "message": f"Position is not a valid integer: '{position}'",
                }
            )

    hold_type = row.get("hold_type", "").strip().lower()
    if hold_type:
        valid_statuses = {s.value for s in HoldStatus}
        if hold_type not in valid_statuses:
            warnings.append(
                {
                    "field": "hold_type",
                    "message": f"Unknown hold type '{hold_type}', will default to 'pending'",
                }
            )

    return errors, warnings


def _validate_policies_row(
    row: dict,
    row_num: int,
    errors: list[dict],
    warnings: list[dict],
) -> tuple[list[dict], list[dict]]:
    from decimal import Decimal, InvalidOperation
    from app.models.catalog import BookBinding

    enum_cols = {"role": UserRole, "item_type": ItemType, "binding": BookBinding}
    int_cols = {"loan_period_days", "max_renewals", "grace_period_days", "hold_pickup_days"}
    dec_cols = {"overdue_fine_per_day", "max_fine"}
    knob_cols = int_cols | dec_cols | {"fine_free"}

    for col, enum_cls in enum_cols.items():
        val = (row.get(col) or "").strip()
        if val:
            try:
                enum_cls(val)
            except ValueError:
                errors.append({"field": col, "message": f"invalid {col}: {val!r}"})

    for col in int_cols:
        val = (row.get(col) or "").strip()
        if val:
            try:
                int(val)
            except ValueError:
                errors.append({"field": col, "message": f"{col} must be an integer"})

    for col in dec_cols:
        val = (row.get(col) or "").strip()
        if val:
            try:
                Decimal(val)
            except (InvalidOperation, ValueError):
                errors.append({"field": col, "message": f"{col} must be a number"})

    if not any((row.get(c) or "").strip() for c in knob_cols):
        errors.append(
            {
                "field": "loan_period_days",
                "message": "row has no policy values (at least one knob required)",
            }
        )

    return errors, warnings
