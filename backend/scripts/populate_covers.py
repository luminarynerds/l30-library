#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Batch populate cover images for catalog items.

Uses Open Library (books/audiobooks/ebooks) and iTunes Search API (music/movies).
All APIs are free and require no authentication.

Usage:
    docker-compose exec backend python scripts/populate_covers.py
"""
import sys, os, asyncio, logging
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)
# Suppress noisy HTTP request logging
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://lsc:MIGn7nVocgKpOgiZ0Lo81gS-OJ1VfE_n@database:5432/lsc_library",
)
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ── APIs ──────────────────────────────────────────────────────────────────────

OPEN_LIBRARY_COVERS = "https://covers.openlibrary.org/b/isbn"
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"
ITUNES_API = "https://itunes.apple.com/search"


async def fetch_book_cover(client: httpx.AsyncClient, isbn: str, title: str, author: str | None) -> str | None:
    """Try Open Library by ISBN, then Google Books as fallback."""
    clean_isbn = isbn.replace("-", "").strip()
    if not clean_isbn:
        return None

    # 1) Open Library — direct URL, validate with HEAD
    cover_url = f"{OPEN_LIBRARY_COVERS}/{clean_isbn}-M.jpg"
    try:
        resp = await client.head(cover_url, follow_redirects=True)
        content_len = int(resp.headers.get("content-length", "0"))
        if resp.status_code == 200 and content_len > 1000:
            return cover_url
    except Exception:
        pass

    # 2) Google Books fallback — search by ISBN
    try:
        resp = await client.get(GOOGLE_BOOKS_API, params={"q": f"isbn:{clean_isbn}", "maxResults": 1})
        if resp.status_code == 200:
            data = resp.json()
            if data.get("totalItems", 0) > 0:
                info = data["items"][0].get("volumeInfo", {})
                links = info.get("imageLinks", {})
                thumb = links.get("thumbnail") or links.get("smallThumbnail")
                if thumb:
                    # Upgrade to larger size and ensure HTTPS
                    url = thumb.replace("zoom=1", "zoom=2").replace("&edge=curl", "")
                    return url.replace("http://", "https://")
    except Exception:
        pass

    # 3) Google Books fallback — search by title+author
    if title:
        query = f'intitle:{title}'
        if author:
            query += f'+inauthor:{author}'
        try:
            resp = await client.get(GOOGLE_BOOKS_API, params={"q": query, "maxResults": 1})
            if resp.status_code == 200:
                data = resp.json()
                if data.get("totalItems", 0) > 0:
                    info = data["items"][0].get("volumeInfo", {})
                    links = info.get("imageLinks", {})
                    thumb = links.get("thumbnail") or links.get("smallThumbnail")
                    if thumb:
                        url = thumb.replace("zoom=1", "zoom=2").replace("&edge=curl", "")
                        return url.replace("http://", "https://")
        except Exception:
            pass

    return None


async def fetch_music_cover(client: httpx.AsyncClient, artist: str, title: str) -> str | None:
    """iTunes Search API for music albums."""
    try:
        resp = await client.get(ITUNES_API, params={
            "term": f"{artist} {title}",
            "media": "music",
            "entity": "album",
            "limit": 1,
        })
        if resp.status_code == 200:
            data = resp.json()
            if data.get("resultCount", 0) > 0:
                art = data["results"][0].get("artworkUrl100", "")
                if art:
                    # Upgrade to 600x600
                    return art.replace("100x100bb", "600x600bb")
    except Exception:
        pass
    return None


async def fetch_movie_cover(client: httpx.AsyncClient, title: str, year: int | None) -> str | None:
    """iTunes Search API for movies."""
    try:
        term = title
        resp = await client.get(ITUNES_API, params={
            "term": term,
            "media": "movie",
            "entity": "movie",
            "limit": 5,
        })
        if resp.status_code == 200:
            data = resp.json()
            for result in data.get("results", []):
                # If year provided, try to match
                if year and str(year) in result.get("releaseDate", ""):
                    art = result.get("artworkUrl100", "")
                    if art:
                        return art.replace("100x100bb", "600x600bb")
            # Fallback: first result
            if data.get("resultCount", 0) > 0:
                art = data["results"][0].get("artworkUrl100", "")
                if art:
                    return art.replace("100x100bb", "600x600bb")
    except Exception:
        pass
    return None


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    log.info("=" * 60)
    log.info("  Cover Image Population")
    log.info("=" * 60)

    async with async_session() as db:
        # Get all items needing covers
        result = await db.execute(text("""
            SELECT id, title, author, artist, isbn, item_type, publication_year
            FROM catalog_items
            WHERE cover_url IS NULL OR cover_url = ''
            ORDER BY id
        """))
        items = result.fetchall()
        log.info(f"\n{len(items)} items need covers\n")

        found = 0
        skipped = 0
        failed = 0

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            for i, row in enumerate(items):
                item_id, title, author, artist, isbn, item_type, pub_year = row
                cover_url = None

                try:
                    if item_type in ("book", "audiobook", "ebook"):
                        if isbn:
                            cover_url = await fetch_book_cover(client, isbn, title, author)
                        else:
                            skipped += 1
                            continue

                    elif item_type in ("cd", "vinyl"):
                        lookup_artist = artist or author or ""
                        if lookup_artist:
                            cover_url = await fetch_music_cover(client, lookup_artist, title)
                        else:
                            skipped += 1
                            continue

                    elif item_type in ("dvd", "bluray"):
                        cover_url = await fetch_movie_cover(client, title, pub_year)

                    else:
                        # games, magazines, equipment, kits — no reliable free API
                        skipped += 1
                        continue

                    if cover_url:
                        await db.execute(
                            text("UPDATE catalog_items SET cover_url = :url WHERE id = :id"),
                            {"url": cover_url, "id": item_id},
                        )
                        found += 1
                        log.info(f"  [{found:3d}] ✓ {title[:50]}")
                    else:
                        failed += 1
                        log.info(f"  [---] ✗ {title[:50]} (no cover found)")

                except Exception as e:
                    failed += 1
                    log.info(f"  [ERR] ✗ {title[:50]} ({e})")

                # Commit every 10 items so we don't lose progress
                if found > 0 and found % 10 == 0:
                    await db.commit()
                    log.info(f"  ... committed {found} covers so far")

                # Rate limit: ~2 requests/sec to be polite
                if (i + 1) % 5 == 0:
                    await asyncio.sleep(0.5)

        await db.commit()

    log.info(f"\n{'=' * 60}")
    log.info(f"  Results: {found} covers found, {skipped} skipped, {failed} not found")
    log.info(f"{'=' * 60}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
