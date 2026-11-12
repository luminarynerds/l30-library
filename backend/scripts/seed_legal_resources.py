#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for Legal Resources featuring LA County resources.

This script populates:
- Legal topics (family, housing, etc.)
- LA County legal service providers
- LASC (LA Superior Court) common forms
- Legal guides
- Legal glossary terms
- Legal clinic schedules
- Clinic registrations
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports - must be before app imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.datetime_utils import utc_now
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from app.core.database import AsyncSessionLocal
from app.models.legal import (
    LegalTopic, LegalForm, LegalGuide, LegalServiceProvider,
    LegalClinic, LegalClinicRegistration, LegalGlossaryTerm,
    CourtLocation, FormDifficulty, FormStatus,
    GuideReadingLevel, ProviderType, ClinicStatus, CourtType,
    RegistrationStatus
)
from app.models.user import User
from datetime import date, datetime, timedelta


async def get_or_create_admin_user(db: AsyncSession) -> User:
    """Get or create admin user for created_by references."""
    result = await db.execute(
        select(User).where(User.email == "admin@l30.org").limit(1)
    )
    admin = result.scalar_one_or_none()

    if not admin:
        # Try to get any admin user
        result = await db.execute(
            select(User).where(User.role == "ADMIN").limit(1)
        )
        admin = result.scalar_one_or_none()

    if not admin:
        # Try to get super admin user
        result = await db.execute(
            select(User).where(User.role == "SUPER_ADMIN").limit(1)
        )
        admin = result.scalar_one_or_none()

    return admin


async def seed_legal_topics(db: AsyncSession, admin_id: int) -> dict:
    """Create legal topics taxonomy."""
    print("Seeding legal topics...")

    topics_data = [
        {
            "name": "Family Law",
            "slug": "family",
            "description": "Divorce, custody, child support, domestic violence restraining orders, adoption, guardianship",
            "icon": "heart",
            "color": "#E91E63",
            "is_featured": True,
            "keywords": ["divorce", "custody", "child support", "restraining order", "domestic violence", "adoption"],
        },
        {
            "name": "Housing & Eviction",
            "slug": "housing",
            "description": "Eviction defense, unlawful detainer, tenant rights, habitability issues, security deposits",
            "icon": "home",
            "color": "#2196F3",
            "is_featured": True,
            "keywords": ["eviction", "unlawful detainer", "tenant", "landlord", "rent", "security deposit"],
        },
        {
            "name": "Employment",
            "slug": "employment",
            "description": "Wrongful termination, wage claims, discrimination, workplace harassment, unemployment benefits",
            "icon": "briefcase",
            "color": "#4CAF50",
            "keywords": ["employment", "wrongful termination", "wage", "discrimination", "harassment"],
        },
        {
            "name": "Consumer & Debt",
            "slug": "consumer",
            "description": "Debt collection, bankruptcy, small claims, consumer protection, credit repair",
            "icon": "credit-card",
            "color": "#FF9800",
            "keywords": ["debt", "bankruptcy", "small claims", "consumer", "collection"],
        },
        {
            "name": "Immigration",
            "slug": "immigration",
            "description": "Green cards, citizenship, DACA, asylum, deportation defense",
            "icon": "globe",
            "color": "#9C27B0",
            "keywords": ["immigration", "citizenship", "daca", "asylum", "deportation", "visa"],
        },
        {
            "name": "Name Change",
            "slug": "name-change",
            "description": "Adult name change, minor name change, gender marker change",
            "icon": "user",
            "color": "#00BCD4",
            "keywords": ["name change", "gender marker", "legal name"],
        },
        {
            "name": "Small Claims",
            "slug": "small-claims",
            "description": "File a small claims case, defend a small claims case, collect a judgment",
            "icon": "gavel",
            "color": "#795548",
            "keywords": ["small claims", "sue", "judgment", "dispute"],
        },
    ]

    topic_map = {}
    for topic_data in topics_data:
        # Check if topic already exists
        result = await db.execute(
            select(LegalTopic).where(LegalTopic.slug == topic_data["slug"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            topic = LegalTopic(
                **topic_data,
                created_by_id=admin_id,
                is_active=True
            )
            db.add(topic)
            await db.flush()
            topic_map[topic_data["slug"]] = topic.id
            print(f"  Created topic: {topic_data['name']}")
        else:
            topic_map[topic_data["slug"]] = existing.id
            print(f"  Topic already exists: {topic_data['name']}")

    await db.commit()
    return topic_map


async def seed_la_county_providers(db: AsyncSession, topic_map: dict, admin_id: int):
    """Create LA County legal service providers."""
    print("Seeding LA County legal service providers...")

    providers_data = [
        {
            "name": "Los Angeles County Law Library",
            "slug": "la-county-law-library",
            "provider_type": ProviderType.court_self_help,
            "description": "The LA County Law Library provides free access to legal research materials, "
                          "self-help resources, and research assistance. With locations throughout LA County, "
                          "the library serves self-represented litigants, attorneys, and the public.",
            "services": [
                {
                    "service": "Legal Research Assistance",
                    "description": "Reference librarians help locate legal materials and research strategies"
                },
                {
                    "service": "Self-Help Forms",
                    "description": "Access to California Judicial Council forms and local court forms"
                },
                {
                    "service": "Online Resources",
                    "description": "Free access to legal databases and research tools"
                },
                {
                    "service": "How-To Guides",
                    "description": "Step-by-step guides for common legal procedures"
                }
            ],
            "eligibility_criteria": "Free and open to the public. No library card or residency requirement.",
            "phone": "213-785-2529",
            "email": "lawlibrary@lalawlibrary.org",
            "website": "https://lalawlibrary.org/",
            "address_line1": "301 W 1st Street",
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90012",
            "hours": {
                "monday": {"open": "08:30", "close": "17:00"},
                "tuesday": {"open": "08:30", "close": "17:00"},
                "wednesday": {"open": "08:30", "close": "17:00"},
                "thursday": {"open": "08:30", "close": "17:00"},
                "friday": {"open": "08:30", "close": "17:00"},
                "saturday": {"open": "10:00", "close": "17:00"},
            },
            "hours_notes": "Main library hours. Branch locations may vary. Holiday closures apply.",
            "languages_spoken": ["English", "Spanish"],
            "accepts_walkins": True,
            "appointment_required": False,
            "wheelchair_accessible": True,
            "virtual_services": True,
            "specializations": ["Self-Help Resources", "Legal Research", "Forms Assistance"],
            "is_active": True,
            "is_verified": True,
        },
        {
            "name": "Legal Aid Foundation of Los Angeles (LAFLA)",
            "slug": "lafla",
            "provider_type": ProviderType.legal_aid,
            "description": "Free civil legal services for low-income residents of Los Angeles County.",
            "services": [
                {"service": "Housing Law", "description": "Eviction defense and habitability issues"},
                {"service": "Family Law", "description": "Domestic violence, divorce, custody"},
                {"service": "Consumer Law", "description": "Debt collection defense"},
            ],
            "eligibility_criteria": "Must meet income guidelines (generally at or below 125% of federal poverty level)",
            "income_limit_percentage": 125,
            "phone": "800-399-4529",
            "website": "https://lafla.org/",
            "address_line1": "1102 S Crenshaw Blvd",
            "city": "Los Angeles",
            "state": "CA",
            "zip_code": "90019",
            "languages_spoken": ["English", "Spanish", "Korean", "Vietnamese", "Tagalog"],
            "accepts_walkins": False,
            "appointment_required": True,
            "wheelchair_accessible": True,
            "virtual_services": True,
            "special_populations": ["Domestic Violence Survivors", "Seniors", "Veterans"],
            "is_active": True,
            "is_verified": True,
        },
        {
            "name": "Neighborhood Legal Services of Los Angeles County",
            "slug": "nlsla",
            "provider_type": ProviderType.legal_aid,
            "description": "Free legal services for low-income residents in housing, consumer, and public benefits matters.",
            "services": [
                {"service": "Housing", "description": "Eviction defense and tenant rights"},
                {"service": "Consumer Rights", "description": "Debt and consumer protection"},
                {"service": "Public Benefits", "description": "SSI, SSDI, CalWORKs appeals"},
            ],
            "eligibility_criteria": "Low-income residents of LA County",
            "income_limit_percentage": 125,
            "phone": "800-433-6251",
            "website": "https://nlsla.org/",
            "address_line1": "13327 Van Nuys Blvd",
            "city": "Pacoima",
            "state": "CA",
            "zip_code": "91331",
            "languages_spoken": ["English", "Spanish", "Armenian"],
            "accepts_walkins": True,
            "appointment_required": False,
            "wheelchair_accessible": True,
            "virtual_services": True,
            "is_active": True,
            "is_verified": True,
        },
    ]

    for provider_data in providers_data:
        # Check if provider exists
        result = await db.execute(
            select(LegalServiceProvider).where(
                LegalServiceProvider.slug == provider_data["slug"]
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            provider = LegalServiceProvider(
                **provider_data,
                created_by_id=admin_id,
                verified_at=utc_now()
            )
            db.add(provider)
            print(f"  Created provider: {provider_data['name']}")
        else:
            print(f"  Provider already exists: {provider_data['name']}")

    await db.commit()


async def seed_lasc_forms(db: AsyncSession, topic_map: dict, admin_id: int):
    """Create LASC (LA Superior Court) common forms."""
    print("Seeding LASC common forms...")

    forms_data = [
        {
            "title": "Petition for Dissolution (Divorce) of Marriage",
            "form_number": "FL-100",
            "plain_language_title": "Divorce Petition",
            "topic_id": topic_map.get("family"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Superior Court",
            "description": "This form starts the legal process of ending your marriage or domestic partnership.",
            "when_to_use": "Use this form when you want to file for divorce or legal separation in California.",
            "who_should_use": "Either spouse/partner who wants to end the marriage or domestic partnership",
            "url": "https://www.courts.ca.gov/documents/fl100.pdf",
            "instructions_url": "https://www.courts.ca.gov/1282.htm",
            "difficulty_level": FormDifficulty.complex,
            "estimated_completion_time": 60,
            "filing_fee": 435.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish", "Chinese", "Korean", "Vietnamese"],
            "fillable_pdf": True,
            "page_count": 2,
        },
        {
            "title": "Response to Petition for Dissolution",
            "form_number": "FL-120",
            "plain_language_title": "Divorce Response",
            "topic_id": topic_map.get("family"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Superior Court",
            "description": "This form is your official response to a divorce or legal separation petition.",
            "when_to_use": "Use this form when your spouse has filed for divorce and you've been served with papers.",
            "who_should_use": "The person who was served with divorce papers (the Respondent)",
            "url": "https://www.courts.ca.gov/documents/fl120.pdf",
            "instructions_url": "https://www.courts.ca.gov/1282.htm",
            "difficulty_level": FormDifficulty.complex,
            "estimated_completion_time": 45,
            "filing_fee": 435.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish", "Chinese", "Korean", "Vietnamese"],
            "fillable_pdf": True,
            "page_count": 2,
        },
        {
            "title": "Request for Domestic Violence Restraining Order",
            "form_number": "DV-100",
            "plain_language_title": "Domestic Violence Restraining Order Request",
            "topic_id": topic_map.get("family"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Superior Court",
            "description": "Request court protection from abuse by a spouse, partner, or family member.",
            "when_to_use": "Use when you need legal protection from domestic violence, abuse, or threats.",
            "who_should_use": "Anyone experiencing abuse from a spouse, partner, or close family member",
            "url": "https://www.courts.ca.gov/documents/dv100.pdf",
            "instructions_url": "https://www.courts.ca.gov/1260.htm",
            "difficulty_level": FormDifficulty.moderate,
            "estimated_completion_time": 30,
            "filing_fee": 0.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish", "Chinese", "Korean", "Vietnamese", "Tagalog"],
            "fillable_pdf": True,
            "page_count": 6,
        },
        {
            "title": "Complaint - Unlawful Detainer (Eviction)",
            "form_number": "UD-100",
            "plain_language_title": "Eviction Answer",
            "topic_id": topic_map.get("housing"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Superior Court",
            "description": "This is the form landlords use to start an eviction case.",
            "when_to_use": "You'll receive this if your landlord is trying to evict you. You need to respond within 5 days.",
            "who_should_use": "Tenants who have been served with an eviction lawsuit",
            "url": "https://www.courts.ca.gov/documents/ud100.pdf",
            "instructions_url": "https://selfhelp.courts.ca.gov/eviction",
            "difficulty_level": FormDifficulty.complex,
            "estimated_completion_time": 40,
            "filing_fee": 225.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish"],
            "fillable_pdf": True,
            "page_count": 2,
        },
        {
            "title": "Answer - Unlawful Detainer",
            "form_number": "UD-105",
            "plain_language_title": "Eviction Response",
            "topic_id": topic_map.get("housing"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Superior Court",
            "description": "Your response to an eviction lawsuit. Must be filed within 5 calendar days.",
            "when_to_use": "Use this form to respond to an eviction (unlawful detainer) lawsuit.",
            "who_should_use": "Tenants defending against eviction",
            "url": "https://www.courts.ca.gov/documents/ud105.pdf",
            "instructions_url": "https://selfhelp.courts.ca.gov/eviction/file-answer",
            "difficulty_level": FormDifficulty.complex,
            "estimated_completion_time": 45,
            "filing_fee": 0.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish"],
            "fillable_pdf": True,
            "page_count": 2,
        },
        {
            "title": "Small Claims Plaintiff's Claim",
            "form_number": "SC-100",
            "plain_language_title": "Sue in Small Claims Court",
            "topic_id": topic_map.get("small-claims"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Small Claims",
            "description": "Start a small claims case to collect money owed to you (up to $10,000).",
            "when_to_use": "Use when someone owes you $10,000 or less and won't pay.",
            "who_should_use": "Anyone suing for $10,000 or less",
            "url": "https://www.courts.ca.gov/documents/sc100.pdf",
            "instructions_url": "https://www.courts.ca.gov/selfhelp-smallclaims.htm",
            "difficulty_level": FormDifficulty.moderate,
            "estimated_completion_time": 20,
            "filing_fee": 75.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish", "Chinese"],
            "fillable_pdf": True,
            "page_count": 1,
        },
        {
            "title": "Small Claims Defendant's Claim",
            "form_number": "SC-120",
            "plain_language_title": "Respond to Small Claims",
            "topic_id": topic_map.get("small-claims"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Small Claims",
            "description": "File a counterclaim against the person suing you in small claims court.",
            "when_to_use": "Use if you've been sued in small claims and you want to sue them back.",
            "who_should_use": "Small claims defendants filing a counterclaim",
            "url": "https://www.courts.ca.gov/documents/sc120.pdf",
            "instructions_url": "https://www.courts.ca.gov/selfhelp-smallclaims.htm",
            "difficulty_level": FormDifficulty.moderate,
            "estimated_completion_time": 20,
            "filing_fee": 0.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish", "Chinese"],
            "fillable_pdf": True,
            "page_count": 1,
        },
        {
            "title": "Petition for Change of Name",
            "form_number": "NC-100",
            "plain_language_title": "Name Change Petition",
            "topic_id": topic_map.get("name-change"),
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "Superior Court",
            "description": "Petition the court to legally change your name.",
            "when_to_use": "Use when you want to change your legal name (adult or child).",
            "who_should_use": "Adults changing their own name, or parents changing a child's name",
            "url": "https://www.courts.ca.gov/documents/nc100.pdf",
            "instructions_url": "https://www.courts.ca.gov/selfhelp-namechange.htm",
            "difficulty_level": FormDifficulty.moderate,
            "estimated_completion_time": 25,
            "filing_fee": 435.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish"],
            "fillable_pdf": True,
            "page_count": 2,
        },
        {
            "title": "Fee Waiver Request",
            "form_number": "FW-001",
            "plain_language_title": "Request to Waive Court Fees",
            "topic_id": None,
            "jurisdiction": "California",
            "jurisdiction_code": "CA",
            "court_type": "All Courts",
            "description": "Request that the court waive your filing fees if you can't afford them.",
            "when_to_use": "Use when you can't afford court filing fees and meet income guidelines.",
            "who_should_use": "Anyone who can't afford court fees (receives public benefits or low income)",
            "url": "https://www.courts.ca.gov/documents/fw001.pdf",
            "instructions_url": "https://www.courts.ca.gov/selfhelp-feewaiver.htm",
            "difficulty_level": FormDifficulty.moderate,
            "estimated_completion_time": 30,
            "filing_fee": 0.00,
            "status": FormStatus.active,
            "languages_available": ["English", "Spanish", "Chinese", "Korean", "Vietnamese"],
            "fillable_pdf": True,
            "page_count": 5,
        },
    ]

    for form_data in forms_data:
        # Check if form exists
        result = await db.execute(
            select(LegalForm).where(LegalForm.form_number == form_data["form_number"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            form = LegalForm(
                **form_data,
                created_by_id=admin_id,
                effective_date=date.today(),
                last_updated=date.today(),
            )
            db.add(form)
            print(f"  Created form: {form_data['form_number']} - {form_data['plain_language_title']}")
        else:
            print(f"  Form already exists: {form_data['form_number']}")

    await db.commit()


async def seed_legal_guides(db: AsyncSession, topic_map: dict, admin_id: int):
    """Create helpful legal guides."""
    print("Seeding legal guides...")

    guides_data = [
        {
            "title": "How to File for Divorce in California",
            "slug": "how-to-file-divorce-california",
            "topic_id": topic_map.get("family"),
            "summary": "Step-by-step guide to filing for divorce in California, including required forms, fees, and timeline.",
            "content": """
# How to File for Divorce in California

## Overview
Filing for divorce in California is a legal process that typically takes at least 6 months. This guide walks you through the basic steps.

## Step 1: Determine Eligibility
- You or your spouse must have lived in California for at least 6 months
- You must have lived in the county where you're filing for at least 3 months

## Step 2: Gather Information
Before filing, collect:
- Marriage certificate
- Financial documents (bank statements, pay stubs, tax returns)
- List of all assets and debts
- Information about children (if applicable)

## Step 3: Complete the Forms
Required forms:
- FL-100: Petition for Dissolution
- FL-110: Summons
- FL-160: Property Declaration (if applicable)

## Step 4: File with the Court
- File at your county's Superior Court
- Pay filing fee ($435) or request fee waiver (FW-001)
- Get copies of filed documents

## Step 5: Serve Your Spouse
- Have someone over 18 (not you) serve your spouse
- Complete proof of service form

## Step 6: Wait for Response
- Spouse has 30 days to respond
- If no response, you may get a default judgment

## Timeline
The entire process takes at least 6 months from the date of service.
""",
            "reading_level": GuideReadingLevel.high_school,
            "is_published": True,
            "is_featured": True,
        },
        {
            "title": "Defending Against an Eviction",
            "slug": "defending-eviction",
            "topic_id": topic_map.get("housing"),
            "summary": "Your rights as a tenant facing eviction and how to respond to an unlawful detainer lawsuit.",
            "content": """
# Defending Against an Eviction

## You Have Rights
If you've received an eviction notice, don't panic. You have legal rights and options.

## Types of Eviction Notices
1. **3-Day Notice to Pay or Quit** - For unpaid rent
2. **3-Day Notice to Cure or Quit** - For lease violations
3. **30/60/90-Day Notice** - To end month-to-month tenancy

## Timeline is Critical
- You have only **5 CALENDAR DAYS** to respond to an unlawful detainer (eviction lawsuit)
- File your Answer (UD-105) immediately
- Don't wait to get legal help

## Common Defenses
- Landlord didn't give proper notice
- You paid the rent
- Landlord didn't maintain the property (habitability)
- Retaliation for complaining about repairs
- Discrimination

## Get Help
Contact a legal aid organization immediately. Free help is available for low-income tenants.
""",
            "reading_level": GuideReadingLevel.middle_school,
            "is_published": True,
            "is_featured": True,
        },
    ]

    for guide_data in guides_data:
        # Check if guide exists
        result = await db.execute(
            select(LegalGuide).where(LegalGuide.slug == guide_data["slug"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            guide = LegalGuide(
                **guide_data,
                created_by_id=admin_id,
                published_at=utc_now() if guide_data.get("is_published") else None,
            )
            db.add(guide)
            print(f"  Created guide: {guide_data['title']}")
        else:
            print(f"  Guide already exists: {guide_data['title']}")

    await db.commit()


async def seed_glossary_terms(db: AsyncSession, topic_map: dict):
    """Create legal glossary terms."""
    print("Seeding legal glossary terms...")

    terms_data = [
        {
            "term": "Plaintiff",
            "slug": "plaintiff",
            "definition_simple": "The person who starts a court case by suing someone else.",
            "definition_standard": "The party who initiates a lawsuit by filing a complaint with the court, alleging that the defendant has caused them harm or violated their rights.",
            "definition_legal": "The party who brings a civil action or suit against another in a court of law.",
            "pronunciation": "PLAYN-tiff",
            "related_term_slugs": ["defendant", "complaint", "petitioner"],
            "usage_example": "Maria was the plaintiff in the small claims case because she filed the lawsuit to recover her security deposit.",
            "context_notes": "Used in civil cases. In family law, the equivalent term is 'petitioner'.",
            "translations": {"es": "Demandante", "zh": "原告"},
            "topic_ids": [],
        },
        {
            "term": "Defendant",
            "slug": "defendant",
            "definition_simple": "The person who is being sued or accused in a court case.",
            "definition_standard": "The party against whom a lawsuit is filed or who is accused of a crime in a criminal proceeding.",
            "definition_legal": "The party against whom relief or recovery is sought in an action or suit, or the accused in a criminal case.",
            "pronunciation": "dih-FEN-dunt",
            "related_term_slugs": ["plaintiff", "respondent"],
            "usage_example": "The landlord was named as the defendant in the tenant's habitability lawsuit.",
            "context_notes": "Used in both civil and criminal cases. In family law, the equivalent term is 'respondent'.",
            "translations": {"es": "Demandado", "zh": "被告"},
            "topic_ids": [],
        },
        {
            "term": "Petitioner",
            "slug": "petitioner",
            "definition_simple": "The person who asks the court for something, like a divorce or restraining order.",
            "definition_standard": "The party who files a petition with the court requesting judicial action, commonly used in family law and certain civil proceedings.",
            "definition_legal": "The party presenting a petition to the court; the party who initiates an equity proceeding or who takes an appeal from a judgment.",
            "pronunciation": "peh-TIH-shun-er",
            "related_term_slugs": ["respondent", "plaintiff"],
            "usage_example": "She was the petitioner in the divorce case because she filed the paperwork first.",
            "context_notes": "Used primarily in family law cases instead of 'plaintiff'.",
            "translations": {"es": "Peticionario", "zh": "申请人"},
            "topic_ids": list(filter(None, [topic_map.get("family")])),
        },
        {
            "term": "Respondent",
            "slug": "respondent",
            "definition_simple": "The person who responds to a petition filed in court.",
            "definition_standard": "The party who is required to answer a petition filed in court, commonly used in family law proceedings as the counterpart to the petitioner.",
            "definition_legal": "The party against whom a petition is filed, especially in family law or appellate proceedings.",
            "pronunciation": "rih-SPON-dunt",
            "related_term_slugs": ["petitioner", "defendant"],
            "usage_example": "Her husband was the respondent in the divorce case because she filed first.",
            "context_notes": "Used in family law instead of 'defendant'.",
            "translations": {"es": "Demandado", "zh": "被申请人"},
            "topic_ids": list(filter(None, [topic_map.get("family")])),
        },
        {
            "term": "Unlawful Detainer",
            "slug": "unlawful-detainer",
            "definition_simple": "The legal name for an eviction lawsuit.",
            "definition_standard": "A legal action filed by a landlord to evict a tenant who remains on the property after the right to occupy has ended, such as after a lease expires or proper notice has been given.",
            "definition_legal": "A summary proceeding to recover possession of real property from one who holds possession without right, typically a tenant who has defaulted on rent or violated lease terms.",
            "pronunciation": "un-LAW-ful dih-TAY-ner",
            "related_term_slugs": ["eviction", "complaint", "defendant"],
            "usage_example": "The landlord filed an unlawful detainer action after the tenant did not pay rent for two months.",
            "context_notes": "This is the formal legal term for eviction in California courts.",
            "translations": {"es": "Retención ilegal", "zh": "非法扣留"},
            "topic_ids": list(filter(None, [topic_map.get("housing")])),
        },
        {
            "term": "Eviction",
            "slug": "eviction",
            "definition_simple": "When a landlord forces a tenant to move out through a court order.",
            "definition_standard": "The legal process by which a landlord removes a tenant from a rental property, typically through a court action known as an unlawful detainer.",
            "definition_legal": "The act of depriving a person of possession of lands or tenements held or occupied by that person, pursuant to a lawful court order.",
            "pronunciation": "ih-VIK-shun",
            "related_term_slugs": ["unlawful-detainer", "tenant", "landlord"],
            "usage_example": "The eviction process in California requires the landlord to give proper written notice before filing a lawsuit.",
            "context_notes": "California law requires specific notices before an eviction can be filed in court.",
            "translations": {"es": "Desalojo", "zh": "驱逐"},
            "topic_ids": list(filter(None, [topic_map.get("housing")])),
        },
        {
            "term": "Complaint",
            "slug": "complaint",
            "definition_simple": "The first paper filed in a lawsuit that explains what happened and what you want the court to do.",
            "definition_standard": "The initial document filed by the plaintiff to begin a civil lawsuit, stating the facts of the case and the legal basis for the claim.",
            "definition_legal": "The initial pleading that sets forth a claim for relief by stating the grounds upon which the court's jurisdiction depends, the plaintiff's claim, and the demand for judgment.",
            "pronunciation": "kum-PLAYNT",
            "related_term_slugs": ["plaintiff", "defendant", "petition"],
            "usage_example": "The attorney helped draft a complaint alleging that the contractor failed to complete the work as agreed.",
            "context_notes": "In family law cases, the equivalent document is called a 'petition'.",
            "translations": {"es": "Demanda", "zh": "诉状"},
            "topic_ids": [],
        },
        {
            "term": "Filing Fee",
            "slug": "filing-fee",
            "definition_simple": "The money you pay the court when you file papers.",
            "definition_standard": "A fee charged by the court when documents are filed, such as a complaint or petition. Fee waivers are available for those who cannot afford to pay.",
            "definition_legal": "The statutory fee required by the clerk of court for the filing of legal documents and the commencement of legal proceedings.",
            "pronunciation": "FY-ling fee",
            "related_term_slugs": ["fee-waiver", "complaint", "petition"],
            "usage_example": "The filing fee for a divorce petition in California is $435, but you can apply for a fee waiver if you can't afford it.",
            "context_notes": "Fee waivers are available for low-income individuals. Use form FW-001 in California.",
            "translations": {"es": "Tarifa de presentación", "zh": "申请费"},
            "topic_ids": [],
        },
        {
            "term": "Fee Waiver",
            "slug": "fee-waiver",
            "definition_simple": "A court order that says you don't have to pay court fees because you can't afford them.",
            "definition_standard": "A court-granted exemption from paying filing fees and other court costs for individuals who demonstrate financial hardship.",
            "definition_legal": "An order by the court excusing a party from payment of court fees and costs based on a showing of indigency or financial inability to pay.",
            "pronunciation": "fee WAY-ver",
            "related_term_slugs": ["filing-fee"],
            "usage_example": "She applied for a fee waiver using form FW-001 because her income was below the poverty level.",
            "context_notes": "In California, you may qualify if you receive public benefits, your income is at or below 125% of the federal poverty level, or you cannot pay basic living expenses.",
            "translations": {"es": "Exención de tarifas", "zh": "费用减免"},
            "topic_ids": [],
        },
        {
            "term": "Restraining Order",
            "slug": "restraining-order",
            "definition_simple": "A court order that tells someone to stay away from you and not contact you.",
            "definition_standard": "A court order that prohibits a person from engaging in specific conduct, such as contacting or coming near another person, designed to protect victims of harassment, abuse, or threats.",
            "definition_legal": "An order issued by a court of competent jurisdiction directing a party to refrain from certain acts, including but not limited to contact, harassment, and proximity to the protected party.",
            "pronunciation": "rih-STRAY-ning OR-der",
            "related_term_slugs": ["petitioner", "respondent"],
            "usage_example": "She obtained a domestic violence restraining order after her ex-partner threatened her.",
            "context_notes": "In California, there are several types: domestic violence (DV), civil harassment (CH), elder abuse (EA), and workplace violence (WV).",
            "translations": {"es": "Orden de restricción", "zh": "禁制令"},
            "topic_ids": list(filter(None, [topic_map.get("family")])),
        },
        {
            "term": "Service of Process",
            "slug": "service-of-process",
            "definition_simple": "Officially giving court papers to the other person in your case.",
            "definition_standard": "The formal delivery of legal documents (such as a complaint or summons) to the opposing party, notifying them of the legal action and giving them an opportunity to respond.",
            "definition_legal": "The procedure by which a party to a suit gives appropriate notice to the opposing party by delivering formal documents according to the prescribed rules of court.",
            "pronunciation": "SER-vis of PRAH-ses",
            "related_term_slugs": ["complaint", "summons"],
            "usage_example": "Service of process must be completed by someone over 18 who is not a party to the case.",
            "context_notes": "You cannot serve papers on someone yourself. A friend, process server, or sheriff can do it for you.",
            "translations": {"es": "Notificación judicial", "zh": "送达程序"},
            "topic_ids": [],
        },
        {
            "term": "Continuance",
            "slug": "continuance",
            "definition_simple": "Postponing a court date to a later time.",
            "definition_standard": "A postponement or adjournment of a scheduled court hearing or trial to a future date, which may be requested by either party or ordered by the court.",
            "definition_legal": "The adjournment or postponement of an action pending in a court to a subsequent day of the same or another term.",
            "pronunciation": "kun-TIN-yoo-uns",
            "related_term_slugs": [],
            "usage_example": "The judge granted a continuance so the defendant could have more time to find an attorney.",
            "context_notes": "Courts may grant or deny continuance requests. Having a good reason increases the chance of approval.",
            "translations": {"es": "Aplazamiento", "zh": "延期"},
            "topic_ids": [],
        },
    ]

    for term_data in terms_data:
        result = await db.execute(
            select(LegalGlossaryTerm).where(LegalGlossaryTerm.slug == term_data["slug"])
        )
        existing = result.scalar_one_or_none()

        if not existing:
            term = LegalGlossaryTerm(**term_data, is_active=True)
            db.add(term)
            print(f"  Created glossary term: {term_data['term']}")
        else:
            print(f"  Glossary term already exists: {term_data['term']}")

    await db.commit()


async def seed_legal_clinics(db: AsyncSession, topic_map: dict, admin_id: int) -> list:
    """Create upcoming legal clinic schedules."""
    print("Seeding legal clinic schedules...")

    # Get provider IDs for clinic associations
    result = await db.execute(
        select(LegalServiceProvider).where(LegalServiceProvider.slug == "lafla")
    )
    lafla = result.scalar_one_or_none()
    lafla_id = lafla.id if lafla else None

    result = await db.execute(
        select(LegalServiceProvider).where(LegalServiceProvider.slug == "nlsla")
    )
    nlsla = result.scalar_one_or_none()
    nlsla_id = nlsla.id if nlsla else None

    result = await db.execute(
        select(LegalServiceProvider).where(LegalServiceProvider.slug == "la-county-law-library")
    )
    law_library = result.scalar_one_or_none()
    law_library_id = law_library.id if law_library else None

    # Schedule clinics in the upcoming weeks
    today = date.today()
    next_saturday = today + timedelta(days=(5 - today.weekday()) % 7 or 7)

    clinics_data = [
        {
            "name": "Eviction Defense Workshop",
            "topic_id": topic_map.get("housing"),
            "description": "Free workshop for tenants facing eviction. Attorneys will help you understand your rights and fill out response forms.",
            "provider_id": lafla_id,
            "date": next_saturday,
            "start_time": "10:00",
            "end_time": "13:00",
            "timezone": "America/Los_Angeles",
            "is_virtual": False,
            "location": "LA County Law Library - Main Branch, Meeting Room A, 301 W 1st Street, Los Angeles, CA 90012",
            "capacity": 25,
            "current_registrations": 8,
            "registration_required": True,
            "eligibility_notes": "Open to all LA County tenants facing eviction. No income requirement for workshop attendance.",
            "what_to_bring": [
                {"item": "Eviction notice or court papers", "required": True},
                {"item": "Photo ID", "required": True},
                {"item": "Lease or rental agreement", "required": False},
                {"item": "Rent payment receipts", "required": False},
            ],
            "languages_available": ["English", "Spanish"],
            "interpreter_available": True,
            "wheelchair_accessible": True,
            "attorney_names": ["Maria Garcia, Esq.", "James Chen, Esq."],
            "volunteer_count": 3,
            "status": ClinicStatus.registration_open,
            "public_notes": "Walk-ins welcome if space is available. Priority given to registered attendees.",
        },
        {
            "name": "Family Law Self-Help Clinic",
            "topic_id": topic_map.get("family"),
            "description": "Get help with divorce, custody, child support, and domestic violence restraining orders from volunteer attorneys.",
            "provider_id": lafla_id,
            "date": next_saturday + timedelta(days=7),
            "start_time": "09:00",
            "end_time": "12:00",
            "timezone": "America/Los_Angeles",
            "is_virtual": True,
            "virtual_link": "https://zoom.us/j/example",
            "virtual_platform": "Zoom",
            "capacity": 20,
            "current_registrations": 5,
            "registration_required": True,
            "eligibility_notes": "Open to low-income LA County residents. Income verification may be required for full representation.",
            "what_to_bring": [
                {"item": "Any court documents you have received", "required": True},
                {"item": "Financial information (pay stubs, tax returns)", "required": False},
                {"item": "Children's birth certificates", "required": False},
            ],
            "languages_available": ["English", "Spanish", "Korean"],
            "interpreter_available": True,
            "wheelchair_accessible": True,
            "asl_interpreter": True,
            "attorney_names": ["Patricia Reyes, Esq."],
            "volunteer_count": 4,
            "status": ClinicStatus.registration_open,
            "public_notes": "Virtual clinic via Zoom. Link will be emailed to registered participants.",
        },
        {
            "name": "Small Claims Court Preparation",
            "topic_id": topic_map.get("small-claims"),
            "description": "Learn how to prepare and present your small claims case. Covers filing, serving papers, and what to expect in court.",
            "provider_id": law_library_id,
            "date": next_saturday + timedelta(days=14),
            "start_time": "14:00",
            "end_time": "16:00",
            "timezone": "America/Los_Angeles",
            "is_virtual": False,
            "location": "LA County Law Library - Main Branch, Conference Room B, 301 W 1st Street, Los Angeles, CA 90012",
            "capacity": 30,
            "current_registrations": 12,
            "registration_required": False,
            "eligibility_notes": "Open to the public. No income requirement.",
            "what_to_bring": [
                {"item": "Any contracts or agreements related to your dispute", "required": False},
                {"item": "Evidence (photos, receipts, text messages)", "required": False},
            ],
            "languages_available": ["English"],
            "interpreter_available": False,
            "wheelchair_accessible": True,
            "attorney_names": [],
            "volunteer_count": 2,
            "status": ClinicStatus.registration_open,
            "public_notes": "No registration required. First come, first served.",
        },
        {
            "name": "Immigration Rights Know Your Rights Session",
            "topic_id": topic_map.get("immigration"),
            "description": "Know your rights regarding immigration enforcement. Learn what to do if ICE comes to your door, your workplace, or stops you.",
            "provider_id": nlsla_id,
            "date": next_saturday + timedelta(days=21),
            "start_time": "18:00",
            "end_time": "20:00",
            "timezone": "America/Los_Angeles",
            "is_virtual": True,
            "virtual_link": "https://teams.microsoft.com/example",
            "virtual_platform": "Microsoft Teams",
            "capacity": 50,
            "current_registrations": 15,
            "registration_required": True,
            "eligibility_notes": "Open to all community members regardless of immigration status.",
            "what_to_bring": [],
            "languages_available": ["English", "Spanish"],
            "interpreter_available": True,
            "wheelchair_accessible": True,
            "attorney_names": ["Roberto Alvarez, Esq.", "Linda Park, Esq."],
            "volunteer_count": 5,
            "status": ClinicStatus.registration_open,
            "public_notes": "This is an educational session only. Individual legal advice will not be provided.",
        },
        {
            "name": "Name Change Petition Workshop",
            "topic_id": topic_map.get("name-change"),
            "description": "Step-by-step assistance with completing name change petition forms. Attorneys available for questions.",
            "provider_id": law_library_id,
            "date": next_saturday + timedelta(days=28),
            "start_time": "10:00",
            "end_time": "12:00",
            "timezone": "America/Los_Angeles",
            "is_virtual": False,
            "location": "LA County Law Library - Torrance Branch, 825 Maple Ave, Torrance, CA 90503",
            "capacity": 15,
            "current_registrations": 3,
            "registration_required": True,
            "eligibility_notes": "Open to all. Especially helpful for those seeking adult name change or gender marker change.",
            "what_to_bring": [
                {"item": "Photo ID", "required": True},
                {"item": "Birth certificate", "required": False},
                {"item": "Filing fee ($435) or fee waiver form FW-001", "required": True},
            ],
            "languages_available": ["English", "Spanish"],
            "interpreter_available": False,
            "wheelchair_accessible": True,
            "attorney_names": ["Sarah Kim, Esq."],
            "volunteer_count": 2,
            "status": ClinicStatus.scheduled,
            "public_notes": "Registration opens one week before the event.",
        },
    ]

    clinic_ids = []
    for clinic_data in clinics_data:
        result = await db.execute(
            select(LegalClinic).where(
                LegalClinic.name == clinic_data["name"],
                LegalClinic.date == clinic_data["date"]
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            clinic = LegalClinic(
                **clinic_data,
                created_by_id=admin_id,
            )
            db.add(clinic)
            await db.flush()
            clinic_ids.append(clinic.id)
            print(f"  Created clinic: {clinic_data['name']} ({clinic_data['date']})")
        else:
            clinic_ids.append(existing.id)
            print(f"  Clinic already exists: {clinic_data['name']}")

    await db.commit()
    return clinic_ids


async def seed_clinic_registrations(db: AsyncSession, clinic_ids: list):
    """Create sample clinic registrations.

    Gracefully handles the case where the legal_clinic_registrations table
    does not yet exist (e.g., migration pending from another agent).
    """
    print("Seeding clinic registrations...")

    if not clinic_ids:
        print("  No clinics available for registrations.")
        return

    # Sample registrations for the first clinic (Eviction Defense Workshop)
    first_clinic_id = clinic_ids[0]

    registrations_data = [
        {
            "clinic_id": first_clinic_id,
            "name": "Ana Rodriguez",
            "email": "ana.r@example.com",
            "phone": "213-555-0101",
            "preferred_contact": "email",
            "status": RegistrationStatus.confirmed,
            "language_preference": "Spanish",
            "interpreter_needed": True,
            "issue_description": "Received 3-day notice to pay or quit. Need help understanding my options.",
            "confirmation_sent": True,
        },
        {
            "clinic_id": first_clinic_id,
            "name": "David Chen",
            "email": "d.chen@example.com",
            "preferred_contact": "email",
            "status": RegistrationStatus.confirmed,
            "language_preference": "English",
            "interpreter_needed": False,
            "issue_description": "Landlord is trying to evict me after I complained about mold in the apartment.",
            "confirmation_sent": True,
        },
        {
            "clinic_id": first_clinic_id,
            "name": "Maria Santos",
            "phone": "818-555-0202",
            "preferred_contact": "phone",
            "status": RegistrationStatus.pending,
            "language_preference": "Spanish",
            "interpreter_needed": True,
            "issue_description": "Received eviction papers but I don't understand them.",
            "confirmation_sent": False,
        },
    ]

    # Add registrations for the second clinic (Family Law) if available
    if len(clinic_ids) > 1:
        second_clinic_id = clinic_ids[1]
        registrations_data.extend([
            {
                "clinic_id": second_clinic_id,
                "name": "Jennifer Park",
                "email": "j.park@example.com",
                "preferred_contact": "email",
                "status": RegistrationStatus.confirmed,
                "language_preference": "English",
                "interpreter_needed": False,
                "issue_description": "Need help filing for divorce. Married 5 years, no children.",
                "confirmation_sent": True,
            },
            {
                "clinic_id": second_clinic_id,
                "name": "Carlos Mendez",
                "email": "c.mendez@example.com",
                "phone": "323-555-0303",
                "preferred_contact": "phone",
                "status": RegistrationStatus.confirmed,
                "language_preference": "Spanish",
                "interpreter_needed": True,
                "issue_description": "Need help with child custody modification.",
                "confirmation_sent": True,
            },
        ])

    for reg_data in registrations_data:
        # Check if registration already exists (by name + clinic_id)
        result = await db.execute(
            select(LegalClinicRegistration).where(
                LegalClinicRegistration.clinic_id == reg_data["clinic_id"],
                LegalClinicRegistration.name == reg_data["name"]
            )
        )
        existing = result.scalar_one_or_none()

        if not existing:
            registration = LegalClinicRegistration(**reg_data)
            db.add(registration)
            print(f"  Created registration: {reg_data['name']}")
        else:
            print(f"  Registration already exists: {reg_data['name']}")

    await db.commit()


async def main():
    """Main seed function."""
    print("=" * 60)
    print("Seeding Legal Resources with LA County Data")
    print("=" * 60)

    async with AsyncSessionLocal() as db:
        try:
            # Check if legal tables exist before proceeding
            from sqlalchemy import text as sa_text
            try:
                await db.execute(sa_text("SELECT 1 FROM legal_topics LIMIT 0"))
            except Exception:
                await db.rollback()
                print("  ⏭️  Legal tables not yet created, skipping")
                return
            # Get admin user
            admin = await get_or_create_admin_user(db)
            if not admin:
                print("ERROR: No admin user found. Please create an admin user first.")
                return

            admin_id = admin.id
            print(f"Using admin user: {admin.email}\n")

            # Seed in order
            topic_map = await seed_legal_topics(db, admin_id)
            await seed_la_county_providers(db, topic_map, admin_id)
            await seed_lasc_forms(db, topic_map, admin_id)
            await seed_legal_guides(db, topic_map, admin_id)
            await seed_glossary_terms(db, topic_map)
            clinic_ids = await seed_legal_clinics(db, topic_map, admin_id)

            # Clinic registrations may fail if the table doesn't exist yet
            # (migration may be pending from another agent)
            try:
                await seed_clinic_registrations(db, clinic_ids)
            except ProgrammingError as e:
                if "does not exist" in str(e):
                    await db.rollback()
                    print("  SKIPPED clinic registrations: table does not exist yet (migration pending)")
                    print("  Re-run this script after the legal_clinic_registrations migration is applied.")
                else:
                    raise

            print("\n" + "=" * 60)
            print("Legal resources seeded successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"\nERROR during seeding: {e}")
            import traceback
            traceback.print_exc()
            await db.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(main())
