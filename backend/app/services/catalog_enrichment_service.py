# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache_strategies import CacheTTL
from .ollama_service import OllamaError, get_ollama_service

logger = get_logger(__name__)


SYSTEM_PROMPTS = {
    "description": (
        "You are a professional library cataloger. Write a 2-3 sentence catalog description "
        "suitable for an OPAC (Online Public Access Catalog). Be factual, concise, and informative. "
        "Do not include spoilers. Mention the genre and intended audience when relevant. "
        "Do not use promotional language or subjective opinions. "
        "Output only the description text, nothing else."
    ),
    "subjects": (
        "You are a professional library cataloger assigning subject headings. "
        "Return 3-6 Library of Congress Subject Headings (LCSH) for this item. "
        "Use established LCSH patterns and subdivisions "
        '(e.g., "Fiction -- Psychological", "Cooking -- Italian", "Children -- Books and reading"). '
        "Output only a comma-separated list of subject headings, nothing else."
    ),
}


async def _get_item_context(db: AsyncSession, item_id: int) -> Optional[dict]:
    try:
        from ..models.catalog import CatalogItem

        result = await db.execute(
            select(CatalogItem).where(CatalogItem.id == item_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            return None
        return {
            "id": item.id,
            "title": item.title,
            "author": item.author,
            "isbn": item.isbn,
            "item_type": item.item_type.value if hasattr(item.item_type, "value") else str(item.item_type),
            "description": item.description,
            "subjects": item.subjects,
            "publisher": item.publisher if hasattr(item, "publisher") else None,
            "publication_year": item.publication_year if hasattr(item, "publication_year") else None,
        }
    except SQLAlchemyError as e:
        logger.warning(f"Failed to fetch item context for id={item_id}: {e}")
        return None


def _build_enrichment_prompt(item_context: dict, enrichment_type: str) -> str:
    parts = [f"Title: {item_context.get('title', 'Unknown')}"]

    if item_context.get("author"):
        parts.append(f"Author: {item_context['author']}")
    if item_context.get("isbn"):
        parts.append(f"ISBN: {item_context['isbn']}")
    if item_context.get("item_type"):
        parts.append(f"Item type: {item_context['item_type']}")
    if item_context.get("publisher"):
        parts.append(f"Publisher: {item_context['publisher']}")
    if item_context.get("publication_year"):
        parts.append(f"Publication year: {item_context['publication_year']}")

    if enrichment_type == "description" and item_context.get("subjects"):
        parts.append(f"Subjects: {item_context['subjects']}")
    elif enrichment_type == "subjects" and item_context.get("description"):
        parts.append(f"Description: {item_context['description']}")

    if enrichment_type == "description":
        parts.append("\nWrite a catalog description for this item.")
    else:
        parts.append("\nSuggest Library of Congress subject headings for this item.")

    return "\n".join(parts)


async def generate_catalog_description(db: AsyncSession, item_id: int) -> dict:
    ollama = get_ollama_service()

    available = await ollama.is_available()
    if not available:
        raise OllamaError("AI service is not available. Please check that Ollama is running.")

    item_context = await _get_item_context(db, item_id)
    if not item_context:
        raise OllamaError(f"Catalog item {item_id} not found.")

    prompt = _build_enrichment_prompt(item_context, "description")
    system_prompt = SYSTEM_PROMPTS["description"]

    result = await ollama.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.5,
        max_tokens=200,
        cache_ttl=CacheTTL.DAILY,
    )

    return {
        "generated_text": result["response"].strip(),
        "model": result["model"],
        "generation_time_ms": result["generation_time_ms"],
        "item_context": item_context,
    }


async def generate_catalog_subjects(db: AsyncSession, item_id: int) -> dict:
    ollama = get_ollama_service()

    available = await ollama.is_available()
    if not available:
        raise OllamaError("AI service is not available. Please check that Ollama is running.")

    item_context = await _get_item_context(db, item_id)
    if not item_context:
        raise OllamaError(f"Catalog item {item_id} not found.")

    prompt = _build_enrichment_prompt(item_context, "subjects")
    system_prompt = SYSTEM_PROMPTS["subjects"]

    result = await ollama.generate(
        prompt=prompt,
        system_prompt=system_prompt,
        temperature=0.5,
        max_tokens=150,
        cache_ttl=CacheTTL.DAILY,
    )

    raw_text = result["response"].strip()
    subjects = [s.strip() for s in raw_text.split(",") if s.strip()]

    return {
        "generated_subjects": subjects,
        "generated_text": raw_text,
        "model": result["model"],
        "generation_time_ms": result["generation_time_ms"],
        "item_context": item_context,
    }
