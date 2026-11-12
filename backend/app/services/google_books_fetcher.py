# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from app.core.logging import get_logger
import re
from datetime import date
from typing import Any

import httpx

logger = get_logger(__name__)

from ..models.release_tracker import AgeRating
from ..schemas.release_tracker import AuthorSearchResult, ExternalBookResult


class GoogleBooksFetcher:

    BASE_URL = "https://www.googleapis.com/books/v1/volumes"
    TIMEOUT = 10.0

    # Keywords for age rating detection
    CHILD_KEYWORDS = [
        "juvenile",
        "children",
        "picture book",
        "kids",
        "early reader",
        "board book",
    ]
    TEEN_KEYWORDS = ["young adult", "teen", "ya fiction", "teenage"]

    def __init__(self, api_key: str | None = None):
        from app.core.config import get_settings
        self.api_key = api_key or get_settings().google_books_api_key

    async def search_authors(
        self, query: str, max_results: int = 10
    ) -> list[AuthorSearchResult]:
        params = {
            "q": f"inauthor:{query}",
            "maxResults": min(max_results, 40),
            "printType": "books",
        }
        if self.api_key:
            params["key"] = self.api_key

        try:
            from ..core.external_api_tracker import track_external_call
            async with track_external_call("google_books", "search_authors"):
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
        except httpx.TimeoutException:
            logger.warning(f"Google Books API timeout searching authors: {query}")
            return []
        except httpx.RequestError as e:
            logger.warning(f"Google Books API request error: {e}")
            return []
        except Exception as e:  # noqa: BLE001 - defensive boundary: httpx narrows above cover network errors; this catches unexpected (e.g. JSON parse, KeyError) and returns empty list to keep caller working
            logger.error(f"Unexpected error searching Google Books authors: {e}")
            return []

        # Extract unique authors from results
        authors_seen = {}
        for item in data.get("items", []):
            volume_info = item.get("volumeInfo", {})
            for author in volume_info.get("authors", []):
                if author.lower() not in authors_seen:
                    authors_seen[author.lower()] = AuthorSearchResult(
                        source="google_books",
                        source_id=item.get("id", ""),
                        name=author,
                        bio=None,
                        image_url=None,
                        book_count=1,
                    )
                else:
                    authors_seen[author.lower()].book_count += 1

        return list(authors_seen.values())[:max_results]

    async def fetch_author_books(
        self,
        author_name: str,
        max_results: int = 40,
        order_by: str = "newest",
    ) -> list[ExternalBookResult]:
        params = {
            "q": f'inauthor:"{author_name}"',
            "maxResults": min(max_results, 40),
            "orderBy": order_by,
            "printType": "books",
        }
        if self.api_key:
            params["key"] = self.api_key

        try:
            from ..core.external_api_tracker import track_external_call
            async with track_external_call("google_books", "fetch_author_books"):
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
        except httpx.TimeoutException:
            logger.warning(f"Google Books API timeout fetching author books: {author_name}")
            return []
        except httpx.RequestError as e:
            logger.warning(f"Google Books API request error: {e}")
            return []
        except Exception as e:  # noqa: BLE001 - defensive boundary: httpx narrows above cover network errors; this catches unexpected (e.g. JSON parse, KeyError) and returns empty list to keep caller working
            logger.error(f"Unexpected error fetching author books: {e}")
            return []

        books = []
        for item in data.get("items", []):
            try:
                book = self._parse_volume(item)
                if book:
                    books.append(book)
            except Exception as e:  # noqa: BLE001 - per-iteration boundary: one bad volume payload must not crash the parse loop
                logger.warning("Failed to parse Google Books volume: %s", e)
                continue

        return books

    async def fetch_upcoming_releases(
        self,
        author_name: str,
        from_date: date | None = None,
    ) -> list[ExternalBookResult]:
        books = await self.fetch_author_books(author_name, order_by="newest")

        if from_date:
            books = [b for b in books if b.release_date and b.release_date >= from_date]

        return books

    async def search_books(
        self,
        query: str,
        max_results: int = 20,
    ) -> list[ExternalBookResult]:
        params = {
            "q": query,
            "maxResults": min(max_results, 40),
            "printType": "books",
        }
        if self.api_key:
            params["key"] = self.api_key

        try:
            from ..core.external_api_tracker import track_external_call
            async with track_external_call("google_books", "search_books"):
                async with httpx.AsyncClient(timeout=self.TIMEOUT) as client:
                    response = await client.get(self.BASE_URL, params=params)
                    response.raise_for_status()
                    data = response.json()
        except httpx.TimeoutException:
            logger.warning(f"Google Books API timeout searching books: {query}")
            return []
        except httpx.RequestError as e:
            logger.warning(f"Google Books API request error: {e}")
            return []
        except Exception as e:  # noqa: BLE001 - defensive boundary: httpx narrows above cover network errors; this catches unexpected (e.g. JSON parse, KeyError) and returns empty list to keep caller working
            logger.error(f"Unexpected error searching books: {e}")
            return []

        books = []
        for item in data.get("items", []):
            try:
                book = self._parse_volume(item)
                if book:
                    books.append(book)
            except Exception as e:  # noqa: BLE001 - per-iteration boundary: one bad volume payload must not crash the parse loop
                logger.warning("Failed to parse Google Books volume: %s", e)
                continue

        return books

    def _parse_volume(self, item: dict[str, Any]) -> ExternalBookResult | None:
        volume_info = item.get("volumeInfo", {})
        sale_info = item.get("saleInfo", {})

        title = volume_info.get("title")
        if not title:
            return None

        # Parse release date
        release_date, is_exact = self._parse_release_date(
            volume_info.get("publishedDate", "")
        )

        # Parse ISBN
        isbn_13, isbn_10 = self._parse_isbns(volume_info.get("industryIdentifiers", []))

        # Determine age rating
        age_rating = self._determine_age_rating(volume_info)

        # Get price
        list_price = None
        if sale_info.get("listPrice"):
            list_price = sale_info["listPrice"].get("amount")

        # Get cover image
        cover_url = None
        image_links = volume_info.get("imageLinks", {})
        cover_url = image_links.get("thumbnail") or image_links.get("smallThumbnail")
        if cover_url:
            # Convert to HTTPS and larger size
            cover_url = cover_url.replace("http://", "https://")
            cover_url = cover_url.replace("&zoom=1", "&zoom=2")

        return ExternalBookResult(
            source="google_books",
            source_id=item.get("id", ""),
            title=title,
            subtitle=volume_info.get("subtitle"),
            authors=volume_info.get("authors", []),
            release_date=release_date,
            is_date_exact=is_exact,
            isbn_13=isbn_13,
            isbn_10=isbn_10,
            age_rating=age_rating,
            categories=volume_info.get("categories", []),
            publisher=volume_info.get("publisher"),
            page_count=volume_info.get("pageCount"),
            list_price=list_price,
            cover_url=cover_url,
            description=volume_info.get("description"),
        )

    def _parse_release_date(self, date_str: str) -> tuple[date | None, bool]:
        if not date_str:
            return None, False

        # Full date: 2026-05-12
        if re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
            try:
                return date.fromisoformat(date_str), True
            except ValueError:
                return None, False

        # Year-month: 2026-05
        if re.match(r"^\d{4}-\d{2}$", date_str):
            try:
                return date.fromisoformat(f"{date_str}-01"), False
            except ValueError:
                return None, False

        # Year only: 2026
        if re.match(r"^\d{4}$", date_str):
            try:
                return date(int(date_str), 1, 1), False
            except ValueError:
                return None, False

        return None, False

    def _parse_isbns(self, identifiers: list[dict]) -> tuple[str | None, str | None]:
        isbn_13 = None
        isbn_10 = None

        for ident in identifiers:
            id_type = ident.get("type", "")
            id_value = ident.get("identifier", "")

            if id_type == "ISBN_13":
                isbn_13 = id_value
            elif id_type == "ISBN_10":
                isbn_10 = id_value

        return isbn_13, isbn_10

    def _determine_age_rating(self, volume_info: dict) -> str:
        # Check maturity rating first
        if volume_info.get("maturityRating") == "MATURE":
            return AgeRating.ADULT.value

        # Check categories
        categories = volume_info.get("categories", [])
        categories_lower = " ".join(categories).lower()

        # Check for children's content
        for keyword in self.CHILD_KEYWORDS:
            if keyword in categories_lower:
                return AgeRating.CHILD.value

        # Check for teen/YA content
        for keyword in self.TEEN_KEYWORDS:
            if keyword in categories_lower:
                return AgeRating.TEEN.value

        # Default to adult
        return AgeRating.ADULT.value
