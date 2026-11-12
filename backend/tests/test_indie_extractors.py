import json

import httpx
import pytest

from app.services.release_sources import ollama_extractor as ox


def _fake_transport(payload: str):
    def handler(request):
        return httpx.Response(200, json={"message": {"content": payload}})
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_extract_announcement_positive(monkeypatch):
    payload = json.dumps({"is_announcement": True, "title": "Dragon Ledger", "author": "R. Vale"})
    monkeypatch.setattr(ox, "_transport_for_tests", _fake_transport(payload), raising=False)
    out = await ox.extract_announcement("My debut novel Dragon Ledger is out today!")
    assert out == {"title": "Dragon Ledger", "author": "R. Vale"}


@pytest.mark.asyncio
async def test_extract_announcement_negative_and_junk(monkeypatch):
    for payload in (
        json.dumps({"is_announcement": False, "title": "", "author": ""}),
        json.dumps({"is_announcement": True, "title": "", "author": "x"}),  # empty title -> None
        "not json",
    ):
        monkeypatch.setattr(ox, "_transport_for_tests", _fake_transport(payload), raising=False)
        assert await ox.extract_announcement("some post") is None


@pytest.mark.asyncio
async def test_extract_itch_book(monkeypatch):
    payload = json.dumps({"is_book": True, "title": "Saltwater Zine", "author": "Mo Finch"})
    monkeypatch.setattr(ox, "_transport_for_tests", _fake_transport(payload), raising=False)
    assert await ox.extract_itch_book("Saltwater Zine by Mo Finch - 40 page prose zine") == {
        "title": "Saltwater Zine", "author": "Mo Finch"
    }
    payload = json.dumps({"is_book": False, "title": "", "author": ""})
    monkeypatch.setattr(ox, "_transport_for_tests", _fake_transport(payload), raising=False)
    assert await ox.extract_itch_book("A platformer game") is None


def _raising_transport():
    def handler(request):
        raise httpx.ReadTimeout("slow model")
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_classifiers_raise_on_transport_failure(monkeypatch):
    monkeypatch.setattr(ox, "_transport_for_tests", _raising_transport(), raising=False)
    with pytest.raises(ox.OllamaUnavailableError):
        await ox.extract_announcement("my new book is out")
    with pytest.raises(ox.OllamaUnavailableError):
        await ox.extract_itch_book("a prose zine")
