# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Z39.50 Copy Cataloging API endpoints
"""
from app.core.logging import get_logger

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.user import User
from ...services.z3950_service import z3950_service
from .dependencies import require_staff

router = APIRouter(prefix="/cataloging/z3950", tags=["cataloging", "z3950"])
logger = get_logger(__name__)


@router.post("/search")
async def search_z3950(
    isbn: str | None = Query(None, description="ISBN to search for"),
    title: str | None = Query(None, description="Title to search for"),
    author: str | None = Query(None, description="Author to search for"),
    source: str = Query("loc", description="Z39.50 source: 'loc' or 'oclc'"),
    max_results: int = Query(10, ge=1, le=50, description="Maximum results"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Search Z39.50 sources for MARC records (copy cataloging).

    Staff-only endpoint for retrieving bibliographic records from external sources.

    Supported sources:
    - loc: Library of Congress
    - oclc: OCLC WorldCat (requires authentication)

    At least one search criterion (ISBN, title, or author) must be provided.
    """
    if not z3950_service.available:
        raise HTTPException(
            status_code=503,
            detail="Z39.50 service unavailable. PyZ3950 library not installed.",
        )

    if not isbn and not title and not author:
        raise HTTPException(
            status_code=400,
            detail="At least one search criterion (isbn, title, or author) must be provided",
        )

    if source not in ["loc", "oclc"]:
        raise HTTPException(
            status_code=400, detail="Invalid source. Use 'loc' or 'oclc'"
        )

    try:
        # Prefer ISBN search (most specific)
        if isbn:
            results = await z3950_service.search_by_isbn(
                isbn, source=source, max_results=max_results
            )
        else:
            results = await z3950_service.search_combined(
                isbn=isbn,
                title=title,
                author=author,
                source=source,
                max_results=max_results,
            )

        # Remove raw MARC data from response (too large)
        for result in results:
            result.pop("raw_marc", None)

        hint = None
        if len(results) == 0:
            if isbn and not title:
                hint = "No results for this ISBN. Try searching by title instead."
            elif title and not isbn:
                hint = "No results for this title. Try searching by ISBN if available."

        return {
            "ok": True,
            "source": source,
            "query": {"isbn": isbn, "title": title, "author": author},
            "count": len(results),
            "results": results,
            **({"hint": hint} if hint else {}),
        }

    except Exception as e:
        logger.error(f"Z39.50 search error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Z39.50 search failed",
        ) from e


@router.post("/import-to-bibframe")
async def import_z3950_to_bibframe(
    control_number: str = Query(..., description="MARC control number to import"),
    source: str = Query("loc", description="Z39.50 source: 'loc' or 'oclc'"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Import a Z39.50 MARC record and auto-convert to BIBFRAME entities.

    Retrieves the full MARC record, converts to BIBFRAME Work/Instance/Item,
    and stores the entities in the database. Staff-only endpoint.
    """
    if not z3950_service.available:
        raise HTTPException(
            status_code=503,
            detail="Z39.50 service unavailable.",
        )

    if source not in ["loc", "oclc"]:
        raise HTTPException(status_code=400, detail="Invalid source. Use 'loc' or 'oclc'")

    try:
        record = await z3950_service.get_record_details(control_number, source=source)
        if not record:
            raise HTTPException(status_code=404, detail="Record not found")

        # Get the raw MARC record for BIBFRAME conversion
        from ...services.marc_to_bibframe_service import MarcToBibframeService

        marc_service = MarcToBibframeService()

        # The z3950_service returns parsed dict; we need the raw pymarc Record
        # Use search_combined to get the raw record via control number
        raw_results = await z3950_service.search_combined(
            isbn=record.get("isbn"),
            title=record.get("title"),
            source=source,
            max_results=1,
        )

        if not raw_results:
            raise HTTPException(status_code=404, detail="Could not retrieve MARC record for conversion")

        # Convert using the catalog item converter (from dict)
        conversion = marc_service.convert_catalog_item_from_dict(raw_results[0])

        # Save BIBFRAME entities
        work = conversion.get("work")
        instance = conversion.get("instance")
        contributors = conversion.get("contributors", [])
        subjects = conversion.get("subjects", [])
        authority_links = conversion.get("authority_links", [])

        if work:
            db.add(work)
            await db.flush()

            if instance:
                instance.work_id = work.id
                db.add(instance)

            for contributor in contributors:
                contributor.work_id = work.id
                db.add(contributor)

            for subject in subjects:
                subject.work_id = work.id
                db.add(subject)

            for link in authority_links:
                if hasattr(link, "work_id"):
                    link.work_id = work.id
                db.add(link)

            await db.commit()

            logger.info(
                "Imported MARC record %s to BIBFRAME: work_id=%d",
                control_number, work.id,
            )

            return {
                "ok": True,
                "work_id": work.id,
                "instance_id": instance.id if instance else None,
                "contributors_count": len(contributors),
                "subjects_count": len(subjects),
                "authority_links_count": len(authority_links),
                "warnings": conversion.get("warnings", []),
                "source": source,
                "control_number": control_number,
            }

        return {
            "ok": False,
            "error": "BIBFRAME conversion produced no Work entity",
            "warnings": conversion.get("warnings", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("BIBFRAME import error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="BIBFRAME import failed") from e


@router.get("/sources")
async def get_z3950_sources(
    current_user: User = Depends(require_staff),
):
    """
    Get available Z39.50 sources and their configuration.

    Staff-only endpoint.
    """
    if not z3950_service.available:
        raise HTTPException(
            status_code=503,
            detail="Z39.50 service unavailable. PyZ3950 library not installed.",
        )

    from ...services.z3950_service import Z3950_SOURCES

    sources = []
    for key, config in Z3950_SOURCES.items():
        sources.append(
            {
                "id": key,
                "name": config["name"],
                "host": config["host"],
                "port": config["port"],
                "database": config["database"],
                "requires_auth": config.get("requires_auth", False),
                "available": not config.get("requires_auth", False),
            }
        )

    return {
        "ok": True,
        "available": z3950_service.available,
        "sources": sources,
    }


@router.get("/record/{control_number}")
async def get_z3950_record(
    control_number: str,
    source: str = Query("loc", description="Z39.50 source: 'loc' or 'oclc'"),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve full MARC record by control number.

    Staff-only endpoint for fetching complete record details.
    """
    if not z3950_service.available:
        raise HTTPException(
            status_code=503,
            detail="Z39.50 service unavailable. PyZ3950 library not installed.",
        )

    if source not in ["loc", "oclc"]:
        raise HTTPException(
            status_code=400, detail="Invalid source. Use 'loc' or 'oclc'"
        )

    try:
        result = await z3950_service.get_record_details(control_number, source=source)

        if not result:
            raise HTTPException(status_code=404, detail="Record not found")

        # Remove raw MARC data from response
        result.pop("raw_marc", None)

        return {
            "ok": True,
            "source": source,
            "control_number": control_number,
            "record": result,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Z39.50 record retrieval error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve record",
        ) from e
