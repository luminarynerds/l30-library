# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Immigrant Services API Routes

Provides endpoints for:
- Citizenship resources
- ESL classes and enrollments
- Conversation circles
- Cultural programs
- Translation services
- Community liaison contacts
- Multilingual resources
- Welcome packets
- Partner organizations
- Impact stories
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from ...core.database import get_db
from ...models.immigrant_services import (
    CitizenshipResource,
    ESLClass,
    ESLEnrollment,
    ConversationCircle,
    CulturalProgram,
    CulturalProgramRegistration,
    TranslationService,
    TranslationRequest,
    CommunityLiaisonContact,
    MultilingualResource,
    WelcomePacket,
    WelcomePacketAssembly,
    WelcomePacketDistribution,
    PartnerOrganization,
    ImpactStory,
    ClassScheduleStatus,
    TranslationStatus,
    ImpactStoryStatus,
    PartnerStatus,
)
from ...schemas.immigrant_services import (
    CitizenshipResourceCreate,
    CitizenshipResourceUpdate,
    CitizenshipResourceResponse,
    CitizenshipResourceListResponse,
    ESLClassCreate,
    ESLClassUpdate,
    ESLClassResponse,
    ESLClassListResponse,
    ESLEnrollmentCreate,
    ESLEnrollmentUpdate,
    ESLEnrollmentResponse,
    ESLEnrollmentWithPatronResponse,
    ESLEnrollmentWithPatronListResponse,
    ConversationCircleCreate,
    ConversationCircleUpdate,
    ConversationCircleResponse,
    ConversationCircleListResponse,
    CulturalProgramCreate,
    CulturalProgramUpdate,
    CulturalProgramResponse,
    CulturalProgramListResponse,
    TranslationServiceCreate,
    TranslationServiceUpdate,
    TranslationServiceResponse,
    TranslationServiceListResponse,
    TranslationRequestCreate,
    TranslationRequestUpdate,
    TranslationRequestResponse,
    TranslationRequestListResponse,
    CommunityLiaisonContactCreate,
    CommunityLiaisonContactUpdate,
    CommunityLiaisonContactResponse,
    CommunityLiaisonContactListResponse,
    MultilingualResourceCreate,
    MultilingualResourceUpdate,
    MultilingualResourceResponse,
    MultilingualResourceListResponse,
    WelcomePacketCreate,
    WelcomePacketUpdate,
    WelcomePacketResponse,
    WelcomePacketListResponse,
    PartnerOrganizationCreate,
    PartnerOrganizationUpdate,
    PartnerOrganizationResponse,
    PartnerOrganizationListResponse,
    ImpactStoryCreate,
    ImpactStoryUpdate,
    ImpactStoryResponse,
    ImpactStoryListResponse,
)
from .dependencies import require_staff
from ...models.user import User

router = APIRouter(prefix="/immigrant-services", tags=["immigrant-services"])


# ============================================================================
# Citizenship Resources Routes
# ============================================================================


@router.post(
    "/citizenship-resources",
    response_model=CitizenshipResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_citizenship_resource(
    resource_data: CitizenshipResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new citizenship resource."""
    resource = CitizenshipResource(**resource_data.model_dump())
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


@router.get("/citizenship-resources", response_model=CitizenshipResourceListResponse)
async def list_citizenship_resources(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    category: Optional[str] = None,
    language: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List citizenship resources with optional filtering."""
    query = select(CitizenshipResource)

    if not is_active:
        query = query.where(CitizenshipResource.is_active == is_active)
    else:
        query = query.where(CitizenshipResource.is_active == True)

    if category:
        query = query.where(CitizenshipResource.category == category)

    if language:
        query = query.where(CitizenshipResource.languages_available.contains([language]))

    total = await db.scalar(select(func.count()).select_from(query.subquery()))

    result = await db.execute(
        query.order_by(desc(CitizenshipResource.created_at)).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return CitizenshipResourceListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/citizenship-resources/{resource_id}", response_model=CitizenshipResourceResponse)
async def get_citizenship_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific citizenship resource."""
    resource = await db.get(CitizenshipResource, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


@router.patch("/citizenship-resources/{resource_id}", response_model=CitizenshipResourceResponse)
async def update_citizenship_resource(
    resource_id: int,
    resource_data: CitizenshipResourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a citizenship resource."""
    resource = await db.get(CitizenshipResource, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    for field, value in resource_data.model_dump(exclude_unset=True).items():
        setattr(resource, field, value)

    await db.commit()
    await db.refresh(resource)
    return resource


@router.delete("/citizenship-resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_citizenship_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete a citizenship resource."""
    resource = await db.get(CitizenshipResource, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    await db.delete(resource)
    await db.commit()


# ============================================================================
# ESL Classes Routes
# ============================================================================


@router.post("/esl-classes", response_model=ESLClassResponse, status_code=status.HTTP_201_CREATED)
async def create_esl_class(
    class_data: ESLClassCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new ESL class."""
    esl_class = ESLClass(**class_data.model_dump())
    db.add(esl_class)
    await db.commit()
    await db.refresh(esl_class)
    return esl_class


@router.get("/esl-classes", response_model=ESLClassListResponse)
async def list_esl_classes(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    level: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List ESL classes with optional filtering."""
    query = select(ESLClass)

    if level:
        query = query.where(ESLClass.level == level)
    if status:
        query = query.where(ESLClass.status == status)

    total = await db.scalar(select(func.count(ESLClass.id)))

    result = await db.execute(query.order_by(ESLClass.start_date).limit(limit).offset(offset))
    items = result.scalars().all()

    return ESLClassListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/esl-classes/{class_id}", response_model=ESLClassResponse)
async def get_esl_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific ESL class."""
    esl_class = await db.get(ESLClass, class_id)
    if not esl_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")
    return esl_class


@router.patch("/esl-classes/{class_id}", response_model=ESLClassResponse)
async def update_esl_class(
    class_id: int,
    class_data: ESLClassUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an ESL class."""
    esl_class = await db.get(ESLClass, class_id)
    if not esl_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    for field, value in class_data.model_dump(exclude_unset=True).items():
        setattr(esl_class, field, value)

    await db.commit()
    await db.refresh(esl_class)
    return esl_class


@router.delete("/esl-classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_esl_class(
    class_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Delete an ESL class."""
    esl_class = await db.get(ESLClass, class_id)
    if not esl_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    await db.delete(esl_class)
    await db.commit()


# ============================================================================
# ESL Enrollments Routes
# ============================================================================


@router.post(
    "/esl-enrollments", response_model=ESLEnrollmentResponse, status_code=status.HTTP_201_CREATED
)
async def create_esl_enrollment(
    enrollment_data: ESLEnrollmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new ESL enrollment."""
    enrollment = ESLEnrollment(**enrollment_data.model_dump())
    db.add(enrollment)
    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.patch("/esl-enrollments/{enrollment_id}", response_model=ESLEnrollmentResponse)
async def update_esl_enrollment(
    enrollment_id: int,
    enrollment_data: ESLEnrollmentUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an ESL enrollment."""
    enrollment = await db.get(ESLEnrollment, enrollment_id)
    if not enrollment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found")

    for field, value in enrollment_data.model_dump(exclude_unset=True).items():
        setattr(enrollment, field, value)

    await db.commit()
    await db.refresh(enrollment)
    return enrollment


@router.get(
    "/esl-classes/{class_id}/enrollments",
    response_model=ESLEnrollmentWithPatronListResponse,
)
async def list_esl_class_enrollments(
    class_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """List enrollments for a given ESL class, joined with patron identity (staff roster view)."""
    esl_class = await db.get(ESLClass, class_id)
    if not esl_class:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    query = (
        select(ESLEnrollment, User)
        .join(User, User.id == ESLEnrollment.patron_id)
        .where(ESLEnrollment.esl_class_id == class_id)
    )
    count_query = select(func.count(ESLEnrollment.id)).where(ESLEnrollment.esl_class_id == class_id)

    if status_filter:
        query = query.where(ESLEnrollment.status == status_filter)
        count_query = count_query.where(ESLEnrollment.status == status_filter)

    total = await db.scalar(count_query)

    result = await db.execute(
        query.order_by(desc(ESLEnrollment.enrollment_date)).limit(limit).offset(offset)
    )
    rows = result.all()

    items = [
        ESLEnrollmentWithPatronResponse(
            id=enrollment.id,
            esl_class_id=enrollment.esl_class_id,
            patron_id=enrollment.patron_id,
            patron_first_name=patron.first_name,
            patron_last_name=patron.last_name,
            patron_email=patron.email,
            enrollment_date=enrollment.enrollment_date,
            completion_date=enrollment.completion_date,
            status=enrollment.status,
            attendance_count=enrollment.attendance_count,
            certificate_earned=enrollment.certificate_earned,
            assessment_score=enrollment.assessment_score,
            notes=enrollment.notes,
            created_at=enrollment.created_at,
            updated_at=enrollment.updated_at,
        )
        for enrollment, patron in rows
    ]

    return ESLEnrollmentWithPatronListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


# ============================================================================
# Conversation Circles Routes
# ============================================================================


@router.post(
    "/conversation-circles",
    response_model=ConversationCircleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation_circle(
    circle_data: ConversationCircleCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new conversation circle."""
    circle = ConversationCircle(**circle_data.model_dump())
    db.add(circle)
    await db.commit()
    await db.refresh(circle)
    return circle


@router.get("/conversation-circles", response_model=ConversationCircleListResponse)
async def list_conversation_circles(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    circle_type: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List conversation circles with optional filtering."""
    query = select(ConversationCircle).where(ConversationCircle.is_active == is_active)

    if circle_type:
        query = query.where(ConversationCircle.circle_type == circle_type)

    total = await db.scalar(
        select(func.count(ConversationCircle.id)).where(ConversationCircle.is_active == is_active)
    )

    result = await db.execute(
        query.order_by(ConversationCircle.start_date).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return ConversationCircleListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/conversation-circles/{circle_id}", response_model=ConversationCircleResponse)
async def get_conversation_circle(
    circle_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific conversation circle."""
    circle = await db.get(ConversationCircle, circle_id)
    if not circle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found")
    return circle


@router.patch("/conversation-circles/{circle_id}", response_model=ConversationCircleResponse)
async def update_conversation_circle(
    circle_id: int,
    circle_data: ConversationCircleUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a conversation circle."""
    circle = await db.get(ConversationCircle, circle_id)
    if not circle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Circle not found")

    for field, value in circle_data.model_dump(exclude_unset=True).items():
        setattr(circle, field, value)

    await db.commit()
    await db.refresh(circle)
    return circle


# ============================================================================
# Cultural Programs Routes
# ============================================================================


@router.post(
    "/cultural-programs",
    response_model=CulturalProgramResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cultural_program(
    program_data: CulturalProgramCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new cultural program."""
    program = CulturalProgram(**program_data.model_dump())
    db.add(program)
    await db.commit()
    await db.refresh(program)
    return program


@router.get("/cultural-programs", response_model=CulturalProgramListResponse)
async def list_cultural_programs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    program_type: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List cultural programs with optional filtering."""
    query = select(CulturalProgram)

    if program_type:
        query = query.where(CulturalProgram.program_type == program_type)
    if status:
        query = query.where(CulturalProgram.status == status)

    total = await db.scalar(select(func.count(CulturalProgram.id)))

    result = await db.execute(
        query.order_by(desc(CulturalProgram.event_date)).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return CulturalProgramListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/cultural-programs/{program_id}", response_model=CulturalProgramResponse)
async def get_cultural_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific cultural program."""
    program = await db.get(CulturalProgram, program_id)
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return program


@router.patch("/cultural-programs/{program_id}", response_model=CulturalProgramResponse)
async def update_cultural_program(
    program_id: int,
    program_data: CulturalProgramUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a cultural program."""
    program = await db.get(CulturalProgram, program_id)
    if not program:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

    for field, value in program_data.model_dump(exclude_unset=True).items():
        setattr(program, field, value)

    await db.commit()
    await db.refresh(program)
    return program


# ============================================================================
# Translation Services Routes
# ============================================================================


@router.post(
    "/translation-services",
    response_model=TranslationServiceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_translation_service(
    service_data: TranslationServiceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new translation service."""
    service = TranslationService(**service_data.model_dump())
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service


@router.get("/translation-services", response_model=TranslationServiceListResponse)
async def list_translation_services(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    source_language: Optional[str] = None,
    target_language: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List translation services with optional filtering."""
    query = select(TranslationService).where(TranslationService.is_active == is_active)

    if source_language:
        query = query.where(TranslationService.source_language == source_language)
    if target_language:
        query = query.where(TranslationService.target_language == target_language)

    total = await db.scalar(
        select(func.count(TranslationService.id)).where(TranslationService.is_active == is_active)
    )

    result = await db.execute(query.limit(limit).offset(offset))
    items = result.scalars().all()

    return TranslationServiceListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/translation-services/{service_id}", response_model=TranslationServiceResponse)
async def get_translation_service(
    service_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific translation service."""
    service = await db.get(TranslationService, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    return service


@router.patch("/translation-services/{service_id}", response_model=TranslationServiceResponse)
async def update_translation_service(
    service_id: int,
    service_data: TranslationServiceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a translation service."""
    service = await db.get(TranslationService, service_id)
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")

    for field, value in service_data.model_dump(exclude_unset=True).items():
        setattr(service, field, value)

    await db.commit()
    await db.refresh(service)
    return service


# ============================================================================
# Translation Requests Routes
# ============================================================================


@router.post(
    "/translation-requests",
    response_model=TranslationRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_translation_request(
    request_data: TranslationRequestCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new translation request."""
    from datetime import date

    translation_request = TranslationRequest(**request_data.model_dump(), request_date=date.today())
    db.add(translation_request)
    await db.commit()
    await db.refresh(translation_request)
    return translation_request


@router.get("/translation-requests", response_model=TranslationRequestListResponse)
async def list_translation_requests(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List translation requests with optional filtering."""
    query = select(TranslationRequest)

    if status:
        query = query.where(TranslationRequest.status == status)

    total = await db.scalar(select(func.count(TranslationRequest.id)))

    result = await db.execute(
        query.order_by(desc(TranslationRequest.request_date)).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return TranslationRequestListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.patch("/translation-requests/{request_id}", response_model=TranslationRequestResponse)
async def update_translation_request(
    request_id: int,
    request_data: TranslationRequestUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a translation request."""
    translation_request = await db.get(TranslationRequest, request_id)
    if not translation_request:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Request not found")

    for field, value in request_data.model_dump(exclude_unset=True).items():
        setattr(translation_request, field, value)

    await db.commit()
    await db.refresh(translation_request)
    return translation_request


# ============================================================================
# Community Liaison Contacts Routes
# ============================================================================


@router.post(
    "/community-liaison-contacts",
    response_model=CommunityLiaisonContactResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_community_liaison_contact(
    contact_data: CommunityLiaisonContactCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new community liaison contact."""
    contact = CommunityLiaisonContact(**contact_data.model_dump())
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact


@router.get("/community-liaison-contacts", response_model=CommunityLiaisonContactListResponse)
async def list_community_liaison_contacts(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    role: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List community liaison contacts with optional filtering."""
    query = select(CommunityLiaisonContact).where(CommunityLiaisonContact.is_active == is_active)

    if role:
        query = query.where(CommunityLiaisonContact.role == role)

    total = await db.scalar(
        select(func.count(CommunityLiaisonContact.id)).where(
            CommunityLiaisonContact.is_active == is_active
        )
    )

    result = await db.execute(
        query.order_by(CommunityLiaisonContact.last_name).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return CommunityLiaisonContactListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/community-liaison-contacts/{contact_id}", response_model=CommunityLiaisonContactResponse
)
async def get_community_liaison_contact(
    contact_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific community liaison contact."""
    contact = await db.get(CommunityLiaisonContact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.patch(
    "/community-liaison-contacts/{contact_id}", response_model=CommunityLiaisonContactResponse
)
async def update_community_liaison_contact(
    contact_id: int,
    contact_data: CommunityLiaisonContactUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a community liaison contact."""
    contact = await db.get(CommunityLiaisonContact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    for field, value in contact_data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)

    await db.commit()
    await db.refresh(contact)
    return contact


# ============================================================================
# Multilingual Resources Routes
# ============================================================================


@router.post(
    "/multilingual-resources",
    response_model=MultilingualResourceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_multilingual_resource(
    resource_data: MultilingualResourceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new multilingual resource."""
    resource = MultilingualResource(**resource_data.model_dump())
    db.add(resource)
    await db.commit()
    await db.refresh(resource)
    return resource


@router.get("/multilingual-resources", response_model=MultilingualResourceListResponse)
async def list_multilingual_resources(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    language: Optional[str] = None,
    resource_type: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List multilingual resources with optional filtering."""
    query = select(MultilingualResource).where(MultilingualResource.is_active == is_active)

    if language:
        query = query.where(MultilingualResource.language == language)
    if resource_type:
        query = query.where(MultilingualResource.resource_type == resource_type)

    total = await db.scalar(
        select(func.count(MultilingualResource.id)).where(
            MultilingualResource.is_active == is_active
        )
    )

    result = await db.execute(
        query.order_by(MultilingualResource.title).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return MultilingualResourceListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/multilingual-resources/{resource_id}", response_model=MultilingualResourceResponse)
async def get_multilingual_resource(
    resource_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific multilingual resource."""
    resource = await db.get(MultilingualResource, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return resource


@router.patch("/multilingual-resources/{resource_id}", response_model=MultilingualResourceResponse)
async def update_multilingual_resource(
    resource_id: int,
    resource_data: MultilingualResourceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a multilingual resource."""
    resource = await db.get(MultilingualResource, resource_id)
    if not resource:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    for field, value in resource_data.model_dump(exclude_unset=True).items():
        setattr(resource, field, value)

    await db.commit()
    await db.refresh(resource)
    return resource


# ============================================================================
# Welcome Packets Routes
# ============================================================================


@router.post(
    "/welcome-packets", response_model=WelcomePacketResponse, status_code=status.HTTP_201_CREATED
)
async def create_welcome_packet(
    packet_data: WelcomePacketCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new welcome packet."""
    from datetime import date

    packet = WelcomePacket(**packet_data.model_dump(), creation_date=date.today())
    db.add(packet)
    await db.commit()
    await db.refresh(packet)
    return packet


@router.get("/welcome-packets", response_model=WelcomePacketListResponse)
async def list_welcome_packets(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    packet_type: Optional[str] = None,
    is_active: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """List welcome packets with optional filtering."""
    query = select(WelcomePacket).where(WelcomePacket.is_active == is_active)

    if packet_type:
        query = query.where(WelcomePacket.packet_type == packet_type)

    total = await db.scalar(
        select(func.count(WelcomePacket.id)).where(WelcomePacket.is_active == is_active)
    )

    result = await db.execute(query.order_by(WelcomePacket.title).limit(limit).offset(offset))
    items = result.scalars().all()

    return WelcomePacketListResponse(
        items=items,
        total=total or 0,
        limit=limit,
        offset=offset,
    )


@router.get("/welcome-packets/{packet_id}", response_model=WelcomePacketResponse)
async def get_welcome_packet(
    packet_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific welcome packet."""
    packet = await db.get(WelcomePacket, packet_id)
    if not packet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packet not found")
    return packet


@router.patch("/welcome-packets/{packet_id}", response_model=WelcomePacketResponse)
async def update_welcome_packet(
    packet_id: int,
    packet_data: WelcomePacketUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a welcome packet."""
    packet = await db.get(WelcomePacket, packet_id)
    if not packet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Packet not found")

    for field, value in packet_data.model_dump(exclude_unset=True).items():
        setattr(packet, field, value)

    await db.commit()
    await db.refresh(packet)
    return packet


# ============================================================================
# Partner Organizations Routes
# ============================================================================


@router.post(
    "/partner-organizations",
    response_model=PartnerOrganizationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_partner_organization(
    org_data: PartnerOrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new partner organization."""
    org = PartnerOrganization(**org_data.model_dump())
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return org


@router.get("/partner-organizations", response_model=PartnerOrganizationListResponse)
async def list_partner_organizations(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List partner organizations with optional filtering."""
    query = select(PartnerOrganization)

    if status:
        query = query.where(PartnerOrganization.status == status)

    total = await db.scalar(select(func.count(PartnerOrganization.id)))

    result = await db.execute(query.order_by(PartnerOrganization.name).limit(limit).offset(offset))
    items = result.scalars().all()

    return PartnerOrganizationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/partner-organizations/{org_id}", response_model=PartnerOrganizationResponse)
async def get_partner_organization(
    org_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific partner organization."""
    org = await db.get(PartnerOrganization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return org


@router.patch("/partner-organizations/{org_id}", response_model=PartnerOrganizationResponse)
async def update_partner_organization(
    org_id: int,
    org_data: PartnerOrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update a partner organization."""
    org = await db.get(PartnerOrganization, org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    for field, value in org_data.model_dump(exclude_unset=True).items():
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)
    return org


# ============================================================================
# Impact Stories Routes
# ============================================================================


@router.post(
    "/impact-stories", response_model=ImpactStoryResponse, status_code=status.HTTP_201_CREATED
)
async def create_impact_story(
    story_data: ImpactStoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Create a new impact story."""
    from datetime import date

    story = ImpactStory(**story_data.model_dump(), submitted_date=date.today())
    db.add(story)
    await db.commit()
    await db.refresh(story)
    return story


@router.get("/impact-stories", response_model=ImpactStoryListResponse)
async def list_impact_stories(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    featured_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """List impact stories with optional filtering."""
    query = select(ImpactStory)

    if status:
        query = query.where(ImpactStory.status == status)
    if featured_only:
        query = query.where(ImpactStory.featured_on_website == True)

    total = await db.scalar(select(func.count(ImpactStory.id)))

    result = await db.execute(
        query.order_by(desc(ImpactStory.submitted_date)).limit(limit).offset(offset)
    )
    items = result.scalars().all()

    return ImpactStoryListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/impact-stories/{story_id}", response_model=ImpactStoryResponse)
async def get_impact_story(
    story_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific impact story."""
    story = await db.get(ImpactStory, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    # Increment view count
    story.reach_count += 1
    await db.commit()
    return story


@router.patch("/impact-stories/{story_id}", response_model=ImpactStoryResponse)
async def update_impact_story(
    story_id: int,
    story_data: ImpactStoryUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
):
    """Update an impact story."""
    story = await db.get(ImpactStory, story_id)
    if not story:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    for field, value in story_data.model_dump(exclude_unset=True).items():
        setattr(story, field, value)

    await db.commit()
    await db.refresh(story)
    return story
