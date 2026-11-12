# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""File readers for bulk import jobs."""

import csv
import json
import re

from app.core.logging import get_logger
from app.models.import_job import ImportFileFormat, ImportJob

logger = get_logger(__name__)


async def read_rows(job: ImportJob) -> list[dict[str, str]]:
    if job.file_format == ImportFileFormat.CSV:
        return read_csv(job.source_file_path)
    if job.file_format in (ImportFileFormat.MARC21, ImportFileFormat.MARCXML):
        return read_marc(job.source_file_path, job.file_format)
    if job.file_format == ImportFileFormat.JSON:
        return read_json(job.source_file_path)
    return []


def read_csv(path: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with open(path, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            cleaned = {
                key.strip().lower().replace(" ", "_"): (value.strip() if value else "")
                for key, value in row.items()
                if key is not None
            }
            rows.append(cleaned)
    return rows


def read_marc(path: str, file_format: ImportFileFormat) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    try:
        import pymarc

        if file_format == ImportFileFormat.MARC21:
            with open(path, "rb") as file:
                reader = pymarc.MARCReader(file, to_unicode=True)
                for record in reader:
                    if record is not None:
                        rows.append(marc_to_dict(record))
        else:
            for record in pymarc.parse_xml_to_array(path):
                rows.append(marc_to_dict(record))
    except ImportError:
        logger.error("pymarc not installed - cannot parse MARC files")
    except (OSError, IOError, ValueError, KeyError) as exc:
        logger.error(
            f"MARC parse error: {exc}",
            extra={"error_type": type(exc).__name__, "path": path},
        )
    return rows


def marc_to_dict(record) -> dict[str, str]:
    data: dict[str, str] = {}

    title_field = record.get("245")
    if title_field:
        parts = []
        if title_field.get("a"):
            parts.append(title_field["a"].rstrip(" /:;"))
        if title_field.get("b"):
            parts.append(title_field["b"].rstrip(" /:;"))
        data["title"] = " ".join(parts)

    author_field = record.get("100")
    if author_field and author_field.get("a"):
        data["author"] = author_field["a"].rstrip(",. ")

    isbn_field = record.get("020")
    if isbn_field and isbn_field.get("a"):
        data["isbn"] = isbn_field["a"].split()[0]

    lccn_field = record.get("010")
    if lccn_field and lccn_field.get("a"):
        lccn_value = lccn_field["a"].strip().split()[0].replace("-", "")
        if lccn_value:
            data["lccn"] = lccn_value

    for field in record.get_fields("035"):
        value = (field.get("a") or "").strip()
        if not value or "(OCoLC)" not in value:
            continue
        cleaned = value.split("(OCoLC)", 1)[1].strip()
        for prefix in ("ocm", "ocn", "on"):
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix) :]
                break
        cleaned = cleaned.lstrip("0") or "0"
        if cleaned:
            data["oclc_number"] = cleaned
            break

    publication_field = record.get("264") or record.get("260")
    if publication_field:
        if publication_field.get("b"):
            data["publisher"] = publication_field["b"].rstrip(",. ")
        if publication_field.get("c"):
            year_match = re.search(r"\d{4}", publication_field["c"])
            if year_match:
                data["publication_year"] = year_match.group()

    lcc = record.get("050")
    if lcc and lcc.get("a"):
        data["lc_classification"] = lcc["a"]
    dewey = record.get("082")
    if dewey and dewey.get("a"):
        data["dewey_decimal"] = dewey["a"]

    description_field = record.get("520")
    if description_field and description_field.get("a"):
        data["description"] = description_field["a"]

    subjects = []
    for field in record.get_fields("650"):
        if field.get("a"):
            subjects.append(field["a"].rstrip(". "))
    if subjects:
        data["subjects"] = "; ".join(subjects)

    data["item_type"] = "book"
    return data


def read_json(path: str) -> list[dict[str, str]]:
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)
    if isinstance(data, list):
        return [
            {key: str(value) if value is not None else "" for key, value in item.items()}
            for item in data
        ]
    return []
