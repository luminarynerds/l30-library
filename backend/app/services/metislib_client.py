# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
import hashlib
import asyncio
from app.core.logging import get_logger
from typing import Optional

import httpx

try:
    import redis.asyncio as aioredis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    RedisError = Exception  # type: ignore[misc,assignment]

from ..core.config import get_settings
from ..utils.circuit_breaker import (
    circuit_breaker_manager,
    CircuitBreakerException,
)
from .metislib_errors import (
    MetisLibError, MetisLibUnavailable, MetisLibTimeout,
    MetisLibNotFound, MetisLibAuthError, MetisLibForbidden, MetisLibValidationError
)

logger = get_logger(__name__)

from ..core.cache_strategies import CacheTTL

# Cache TTLs - using centralized tiers from cache_strategies
CACHE_TTL_SHORT = CacheTTL.MEDIUM    # 5 min - catalog, trending, discovery
CACHE_TTL_MEDIUM = CacheTTL.STANDARD # 10 min - ebook detail, author, genres
CACHE_TTL_LONG = CacheTTL.HALF_HOUR  # 30 min - sitemap

MAX_RETRIES = 1
RETRY_DELAY = 1.0
RETRYABLE_STATUS_CODES = {502, 503, 504}


class MetisLibClient:

    def __init__(self):
        settings = get_settings()
        self._base_url = settings.metislib_base_url.rstrip("/")
        self._api_key = settings.metislib_api_key
        self._library_id = settings.metislib_library_id
        self._timeout = float(settings.metislib_timeout_seconds)
        self._public_url = settings.metislib_public_url.rstrip('/')
        self._http_client: Optional[httpx.AsyncClient] = None
        self._redis_client: Optional[aioredis.Redis] = None
        # Shared circuit breaker for all metislib calls. Trips open after 5
        # consecutive infra-level failures (connection refused, timeout, 5xx)
        # and fast-fails subsequent calls for ~30s before re-probing. 4xx
        # responses do NOT count as failures — they are translated outside
        # the breaker in _request() so a 404 on a stale ebook ID can't trip
        # the whole integration.
        self._breaker = circuit_breaker_manager.get_or_create(
            "metislib", failure_threshold=5, recovery_timeout=30,
        )

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self._timeout, connect=3.0),
                limits=httpx.Limits(
                    max_keepalive_connections=5,
                    keepalive_expiry=30,
                ),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def _get_redis(self) -> Optional[aioredis.Redis]:
        if not REDIS_AVAILABLE:
            return None
        if self._redis_client is None:
            try:
                settings = get_settings()
                self._redis_client = await aioredis.from_url(
                    settings.redis_url, decode_responses=True
                )
            except (RedisError, OSError) as e:
                logger.warning(f"Redis connection failed: {e}")
                return None
        return self._redis_client

    async def _http_attempt(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        headers: dict | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        client = await self._get_http_client()
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.request(
                    method, path,
                    params=params,
                    json=json_body,
                    headers=headers or {},
                    timeout=timeout or self._timeout,
                )
                if response.status_code in RETRYABLE_STATUS_CODES and attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                # 5xx is terminal infra failure (counts toward breaker)
                if response.status_code >= 500:
                    raise MetisLibError(
                        f"Server error: {response.status_code}",
                        response.status_code,
                    )
                return response
            except httpx.ConnectError:
                self._http_client = None
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise MetisLibUnavailable("MetisLib is unreachable") from None
            except (httpx.RemoteProtocolError, httpx.ReadError, httpx.WriteError):
                self._http_client = None
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise MetisLibUnavailable("Connection lost to MetisLib") from None
            except httpx.TimeoutException:
                if attempt < MAX_RETRIES:
                    await asyncio.sleep(RETRY_DELAY)
                    continue
                raise MetisLibTimeout("Request timed out") from None

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict | None = None,
        json_body: dict | None = None,
        patron_hash: str | None = None,
        timeout: float | None = None,
        extra_headers: dict | None = None,
    ) -> dict:
        headers: dict = {}
        if patron_hash:
            headers["X-Patron-Ref"] = patron_hash
        if extra_headers:
            headers.update(extra_headers)

        try:
            response = await self._breaker.call(
                self._http_attempt,
                method, path,
                params=params,
                json_body=json_body,
                headers=headers,
                timeout=timeout,
            )
        except CircuitBreakerException:
            raise MetisLibUnavailable(
                "metislib circuit breaker open — upstream marked unavailable"
            ) from None

        # 4xx translation happens outside the breaker
        if response.status_code == 401:
            raise MetisLibAuthError("API key rejected", 401)
        if response.status_code == 403:
            # 403 means the title exists but isn't licensed to this library,
            # not an auth failure. Surface it as a "not available here" signal.
            raise MetisLibForbidden("Title not available at this library", 403)
        if response.status_code == 404:
            raise MetisLibNotFound("Resource not found", 404)
        if response.status_code == 400:
            try:
                detail = response.json().get("detail", "Validation error")
            except (json.JSONDecodeError, ValueError):
                detail = "Validation error"
            raise MetisLibValidationError(str(detail), 400)

        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as e:
            raise MetisLibError(f"Invalid JSON response: {e}") from e

    async def _cached_get(
        self, cache_key: str, path: str, *, params: dict | None = None, ttl: int = CACHE_TTL_SHORT
    ) -> dict:
        redis = await self._get_redis()
        cached = None
        if redis:
            try:
                cached = await redis.get(cache_key)
                if cached:
                    return self._fix_cover_urls(json.loads(cached))
            except (RedisError, json.JSONDecodeError, ValueError):
                logger.debug("MetisLib Redis cache read failed", exc_info=True)

        try:
            data = await self._request("GET", path, params=params)
        except (MetisLibUnavailable, MetisLibTimeout, MetisLibError):
            if cached:
                logger.warning("MetisLib error, serving stale cache for %s", cache_key)
                return json.loads(cached)
            raise

        if redis:
            try:
                await redis.setex(cache_key, int(ttl), json.dumps(data, default=str))
            except RedisError:
                logger.debug("MetisLib Redis cache write failed", exc_info=True)

        return self._fix_cover_urls(data)

    async def _invalidate(self, *patterns: str):
        redis = await self._get_redis()
        if not redis:
            return
        for pattern in patterns:
            try:
                keys = []
                async for key in redis.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    await redis.delete(*keys)
            except RedisError:
                logger.debug("MetisLib Redis cache invalidation failed", exc_info=True)

    def _hash_params(self, **kwargs) -> str:
        raw = json.dumps(kwargs, sort_keys=True, default=str)
        return hashlib.md5(raw.encode()).hexdigest()[:12]

    def _fix_cover_urls(self, data):
        if isinstance(data, dict):
            if "cover_url" in data and data["cover_url"] and data["cover_url"].startswith("/"):
                data["cover_url"] = self._public_url + data["cover_url"]
            if "items" in data and isinstance(data["items"], list):
                for item in data["items"]:
                    if isinstance(item, dict) and "cover_url" in item and item["cover_url"] and item["cover_url"].startswith("/"):
                        item["cover_url"] = self._public_url + item["cover_url"]
        return data

    # ---- Catalog & Discovery ----

    async def search_catalog(self, query: str | None = None, filters: dict | None = None, page: int = 1, per_page: int = 20, q: str | None = None) -> dict:
        query = query or q
        params = {"page": page, "limit": per_page}
        if query:
            params["q"] = query
        if filters:
            params.update(filters)
        key = f"metislib:catalog:{self._hash_params(**params)}"
        return await self._cached_get(key, "/catalog", params=params)

    async def get_ebook(self, ebook_id: int, entry_type: str | None = None) -> dict:
        params = {"entry_type": entry_type} if entry_type else None
        key = f"metislib:ebook:{ebook_id}:{entry_type or 'auto'}"
        return await self._cached_get(key, f"/catalog/{ebook_id}", params=params, ttl=CACHE_TTL_MEDIUM)

    async def get_featured(self) -> dict:
        return await self._cached_get("metislib:featured", "/catalog", params={"featured": True, "limit": 10})

    async def get_popular_ebooks(self, limit: int = 20) -> dict:
        key = f"metislib:popular:{limit}"
        return await self._cached_get(key, "/analytics/popular", params={"limit": limit})

    async def list_genres(self) -> list[dict]:
        data = await self._cached_get("metislib:genres", "/catalog", params={"genres_only": True}, ttl=CACHE_TTL_MEDIUM)
        return data if isinstance(data, list) else data.get("items", [])

    async def get_collections(self, include_library: bool = True) -> dict:
        params = {}
        if include_library:
            params["include_library"] = True
        return await self._cached_get("metislib:collections", "/collections", params=params)

    # ---- Lending ----

    async def checkout(self, ebook_id: int, patron_hash: str) -> dict:
        result = await self._request(
            "POST", "/access/checkout",
            json_body={"ebook_id": ebook_id},
            patron_hash=patron_hash,
        )
        await self._invalidate(f"metislib:ebook:{ebook_id}", "metislib:trending:*")
        return result

    async def return_ebook(self, access_id: int, patron_hash: str, rating: int | None = None) -> dict:
        body = {"access_id": access_id}
        if rating is not None:
            body["rating"] = rating
        result = await self._request(
            "POST", f"/access/return/{access_id}",
            json_body=body,
            patron_hash=patron_hash,
        )
        await self._invalidate("metislib:ebook:*", "metislib:trending:*")
        return result

    async def get_download_url(self, access_id: int, patron_hash: str) -> dict:
        return await self._request(
            "GET", f"/access/download/{access_id}",
            patron_hash=patron_hash,
        )

    async def get_patron_checkouts(self, patron_hash: str) -> list[dict]:
        try:
            data = await self._request("GET", "/access", patron_hash=patron_hash, params={"active": True})
            return data if isinstance(data, list) else data.get("items", [])
        except MetisLibNotFound:
            # 404 here means metislib has no access records for this patron
            # at all — a legitimately-empty list, not a failure. Log it at
            # warning so a misconfigured endpoint (wrong path, bad prefix)
            # is at least visible in operator logs rather than silently
            # reporting "no checkouts" to every patron.
            logger.warning(
                "metislib GET /access?active=true returned 404 for patron %s… — serving empty list",
                (patron_hash[:8] if patron_hash else "(none)"),
            )
            return []

    # ---- Holds ----

    async def place_hold(self, ebook_id: int, patron_hash: str) -> dict:
        return await self._request(
            "POST", "/holds/place",
            json_body={"ebook_id": ebook_id},
            patron_hash=patron_hash,
        )

    async def cancel_hold(self, hold_id: int, patron_hash: str) -> dict:
        return await self._request("DELETE", f"/holds/{hold_id}", patron_hash=patron_hash)

    async def hold_status(self, ebook_id: int, patron_hash: str) -> dict:
        """The patron's current hold standing for an ebook (catalog or indie).

        Raises MetisLibNotFound when the patron has no active hold on it.
        """
        return await self._request(
            "GET", "/holds/status",
            params={"ebook_id": ebook_id},
            patron_hash=patron_hash,
        )

    async def leave_indie_hold(self, ebook_id: int, patron_hash: str) -> dict:
        """Leave an indie waitlist (ebook-scoped; catalog holds use cancel_hold)."""
        return await self._request(
            "DELETE", f"/holds/indie/{ebook_id}", patron_hash=patron_hash,
        )

    # ---- Analytics ----

    async def get_library_usage(self, days: int = 30) -> dict:
        key = f"metislib:usage:{days}"
        return await self._cached_get(key, "/analytics/usage", params={"days": days})

    # ---- Indie Lending (L30 → MetisLib) ----

    async def get_preview(self, metislib_ebook_id: int) -> dict:
        key = f"metislib:preview:{metislib_ebook_id}"
        return await self._cached_get(key, f"/content/{metislib_ebook_id}/preview", ttl=CACHE_TTL_LONG)

    async def borrow_indie(self, metislib_ebook_id: int, patron_hash: str) -> dict:
        result = await self._request(
            "POST", f"/access/indie/{metislib_ebook_id}/borrow",
            patron_hash=patron_hash,
        )
        await self._invalidate(f"metislib:ebook:{metislib_ebook_id}", "metislib:trending:*")
        return result

    async def return_indie(self, metislib_borrow_id: int, patron_hash: str) -> dict:
        result = await self._request(
            "POST", f"/access/indie/{metislib_borrow_id}/return",
            patron_hash=patron_hash,
        )
        await self._invalidate("metislib:ebook:*", "metislib:trending:*")
        return result

    # ---- Indie Publish (L30 → MetisLib) ----

    async def register_or_get_author(self, pen_name: str, email: str, bio: str | None = None) -> dict:
        try:
            # Try to register
            data = await self._request("POST", "/author/register", json_body={
                "email": email,
                "password": email,  # MetisLib will hash it; author won't use this login
                "display_name": pen_name,
                "pen_name": pen_name,
                "bio": bio or "",
            })
            return data
        except MetisLibError:
            # Author may already exist — try to login
            try:
                data = await self._request("POST", "/author/login", json_body={
                    "email": email,
                    "password": email,
                })
                return data
            except Exception as e:
                logger.error("Failed to register/login author in MetisLib: %s", e)
                raise

    async def publish_ebook(
        self,
        author_token: str,
        title: str,
        description: str,
        genre: str | None = None,
        language: str = "en",
        isbn: str | None = None,
        publication_year: int | None = None,
        cover_url: str | None = None,
        content_warnings: list[str] | None = None,
        purchase_url: str | None = None,
    ) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/content/submit",
                json={
                    "title": title,
                    "description": description or "",
                    "genre": genre,
                    "language": language,
                    "isbn": isbn,
                    "publication_year": publication_year,
                    "cover_url": cover_url,
                    "content_warnings": content_warnings or [],
                    "purchase_url": purchase_url,
                },
                headers={"Authorization": f"Bearer {author_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def upload_ebook_file(
        self,
        author_token: str,
        metislib_ebook_id: int,
        file_content: bytes,
        filename: str,
    ) -> dict:
        async with httpx.AsyncClient(timeout=max(self._timeout, 30)) as client:
            response = await client.post(
                f"{self._base_url}/content/{metislib_ebook_id}/upload",
                files={"file": (filename, file_content, "application/octet-stream")},
                headers={"Authorization": f"Bearer {author_token}"},
            )
            response.raise_for_status()
            return response.json()

    async def submit_for_review(self, author_token: str, metislib_ebook_id: int) -> dict:
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._base_url}/content/{metislib_ebook_id}/submit-for-review",
                headers={"Authorization": f"Bearer {author_token}"},
            )
            response.raise_for_status()
            return response.json()

    # ---- AMA ----

    async def ama_list_sessions(self, status=None, page=1, limit=20) -> dict:
        params = {"page": page, "limit": limit}
        if status:
            params["status"] = status
        return await self._request("GET", "/ama/sessions", params=params)

    async def ama_get_session(self, session_id: int) -> dict:
        return await self._request("GET", f"/ama/sessions/{session_id}")

    async def ama_get_session_detail(self, session_id: int, patron_hash=None) -> dict:
        return await self._request("GET", f"/ama/sessions/{session_id}", patron_hash=patron_hash)

    async def ama_create_session(self, data: dict, staff_name=None) -> dict:
        return await self._request(
            "POST", "/ama/sessions", json_body=data,
            extra_headers={"X-Staff-Name": staff_name} if staff_name else None,
        )

    async def ama_update_session(self, session_id: int, data: dict) -> dict:
        return await self._request("PUT", f"/ama/sessions/{session_id}", json_body=data)

    async def ama_transition_status(self, session_id: int, status: str) -> dict:
        return await self._request("PUT", f"/ama/sessions/{session_id}/status", json_body={"status": status})

    async def ama_delete_session(self, session_id: int) -> None:
        await self._request("DELETE", f"/ama/sessions/{session_id}")

    async def ama_submit_question(self, session_id: int, patron_hash: str, question_text: str, display_name=None) -> dict:
        body = {"question_text": question_text}
        if display_name:
            body["display_name"] = display_name
        return await self._request("POST", f"/ama/sessions/{session_id}/questions", json_body=body, patron_hash=patron_hash)

    async def ama_toggle_upvote(self, question_id: int, patron_hash: str) -> dict:
        return await self._request("POST", f"/ama/questions/{question_id}/upvote", patron_hash=patron_hash)

    async def ama_get_my_questions(self, session_id: int, patron_hash: str) -> dict:
        return await self._request("GET", f"/ama/sessions/{session_id}/my-questions", patron_hash=patron_hash)

    async def ama_get_moderation_queue(self, session_id: int) -> dict:
        return await self._request("GET", f"/ama/sessions/{session_id}/moderate")

    async def ama_moderate_question(self, question_id: int, action: str, staff_name: str, reason=None) -> dict:
        body = {"action": action}
        if reason:
            body["reason"] = reason
        return await self._request(
            "POST", f"/ama/questions/{question_id}/moderate",
            json_body=body, extra_headers={"X-Staff-Name": staff_name},
        )

    async def ama_answer_question(self, question_id: int, answer_text: str, author_token: str) -> dict:
        return await self._request(
            "POST", f"/ama/questions/{question_id}/answer",
            json_body={"answer_text": answer_text},
            extra_headers={"X-Author-Token": author_token},
        )

    async def ama_toggle_feature(self, question_id: int) -> dict:
        return await self._request("POST", f"/ama/questions/{question_id}/feature")

    async def ama_reorder_question(self, question_id: int, display_order: int) -> dict:
        return await self._request("PUT", f"/ama/questions/{question_id}/order", json_body={"display_order": display_order})

    # ---- Authority Records (MARC-A) ----

    async def get_authority(self, author_id: int) -> dict:
        return await self._cached_get(
            f"metislib:authority:{author_id}",
            f"/marc/authority/{author_id}",
            ttl=CACHE_TTL_SHORT,
        )

    async def get_authority_xml(self, author_id: int) -> bytes:
        client = await self._get_http_client()
        response = await client.get(f"/marc/authority/{author_id}/export")
        if response.status_code == 404:
            raise MetisLibNotFound("Author not found", 404)
        return response.content

    async def get_authority_with_bibs_xml(self, author_id: int) -> bytes:
        client = await self._get_http_client()
        response = await client.get(f"/marc/authority/{author_id}/with-bibs")
        if response.status_code == 404:
            raise MetisLibNotFound("Author not found", 404)
        return response.content

    async def submit_overlay_decision(
        self, author_id: int, change_id: int, decision: str, notes: str | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            f"/marc/authority/{author_id}/overlay-decision",
            json_body={"change_id": change_id, "decision": decision, "notes": notes},
        )

    async def get_overlay_history(self, author_id: int) -> dict:
        return await self._request("GET", f"/marc/authority/{author_id}/overlay-history")

    async def submit_correction(
        self, author_id: int, field_tag: str, reason: str,
        current_value: str | None = None, suggested_value: str | None = None,
    ) -> dict:
        return await self._request(
            "POST",
            f"/marc/authority/{author_id}/corrections",
            json_body={
                "field_tag": field_tag,
                "current_value": current_value,
                "suggested_value": suggested_value,
                "reason": reason,
            },
        )

    async def list_corrections(self, author_id: int) -> dict:
        return await self._request("GET", f"/marc/authority/{author_id}/corrections")

    async def get_marc_bib(self, ebook_id: int) -> dict:
        return await self._cached_get(
            f"metislib:marc:{ebook_id}",
            f"/marc/{ebook_id}",
            ttl=CACHE_TTL_MEDIUM,
        )

    # ---- Liveness probe (for L30 /health/ready) ----

    async def ping(self, timeout: float = 2.0) -> dict:
        import time as _time
        start = _time.perf_counter()
        try:
            client = await self._get_http_client()
            # /health lives at the server root, not under /api/v1, so hit
            # the absolute URL derived from base_url's origin.
            origin = self._base_url.split("/api/v1")[0].rstrip("/")
            response = await client.get(
                f"{origin}/health", timeout=timeout,
            )
            latency_ms = round((_time.perf_counter() - start) * 1000, 2)
            return {
                "ok": response.status_code == 200,
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                "breaker_state": self._breaker.state.value,
                "breaker_failures": self._breaker.failure_count,
            }
        except Exception as e:  # noqa: BLE001 - health probe must report any failure as a structured dict, not raise
            latency_ms = round((_time.perf_counter() - start) * 1000, 2)
            return {
                "ok": False,
                "error": f"{type(e).__name__}: {e}",
                "latency_ms": latency_ms,
                "breaker_state": self._breaker.state.value,
                "breaker_failures": self._breaker.failure_count,
            }

    # ---- Cleanup ----

    async def close(self):
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()
        if self._redis_client:
            await self._redis_client.close()


# Singleton
_client: MetisLibClient | None = None
_mock_client = None


def get_metislib_client():
    settings = get_settings()
    if settings.metislib_mock:
        global _mock_client
        if _mock_client is None:
            from .metislib_mock import MetisLibMockClient
            _mock_client = MetisLibMockClient()
            logger.info("Using MetisLib MOCK client (demo mode)")
        return _mock_client

    global _client
    if _client is None:
        _client = MetisLibClient()
    return _client
