# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Proxy patron request endpoints to MetisLib. Public — no auth required."""
from app.core.logging import get_logger
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, EmailStr
from typing import Optional

from ...services.metislib_client import get_metislib_client
from ...services.metislib_errors import (
    MetisLibError, MetisLibUnavailable, MetisLibNotFound, MetisLibValidationError
)

logger = get_logger(__name__)
router = APIRouter(prefix="/patron-requests", tags=["patron-requests"])


class LibrarySearchResult(BaseModel):
    id: int
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    is_connected: bool


class PatronRequestCreate(BaseModel):
    ebook_id: int
    library_directory_id: int
    patron_email: Optional[EmailStr] = None
    patron_name: Optional[str] = None
    source: str = "web"


class PatronRequestResponse(BaseModel):
    success: bool
    message: str
    library_name: str
    is_connected: bool


class LibraryDirectoryAdd(BaseModel):
    name: str
    city: Optional[str] = None
    state: Optional[str] = None
    contact_email: Optional[EmailStr] = None


@router.get("/libraries/search", response_model=list[LibrarySearchResult])
async def search_libraries(q: str = Query(min_length=2)):
    """Search libraries for autocomplete. Public — no auth."""
    client = get_metislib_client()
    try:
        response = await client._request("GET", "/requests/libraries/search", params={"q": q})
        return response
    except MetisLibError as e:
        logger.error(f"Library search failed: {e}")
        raise HTTPException(status_code=502, detail="Library search unavailable") from e


@router.post("/", response_model=PatronRequestResponse)
async def submit_patron_request(data: PatronRequestCreate):
    """Submit a book request at a library. Public — no auth."""
    client = get_metislib_client()
    try:
        response = await client._request("POST", "/requests/", json_body=data.model_dump())
        return response
    except MetisLibNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibError as e:
        logger.error(f"Request submission failed: {e}")
        raise HTTPException(status_code=502, detail="Request submission unavailable") from e


@router.get("/stats/{library_directory_id}")
async def get_request_stats(library_directory_id: int):
    """Get request stats for a library. Used by pitch page."""
    client = get_metislib_client()
    try:
        response = await client._request("GET", f"/requests/stats/{library_directory_id}")
        return response
    except MetisLibNotFound as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except MetisLibError as e:
        logger.error(f"Stats fetch failed: {e}")
        raise HTTPException(status_code=502, detail="Stats unavailable") from e


@router.post("/libraries/add")
async def add_library(data: LibraryDirectoryAdd):
    """Add a library to the directory. Public — no auth."""
    client = get_metislib_client()
    try:
        response = await client._request("POST", "/requests/libraries/add", json_body=data.model_dump())
        return response
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibError as e:
        logger.error(f"Library add failed: {e}")
        raise HTTPException(status_code=502, detail="Could not add library") from e
