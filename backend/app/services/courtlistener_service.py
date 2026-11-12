# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
from app.core.logging import get_logger
from datetime import datetime, timedelta
from typing import Optional

import httpx
from redis.exceptions import RedisError
from pydantic import BaseModel

from ..core.cache import get_redis
from ..core.config import get_settings

logger = get_logger(__name__)

from ..core.cache_strategies import CacheTTL

COURTLISTENER_BASE = "https://www.courtlistener.com/api/rest/v4"
CACHE_TTL = CacheTTL.LONG       # 1 hour
SEARCH_CACHE_TTL = CacheTTL.HALF_HOUR  # 30 minutes
COURTS_CACHE_TTL = CacheTTL.DAILY  # 24 hours


class BankruptcyFiling(BaseModel):
    docket_id: int
    case_name: str
    docket_number: str
    date_filed: Optional[str] = None
    court_name: str
    court_id: str
    chapter: Optional[str] = None
    trustee: Optional[str] = None
    courtlistener_url: str


class BankruptcyCourt(BaseModel):
    id: str
    short_name: str
    full_name: str
    url: str


class CourtListenerService:

    def __init__(self):
        settings = get_settings()
        self.api_token = getattr(settings, 'courtlistener_api_token', None) or ""
        self.headers = {}
        if self.api_token:
            self.headers["Authorization"] = f"Token {self.api_token}"

    async def get_bankruptcy_courts(self) -> list[BankruptcyCourt]:
        cache_key = "cl:bankruptcy:courts"

        try:
            redis = await get_redis()
            if redis:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return [BankruptcyCourt(**c) for c in data]
        except (RedisError, json.JSONDecodeError, ValueError):
            pass

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    f"{COURTLISTENER_BASE}/courts/",
                    params={"jurisdiction": "FB", "page_size": 100},
                    headers=self.headers,
                )
                resp.raise_for_status()
                data = resp.json()

            courts = []
            for court in data.get("results", []):
                courts.append(BankruptcyCourt(
                    id=court["id"],
                    short_name=court.get("short_name", ""),
                    full_name=court.get("full_name", ""),
                    url=court.get("url", ""),
                ))

            try:
                if redis and courts:
                    await redis.setex(cache_key, int(COURTS_CACHE_TTL), json.dumps([c.model_dump() for c in courts]))
            except RedisError:
                pass

            return courts
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            logger.error(f"Failed to fetch bankruptcy courts: {e}")
            return []

    async def get_recent_filings(
        self,
        court_id: Optional[str] = None,
        days: int = 7,
        page_size: int = 20,
    ) -> list[BankruptcyFiling]:
        cache_key = f"cl:bankruptcy:recent:{court_id or 'all'}:{days}"

        try:
            redis = await get_redis()
            if redis:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return [BankruptcyFiling(**f) for f in data]
        except (RedisError, json.JSONDecodeError, ValueError):
            pass

        try:
            since = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
            params: dict = {
                "type": "r",
                "q": "bankruptcy",
                "filed_after": since,
                "order_by": "dateFiled desc",
                "page_size": min(page_size, 20),
            }
            if court_id:
                params["court"] = court_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{COURTLISTENER_BASE}/search/",
                    params=params,
                    headers=self.headers,
                )
                resp.raise_for_status()
                data = resp.json()

            filings = self._parse_search_results(data)

            try:
                if redis and filings:
                    await redis.setex(cache_key, int(CACHE_TTL), json.dumps([f.model_dump() for f in filings]))
            except RedisError:
                pass

            return filings
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            logger.error(f"Failed to fetch bankruptcy filings: {e}")
            return []

    async def search_filings(
        self,
        query: str,
        court_id: Optional[str] = None,
        page_size: int = 20,
    ) -> list[BankruptcyFiling]:
        cache_key = f"cl:bankruptcy:search:{query}:{court_id or 'all'}"

        try:
            redis = await get_redis()
            if redis:
                cached = await redis.get(cache_key)
                if cached:
                    data = json.loads(cached)
                    return [BankruptcyFiling(**f) for f in data]
        except (RedisError, json.JSONDecodeError, ValueError):
            pass

        try:
            params: dict = {
                "type": "r",
                "q": f"bankruptcy {query}",
                "order_by": "dateFiled desc",
                "page_size": min(page_size, 20),
            }
            if court_id:
                params["court"] = court_id

            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    f"{COURTLISTENER_BASE}/search/",
                    params=params,
                    headers=self.headers,
                )
                resp.raise_for_status()
                data = resp.json()

            filings = self._parse_search_results(data)

            try:
                if redis and filings:
                    await redis.setex(cache_key, int(SEARCH_CACHE_TTL), json.dumps([f.model_dump() for f in filings]))
            except RedisError:
                pass

            return filings
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError) as e:
            logger.error(f"Failed to search bankruptcy filings: {e}")
            return []

    def _parse_search_results(self, data: dict) -> list[BankruptcyFiling]:
        filings = []
        for result in data.get("results", []):
            docket_id = result.get("docket_id", 0)
            abs_url = result.get("docket_absolute_url") or f"/docket/{docket_id}/"
            filings.append(BankruptcyFiling(
                docket_id=docket_id,
                case_name=result.get("caseName", "Unknown"),
                docket_number=result.get("docketNumber", ""),
                date_filed=result.get("dateFiled"),
                court_name=result.get("court_citation_string", "") or result.get("court", ""),
                court_id=result.get("court_id", "") or result.get("court", ""),
                chapter=result.get("chapter"),
                courtlistener_url=f"https://www.courtlistener.com{abs_url}",
            ))
        return filings
