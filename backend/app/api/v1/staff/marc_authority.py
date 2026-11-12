# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Staff MARC Authority Review

Lets cataloging staff review indie author authority records from MetisLib,
accept/reject heading changes before overlaying the local ILS, and flag
corrections when an authority record has errors.

Workflow:
  1. Staff browses authors with pending heading changes
  2. Staff reviews the authority record (100 heading, 400 variants, 667 notes)
  3. Staff accepts overlay (updates local catalog) or rejects (keeps old heading)
  4. If errors found, staff submits a correction request back to the author
"""
from app.core.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..dependencies import require_staff
from app.services.metislib_client import get_metislib_client
from app.services.metislib_errors import (
    MetisLibError, MetisLibNotFound, MetisLibUnavailable, MetisLibValidationError,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/staff/marc-authority", tags=["staff-marc-authority"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class OverlayDecisionRequest(BaseModel):
    change_id: int
    decision: str  # "accepted" or "rejected"
    notes: str | None = None


class CorrectionRequest(BaseModel):
    field_tag: str
    current_value: str | None = None
    suggested_value: str | None = None
    reason: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/authors/{author_id}")
async def get_authority_record(
    author_id: int,
    staff_user=Depends(require_staff),
):
    """Get the full MARC Authority record for an indie author.

    Returns the authority fields, heading change history, and whether
    there are breaking changes that need review before overlay.
    """
    client = get_metislib_client()
    try:
        data = await client.get_authority(author_id)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Author not found in MetisLib") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="MetisLib is currently unavailable") from None

    return data


@router.get("/authors/{author_id}/export")
async def export_authority_xml(
    author_id: int,
    include_bibs: bool = Query(False, description="Include all bib records in the export"),
    staff_user=Depends(require_staff),
):
    """Export MARCXML for import into the local ILS.

    With include_bibs=true, exports a single file containing the authority
    record followed by all bibliographic records for the author's ebooks.
    """
    from fastapi.responses import Response
    client = get_metislib_client()
    try:
        if include_bibs:
            xml_bytes = await client.get_authority_with_bibs_xml(author_id)
            filename = f"author_{author_id}_complete.xml"
        else:
            xml_bytes = await client.get_authority_xml(author_id)
            filename = f"authority_{author_id}.xml"
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Author not found in MetisLib") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="MetisLib is currently unavailable") from None

    return Response(
        content=xml_bytes,
        media_type="application/xml",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/authors/{author_id}/overlay-decision")
async def submit_overlay_decision(
    author_id: int,
    body: OverlayDecisionRequest,
    staff_user=Depends(require_staff),
):
    """Accept or reject a breaking heading change.

    **accepted** — The updated authority record can be imported into the ILS.
    All linked bib records (including print) will be updated by ILS authority control.

    **rejected** — The library keeps its current local heading. The MetisLib
    authority record diverges until manually reconciled.
    """
    if body.decision not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Decision must be 'accepted' or 'rejected'")

    client = get_metislib_client()
    try:
        result = await client.submit_overlay_decision(
            author_id, body.change_id, body.decision, body.notes,
        )
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Author or heading change not found") from None
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="MetisLib is currently unavailable") from None

    logger.info(
        "Authority overlay decision: author=%d change=%d decision=%s by=%s",
        author_id, body.change_id, body.decision, staff_user.email,
    )
    return result


@router.get("/authors/{author_id}/overlay-history")
async def get_overlay_history(
    author_id: int,
    staff_user=Depends(require_staff),
):
    """View all overlay decisions this library has made for an author."""
    client = get_metislib_client()
    try:
        return await client.get_overlay_history(author_id)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Author not found in MetisLib") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="MetisLib is currently unavailable") from None


@router.post("/authors/{author_id}/corrections")
async def submit_correction(
    author_id: int,
    body: CorrectionRequest,
    staff_user=Depends(require_staff),
):
    """Flag an issue on an authority record.

    The correction is sent to MetisLib and the author is notified.
    Valid field_tags: 100 (heading), 400 (variants), 046 (dates),
    024 (OAID), 377 (language), 670 (sources), 678 (bio).
    """
    client = get_metislib_client()
    try:
        result = await client.submit_correction(
            author_id, body.field_tag, body.reason,
            body.current_value, body.suggested_value,
        )
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Author not found in MetisLib") from None
    except MetisLibValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="MetisLib is currently unavailable") from None

    logger.info(
        "Authority correction submitted: author=%d field=%s by=%s",
        author_id, body.field_tag, staff_user.email,
    )
    return result


@router.get("/authors/{author_id}/corrections")
async def list_corrections(
    author_id: int,
    staff_user=Depends(require_staff),
):
    """View correction requests this library has filed on an author."""
    client = get_metislib_client()
    try:
        return await client.list_corrections(author_id)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Author not found in MetisLib") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="MetisLib is currently unavailable") from None


@router.get("/authors/{author_id}/marc-bib/{ebook_id}")
async def get_marc_bib(
    author_id: int,
    ebook_id: int,
    staff_user=Depends(require_staff),
):
    """Get MARC bibliographic record for a specific ebook."""
    client = get_metislib_client()
    try:
        return await client.get_marc_bib(ebook_id)
    except MetisLibNotFound:
        raise HTTPException(status_code=404, detail="Ebook not found in MetisLib") from None
    except MetisLibUnavailable:
        raise HTTPException(status_code=503, detail="MetisLib is currently unavailable") from None
