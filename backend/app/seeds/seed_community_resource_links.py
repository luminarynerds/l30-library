# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = get_logger(__name__)

SEED_LINKS = [
    # Community: Food & Nutrition
    {"category": "food_nutrition", "category_label": "Food & Nutrition", "icon_hint": "utensils", "page_contexts": ["community", "life_situations"], "name": "Local Food Bank"},
    {"category": "food_nutrition", "category_label": "Food & Nutrition", "icon_hint": "utensils", "page_contexts": ["community", "life_situations"], "name": "Community Kitchen Program"},
    {"category": "food_nutrition", "category_label": "Food & Nutrition", "icon_hint": "utensils", "page_contexts": ["community", "life_situations"], "name": "Meals on Wheels"},
    # Community: Health & Wellness
    {"category": "health_wellness", "category_label": "Health & Wellness", "icon_hint": "stethoscope", "page_contexts": ["community", "life_situations"], "name": "Community Health Centre"},
    {"category": "health_wellness", "category_label": "Health & Wellness", "icon_hint": "stethoscope", "page_contexts": ["community", "life_situations"], "name": "Mental Health Support Line"},
    {"category": "health_wellness", "category_label": "Health & Wellness", "icon_hint": "stethoscope", "page_contexts": ["community", "life_situations"], "name": "Addiction Services"},
    # Community: Housing Support
    {"category": "housing", "category_label": "Housing Support", "icon_hint": "home", "page_contexts": ["community", "life_situations"], "name": "Affordable Housing Registry"},
    {"category": "housing", "category_label": "Housing Support", "icon_hint": "home", "page_contexts": ["community", "life_situations"], "name": "Emergency Shelter Info"},
    {"category": "housing", "category_label": "Housing Support", "icon_hint": "home", "page_contexts": ["community", "life_situations"], "name": "Rent Assistance Program"},
    # Community: Jobs & Employment
    {"category": "jobs_employment", "category_label": "Jobs & Employment", "icon_hint": "briefcase", "page_contexts": ["community"], "name": "Workforce Development"},
    # Community: Family Services
    {"category": "family_services", "category_label": "Family Services", "icon_hint": "baby", "page_contexts": ["community", "life_situations"], "name": "Childcare Subsidies"},
    {"category": "family_services", "category_label": "Family Services", "icon_hint": "baby", "page_contexts": ["community", "life_situations"], "name": "Parenting Programs"},
    {"category": "family_services", "category_label": "Family Services", "icon_hint": "baby", "page_contexts": ["community", "life_situations"], "name": "Youth Services"},
    # Business: State Resources
    {"category": "business_state", "category_label": "State Resources", "icon_hint": "landmark", "page_contexts": ["business"], "name": "NOS Business Registry"},
    {"category": "business_state", "category_label": "State Resources", "icon_hint": "landmark", "page_contexts": ["business"], "name": "Small Business Enterprise Centre"},
    {"category": "business_state", "category_label": "State Resources", "icon_hint": "landmark", "page_contexts": ["business"], "name": "North of Somewhere Business Network"},
    # Business: Learning & Training
    {"category": "business_learning", "category_label": "Learning & Training", "icon_hint": "graduation-cap", "page_contexts": ["business"], "name": "LinkedIn Learning (Library Access)"},
    # Business: Market Research
    {"category": "business_research", "category_label": "Market Research", "icon_hint": "trending-up", "page_contexts": ["business"], "name": "NOS Statistics Bureau"},
    {"category": "business_research", "category_label": "Market Research", "icon_hint": "trending-up", "page_contexts": ["business"], "name": "IBISWorld (Library Access)"},
    # Business: Research Databases
    {"category": "business_databases", "category_label": "Research Databases", "icon_hint": "database", "page_contexts": ["business"], "name": "Reference USA"},
    {"category": "business_databases", "category_label": "Research Databases", "icon_hint": "database", "page_contexts": ["business"], "name": "Business Source Complete"},
    {"category": "business_databases", "category_label": "Research Databases", "icon_hint": "database", "page_contexts": ["business"], "name": "SBDC Resources"},
    {"category": "business_databases", "category_label": "Research Databases", "icon_hint": "database", "page_contexts": ["business"], "name": "IBISWorld Industry Reports"},
    {"category": "business_databases", "category_label": "Research Databases", "icon_hint": "database", "page_contexts": ["business"], "name": "Mergent Online"},
    {"category": "business_databases", "category_label": "Research Databases", "icon_hint": "database", "page_contexts": ["business"], "name": "Demographics Now"},
    # Business: Career Services
    {"category": "business_career", "category_label": "Career Services", "icon_hint": "briefcase", "page_contexts": ["business"], "name": "Job Search Databases"},
    # Business: Small Business Support
    {"category": "business_smallbiz", "category_label": "Small Business Support", "icon_hint": "rocket", "page_contexts": ["business"], "name": "Business Plan Templates"},
    {"category": "business_smallbiz", "category_label": "Small Business Support", "icon_hint": "rocket", "page_contexts": ["business"], "name": "Business Licensing Guide"},
    {"category": "business_smallbiz", "category_label": "Small Business Support", "icon_hint": "rocket", "page_contexts": ["business"], "name": "Marketing Toolkit"},
    # Makerspace: 3D Printing
    {"category": "makerspace_3d", "category_label": "3D Printing", "icon_hint": "printer", "page_contexts": ["makerspace"], "name": "Getting Started Guide"},
    {"category": "makerspace_3d", "category_label": "3D Printing", "icon_hint": "printer", "page_contexts": ["makerspace"], "name": "File Preparation Tips"},
    {"category": "makerspace_3d", "category_label": "3D Printing", "icon_hint": "printer", "page_contexts": ["makerspace"], "name": "Material Guidelines"},
    # Makerspace: Laser Cutting
    {"category": "makerspace_laser", "category_label": "Laser Cutting", "icon_hint": "zap", "page_contexts": ["makerspace"], "name": "Safety Certification"},
    {"category": "makerspace_laser", "category_label": "Laser Cutting", "icon_hint": "zap", "page_contexts": ["makerspace"], "name": "Design Templates"},
    {"category": "makerspace_laser", "category_label": "Laser Cutting", "icon_hint": "zap", "page_contexts": ["makerspace"], "name": "Material Compatibility"},
    # Makerspace: Electronics Lab
    {"category": "makerspace_electronics", "category_label": "Electronics Lab", "icon_hint": "cpu", "page_contexts": ["makerspace"], "name": "Arduino Starter Guide"},
    {"category": "makerspace_electronics", "category_label": "Electronics Lab", "icon_hint": "cpu", "page_contexts": ["makerspace"], "name": "Soldering Basics"},
    {"category": "makerspace_electronics", "category_label": "Electronics Lab", "icon_hint": "cpu", "page_contexts": ["makerspace"], "name": "Component Library"},
    # Makerspace: Media Studio
    {"category": "makerspace_media", "category_label": "Media Studio", "icon_hint": "video", "page_contexts": ["makerspace"], "name": "Studio Booking"},
    {"category": "makerspace_media", "category_label": "Media Studio", "icon_hint": "video", "page_contexts": ["makerspace"], "name": "Equipment List"},
    {"category": "makerspace_media", "category_label": "Media Studio", "icon_hint": "video", "page_contexts": ["makerspace"], "name": "Recording Tips"},
]


async def seed_community_resource_links(db: AsyncSession) -> None:
    result = await db.execute(text("SELECT count(*) FROM community_resource_links"))
    count = result.scalar()
    if count > 0:
        logger.info(f"Community resource links already seeded ({count} rows), skipping")
        return True
        return

    logger.info(f"Seeding {len(SEED_LINKS)} community resource links...")
    for i, link_data in enumerate(SEED_LINKS):
        await db.execute(
            text("""
                INSERT INTO community_resource_links
                (category, category_label, icon_hint, page_contexts, name, url, sort_order, is_active, source)
                VALUES (:category, :category_label, :icon_hint, CAST(:page_contexts AS varchar[]), :name, NULL, :sort_order, false, 'manual')
            """),
            {
                "category": link_data["category"],
                "category_label": link_data["category_label"],
                "icon_hint": link_data.get("icon_hint"),
                "page_contexts": link_data["page_contexts"],
                "name": link_data["name"],
                "sort_order": i,
            },
        )
    await db.commit()
    logger.info(f"Seeded {len(SEED_LINKS)} community resource links")
    return True
