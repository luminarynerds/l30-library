# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
import hashlib
import json
from app.core.logging import get_logger
import os
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from io import BytesIO
from typing import Optional, List, Dict
from urllib.parse import urlencode

import httpx
import pymarc
import redis.asyncio as aioredis
from pymarc import Record
from sqlalchemy import select

from app.core.config import get_settings
from app.core.database import get_async_session
from app.core.datetime_utils import utc_now
from app.models.system_status import (
    IssueComponent,
    SystemStatus,
    SystemStatusLog,
)

logger = get_logger(__name__)


class Z3950Error(Exception):
    pass


def _load_z3950_sources() -> Dict:
    # First, try to load from JSON environment variable for advanced use cases
    z3950_json_str = os.getenv("Z3950_SOURCES_JSON")
    if z3950_json_str:
        try:
            return json.loads(z3950_json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse Z3950_SOURCES_JSON: {e}")

    # Fall back to individual environment variables with sensible defaults
    sources = {}

    # Library of Congress configuration
    loc_config = {
        "name": "Library of Congress",
        "host": os.getenv("Z3950_LOC_HOST", "lx2.loc.gov"),
        "port": int(os.getenv("Z3950_LOC_PORT", "210")),
        "database": os.getenv("Z3950_LOC_DATABASE", "LCDB"),
        "syntax": "USMARC",
        "encoding": "UTF-8",
        "sru_url": os.getenv(
            "Z3950_LOC_SRU_URL",
            "https://lx2.loc.gov/sru/lcdb",
        ),
    }
    sources["loc"] = loc_config

    # OCLC WorldCat configuration
    oclc_config = {
        "name": "OCLC WorldCat",
        "host": os.getenv("Z3950_OCLC_HOST", "z3950.oclc.org"),
        "port": int(os.getenv("Z3950_OCLC_PORT", "210")),
        "database": os.getenv("Z3950_OCLC_DATABASE", "OLUCWorldCat"),
        "syntax": "USMARC",
        "encoding": "UTF-8",
        # Note: OCLC requires authentication/subscription
        "requires_auth": os.getenv("Z3950_OCLC_REQUIRES_AUTH", "true").lower() == "true",
    }
    sources["oclc"] = oclc_config

    return sources


# Z39.50 connection settings for major sources - loaded from environment
Z3950_SOURCES = _load_z3950_sources()


# SRU XML namespaces
_SRU_NS = "http://www.loc.gov/zing/srw/"
_MARC_NS = "http://www.loc.gov/MARC21/slim"

# Retry transient upstream errors from SRU sources (LOC's lx2 proxy intermittently
# returns 5xx or drops TCP mid-response when its backend pool is degraded).
# Idempotent search → safe to retry.
_SRU_RETRYABLE_STATUS = {502, 503, 504}
# Per-attempt timeout stays 30s: LOC's lx2 returns slow-but-OK at ~16-27s.
# Total work is bounded under nginx's /api/ proxy_read_timeout (60s): 2 x 30s,
# instead of 3 x 30s = 90s that overran the edge and hammered a dead upstream.
_SRU_TIMEOUT_SECONDS = 30.0
_SRU_MAX_ATTEMPTS = 2
_SRU_BACKOFF_BASE_SECONDS = 0.5

# Stale-on-error cache: keep the last good SRU response per exact query so a
# repeat lookup still works while the live source is down. Bib records are
# stable, so a long TTL is fine. Best-effort; never breaks the search path.
_SRU_CACHE_KEY_PREFIX = "sru:cache:"
_SRU_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60

# Status-page integration: a Redis flag prevents duplicate SystemStatusLog rows
# when the upstream is flapping. TTL is a safety net for missed recovery writes.
_SRU_STATUS_KEY_PREFIX = "sru:degraded:"
_SRU_STATUS_KEY_TTL_SECONDS = 60 * 60 * 6


# Cross-source failover (see specs/2026-05-29-l30-z3950-cross-source-failover-design.md)
_SRU_TOTAL_BUDGET_SECONDS = 55.0      # under nginx /api/ proxy_read_timeout (60s)
_SRU_MIN_FALLBACK_BUDGET = 10.0       # skip fallbacks if less than this remains
_SRU_FALLBACK_TIMEOUT = 18.0          # per fallback source
_SRU_FALLBACK_MAX_ATTEMPTS = 1

# CQL index maps (verified live 2026-05-29; all return recordSchema=marcxml)
_LOC_CQL = {"isbn": "bath.isbn", "title": "dc.title", "author": "dc.creator"}
_SRU_FALLBACK_SOURCES = [
    {
        "name": "K10plus",
        "sru_url": os.getenv("Z3950_K10PLUS_SRU_URL", "https://sru.k10plus.de/opac-de-627"),
        "cql": {"isbn": "pica.isb", "title": "pica.tit", "author": "pica.per"},
    },
    {
        "name": "Libris",
        "sru_url": os.getenv("Z3950_LIBRIS_SRU_URL", "https://libris.kb.se/sru/libris"),
        "cql": {"isbn": "bath.isbn", "title": "bath.title", "author": "bath.personalName"},
    },
]


async def _report_sru_degraded(source_name: str, last_error: str) -> None:
    """Mark an external SRU source DEGRADED on the status page. Idempotent."""
    try:
        settings = get_settings()
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            key = f"{_SRU_STATUS_KEY_PREFIX}{source_name}"
            # Atomic claim: only the first of N concurrent failures writes a row.
            if not await client.set(
                key, "pending", nx=True, ex=_SRU_STATUS_KEY_TTL_SECONDS
            ):
                return
            async with get_async_session() as db:
                log = SystemStatusLog(
                    organization_id=1,
                    status=SystemStatus.DEGRADED.value,
                    component=IssueComponent.CATALOG.value,
                    title=f"External catalog source unavailable: {source_name}",
                    description=(
                        f"Z39.50/SRU lookups against {source_name} are failing "
                        f"after {_SRU_MAX_ATTEMPTS} attempts. Local catalog and "
                        f"manual cataloging are unaffected."
                    ),
                    patron_message=(
                        f"{source_name} catalog search is temporarily unavailable. "
                        f"Local search and holds are unaffected."
                    ),
                    technical_details=f"Last error: {last_error}",
                    degraded_features=[
                        f"z3950-{source_name.lower().replace(' ', '-')}"
                    ],
                    is_public=True,
                )
                db.add(log)
                await db.flush()
                log_id = log.id
            await client.set(key, str(log_id), ex=_SRU_STATUS_KEY_TTL_SECONDS)
            logger.warning(
                f"Reported SRU source {source_name} DEGRADED (log id={log_id})"
            )
        finally:
            await client.aclose()
    except Exception:
        logger.exception("Failed to report SRU degradation to system_status")


async def _report_sru_recovered(source_name: str) -> None:
    """Resolve all open DEGRADED logs for this source. Idempotent, self-healing.

    Resolves by querying open rows for this source rather than trusting the
    Redis dedup key. That key's TTL (6h) is shorter than a long upstream
    outage, so relying on it alone orphaned incidents that outlived it (and let
    each post-expiry failure log a duplicate). The title-matched DB query
    catches every open row, including the duplicates, so recovery converges.
    """
    try:
        title = f"External catalog source unavailable: {source_name}"
        resolved = 0
        async with get_async_session() as db:
            result = await db.execute(
                select(SystemStatusLog).where(
                    SystemStatusLog.status == SystemStatus.DEGRADED.value,
                    SystemStatusLog.component == IssueComponent.CATALOG.value,
                    SystemStatusLog.title == title,
                    SystemStatusLog.resolved_at.is_(None),
                )
            )
            for log in result.scalars().all():
                # resolved_at is a naive DateTime column (unlike
                # started_at, which is timezone-aware); strip tzinfo so asyncpg
                # can bind it to TIMESTAMP WITHOUT TIME ZONE.
                log.resolved_at = utc_now().replace(tzinfo=None)
                log.resolution_notes = (
                    f"Auto-resolved: {source_name} responding again."
                )
                resolved += 1
            if resolved:
                await db.flush()
        # Clear the dedup key so the next failure can re-report immediately.
        settings = get_settings()
        client = aioredis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.delete(f"{_SRU_STATUS_KEY_PREFIX}{source_name}")
        finally:
            await client.aclose()
        if resolved:
            logger.info(
                f"Resolved {resolved} open SRU incident(s) for {source_name}"
            )
    except Exception:
        logger.exception("Failed to resolve SRU status")


def _sru_cache_key(url: str) -> str:
    return f"{_SRU_CACHE_KEY_PREFIX}{hashlib.md5(url.encode()).hexdigest()}"


async def _sru_cache_get(url: str) -> Optional[str]:
    """Return the last good SRU response body for this query, or None."""
    try:
        client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        try:
            return await client.get(_sru_cache_key(url))
        finally:
            await client.aclose()
    except Exception:
        logger.exception("SRU cache read failed")
        return None


async def _sru_cache_set(url: str, xml_text: str) -> None:
    """Cache a good SRU response body. Best-effort; never raises."""
    try:
        client = aioredis.from_url(get_settings().redis_url, decode_responses=True)
        try:
            await client.set(_sru_cache_key(url), xml_text, ex=_SRU_CACHE_TTL_SECONDS)
        finally:
            await client.aclose()
    except Exception:
        logger.exception("SRU cache write failed")


class Z3950Service:

    def __init__(self):
        self._use_z3950 = False
        self.zoom = None

        try:
            from PyZ3950 import zoom
            self.zoom = zoom
            self._use_z3950 = True
            logger.info("PyZ3950 available - using Z39.50 protocol")
        except ImportError:
            logger.info(
                "PyZ3950 not installed, using SRU (HTTP) for library catalog searches"
            )

        # Service is always available since we have SRU fallback
        self.available = True

    def get_available_sources(self) -> List[str]:
        return list(Z3950_SOURCES.keys())

    def get_source_config(self, source: str) -> Optional[Dict]:
        return Z3950_SOURCES.get(source)

    def parse_marc_record(self, marc_record: Record) -> Dict:
        return self._extract_marc_fields(marc_record)

    async def search_by_isbn(
        self, isbn: str, source: str = "loc", max_results: int = 5
    ) -> List[Dict]:
        # Clean ISBN (remove dashes and spaces)
        isbn_clean = isbn.replace("-", "").replace(" ", "").strip()

        if not isbn_clean:
            return []

        return await self._search_dispatch(
            isbn=isbn_clean, source=source, max_results=max_results
        )

    async def search_by_title(
        self, title: str, source: str = "loc", max_results: int = 10
    ) -> List[Dict]:
        if not title or not title.strip():
            return []

        return await self._search_dispatch(
            title=title, source=source, max_results=max_results
        )

    async def search_by_author(
        self, author: str, source: str = "loc", max_results: int = 10
    ) -> List[Dict]:
        if not author or not author.strip():
            return []

        return await self._search_dispatch(
            author=author, source=source, max_results=max_results
        )

    async def search_combined(
        self,
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        source: str = "loc",
        max_results: int = 10,
    ) -> List[Dict]:
        isbn_clean = None
        if isbn:
            isbn_clean = isbn.replace("-", "").replace(" ", "").strip()
            if not isbn_clean:
                isbn_clean = None

        title_clean = title.strip() if title and title.strip() else None
        author_clean = author.strip() if author and author.strip() else None

        if not isbn_clean and not title_clean and not author_clean:
            return []

        return await self._search_dispatch(
            isbn=isbn_clean,
            title=title_clean,
            author=author_clean,
            source=source,
            max_results=max_results,
        )

    async def get_record_details(
        self, control_number: str, source: str = "loc"
    ) -> Optional[Dict]:
        if source not in Z3950_SOURCES:
            return None

        config = Z3950_SOURCES[source]
        if config.get("requires_auth"):
            raise Z3950Error(
                f"{config['name']} requires an authentication subscription. "
                f"Contact your administrator to configure OCLC credentials."
            )

        if self._use_z3950:
            query = f'@attr 1=12 "{control_number}"'
            results = await self._z3950_search(query, source, 1)
        else:
            sru_url = config.get("sru_url")
            if not sru_url:
                return None
            cql_query = f'rec.id = "{_escape_cql(control_number)}"'
            results = await self._sru_search(sru_url, cql_query, 1, config["name"])

        return results[0] if results else None

    # =========================================================================
    # Search Dispatch
    # =========================================================================

    async def _search_dispatch(
        self,
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        source: str = "loc",
        max_results: int = 10,
    ) -> List[Dict]:
        if source not in Z3950_SOURCES:
            return []

        config = Z3950_SOURCES[source]

        if config.get("requires_auth"):
            raise Z3950Error(
                f"{config['name']} requires an authentication subscription. "
                f"Contact your administrator to configure OCLC credentials."
            )

        if self._use_z3950:
            query = _build_pqf_query(isbn=isbn, title=title, author=author)
            if not query:
                return []
            return await self._z3950_search(query, source, max_results)
        else:
            sru_url = config.get("sru_url")
            if not sru_url:
                logger.warning(
                    f"No SRU URL configured for {config['name']} and PyZ3950 unavailable"
                )
                return []
            deadline = time.monotonic() + _SRU_TOTAL_BUDGET_SECONDS
            primary_query = _build_cql_query(
                _LOC_CQL, isbn=isbn, title=title, author=author
            )
            if not primary_query:
                return []
            primary: List[Dict] = []
            primary_error: Optional[Z3950Error] = None
            try:
                primary = await self._sru_search(
                    sru_url, primary_query, max_results, config["name"]
                )
                if primary:
                    return primary
            except Z3950Error as exc:
                primary_error = exc
            # Failover only for the default LOC source, and only with budget left.
            if source == "loc":
                remaining = deadline - time.monotonic()
                if remaining >= _SRU_MIN_FALLBACK_BUDGET:
                    fallback = await self._failover_search(
                        isbn, title, author, max_results, remaining
                    )
                    if fallback:
                        return fallback
            # Nothing from LOC or failover: preserve today's contract
            # (empty list on no-results, re-raise on LOC error).
            if primary_error is not None:
                raise primary_error
            return primary

    async def _failover_search(
        self, isbn, title, author, max_results: int, budget: float
    ) -> List[Dict]:
        timeout = min(budget, _SRU_FALLBACK_TIMEOUT)

        async def _one(src):
            query = _build_cql_query(src["cql"], isbn=isbn, title=title, author=author)
            if not query:
                return []
            return await self._sru_search(
                src["sru_url"], query, max_results, src["name"],
                report_status=False, is_fallback=True,
                timeout=timeout, max_attempts=_SRU_FALLBACK_MAX_ATTEMPTS,
            )

        outcomes = await asyncio.gather(
            *[_one(s) for s in _SRU_FALLBACK_SOURCES], return_exceptions=True
        )
        for src, res in zip(_SRU_FALLBACK_SOURCES, outcomes):
            if isinstance(res, list) and res:
                logger.info(f"SRU failover served result from {src['name']}")
                return res
            if isinstance(res, Exception):
                logger.warning(f"SRU failover source {src['name']} failed: {res}")
        return []

    # =========================================================================
    # Z39.50 Protocol Search (requires PyZ3950)
    # =========================================================================

    async def _z3950_search(
        self, query: str, source: str, max_results: int
    ) -> List[Dict]:
        config = Z3950_SOURCES[source]
        results = []

        try:
            conn = self.zoom.Connection(
                config["host"],
                config["port"],
                databaseName=config["database"],
                preferredRecordSyntax=config["syntax"],
            )

            result_set = conn.search(self.zoom.Query("PQF", query))

            for i in range(min(len(result_set), max_results)):
                try:
                    record_data = result_set[i].data

                    if isinstance(record_data, bytes):
                        marc_record = Record(data=record_data)
                    else:
                        marc_record = Record(data=record_data.encode("utf-8"))

                    record_dict = self._extract_marc_fields(marc_record)
                    record_dict["source"] = config["name"]
                    record_dict["raw_marc"] = record_data
                    results.append(record_dict)

                except Exception as e:
                    logger.error(f"Error parsing record {i}: {e}", exc_info=True)
                    continue

            conn.close()

        except Exception as e:
            logger.error(f"Z39.50 search error for {source}: {e}", exc_info=True)
            raise Z3950Error(f"Z39.50 search failed for {source}: {e}") from e

        return results

    # =========================================================================
    # SRU (HTTP) Search Fallback
    # =========================================================================

    async def _sru_search(
        self, sru_url: str, cql_query: str, max_results: int, source_name: str,
        *, report_status: bool = True, is_fallback: bool = False,
        timeout: float = _SRU_TIMEOUT_SECONDS, max_attempts: int = _SRU_MAX_ATTEMPTS,
    ) -> List[Dict]:
        params = {
            "operation": "searchRetrieve",
            "version": "1.1",
            "query": cql_query,
            "maximumRecords": max_results,
            "recordSchema": "marcxml",
        }

        url = f"{sru_url}?{urlencode(params)}"
        results = []

        try:
            served_from_cache = False
            cached_xml: Optional[str] = None
            xml_text: Optional[str] = None
            async with httpx.AsyncClient(timeout=timeout) as client:
                response: Optional[httpx.Response] = None
                for attempt in range(max_attempts):
                    try:
                        response = await client.get(url)
                    except httpx.TransportError as e:
                        if attempt < max_attempts - 1:
                            wait = _SRU_BACKOFF_BASE_SECONDS * (2 ** attempt)
                            logger.warning(
                                f"SRU {source_name} transport error "
                                f"{type(e).__name__}; retrying in {wait:.1f}s "
                                f"(attempt {attempt + 2}/{max_attempts})"
                            )
                            await asyncio.sleep(wait)
                            continue
                        if report_status:
                            await _report_sru_degraded(
                                source_name, f"{type(e).__name__}: {e}"
                            )
                        cached_xml = await _sru_cache_get(url)
                        if cached_xml is None:
                            raise
                        served_from_cache = True
                        break
                    if (
                        response.status_code in _SRU_RETRYABLE_STATUS
                        and attempt < max_attempts - 1
                    ):
                        wait = _SRU_BACKOFF_BASE_SECONDS * (2 ** attempt)
                        logger.warning(
                            f"SRU {source_name} returned {response.status_code}; "
                            f"retrying in {wait:.1f}s "
                            f"(attempt {attempt + 2}/{max_attempts})"
                        )
                        await asyncio.sleep(wait)
                        continue
                    break
                if not served_from_cache:
                    assert response is not None  # loop runs ≥ 1 iteration
                    if response.status_code in _SRU_RETRYABLE_STATUS:
                        if report_status:
                            await _report_sru_degraded(
                                source_name, f"HTTP {response.status_code}"
                            )
                        cached_xml = await _sru_cache_get(url)
                        if cached_xml is None:
                            response.raise_for_status()
                        served_from_cache = True
                    else:
                        response.raise_for_status()
                        xml_text = response.text

            if served_from_cache:
                xml_text = cached_xml
                logger.warning(
                    f"SRU {source_name} unavailable; served cached result for query"
                )

            root = ET.fromstring(xml_text)

            # Check for SRU diagnostic errors (200 OK with error body)
            diagnostics = root.findall(
                f".//{{{_SRU_NS}}}diagnostic"
            ) or root.findall(".//diagnostic")
            if diagnostics:
                diag_messages = []
                for diag in diagnostics:
                    msg_elem = diag.find(f"{{{_SRU_NS}}}message") or diag.find("message")
                    uri_elem = diag.find(f"{{{_SRU_NS}}}uri") or diag.find("uri")
                    msg = msg_elem.text if msg_elem is not None else "Unknown diagnostic"
                    uri = uri_elem.text if uri_elem is not None else ""
                    diag_messages.append(f"{msg} ({uri})" if uri else msg)
                logger.warning(
                    f"SRU returned diagnostic errors for {source_name}: "
                    + "; ".join(diag_messages)
                )
                raise Z3950Error(
                    f"SRU diagnostic error from {source_name}: {'; '.join(diag_messages)}"
                )

            # Find MARCXML records in the SRU response
            marc_records = root.findall(
                f".//{{{_SRU_NS}}}record"
            ) or root.findall(".//record")

            for record_elem in marc_records:
                try:
                    marcxml_elem = record_elem.find(
                        f".//{{{_MARC_NS}}}record"
                    )
                    if marcxml_elem is None:
                        continue

                    # Convert MARCXML element to pymarc Record
                    marc_xml_bytes = ET.tostring(marcxml_elem, encoding="unicode")
                    # Wrap in collection for pymarc parsing
                    collection_xml = (
                        f'<?xml version="1.0" encoding="UTF-8"?>'
                        f'<collection xmlns="{_MARC_NS}">'
                        f'{marc_xml_bytes}'
                        f'</collection>'
                    )
                    parsed_records = pymarc.parse_xml_to_array(
                        BytesIO(collection_xml.encode("utf-8"))
                    )

                    if parsed_records:
                        marc_record = parsed_records[0]
                        record_dict = self._extract_marc_fields(marc_record)
                        record_dict["source"] = source_name
                        record_dict["is_fallback"] = is_fallback
                        record_dict["raw_marc"] = marc_record.as_marc()
                        results.append(record_dict)

                except Exception as e:
                    logger.error(f"Error parsing SRU record: {e}", exc_info=True)
                    continue

        except httpx.HTTPStatusError as e:
            logger.error(f"SRU HTTP error: {e}", exc_info=True)
            raise Z3950Error(f"SRU search failed: HTTP {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"SRU request error: {e}", exc_info=True)
            raise Z3950Error(f"SRU search failed: {e}") from e
        except ET.ParseError as e:
            logger.error(f"SRU XML parse error: {e}", exc_info=True)
            raise Z3950Error(f"Failed to parse SRU response: {e}") from e

        if not served_from_cache:
            await _report_sru_recovered(source_name)
            if results:
                await _sru_cache_set(url, xml_text)
        return results

    # =========================================================================
    # MARC Field Extraction
    # =========================================================================

    def _extract_marc_fields(self, marc_record: Record) -> Dict:
        result = {
            "title": None,
            "author": None,
            "isbn": None,
            "publisher": None,
            "publication_year": None,
            "description": None,
            "subjects": [],
            "lc_call_number": None,
            "dewey_decimal": None,
            "edition": None,
            "page_count": None,
            "control_number": None,
        }

        def _get_field(tag: str):
            fields = marc_record.get_fields(tag)
            return fields[0] if fields else None

        def _get_subfield(field, code: str) -> str | None:
            values = field.get_subfields(code)
            return values[0] if values else None

        try:
            # Control number (001)
            field_001 = _get_field("001")
            if field_001:
                result["control_number"] = field_001.data

            # ISBN (020$a)
            field_020 = _get_field("020")
            if field_020:
                isbn = _get_subfield(field_020, "a")
                if isbn:
                    result["isbn"] = isbn.split()[0].replace("-", "")

            # LC Call Number (050$a)
            field_050 = _get_field("050")
            if field_050:
                result["lc_call_number"] = _get_subfield(field_050, "a")

            # Dewey Decimal (082$a)
            field_082 = _get_field("082")
            if field_082:
                result["dewey_decimal"] = _get_subfield(field_082, "a")

            # Author (100$a)
            field_100 = _get_field("100")
            if field_100:
                result["author"] = _get_subfield(field_100, "a")

            # Title (245$a and $b)
            field_245 = _get_field("245")
            if field_245:
                title_parts = []
                title_a = _get_subfield(field_245, "a")
                if title_a:
                    title_parts.append(title_a.rstrip(" /:"))
                title_b = _get_subfield(field_245, "b")
                if title_b:
                    title_parts.append(title_b.rstrip(" /:"))
                result["title"] = " ".join(title_parts) if title_parts else None

            # Edition statement (250$a)
            field_250 = _get_field("250")
            if field_250:
                result["edition"] = _get_subfield(field_250, "a")

            # Publisher and publication year (260 or 264)
            pub_field = _get_field("264") or _get_field("260")
            if pub_field:
                pub_b = _get_subfield(pub_field, "b")
                if pub_b:
                    result["publisher"] = pub_b.rstrip(" ,")
                pub_c = _get_subfield(pub_field, "c")
                if pub_c:
                    year_str = pub_c.strip("[].,")
                    year_match = re.search(r"\d{4}", year_str)
                    if year_match:
                        result["publication_year"] = int(year_match.group())

            # Physical description (300$a - page count)
            field_300 = _get_field("300")
            if field_300:
                extent = _get_subfield(field_300, "a")
                if extent:
                    page_match = re.search(r"(\d+)\s*p", extent.lower())
                    if page_match:
                        result["page_count"] = int(page_match.group(1))

            # Summary/Description (520$a)
            field_520 = _get_field("520")
            if field_520:
                result["description"] = _get_subfield(field_520, "a")

            # Subject headings (650$a)
            for field in marc_record.get_fields("650"):
                subj = _get_subfield(field, "a")
                if subj:
                    result["subjects"].append(subj.rstrip("."))

        except Exception as e:
            logger.error(f"Error extracting MARC fields: {e}", exc_info=True)

        return result

    # =========================================================================
    # Import Tracking
    # =========================================================================

    def mark_fields_as_imported(self, record_dict: Dict, source: str) -> Dict:
        field_metadata = {}

        imported_fields = [
            "title", "author", "isbn", "publisher", "publication_year",
            "description", "subjects", "lc_call_number", "dewey_decimal"
        ]

        for field in imported_fields:
            if field in record_dict and record_dict[field]:
                field_tag = self._get_marc_field_tag(field)
                if field_tag:
                    field_metadata[field_tag] = {
                        "origin": "imported",
                        "source": source,
                        "protected": False,
                        "imported_from": source,
                        "imported_at": str(datetime.now(timezone.utc).isoformat()),
                    }

        return field_metadata

    def _get_marc_field_tag(self, field_name: str) -> Optional[str]:
        mapping = {
            "title": "245",
            "author": "100",
            "isbn": "020",
            "publisher": "264",
            "publication_year": "264",
            "description": "520",
            "subjects": "650",
            "lc_call_number": "050",
            "dewey_decimal": "082",
        }
        return mapping.get(field_name)


# =============================================================================
# Query Building Helpers
# =============================================================================

def _escape_cql(text: str) -> str:
    return text.replace('"', '\\"')


def _build_cql_query(
    indexes: Dict[str, str],
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> Optional[str]:
    clauses = []
    if isbn:
        clauses.append(f'{indexes["isbn"]} = "{_escape_cql(isbn)}"')
    if title:
        clauses.append(f'{indexes["title"]} = "{_escape_cql(title)}"')
    if author:
        clauses.append(f'{indexes["author"]} = "{_escape_cql(author)}"')
    if not clauses:
        return None
    return " AND ".join(clauses)


def _build_pqf_query(
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> Optional[str]:
    parts = []

    if isbn:
        parts.append(f'@attr 1=7 "{isbn}"')
    if title:
        parts.append(f'@attr 1=4 "{title}"')
    if author:
        parts.append(f'@attr 1=1003 "{author}"')

    if not parts:
        return None

    if len(parts) == 1:
        return parts[0]

    # Build valid PQF prefix notation by nesting @and operators
    # For [A, B, C]: @and @and A B C
    query = parts[0]
    for part in parts[1:]:
        query = f"@and {query} {part}"

    return query


# Singleton instance
z3950_service = Z3950Service()
