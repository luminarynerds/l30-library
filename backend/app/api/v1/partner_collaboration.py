# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Partner Collaboration API Endpoints

Provides endpoints for:
- Shared event calendar management
- Resource sharing requests
- Co-sponsored program tracking
- Partner contact directory
- Partnership meetings
- MOUs and agreements
- Joint grant opportunities
- Impact reporting
- Partner recognition and appreciation
"""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from .dependencies import require_staff, require_admin, get_current_user
from ...models.user import User, UserRole
from ...schemas.partner_collaboration import (
    SharedEventCreate, SharedEventUpdate, SharedEventResponse,
    ResourceSharingRequestCreate, ResourceSharingRequestUpdate, ResourceSharingRequestResponse,
    CoSponsoredProgramCreate, CoSponsoredProgramResponse,
    ProgramSessionCreate,
    PartnerContactCreate, PartnerContactResponse,
    PartnershipMeetingCreate, PartnershipMeetingResponse,
    PartnershipAgreementCreate, PartnershipAgreementResponse,
    JointGrantOpportunityCreate, JointGrantOpportunityResponse,
    PartnerImpactReportCreate, PartnerImpactReportResponse,
    PartnerRecognitionCreate, PartnerRecognitionResponse,
    ThankYouMessageCreate, ThankYouMessageResponse,
)
from ...services.partner_collaboration_service import (
    SharedEventService,
    ResourceSharingService,
    CoSponsoredProgramService,
    ContactDirectoryService,
    PartnershipMeetingService,
    PartnershipAgreementService,
    JointGrantService,
    ImpactReportingService,
    PartnerRecognitionService,
)

router = APIRouter(prefix="/partner-collaboration", tags=["partner-collaboration"])


# ============================================================================
# Shared Event Calendar
# ============================================================================

@router.post("/events", response_model=SharedEventResponse, status_code=status.HTTP_201_CREATED)
async def create_shared_event(
    data: SharedEventCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new shared event on the partnership calendar."""
    event = await SharedEventService.create_event(
        db=db,
        created_by_id=current_user.id,
        **data.dict()
    )
    return event


@router.get("/events/partner/{partner_id}", response_model=List[SharedEventResponse])
async def get_partner_events(
    partner_id: int,
    status: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get shared events for a partner."""
    events = await SharedEventService.get_partner_events(
        db=db,
        partner_id=partner_id,
        status=status,
        start_date=start_date,
        end_date=end_date
    )
    return events


@router.put("/events/{event_id}", response_model=SharedEventResponse)
async def update_shared_event(
    event_id: int,
    data: SharedEventUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a shared event."""
    event = await SharedEventService.update_event(
        db=db,
        event_id=event_id,
        **data.dict(exclude_unset=True)
    )
    return event


# ============================================================================
# Resource Sharing Requests
# ============================================================================

@router.post("/resource-requests", response_model=ResourceSharingRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_resource_request(
    data: ResourceSharingRequestCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new resource sharing request."""
    request = await ResourceSharingService.create_request(
        db=db,
        requester_user_id=current_user.id,
        **data.dict()
    )
    return request


@router.get("/resource-requests/partner/{partner_id}", response_model=List[ResourceSharingRequestResponse])
async def get_partner_resource_requests(
    partner_id: int,
    role: str = Query("requester", description="requester or provider"),
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get resource requests for a partner."""
    requests = await ResourceSharingService.get_requests_by_partner(
        db=db,
        partner_id=partner_id,
        role=role,
        status=status
    )
    return requests


@router.put("/resource-requests/{request_id}", response_model=ResourceSharingRequestResponse)
async def update_resource_request(
    request_id: int,
    data: ResourceSharingRequestUpdate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Update a resource request."""
    try:
        request = await ResourceSharingService.update_request(
            db=db,
            request_id=request_id,
            **data.dict(exclude_unset=True)
        )
        return request
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Resource request {request_id} not found"
        ) from None


@router.post("/resource-requests/{request_id}/approve", response_model=ResourceSharingRequestResponse)
async def approve_resource_request(
    request_id: int,
    approval_notes: Optional[str] = Query(None),
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Approve a resource sharing request."""
    request = await ResourceSharingService.approve_request(
        db=db,
        request_id=request_id,
        approved_by_id=current_user.id,
        approval_notes=approval_notes
    )
    return request


# ============================================================================
# Co-Sponsored Programs
# ============================================================================

@router.post("/programs", response_model=CoSponsoredProgramResponse, status_code=status.HTTP_201_CREATED)
async def create_program(
    data: CoSponsoredProgramCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new co-sponsored program."""
    program = await CoSponsoredProgramService.create_program(
        db=db,
        created_by_id=current_user.id,
        **data.dict()
    )
    return program


@router.get("/programs/partner/{partner_id}", response_model=List[CoSponsoredProgramResponse])
async def get_partner_programs(
    partner_id: int,
    status: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get co-sponsored programs for a partner."""
    programs = await CoSponsoredProgramService.get_partner_programs(
        db=db,
        partner_id=partner_id,
        status=status
    )
    return programs


@router.post("/programs/{program_id}/sessions", status_code=status.HTTP_201_CREATED)
async def add_program_session(
    program_id: int,
    data: ProgramSessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a session to a program."""
    session = await CoSponsoredProgramService.add_session(
        db=db,
        program_id=program_id,
        **data.dict()
    )
    return session


# ============================================================================
# Partner Contact Directory
# ============================================================================

@router.post("/contacts", response_model=PartnerContactResponse, status_code=status.HTTP_201_CREATED)
async def add_partner_contact(
    partner_id: int,
    data: PartnerContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Add a new contact to partner directory."""
    contact = await ContactDirectoryService.add_contact(
        db=db,
        partner_id=partner_id,
        **data.dict()
    )
    return contact


@router.get("/contacts/partner/{partner_id}", response_model=List[PartnerContactResponse])
async def get_partner_contacts(
    partner_id: int,
    is_primary: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get contacts for a partner."""
    contacts = await ContactDirectoryService.get_partner_contacts(
        db=db,
        partner_id=partner_id,
        is_primary=is_primary
    )
    return contacts


@router.put("/contacts/{contact_id}", response_model=PartnerContactResponse)
async def update_partner_contact(
    contact_id: int,
    data: PartnerContactCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a partner contact."""
    contact = await ContactDirectoryService.update_contact(
        db=db,
        contact_id=contact_id,
        **data.dict(exclude_unset=True)
    )
    return contact


# ============================================================================
# Partnership Meetings
# ============================================================================

@router.post("/meetings", response_model=PartnershipMeetingResponse, status_code=status.HTTP_201_CREATED)
async def create_meeting(
    partner_id: int,
    data: PartnershipMeetingCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a partnership meeting record."""
    meeting = await PartnershipMeetingService.create_meeting(
        db=db,
        partner_id=partner_id,
        recorded_by_id=current_user.id,
        **data.dict()
    )
    return meeting


@router.get("/meetings/partner/{partner_id}", response_model=List[PartnershipMeetingResponse])
async def get_partner_meetings(
    partner_id: int,
    meeting_type: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get meetings for a partner."""
    meetings = await PartnershipMeetingService.get_partner_meetings(
        db=db,
        partner_id=partner_id,
        meeting_type=meeting_type
    )
    return meetings


# ============================================================================
# Partnership Agreements and MOUs
# ============================================================================

@router.post("/agreements", response_model=PartnershipAgreementResponse, status_code=status.HTTP_201_CREATED)
async def create_agreement(
    partner_id: int,
    data: PartnershipAgreementCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new partnership agreement/MOU."""
    agreement = await PartnershipAgreementService.create_agreement(
        db=db,
        partner_id=partner_id,
        created_by_id=current_user.id,
        **data.dict()
    )
    return agreement


@router.get("/agreements/partner/{partner_id}", response_model=List[PartnershipAgreementResponse])
async def get_partner_agreements(
    partner_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get active agreements for a partner."""
    agreements = await PartnershipAgreementService.get_active_agreements(
        db=db,
        partner_id=partner_id
    )
    return agreements


@router.post("/agreements/{agreement_id}/sign", response_model=PartnershipAgreementResponse)
async def sign_agreement(
    agreement_id: int,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Sign/approve an agreement."""
    agreement = await PartnershipAgreementService.sign_agreement(
        db=db,
        agreement_id=agreement_id,
        approved_by_id=current_user.id
    )
    return agreement


# ============================================================================
# Joint Grant Opportunities
# ============================================================================

@router.post("/grants", response_model=JointGrantOpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_grant_opportunity(
    data: JointGrantOpportunityCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a new joint grant opportunity."""
    grant = await JointGrantService.create_grant_opportunity(
        db=db,
        created_by_id=current_user.id,
        **data.dict()
    )
    return grant


@router.get("/grants", response_model=List[JointGrantOpportunityResponse])
async def list_grant_opportunities(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List active grant opportunities."""
    grants = await JointGrantService.get_active_opportunities(
        db=db,
        exclude_statuses=["rejected", "awarded"]
    )
    return grants


# ============================================================================
# Impact Reporting
# ============================================================================

@router.post("/impact-reports", response_model=PartnerImpactReportResponse, status_code=status.HTTP_201_CREATED)
async def create_impact_report(
    partner_id: int,
    data: PartnerImpactReportCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a partner impact report."""
    report = await ImpactReportingService.create_report(
        db=db,
        partner_id=partner_id,
        created_by_id=current_user.id,
        **data.dict()
    )
    return report


@router.get("/impact-reports/partner/{partner_id}", response_model=List[PartnerImpactReportResponse])
async def get_partner_impact_reports(
    partner_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get impact reports for a partner."""
    reports = await ImpactReportingService.get_partner_reports(
        db=db,
        partner_id=partner_id
    )
    return reports


# ============================================================================
# Partner Recognition and Appreciation
# ============================================================================

@router.post("/recognition", response_model=PartnerRecognitionResponse, status_code=status.HTTP_201_CREATED)
async def create_recognition(
    partner_id: int,
    data: PartnerRecognitionCreate,
    current_user: User = Depends(require_staff),
    db: AsyncSession = Depends(get_db),
):
    """Create a partner recognition record."""
    recognition = await PartnerRecognitionService.create_recognition(
        db=db,
        partner_id=partner_id,
        created_by_id=current_user.id,
        **data.dict()
    )
    return recognition


@router.get("/recognition/partner/{partner_id}", response_model=List[PartnerRecognitionResponse])
async def get_partner_recognition(
    partner_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recognition records for a partner."""
    recognition = await PartnerRecognitionService.get_partner_recognition(
        db=db,
        partner_id=partner_id
    )
    return recognition


@router.post("/thank-you", response_model=ThankYouMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_thank_you(
    partner_id: int,
    data: ThankYouMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a thank you message to a partner."""
    message = await PartnerRecognitionService.send_thank_you(
        db=db,
        partner_id=partner_id,
        sent_by_id=current_user.id,
        **data.dict()
    )
    return message


@router.get("/thank-you/partner/{partner_id}", response_model=List[ThankYouMessageResponse])
async def get_thank_you_messages(
    partner_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get thank you messages sent to a partner."""
    return await PartnerRecognitionService.get_thank_you_messages(
        db=db,
        partner_id=partner_id,
    )
