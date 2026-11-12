# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Material Cost Comparison API - Transparency Tool

Provides factual cost breakdowns for different library material formats.
This is a public endpoint designed to help patrons understand the economics
of library materials without bias.

Data sources:
- American Library Association cost surveys
- Publisher pricing data
- Library Journal budget reports
- Internal acquisition records (anonymized)
"""

from decimal import Decimal
from fastapi import APIRouter

from app.schemas.material_cost import (
    CostFactor,
    MaterialFormatCosts,
    CostComparisonCategory,
    MaterialCostComparisonResponse,
    CostComparisonSummary,
)

router = APIRouter(prefix="/material-costs", tags=["transparency"])


def get_cost_comparison_data() -> MaterialCostComparisonResponse:
    return MaterialCostComparisonResponse(
        last_updated="2024-01",
        data_sources=[
            "American Library Association - Library Materials Price Index",
            "Library Journal - Periodicals Price Survey",
            "Publishers Weekly - Book Publishing Statistics",
            "Palace Project Usage Reports",
            "Public Library Association - Technology Survey",
        ],
        methodology_note=(
            "Cost estimates represent typical ranges for public libraries. "
            "Actual costs vary by vendor, licensing terms, consortium membership, "
            "and regional factors. All figures are educational estimates, not "
            "guarantees. Processing costs include cataloging, labeling, and "
            "shelf preparation. Storage costs are annualized estimates."
        ),
        categories=[
            # BOOKS CATEGORY
            CostComparisonCategory(
                category_name="Books",
                category_description="Print and digital book formats",
                formats=[
                    MaterialFormatCosts(
                        format_type="print_book",
                        format_name="Print Book (Hardcover)",
                        description="Traditional physical hardcover book",
                        acquisition_cost=CostFactor(
                            name="Purchase Price",
                            description="Wholesale cost from distributors (typically 40-50% off list price)",
                            low_estimate=Decimal("12.00"),
                            high_estimate=Decimal("35.00"),
                            unit="per copy",
                            notes="Library editions may cost more due to reinforced bindings"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Cataloging, spine labels, RFID tags, protective covers",
                            low_estimate=Decimal("3.50"),
                            high_estimate=Decimal("8.00"),
                            unit="per copy",
                            notes="Includes staff time for cataloging"
                        ),
                        storage_cost=CostFactor(
                            name="Shelf Space",
                            description="Physical shelf space, climate control, facility costs",
                            low_estimate=Decimal("0.50"),
                            high_estimate=Decimal("2.00"),
                            unit="per year",
                            notes="Based on square footage allocation"
                        ),
                        maintenance_cost=CostFactor(
                            name="Repairs & Binding",
                            description="Mending, rebinding, and eventual replacement",
                            low_estimate=Decimal("0.25"),
                            high_estimate=Decimal("1.50"),
                            unit="per year",
                            notes="Varies greatly by circulation volume"
                        ),
                        typical_lifespan_years=10,
                        simultaneous_users="1",
                        environmental_notes="Paper production, printing, shipping. Can be recycled or donated at end of life.",
                        advantages=[
                            "No special equipment needed to read",
                            "No ongoing licensing fees after purchase",
                            "Can be repaired and rebound",
                            "Owned permanently by the library",
                            "Works during power outages",
                            "No internet connection required",
                        ],
                        limitations=[
                            "Only one patron can use at a time",
                            "Requires physical storage space",
                            "Can be damaged, lost, or stolen",
                            "Must be physically transported",
                            "Font size is fixed",
                        ],
                    ),
                    MaterialFormatCosts(
                        format_type="print_paperback",
                        format_name="Print Book (Paperback)",
                        description="Physical paperback book",
                        acquisition_cost=CostFactor(
                            name="Purchase Price",
                            description="Wholesale cost, typically lower than hardcover",
                            low_estimate=Decimal("8.00"),
                            high_estimate=Decimal("18.00"),
                            unit="per copy",
                            notes="Trade paperbacks cost more than mass market"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Cataloging, spine labels, RFID tags",
                            low_estimate=Decimal("3.00"),
                            high_estimate=Decimal("6.00"),
                            unit="per copy",
                            notes="Less processing than hardcovers (no jacket covers)"
                        ),
                        storage_cost=CostFactor(
                            name="Shelf Space",
                            description="Physical shelf space, typically smaller footprint",
                            low_estimate=Decimal("0.40"),
                            high_estimate=Decimal("1.50"),
                            unit="per year",
                            notes="Smaller than hardcovers"
                        ),
                        maintenance_cost=CostFactor(
                            name="Repairs",
                            description="Limited repair options; often replaced rather than repaired",
                            low_estimate=Decimal("0.50"),
                            high_estimate=Decimal("2.00"),
                            unit="per year",
                            notes="Paperbacks wear out faster than hardcovers"
                        ),
                        typical_lifespan_years=5,
                        simultaneous_users="1",
                        environmental_notes="Lower material use than hardcovers. Often not rebindable.",
                        advantages=[
                            "Lower initial cost",
                            "Lighter weight for transport",
                            "No ongoing fees",
                            "Popular for book clubs (multiple copies)",
                        ],
                        limitations=[
                            "Shorter lifespan",
                            "Harder to repair",
                            "Spines crack more easily",
                            "Only one patron at a time",
                        ],
                    ),
                    MaterialFormatCosts(
                        format_type="ebook",
                        format_name="eBook",
                        description="Digital book accessed via app or e-reader",
                        acquisition_cost=CostFactor(
                            name="License Fee",
                            description="Cost per license; varies widely by publisher and model",
                            low_estimate=Decimal("9.99"),
                            high_estimate=Decimal("65.00"),
                            unit="per license",
                            notes="Some publishers charge 2-3x consumer price for library licenses"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Metadata import, platform integration",
                            low_estimate=Decimal("0.50"),
                            high_estimate=Decimal("2.00"),
                            unit="per title",
                            notes="Often automated through vendor platforms"
                        ),
                        storage_cost=CostFactor(
                            name="Platform Fees",
                            description="Hosting platform subscription (e.g., Palace Project)",
                            low_estimate=Decimal("0.10"),
                            high_estimate=Decimal("0.50"),
                            unit="per title per year",
                            notes="Usually bundled into consortium fees"
                        ),
                        maintenance_cost=CostFactor(
                            name="License Renewal",
                            description="Many licenses expire after set checkouts or time period",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("65.00"),
                            unit="per renewal",
                            notes="Perpetual licenses have no renewal; metered licenses must be repurchased"
                        ),
                        licensing_model="Varies: One Copy/One User, Metered Access (26 checkouts or 2 years), Cost Per Circ, Simultaneous Use",
                        typical_lifespan_years=None,
                        simultaneous_users="1 (typically) or unlimited (with premium license)",
                        environmental_notes="No physical production. Energy for servers and devices. No shipping.",
                        advantages=[
                            "Instant access, no wait for holds (if available)",
                            "No physical storage needed",
                            "Cannot be physically damaged or lost",
                            "Adjustable font size and accessibility features",
                            "Available 24/7 remotely",
                            "Some titles allow simultaneous users",
                        ],
                        limitations=[
                            "Requires device and internet (for download)",
                            "License may expire (not owned permanently)",
                            "Some publishers embargo new titles",
                            "Platform may change or discontinue",
                            "Learning curve for some patrons",
                            "Publisher pricing often higher than print",
                        ],
                    ),
                ],
            ),
            # AUDIOBOOKS CATEGORY
            CostComparisonCategory(
                category_name="Audiobooks",
                category_description="Audio formats for listening to books",
                formats=[
                    MaterialFormatCosts(
                        format_type="audiobook_cd",
                        format_name="Audiobook on CD",
                        description="Physical CD set with narrated book",
                        acquisition_cost=CostFactor(
                            name="Purchase Price",
                            description="Multi-disc sets from library distributors",
                            low_estimate=Decimal("25.00"),
                            high_estimate=Decimal("80.00"),
                            unit="per set",
                            notes="Unabridged titles typically 8-15 discs"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Cases, cataloging, disc verification",
                            low_estimate=Decimal("4.00"),
                            high_estimate=Decimal("10.00"),
                            unit="per set",
                            notes="Multiple discs require more handling"
                        ),
                        storage_cost=CostFactor(
                            name="Shelf Space",
                            description="AV shelving and organization",
                            low_estimate=Decimal("0.75"),
                            high_estimate=Decimal("2.50"),
                            unit="per year",
                            notes="Larger cases than books"
                        ),
                        maintenance_cost=CostFactor(
                            name="Disc Replacement",
                            description="Individual disc replacement when damaged",
                            low_estimate=Decimal("1.00"),
                            high_estimate=Decimal("5.00"),
                            unit="per year",
                            notes="Discs scratch; sets often incomplete"
                        ),
                        typical_lifespan_years=7,
                        simultaneous_users="1",
                        environmental_notes="Plastic production. Often difficult to recycle. Being phased out by many libraries.",
                        advantages=[
                            "No internet required",
                            "Works in older vehicles",
                            "Owned permanently",
                            "No platform dependency",
                        ],
                        limitations=[
                            "Discs scratch and skip",
                            "Bulky to store and transport",
                            "Declining CD player availability",
                            "Easy to lose individual discs",
                            "Only one patron at a time",
                        ],
                    ),
                    MaterialFormatCosts(
                        format_type="audiobook_digital",
                        format_name="Digital Audiobook",
                        description="Streaming/downloadable audiobook via app",
                        acquisition_cost=CostFactor(
                            name="License Fee",
                            description="Per-title license from platforms like Palace Project",
                            low_estimate=Decimal("15.00"),
                            high_estimate=Decimal("95.00"),
                            unit="per license",
                            notes="Premium narrators and new releases cost more"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Automated metadata import",
                            low_estimate=Decimal("0.25"),
                            high_estimate=Decimal("1.00"),
                            unit="per title",
                            notes="Minimal manual processing"
                        ),
                        storage_cost=CostFactor(
                            name="Platform Fees",
                            description="Included in platform subscription",
                            low_estimate=Decimal("0.05"),
                            high_estimate=Decimal("0.25"),
                            unit="per title per year",
                            notes="Bundled with ebook platform"
                        ),
                        maintenance_cost=CostFactor(
                            name="License Renewal",
                            description="Metered licenses require repurchase",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("95.00"),
                            unit="per renewal",
                            notes="Similar models to ebooks"
                        ),
                        licensing_model="One Copy/One User, Metered Access, Cost Per Circ",
                        typical_lifespan_years=None,
                        simultaneous_users="1 (typically)",
                        environmental_notes="No physical media. Server energy for streaming.",
                        advantages=[
                            "Instant access from anywhere",
                            "No physical damage possible",
                            "Playback speed control",
                            "Sleep timers and bookmarks",
                            "No storage space needed",
                        ],
                        limitations=[
                            "Requires smartphone/device",
                            "Needs internet for initial download",
                            "License may expire",
                            "Platform dependency",
                            "Data usage for streaming",
                        ],
                    ),
                ],
            ),
            # VIDEO CATEGORY
            CostComparisonCategory(
                category_name="Video",
                category_description="Movies and video content formats",
                formats=[
                    MaterialFormatCosts(
                        format_type="dvd",
                        format_name="DVD",
                        description="Standard definition disc",
                        acquisition_cost=CostFactor(
                            name="Purchase Price",
                            description="Library-licensed DVDs from distributors",
                            low_estimate=Decimal("15.00"),
                            high_estimate=Decimal("40.00"),
                            unit="per disc",
                            notes="Public performance rights may cost extra"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Cases, security, cataloging",
                            low_estimate=Decimal("3.00"),
                            high_estimate=Decimal("7.00"),
                            unit="per disc",
                            notes="Security cases add cost"
                        ),
                        storage_cost=CostFactor(
                            name="Shelf Space",
                            description="AV shelving",
                            low_estimate=Decimal("0.50"),
                            high_estimate=Decimal("1.50"),
                            unit="per year",
                            notes="Compact storage possible"
                        ),
                        maintenance_cost=CostFactor(
                            name="Disc Repair/Replacement",
                            description="Resurfacing or replacement",
                            low_estimate=Decimal("0.50"),
                            high_estimate=Decimal("3.00"),
                            unit="per year",
                            notes="Resurfacing machines can extend life"
                        ),
                        typical_lifespan_years=8,
                        simultaneous_users="1",
                        environmental_notes="Plastic disc and case. Difficult to recycle.",
                        advantages=[
                            "Lower cost than Blu-ray",
                            "Wide player compatibility",
                            "Owned permanently",
                            "No internet required",
                        ],
                        limitations=[
                            "Standard definition quality",
                            "Scratches affect playback",
                            "Declining new releases",
                            "Only one patron at a time",
                        ],
                    ),
                    MaterialFormatCosts(
                        format_type="bluray",
                        format_name="Blu-ray",
                        description="High definition disc",
                        acquisition_cost=CostFactor(
                            name="Purchase Price",
                            description="Library-licensed Blu-rays",
                            low_estimate=Decimal("20.00"),
                            high_estimate=Decimal("50.00"),
                            unit="per disc",
                            notes="4K UHD titles cost more"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Cases, security, cataloging",
                            low_estimate=Decimal("3.50"),
                            high_estimate=Decimal("8.00"),
                            unit="per disc",
                            notes="Similar to DVD processing"
                        ),
                        storage_cost=CostFactor(
                            name="Shelf Space",
                            description="AV shelving",
                            low_estimate=Decimal("0.50"),
                            high_estimate=Decimal("1.50"),
                            unit="per year",
                            notes="Same footprint as DVD"
                        ),
                        maintenance_cost=CostFactor(
                            name="Disc Care",
                            description="More scratch-resistant than DVD but still needs care",
                            low_estimate=Decimal("0.25"),
                            high_estimate=Decimal("2.00"),
                            unit="per year",
                            notes="More durable coating than DVD"
                        ),
                        typical_lifespan_years=10,
                        simultaneous_users="1",
                        environmental_notes="Similar to DVD environmental impact.",
                        advantages=[
                            "High definition quality",
                            "More durable than DVD",
                            "Owned permanently",
                            "Best quality for home viewing",
                        ],
                        limitations=[
                            "Requires Blu-ray player",
                            "Higher cost than DVD",
                            "Physical storage needed",
                            "Only one patron at a time",
                        ],
                    ),
                    MaterialFormatCosts(
                        format_type="streaming",
                        format_name="Streaming Video",
                        description="Digital streaming access (Palace Project)",
                        acquisition_cost=CostFactor(
                            name="Platform Subscription or Per-Play",
                            description="Annual subscription or cost-per-circulation model",
                            low_estimate=Decimal("0.99"),
                            high_estimate=Decimal("4.00"),
                            unit="per play",
                            notes="Palace Project: free (open-source)"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Minimal - automated through platform",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("0.10"),
                            unit="per title",
                            notes="Catalog is pre-loaded"
                        ),
                        storage_cost=CostFactor(
                            name="Platform Fees",
                            description="Some platforms have base subscription fees",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("500.00"),
                            unit="per month (library-wide)",
                            notes="Varies by platform and library size"
                        ),
                        maintenance_cost=CostFactor(
                            name="Budget Management",
                            description="Staff time to monitor usage and budgets",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("0.50"),
                            unit="per transaction",
                            notes="Cost-per-circ requires budget monitoring"
                        ),
                        licensing_model="Cost Per Circulation (pay per play) or Unlimited Subscription",
                        typical_lifespan_years=None,
                        simultaneous_users="Varies by title and license",
                        environmental_notes="No physical media. Energy for streaming servers and user devices.",
                        advantages=[
                            "Instant access from home",
                            "Large catalog available",
                            "No physical damage",
                            "New releases often available",
                        ],
                        limitations=[
                            "Requires internet connection",
                            "Cost per play adds up",
                            "Catalog changes without notice",
                            "Quality depends on internet speed",
                            "Title availability varies",
                        ],
                    ),
                ],
            ),
            # MUSIC CATEGORY
            CostComparisonCategory(
                category_name="Music",
                category_description="Music formats",
                formats=[
                    MaterialFormatCosts(
                        format_type="music_cd",
                        format_name="Music CD",
                        description="Physical compact disc",
                        acquisition_cost=CostFactor(
                            name="Purchase Price",
                            description="From music distributors",
                            low_estimate=Decimal("10.00"),
                            high_estimate=Decimal("20.00"),
                            unit="per disc",
                            notes="Box sets cost more"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Cases, cataloging, security",
                            low_estimate=Decimal("2.50"),
                            high_estimate=Decimal("5.00"),
                            unit="per disc",
                            notes="Standard AV processing"
                        ),
                        storage_cost=CostFactor(
                            name="Shelf Space",
                            description="CD shelving",
                            low_estimate=Decimal("0.25"),
                            high_estimate=Decimal("1.00"),
                            unit="per year",
                            notes="Compact storage"
                        ),
                        maintenance_cost=CostFactor(
                            name="Disc Care",
                            description="Resurfacing and case replacement",
                            low_estimate=Decimal("0.25"),
                            high_estimate=Decimal("1.50"),
                            unit="per year",
                            notes="Cases crack frequently"
                        ),
                        typical_lifespan_years=10,
                        simultaneous_users="1",
                        environmental_notes="Plastic production. Many libraries reducing CD collections.",
                        advantages=[
                            "High audio quality",
                            "No internet needed",
                            "Owned permanently",
                            "Works in many vehicles",
                        ],
                        limitations=[
                            "Declining popularity",
                            "Scratches affect playback",
                            "Only one patron at a time",
                            "Limited new releases",
                        ],
                    ),
                    MaterialFormatCosts(
                        format_type="vinyl_record",
                        format_name="Vinyl Record",
                        description="Analog LP records",
                        acquisition_cost=CostFactor(
                            name="Purchase Price",
                            description="New vinyl from distributors",
                            low_estimate=Decimal("18.00"),
                            high_estimate=Decimal("40.00"),
                            unit="per record",
                            notes="Specialty/limited editions cost more"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Protective sleeves, cataloging",
                            low_estimate=Decimal("3.00"),
                            high_estimate=Decimal("6.00"),
                            unit="per record",
                            notes="Requires careful handling"
                        ),
                        storage_cost=CostFactor(
                            name="Shelf Space",
                            description="Vertical storage for records",
                            low_estimate=Decimal("0.75"),
                            high_estimate=Decimal("2.00"),
                            unit="per year",
                            notes="Larger footprint than CDs"
                        ),
                        maintenance_cost=CostFactor(
                            name="Cleaning and Care",
                            description="Cleaning supplies, sleeve replacement",
                            low_estimate=Decimal("0.50"),
                            high_estimate=Decimal("2.00"),
                            unit="per year",
                            notes="Scratches are permanent"
                        ),
                        typical_lifespan_years=15,
                        simultaneous_users="1",
                        environmental_notes="PVC production. Durable if properly cared for.",
                        advantages=[
                            "Warm analog sound quality",
                            "Growing popularity/demand",
                            "Collectible value",
                            "Large artwork format",
                            "Owned permanently",
                        ],
                        limitations=[
                            "Requires turntable",
                            "Easily damaged by improper handling",
                            "Bulky storage",
                            "Only one patron at a time",
                            "Not portable",
                        ],
                    ),
                ],
            ),
            # PERIODICALS CATEGORY
            CostComparisonCategory(
                category_name="Periodicals",
                category_description="Magazines and newspapers",
                formats=[
                    MaterialFormatCosts(
                        format_type="magazine_print",
                        format_name="Print Magazine",
                        description="Physical magazine subscription",
                        acquisition_cost=CostFactor(
                            name="Annual Subscription",
                            description="Institutional subscription rate",
                            low_estimate=Decimal("25.00"),
                            high_estimate=Decimal("150.00"),
                            unit="per year",
                            notes="Weekly magazines cost more than monthly"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Check-in, display, binding consideration",
                            low_estimate=Decimal("1.00"),
                            high_estimate=Decimal("3.00"),
                            unit="per year",
                            notes="Ongoing check-in labor"
                        ),
                        storage_cost=CostFactor(
                            name="Display and Archive",
                            description="Current display and back issue storage",
                            low_estimate=Decimal("2.00"),
                            high_estimate=Decimal("10.00"),
                            unit="per year",
                            notes="Back issues require significant space"
                        ),
                        maintenance_cost=CostFactor(
                            name="Binding/Disposal",
                            description="Binding back issues or recycling",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("50.00"),
                            unit="per year",
                            notes="Most libraries no longer bind"
                        ),
                        typical_lifespan_years=1,
                        simultaneous_users="1 (current issue in-library)",
                        environmental_notes="Paper and ink. Recyclable. High turnover.",
                        advantages=[
                            "Browsable in library",
                            "No technology needed",
                            "Current awareness",
                            "Tactile reading experience",
                        ],
                        limitations=[
                            "Cannot be checked out (usually)",
                            "Quickly outdated",
                            "Storage intensive",
                            "High ongoing cost",
                        ],
                    ),
                    MaterialFormatCosts(
                        format_type="magazine_digital",
                        format_name="Digital Magazines",
                        description="Digital magazine access (Palace Project, PressReader)",
                        acquisition_cost=CostFactor(
                            name="Platform Subscription",
                            description="Annual platform access fee",
                            low_estimate=Decimal("500.00"),
                            high_estimate=Decimal("5000.00"),
                            unit="per year (library-wide)",
                            notes="Provides access to hundreds of titles"
                        ),
                        processing_cost=CostFactor(
                            name="Processing",
                            description="Minimal - platform managed",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("50.00"),
                            unit="per year",
                            notes="Marketing and patron education"
                        ),
                        storage_cost=CostFactor(
                            name="Platform Fees",
                            description="Included in subscription",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("0.00"),
                            unit="per year",
                            notes="Bundled cost"
                        ),
                        maintenance_cost=CostFactor(
                            name="Subscription Management",
                            description="Staff time for renewals and troubleshooting",
                            low_estimate=Decimal("0.00"),
                            high_estimate=Decimal("100.00"),
                            unit="per year",
                            notes="Minimal ongoing effort"
                        ),
                        licensing_model="Unlimited simultaneous access (typically)",
                        typical_lifespan_years=None,
                        simultaneous_users="Unlimited (platform-dependent)",
                        environmental_notes="No paper. Server energy for delivery.",
                        advantages=[
                            "Hundreds of titles in one subscription",
                            "Unlimited simultaneous access",
                            "Remote access 24/7",
                            "Back issues often included",
                            "No physical storage",
                            "Searchable content",
                        ],
                        limitations=[
                            "Requires device and internet",
                            "Some titles unavailable digitally",
                            "Platform interface learning curve",
                            "No ownership - access ends with subscription",
                        ],
                    ),
                ],
            ),
        ],
    )


@router.get(
    "",
    response_model=MaterialCostComparisonResponse,
    summary="Get material cost comparison data",
    description="Returns comprehensive, unbiased cost breakdown data for different library material formats. Designed for transparency to help patrons understand the economics of library materials.",
)
async def get_material_costs() -> MaterialCostComparisonResponse:
    """
    Public endpoint providing transparent cost comparison data.
    No authentication required - this is for public transparency.
    """
    return get_cost_comparison_data()


@router.get(
    "/summary",
    response_model=list[CostComparisonSummary],
    summary="Get simplified cost summary",
    description="Returns a simplified summary of costs per format for quick comparison.",
)
async def get_cost_summary() -> list[CostComparisonSummary]:
    """
    Returns simplified cost-per-use estimates for quick comparison.
    These are rough estimates based on typical library usage patterns.
    """
    return [
        CostComparisonSummary(
            format_type="print_book",
            format_name="Print Book (Hardcover)",
            avg_total_cost_per_circulation=Decimal("1.50"),
            typical_circulations_per_copy=25,
            cost_per_simultaneous_user=Decimal("25.00"),
        ),
        CostComparisonSummary(
            format_type="ebook",
            format_name="eBook",
            avg_total_cost_per_circulation=Decimal("2.50"),
            typical_circulations_per_copy=26,
            cost_per_simultaneous_user=Decimal("40.00"),
        ),
        CostComparisonSummary(
            format_type="audiobook_digital",
            format_name="Digital Audiobook",
            avg_total_cost_per_circulation=Decimal("3.00"),
            typical_circulations_per_copy=26,
            cost_per_simultaneous_user=Decimal("50.00"),
        ),
        CostComparisonSummary(
            format_type="dvd",
            format_name="DVD",
            avg_total_cost_per_circulation=Decimal("1.25"),
            typical_circulations_per_copy=30,
            cost_per_simultaneous_user=Decimal("30.00"),
        ),
        CostComparisonSummary(
            format_type="streaming",
            format_name="Streaming Video",
            avg_total_cost_per_circulation=Decimal("2.50"),
            typical_circulations_per_copy=1,
            cost_per_simultaneous_user=Decimal("2.50"),
        ),
    ]
