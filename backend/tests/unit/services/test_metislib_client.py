# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Unit tests for MetisLibClient — error handling, retry logic, headers, caching.

Uses httpx mocking to simulate MetisLib API responses without network calls.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from httpx import Response, Request, ConnectError, TimeoutException

from app.services.metislib_client import MetisLibClient
from app.services.metislib_errors import (
    MetisLibError,
    MetisLibUnavailable,
    MetisLibTimeout,
    MetisLibNotFound,
    MetisLibAuthError,
    MetisLibValidationError,
)


@pytest.fixture
def metislib_client():
    """Create a MetisLibClient with patched settings."""
    with patch("app.services.metislib_client.get_settings") as mock_settings:
        settings = MagicMock()
        settings.metislib_base_url = "http://metislib-test:8803"
        settings.metislib_api_key = "test-key"
        settings.metislib_library_id = "test-library"
        settings.metislib_timeout_seconds = 5
        settings.redis_url = "redis://localhost:6379"
        mock_settings.return_value = settings
        client = MetisLibClient()
        # Disable Redis for unit tests
        client._redis_client = None
        yield client


def _make_response(status_code: int, json_data: dict = None) -> Response:
    """Build a fake httpx Response."""
    return Response(
        status_code=status_code,
        json=json_data or {},
        request=Request("GET", "http://test"),
    )


@pytest.mark.asyncio
class TestRequestErrorMapping:
    """_request() maps HTTP status codes to correct exceptions."""

    async def test_401_raises_auth_error(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.request.return_value = _make_response(401)
        mock_http.is_closed = False
        metislib_client._http_client = mock_http

        with pytest.raises(MetisLibAuthError):
            await metislib_client._request("GET", "/test")

    async def test_403_raises_forbidden_error(self, metislib_client):
        """403 means the title exists but isn't licensed to this library --
        a distinct signal from 401 (bad API key), not an auth failure."""
        from app.services.metislib_errors import MetisLibForbidden

        mock_http = AsyncMock()
        mock_http.request.return_value = _make_response(403)
        mock_http.is_closed = False
        metislib_client._http_client = mock_http

        with pytest.raises(MetisLibForbidden):
            await metislib_client._request("GET", "/test")

    async def test_404_raises_not_found(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.request.return_value = _make_response(404)
        mock_http.is_closed = False
        metislib_client._http_client = mock_http

        with pytest.raises(MetisLibNotFound):
            await metislib_client._request("GET", "/catalog/999")

    async def test_400_raises_validation_error(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.request.return_value = _make_response(400, {"detail": "Bad field"})
        mock_http.is_closed = False
        metislib_client._http_client = mock_http

        with pytest.raises(MetisLibValidationError) as exc_info:
            await metislib_client._request("POST", "/access/checkout")
        assert "Bad field" in str(exc_info.value)

    async def test_500_raises_server_error(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.request.return_value = _make_response(500)
        mock_http.is_closed = False
        metislib_client._http_client = mock_http

        with pytest.raises(MetisLibError):
            await metislib_client._request("GET", "/test")

    async def test_200_returns_json(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.request.return_value = _make_response(200, {"items": [], "total": 0})
        mock_http.is_closed = False
        metislib_client._http_client = mock_http

        result = await metislib_client._request("GET", "/catalog")
        assert result == {"items": [], "total": 0}


@pytest.mark.asyncio
class TestRetryLogic:
    """Retry behavior on transient errors."""

    async def test_retries_on_502(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        # First call: 502, second call: 200
        mock_http.request.side_effect = [
            _make_response(502),
            _make_response(200, {"ok": True}),
        ]
        metislib_client._http_client = mock_http

        result = await metislib_client._request("GET", "/catalog")
        assert result == {"ok": True}
        assert mock_http.request.call_count == 2

    async def test_retries_on_503(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.side_effect = [
            _make_response(503),
            _make_response(200, {"ok": True}),
        ]
        metislib_client._http_client = mock_http

        result = await metislib_client._request("GET", "/catalog")
        assert result == {"ok": True}

    async def test_retries_on_connect_error(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.side_effect = [
            ConnectError("Connection refused"),
            _make_response(200, {"ok": True}),
        ]
        metislib_client._http_client = mock_http

        result = await metislib_client._request("GET", "/catalog")
        assert result == {"ok": True}

    async def test_raises_unavailable_after_max_retries(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.side_effect = ConnectError("Connection refused")
        metislib_client._http_client = mock_http

        with pytest.raises(MetisLibUnavailable):
            await metislib_client._request("GET", "/catalog")

    async def test_raises_timeout_after_max_retries(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.side_effect = TimeoutException("Timed out")
        metislib_client._http_client = mock_http

        with pytest.raises(MetisLibTimeout):
            await metislib_client._request("GET", "/catalog")


@pytest.mark.asyncio
class TestHeaders:
    """Correct headers sent with requests."""

    async def test_patron_hash_header(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.return_value = _make_response(200, {"items": []})
        metislib_client._http_client = mock_http

        await metislib_client._request("GET", "/access", patron_hash="abc123def456")
        call_kwargs = mock_http.request.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert headers.get("X-Patron-Ref") == "abc123def456"

    async def test_patron_email_never_sent(self, metislib_client):
        # Privacy decision (maintainer, 2026-07-07): patron email does NOT leave L30
        # for MetisLib. The client identifies patrons only by the anonymized
        # X-Patron-Ref hash. This test pins both halves of that decision.
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.return_value = _make_response(200, {"url": "https://example.com"})
        metislib_client._http_client = mock_http

        await metislib_client._request(
            "GET",
            "/access/download/1",
            patron_hash="abc123",
        )
        call_kwargs = mock_http.request.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert "X-Patron-Email" not in headers

        # The API surface must not grow an email path back.
        with pytest.raises(TypeError):
            await metislib_client._request(
                "GET",
                "/access/download/1",
                patron_hash="abc123",
                patron_email="test@lib.org",
            )

    async def test_extra_headers_passed(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.return_value = _make_response(200, {})
        metislib_client._http_client = mock_http

        await metislib_client._request(
            "POST",
            "/ama/sessions",
            extra_headers={"X-Staff-Name": "Jane Doe"},
        )
        call_kwargs = mock_http.request.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert headers.get("X-Staff-Name") == "Jane Doe"

    async def test_no_patron_header_when_none(self, metislib_client):
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.request.return_value = _make_response(200, {})
        metislib_client._http_client = mock_http

        await metislib_client._request("GET", "/catalog")
        call_kwargs = mock_http.request.call_args
        headers = call_kwargs.kwargs.get("headers") or call_kwargs[1].get("headers", {})
        assert "X-Patron-Ref" not in headers


@pytest.mark.asyncio
class TestCatalogMethods:
    """High-level catalog methods."""

    async def test_search_catalog_passes_params(self, metislib_client):
        with patch.object(metislib_client, "_cached_get", new_callable=AsyncMock) as mock_cached:
            mock_cached.return_value = {"items": [], "total": 0}
            result = await metislib_client.search_catalog(query="moss", page=2, per_page=10)
            assert result["total"] == 0
            call_args = mock_cached.call_args
            assert call_args[1]["params"]["q"] == "moss"
            assert call_args[1]["params"]["page"] == 2

    async def test_get_ebook_uses_correct_path(self, metislib_client):
        with patch.object(metislib_client, "_cached_get", new_callable=AsyncMock) as mock_cached:
            mock_cached.return_value = {"id": 42, "title": "Test"}
            result = await metislib_client.get_ebook(42)
            assert result["id"] == 42
            assert "/catalog/42" in mock_cached.call_args[0][1]


@pytest.mark.asyncio
class TestLendingMethods:
    """Checkout/return/hold methods."""

    async def test_checkout_sends_ebook_id(self, metislib_client):
        with patch.object(metislib_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"access_id": 1}
            with patch.object(metislib_client, "_invalidate", new_callable=AsyncMock):
                await metislib_client.checkout(42, "patron_abc")
                mock_req.assert_called_once_with(
                    "POST",
                    "/access/checkout",
                    json_body={"ebook_id": 42},
                    patron_hash="patron_abc",
                )

    async def test_return_ebook_with_rating(self, metislib_client):
        with patch.object(metislib_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"status": "returned"}
            with patch.object(metislib_client, "_invalidate", new_callable=AsyncMock):
                await metislib_client.return_ebook(100, "patron_abc", rating=4)
                call_kwargs = mock_req.call_args
                assert call_kwargs.kwargs["json_body"]["rating"] == 4

    async def test_place_hold(self, metislib_client):
        with patch.object(metislib_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"hold_id": 1}
            await metislib_client.place_hold(42, "patron_abc")
            mock_req.assert_called_once_with(
                "POST",
                "/holds/place",
                json_body={"ebook_id": 42},
                patron_hash="patron_abc",
            )

    async def test_get_patron_checkouts_returns_empty_on_404(self, metislib_client):
        with patch.object(metislib_client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = MetisLibNotFound("Not found", 404)
            result = await metislib_client.get_patron_checkouts("patron_abc")
            assert result == []
