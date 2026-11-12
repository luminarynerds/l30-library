# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Library Pitch PDF Endpoint

Serves the 1-page indie vault pitch PDF for librarian meetings.
"""

from fastapi import APIRouter
from fastapi.responses import Response

from ...services.library_pitch_pdf import generate_library_pitch_pdf

router = APIRouter(prefix="/library-pitch", tags=["library-pitch"])


@router.get("/pdf", response_class=Response)
async def get_pitch_pdf():
    """
    Download the L30 Indie Vault 1-page pitch PDF.

    Returns:
        bytes: PDF content with Content-Disposition header set to inline
    """
    pdf_bytes = await generate_library_pitch_pdf()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": "inline; filename=l30-indie-vault-overview.pdf",
            "Cache-Control": "public, max-age=3600",
        },
    )
