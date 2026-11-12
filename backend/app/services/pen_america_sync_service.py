# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import csv
import io
from app.core.logging import get_logger
from datetime import date, datetime, timezone
from typing import Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ban_tracker import BanReport, BanSource, BanType
from .ban_tracker_service import BanTrackerService

logger = get_logger(__name__)

# PEN America publishes their Index of School Book Bans via Google Sheets.
# The CSV export URL lives in settings (pen_america_sheet_csv_url) so it can be
# updated via env var when PEN changes their sheet ID, without a code change.

# Common column name mappings (PEN America has used several header variations)
_COLUMN_ALIASES = {
    "title": ["title", "book title", "book_title"],
    "author": ["author", "author(s)", "authors", "author_name"],
    "isbn": ["isbn", "isbn-13", "isbn13"],
    "state": ["state", "state_code", "st"],
    "district": ["district", "school district", "district_name"],
    "institution": ["institution", "school", "library", "institution_name"],
    "ban_type": ["ban status", "type of ban", "ban type", "ban_type", "type", "action"],
    "date_reported": ["date of challenge/removal", "date", "date_reported", "date reported"],
    "reason": ["reason", "reason for ban", "rationale", "reason_category"],
}


def _normalize_header(header: str) -> str:
    return header.strip().lower().replace("\ufeff", "")


def _map_columns(headers: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    normalized = [_normalize_header(h) for h in headers]

    for field, aliases in _COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in normalized:
                mapping[field] = normalized.index(alias)
                break

    return mapping


def _parse_ban_type(raw: str) -> BanType:
    raw_upper = raw.strip().upper()
    if "BAN" in raw_upper and "CHALLENGE" not in raw_upper:
        return BanType.BANNED
    if "RESTRICT" in raw_upper:
        return BanType.RESTRICTED
    if "PEND" in raw_upper:
        return BanType.PENDING
    return BanType.CHALLENGED


# Day-precision formats are tried first so an exact date always wins. The
# month-precision formats at the end are what PEN actually publishes: every
# dated row in their sheet reads "August 2023", never "August 15, 2023".
# strptime resolves those to the first of the month.
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%m/%d/%Y",
    "%m/%d/%y",
    "%m-%d-%Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%B %Y",
    "%b %Y",
)


def _parse_date(raw: str) -> Optional[date]:
    """Parse a challenge date, resolving month-precision values to day 1.

    Returns None for anything that names no month -- a bare year, or a season
    word like "Fall 2023" (13 rows in the 2023-24 sheet). Mapping a season onto
    a month would invent precision the source never gave, so those stay unset.
    """
    raw = raw.strip()
    if not raw:
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    return None


def _categorize_reason(raw: str) -> str:
    raw_lower = raw.lower()
    if any(kw in raw_lower for kw in ("sexual", "sex", "explicit", "pornograph")):
        return "sexual_content"
    if any(
        kw in raw_lower
        for kw in ("lgbtq", "gay", "lesbian", "trans", "queer", "gender identity", "homosexual")
    ):
        return "lgbtq"
    if any(kw in raw_lower for kw in ("race", "racial", "racism", "crt", "critical race")):
        return "race"
    if any(kw in raw_lower for kw in ("violen", "profanity", "language", "profane")):
        return "violence_profanity"
    if any(kw in raw_lower for kw in ("religion", "religious", "witchcraft", "occult")):
        return "religion"
    if any(kw in raw_lower for kw in ("drug", "alcohol", "substance")):
        return "drugs_alcohol"
    return "other"


# US state name -> code lookup
_STATE_NAME_TO_CODE = {
    "alabama": "AL",
    "alaska": "AK",
    "arizona": "AZ",
    "arkansas": "AR",
    "california": "CA",
    "colorado": "CO",
    "connecticut": "CT",
    "delaware": "DE",
    "florida": "FL",
    "georgia": "GA",
    "hawaii": "HI",
    "idaho": "ID",
    "illinois": "IL",
    "indiana": "IN",
    "iowa": "IA",
    "kansas": "KS",
    "kentucky": "KY",
    "louisiana": "LA",
    "maine": "ME",
    "maryland": "MD",
    "massachusetts": "MA",
    "michigan": "MI",
    "minnesota": "MN",
    "mississippi": "MS",
    "missouri": "MO",
    "montana": "MT",
    "nebraska": "NE",
    "nevada": "NV",
    "new hampshire": "NH",
    "new jersey": "NJ",
    "new mexico": "NM",
    "new york": "NY",
    "north carolina": "NC",
    "north dakota": "ND",
    "ohio": "OH",
    "oklahoma": "OK",
    "oregon": "OR",
    "pennsylvania": "PA",
    "rhode island": "RI",
    "south carolina": "SC",
    "south dakota": "SD",
    "tennessee": "TN",
    "texas": "TX",
    "utah": "UT",
    "vermont": "VT",
    "virginia": "VA",
    "washington": "WA",
    "west virginia": "WV",
    "wisconsin": "WI",
    "wyoming": "WY",
}
_VALID_STATE_CODES = set(_STATE_NAME_TO_CODE.values())


def _normalize_state(raw: str) -> Optional[str]:
    raw = raw.strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in _VALID_STATE_CODES:
        return upper
    code = _STATE_NAME_TO_CODE.get(raw.lower())
    return code


def _is_header_row(row: list[str]) -> bool:
    """A row is the header if its normalized cells contain 'title' AND
    ('author' OR 'state'). PEN's published sheet puts a banner + description in
    the first two rows and the real header below them, so we cannot assume the
    header is row 0."""
    normalized = {_normalize_header(cell) for cell in row}
    return "title" in normalized and ("author" in normalized or "state" in normalized)


def parse_csv_records(csv_text: str) -> list[dict]:
    all_rows = list(csv.reader(io.StringIO(csv_text)))

    header_idx = None
    for idx, row in enumerate(all_rows):
        if _is_header_row(row):
            header_idx = idx
            break

    if header_idx is None:
        logger.error(
            "CSV missing recognizable header row (need 'title' + 'author'/'state'). First row: %s",
            all_rows[0] if all_rows else "<empty>",
        )
        return []

    headers = all_rows[header_idx]
    col_map = _map_columns(headers)

    if "title" not in col_map:
        logger.error("CSV missing required 'title' column. Headers: %s", headers)
        return []

    records: list[dict] = []
    for row_num, row in enumerate(all_rows[header_idx + 1 :], start=header_idx + 2):
        if not any(cell.strip() for cell in row):
            continue  # skip blank rows

        title = (
            row[col_map["title"]].strip()
            if "title" in col_map and col_map["title"] < len(row)
            else ""
        )
        if not title:
            continue

        author = (
            row[col_map["author"]].strip()
            if "author" in col_map and col_map["author"] < len(row)
            else "Unknown"
        )

        record: dict = {
            "title": title,
            "author": author,
            "source": BanSource.PEN_AMERICA,
        }

        if "isbn" in col_map and col_map["isbn"] < len(row):
            isbn = row[col_map["isbn"]].strip().replace("-", "")
            if isbn and isbn.isdigit() and len(isbn) in (10, 13):
                record["isbn"] = isbn

        if "state" in col_map and col_map["state"] < len(row):
            state = _normalize_state(row[col_map["state"]])
            if state:
                record["state"] = state

        if "district" in col_map and col_map["district"] < len(row):
            district = row[col_map["district"]].strip()
            if district:
                record["district"] = district

        if "institution" in col_map and col_map["institution"] < len(row):
            institution = row[col_map["institution"]].strip()
            if institution:
                record["institution"] = institution

        if "ban_type" in col_map and col_map["ban_type"] < len(row):
            record["ban_type"] = _parse_ban_type(row[col_map["ban_type"]])
        else:
            record["ban_type"] = BanType.CHALLENGED

        if "date_reported" in col_map and col_map["date_reported"] < len(row):
            parsed_date = _parse_date(row[col_map["date_reported"]])
            if parsed_date:
                record["date_reported"] = parsed_date

        if "reason" in col_map and col_map["reason"] < len(row):
            reason_raw = row[col_map["reason"]].strip()
            if reason_raw:
                record["reason"] = reason_raw
                record["reason_category"] = _categorize_reason(reason_raw)

        records.append(record)

    logger.info("Parsed %d records from CSV (%d columns mapped)", len(records), len(col_map))
    return records


class PenAmericaSyncService:
    @staticmethod
    async def sync(db: AsyncSession) -> dict:
        stats = {
            "new_reports": 0,
            "duplicates_skipped": 0,
            "matches_found": 0,
            "errors": 0,
        }

        raw_records = await PenAmericaSyncService._fetch_data()
        if not raw_records:
            logger.info("PEN America sync: no records to process.")
            return stats

        new_records = await PenAmericaSyncService._deduplicate(db, raw_records)
        stats["duplicates_skipped"] = len(raw_records) - len(new_records)

        for record_dict in new_records:
            try:
                report = await PenAmericaSyncService._process_record(db, record_dict)
                stats["new_reports"] += 1
                if report.catalog_match_id is not None:
                    stats["matches_found"] += 1
            except Exception as exc:  # noqa: BLE001
                stats["errors"] += 1
                logger.error(
                    "PEN America sync: error processing record '%s': %s",
                    record_dict.get("title", "<unknown>"),
                    exc,
                )

        logger.info(
            "PEN America sync complete: %d new, %d skipped, %d matched, %d errors",
            stats["new_reports"],
            stats["duplicates_skipped"],
            stats["matches_found"],
            stats["errors"],
        )
        return stats

    @staticmethod
    async def sync_from_csv(db: AsyncSession, csv_text: str) -> dict:
        stats = {
            "new_reports": 0,
            "duplicates_skipped": 0,
            "matches_found": 0,
            "errors": 0,
            "total_parsed": 0,
        }

        raw_records = parse_csv_records(csv_text)
        stats["total_parsed"] = len(raw_records)

        if not raw_records:
            return stats

        new_records = await PenAmericaSyncService._deduplicate(db, raw_records)
        stats["duplicates_skipped"] = len(raw_records) - len(new_records)

        for record_dict in new_records:
            try:
                report = await PenAmericaSyncService._process_record(db, record_dict)
                stats["new_reports"] += 1
                if report.catalog_match_id is not None:
                    stats["matches_found"] += 1
            except Exception as exc:  # noqa: BLE001
                stats["errors"] += 1
                logger.error(
                    "CSV import: error processing record '%s': %s",
                    record_dict.get("title", "<unknown>"),
                    exc,
                )

        logger.info(
            "CSV import complete: %d parsed, %d new, %d skipped, %d matched, %d errors",
            stats["total_parsed"],
            stats["new_reports"],
            stats["duplicates_skipped"],
            stats["matches_found"],
            stats["errors"],
        )
        return stats

    @staticmethod
    async def _fetch_data() -> list[dict]:
        # Imported locally to avoid any import-time circular dependency.
        from app.core.config import get_settings

        url = get_settings().pen_america_sheet_csv_url
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
                csv_text = response.text
        except httpx.HTTPStatusError as exc:
            logger.error(
                "PEN America fetch HTTP error %s for %s: %s",
                exc.response.status_code,
                url,
                exc.response.text[:200],
            )
            # Fail loud: a dead/moved sheet must surface as a FAILED job run,
            # not a silent 0-import "success".
            raise RuntimeError(
                f"PEN America fetch failed: HTTP {exc.response.status_code} for {url}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("PEN America fetch request error for %s: %s", url, exc)
            raise RuntimeError(f"PEN America fetch failed: request error for {url}: {exc}") from exc

        records = parse_csv_records(csv_text)
        if csv_text.strip() and not records:
            # 200 OK with a non-empty body but zero parsed rows means the sheet's
            # layout/schema drifted (e.g. header row moved or columns renamed).
            # Surface it instead of logging a false success.
            raise ValueError(
                "PEN America fetch returned a non-empty response but parsed 0 records "
                f"from {url}; likely a header/layout/schema change in the published sheet."
            )
        logger.info("PEN America fetch: parsed %d records from remote sheet", len(records))
        return records

    @staticmethod
    async def _deduplicate(db: AsyncSession, records: list[dict]) -> list[dict]:
        new_records: list[dict] = []

        for record in records:
            isbn = record.get("isbn") or None
            title = record.get("title", "")
            author = record.get("author", "")
            state = record.get("state") or None
            district = record.get("district") or None

            if isbn:
                existing_result = await db.execute(
                    select(BanReport.id).where(
                        BanReport.isbn == isbn,
                        BanReport.state == state,
                        BanReport.district == district,
                    )
                )
            else:
                existing_result = await db.execute(
                    select(BanReport.id).where(
                        BanReport.title == title,
                        BanReport.author == author,
                        BanReport.state == state,
                        BanReport.district == district,
                    )
                )

            if existing_result.scalar_one_or_none() is None:
                new_records.append(record)

        return new_records

    @staticmethod
    async def _process_record(db: AsyncSession, record_dict: dict) -> BanReport:
        record_dict = dict(record_dict)
        record_dict["source"] = BanSource.PEN_AMERICA

        report = await BanTrackerService.create_report(db, record_dict)
        return report

    @staticmethod
    async def get_sync_status(db: AsyncSession) -> dict:
        result = await db.execute(
            select(BanReport.created_at)
            .where(BanReport.source == BanSource.PEN_AMERICA)
            .order_by(BanReport.created_at.desc())
            .limit(1)
        )
        last_created_at = result.scalar_one_or_none()

        count_result = await db.execute(
            select(BanReport.id).where(BanReport.source == BanSource.PEN_AMERICA)
        )
        total = len(count_result.scalars().all())

        return {
            "last_sync_time": last_created_at.isoformat() if last_created_at else None,
            "total_pen_america_records": total,
            "fetch_configured": True,
        }
