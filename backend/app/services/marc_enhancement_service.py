# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

import httpx

logger = get_logger(__name__)

GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"


class MarcEnhancementService:

    async def _search_google_books(
        self, isbn: Optional[str] = None, search_query: Optional[str] = None
    ) -> Optional[dict]:
        if not isbn and not search_query:
            return None

        query = f"isbn:{isbn}" if isbn else search_query
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(GOOGLE_BOOKS_API, params={"q": query, "maxResults": 1})
                resp.raise_for_status()
                data = resp.json()
                items = data.get("items", [])
                if items:
                    return items[0].get("volumeInfo", {})
        except (httpx.HTTPError, ValueError) as e:
            logger.warning("Google Books API lookup failed: %s", e)
        return None

    async def enhance_from_google_books(
        self, item, search_query: Optional[str] = None
    ) -> dict:
        vol = await self._search_google_books(
            isbn=getattr(item, "isbn", None),
            search_query=search_query or getattr(item, "title", None),
        )
        if not vol:
            return {}

        return {
            "description": vol.get("description"),
            "page_count": vol.get("pageCount"),
            "publisher": vol.get("publisher"),
            "publication_year": (vol.get("publishedDate") or "")[:4] or None,
            "subjects": vol.get("categories", []),
            "cover_url": (vol.get("imageLinks") or {}).get("thumbnail"),
            "dewey_hint": None,
        }

    async def update_catalog_item_from_google_books(
        self, item, search_query: Optional[str] = None, overwrite_existing: bool = False
    ):
        enhanced = await self.enhance_from_google_books(item, search_query)

        for field, value in enhanced.items():
            if value is None:
                continue
            if field == "subjects":
                # subjects is a list; skip if item already has subjects and not overwriting
                current = getattr(item, "subjects", None)
                if current and not overwrite_existing:
                    continue
                setattr(item, "subjects", value)
            elif field == "dewey_hint":
                if overwrite_existing or not getattr(item, "dewey_decimal", None):
                    if value:
                        item.dewey_decimal = value
            else:
                current = getattr(item, field, None)
                if current and not overwrite_existing:
                    continue
                if hasattr(item, field):
                    setattr(item, field, value)

        return item


marc_enhancement_service = MarcEnhancementService()
