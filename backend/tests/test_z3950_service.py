# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
TDD Tests for Z39.50 Cataloging Service

Tests the Z39.50 service for searching library catalogs and importing MARC records.
Tests cover both SRU (HTTP) and Z39.50 protocol backends.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from io import BytesIO

import pymarc
from pymarc import Record, Field, Subfield


def _create_sample_marc_record(
    title="Test Book",
    author=None,
    isbn=None,
    publisher=None,
    year=None,
    subjects=None,
):
    """Create a real pymarc Record for testing."""
    record = Record()
    record.leader = "00000nam a2200000 a 4500"

    record.add_field(Field(tag="001", data="TEST001"))

    if isbn:
        record.add_field(
            Field(
                tag="020",
                indicators=[" ", " "],
                subfields=[Subfield(code="a", value=isbn)],
            )
        )

    if author:
        record.add_field(
            Field(
                tag="100",
                indicators=["1", " "],
                subfields=[Subfield(code="a", value=author)],
            )
        )

    if title:
        record.add_field(
            Field(
                tag="245",
                indicators=["1", "0"],
                subfields=[
                    Subfield(code="a", value=f"{title} /"),
                    Subfield(code="b", value=""),
                ],
            )
        )

    if publisher or year:
        subfields = [Subfield(code="a", value="New York :")]
        if publisher:
            subfields.append(Subfield(code="b", value=f"{publisher},"))
        if year:
            subfields.append(Subfield(code="c", value=f"{year}."))
        record.add_field(
            Field(tag="264", indicators=[" ", "1"], subfields=subfields)
        )

    if subjects:
        for subject in subjects:
            record.add_field(
                Field(
                    tag="650",
                    indicators=[" ", "0"],
                    subfields=[Subfield(code="a", value=subject)],
                )
            )

    return record


def _build_sru_xml_response(marc_records):
    """Build a fake SRU XML response containing MARCXML records."""
    _ = "http://www.loc.gov/MARC21/slim"
    sru_ns = "http://www.loc.gov/zing/srw/"

    records_xml = ""
    for rec in marc_records:
        rec_xml = pymarc.record_to_xml(rec, namespace=True).decode("utf-8")
        records_xml += (
            f"<srw:record xmlns:srw=\"{sru_ns}\">"
            f"<srw:recordData>{rec_xml}</srw:recordData>"
            f"</srw:record>"
        )

    return (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<srw:searchRetrieveResponse xmlns:srw="{sru_ns}">'
        f'<srw:numberOfRecords>{len(marc_records)}</srw:numberOfRecords>'
        f'<srw:records>{records_xml}</srw:records>'
        f'</srw:searchRetrieveResponse>'
    )


class TestZ3950Search:
    """Test Z39.50 search functionality"""

    @pytest.mark.asyncio
    async def test_searches_library_of_congress_by_isbn(self):
        """Test searching Library of Congress by ISBN via SRU."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        marc_record = _create_sample_marc_record(
            title="Test Book", isbn="9780123456789"
        )
        sru_response = _build_sru_xml_response([marc_record])

        mock_response = MagicMock()
        mock_response.text = sru_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.z3950_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await service.search_by_isbn("978-0-123456-78-9", source="loc")

            assert len(results) > 0
            assert results[0]["isbn"] == "9780123456789"
            assert results[0]["title"] is not None

    @pytest.mark.asyncio
    async def test_searches_by_title(self):
        """Test searching by title via SRU."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        marc_records = [
            _create_sample_marc_record(title="Test Book Title"),
            _create_sample_marc_record(title="Another Test Book"),
        ]
        sru_response = _build_sru_xml_response(marc_records)

        mock_response = MagicMock()
        mock_response.text = sru_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.z3950_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await service.search_by_title("Test Book", source="loc")

            assert len(results) == 2
            assert "Test Book" in results[0]["title"]

    @pytest.mark.asyncio
    async def test_searches_by_author(self):
        """Test searching by author via SRU."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        marc_record = _create_sample_marc_record(
            title="A Novel", author="Smith, John"
        )
        sru_response = _build_sru_xml_response([marc_record])

        mock_response = MagicMock()
        mock_response.text = sru_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.z3950_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await service.search_by_author("Smith, John", source="loc")

            assert len(results) > 0
            assert "Smith" in results[0]["author"]

    @pytest.mark.asyncio
    async def test_returns_multiple_results_when_applicable(self):
        """Test that multiple results are returned when applicable."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        marc_records = [
            _create_sample_marc_record(title="Book 1"),
            _create_sample_marc_record(title="Book 2"),
            _create_sample_marc_record(title="Book 3"),
        ]
        sru_response = _build_sru_xml_response(marc_records)

        mock_response = MagicMock()
        mock_response.text = sru_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.z3950_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await service.search_by_title("Test", source="loc")

            assert len(results) == 3


class TestMARCParsing:
    """Test MARC record parsing functionality"""

    def test_parses_marc_records_correctly(self):
        """Test that MARC records are parsed correctly via parse_marc_record."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        marc_record = _create_sample_marc_record(
            title="Complete MARC Record",
            author="Author, Test",
            isbn="9780123456789",
            publisher="Test Publisher",
            year="2024",
        )

        parsed = service.parse_marc_record(marc_record)

        assert "Complete MARC Record" in parsed["title"]
        assert parsed["author"] == "Author, Test"
        assert parsed["isbn"] == "9780123456789"
        assert "Test Publisher" in parsed["publisher"]
        assert parsed["publication_year"] == 2024

    def test_handles_missing_marc_fields_gracefully(self):
        """Test that missing MARC fields are handled gracefully."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        marc_record = _create_sample_marc_record(title="Minimal Record")

        parsed = service.parse_marc_record(marc_record)

        assert "Minimal Record" in parsed["title"]
        assert "author" in parsed
        assert "isbn" in parsed

    def test_extracts_multiple_subjects(self):
        """Test that multiple subject headings are extracted."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        marc_record = _create_sample_marc_record(
            title="Multi-Subject Book",
            subjects=["Fiction", "Adventure", "Science Fiction", "Dystopian"],
        )

        parsed = service.parse_marc_record(marc_record)

        assert isinstance(parsed["subjects"], list)
        assert len(parsed["subjects"]) == 4
        assert "Fiction" in parsed["subjects"]
        assert "Adventure" in parsed["subjects"]
        assert "Science Fiction" in parsed["subjects"]


class TestZ3950ErrorHandling:
    """Test Z39.50 error handling"""

    @pytest.mark.asyncio
    async def test_handles_no_results_gracefully(self):
        """Test that no results are handled gracefully."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        sru_response = _build_sru_xml_response([])

        mock_response = MagicMock()
        mock_response.text = sru_response
        mock_response.raise_for_status = MagicMock()

        with patch("app.services.z3950_service.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await service.search_by_isbn("000-0-000000-00-0", source="loc")

            assert results == []

    @pytest.mark.asyncio
    async def test_handles_connection_errors(self):
        """Test that connection errors raise Z3950Error when there's no
        stale cache to fall back on.

        z3950_service now serves a cached response (Redis, keyed by URL)
        when the SRU source is unreachable rather than raising -- see
        `_sru_cache_get`/`served_from_cache` in app/services/z3950_service.py.
        This test's ISBN can pick up a real cache entry left behind by an
        earlier test in the same run (shared Redis), which would silently
        swallow the connection error instead of raising it. Force a cache
        miss so this test genuinely exercises the no-fallback-available path.
        """
        from app.services.z3950_service import Z3950Service, Z3950Error
        import httpx

        service = Z3950Service()

        with patch("app.services.z3950_service.httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)):
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            with pytest.raises(Z3950Error) as exc_info:
                await service.search_by_isbn("978-0-123456-78-9", source="loc")

            assert "failed" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_handles_invalid_source(self):
        """Test that invalid source returns empty results."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        results = await service.search_by_isbn(
            "978-0-123456-78-9", source="nonexistent"
        )

        assert results == []

    @pytest.mark.asyncio
    async def test_handles_empty_isbn(self):
        """Test that empty ISBN returns empty results."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        results = await service.search_by_isbn("", source="loc")
        assert results == []

        results = await service.search_by_isbn("---", source="loc")
        assert results == []

    @pytest.mark.asyncio
    async def test_handles_empty_title(self):
        """Test that empty title returns empty results."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        results = await service.search_by_title("", source="loc")
        assert results == []

        results = await service.search_by_title("   ", source="loc")
        assert results == []


class TestZ3950Sources:
    """Test different Z39.50 sources"""

    def test_supports_library_of_congress(self):
        """Test Library of Congress as Z39.50 source."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        assert "loc" in service.get_available_sources()

        source_config = service.get_source_config("loc")
        assert source_config["host"] is not None
        assert source_config["port"] is not None
        assert source_config["database"] is not None

    def test_supports_oclc_worldcat(self):
        """Test OCLC WorldCat as Z39.50 source (if configured)."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()

        sources = service.get_available_sources()
        assert isinstance(sources, list)
        assert "oclc" in sources

    def test_service_is_available(self):
        """Test that service is always available (SRU fallback)."""
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()
        assert service.available is True


class TestQueryBuilding:
    """Test PQF and CQL query building."""

    def test_pqf_single_criterion(self):
        """Test PQF query with single criterion."""
        from app.services.z3950_service import _build_pqf_query

        query = _build_pqf_query(isbn="9780123456789")
        assert query == '@attr 1=7 "9780123456789"'

    def test_pqf_two_criteria(self):
        """Test PQF query with two criteria."""
        from app.services.z3950_service import _build_pqf_query

        query = _build_pqf_query(title="Gatsby", author="Fitzgerald")
        assert query == '@and @attr 1=4 "Gatsby" @attr 1=1003 "Fitzgerald"'

    def test_pqf_three_criteria(self):
        """Test PQF query with three criteria produces valid prefix notation."""
        from app.services.z3950_service import _build_pqf_query

        query = _build_pqf_query(
            isbn="9780743273565", title="Gatsby", author="Fitzgerald"
        )
        # Should produce nested @and: @and @and A B C
        assert query == (
            '@and @and @attr 1=7 "9780743273565" '
            '@attr 1=4 "Gatsby" '
            '@attr 1=1003 "Fitzgerald"'
        )

    def test_pqf_no_criteria_returns_none(self):
        """Test PQF query with no criteria returns None."""
        from app.services.z3950_service import _build_pqf_query

        assert _build_pqf_query() is None

    def test_cql_single_criterion(self):
        """Test CQL query with single criterion."""
        from app.services.z3950_service import _build_cql_query, _LOC_CQL

        query = _build_cql_query(_LOC_CQL, isbn="9780123456789")
        assert query == 'bath.isbn = "9780123456789"'

    def test_cql_combined_criteria(self):
        """Test CQL query with combined criteria."""
        from app.services.z3950_service import _build_cql_query, _LOC_CQL

        query = _build_cql_query(_LOC_CQL, title="Gatsby", author="Fitzgerald")
        assert 'dc.title = "Gatsby"' in query
        assert 'dc.creator = "Fitzgerald"' in query
        assert " AND " in query

    def test_cql_no_criteria_returns_none(self):
        """Test CQL query with no criteria returns None."""
        from app.services.z3950_service import _build_cql_query, _LOC_CQL

        assert _build_cql_query(_LOC_CQL) is None


class TestZ3950StaleOnError:
    """SRU cache fallback: serve the last good result when the source is down."""

    @pytest.mark.asyncio
    async def test_serves_cached_result_when_source_down(self):
        from app.services import z3950_service as z3
        from app.services.z3950_service import Z3950Service

        service = Z3950Service()
        marc_record = _create_sample_marc_record(
            title="Cached Book", isbn="9780123456789"
        )
        cached_xml = _build_sru_xml_response([marc_record])

        with patch("app.services.z3950_service.httpx.AsyncClient") as mock_client_cls, \
             patch("app.services.z3950_service._sru_cache_get",
                   new=AsyncMock(return_value=cached_xml)), \
             patch("app.services.z3950_service._report_sru_degraded", new=AsyncMock()), \
             patch("app.services.z3950_service.asyncio.sleep", new=AsyncMock()):
            mock_client = AsyncMock()
            mock_client.get.side_effect = z3.httpx.ConnectError("LOC down")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            results = await service.search_by_isbn("9780123456789", source="loc")

        assert len(results) == 1
        assert results[0]["title"] is not None


class TestPerSourceCQL:
    def test_loc_indexes(self):
        from app.services.z3950_service import _build_cql_query, _LOC_CQL
        q = _build_cql_query(_LOC_CQL, isbn="9780262033848")
        assert q == 'bath.isbn = "9780262033848"'

    def test_k10plus_indexes(self):
        from app.services.z3950_service import _build_cql_query, _SRU_FALLBACK_SOURCES
        k10 = next(s for s in _SRU_FALLBACK_SOURCES if s["name"] == "K10plus")
        q = _build_cql_query(k10["cql"], title="algorithms")
        assert q == 'pica.tit = "algorithms"'

    def test_libris_author_index(self):
        from app.services.z3950_service import _build_cql_query, _SRU_FALLBACK_SOURCES
        lib = next(s for s in _SRU_FALLBACK_SOURCES if s["name"] == "Libris")
        q = _build_cql_query(lib["cql"], author="cormen")
        assert q == 'bath.personalName = "cormen"'


class TestSruSearchParams:
    @pytest.mark.asyncio
    async def test_is_fallback_stamped_on_records(self):
        from app.services.z3950_service import Z3950Service
        svc = Z3950Service()
        xml = _build_sru_xml_response([_create_sample_marc_record(title="T", isbn="9780262033848")])
        resp = MagicMock(); resp.text = xml; resp.raise_for_status = MagicMock()
        with patch("app.services.z3950_service.httpx.AsyncClient") as cc, \
             patch("app.services.z3950_service._sru_cache_set", new=AsyncMock()), \
             patch("app.services.z3950_service._report_sru_recovered", new=AsyncMock()):
            c = AsyncMock(); c.get.return_value = resp
            c.__aenter__ = AsyncMock(return_value=c); c.__aexit__ = AsyncMock(return_value=False)
            cc.return_value = c
            res = await svc._sru_search("https://x/sru", 'bath.isbn = "9780262033848"', 1, "K10plus", is_fallback=True)
        assert res and res[0]["is_fallback"] is True
        assert res[0]["source"] == "K10plus"

    @pytest.mark.asyncio
    async def test_report_status_false_suppresses_degraded(self):
        from app.services import z3950_service as z3
        from app.services.z3950_service import Z3950Service, Z3950Error
        svc = Z3950Service()
        with patch("app.services.z3950_service.httpx.AsyncClient") as cc, \
             patch("app.services.z3950_service._report_sru_degraded", new=AsyncMock()) as rep, \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)), \
             patch("app.services.z3950_service.asyncio.sleep", new=AsyncMock()):
            c = AsyncMock(); c.get.side_effect = z3.httpx.ConnectError("down")
            c.__aenter__ = AsyncMock(return_value=c); c.__aexit__ = AsyncMock(return_value=False)
            cc.return_value = c
            with pytest.raises(Z3950Error):
                await svc._sru_search("https://x/sru", "q", 1, "K10plus", report_status=False, max_attempts=1)
            rep.assert_not_awaited()


class TestFailoverHelper:
    def _resp(self, xml):
        r = MagicMock(); r.text = xml; r.raise_for_status = MagicMock(); return r

    def _client_by_url(self, mapping):
        import app.services.z3950_service as z3
        def getter(url, *a, **k):
            for sub, beh in mapping.items():
                if sub in url:
                    if beh[0] == "err":
                        raise z3.httpx.ConnectError("down")
                    return self._resp(beh[1])
            raise z3.httpx.ConnectError("unmapped")
        c = AsyncMock(); c.get.side_effect = getter
        c.__aenter__ = AsyncMock(return_value=c); c.__aexit__ = AsyncMock(return_value=False)
        return c

    @pytest.mark.asyncio
    async def test_prefers_k10plus_when_both_return(self):
        from app.services.z3950_service import Z3950Service
        svc = Z3950Service()
        k = _build_sru_xml_response([_create_sample_marc_record(title="K", isbn="9780262033848")])
        l = _build_sru_xml_response([_create_sample_marc_record(title="L", isbn="9780262033848")])
        client = self._client_by_url({"k10plus": ("xml", k), "libris": ("xml", l)})
        with patch("app.services.z3950_service.httpx.AsyncClient", return_value=client), \
             patch("app.services.z3950_service._sru_cache_set", new=AsyncMock()), \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)), \
             patch("app.services.z3950_service._report_sru_recovered", new=AsyncMock()):
            res = await svc._failover_search(isbn="9780262033848", title=None, author=None,
                                             max_results=1, budget=18.0)
        assert res and res[0]["source"] == "K10plus" and res[0]["is_fallback"] is True

    @pytest.mark.asyncio
    async def test_falls_through_to_libris_when_k10plus_empty(self):
        from app.services.z3950_service import Z3950Service
        svc = Z3950Service()
        empty = _build_sru_xml_response([])
        l = _build_sru_xml_response([_create_sample_marc_record(title="L", isbn="9780262033848")])
        client = self._client_by_url({"k10plus": ("xml", empty), "libris": ("xml", l)})
        with patch("app.services.z3950_service.httpx.AsyncClient", return_value=client), \
             patch("app.services.z3950_service._sru_cache_set", new=AsyncMock()), \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)), \
             patch("app.services.z3950_service._report_sru_recovered", new=AsyncMock()):
            res = await svc._failover_search(isbn="9780262033848", title=None, author=None,
                                             max_results=1, budget=18.0)
        assert res and res[0]["source"] == "Libris"

    @pytest.mark.asyncio
    async def test_returns_empty_when_all_fail(self):
        from app.services.z3950_service import Z3950Service
        svc = Z3950Service()
        client = self._client_by_url({"k10plus": ("err",), "libris": ("err",)})
        with patch("app.services.z3950_service.httpx.AsyncClient", return_value=client), \
             patch("app.services.z3950_service._report_sru_degraded", new=AsyncMock()), \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)), \
             patch("app.services.z3950_service.asyncio.sleep", new=AsyncMock()):
            res = await svc._failover_search(isbn="9780262033848", title=None, author=None,
                                             max_results=1, budget=18.0)
        assert res == []


class TestDispatchFailover:
    def _client_by_url(self, mapping):
        import app.services.z3950_service as z3
        def getter(url, *a, **k):
            for sub, beh in mapping.items():
                if sub in url:
                    if beh[0] == "err":
                        raise z3.httpx.ConnectError("down")
                    r = MagicMock(); r.text = beh[1]; r.raise_for_status = MagicMock(); return r
            raise z3.httpx.ConnectError("unmapped")
        c = AsyncMock(); c.get.side_effect = getter
        c.__aenter__ = AsyncMock(return_value=c); c.__aexit__ = AsyncMock(return_value=False)
        return c

    @pytest.mark.asyncio
    async def test_loc_success_no_failover(self):
        from app.services.z3950_service import Z3950Service
        svc = Z3950Service()
        loc = _build_sru_xml_response([_create_sample_marc_record(title="LOC", isbn="9780262033848")])
        client = self._client_by_url({"loc.gov": ("xml", loc), "k10plus": ("err",), "libris": ("err",)})
        with patch("app.services.z3950_service.httpx.AsyncClient", return_value=client), \
             patch("app.services.z3950_service._sru_cache_set", new=AsyncMock()), \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)), \
             patch("app.services.z3950_service._report_sru_recovered", new=AsyncMock()):
            res = await svc.search_by_isbn("9780262033848", source="loc")
        assert res and res[0]["source"] != "K10plus" and res[0].get("is_fallback") is False

    @pytest.mark.asyncio
    async def test_loc_down_fails_over(self):
        from app.services.z3950_service import Z3950Service
        svc = Z3950Service()
        k = _build_sru_xml_response([_create_sample_marc_record(title="K", isbn="9780262033848")])
        client = self._client_by_url({"loc.gov": ("err",), "k10plus": ("xml", k), "libris": ("err",)})
        with patch("app.services.z3950_service.httpx.AsyncClient", return_value=client), \
             patch("app.services.z3950_service._report_sru_degraded", new=AsyncMock()), \
             patch("app.services.z3950_service._sru_cache_set", new=AsyncMock()), \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)), \
             patch("app.services.z3950_service._report_sru_recovered", new=AsyncMock()), \
             patch("app.services.z3950_service.asyncio.sleep", new=AsyncMock()):
            res = await svc.search_by_isbn("9780262033848", source="loc")
        assert res and res[0]["source"] == "K10plus" and res[0]["is_fallback"] is True

    @pytest.mark.asyncio
    async def test_budget_exhausted_skips_failover(self):
        from app.services.z3950_service import Z3950Service
        import app.services.z3950_service as z3
        svc = Z3950Service()
        client = self._client_by_url({"loc.gov": ("err",), "k10plus": ("xml", "X"), "libris": ("err",)})
        called = {"failover": False}
        async def spy(*a, **k):
            called["failover"] = True; return []
        with patch("app.services.z3950_service.httpx.AsyncClient", return_value=client), \
             patch("app.services.z3950_service._report_sru_degraded", new=AsyncMock()), \
             patch("app.services.z3950_service._sru_cache_get", new=AsyncMock(return_value=None)), \
             patch("app.services.z3950_service.asyncio.sleep", new=AsyncMock()), \
             patch.object(z3, "_SRU_TOTAL_BUDGET_SECONDS", 0.0), \
             patch.object(Z3950Service, "_failover_search", new=spy):
            with pytest.raises(z3.Z3950Error):
                await svc.search_by_isbn("9780262033848", source="loc")
        assert called["failover"] is False
