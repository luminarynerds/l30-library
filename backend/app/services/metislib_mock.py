# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Mock MetisLib backend for demo/development without external API."""
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


class MetisLibMockClient:
    """Mock MetisLib client returning realistic ebook catalog data."""

    _active_borrows: dict[str, list[dict]] = {}
    _next_access_id: int = 2000

    # Simplified mock data for 14 indie ebooks
    MOCK_EBOOKS = [
        {
            "id": 1, "title": "The Moss Grows Back", "author_name": "Sage Holloway",
            "description": "A coming-of-age novel set in a small Oregon logging town.",
            "genre": "Literary Fiction", "language": "en", "format": "pdf",
            "average_rating": 4.6, "total_ratings": 142, "source_type": "indie",
            "isbn": "978-1-0000-0001-0", "page_count": 312, "cover_url": None,
        },
        {
            "id": 2, "title": "Neon Pagoda", "author_name": "Ren Takahashi",
            "description": "In a near-future Osaka, a rogue AI fights to save digital temples.",
            "genre": "Science Fiction", "language": "en", "format": "epub",
            "average_rating": 4.8, "total_ratings": 234, "source_type": "indie",
            "isbn": "978-1-0000-0002-7", "page_count": 368, "cover_url": None,
        },
        {
            "id": 3, "title": "Salt and Ceiba", "author_name": "Marisol Vega",
            "description": "Three generations of women in a coastal Dominican town.",
            "genre": "Magical Realism", "language": "en", "format": "pdf",
            "average_rating": 4.5, "total_ratings": 98, "source_type": "indie",
            "isbn": "978-1-0000-0003-4", "page_count": 260, "cover_url": None,
        },
        {
            "id": 4, "title": "The Quiet Floor", "author_name": "Devon Marsh",
            "description": "A locked-room thriller set in a public library after hours.",
            "genre": "Thriller", "language": "en", "format": "epub",
            "average_rating": 4.3, "total_ratings": 312, "source_type": "indie",
            "isbn": "978-1-0000-0004-1", "page_count": 336, "cover_url": None,
        },
        {
            "id": 5, "title": "Lavender Milk", "author_name": "Arlo Chen",
            "description": "A cozy mystery where a nonbinary tea shop owner investigates.",
            "genre": "Cozy Mystery", "language": "en", "format": "pdf",
            "average_rating": 4.7, "total_ratings": 189, "source_type": "indie",
            "isbn": "978-1-0000-0005-8", "page_count": 232, "cover_url": None,
        },
        {
            "id": 6, "title": "Between Harbors", "author_name": "Nadia Okafor",
            "description": "Essays on growing up between Lagos and Toronto.",
            "genre": "Memoir", "language": "en", "format": "epub",
            "average_rating": 4.4, "total_ratings": 76, "source_type": "indie",
            "isbn": "978-1-0000-0006-5", "page_count": 208, "cover_url": None,
        },
        {
            "id": 7, "title": "The Cartographer's Daughter", "author_name": "Jasper Wren",
            "description": "An autistic mapmaker discovers that blank spaces are doors.",
            "genre": "Fantasy", "language": "en", "format": "pdf",
            "average_rating": 4.6, "total_ratings": 154, "source_type": "indie",
            "isbn": "978-1-0000-0007-2", "page_count": 420, "cover_url": None,
        },
        {
            "id": 8, "title": "Smoke and Mirrors", "author_name": "Sage Holloway",
            "description": "A poet's journey through loss and rediscovery.",
            "genre": "Poetry", "language": "en", "format": "epub",
            "average_rating": 4.5, "total_ratings": 112, "source_type": "indie",
            "isbn": "978-1-0000-0008-9", "page_count": 144, "cover_url": None,
        },
        {
            "id": 9, "title": "City of Ghosts", "author_name": "Ren Takahashi",
            "description": "A haunting tale of a city where memories become real.",
            "genre": "Science Fiction", "language": "en", "format": "pdf",
            "average_rating": 4.7, "total_ratings": 198, "source_type": "indie",
            "isbn": "978-1-0000-0009-6", "page_count": 384, "cover_url": None,
        },
        {
            "id": 10, "title": "Threads of Gold", "author_name": "Marisol Vega",
            "description": "A modern reimagining of ancient Caribbean legends.",
            "genre": "Magical Realism", "language": "en", "format": "epub",
            "average_rating": 4.6, "total_ratings": 126, "source_type": "indie",
            "isbn": "978-1-0000-0010-2", "page_count": 296, "cover_url": None,
        },
        {
            "id": 11, "title": "Midnight Investigation", "author_name": "Devon Marsh",
            "description": "A detective's race against time in a snow-covered town.",
            "genre": "Thriller", "language": "en", "format": "pdf",
            "average_rating": 4.4, "total_ratings": 287, "source_type": "indie",
            "isbn": "978-1-0000-0011-9", "page_count": 312, "cover_url": None,
        },
        {
            "id": 12, "title": "Whispers in the Woods", "author_name": "Arlo Chen",
            "description": "When strange whispers echo through a small forest town.",
            "genre": "Cozy Mystery", "language": "en", "format": "epub",
            "average_rating": 4.5, "total_ratings": 167, "source_type": "indie",
            "isbn": "978-1-0000-0012-6", "page_count": 278, "cover_url": None,
        },
        {
            "id": 13, "title": "Crossing Borders", "author_name": "Nadia Okafor",
            "description": "Stories of women crossing physical and emotional boundaries.",
            "genre": "Memoir", "language": "en", "format": "pdf",
            "average_rating": 4.3, "total_ratings": 89, "source_type": "indie",
            "isbn": "978-1-0000-0013-3", "page_count": 256, "cover_url": None,
        },
        {
            "id": 14, "title": "Wings of Wonder", "author_name": "Jasper Wren",
            "description": "A young aviator discovers a world hidden in the clouds.",
            "genre": "Fantasy", "language": "en", "format": "epub",
            "average_rating": 4.7, "total_ratings": 201, "source_type": "indie",
            "isbn": "978-1-0000-0014-0", "page_count": 398, "cover_url": None,
        },
    ]

    async def search_catalog(self, query: str | None = None, filters: dict | None = None, page: int = 1, per_page: int = 20, q: str | None = None) -> dict:
        """Search ebook catalog."""
        search_query = query or q or ""
        search_lower = search_query.lower()

        # Filter by query
        results = self.MOCK_EBOOKS
        if search_query:
            results = [
                ebook for ebook in self.MOCK_EBOOKS
                if (search_lower in ebook["title"].lower() or
                    search_lower in ebook["author_name"].lower() or
                    search_lower in ebook["description"].lower())
            ]

        # Apply other filters
        if filters:
            source_type = filters.get("source_type")
            if source_type:
                results = [e for e in results if e.get("source_type") == source_type]

        total = len(results)
        offset = (page - 1) * per_page
        paginated = results[offset: offset + per_page]

        return {
            "items": paginated,
            "total": total,
            "page": page,
            "pages": (total + per_page - 1) // per_page,
        }

    async def get_ebook(self, ebook_id: int, entry_type: str | None = None) -> dict:
        """Get full detail for a single ebook."""
        for ebook in self.MOCK_EBOOKS:
            if ebook["id"] == ebook_id:
                return ebook
        raise ValueError(f"Ebook {ebook_id} not found")

    async def get_featured(self) -> dict:
        """Get featured ebooks."""
        featured = self.MOCK_EBOOKS[:5]
        return {
            "items": featured,
            "total": len(featured),
            "page": 1,
            "pages": 1,
        }

    async def get_popular_ebooks(self, limit: int = 20) -> dict:
        """Get popular ebooks by rating."""
        sorted_ebooks = sorted(self.MOCK_EBOOKS, key=lambda x: x["average_rating"], reverse=True)
        results = sorted_ebooks[:limit]
        return {
            "items": results,
            "total": len(results),
            "page": 1,
            "pages": 1,
        }

    async def get_collections(self, include_library: bool = True) -> dict:
        """Get curated collections."""
        return {
            "items": [
                {"id": 1, "title": "Indie Favorites", "description": "Community picks"},
                {"id": 2, "title": "New Releases", "description": "Latest ebooks"},
            ],
            "total": 2,
        }

    async def checkout(self, ebook_id: int, patron_hash: str) -> dict:
        """Borrow an ebook and track it in-memory."""
        ebook = await self.get_ebook(ebook_id)
        MetisLibMockClient._next_access_id += 1
        access_id = MetisLibMockClient._next_access_id
        expires = (datetime.now(timezone.utc) + timedelta(days=21)).isoformat()
        record = {
            "access_id": access_id,
            "ebook_id": ebook_id,
            "title": ebook["title"],
            "author_name": ebook["author_name"],
            "cover_url": ebook.get("cover_url"),
            "format": ebook.get("format", "epub"),
            "status": "active",
            "expires_at": expires,
            "download_url": f"https://metislib.local/download/{ebook_id}",
        }
        MetisLibMockClient._active_borrows.setdefault(patron_hash, []).append(record)
        return record

    async def get_patron_checkouts(self, patron_hash: str) -> list[dict]:
        """Get user's current checkouts from session tracking."""
        borrows = MetisLibMockClient._active_borrows.get(patron_hash, [])
        # Return only what the patron actually has out. (A previous version
        # returned a static demo checkout for ebook_id=1 when empty; that now
        # collides with the borrow guard, which reads this list to reject
        # double-borrows -- a fresh patron borrowing ebook 1 would 409.)
        return [b for b in borrows if b["status"] == "active"]

    async def return_ebook(self, access_id: int, patron_hash: str, rating: int | None = None) -> dict:
        """Return an ebook and remove from session tracking."""
        borrows = MetisLibMockClient._active_borrows.get(patron_hash, [])
        for b in borrows:
            if b["access_id"] == access_id:
                b["status"] = "returned"
                return {"access_id": access_id, "status": "returned", "rating": rating}
        return {"access_id": access_id, "status": "returned", "rating": rating}

    async def place_hold(self, ebook_id: int, patron_hash: str) -> dict:
        """Place a hold on an ebook."""
        return {
            "hold_id": 2001,
            "ebook_id": ebook_id,
            "position": 1,
            "status": "pending",
        }

    # ---- Orders (Staff Procurement) ----

    _next_order_id: int = 3000
    _order_history: list[dict] = []

    async def create_order(self, ebook_id: int, copies: int, po_number: str | None = None) -> dict:
        ebook = await self.get_ebook(ebook_id)
        MetisLibMockClient._next_order_id += 1
        order_number = f"ORD-{MetisLibMockClient._next_order_id}"
        price_per_copy = 9.99
        order = {
            "order_number": order_number,
            "ebook_id": ebook_id,
            "title": ebook["title"],
            "copies": copies,
            "price_per_copy": price_per_copy,
            "amount": round(price_per_copy * copies, 2),
            "po_number": po_number,
            "status": "pending",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        MetisLibMockClient._order_history.append(order)
        return order

    async def confirm_order(self, order_number: str) -> dict:
        for order in MetisLibMockClient._order_history:
            if order["order_number"] == order_number:
                order["status"] = "confirmed"
                return {
                    "order_number": order_number,
                    "status": "confirmed",
                    "copies_owned": order["copies"],
                }
        return {"order_number": order_number, "status": "confirmed", "copies_owned": 1}

    async def get_order_history(self, page: int = 1, page_size: int = 20) -> dict:
        orders = list(reversed(MetisLibMockClient._order_history))
        total = len(orders)
        offset = (page - 1) * page_size
        paginated = orders[offset: offset + page_size]
        return {
            "items": paginated,
            "total": total,
            "page": page,
            "pages": max(1, (total + page_size - 1) // page_size),
        }

    async def borrow_indie(self, metislib_ebook_id: int, patron_hash: str) -> dict:
        """Mock indie ebook borrow via MetisLib."""
        return {
            "borrow_id": 5001,
            "status": "granted",
            "access_token": "mock_token",
            "due_at": (datetime.now(timezone.utc) + timedelta(days=21)).isoformat(),
            "duration_days": 21,
        }

    async def return_indie(self, metislib_borrow_id: int, patron_hash: str) -> dict:
        """Mock indie ebook return via MetisLib."""
        return {"status": "returned"}

    async def get_library_usage(self, days: int = 30) -> dict:
        """Get library usage analytics."""
        return {
            "total_checkouts": 1247,
            "active_users": 89,
            "total_available_titles": len(self.MOCK_EBOOKS),
        }
