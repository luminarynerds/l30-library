# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""AI Tools API - Chat with AI personalities like Ernie, Reader Advisory, Writing Assistant"""

from app.core.logging import get_logger

logger = get_logger(__name__)
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings

from ...core.database import get_db
from ...models.ai_tools import AITool
from ...models.user import User
from .auth import get_current_user, get_optional_user
from .dependencies import require_admin, require_staff

router = APIRouter(prefix="/ai-tools", tags=["ai-tools"])


# ============================================================================
# Schemas
# ============================================================================


class AIToolResponse(BaseModel):

    id: int
    tool_id: str
    name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    category: Optional[str] = None
    enabled: bool
    in_library_only: bool
    requires_auth: bool
    block_for_minors: bool = False
    requires_parental_consent: bool = False
    block_for_patron_types: List[str] = Field(default_factory=list)
    sort_order: int
    usage_count: int

    class Config:
        from_attributes = True


class AIToolDetailResponse(BaseModel):

    id: int
    tool_id: str
    name: str
    description: Optional[str] = None
    system_prompt: str  # Show for transparency
    temperature: float
    max_tokens: int
    model: str
    icon: Optional[str] = None
    category: Optional[str] = None
    enabled: bool
    in_library_only: bool
    requires_auth: bool
    block_for_minors: bool = False
    requires_parental_consent: bool = False
    block_for_patron_types: List[str] = Field(default_factory=list)
    sort_order: int
    usage_count: int
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):

    message: str = Field(..., min_length=1, max_length=2000)
    conversation_history: Optional[List[dict]] = Field(default=None, max_items=20)


class ChatResponse(BaseModel):

    success: bool
    response: Optional[str] = None
    tool_id: str
    model_used: Optional[str] = None
    generation_time_ms: Optional[int] = None
    error: Optional[str] = None


class AIToolCreate(BaseModel):

    tool_id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: str = Field(..., min_length=10)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=500, ge=50, le=4000)
    model: str = Field(default="llama3.2:3b", max_length=100)
    icon: Optional[str] = Field(default=None, max_length=50)
    category: Optional[str] = Field(default=None, max_length=50)
    enabled: bool = True
    in_library_only: bool = False
    requires_auth: bool = False
    block_for_minors: bool = False
    requires_parental_consent: bool = False
    block_for_patron_types: List[str] = Field(default_factory=list)
    sort_order: int = Field(default=0, ge=0)


class AIToolUpdate(BaseModel):

    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(default=None, min_length=10)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=50, le=4000)
    model: Optional[str] = Field(default=None, max_length=100)
    icon: Optional[str] = Field(default=None, max_length=50)
    category: Optional[str] = Field(default=None, max_length=50)
    enabled: Optional[bool] = None
    in_library_only: Optional[bool] = None
    requires_auth: Optional[bool] = None
    block_for_minors: Optional[bool] = None
    requires_parental_consent: Optional[bool] = None
    block_for_patron_types: Optional[List[str]] = None
    sort_order: Optional[int] = Field(default=None, ge=0)


async def get_ollama_base_url(db: AsyncSession) -> str:
    # Try to get from ai_configurations table if it exists
    try:
        from ...models.ai_config import AIConfiguration

        result = await db.execute(
            select(AIConfiguration).where(AIConfiguration.config_key == "ollama")
        )
        config = result.scalar_one_or_none()
        if config and config.config_value:
            return config.config_value.get("base_url", get_settings().ollama_base_url)
    except Exception as e:  # noqa: BLE001  # config lookup best-effort — fall back to default
        logger.warning("Failed to load Ollama base URL from config: %s", e)

    return get_settings().ollama_base_url


# ============================================================================
# Public Endpoints
# ============================================================================


class AIToolListResponse(BaseModel):

    items: List[AIToolResponse]
    total: int
    limit: int
    offset: int


@router.get("", response_model=AIToolListResponse)
async def list_ai_tools(
    enabled_only: bool = True,
    limit: int = Query(50, ge=1, le=100, description="Maximum number of items to return"),
    offset: int = Query(0, ge=0, description="Number of items to skip"),
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> AIToolListResponse:
    """
    List all available AI tools with pagination.

    - **enabled_only**: Only return enabled tools (default: true)
    - **limit**: Maximum number of items to return (default: 50, max: 100)
    - **offset**: Number of items to skip for pagination (default: 0)
    - Returns tools sorted by sort_order
    """
    # Base query conditions
    conditions = []
    if enabled_only:
        conditions.append(AITool.enabled == True)

    # If user not logged in, exclude auth-required tools
    if not current_user:
        conditions.append(AITool.requires_auth == False)

    # Build query with conditions
    query = select(AITool)
    if conditions:
        query = query.where(*conditions)

    # Get total count
    count_query = select(func.count(AITool.id))
    if conditions:
        count_query = count_query.where(*conditions)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(AITool.sort_order, AITool.name).offset(offset).limit(limit)

    result = await db.execute(query)
    tools = result.scalars().all()

    # Hide tools the current viewer cannot use due to minor / patron-type gating.
    from ...services.ai_guardrails_service import check_minor_access
    visible = [t for t in tools if check_minor_access(t, current_user)[0]]
    if len(visible) != len(tools):
        total = max(0, total - (len(tools) - len(visible)))

    return AIToolListResponse(
        items=visible,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{tool_id}", response_model=AIToolDetailResponse)
async def get_ai_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
) -> AIToolDetailResponse:
    """
    Get detailed information about a specific AI tool.

    System prompts are shown for transparency - patrons can see how we configure the AI.
    """
    result = await db.execute(select(AITool).where(AITool.tool_id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI tool '{tool_id}' not found",
        )

    if not tool.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI tool '{tool_id}' is currently unavailable",
        )

    if (tool.requires_auth or tool.block_for_minors or tool.requires_parental_consent) and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for this AI tool",
        )

    from ...services.ai_guardrails_service import check_minor_access
    minor_ok, minor_reason = check_minor_access(tool, current_user)
    if not minor_ok:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=minor_reason)

    return tool


@router.post("/{tool_id}/chat", response_model=ChatResponse)
async def chat_with_ai_tool(  # staff-only while AI tools are in pilot
    tool_id: str,
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_staff),
) -> ChatResponse:
    """
    Chat with an AI tool.

    - **tool_id**: The AI tool to chat with (ernie, reader, writer, garden)
    - **message**: Your message to the AI
    - **conversation_history**: Optional previous messages for context

    Guardrails are enforced automatically:
    - Blocked topics are rejected before calling the model
    - Usage limits are checked per-role
    - Model allowlists are validated
    - Disclaimers and content filters are applied to responses
    - All usage is logged for audit
    """
    from ...services.ai_guardrails_service import (
        GuardrailResult, check_prompt_guardrails, check_usage_limits, check_model_allowed,
        check_minor_access, apply_response_guardrails, apply_youth_guardrails,
        build_guarded_system_prompt, log_ai_usage,
    )

    # Get the AI tool
    result = await db.execute(select(AITool).where(AITool.tool_id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool or not tool.enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI tool '{tool_id}' not available",
        )

    # Tools that gate by age/consent must know who the user is. Treat them as
    # implicitly requires_auth so anonymous callers get a 401 rather than
    # silently passing through the minor check.
    auth_required = tool.requires_auth or tool.block_for_minors or tool.requires_parental_consent
    if auth_required and not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required for this AI tool",
        )

    # Snapshot audience attributes once, used for guardrail filtering and the audit log.
    is_minor = bool(current_user and getattr(current_user, "is_minor", False))
    patron_type = getattr(current_user, "patron_type", None) if current_user else None

    # --- Guardrails: Minor / patron-type access ---
    minor_ok, minor_reason = check_minor_access(tool, current_user)
    if not minor_ok:
        guardrail_result_blocked = GuardrailResult()
        guardrail_result_blocked.blocked = True
        guardrail_result_blocked.block_reason = minor_reason
        await log_ai_usage(
            db, current_user.id if current_user else None, tool_id, tool.model,
            request.message, None, None, guardrail_result=guardrail_result_blocked,
            success=False, error_message=minor_reason,
            was_minor=is_minor, patron_type_at_request=patron_type,
        )
        await db.commit()
        return ChatResponse(success=False, tool_id=tool_id, error=minor_reason)

    # --- Guardrails: Usage limits ---
    if current_user:
        allowed, reason = await check_usage_limits(db, current_user.id, current_user.role.value if hasattr(current_user.role, 'value') else str(current_user.role))
        if not allowed:
            guardrail_result_blocked = GuardrailResult()
            guardrail_result_blocked.blocked = True
            guardrail_result_blocked.block_reason = reason
            await log_ai_usage(db, current_user.id, tool_id, tool.model, request.message, None, None,
                               guardrail_result=guardrail_result_blocked, success=False, error_message=reason,
                               was_minor=is_minor, patron_type_at_request=patron_type)
            await db.commit()
            return ChatResponse(success=False, tool_id=tool_id, error=reason)

    # --- Guardrails: Model allowlist ---
    model_ok, model_reason = await check_model_allowed(db, tool.model)
    if not model_ok:
        guardrail_result_blocked = GuardrailResult()
        guardrail_result_blocked.blocked = True
        guardrail_result_blocked.block_reason = model_reason
        await log_ai_usage(db, current_user.id if current_user else None, tool_id, tool.model,
                           request.message, None, None, guardrail_result=guardrail_result_blocked,
                           success=False, error_message=model_reason,
                           was_minor=is_minor, patron_type_at_request=patron_type)
        await db.commit()
        return ChatResponse(success=False, tool_id=tool_id, error=model_reason)

    # --- Guardrails: Content guardrails (blocked topics, filters, etc.) ---
    guardrail_result = await check_prompt_guardrails(
        db, request.message, tool_id,
        is_minor=is_minor, patron_type=patron_type,
    )

    # --- Guardrails: Youth patron protections (age-appropriate responses) ---
    if current_user:
        guardrail_result = apply_youth_guardrails(guardrail_result, current_user)

    if guardrail_result.blocked:
        await log_ai_usage(db, current_user.id if current_user else None, tool_id, tool.model,
                           request.message, None, None, guardrail_result=guardrail_result,
                           success=False, error_message=guardrail_result.block_reason,
                           was_minor=is_minor, patron_type_at_request=patron_type)
        await db.commit()
        return ChatResponse(
            success=False,
            tool_id=tool_id,
            error=guardrail_result.block_reason,
        )

    # Get Ollama URL
    base_url = await get_ollama_base_url(db)

    # Build prompt with conversation history
    prompt = request.message
    if request.conversation_history:
        history_text = ""
        for msg in request.conversation_history[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"{role}: {content}\n"
        prompt = f"{history_text}user: {request.message}"

    # Apply guardrail system prompt modifications
    system_prompt = build_guarded_system_prompt(tool.system_prompt, guardrail_result)

    # Call Ollama
    import time

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": tool.model,
                "prompt": prompt,
                "system": system_prompt,
                "stream": False,
                "options": {
                    "temperature": tool.temperature,
                    "num_predict": tool.max_tokens,
                },
            }

            response = await client.post(f"{base_url}/api/generate", json=payload)

            if response.status_code == 200:
                data = response.json()
                generation_time = int((time.time() - start_time) * 1000)
                raw_response = data.get("response", "")

                # Apply post-generation guardrails (disclaimers, filters)
                final_response = apply_response_guardrails(raw_response, guardrail_result)

                # Update usage stats
                tool.usage_count += 1
                tool.last_used_at = datetime.now(timezone.utc)

                # Log the usage for audit
                await log_ai_usage(
                    db, current_user.id if current_user else None, tool_id, tool.model,
                    request.message, final_response, generation_time,
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    guardrail_result=guardrail_result,
                    system_prompt=system_prompt,
                    was_minor=is_minor, patron_type_at_request=patron_type,
                )

                await db.commit()

                return ChatResponse(
                    success=True,
                    response=final_response,
                    tool_id=tool_id,
                    model_used=tool.model,
                    generation_time_ms=generation_time,
                )
            else:
                await log_ai_usage(
                    db, current_user.id if current_user else None, tool_id, tool.model,
                    request.message, None, None, success=False,
                    error_message=f"HTTP {response.status_code}",
                    was_minor=is_minor, patron_type_at_request=patron_type,
                )
                await db.commit()
                return ChatResponse(
                    success=False,
                    tool_id=tool_id,
                    error=f"AI service error: HTTP {response.status_code}",
                )

    except httpx.ConnectError:
        await log_ai_usage(
            db, current_user.id if current_user else None, tool_id, tool.model,
            request.message, None, None, success=False, error_message="Connection refused",
            was_minor=is_minor, patron_type_at_request=patron_type,
        )
        await db.commit()
        return ChatResponse(
            success=False,
            tool_id=tool_id,
            error="AI service unavailable - please try again later",
        )
    except Exception as e:  # noqa: BLE001  # AI tool catch-all after httpx-specific handlers
        await log_ai_usage(
            db, current_user.id if current_user else None, tool_id, tool.model,
            request.message, None, None, success=False, error_message=str(e),
            was_minor=is_minor, patron_type_at_request=patron_type,
        )
        await db.commit()
        return ChatResponse(success=False, tool_id=tool_id, error=f"Error: {str(e)}")


# ============================================================================
# Admin Endpoints
# ============================================================================


@router.post(
    "/admin/tools",
    response_model=AIToolDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_ai_tool(
    tool_data: AIToolCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIToolDetailResponse:
    """Create a new AI tool (admin only)"""
    await require_admin(current_user)

    # Check if tool_id already exists
    result = await db.execute(select(AITool).where(AITool.tool_id == tool_data.tool_id))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"AI tool with ID '{tool_data.tool_id}' already exists",
        )

    # Create tool
    tool = AITool(
        **tool_data.model_dump(),
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )

    db.add(tool)
    await db.commit()
    await db.refresh(tool)

    return tool


@router.get("/admin/tools/{tool_id}", response_model=AIToolDetailResponse)
async def get_ai_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIToolDetailResponse:
    """Get an AI tool (admin only)"""
    await require_admin(current_user)

    result = await db.execute(select(AITool).where(AITool.tool_id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI tool '{tool_id}' not found",
        )

    return tool


@router.put("/admin/tools/{tool_id}", response_model=AIToolDetailResponse)
async def update_ai_tool(
    tool_id: str,
    update_data: AIToolUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AIToolDetailResponse:
    """Update an AI tool (admin only)"""
    await require_admin(current_user)

    result = await db.execute(select(AITool).where(AITool.tool_id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI tool '{tool_id}' not found",
        )

    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(tool, field, value)

    tool.updated_by_id = current_user.id

    await db.commit()
    await db.refresh(tool)

    return tool


@router.delete("/admin/tools/{tool_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ai_tool(
    tool_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete an AI tool (admin only)"""
    await require_admin(current_user)

    result = await db.execute(select(AITool).where(AITool.tool_id == tool_id))
    tool = result.scalar_one_or_none()

    if not tool:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"AI tool '{tool_id}' not found",
        )

    await db.delete(tool)
    await db.commit()


@router.get("/admin/tools/stats/summary")
async def get_tools_stats(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
) -> dict:
    """Get AI tools usage statistics (admin only)"""
    await require_admin(current_user)

    result = await db.execute(select(AITool))
    tools = result.scalars().all()

    total_usage = sum(t.usage_count for t in tools)
    enabled_count = sum(1 for t in tools if t.enabled)

    tool_stats = [
        {
            "tool_id": t.tool_id,
            "name": t.name,
            "usage_count": t.usage_count,
            "last_used_at": t.last_used_at.isoformat() if t.last_used_at else None,
        }
        for t in sorted(tools, key=lambda x: x.usage_count, reverse=True)
    ]

    return {
        "total_tools": len(tools),
        "enabled_tools": enabled_count,
        "total_usage": total_usage,
        "tools": tool_stats,
    }
