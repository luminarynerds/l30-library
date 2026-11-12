import json

import httpx
import pytest
from app.services.release_sources import ollama_extractor


@pytest.mark.asyncio
async def test_extract_titles_parses_json(monkeypatch):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": json.dumps({"books": [
            {"title": "Villa Coco", "author": "Andrew Sean Greer"},
            {"title": "", "author": "x"},
        ]})}}

    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return FakeResp()

    monkeypatch.setattr(ollama_extractor.httpx, "AsyncClient", FakeClient)
    out = await ollama_extractor.extract_titles("some most-anticipated post body")
    assert out == [{"title": "Villa Coco", "author": "Andrew Sean Greer"}]


@pytest.mark.asyncio
async def test_extract_titles_handles_bad_json(monkeypatch):
    class FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"message": {"content": "not json"}}
    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): return FakeResp()
    monkeypatch.setattr(ollama_extractor.httpx, "AsyncClient", FakeClient)
    assert await ollama_extractor.extract_titles("x") == []


@pytest.mark.asyncio
async def test_extract_titles_raises_on_transport_failure(monkeypatch):
    class FakeClient:
        def __init__(self, *a, **k): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def post(self, *a, **k): raise httpx.ReadTimeout("slow model")
    monkeypatch.setattr(ollama_extractor.httpx, "AsyncClient", FakeClient)
    with pytest.raises(ollama_extractor.OllamaUnavailableError):
        await ollama_extractor.extract_titles("a long listicle body")
