# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the PEN America ban-tracker CSV parser.

Exercises parse_csv_records directly (no DB, no network). These cover the
header-row-detection hardening: PEN's published sheet puts a banner and a
description row above the real header, and labels its ban column "Ban Status".
"""

from app.models.ban_tracker import BanType
from app.services.pen_america_sync_service import parse_csv_records


# A faithful miniature of PEN's published layout: two preamble rows (banner +
# description), then the real header in row 2, then data rows.
_PEN_LIKE_CSV = (
    "PEN America Index of School Book Bans,,,,\n"
    "Bans recorded during the listed school years. Contact pen.org for details.,,,,\n"
    "Title,Author,State,Date of Challenge/Removal,Ban Status\n"
    "Gender Queer,Maia Kobabe,FL,2023-09-01,Banned\n"
    "The Bluest Eye,Toni Morrison,TX,2023-10-15,Banned in Libraries\n"
)


def test_skips_preamble_and_parses_under_later_header_row():
    records = parse_csv_records(_PEN_LIKE_CSV)
    assert len(records) == 2
    titles = {r["title"] for r in records}
    assert titles == {"Gender Queer", "The Bluest Eye"}
    first = records[0]
    assert first["title"] == "Gender Queer"
    assert first["author"] == "Maia Kobabe"
    assert first["state"] == "FL"


def test_ban_status_column_maps_to_ban_type_banned():
    records = parse_csv_records(_PEN_LIKE_CSV)
    # "Banned" must resolve to BanType.BANNED, not the CHALLENGED default.
    by_title = {r["title"]: r for r in records}
    assert by_title["Gender Queer"]["ban_type"] is BanType.BANNED
    assert by_title["The Bluest Eye"]["ban_type"] is BanType.BANNED
    # And not everything defaults to CHALLENGED.
    assert all(r["ban_type"] is not BanType.CHALLENGED for r in records)


def test_no_recognizable_header_row_returns_empty():
    junk = (
        "just,some,unrelated,columns\n"
        "1,2,3,4\n"
        "5,6,7,8\n"
    )
    assert parse_csv_records(junk) == []
