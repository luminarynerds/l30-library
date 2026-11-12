# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import os

import httpx

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Generous ceiling: qwen2.5:3b prompt-eval on this CPU host can take minutes on
# long listicle bodies. With raise-on-failure semantics a timeout only defers
# the post to the next weekly run, so this is a performance knob, not a
# data-loss knob.
_TIMEOUT = 300.0


class OllamaUnavailableError(RuntimeError):
    """Ollama could not be reached or did not answer in time.

    Raised (never swallowed) so connectors skip the post WITHOUT marking it
    processed -- it gets retried on the next run. Silently returning [] here
    is what let the editorial RSS pipeline run dead for a month while
    consuming its backlog (2026-07-07 postmortem)."""


_SYSTEM = (
    "You extract forthcoming/anticipated BOOK titles from an article. "
    "Return ONLY JSON of the form {\"books\": [{\"title\": str, \"author\": str}]}. "
    "Include only titles the article itself presents as forthcoming, newly announced, "
    "or anticipated. Exclude backlist books, classics, re-reads, reviews of "
    "already-published books, publication or article names, and the article's own "
    "headline, section names, and commentary. When unsure whether a book is "
    "forthcoming, omit it."
)

# Test seam: pytest injects an httpx.MockTransport here; None in prod.
_transport_for_tests: httpx.AsyncBaseTransport | None = None

_ANNOUNCE_SYSTEM = (
    "You classify one social media post about books. Decide whether the POSTER is announcing "
    "their own newly released or upcoming book (not a review, reading update, or promo of "
    "someone else's book). Return ONLY JSON of the form "
    '{"is_announcement": bool, "title": str, "author": str}. '
    "title = the announced book title; author = the author name as stated in the post, else empty string."
)

_ITCH_SYSTEM = (
    "You classify one itch.io storefront listing. Decide whether it is a prose BOOK someone reads "
    "(novel, novella, story collection, narrative zine, nonfiction book) rather than a game, game "
    "asset, software, or tabletop rules product. Return ONLY JSON of the form "
    '{"is_book": bool, "title": str, "author": str}. '
    "title = the book title without any 'by <name>' suffix; author = creator name if present, else empty string."
)


async def extract_titles(post_text: str) -> list[dict]:
    """Run an editorial post body through Ollama and return [{'title','author'}].

    Raises OllamaUnavailableError on transport failure (timeout, HTTP error) so
    callers skip the post without consuming it. A well-formed response with no
    parseable books returns [] (deterministic garbage should not recycle the
    same post through the per-run cap forever)."""
    settings = get_settings()
    base_url = settings.ollama_base_url.rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM},
            {"role": "user", "content": post_text[:12000]},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, transport=_transport_for_tests) as client:
            resp = await client.post(f"{base_url}/api/chat", json=body)
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "")
    except httpx.HTTPError as e:
        logger.error(f"Ollama extraction request failed: {e}")
        raise OllamaUnavailableError(f"Ollama chat failed for model {model}: {e}") from e
    try:
        data = json.loads(content)
    except (json.JSONDecodeError, TypeError):
        logger.error("Ollama extraction returned non-JSON")
        return []
    out: list[dict] = []
    for b in data.get("books", []):
        title = (b.get("title") or "").strip()
        if not title:
            continue
        out.append({"title": title, "author": (b.get("author") or "").strip()})
    return out


async def _chat_json(system: str, user_text: str) -> dict | None:
    """POST one chat to Ollama with format:json.

    Raises OllamaUnavailableError on transport failure; returns the parsed dict,
    or None when the model answered with unparseable content."""
    settings = get_settings()
    base_url = settings.ollama_base_url.rstrip("/")
    model = os.environ.get("OLLAMA_MODEL", "llama3.2")
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_text[:12000]},
        ],
        "stream": False,
        "format": "json",
        "options": {"temperature": 0},
    }
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, transport=_transport_for_tests) as client:
            resp = await client.post(f"{base_url}/api/chat", json=body)
            resp.raise_for_status()
            content = resp.json().get("message", {}).get("content", "")
    except httpx.HTTPError as e:
        logger.error(f"Ollama extraction request failed: {e}")
        raise OllamaUnavailableError(f"Ollama chat failed for model {model}: {e}") from e
    try:
        return json.loads(content)
    except (json.JSONDecodeError, TypeError):
        logger.error("Ollama extraction returned non-JSON")
        return None


async def extract_announcement(post_text: str) -> dict | None:
    """Classify a social post; return {'title','author'} if it announces the poster's own new book.

    None = negative classification (or unparseable model output). Transport
    failures raise OllamaUnavailableError -- callers skip without marking."""
    data = await _chat_json(_ANNOUNCE_SYSTEM, post_text)
    if not data or not data.get("is_announcement"):
        return None
    title = (data.get("title") or "").strip()
    if not title:
        return None
    return {"title": title, "author": (data.get("author") or "").strip()}


async def extract_itch_book(item_text: str) -> dict | None:
    """Classify an itch.io listing; return {'title','author'} if it is a prose book.

    None = negative classification (or unparseable model output). Transport
    failures raise OllamaUnavailableError -- callers skip without marking."""
    data = await _chat_json(_ITCH_SYSTEM, item_text)
    if not data or not data.get("is_book"):
        return None
    title = (data.get("title") or "").strip()
    if not title:
        return None
    return {"title": title, "author": (data.get("author") or "").strip()}
