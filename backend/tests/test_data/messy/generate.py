# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic dirty-data generator for the import stress harness.

Run:  python -m tests.test_data.messy.generate
It (re)writes the committed fixture files in this directory. Output is
deterministic: re-running produces byte-identical files.

Each CSV interleaves known-good rows with seeded defects drawn from real
Koha/Sierra/Polaris export messiness. Every CSV ships with a sibling
<name>.manifest.json recording the expected pipeline outcome per data row.

Cross-reference notes:
  - HOLDINGS valid rows reference a parent catalog item by the literal token
    __CATALOG_ID__; the test substitutes the real id at upload time (catalog
    ids are not predictable across tests). The *_orphan file uses a numeric id
    guaranteed not to exist (999999).
  - CIRCULATION / FINES / HOLDS reference parents by natural keys
    (patron_barcode, item_barcode, ISBN), which the test seeds with those exact
    values. The *_orphan files reference barcodes/ISBNs that are never seeded.
"""

import csv
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# Real legacy-export junk used across files. Escapes used so the source is
# ASCII-safe; they decode to the intended dirty characters.
SMART_QUOTE_NAME = "O’Brien"          # curly apostrophe
NBSP_NAME = "Jane Doe"                 # non-breaking space
MOJIBAKE_TITLE = "CafÃ© Society"  # UTF-8 'e-acute' mis-decoded as Latin-1


def _write_csv(name, header, rows):
    """Write rows (list of dict) to <name> using header order. Returns path."""
    path = os.path.join(HERE, name)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=header, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    # Normalize line endings to \n for byte-stable output across platforms.
    data = buf.getvalue().replace("\r\n", "\n")
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(data)
    return path


def _write_manifest(name, job_type, specs):
    """specs: list of (row, defect_class, expected_outcome, note)."""
    path = os.path.join(HERE, name)
    payload = {
        "job_type": job_type,
        "rows": [
            {"row": r, "defect_class": d, "expected_outcome": o, "note": n}
            for (r, d, o, n) in specs
        ],
    }
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return path


def gen_patrons():
    header = ["name", "email", "barcode", "patron_type"]
    rows = [
        {"name": "Alice Johnson", "email": "alice@example.com",
         "barcode": "L30-AAAA-0001", "patron_type": "PATRON"},
        {"name": SMART_QUOTE_NAME, "email": "obrien@example.com",
         "barcode": "L30-AAAA-0002", "patron_type": "PATRON"},
        {"name": NBSP_NAME, "email": "jane@example.com",
         "barcode": "L30-AAAA-0003", "patron_type": "PATRON"},
        {"name": "  Bob  Spaces  ", "email": "  bob@example.com  ",
         "barcode": "L30-AAAA-0004", "patron_type": "patron"},
        {"name": "No Email", "email": "", "barcode": "L30-AAAA-0005",
         "patron_type": "PATRON"},
        {"name": "Bad Email", "email": "not-an-email",
         "barcode": "L30-AAAA-0006", "patron_type": "PATRON"},
        {"name": "Bad Barcode", "email": "bb@example.com",
         "barcode": "!!! bad !!!", "patron_type": "PATRON"},
        {"name": "Mystery Role", "email": "mr@example.com",
         "barcode": "L30-AAAA-0008", "patron_type": "WIZARD"},
        {"name": "Dup Alice", "email": "ALICE@EXAMPLE.COM",
         "barcode": "L30-AAAA-0009", "patron_type": "PATRON"},
    ]
    specs = [
        (1, "valid", "valid", "clean baseline row"),
        (2, "encoding_smart_quotes", "valid", "curly apostrophe in name"),
        (3, "encoding_nbsp", "valid", "non-breaking space in name"),
        (4, "whitespace_and_case", "valid", "leading/trailing spaces, lowercase type"),
        (5, "empty_required_email", "error", "email is required"),
        (6, "malformed_email", "error", "fails EMAIL_PATTERN"),
        (7, "malformed_barcode", "error", "fails BARCODE_PATTERN"),
        (8, "unknown_patron_type", "warning", "unknown type should warn not error"),
        (9, "duplicate_email_case", "duplicate", "same email as row 1, different case"),
    ]
    _write_csv("messy_patrons.csv", header, rows)
    _write_manifest("messy_patrons.manifest.json", "patrons", specs)


def gen_catalog():
    header = ["title", "author", "isbn", "publication_year", "item_type"]
    rows = [
        {"title": "The Great Gatsby", "author": "F. Scott Fitzgerald",
         "isbn": "9780743273565", "publication_year": "1925",
         "item_type": "book"},
        {"title": MOJIBAKE_TITLE, "author": "Anon",
         "isbn": "9780000000017", "publication_year": "2001",
         "item_type": "book"},
        {"title": "  Padded Title  ", "author": "  Spacey  ",
         "isbn": "9780000000024", "publication_year": "2010",
         "item_type": "BOOK"},
        {"title": "", "author": "No Title", "isbn": "9780000000031",
         "publication_year": "2010", "item_type": "book"},
        {"title": "Bad Year", "author": "X", "isbn": "9780000000048",
         "publication_year": "MCMXCIX", "item_type": "book"},
        {"title": "Hologram Media", "author": "Y", "isbn": "9780000000055",
         "publication_year": "2020", "item_type": "hologram"},
        {"title": "The Great Gatsby", "author": "F Scott Fitzgerald",
         "isbn": "9780000000062", "publication_year": "1925",
         "item_type": "book"},
    ]
    specs = [
        (1, "valid", "valid", "clean baseline row"),
        (2, "encoding_mojibake", "valid", "double-encoded accent in title"),
        (3, "whitespace_and_case", "valid", "padded fields, uppercase type"),
        (4, "empty_required_title", "error", "title is required"),
        (5, "non_numeric_year", "error", "validator flags non-numeric year"),
        (6, "unknown_item_type", "warning", "unknown type should warn"),
        (7, "near_duplicate_title_author", "duplicate",
         "same title, author missing a period; fuzzy >= 0.85 expected"),
    ]
    _write_csv("messy_catalog.csv", header, rows)
    _write_manifest("messy_catalog.manifest.json", "catalog_items", specs)


def gen_holdings():
    header = ["item_barcode", "catalog_id", "condition", "status"]
    rows = [
        {"item_barcode": "COPY-MESSY-001", "catalog_id": "__CATALOG_ID__",
         "condition": "good", "status": "available"},
        {"item_barcode": "COPY-MESSY-002", "catalog_id": "__CATALOG_ID__",
         "condition": "  Fair  ", "status": "available"},
        {"item_barcode": "", "catalog_id": "__CATALOG_ID__",
         "condition": "good", "status": "available"},
        {"item_barcode": "COPY-MESSY-004", "catalog_id": "abc",
         "condition": "good", "status": "available"},
    ]
    specs = [
        (1, "valid", "valid", "clean row, catalog_id substituted at upload"),
        (2, "whitespace_condition", "valid", "padded condition string"),
        (3, "empty_required_barcode", "error", "item_barcode required"),
        (4, "non_numeric_catalog_id", "error", "validator flags non-numeric id"),
    ]
    _write_csv("messy_holdings.csv", header, rows)
    _write_manifest("messy_holdings.manifest.json", "holdings", specs)

    orphan_rows = [
        {"item_barcode": "COPY-ORPHAN-001", "catalog_id": "999999",
         "condition": "good", "status": "available"},
    ]
    orphan_specs = [
        (1, "orphan_catalog_id", "orphan_fk",
         "numeric but nonexistent catalog_id; IntegrityError expected"),
    ]
    _write_csv("messy_holdings_orphan.csv", header, orphan_rows)
    _write_manifest("messy_holdings_orphan.manifest.json", "holdings", orphan_specs)


def gen_circulation():
    header = ["patron_barcode", "item_barcode", "checkout_date", "return_date"]
    # All rows are COMPLETED historical loans (each has a return_date) -- a copy
    # can only be physically out to one patron at a time, so circulation-HISTORY
    # import is overwhelmingly closed loans. (Two *open* loans on one copy is
    # corrupt data; that robustness gap is covered by a separate finding.) The
    # rows still exercise every date-format variant on checkout_date.
    rows = [
        {"patron_barcode": "L30-CIRC-0001", "item_barcode": "COPY-CIRC-001",
         "checkout_date": "2024-01-15", "return_date": "2024-02-01"},
        {"patron_barcode": "L30-CIRC-0001", "item_barcode": "COPY-CIRC-001",
         "checkout_date": "01/15/2024", "return_date": "2024-02-01"},
        {"patron_barcode": "L30-CIRC-0001", "item_barcode": "COPY-CIRC-001",
         "checkout_date": "13/02/2024", "return_date": "2024-03-01"},
        {"patron_barcode": "L30-CIRC-0001", "item_barcode": "COPY-CIRC-001",
         "checkout_date": "02/03/2024", "return_date": "2024-04-01"},
        {"patron_barcode": "L30-CIRC-0001", "item_barcode": "COPY-CIRC-001",
         "checkout_date": "not-a-date", "return_date": "2024-02-01"},
        {"patron_barcode": "L30-CIRC-0001", "item_barcode": "COPY-CIRC-001",
         "checkout_date": "", "return_date": "2024-02-01"},
    ]
    specs = [
        (1, "valid", "valid", "ISO checkout date, completed loan"),
        (2, "us_date_format", "valid", "MM/DD/YYYY accepted"),
        (3, "eu_date_format", "valid", "DD/MM/YYYY accepted when m/d impossible"),
        (4, "ambiguous_date", "valid",
         "02/03/2024 parses US-style (Feb 3) silently; see characterization test"),
        (5, "unparseable_date", "error", "no format matches"),
        (6, "empty_required_date", "error", "checkout_date required"),
    ]
    _write_csv("messy_circulation.csv", header, rows)
    _write_manifest("messy_circulation.manifest.json", "circulation_history", specs)

    orphan_rows = [
        {"patron_barcode": "L30-NOPE-9999", "item_barcode": "COPY-CIRC-001",
         "checkout_date": "2024-01-15", "return_date": ""},
        {"patron_barcode": "L30-CIRC-0001", "item_barcode": "COPY-NOPE-9999",
         "checkout_date": "2024-01-15", "return_date": ""},
    ]
    orphan_specs = [
        (1, "orphan_patron_barcode", "orphan_fk",
         "ValueError(Patron not found) expected -> FAILED, graceful"),
        (2, "orphan_item_barcode", "orphan_fk",
         "ValueError(Item not found) expected -> FAILED, graceful"),
    ]
    _write_csv("messy_circulation_orphan.csv", header, orphan_rows)
    _write_manifest("messy_circulation_orphan.manifest.json",
                    "circulation_history", orphan_specs)


def gen_fines():
    header = ["patron_barcode", "amount", "reason", "date_assessed",
              "item_barcode", "description"]
    rows = [
        {"patron_barcode": "L30-FINE-0001", "amount": "2.50",
         "reason": "overdue", "date_assessed": "2024-01-15",
         "item_barcode": "", "description": "late"},
        {"patron_barcode": "L30-FINE-0001", "amount": "$3.00",
         "reason": "overdue", "date_assessed": "2024-01-15",
         "item_barcode": "", "description": "currency symbol"},
        {"patron_barcode": "L30-FINE-0001", "amount": "",
         "reason": "overdue", "date_assessed": "2024-01-15",
         "item_barcode": "", "description": "no amount"},
    ]
    specs = [
        (1, "valid", "valid", "clean fine"),
        (2, "currency_symbol_amount", "error",
         "leading $ in amount; record actual handling"),
        (3, "empty_required_amount", "error", "amount required"),
    ]
    _write_csv("messy_fines.csv", header, rows)
    _write_manifest("messy_fines.manifest.json", "fines", specs)


def gen_holds():
    header = ["patron_barcode", "catalog_reference", "hold_date",
              "position_in_queue", "pickup_branch", "hold_type"]
    rows = [
        {"patron_barcode": "L30-HOLD-0001", "catalog_reference": "9780743273565",
         "hold_date": "2024-01-15", "position_in_queue": "1",
         "pickup_branch": "main", "hold_type": "standard"},
        {"patron_barcode": "L30-HOLD-0001", "catalog_reference": "9780743273565",
         "hold_date": "15/01/2024", "position_in_queue": "two",
         "pickup_branch": "main", "hold_type": "standard"},
    ]
    specs = [
        (1, "valid", "valid", "hold referencing seeded ISBN"),
        (2, "eu_date_and_bad_position", "error",
         "non-numeric queue position 'two' is correctly rejected (a malformed "
         "position is an error, not a silently-defaulted warning)"),
    ]
    _write_csv("messy_holds.csv", header, rows)
    _write_manifest("messy_holds.manifest.json", "holds", specs)


def generate_all():
    gen_patrons()
    gen_catalog()
    gen_holdings()
    gen_circulation()
    gen_fines()
    gen_holds()


if __name__ == "__main__":
    generate_all()
    print("messy fixtures regenerated in", HERE)
