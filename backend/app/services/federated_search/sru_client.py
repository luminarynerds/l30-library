# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
from app.core.logging import get_logger
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import aiohttp

from .base_client import (
    AuthenticationError,
    BaseSearchClient,
    ClientError,
    ConnectionError,
    NormalizedSearchResult,
    ParsingError,
    ProtocolType,
    QueryError,
    SearchResultType,
    ServerConfig,
    TimeoutError,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class SRUQueryBuilder:

    @staticmethod
    def build_cql_query(
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        keywords: Optional[str] = None,
        issn: Optional[str] = None,
    ) -> str:
        clauses = []

        if isbn:
            isbn_clean = isbn.strip().replace("-", "")
            clauses.append(f'bath.isbn = "{SRUQueryBuilder._escape_cql(isbn_clean)}"')

        if issn:
            issn_clean = issn.strip().replace("-", "")
            clauses.append(f'bath.issn = "{SRUQueryBuilder._escape_cql(issn_clean)}"')

        if title:
            # Support phrase searching for titles
            clauses.append(f'dc.title = "{SRUQueryBuilder._escape_cql(title)}"')

        if author:
            clauses.append(f'dc.creator = "{SRUQueryBuilder._escape_cql(author)}"')

        if keywords:
            # Keywords typically map to subject/keywords indexes
            clauses.append(f'dc.subject = "{SRUQueryBuilder._escape_cql(keywords)}"')

        if not clauses:
            raise QueryError("At least one search criterion must be provided")

        # Combine with AND operator (most restrictive - better precision)
        query = " AND ".join(clauses)
        return query

    @staticmethod
    def build_type1_query(
        isbn: Optional[str] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        keywords: Optional[str] = None,
    ) -> str:
        clauses = []

        # BIB-1 attributes: 1=7 (ISBN), 1=4 (title), 1=1003 (author), 1=21 (subject)
        if isbn:
            isbn_clean = isbn.strip().replace("-", "")
            clauses.append(f'@attr 1=7 "{isbn_clean}"')

        if title:
            clauses.append(f'@attr 1=4 "{title}"')

        if author:
            clauses.append(f'@attr 1=1003 "{author}"')

        if keywords:
            clauses.append(f'@attr 1=21 "{keywords}"')

        if not clauses:
            raise QueryError("At least one search criterion must be provided")

        if len(clauses) == 1:
            query = clauses[0]
        else:
            # Combine with AND: @and query1 query2
            query = " @and ".join(clauses)

        return query

    @staticmethod
    def _escape_cql(text: str) -> str:
        # In CQL, quotes within quoted strings need escaping
        return text.replace('"', '\\"')


class SRUClient(BaseSearchClient):

    # SRU XML namespace
    SRU_NAMESPACE = "http://www.loc.gov/zing/srw/"

    def __init__(self, config: ServerConfig):
        super().__init__(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self.base_url = self._build_base_url()
        self.query_builder = SRUQueryBuilder()

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def connect(self) -> None:
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
            self.session = aiohttp.ClientSession(timeout=timeout)
            self._connection = self.session
            self.logger.debug(f"Connected to SRU server: {self.base_url}")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to {self.config.id}: {e}") from e

    async def disconnect(self) -> None:
        if self.session:
            await self.session.close()
            self.session = None
            self._connection = None

    async def _check_connection(self) -> bool:
        return self.session is not None and not self.session.closed

    # =========================================================================
    # Search Implementation
    # =========================================================================

    async def search(
        self,
        query: str,
        max_results: int = 10,
        result_type: SearchResultType = SearchResultType.BIBLIOGRAPHIC,
    ) -> List[NormalizedSearchResult]:
        self._validate_query(query)
        self._validate_results(0, max_results)

        await self.ensure_connected()

        start_time = utc_now()
        self._log_request(query, max_results)

        try:
            results = await self._execute_with_retry(
                self._execute_search,
                query,
                max_results,
                max_retries=self.config.max_retries,
            )

            elapsed = (utc_now() - start_time).total_seconds()
            self._log_response(len(results), elapsed)

            return results

        except asyncio.TimeoutError as e:
            raise TimeoutError(f"SRU search timed out after {self.config.timeout_seconds}s") from e
        except (ConnectionError, QueryError, TimeoutError):
            raise
        except Exception as e:
            self.logger.error(f"Search error on {self.config.id}: {e}", exc_info=True)
            raise ClientError(f"Search failed on {self.config.id}: {e}") from e

    async def _execute_search(
        self, query: str, max_results: int
    ) -> List[NormalizedSearchResult]:
        if self.config.protocol == ProtocolType.SRU_SOAP:
            response = await self._execute_soap_request(query, max_results)
        else:  # SRU_REST or default to REST
            response = await self._execute_rest_request(query, max_results)

        return await self._parse_response(response)

    async def _execute_rest_request(self, query: str, max_results: int) -> str:
        if not self.session:
            raise ConnectionError("Not connected to SRU server")

        params = {
            "query": query,
            "maximumRecords": max_results,
            "operation": "searchRetrieve",
            # SRU 1.1 makes lx2 reply in the SRW 1.1 namespace
            # (http://www.loc.gov/zing/srw/) that _parse_response looks for; 2.0
            # switches to the OASIS search-ws namespace and the parser finds 0 records.
            "version": "1.1",
            # "marcxml" is the short schema name LC's lx2, K10plus, and Libris all
            # accept; the full "info:srw/schema/1/marcxml-v1.1" URI makes lx2 return
            # numberOfRecords>0 but empty recordData with a diagnostic.
            "recordSchema": "marcxml",
        }

        url = f"{self.base_url}?{urlencode(params)}"

        try:
            async with self.session.get(url, ssl=False) as response:
                if response.status == 401:
                    raise AuthenticationError("SRU server returned 401 Unauthorized")
                if response.status == 400:
                    raise QueryError("SRU server returned 400 Bad Request (invalid query)")
                if response.status >= 500:
                    raise ConnectionError(f"SRU server error: {response.status}")
                if response.status >= 400:
                    raise ClientError(f"SRU request failed: {response.status}")

                return await response.text()

        except asyncio.TimeoutError:
            raise TimeoutError(f"SRU request to {self.config.id} timed out") from None
        except aiohttp.ClientError as e:
            raise ConnectionError(f"HTTP error contacting {self.config.id}: {e}") from e

    async def _execute_soap_request(self, query: str, max_results: int) -> str:
        if not self.session:
            raise ConnectionError("Not connected to SRU server")

        soap_body = self._build_soap_request(query, max_results)

        try:
            async with self.session.post(
                self.base_url,
                data=soap_body,
                headers={"Content-Type": "application/soap+xml; charset=utf-8"},
                ssl=False,
            ) as response:
                if response.status == 401:
                    raise AuthenticationError("SRU server returned 401 Unauthorized")
                if response.status >= 500:
                    raise ConnectionError(f"SRU server error: {response.status}")
                if response.status >= 400:
                    raise ClientError(f"SOAP request failed: {response.status}")

                return await response.text()

        except asyncio.TimeoutError:
            raise TimeoutError(f"SRU SOAP request to {self.config.id} timed out") from None
        except aiohttp.ClientError as e:
            raise ConnectionError(f"HTTP error in SOAP request to {self.config.id}: {e}") from e

    # =========================================================================
    # Response Parsing
    # =========================================================================

    async def _parse_response(self, response: str) -> List[NormalizedSearchResult]:
        try:
            root = ET.fromstring(response)
        except ET.ParseError as e:
            raise ParsingError(f"Failed to parse SRU XML response: {e}") from e

        # Check for SRU diagnostic/error response
        self._check_for_sru_errors(root)

        # Extract records
        results = []
        records = root.findall(
            ".//srw:record", {"srw": self.SRU_NAMESPACE}
        ) or root.findall(".//record")

        for record_elem in records:
            try:
                result = self._parse_record(record_elem)
                if result:
                    result.source_id = self.config.id
                    result.source_name = self.config.name
                    result.protocol = self.config.protocol
                    results.append(result)
            except Exception as e:  # noqa: BLE001  # per-record parse boundary - skip malformed external record not whole result
                self.logger.warning(f"Error parsing record: {e}")
                continue

        return results

    async def _execute_request(self, query: str, max_results: int) -> str:
        return await self._execute_rest_request(query, max_results)

    def _parse_record(self, record_elem: ET.Element) -> Optional[NormalizedSearchResult]:
        try:
            # Try MARCXML format first
            marcxml = record_elem.find(".//{http://www.loc.gov/MARC21/slim}record")
            if marcxml is not None:
                return self._parse_marcxml_record(marcxml)

            # Fall back to Dublin Core
            dc_elements = record_elem.findall(".//{http://purl.org/dc/elements/1.1/}*")
            if dc_elements:
                return self._parse_dublin_core_record(record_elem)

            return None

        except Exception as e:  # noqa: BLE001  # per-record parse boundary - skip malformed external record not whole result
            self.logger.warning(f"Error parsing record element: {e}")
            return None

    def _parse_marcxml_record(self, marcxml: ET.Element) -> NormalizedSearchResult:
        ns = {"marc": "http://www.loc.gov/MARC21/slim"}

        def get_field(tag: str, subfield: str) -> Optional[str]:
            datafield = marcxml.find(f".//marc:datafield[@tag='{tag}']", ns)
            if datafield is not None:
                subfield_elem = datafield.find(f"marc:subfield[@code='{subfield}']", ns)
                if subfield_elem is not None and subfield_elem.text:
                    return subfield_elem.text
            return None

        def get_all_subfields(tag: str, subfield: Optional[str] = None) -> List[str]:
            values = []
            datafields = marcxml.findall(f".//marc:datafield[@tag='{tag}']", ns)
            for df in datafields:
                if subfield:
                    sf = df.find(f"marc:subfield[@code='{subfield}']", ns)
                    if sf is not None and sf.text:
                        values.append(sf.text)
                else:
                    # Get all non-control subfields
                    for sf in df.findall("marc:subfield", ns):
                        if sf.text:
                            values.append(sf.text)
            return values

        result = NormalizedSearchResult(
            source_id=self.config.id,
            source_name=self.config.name,
            protocol=self.config.protocol,
        )

        # Extract key fields
        result.control_number = get_field("001", "a")
        result.title = get_field("245", "a")
        if not result.title:
            result.title = get_field("245", "")
        result.author = get_field("100", "a")
        result.publisher = get_field("260", "b") or get_field("264", "b")
        result.isbn = get_field("020", "a")
        result.issn = get_field("022", "a")
        result.lc_classification = get_field("050", "a")
        result.dewey_decimal = get_field("082", "a")
        result.description = get_field("520", "a")
        result.extent = get_field("300", "a")
        result.language = get_field("008", "")[:3] if get_field("008", "") else None

        # Extract year from 260$c or 264$c
        pub_date = get_field("260", "c") or get_field("264", "c")
        if pub_date:
            import re
            year_match = re.search(r"\d{4}", pub_date)
            if year_match:
                result.publication_year = int(year_match.group())

        # Extract subjects
        result.subjects = get_all_subfields("650", "a")

        # Extract series
        series_parts = get_all_subfields("490", "a")
        if series_parts:
            result.series = " ; ".join(series_parts)

        return result

    def _parse_dublin_core_record(self, record_elem: ET.Element) -> NormalizedSearchResult:
        dc_ns = {"dc": "http://purl.org/dc/elements/1.1/"}

        def get_dc_value(element_name: str) -> Optional[str]:
            elem = record_elem.find(f".//dc:{element_name}", dc_ns)
            return elem.text if elem is not None else None

        def get_dc_all_values(element_name: str) -> List[str]:
            elems = record_elem.findall(f".//dc:{element_name}", dc_ns)
            return [elem.text for elem in elems if elem.text]

        result = NormalizedSearchResult(
            source_id=self.config.id,
            source_name=self.config.name,
            protocol=self.config.protocol,
        )

        result.title = get_dc_value("title")
        result.author = get_dc_value("creator")
        result.description = get_dc_value("description")
        result.publisher = get_dc_value("publisher")
        result.isbn = get_dc_value("identifier")
        result.subjects = get_dc_all_values("subject")
        result.language = get_dc_value("language")

        return result

    def _check_for_sru_errors(self, root: ET.Element) -> None:
        diagnostics = root.findall(
            ".//srw:diagnostic", {"srw": self.SRU_NAMESPACE}
        ) or root.findall(".//diagnostic")

        if diagnostics:
            for diag in diagnostics:
                code_elem = diag.find("srw:code", {"srw": self.SRU_NAMESPACE})
                msg_elem = diag.find("srw:message", {"srw": self.SRU_NAMESPACE})

                code = code_elem.text if code_elem is not None else "unknown"
                message = msg_elem.text if msg_elem is not None else "Unknown error"

                # Query-related diagnostics (20-27)
                if code in ["20", "21", "22", "23", "24", "25", "26", "27"]:
                    raise QueryError(f"SRU query error [{code}]: {message}")

                # Other errors
                raise ClientError(f"SRU error [{code}]: {message}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _build_base_url(self) -> str:
        protocol = "https" if self.config.port == 443 else "http"
        return f"{protocol}://{self.config.host}:{self.config.port}/{self.config.database}"

    def _build_soap_request(self, query: str, max_records: int) -> str:
        soap_template = f"""<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                   xmlns:sru="http://www.loc.gov/zing/srw/">
    <soapenv:Body>
        <sru:searchRetrieveRequest>
            <sru:query>{query}</sru:query>
            <sru:maximumRecords>{max_records}</sru:maximumRecords>
            <sru:recordSchema>info:srw/schema/1/marcxml-v1.1</sru:recordSchema>
            <sru:version>2.0</sru:version>
        </sru:searchRetrieveRequest>
    </soapenv:Body>
</soapenv:Envelope>"""

        return soap_template
