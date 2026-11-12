# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.error_codes import ErrorCode
from ...core.exceptions import ResourceNotFoundError

from ...models.legal import (
    LegalTopic, LegalClinic, LegalClinicRegistration, CourtLocation, CourtType,
    ClinicStatus, RegistrationStatus, LegalServiceProvider, EmergencyResource,
    FeeWaiverEligibility, ExpungementEligibility, DeadlineRule,
    DeadlineCalculation, LegalGlossaryTerm, KnowYourRightsGuide,
    LegalFormLinkCheck, LegalContentFeedback, LegalStaffGuideline
)

logger = get_logger(__name__)


# ============================================================================
# Legal Topic Services (Organizational/Compliance Structure)
# ============================================================================

async def get_topic_by_id(
    db: AsyncSession,
    topic_id: int
) -> Optional[LegalTopic]:
    result = await db.execute(
        select(LegalTopic)
        .options(selectinload(LegalTopic.children))
        .where(LegalTopic.id == topic_id)
    )
    return result.scalar_one_or_none()


async def get_topic_by_slug(
    db: AsyncSession,
    slug: str
) -> Optional[LegalTopic]:
    result = await db.execute(
        select(LegalTopic)
        .options(selectinload(LegalTopic.children))
        .where(LegalTopic.slug == slug)
    )
    return result.scalar_one_or_none()


async def list_topics(
    db: AsyncSession,
    parent_id: Optional[int] = None,
    is_active: Optional[bool] = True,
    is_featured: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalTopic], int]:
    query = select(LegalTopic).options(selectinload(LegalTopic.children))
    count_query = select(func.count(LegalTopic.id))

    # Apply filters
    filters = []
    if parent_id is not None:
        filters.append(LegalTopic.parent_id == parent_id)
    elif parent_id is None:
        # Get root topics by default
        filters.append(LegalTopic.parent_id.is_(None))
    if is_active is not None:
        filters.append(LegalTopic.is_active == is_active)
    if is_featured is not None:
        filters.append(LegalTopic.is_featured == is_featured)

    if filters:
        query = query.where(and_(*filters))
        count_query = count_query.where(and_(*filters))

    # Get total count
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get paginated results
    query = query.order_by(LegalTopic.display_order, LegalTopic.name)
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    topics = result.scalars().all()

    return topics, total


async def get_topic_tree(
    db: AsyncSession,
    is_active: bool = True
) -> list[LegalTopic]:
    # Get root topics
    result = await db.execute(
        select(LegalTopic)
        .options(selectinload(LegalTopic.children).selectinload(LegalTopic.children))
        .where(
            LegalTopic.parent_id.is_(None),
            LegalTopic.is_active == is_active
        )
        .order_by(LegalTopic.display_order, LegalTopic.name)
    )
    return result.scalars().all()


async def create_topic(
    db: AsyncSession,
    topic_data: dict,
    created_by_id: Optional[int] = None
) -> LegalTopic:
    topic = LegalTopic(**topic_data, created_by_id=created_by_id)
    db.add(topic)
    await db.commit()
    await db.refresh(topic)
    return topic


async def update_topic(
    db: AsyncSession,
    topic_id: int,
    topic_data: dict
) -> LegalTopic:
    topic = await get_topic_by_id(db, topic_id)
    if not topic:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Legal topic not found"
        )

    for key, value in topic_data.items():
        if value is not None:
            setattr(topic, key, value)

    await db.commit()
    await db.refresh(topic)
    return topic


async def increment_topic_views(
    db: AsyncSession,
    topic_id: int
) -> None:
    topic = await get_topic_by_id(db, topic_id)
    if topic:
        topic.view_count = (topic.view_count or 0) + 1
        await db.commit()


# ============================================================================
# Court Location Services
# ============================================================================

async def get_court_by_id(
    db: AsyncSession,
    court_id: int
) -> Optional[CourtLocation]:
    result = await db.execute(
        select(CourtLocation).where(CourtLocation.id == court_id)
    )
    return result.scalar_one_or_none()


async def list_courts(
    db: AsyncSession,
    court_type: Optional[CourtType] = None,
    jurisdiction: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    has_self_help: Optional[bool] = None,
    e_filing: Optional[bool] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[CourtLocation], int]:
    base_query = select(CourtLocation)
    count_query = select(func.count(CourtLocation.id))

    filters = [CourtLocation.is_active == is_active]
    if court_type is not None:
        filters.append(CourtLocation.court_type == court_type)
    if jurisdiction is not None:
        safe_jurisdiction = jurisdiction.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(CourtLocation.jurisdiction.ilike(f"%{safe_jurisdiction}%"))
    if city is not None:
        safe_city = city.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(CourtLocation.city.ilike(f"%{safe_city}%"))
    if state is not None:
        filters.append(CourtLocation.state == state)
    if has_self_help is not None:
        filters.append(CourtLocation.has_self_help_center == has_self_help)
    if e_filing is not None:
        filters.append(CourtLocation.e_filing_available == e_filing)

    base_query = base_query.where(and_(*filters))
    count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(CourtLocation.name)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    courts = result.scalars().all()

    return courts, total


async def create_court(
    db: AsyncSession,
    court_data: dict,
    created_by_id: Optional[int] = None
) -> CourtLocation:
    court = CourtLocation(**court_data, created_by_id=created_by_id)
    db.add(court)
    await db.commit()
    await db.refresh(court)
    return court


async def update_court(
    db: AsyncSession,
    court_id: int,
    court_data: dict
) -> CourtLocation:
    court = await get_court_by_id(db, court_id)
    if not court:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Court location not found"
        )

    for key, value in court_data.items():
        if value is not None:
            setattr(court, key, value)

    await db.commit()
    await db.refresh(court)
    return court


# ============================================================================
# Legal Service Provider Services
# ============================================================================

async def get_provider_by_id(
    db: AsyncSession,
    provider_id: int
) -> Optional[LegalServiceProvider]:
    result = await db.execute(
        select(LegalServiceProvider)
        .options(selectinload(LegalServiceProvider.clinics))
        .where(LegalServiceProvider.id == provider_id)
    )
    return result.scalar_one_or_none()


async def list_providers(
    db: AsyncSession,
    provider_type: Optional[str] = None,
    topic_id: Optional[int] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    language: Optional[str] = None,
    accepts_walkins: Optional[bool] = None,
    virtual_services: Optional[bool] = None,
    query: Optional[str] = None,
    special_population: Optional[str] = None,
    is_active: bool = True,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalServiceProvider], int]:
    base_query = select(LegalServiceProvider)
    count_query = select(func.count(LegalServiceProvider.id))

    filters = [LegalServiceProvider.is_active == is_active]
    if provider_type is not None:
        filters.append(LegalServiceProvider.provider_type == provider_type)
    if topic_id is not None:
        filters.append(LegalServiceProvider.topic_ids.contains([topic_id]))
    if city is not None:
        safe_city = city.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(LegalServiceProvider.city.ilike(f"%{safe_city}%"))
    if state is not None:
        filters.append(LegalServiceProvider.state == state)
    if language is not None:
        filters.append(LegalServiceProvider.languages_spoken.any(language))
    if accepts_walkins is not None:
        filters.append(LegalServiceProvider.accepts_walkins == accepts_walkins)
    if virtual_services is not None:
        filters.append(LegalServiceProvider.virtual_services == virtual_services)
    if query is not None:
        safe_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(
            or_(
                LegalServiceProvider.name.ilike(f"%{safe_query}%"),
                LegalServiceProvider.description.ilike(f"%{safe_query}%"),
            )
        )
    if special_population is not None:
        filters.append(LegalServiceProvider.special_populations.any(special_population))

    base_query = base_query.where(and_(*filters))
    count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(LegalServiceProvider.name)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    providers = result.scalars().all()

    return providers, total


async def create_provider(
    db: AsyncSession,
    provider_data: dict,
    created_by_id: Optional[int] = None
) -> LegalServiceProvider:
    provider = LegalServiceProvider(**provider_data, created_by_id=created_by_id)
    db.add(provider)
    await db.commit()
    await db.refresh(provider)
    return provider


async def update_provider(
    db: AsyncSession,
    provider_id: int,
    provider_data: dict
) -> LegalServiceProvider:
    provider = await get_provider_by_id(db, provider_id)
    if not provider:
        raise ResourceNotFoundError(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message="Service provider not found"
        )

    for key, value in provider_data.items():
        if value is not None:
            setattr(provider, key, value)

    await db.commit()
    await db.refresh(provider)
    return provider


# ============================================================================
# Glossary Services (Compliance/Reference)
# ============================================================================

async def get_glossary_term(
    db: AsyncSession,
    slug: str
) -> Optional[LegalGlossaryTerm]:
    result = await db.execute(
        select(LegalGlossaryTerm)
        .where(
            LegalGlossaryTerm.slug == slug,
            LegalGlossaryTerm.is_active == True
        )
    )
    return result.scalar_one_or_none()


async def list_glossary_terms(
    db: AsyncSession,
    query: Optional[str] = None,
    letter: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalGlossaryTerm], int]:
    base_query = select(LegalGlossaryTerm)
    count_query = select(func.count(LegalGlossaryTerm.id))

    filters = [LegalGlossaryTerm.is_active == True]
    if query:
        safe_query = query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(or_(
            LegalGlossaryTerm.term.ilike(f"%{safe_query}%"),
            LegalGlossaryTerm.definition_standard.ilike(f"%{safe_query}%")
        ))
    if letter:
        safe_letter = letter.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        filters.append(LegalGlossaryTerm.term.ilike(f"{safe_letter}%"))

    base_query = base_query.where(and_(*filters))
    count_query = count_query.where(and_(*filters))

    # Get total
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    # Get results
    base_query = base_query.order_by(LegalGlossaryTerm.term)
    base_query = base_query.offset(skip).limit(limit)
    result = await db.execute(base_query)
    terms = result.scalars().all()

    return terms, total


async def create_glossary_term(
    db: AsyncSession,
    term_data: dict
) -> LegalGlossaryTerm:
    term = LegalGlossaryTerm(**term_data)
    db.add(term)
    await db.commit()
    await db.refresh(term)
    return term


# ============================================================================
# Fee Waiver Eligibility Services
# ============================================================================

async def check_fee_waiver_eligibility(
    db: AsyncSession,
    jurisdiction: str,
    household_size: int,
    annual_income: float,
    receives_public_benefits: list[str]
) -> dict:
    result = await db.execute(
        select(FeeWaiverEligibility)
        .where(
            FeeWaiverEligibility.jurisdiction == jurisdiction,
            FeeWaiverEligibility.is_active == True
        )
    )
    eligibility = result.scalar_one_or_none()

    if not eligibility:
        return {
            "is_eligible": False,
            "eligibility_reason": "Eligibility information not available for this jurisdiction",
            "automatic_eligibility": False,
            "partial_waiver_available": False,
            "payment_plan_available": False,
            "form_id": None,
            "required_documentation": [],
            "next_steps": ["Contact the court clerk for eligibility information"]
        }

    # Check automatic eligibility
    for auto_criteria in eligibility.automatic_eligibility:
        if auto_criteria.get("criteria") in receives_public_benefits:
            return {
                "is_eligible": True,
                "eligibility_reason": f"Automatically eligible due to {auto_criteria.get('criteria')}",
                "automatic_eligibility": True,
                "partial_waiver_available": False,
                "payment_plan_available": False,
                "form_id": eligibility.form_id,
                "required_documentation": [auto_criteria.get("documentation", "Proof of benefits")],
                "next_steps": ["Complete the fee waiver form", "Attach proof of benefits"]
            }

    # Check income thresholds
    for threshold in eligibility.income_thresholds:
        if threshold.get("household_size") == household_size:
            max_income = threshold.get("annual_income", 0)
            if annual_income <= max_income:
                return {
                    "is_eligible": True,
                    "eligibility_reason": f"Income is within fee waiver threshold for household size {household_size}",
                    "automatic_eligibility": False,
                    "partial_waiver_available": eligibility.partial_waiver_available,
                    "payment_plan_available": eligibility.payment_plan_available,
                    "form_id": eligibility.form_id,
                    "required_documentation": eligibility.required_documentation,
                    "next_steps": ["Complete the fee waiver form", "Gather income documentation"]
                }

    return {
        "is_eligible": False,
        "eligibility_reason": "Income exceeds fee waiver threshold",
        "automatic_eligibility": False,
        "partial_waiver_available": eligibility.partial_waiver_available,
        "payment_plan_available": eligibility.payment_plan_available,
        "form_id": None,
        "required_documentation": [],
        "next_steps": [
            "You may apply for a partial waiver" if eligibility.partial_waiver_available else None,
            "Payment plans may be available" if eligibility.payment_plan_available else None
        ]
    }


# ============================================================================
# Expungement Eligibility Services
# ============================================================================

async def check_expungement_eligibility(
    db: AsyncSession,
    jurisdiction: str,
    offense_category: str,
    offense_type: Optional[str],
    conviction_date: date,
    sentence_completed_date: Optional[date]
) -> dict:
    query = select(ExpungementEligibility).where(
        ExpungementEligibility.jurisdiction == jurisdiction,
        ExpungementEligibility.offense_category == offense_category,
        ExpungementEligibility.is_active == True
    )

    if offense_type:
        query = query.where(
            or_(
                ExpungementEligibility.offense_type == offense_type,
                ExpungementEligibility.offense_type.is_(None)
            )
        )

    result = await db.execute(query)
    eligibility = result.scalar_one_or_none()

    if not eligibility:
        return {
            "is_eligible": False,
            "eligibility_notes": "Eligibility information not available for this offense type",
            "waiting_period_met": False,
            "waiting_period_end_date": None,
            "requirements": [],
            "exclusions": [],
            "form_ids": [],
            "estimated_timeline": None,
            "estimated_cost": None
        }

    # Calculate waiting period
    start_date = sentence_completed_date or conviction_date
    if eligibility.waiting_period_years:
        waiting_end = start_date + timedelta(days=int(eligibility.waiting_period_years * 365))
        waiting_period_met = date.today() >= waiting_end
    else:
        waiting_end = None
        waiting_period_met = True

    return {
        "is_eligible": eligibility.is_eligible and waiting_period_met,
        "eligibility_notes": eligibility.eligibility_notes or "",
        "waiting_period_met": waiting_period_met,
        "waiting_period_end_date": waiting_end,
        "requirements": eligibility.requirements,
        "exclusions": eligibility.exclusions,
        "form_ids": eligibility.form_ids,
        "estimated_timeline": eligibility.estimated_timeline,
        "estimated_cost": eligibility.estimated_cost
    }


# ============================================================================
# Staff Guidelines Services
# ============================================================================

async def list_staff_guidelines(
    db: AsyncSession,
    category: Optional[str] = None,
    is_active: bool = True
) -> list[LegalStaffGuideline]:
    query = select(LegalStaffGuideline).where(LegalStaffGuideline.is_active == is_active)

    if category:
        query = query.where(LegalStaffGuideline.category == category)

    query = query.order_by(LegalStaffGuideline.category, LegalStaffGuideline.title)
    result = await db.execute(query)
    return result.scalars().all()


async def get_staff_guideline(
    db: AsyncSession,
    slug: str
) -> Optional[LegalStaffGuideline]:
    result = await db.execute(
        select(LegalStaffGuideline)
        .where(
            LegalStaffGuideline.slug == slug,
            LegalStaffGuideline.is_active == True
        )
    )
    return result.scalar_one_or_none()


# ============================================================================
# Link Checking Services (Quality Assurance)
# ============================================================================

async def check_form_links(
    db: AsyncSession,
    form_id: int
) -> list[LegalFormLinkCheck]:
    import asyncio
    import aiohttp
    from .document_service import get_form_by_id

    form = await get_form_by_id(db, form_id)
    if not form:
        return []

    links_to_check = []
    if form.form_url:
        links_to_check.append(("form_url", form.form_url))
    if form.instructions_url:
        links_to_check.append(("instructions_url", form.instructions_url))
    if form.example_url:
        links_to_check.append(("example_url", form.example_url))

    results = []
    async with aiohttp.ClientSession() as session:
        for link_type, url in links_to_check:
            try:
                async with session.head(url, timeout=10) as response:
                    check = LegalFormLinkCheck(
                        form_id=form_id,
                        link_type=link_type,
                        url=url,
                        is_valid=response.status < 400,
                        http_status=response.status
                    )
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                check = LegalFormLinkCheck(
                    form_id=form_id,
                    link_type=link_type,
                    url=url,
                    is_valid=False,
                    error_message=str(e)
                )

            db.add(check)
            results.append(check)

    await db.commit()
    return results


async def get_broken_links(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> tuple[list[LegalFormLinkCheck], int]:
    # Get the most recent check for each form/link combination
    subquery = (
        select(
            LegalFormLinkCheck.form_id,
            LegalFormLinkCheck.link_type,
            func.max(LegalFormLinkCheck.checked_at).label("max_checked")
        )
        .group_by(LegalFormLinkCheck.form_id, LegalFormLinkCheck.link_type)
        .subquery()
    )

    query = (
        select(LegalFormLinkCheck)
        .join(
            subquery,
            and_(
                LegalFormLinkCheck.form_id == subquery.c.form_id,
                LegalFormLinkCheck.link_type == subquery.c.link_type,
                LegalFormLinkCheck.checked_at == subquery.c.max_checked
            )
        )
        .where(LegalFormLinkCheck.is_valid == False)
    )

    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar()

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    checks = result.scalars().all()

    return checks, total
