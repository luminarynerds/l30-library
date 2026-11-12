# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import datetime, timedelta

from ..models.streaming import StreamingContentType, StreamingService
from .streaming_base import (
    BaseStreamingClient,
    StreamingCheckoutResult,
    StreamingClientError,
    StreamingContent,
    StreamingPatronInfo,
)
from app.core.datetime_utils import utc_now

logger = get_logger(__name__)


class PalaceClient(BaseStreamingClient):

    # Content type mappings from OPDS types to our standard types
    CONTENT_TYPE_MAP = {
        "application/epub+zip": StreamingContentType.EBOOK,
        "application/pdf": StreamingContentType.EBOOK,
        "application/audiobook+json": StreamingContentType.AUDIOBOOK,
        "application/x-mobipocket-ebook": StreamingContentType.EBOOK,
        "ebook": StreamingContentType.EBOOK,
        "audiobook": StreamingContentType.AUDIOBOOK,
    }

    # Default loan durations by content type (in days)
    LOAN_DURATIONS = {
        StreamingContentType.EBOOK: 21,
        StreamingContentType.AUDIOBOOK: 21,
    }

    @property
    def service(self) -> StreamingService:
        return StreamingService.PALACE

    @property
    def service_name(self) -> str:
        return "Palace Project"

    def _get_default_headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/opds+json, application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def search(
        self,
        query: str,
        content_types: list[StreamingContentType] | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[StreamingContent], int]:
        params = {
            "q": query,
            "size": page_size,
            "after": (page - 1) * page_size,
        }

        if content_types:
            media_types = []
            for ct in content_types:
                if ct == StreamingContentType.EBOOK:
                    media_types.append("ebook")
                elif ct == StreamingContentType.AUDIOBOOK:
                    media_types.append("audiobook")
            if media_types:
                params["media"] = ",".join(media_types)

        try:
            response = await self._make_request(
                "GET", "/search", params=params
            )

            items = []
            publications = response.get("publications", [])
            for pub in publications:
                content = self._parse_opds_publication(pub)
                if content:
                    items.append(content)

            total = response.get("metadata", {}).get("numberOfItems", len(items))
            return items, total

        except StreamingClientError:
            raise
        except Exception as e:
            logger.error(f"Error searching Palace Project: {e}")
            raise StreamingClientError(f"Search failed: {e}") from e

    async def get_content(self, external_id: str) -> StreamingContent | None:
        try:
            response = await self._make_request(
                "GET", f"/works/{external_id}"
            )
            return self._parse_opds_publication(response)
        except StreamingClientError as e:
            if e.status_code == 404:
                return None
            raise

    async def checkout(
        self,
        external_id: str,
        patron_barcode: str,
    ) -> StreamingCheckoutResult:
        try:
            response = await self._make_request(
                "POST",
                f"/works/{external_id}/borrow",
                json_data={
                    "patron_barcode": patron_barcode,
                },
            )

            expires_at = None
            if "expires" in response:
                try:
                    expires_at = datetime.fromisoformat(
                        response["expires"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    expires_at = utc_now() + timedelta(days=21)

            return StreamingCheckoutResult(
                success=True,
                external_checkout_id=response.get("id"),
                expires_at=expires_at,
                access_url=response.get("links", [{}])[0].get("href")
                if response.get("links")
                else None,
            )

        except StreamingClientError as e:
            return StreamingCheckoutResult(
                success=False,
                error_message=e.message,
            )

    async def return_content(
        self,
        external_checkout_id: str,
        patron_barcode: str,
    ) -> bool:
        try:
            await self._make_request(
                "POST",
                f"/loans/{external_checkout_id}/revoke",
                json_data={"patron_barcode": patron_barcode},
            )
            return True
        except StreamingClientError as e:
            logger.error(f"Failed to return Palace Project content: {e}")
            return False

    async def get_patron_checkouts(
        self,
        patron_barcode: str,
    ) -> list[StreamingContent]:
        try:
            response = await self._make_request(
                "GET",
                "/loans",
                params={"patron_barcode": patron_barcode},
            )

            items = []
            for loan in response.get("publications", []):
                content = self._parse_opds_publication(loan)
                if content:
                    items.append(content)

            return items

        except StreamingClientError:
            raise
        except Exception as e:  # noqa: BLE001  # external streaming API boundary; degrade to empty result
            logger.error(f"Error getting Palace Project loans: {e}")
            return []

    async def get_patron_info(
        self,
        patron_barcode: str,
    ) -> StreamingPatronInfo | None:
        try:
            response = await self._make_request(
                "GET",
                "/patrons/me",
                params={"patron_barcode": patron_barcode},
            )

            return StreamingPatronInfo(
                external_patron_id=response.get("id", patron_barcode),
                checkouts_this_month=response.get("loans_count", 0),
                checkout_limit=response.get("loan_limit", 10),
                remaining_checkouts=response.get("loans_remaining", 10),
            )

        except StreamingClientError as e:
            if e.status_code == 404:
                return None
            raise

    def get_app_deep_link(self, external_id: str) -> str | None:
        return f"palace://work/{external_id}"

    def get_web_deep_link(self, external_id: str) -> str | None:
        return f"{self.base_url}/works/{external_id}"

    def _map_content_type(self, raw_type: str) -> StreamingContentType:
        return self.CONTENT_TYPE_MAP.get(
            raw_type.lower() if raw_type else "",
            StreamingContentType.EBOOK,
        )

    def _parse_opds_publication(self, data: dict) -> StreamingContent | None:
        if not data:
            return None

        try:
            metadata = data.get("metadata", data)
            external_id = str(
                metadata.get("identifier", data.get("id", ""))
            )
            if not external_id:
                return None

            # Determine content type from links or metadata
            content_type = StreamingContentType.EBOOK
            for link in data.get("links", []):
                link_type = link.get("type", "")
                if "audiobook" in link_type:
                    content_type = StreamingContentType.AUDIOBOOK
                    break
            if metadata.get("@type") == "http://schema.org/Audiobook":
                content_type = StreamingContentType.AUDIOBOOK

            # Parse duration for audiobooks
            duration = None
            if content_type == StreamingContentType.AUDIOBOOK:
                duration_raw = metadata.get("duration")
                if duration_raw and isinstance(duration_raw, (int, float)):
                    duration = int(duration_raw / 60) if duration_raw > 60 else int(duration_raw)

            # Parse availability
            availability = data.get("availability", {})
            is_available = availability.get("state", "available") == "available"

            # Parse author(s)
            authors = metadata.get("author", [])
            author_name = None
            if isinstance(authors, list) and authors:
                author_name = authors[0].get("name") if isinstance(authors[0], dict) else str(authors[0])
            elif isinstance(authors, dict):
                author_name = authors.get("name")
            elif isinstance(authors, str):
                author_name = authors

            # Parse subjects/genres
            subjects = metadata.get("subject", [])
            genres = None
            if subjects:
                if isinstance(subjects, list):
                    genres = [
                        s.get("name", str(s)) if isinstance(s, dict) else str(s)
                        for s in subjects
                    ]

            # Get cover image
            cover_url = None
            for img in data.get("images", []):
                if isinstance(img, dict):
                    cover_url = img.get("href")
                    break
                elif isinstance(img, str):
                    cover_url = img
                    break

            return StreamingContent(
                external_id=external_id,
                title=metadata.get("title", "Unknown Title"),
                content_type=content_type,
                author=author_name,
                description=metadata.get("description"),
                isbn=metadata.get("identifier"),
                duration_minutes=duration,
                release_year=None,
                genres=genres,
                cover_url=cover_url,
                rating=None,
                is_available=is_available,
                raw_data=data,
            )

        except Exception as e:  # noqa: BLE001  # tolerate malformed publication entries; degrade to None
            logger.error(f"Error parsing Palace Project publication: {e}")
            return None

    async def get_opds_feed(
        self,
        feed_url: str | None = None,
    ) -> list[StreamingContent]:
        endpoint = feed_url or "/catalog"

        try:
            response = await self._make_request("GET", endpoint)

            items = []
            for pub in response.get("publications", []):
                content = self._parse_opds_publication(pub)
                if content:
                    items.append(content)

            return items

        except StreamingClientError:
            raise
        except Exception as e:  # noqa: BLE001  # external streaming API boundary; degrade to empty result
            logger.error(f"Error fetching Palace Project OPDS feed: {e}")
            return []
