# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Marketing Hub API - AI-powered marketing content generation for library staff.

Endpoints for generating, saving, and managing AI-created marketing materials
that leverage library program data, events, and campaigns.
"""

from app.core.logging import get_logger
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.generated_content import GeneratedContent, ContentType
from ...models.user import User
from ...services.marketing_content_service import generate_marketing_content
from ...services.ollama_service import OllamaError, get_ollama_service
from .dependencies import require_staff

logger = get_logger(__name__)

router = APIRouter(prefix="/marketing-hub", tags=["marketing-hub"])


# ============================================================================
# Schemas
# ============================================================================


class GenerateContentRequest(BaseModel):
    content_type: str = Field(
        ...,
        description="Type of content: social_post, newsletter, flyer, program_promo, event_promo",
    )
    instructions: str = Field(
        ..., min_length=5, max_length=2000,
        description="What you want the AI to write",
    )
    program_id: Optional[int] = Field(None, description="Reading program ID for context")
    event_id: Optional[int] = Field(None, description="Event ID for context")
    tone: Optional[str] = Field(None, max_length=50, description="e.g. playful, formal, urgent")
    temperature: float = Field(0.7, ge=0.0, le=1.5, description="AI creativity level")


class GenerateContentResponse(BaseModel):
    success: bool
    generated_text: Optional[str] = None
    content_type: str
    model_used: Optional[str] = None
    generation_time_ms: Optional[int] = None
    context_data: Optional[dict] = None
    error: Optional[str] = None


class SaveContentRequest(BaseModel):
    content_type: ContentType
    title: Optional[str] = Field(None, max_length=200)
    generated_text: str = Field(..., min_length=1)
    user_prompt: str
    model_used: Optional[str] = None
    temperature: float = 0.7
    generation_time_ms: Optional[int] = None
    program_id: Optional[int] = None
    event_id: Optional[int] = None
    context_data: Optional[dict] = None


class SavedContentResponse(BaseModel):
    id: int
    content_type: str
    title: Optional[str]
    generated_text: str
    user_prompt: str
    model_used: Optional[str]
    temperature: float
    generation_time_ms: Optional[int]
    program_id: Optional[int]
    event_id: Optional[int]
    context_data: Optional[dict]
    is_favorite: bool
    created_at: str

    class Config:
        from_attributes = True


class SavedContentListResponse(BaseModel):
    items: List[SavedContentResponse]
    total: int


class ProgramSummary(BaseModel):
    id: int
    name: str
    program_type: str
    age_group: Optional[str]
    start_date: str
    end_date: str
    is_active: bool


class EventSummary(BaseModel):
    id: int
    name: str
    start_time: Optional[str]
    location: Optional[str]


class AIStatusResponse(BaseModel):
    available: bool
    models: List[str] = []


# ============================================================================
# Endpoints
# ============================================================================


@router.get("/ai-status", response_model=AIStatusResponse)
async def check_ai_status(
    current_user: User = Depends(require_staff),
) -> AIStatusResponse:
    """Check if the AI service is available."""
    ollama = get_ollama_service()
    available = await ollama.is_available()
    models = []
    if available:
        models = await ollama.list_models()
    return AIStatusResponse(available=available, models=models)


@router.post("/generate", response_model=GenerateContentResponse)
async def generate_content(
    request: GenerateContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> GenerateContentResponse:
    """
    Generate marketing content using AI.

    Provide instructions and optionally reference a reading program or event
    to give the AI relevant library context.
    """

    valid_types = [ct.value for ct in ContentType]
    if request.content_type not in valid_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid content_type. Must be one of: {', '.join(valid_types)}",
        )

    try:
        result = await generate_marketing_content(
            db=db,
            content_type=request.content_type,
            user_instructions=request.instructions,
            program_id=request.program_id,
            event_id=request.event_id,
            tone=request.tone,
            temperature=request.temperature,
        )

        return GenerateContentResponse(
            success=True,
            generated_text=result["generated_text"],
            content_type=request.content_type,
            model_used=result["model"],
            generation_time_ms=result["generation_time_ms"],
            context_data=result["context_data"],
        )

    except OllamaError as e:
        return GenerateContentResponse(
            success=False,
            content_type=request.content_type,
            error=str(e),
        )
    except Exception as e:  # noqa: BLE001  # content gen route boundary — translates to error response
        logger.error(f"Content generation failed: {e}")
        return GenerateContentResponse(
            success=False,
            content_type=request.content_type,
            error="Content generation failed. Please try again.",
        )


@router.post("/save", response_model=SavedContentResponse, status_code=status.HTTP_201_CREATED)
async def save_content(
    request: SaveContentRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> SavedContentResponse:
    """Save generated content for later use."""

    from ...services.marketing_content_service import SYSTEM_PROMPTS
    content = GeneratedContent(
        content_type=request.content_type,
        title=request.title,
        generated_text=request.generated_text,
        user_prompt=request.user_prompt,
        system_prompt=SYSTEM_PROMPTS.get(str(request.content_type), ""),
        model_used=request.model_used,
        temperature=request.temperature,
        generation_time_ms=request.generation_time_ms,
        program_id=request.program_id,
        event_id=request.event_id,
        context_data=request.context_data,
        created_by_id=current_user.id,
    )

    db.add(content)
    await db.commit()
    await db.refresh(content)

    return SavedContentResponse(
        id=content.id,
        content_type=content.content_type.value if hasattr(content.content_type, 'value') else content.content_type,
        title=content.title,
        generated_text=content.generated_text,
        user_prompt=content.user_prompt,
        model_used=content.model_used,
        temperature=content.temperature,
        generation_time_ms=content.generation_time_ms,
        program_id=content.program_id,
        event_id=content.event_id,
        context_data=content.context_data,
        is_favorite=content.is_favorite,
        created_at=content.created_at.isoformat(),
    )


@router.get("/history", response_model=SavedContentListResponse)
async def list_saved_content(
    content_type: Optional[str] = Query(None),
    favorites_only: bool = Query(False),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> SavedContentListResponse:
    """List saved generated content with optional filtering."""

    # Build shared filter conditions
    conditions = [GeneratedContent.created_by_id == current_user.id]
    if content_type:
        conditions.append(GeneratedContent.content_type == content_type)
    if favorites_only:
        conditions.append(GeneratedContent.is_favorite == True)

    # Count
    count_query = select(func.count(GeneratedContent.id)).where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Fetch
    query = (
        select(GeneratedContent)
        .where(*conditions)
        .order_by(desc(GeneratedContent.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    items = result.scalars().all()

    return SavedContentListResponse(
        items=[
            SavedContentResponse(
                id=item.id,
                content_type=item.content_type.value if hasattr(item.content_type, 'value') else item.content_type,
                title=item.title,
                generated_text=item.generated_text,
                user_prompt=item.user_prompt,
                model_used=item.model_used,
                temperature=item.temperature,
                generation_time_ms=item.generation_time_ms,
                program_id=item.program_id,
                event_id=item.event_id,
                context_data=item.context_data,
                is_favorite=item.is_favorite,
                created_at=item.created_at.isoformat(),
            )
            for item in items
        ],
        total=total,
    )


@router.delete("/history/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_content(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> None:
    """Delete a saved content item."""

    result = await db.execute(
        select(GeneratedContent).where(
            GeneratedContent.id == content_id,
            GeneratedContent.created_by_id == current_user.id,
        )
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    await db.delete(content)
    await db.commit()


@router.put("/history/{content_id}/favorite")
async def toggle_favorite(
    content_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> dict:
    """Toggle favorite status on a saved content item."""

    result = await db.execute(
        select(GeneratedContent).where(
            GeneratedContent.id == content_id,
            GeneratedContent.created_by_id == current_user.id,
        )
    )
    content = result.scalar_one_or_none()
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")

    content.is_favorite = not content.is_favorite
    await db.commit()

    return {"id": content_id, "is_favorite": content.is_favorite}


@router.get("/programs", response_model=List[ProgramSummary])
async def list_programs_for_context(
    active_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> List[ProgramSummary]:
    """List reading programs available for use as marketing context."""

    try:
        from ...models.reading import ReadingProgram
        query = select(ReadingProgram)
        if active_only:
            query = query.where(ReadingProgram.is_active == True)
        query = query.order_by(desc(ReadingProgram.start_date)).limit(50)

        result = await db.execute(query)
        programs = result.scalars().all()

        return [
            ProgramSummary(
                id=p.id,
                name=p.name,
                program_type=p.program_type.value if hasattr(p.program_type, 'value') else str(p.program_type),
                age_group=p.age_group,
                start_date=str(p.start_date),
                end_date=str(p.end_date),
                is_active=p.is_active,
            )
            for p in programs
        ]
    except Exception as e:  # noqa: BLE001  # list fallback — return empty on any failure
        logger.warning(f"Failed to list programs: {e}")
        return []


@router.get("/events", response_model=List[EventSummary])
async def list_events_for_context(
    upcoming_only: bool = Query(True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> List[EventSummary]:
    """List events available for use as marketing context."""

    try:
        from ...models.event import Event
        query = select(Event)
        if upcoming_only:
            query = query.where(Event.start_time >= date.today())
        query = query.order_by(Event.start_time).limit(50)

        result = await db.execute(query)
        events = result.scalars().all()

        return [
            EventSummary(
                id=e.id,
                name=e.title,
                start_time=str(e.start_time) if e.start_time else None,
                location=e.location,
            )
            for e in events
        ]
    except Exception as e:  # noqa: BLE001  # list fallback — return empty on any failure
        logger.warning(f"Failed to list events: {e}")
        return []
