# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.community_resource import CommunityResourceLink
from ..schemas.community_resource import (
    CommunityResourceLinkCreate,
    CommunityResourceLinkUpdate,
    DiscoverySuggestion,
)
from ..core.cache_strategies import CacheTTL
from ..services.ollama_service import OllamaService

logger = get_logger(__name__)

COMMUNITY_CATEGORIES = {
    "food_nutrition", "health_wellness", "housing",
    "jobs_employment", "family_services",
}


async def get_public_resources(
    db: AsyncSession, page_context: str
) -> list[CommunityResourceLink]:
    result = await db.execute(
        select(CommunityResourceLink)
        .where(
            CommunityResourceLink.is_active.is_(True),
            CommunityResourceLink.url.isnot(None),
            CommunityResourceLink.page_contexts.any(page_context),
        )
        .order_by(CommunityResourceLink.category, CommunityResourceLink.sort_order)
    )
    return result.scalars().all()


async def get_all_resources(db: AsyncSession) -> list[CommunityResourceLink]:
    result = await db.execute(
        select(CommunityResourceLink)
        .order_by(CommunityResourceLink.category, CommunityResourceLink.sort_order)
    )
    return result.scalars().all()


async def create_resource(
    db: AsyncSession, data: CommunityResourceLinkCreate
) -> CommunityResourceLink:
    link = CommunityResourceLink(**data.model_dump())
    db.add(link)
    await db.flush()
    await db.refresh(link)
    return link


async def update_resource(
    db: AsyncSession, link_id: int, data: CommunityResourceLinkUpdate
) -> Optional[CommunityResourceLink]:
    result = await db.execute(
        select(CommunityResourceLink).where(CommunityResourceLink.id == link_id)
    )
    link = result.scalar_one_or_none()
    if not link:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(link, field, value)
    await db.flush()
    await db.refresh(link)
    return link


async def delete_resource(db: AsyncSession, link_id: int) -> bool:
    result = await db.execute(
        delete(CommunityResourceLink).where(CommunityResourceLink.id == link_id)
    )
    return result.rowcount > 0


async def discover_resources(
    db: AsyncSession, city: str, state: str, zip_code: str
) -> list[DiscoverySuggestion]:
    ollama = OllamaService()
    if not await ollama.is_available():
        raise RuntimeError("AI service is not available")

    prompt = f"""For a public library in {city}, {state} {zip_code}, suggest local community resources.

Return a JSON array of objects with these fields:
- "name": organization name
- "url": website URL
- "category": one of "food_nutrition", "health_wellness", "housing", "jobs_employment", "family_services"
- "category_label": human-readable category name (e.g. "Food & Nutrition")
- "description": one-sentence description

Include real organizations with real URLs. Return ONLY the JSON array, no other text.
Focus on: food banks, health clinics, mental health services, housing assistance, shelters, employment services, childcare, family services."""

    result = await ollama.generate(
        prompt=prompt,
        system_prompt="You are a helpful assistant that returns only valid JSON arrays. No markdown, no explanation.",
        max_tokens=3000,
        cache_ttl=CacheTTL.DAILY,
    )

    try:
        raw = result.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        suggestions_data = json.loads(raw)
    except (json.JSONDecodeError, IndexError):
        logger.error(f"Failed to parse AI discovery response: {result[:200]}")
        return []

    suggestions = []
    for item in suggestions_data:
        if not isinstance(item, dict):
            continue
        cat = item.get("category", "")
        if cat not in COMMUNITY_CATEGORIES:
            continue
        suggestions.append(DiscoverySuggestion(
            name=item.get("name", "Unknown"),
            url=item.get("url", ""),
            category=cat,
            category_label=item.get("category_label", cat.replace("_", " ").title()),
            description=item.get("description"),
        ))

    return suggestions


async def save_discovery_suggestions(
    db: AsyncSession, suggestions: list[DiscoverySuggestion], page_contexts: list[str]
) -> list[CommunityResourceLink]:
    saved = []
    for s in suggestions:
        link = CommunityResourceLink(
            category=s.category,
            category_label=s.category_label,
            page_contexts=page_contexts,
            name=s.name,
            url=s.url,
            description=s.description,
            sort_order=0,
            is_active=False,
            source="ai_suggested",
        )
        db.add(link)
        saved.append(link)
    await db.flush()
    for link in saved:
        await db.refresh(link)
    return saved
