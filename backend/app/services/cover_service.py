# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional
from enum import StrEnum

import httpx

from ..core.config import get_settings

logger = get_logger(__name__)
settings = get_settings()

# Open Library API (books)
OPEN_LIBRARY_COVERS_BASE = "https://covers.openlibrary.org/b/isbn"
OPEN_LIBRARY_API = "https://openlibrary.org/api/books"

# Google Books API
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# iTunes Search API (music, movies - no API key required)
ITUNES_SEARCH_API = "https://itunes.apple.com/search"

# MusicBrainz Cover Art Archive (music - no API key required)
MUSICBRAINZ_SEARCH_API = "https://musicbrainz.org/ws/2/release"
COVERART_ARCHIVE_API = "https://coverartarchive.org/release"

# OMDb API (movies - requires free API key, set via environment variable)
OMDB_API = "https://www.omdbapi.com"


class MediaType(StrEnum):
    book = "book"
    music = "music"
    movie = "movie"
    game = "game"


def get_open_library_cover_url(isbn: str, size: str = "M") -> str:
    return f"{OPEN_LIBRARY_COVERS_BASE}/{isbn}-{size}.jpg"


async def check_open_library_cover_exists(isbn: str) -> Optional[str]:
    if not isbn:
        return None

    # Clean ISBN (remove hyphens)
    clean_isbn = isbn.replace("-", "").strip()
    if not clean_isbn:
        return None

    cover_url = get_open_library_cover_url(clean_isbn, "M")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            # HEAD request to check if image exists
            response = await client.head(cover_url, follow_redirects=True)
            # Open Library returns a 1x1 pixel image for missing covers
            # Check Content-Length - real covers are > 1000 bytes
            content_length = response.headers.get("content-length", "0")
            if response.status_code == 200 and int(content_length) > 1000:
                return cover_url
    except httpx.TimeoutException:
        logger.debug(f"Timeout checking Open Library cover for ISBN {isbn}")
    except httpx.RequestError as e:
        logger.debug(f"Error checking Open Library cover for ISBN {isbn}: {e}")
    except ValueError as e:
        logger.warning("Failed to parse Open Library cover response for ISBN %s: %s", isbn, e)

    return None


async def fetch_google_books_cover(
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> Optional[str]:
    if not isbn and not title:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Build search query
            if isbn:
                clean_isbn = isbn.replace("-", "").strip()
                query = f"isbn:{clean_isbn}"
            else:
                query = title
                if author:
                    query = f"{title} {author}"

            params = {
                "q": query,
                "maxResults": 1,
                "printType": "books",
            }

            response = await client.get(GOOGLE_BOOKS_API, params=params)
            response.raise_for_status()
            data = response.json()

            items = data.get("items", [])
            if items:
                volume_info = items[0].get("volumeInfo", {})
                image_links = volume_info.get("imageLinks", {})

                # Get thumbnail and enhance quality
                cover_url = image_links.get("thumbnail") or image_links.get(
                    "smallThumbnail"
                )
                if cover_url:
                    # Convert to HTTPS and get larger image
                    cover_url = cover_url.replace("http://", "https://")
                    cover_url = cover_url.replace("&zoom=1", "&zoom=2")
                    # Remove edge curl effect
                    cover_url = cover_url.replace("&edge=curl", "")
                    return cover_url

    except httpx.HTTPStatusError as e:
        logger.debug(f"Google Books API error {e.response.status_code} for {isbn or title}")
    except httpx.TimeoutException:
        logger.debug(f"Timeout fetching Google Books cover for {isbn or title}")
    except httpx.RequestError as e:
        logger.debug(f"Error fetching Google Books cover: {e}")
    except (KeyError, ValueError, IndexError) as e:
        logger.debug(f"Could not parse Google Books data: {e}")

    return None


async def get_cover_url(
    isbn: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
) -> Optional[str]:
    # Try Open Library first (fastest - direct URL check)
    if isbn:
        cover = await check_open_library_cover_exists(isbn)
        if cover:
            logger.debug(f"Found Open Library cover for ISBN {isbn}")
            return cover

    # Try Google Books with ISBN
    if isbn:
        cover = await fetch_google_books_cover(isbn=isbn)
        if cover:
            logger.debug(f"Found Google Books cover for ISBN {isbn}")
            return cover

    # Fallback to Google Books title search
    if title:
        cover = await fetch_google_books_cover(title=title, author=author)
        if cover:
            logger.debug(f"Found Google Books cover for title: {title}")
            return cover

    return None


async def batch_fetch_covers(
    items: list[dict],
) -> dict[int, Optional[str]]:
    results = {}

    for item in items:
        item_id = item.get("id")
        if item_id is None:
            continue

        cover_url = await get_cover_url(
            isbn=item.get("isbn"),
            title=item.get("title"),
            author=item.get("author"),
        )
        results[item_id] = cover_url

    return results


# =============================================================================
# MUSIC COVER FUNCTIONS (CDs, Vinyl)
# =============================================================================


async def fetch_itunes_music_cover(
    artist: Optional[str] = None,
    album: Optional[str] = None,
) -> Optional[str]:
    if not album:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Build search query
            query = album
            if artist:
                query = f"{artist} {album}"

            params = {
                "term": query,
                "media": "music",
                "entity": "album",
                "limit": 3,
            }

            response = await client.get(ITUNES_SEARCH_API, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                # Get the artwork URL and upgrade to high resolution
                artwork_url = results[0].get("artworkUrl100")
                if artwork_url:
                    # Replace 100x100 with 600x600 for higher resolution
                    return artwork_url.replace("100x100bb", "600x600bb")

    except httpx.TimeoutException:
        logger.debug(f"Timeout fetching iTunes music cover for {album}")
    except httpx.RequestError as e:
        logger.debug(f"Error fetching iTunes music cover: {e}")
    except (KeyError, ValueError, IndexError) as e:
        logger.debug(f"Could not parse iTunes music data: {e}")

    return None


async def fetch_musicbrainz_cover(
    artist: Optional[str] = None,
    album: Optional[str] = None,
) -> Optional[str]:
    if not album:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # First, search MusicBrainz for the release
            query = f'release:"{album}"'
            if artist:
                query += f' AND artist:"{artist}"'

            params = {
                "query": query,
                "fmt": "json",
                "limit": 1,
            }
            headers = {
                "User-Agent": settings.library_user_agent,
            }

            response = await client.get(
                MUSICBRAINZ_SEARCH_API, params=params, headers=headers
            )
            response.raise_for_status()
            data = response.json()

            releases = data.get("releases", [])
            if releases:
                release_id = releases[0].get("id")
                if release_id:
                    # Try to get cover from Cover Art Archive
                    cover_response = await client.get(
                        f"{COVERART_ARCHIVE_API}/{release_id}/front",
                        follow_redirects=True,
                        headers=headers,
                    )
                    if cover_response.status_code == 200:
                        # Return the final URL after redirects
                        return str(cover_response.url)

    except httpx.TimeoutException:
        logger.debug(f"Timeout fetching MusicBrainz cover for {album}")
    except httpx.RequestError as e:
        logger.debug(f"Error fetching MusicBrainz cover: {e}")
    except (KeyError, ValueError, IndexError) as e:
        logger.debug(f"Could not parse MusicBrainz data: {e}")

    return None


async def get_music_cover_url(
    artist: Optional[str] = None,
    album: Optional[str] = None,
) -> Optional[str]:
    # Try iTunes first (fastest)
    cover = await fetch_itunes_music_cover(artist=artist, album=album)
    if cover:
        logger.debug(f"Found iTunes music cover for: {album}")
        return cover

    # Try MusicBrainz as fallback
    cover = await fetch_musicbrainz_cover(artist=artist, album=album)
    if cover:
        logger.debug(f"Found MusicBrainz cover for: {album}")
        return cover

    return None


# =============================================================================
# MOVIE/DVD COVER FUNCTIONS
# =============================================================================


async def fetch_itunes_movie_cover(
    title: Optional[str] = None,
    director: Optional[str] = None,
    year: Optional[int] = None,
) -> Optional[str]:
    if not title:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            query = title
            if year:
                query = f"{title} {year}"

            params = {
                "term": query,
                "media": "movie",
                "entity": "movie",
                "limit": 5,
            }

            response = await client.get(ITUNES_SEARCH_API, params=params)
            response.raise_for_status()
            data = response.json()

            results = data.get("results", [])
            if results:
                # Try to match by year if provided
                for result in results:
                    release_date = result.get("releaseDate", "")
                    if year and release_date:
                        result_year = release_date[:4]
                        if str(year) == result_year:
                            artwork_url = result.get("artworkUrl100")
                            if artwork_url:
                                return artwork_url.replace("100x100bb", "600x600bb")

                # Fallback to first result
                artwork_url = results[0].get("artworkUrl100")
                if artwork_url:
                    return artwork_url.replace("100x100bb", "600x600bb")

    except httpx.TimeoutException:
        logger.debug(f"Timeout fetching iTunes movie cover for {title}")
    except httpx.RequestError as e:
        logger.debug(f"Error fetching iTunes movie cover: {e}")
    except (KeyError, ValueError, IndexError) as e:
        logger.debug(f"Could not parse iTunes movie data: {e}")

    return None


async def fetch_omdb_cover(
    title: Optional[str] = None,
    year: Optional[int] = None,
    api_key: Optional[str] = None,
) -> Optional[str]:
    if not title or not api_key:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            params = {
                "t": title,
                "apikey": api_key,
            }
            if year:
                params["y"] = str(year)

            response = await client.get(OMDB_API, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get("Response") == "True":
                poster = data.get("Poster")
                if poster and poster != "N/A":
                    return poster

    except httpx.TimeoutException:
        logger.debug(f"Timeout fetching OMDb cover for {title}")
    except httpx.RequestError as e:
        logger.debug(f"Error fetching OMDb cover: {e}")
    except (KeyError, ValueError) as e:
        logger.debug(f"Could not parse OMDb data: {e}")

    return None


async def get_movie_cover_url(
    title: Optional[str] = None,
    director: Optional[str] = None,
    year: Optional[int] = None,
    omdb_api_key: Optional[str] = None,
) -> Optional[str]:
    # Try iTunes first (no API key required)
    cover = await fetch_itunes_movie_cover(title=title, director=director, year=year)
    if cover:
        logger.debug(f"Found iTunes movie cover for: {title}")
        return cover

    # Try OMDb if API key is provided
    if omdb_api_key:
        cover = await fetch_omdb_cover(title=title, year=year, api_key=omdb_api_key)
        if cover:
            logger.debug(f"Found OMDb cover for: {title}")
            return cover

    return None


# =============================================================================
# UNIFIED COVER LOOKUP FOR ALL MEDIA TYPES
# =============================================================================


async def get_multimedia_cover_url(
    media_type: MediaType,
    title: Optional[str] = None,
    # Book-specific
    isbn: Optional[str] = None,
    author: Optional[str] = None,
    # Music-specific
    artist: Optional[str] = None,
    album: Optional[str] = None,
    # Movie-specific
    director: Optional[str] = None,
    year: Optional[int] = None,
    # API keys (optional)
    omdb_api_key: Optional[str] = None,
) -> Optional[str]:
    if media_type == MediaType.book:
        return await get_cover_url(isbn=isbn, title=title, author=author)

    elif media_type == MediaType.music:
        return await get_music_cover_url(artist=artist, album=album or title)

    elif media_type == MediaType.movie:
        return await get_movie_cover_url(
            title=title,
            director=director,
            year=year,
            omdb_api_key=omdb_api_key,
        )

    elif media_type == MediaType.game:
        # Games would require RAWG or IGDB API key
        # For now, return None - can be extended later
        logger.debug(f"Game cover lookup not yet implemented for: {title}")
        return None

    return None
