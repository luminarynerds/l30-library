# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Acquisition - External Catalog Search API Endpoints

Provides endpoints for:
- Searching Open Library
- Searching Google Books
- ISBN lookup (single and bulk)
- Catalog existence checking
- Previous order checking
- Price estimation
"""
import asyncio
from app.core.logging import get_logger
import re
from decimal import Decimal

import httpx
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.acquisition import PurchaseOrderItem, SelectionSource
from ....models.catalog import CatalogItem
from ....models.user import User, UserRole
from ....schemas.acquisition import ExternalSearchResponse, ExternalSearchResult
from ..auth import get_current_user
from ..dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/acquisition", tags=["acquisition-external"])


# ============ Pydantic Models for ISBN Lookup ============


class ISBNLookupResult(BaseModel):
    isbn: str
    isbn_10: str | None = None
    isbn_13: str | None = None
    title: str
    author: str | None = None
    cover_url: str | None = None
    publisher: str | None = None
    publication_year: int | None = None
    description: str | None = None
    page_count: int | None = None
    subjects: list[str] = []
    estimated_price: Decimal | None = None
    source: str
    source_id: str
    # Catalog status
    in_catalog: bool = False
    catalog_item_id: int | None = None
    previously_ordered: bool = False
    previous_po_numbers: list[str] = []


class ISBNLookupResponse(BaseModel):
    success: bool
    result: ISBNLookupResult | None = None
    error: str | None = None


class BulkISBNRequest(BaseModel):
    isbns: list[str] = Field(..., min_length=1, max_length=100)


class BulkISBNResult(BaseModel):
    isbn: str
    success: bool
    result: ISBNLookupResult | None = None
    error: str | None = None


class BulkISBNResponse(BaseModel):
    total: int
    successful: int
    failed: int
    results: list[BulkISBNResult]


class RecentSearch(BaseModel):
    query: str
    timestamp: str
    result_count: int


# ============ ISBN Validation Helpers ============


def normalize_isbn(isbn: str) -> str:
    return re.sub(r'[-\s]', '', isbn.strip())


def is_valid_isbn_10(isbn: str) -> bool:
    isbn = normalize_isbn(isbn)
    if len(isbn) != 10:
        return False
    if not isbn[:-1].isdigit():
        return False
    if not (isbn[-1].isdigit() or isbn[-1].upper() == 'X'):
        return False

    # Calculate checksum
    total = 0
    for i, char in enumerate(isbn[:-1]):
        total += int(char) * (10 - i)
    check = isbn[-1].upper()
    check_val = 10 if check == 'X' else int(check)
    return (total + check_val) % 11 == 0


def is_valid_isbn_13(isbn: str) -> bool:
    isbn = normalize_isbn(isbn)
    if len(isbn) != 13:
        return False
    if not isbn.isdigit():
        return False
    if not (isbn.startswith('978') or isbn.startswith('979')):
        return False

    # Calculate checksum
    total = sum(
        int(digit) * (1 if i % 2 == 0 else 3)
        for i, digit in enumerate(isbn[:-1])
    )
    check_digit = (10 - (total % 10)) % 10
    return int(isbn[-1]) == check_digit


def is_valid_isbn(isbn: str) -> bool:
    isbn = normalize_isbn(isbn)
    return is_valid_isbn_10(isbn) or is_valid_isbn_13(isbn)


def isbn_10_to_13(isbn_10: str) -> str | None:
    isbn_10 = normalize_isbn(isbn_10)
    if not is_valid_isbn_10(isbn_10):
        return None

    # Remove check digit and prepend 978
    isbn_12 = '978' + isbn_10[:-1]

    # Calculate new check digit
    total = sum(
        int(digit) * (1 if i % 2 == 0 else 3)
        for i, digit in enumerate(isbn_12)
    )
    check_digit = (10 - (total % 10)) % 10
    return isbn_12 + str(check_digit)


def isbn_13_to_10(isbn_13: str) -> str | None:
    isbn_13 = normalize_isbn(isbn_13)
    if not is_valid_isbn_13(isbn_13) or not isbn_13.startswith('978'):
        return None

    # Remove 978 prefix and check digit
    isbn_9 = isbn_13[3:-1]

    # Calculate new check digit
    total = sum(int(digit) * (10 - i) for i, digit in enumerate(isbn_9))
    check = (11 - (total % 11)) % 11
    check_char = 'X' if check == 10 else str(check)
    return isbn_9 + check_char



@router.get("/external-search", response_model=ExternalSearchResponse)
async def search_external_catalogs(
    q: str = Query(..., min_length=2),
    source: SelectionSource = Query(SelectionSource.OPEN_LIBRARY),
    current_user: User = Depends(get_current_user),
):
    """Search external catalogs (Open Library, Google Books)"""
    await require_staff(current_user)

    results = []

    if source == SelectionSource.OPEN_LIBRARY:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://openlibrary.org/search.json",
                    params={"q": q, "limit": 20},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    for doc in data.get("docs", [])[:20]:
                        results.append(
                            ExternalSearchResult(
                                source=SelectionSource.OPEN_LIBRARY,
                                source_id=doc.get("key", ""),
                                title=doc.get("title", "Unknown"),
                                author=", ".join(doc.get("author_name", [])[:3]),
                                isbn=(
                                    doc.get("isbn", [None])[0]
                                    if doc.get("isbn")
                                    else None
                                ),
                                cover_url=(
                                    f"https://covers.openlibrary.org/b/id/{doc.get('cover_i')}-M.jpg"
                                    if doc.get("cover_i")
                                    else None
                                ),
                                publisher=(
                                    doc.get("publisher", [None])[0]
                                    if doc.get("publisher")
                                    else None
                                ),
                                publication_year=doc.get("first_publish_year"),
                            )
                        )
            except httpx.TimeoutException:
                logger.warning(f"Open Library API timeout for query: {q}")
            except httpx.RequestError as e:
                logger.warning(f"Open Library API request error: {e}")
            except Exception as e:  # noqa: BLE001  # defensive catch-all after httpx-specific handlers — log and continue
                logger.error(f"Unexpected error searching Open Library: {e}")

    elif source == SelectionSource.GOOGLE_BOOKS:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    "https://www.googleapis.com/books/v1/volumes",
                    params={"q": q, "maxResults": 20},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get("items", [])[:20]:
                        vol = item.get("volumeInfo", {})
                        isbn = None
                        for ident in vol.get("industryIdentifiers", []):
                            if ident.get("type") == "ISBN_13":
                                isbn = ident.get("identifier")
                                break

                        results.append(
                            ExternalSearchResult(
                                source=SelectionSource.GOOGLE_BOOKS,
                                source_id=item.get("id", ""),
                                title=vol.get("title", "Unknown"),
                                author=", ".join(vol.get("authors", [])[:3]),
                                isbn=isbn,
                                cover_url=vol.get("imageLinks", {}).get("thumbnail"),
                                publisher=vol.get("publisher"),
                                publication_year=(
                                    int(vol.get("publishedDate", "0")[:4])
                                    if vol.get("publishedDate")
                                    else None
                                ),
                                description=(
                                    vol.get("description", "")[:500]
                                    if vol.get("description")
                                    else None
                                ),
                            )
                        )
            except httpx.TimeoutException:
                logger.warning(f"Google Books API timeout for query: {q}")
            except httpx.RequestError as e:
                logger.warning(f"Google Books API request error: {e}")
            except Exception as e:  # noqa: BLE001  # defensive catch-all after httpx-specific handlers — log and continue
                logger.error(f"Unexpected error searching Google Books: {e}")

    return ExternalSearchResponse(
        query=q,
        total_results=len(results),
        results=results,
    )


# ============ ISBN Lookup Helper Functions ============


async def lookup_isbn_open_library(isbn: str) -> dict | None:
    normalized = normalize_isbn(isbn)

    async with httpx.AsyncClient() as client:
        try:
            # Try the ISBN API first
            response = await client.get(
                f"https://openlibrary.org/isbn/{normalized}.json",
                timeout=10.0,
                follow_redirects=True,
            )

            if response.status_code == 200:
                data = response.json()

                # Get author info if available
                author = None
                if data.get("authors"):
                    author_key = data["authors"][0].get("key")
                    if author_key:
                        author_resp = await client.get(
                            f"https://openlibrary.org{author_key}.json",
                            timeout=5.0,
                        )
                        if author_resp.status_code == 200:
                            author_data = author_resp.json()
                            author = author_data.get("name")

                # Get cover URL
                cover_url = None
                if data.get("covers"):
                    cover_id = data["covers"][0]
                    cover_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

                # Extract ISBN-10 and ISBN-13
                isbn_10 = None
                isbn_13 = None
                if data.get("isbn_10"):
                    isbn_10 = data["isbn_10"][0]
                if data.get("isbn_13"):
                    isbn_13 = data["isbn_13"][0]

                # If we only have one, compute the other
                if isbn_10 and not isbn_13:
                    isbn_13 = isbn_10_to_13(isbn_10)
                elif isbn_13 and not isbn_10:
                    isbn_10 = isbn_13_to_10(isbn_13)

                # Extract publication year
                pub_year = None
                if data.get("publish_date"):
                    # Try to extract year from various formats
                    date_str = data["publish_date"]
                    year_match = re.search(r'\d{4}', date_str)
                    if year_match:
                        pub_year = int(year_match.group())

                # Get subjects
                subjects = []
                if data.get("subjects"):
                    subjects = data["subjects"][:5]  # Limit to first 5

                return {
                    "title": data.get("title", "Unknown"),
                    "author": author,
                    "cover_url": cover_url,
                    "publisher": (
                        data.get("publishers", [None])[0]
                        if data.get("publishers")
                        else None
                    ),
                    "publication_year": pub_year,
                    "description": (
                        data.get("description", {}).get("value")
                        if isinstance(data.get("description"), dict)
                        else data.get("description")
                    ),
                    "page_count": data.get("number_of_pages"),
                    "subjects": subjects,
                    "isbn_10": isbn_10,
                    "isbn_13": isbn_13,
                    "source": "open_library",
                    "source_id": data.get("key", ""),
                }

        except httpx.TimeoutException:
            logger.warning(f"Open Library API timeout for ISBN: {isbn}")
        except httpx.RequestError as e:
            logger.warning(f"Open Library API request error: {e}")
        except Exception as e:  # noqa: BLE001  # defensive catch-all after httpx-specific handlers — log and continue
            logger.error(f"Unexpected error searching Open Library by ISBN: {e}")

    return None


async def lookup_isbn_google_books(isbn: str) -> dict | None:
    normalized = normalize_isbn(isbn)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                "https://www.googleapis.com/books/v1/volumes",
                params={"q": f"isbn:{normalized}", "maxResults": 1},
                timeout=10.0,
            )

            if response.status_code == 200:
                data = response.json()
                items = data.get("items", [])

                if items:
                    item = items[0]
                    vol = item.get("volumeInfo", {})
                    sale_info = item.get("saleInfo", {})

                    # Extract ISBNs
                    isbn_10 = None
                    isbn_13 = None
                    for ident in vol.get("industryIdentifiers", []):
                        if ident.get("type") == "ISBN_10":
                            isbn_10 = ident.get("identifier")
                        elif ident.get("type") == "ISBN_13":
                            isbn_13 = ident.get("identifier")

                    # If we only have one, compute the other
                    if isbn_10 and not isbn_13:
                        isbn_13 = isbn_10_to_13(isbn_10)
                    elif isbn_13 and not isbn_10:
                        isbn_10 = isbn_13_to_10(isbn_13)

                    # Extract price if available
                    estimated_price = None
                    if sale_info.get("listPrice"):
                        price_amount = sale_info["listPrice"].get("amount")
                        if price_amount:
                            estimated_price = Decimal(str(price_amount))
                    elif sale_info.get("retailPrice"):
                        price_amount = sale_info["retailPrice"].get("amount")
                        if price_amount:
                            estimated_price = Decimal(str(price_amount))

                    # Get cover URL (prefer higher resolution)
                    cover_url = None
                    image_links = vol.get("imageLinks", {})
                    cover_url = (
                        image_links.get("thumbnail")
                        or image_links.get("smallThumbnail")
                    )
                    # Clean up the URL (Google often returns http)
                    if cover_url and cover_url.startswith("http:"):
                        cover_url = cover_url.replace("http:", "https:")

                    # Extract publication year
                    pub_year = None
                    if vol.get("publishedDate"):
                        date_str = vol["publishedDate"]
                        year_match = re.search(r'\d{4}', date_str)
                        if year_match:
                            pub_year = int(year_match.group())

                    return {
                        "title": vol.get("title", "Unknown"),
                        "author": ", ".join(vol.get("authors", [])[:3]),
                        "cover_url": cover_url,
                        "publisher": vol.get("publisher"),
                        "publication_year": pub_year,
                        "description": (
                            vol.get("description", "")[:500]
                            if vol.get("description")
                            else None
                        ),
                        "page_count": vol.get("pageCount"),
                        "subjects": vol.get("categories", [])[:5],
                        "isbn_10": isbn_10,
                        "isbn_13": isbn_13,
                        "estimated_price": estimated_price,
                        "source": "google_books",
                        "source_id": item.get("id", ""),
                    }

        except httpx.TimeoutException:
            logger.warning(f"Google Books API timeout for ISBN: {isbn}")
        except httpx.RequestError as e:
            logger.warning(f"Google Books API request error: {e}")
        except Exception as e:  # noqa: BLE001  # defensive catch-all after httpx-specific handlers — log and continue
            logger.error(f"Unexpected error searching Google Books by ISBN: {e}")

    return None


async def check_catalog_existence(
    db: AsyncSession, isbn: str
) -> tuple[bool, int | None]:
    normalized = normalize_isbn(isbn)

    # Try both ISBN-10 and ISBN-13 forms
    isbns_to_check = [normalized]
    if len(normalized) == 10:
        isbn_13 = isbn_10_to_13(normalized)
        if isbn_13:
            isbns_to_check.append(isbn_13)
    elif len(normalized) == 13:
        isbn_10 = isbn_13_to_10(normalized)
        if isbn_10:
            isbns_to_check.append(isbn_10)

    # Normalize stored ISBN on the DB side: production stores ISBNs
    # either hyphenated (e.g. "978-0-13-110412-9") or unhyphenated.
    # isbns_to_check is already hyphen/space-stripped via normalize_isbn,
    # so we strip the same characters from CatalogItem.isbn for the compare.
    normalized_db_isbn = func.replace(
        func.replace(CatalogItem.isbn, "-", ""), " ", ""
    )
    result = await db.execute(
        select(CatalogItem.id).where(normalized_db_isbn.in_(isbns_to_check)).limit(1)
    )
    catalog_item = result.scalar_one_or_none()

    return (catalog_item is not None, catalog_item)


async def check_previous_orders(
    db: AsyncSession, isbn: str
) -> tuple[bool, list[str]]:
    normalized = normalize_isbn(isbn)

    # Try both ISBN-10 and ISBN-13 forms
    isbns_to_check = [normalized]
    if len(normalized) == 10:
        isbn_13 = isbn_10_to_13(normalized)
        if isbn_13:
            isbns_to_check.append(isbn_13)
    elif len(normalized) == 13:
        isbn_10 = isbn_13_to_10(normalized)
        if isbn_10:
            isbns_to_check.append(isbn_10)

    # Import here to avoid circular import
    from ....models.acquisition import PurchaseOrder

    # Normalize stored ISBN on the DB side (see check_catalog_existence
    # for rationale). PurchaseOrderItem.isbn is staff-entered and may
    # also be hyphenated.
    normalized_po_isbn = func.replace(
        func.replace(PurchaseOrderItem.isbn, "-", ""), " ", ""
    )
    result = await db.execute(
        select(PurchaseOrder.po_number)
        .join(PurchaseOrderItem)
        .where(normalized_po_isbn.in_(isbns_to_check))
        .distinct()
    )
    po_numbers = [row[0] for row in result.fetchall()]

    return (len(po_numbers) > 0, po_numbers)


async def lookup_single_isbn(
    isbn: str, db: AsyncSession | None = None
) -> ISBNLookupResult | None:
    normalized = normalize_isbn(isbn)

    if not is_valid_isbn(normalized):
        return None

    # Try Open Library first, then Google Books
    result = await lookup_isbn_open_library(normalized)

    if not result:
        result = await lookup_isbn_google_books(normalized)

    if not result:
        return None

    # Check catalog existence and previous orders if db session provided
    in_catalog = False
    catalog_item_id = None
    previously_ordered = False
    previous_po_numbers = []

    if db:
        in_catalog, catalog_item_id = await check_catalog_existence(db, normalized)
        previously_ordered, previous_po_numbers = await check_previous_orders(
            db, normalized
        )

    return ISBNLookupResult(
        isbn=normalized,
        isbn_10=result.get("isbn_10"),
        isbn_13=result.get("isbn_13"),
        title=result["title"],
        author=result.get("author"),
        cover_url=result.get("cover_url"),
        publisher=result.get("publisher"),
        publication_year=result.get("publication_year"),
        description=result.get("description"),
        page_count=result.get("page_count"),
        subjects=result.get("subjects", []),
        estimated_price=result.get("estimated_price"),
        source=result["source"],
        source_id=result["source_id"],
        in_catalog=in_catalog,
        catalog_item_id=catalog_item_id,
        previously_ordered=previously_ordered,
        previous_po_numbers=previous_po_numbers,
    )


# ============ ISBN Lookup Endpoints ============


@router.get("/isbn-lookup/{isbn}", response_model=ISBNLookupResponse)
async def lookup_isbn(
    isbn: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Look up a single ISBN and return book details.

    - Validates ISBN-10 and ISBN-13 formats
    - Searches Open Library and Google Books
    - Checks if item exists in catalog
    - Checks if item was previously ordered
    - Returns price estimate if available
    """
    await require_staff(current_user)

    normalized = normalize_isbn(isbn)

    if not is_valid_isbn(normalized):
        return ISBNLookupResponse(
            success=False,
            error=f"Invalid ISBN format: {isbn}",
        )

    result = await lookup_single_isbn(normalized, db)

    if not result:
        return ISBNLookupResponse(
            success=False,
            error=f"ISBN not found: {isbn}",
        )

    return ISBNLookupResponse(success=True, result=result)


@router.post("/isbn-lookup/bulk", response_model=BulkISBNResponse)
async def bulk_lookup_isbns(
    request: BulkISBNRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Look up multiple ISBNs at once.

    - Accepts up to 100 ISBNs
    - Processes in parallel for speed
    - Returns results for all ISBNs (successful and failed)
    """
    await require_staff(current_user)

    results = []
    successful = 0
    failed = 0

    # Process ISBNs in batches of 10 to avoid overwhelming APIs
    batch_size = 10
    for i in range(0, len(request.isbns), batch_size):
        batch = request.isbns[i : i + batch_size]

        # Process batch in parallel
        tasks = []
        for isbn in batch:
            normalized = normalize_isbn(isbn)
            if is_valid_isbn(normalized):
                tasks.append((isbn, lookup_single_isbn(normalized, db)))
            else:
                results.append(
                    BulkISBNResult(
                        isbn=isbn,
                        success=False,
                        error="Invalid ISBN format",
                    )
                )
                failed += 1

        # Execute parallel lookups
        if tasks:
            lookup_results = await asyncio.gather(
                *[task[1] for task in tasks],
                return_exceptions=True,
            )

            for (isbn, _), result in zip(tasks, lookup_results):
                if isinstance(result, Exception):
                    results.append(
                        BulkISBNResult(
                            isbn=isbn,
                            success=False,
                            error=f"Lookup error: {str(result)}",
                        )
                    )
                    failed += 1
                elif result is None:
                    results.append(
                        BulkISBNResult(
                            isbn=isbn,
                            success=False,
                            error="ISBN not found",
                        )
                    )
                    failed += 1
                else:
                    results.append(
                        BulkISBNResult(
                            isbn=isbn,
                            success=True,
                            result=result,
                        )
                    )
                    successful += 1

        # Small delay between batches to be nice to external APIs
        if i + batch_size < len(request.isbns):
            await asyncio.sleep(0.1)

    return BulkISBNResponse(
        total=len(request.isbns),
        successful=successful,
        failed=failed,
        results=results,
    )


@router.get("/isbn-validate/{isbn}")
async def validate_isbn(
    isbn: str,
    current_user: User = Depends(get_current_user),
):
    """
    Validate an ISBN format without looking it up.

    Useful for barcode scanner input validation.
    """
    await require_staff(current_user)

    normalized = normalize_isbn(isbn)
    is_10 = is_valid_isbn_10(normalized)
    is_13 = is_valid_isbn_13(normalized)

    result = {
        "input": isbn,
        "normalized": normalized,
        "valid": is_10 or is_13,
        "format": None,
        "isbn_10": None,
        "isbn_13": None,
    }

    if is_10:
        result["format"] = "ISBN-10"
        result["isbn_10"] = normalized
        result["isbn_13"] = isbn_10_to_13(normalized)
    elif is_13:
        result["format"] = "ISBN-13"
        result["isbn_13"] = normalized
        result["isbn_10"] = isbn_13_to_10(normalized)

    return result


@router.get("/check-catalog/{isbn}")
async def check_isbn_in_catalog(
    isbn: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if an ISBN exists in the library catalog.
    """
    await require_staff(current_user)

    normalized = normalize_isbn(isbn)
    in_catalog, catalog_item_id = await check_catalog_existence(db, normalized)
    previously_ordered, po_numbers = await check_previous_orders(db, normalized)

    return {
        "isbn": normalized,
        "in_catalog": in_catalog,
        "catalog_item_id": catalog_item_id,
        "previously_ordered": previously_ordered,
        "previous_po_numbers": po_numbers,
    }


@router.get("/isbn-lookup/bulk")
async def get_isbn_lookup_bulk_status(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get status of /isbn-lookup/bulk operation."""
    return {"status": "pending", "processed": 0, "total": 0}

