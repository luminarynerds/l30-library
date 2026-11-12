# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path

from app.clients.metislib_opds_client import MetisLibOpdsClient

FIXTURE = Path(__file__).parent.parent / "fixtures" / "metislib_indie_opds_page1.xml"


def test_parse_indie_feed_extracts_owned_fields():
    xml = FIXTURE.read_text()
    client = MetisLibOpdsClient()
    entries, next_page = client.parse_feed(xml)

    assert len(entries) == 20
    first = entries[0]
    assert isinstance(first.metislib_ebook_id, int)
    assert first.title
    assert first.author_pen_name
    assert first.acquisition_href.endswith(f"/opds/borrow/{first.metislib_ebook_id}")
    assert next_page is not None


def test_parse_indie_feed_extracts_copies_and_optional_cover():
    xml = FIXTURE.read_text()
    entries, _ = MetisLibOpdsClient().parse_feed(xml)

    by_id = {e.metislib_ebook_id: e for e in entries}
    # entry 164 has copies total=5/available=5 and NO cover link
    e164 = by_id[164]
    assert e164.copies_total == 5
    assert e164.copies_available == 5
    assert e164.cover_url is None
    # entry 89 carries a cover link
    e89 = by_id[89]
    assert e89.cover_url and e89.cover_url.startswith("http")


import pytest
import httpx
from unittest.mock import AsyncMock, patch
from app.clients.metislib_opds_client import MetisLibOpdsClient, MetisLibOpdsClientError


@pytest.mark.asyncio
async def test_fetch_indie_feed_wraps_timeout(monkeypatch):
    client = MetisLibOpdsClient()
    async def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timed out")
    with patch("httpx.AsyncClient.get", new=raise_timeout):
        with pytest.raises(MetisLibOpdsClientError, match="unreachable"):
            await client.fetch_indie_feed()


@pytest.mark.asyncio
async def test_fetch_ebook_bytes_wraps_connect_error(monkeypatch):
    client = MetisLibOpdsClient()
    async def raise_connect(*args, **kwargs):
        raise httpx.ConnectError("refused")
    with patch("httpx.AsyncClient.get", new=raise_connect):
        with pytest.raises(MetisLibOpdsClientError, match="unreachable"):
            await client.fetch_ebook_bytes(164)


@pytest.mark.asyncio
async def test_fetch_ebook_bytes_url_has_single_api_v1(monkeypatch):
    """fetch_ebook_bytes must not double /api/v1 when metislib_base_url already includes it."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from app.core.config import get_settings

    captured = {}

    class FakeResponse:
        status_code = 200
        content = b"PK\x03\x04epub"

    async def fake_get(self_client, url, **kwargs):
        captured["url"] = url
        return FakeResponse()

    with patch("httpx.AsyncClient.get", new=fake_get):
        client = MetisLibOpdsClient()
        await client.fetch_ebook_bytes(12)

    settings = get_settings()
    base = settings.metislib_base_url.rstrip("/")
    url = captured["url"]
    assert url == f"{base}/opds/borrow/12", f"unexpected URL: {url}"
    # The old bug appended /api/v1/opds/borrow when base already ends in /api/v1.
    # After the fix the path segment is just /opds/borrow/<id> regardless of base.
    assert "/api/v1/opds/borrow" not in url, f"doubled /api/v1 still present: {url}"
