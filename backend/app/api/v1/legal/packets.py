# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
API endpoints for legal form packet management.

This module handles form packets (bundles of related forms for common needs)
including listing, viewing, and CRUD operations.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ....core.database import get_db
from ....models.user import User
from ....schemas.legal import (
    LegalFormPacketCreate, LegalFormPacketUpdate, LegalFormPacketResponse,
    LegalFormPacketSummaryResponse, LegalFormPacketListResponse,
    LegalFormPacketItemCreate,
)
from ....services import legal_service
from ....services.pdf_packet import generate_packet_cover_pdf
from .dependencies import get_current_user, get_current_user_optional
from .helpers import paginated_response, require_resource

router = APIRouter(prefix="/legal", tags=["legal-forms"])


# ============================================================================
# Form Packets
# ============================================================================

@router.get("/packets", response_model=LegalFormPacketListResponse)
async def list_packets(
    topic_id: Optional[int] = Query(None),
    jurisdiction: Optional[str] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    List form packets (bundles of related forms for common needs).

    Packets include checklists, filing sequences, and total cost estimates.
    Examples: "Uncontested Divorce Packet", "Small Claims Plaintiff Packet"
    """
    packets, total = await legal_service.list_packets(
        db, topic_id=topic_id, jurisdiction=jurisdiction,
        skip=offset, limit=limit
    )
    return paginated_response(
        key="packets",
        items=packets,
        total=total,
        limit=limit,
        offset=offset,
        mapper=_packet_to_summary,
    )


@router.get("/packets/{packet_id}", response_model=LegalFormPacketResponse)
async def get_packet(
    packet_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get detailed packet information including all forms.

    Includes the complete checklist, filing sequence, instructions,
    and court information for filing.
    """
    packet = require_resource(
        await legal_service.get_packet_by_id(db, packet_id),
        message="Form packet not found",
    )
    return _packet_to_response(packet)


@router.get("/packets/slug/{slug}", response_model=LegalFormPacketResponse)
async def get_packet_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get a form packet by its URL slug."""
    packet = require_resource(
        await legal_service.get_packet_by_slug(db, slug),
        message="Form packet not found",
    )
    return _packet_to_response(packet)



@router.get("/packets/{packet_id}/pdf")
async def download_packet_pdf(
    packet_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Download a form packet as a PDF with cover sheet."""
    packet = require_resource(
        await legal_service.get_packet_by_id(db, packet_id),
        message="Form packet not found",
    )

    forms = []
    for item in sorted(packet.forms, key=lambda f: f.order):
        form = item.form
        if not form:
            continue
        forms.append({
            "title": form.title,
            "form_number": form.form_number,
            "description": form.description,
            "when_to_use": form.when_to_use,
            "form_url": form.form_url,
        })

    topic_name = packet.topic.name if packet.topic else packet.name
    pdf_bytes = generate_packet_cover_pdf(topic_name=topic_name, forms=forms)

    filename = f"{packet.slug or 'packet'}-forms.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/packets", response_model=LegalFormPacketResponse, status_code=status.HTTP_201_CREATED)
async def create_packet(
    packet_data: LegalFormPacketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new form packet. Requires staff access."""
    forms_data = [f.model_dump() for f in packet_data.forms]
    packet_dict = packet_data.model_dump(exclude={"forms"})
    packet = await legal_service.create_packet(
        db, packet_dict, forms_data, created_by_id=current_user.id
    )
    return _packet_to_response(packet)


# ============================================================================
# Helper Functions
# ============================================================================

def _packet_to_summary(packet) -> dict:
    return {
        "id": packet.id,
        "name": packet.name,
        "slug": packet.slug,
        "description": packet.description,
        "jurisdiction": packet.jurisdiction,
        "total_filing_fee": packet.total_filing_fee,
        "form_count": len(packet.forms) if packet.forms else 0,
        "is_active": packet.is_active,
        "topic_name": packet.topic.name if packet.topic else None
    }


def _packet_to_response(packet) -> dict:
    return {
        "id": packet.id,
        "name": packet.name,
        "slug": packet.slug,
        "topic_id": packet.topic_id,
        "description": packet.description,
        "use_case": packet.use_case,
        "who_should_use": packet.who_should_use,
        "checklist": packet.checklist or [],
        "filing_sequence": packet.filing_sequence or [],
        "total_filing_fee": packet.total_filing_fee,
        "estimated_total_time": packet.estimated_total_time,
        "timeline_description": packet.timeline_description,
        "cost_breakdown": packet.cost_breakdown or [],
        "instructions": packet.instructions,
        "related_guide_ids": packet.related_guide_ids or [],
        "jurisdiction": packet.jurisdiction,
        "court_addresses": packet.court_addresses or [],
        "is_active": packet.is_active,
        "download_count": packet.download_count,
        "view_count": packet.view_count,
        "created_at": getattr(packet, "created_at", None),
        "updated_at": getattr(packet, "updated_at", None),
        "created_by_id": packet.created_by_id,
        "forms": [_packet_item_to_response(f) for f in packet.forms],
        "topic_name": packet.topic.name if packet.topic else None
    }


def _packet_item_to_response(item) -> dict:
    return {
        "id": item.id,
        "packet_id": item.packet_id,
        "form_id": item.form_id,
        "order": item.order,
        "instructions": item.instructions,
        "is_required": item.is_required,
        "conditional_notes": item.conditional_notes,
        "form_title": item.form.title if item.form else None,
        "form_number": item.form.form_number if item.form else None
    }
