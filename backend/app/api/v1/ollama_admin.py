# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Ollama Admin Controls API - Full admin management for AI guardrails, models, and usage.

Provides endpoints for:
- Content guardrails (blocked topics, disclaimers, content filters)
- Model allowlist management
- Usage limits per role
- AI usage audit logs
- AI tool CRUD with prompt editing
"""

from app.core.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_db
from ...models.ai_guardrails import AIGuardrail, AIModelAllowlist, AIUsageLimit, AIUsageLog
from ...models.ai_tools import AITool
from ...models.user import User
from .auth import get_current_user
from .dependencies import require_admin

logger = get_logger(__name__)

router = APIRouter(prefix="/admin/ollama", tags=["admin-ollama"])


# ============================================================================
# Schemas
# ============================================================================


# --- Guardrails ---

class GuardrailCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    rule_type: str = Field(..., pattern="^(blocked_topic|required_disclaimer|content_filter|response_prefix)$")
    rule_config: dict = Field(default_factory=dict)
    applies_to_tools: list = Field(default_factory=list)
    priority: int = Field(default=0, ge=0)
    enabled: bool = True


class GuardrailUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = None
    rule_type: Optional[str] = Field(default=None, pattern="^(blocked_topic|required_disclaimer|content_filter|response_prefix)$")
    rule_config: Optional[dict] = None
    applies_to_tools: Optional[list] = None
    priority: Optional[int] = Field(default=None, ge=0)
    enabled: Optional[bool] = None


class GuardrailResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    rule_type: str
    rule_config: dict = Field(default_factory=dict)
    applies_to_tools: Optional[list] = Field(default_factory=list)
    priority: int = 0
    enabled: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Model Allowlist ---

class ModelAllowlistCreate(BaseModel):
    model_name: str = Field(..., min_length=1, max_length=100)
    display_name: Optional[str] = None
    description: Optional[str] = None
    max_tokens_limit: int = Field(default=4000, ge=100, le=32000)
    allowed_temperature_min: float = Field(default=0.0, ge=0.0, le=2.0)
    allowed_temperature_max: float = Field(default=1.5, ge=0.0, le=2.0)
    enabled: bool = True


class ModelAllowlistUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    max_tokens_limit: Optional[int] = Field(default=None, ge=100, le=32000)
    allowed_temperature_min: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    allowed_temperature_max: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    enabled: Optional[bool] = None


class ModelAllowlistResponse(BaseModel):
    id: int
    model_name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    max_tokens_limit: int
    allowed_temperature_min: float
    allowed_temperature_max: float
    enabled: bool

    class Config:
        from_attributes = True


# --- Usage Limits ---

class UsageLimitCreate(BaseModel):
    role: str = Field(..., min_length=1, max_length=50)
    daily_limit: int = Field(default=50, ge=1, le=10000)
    hourly_limit: int = Field(default=10, ge=1, le=1000)
    max_tokens_per_request: int = Field(default=2000, ge=100, le=32000)
    enabled: bool = True


class UsageLimitUpdate(BaseModel):
    daily_limit: Optional[int] = Field(default=None, ge=1, le=10000)
    hourly_limit: Optional[int] = Field(default=None, ge=1, le=1000)
    max_tokens_per_request: Optional[int] = Field(default=None, ge=100, le=32000)
    enabled: Optional[bool] = None


class UsageLimitResponse(BaseModel):
    id: int
    role: str
    daily_limit: int
    hourly_limit: int
    max_tokens_per_request: int
    enabled: bool

    class Config:
        from_attributes = True


# --- Usage Logs ---

class UsageLogResponse(BaseModel):
    id: int
    user_id: Optional[int] = None
    tool_id: Optional[str] = None
    model_used: Optional[str] = None
    prompt_preview: Optional[str] = None
    response_preview: Optional[str] = None
    generation_time_ms: Optional[int] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    guardrails_triggered: list = []
    was_blocked: bool = False
    block_reason: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- AI Tool Admin ---

class AIToolAdminResponse(BaseModel):
    id: int
    tool_id: str
    name: str
    description: Optional[str] = None
    system_prompt: str
    temperature: float
    max_tokens: int
    model: str
    icon: Optional[str] = None
    category: Optional[str] = None
    enabled: bool
    in_library_only: bool
    requires_auth: bool
    sort_order: int
    usage_count: int
    last_used_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============================================================================
# Guardrails CRUD
# ============================================================================


@router.get("/guardrails", response_model=List[GuardrailResponse])
async def list_guardrails(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all AI content guardrails."""
    await require_admin(current_user)
    result = await db.execute(
        select(AIGuardrail).order_by(AIGuardrail.priority, AIGuardrail.name)
    )
    return result.scalars().all()


@router.post("/guardrails", response_model=GuardrailResponse, status_code=status.HTTP_201_CREATED)
async def create_guardrail(
    data: GuardrailCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new content guardrail."""
    await require_admin(current_user)
    guardrail = AIGuardrail(
        **data.model_dump(),
        created_by_id=current_user.id,
    )
    db.add(guardrail)
    await db.commit()
    await db.refresh(guardrail)
    logger.info("Guardrail created: %s by user %s", guardrail.name, current_user.id)
    return guardrail


@router.get("/guardrails/{guardrail_id}", response_model=GuardrailResponse)
async def get_guardrail(
    guardrail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific guardrail."""
    await require_admin(current_user)
    result = await db.execute(select(AIGuardrail).where(AIGuardrail.id == guardrail_id))
    guardrail = result.scalar_one_or_none()
    if not guardrail:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    return guardrail


@router.put("/guardrails/{guardrail_id}", response_model=GuardrailResponse)
async def update_guardrail(
    guardrail_id: int,
    data: GuardrailUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a guardrail."""
    await require_admin(current_user)
    result = await db.execute(select(AIGuardrail).where(AIGuardrail.id == guardrail_id))
    guardrail = result.scalar_one_or_none()
    if not guardrail:
        raise HTTPException(status_code=404, detail="Guardrail not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(guardrail, field, value)

    await db.commit()
    await db.refresh(guardrail)
    logger.info("Guardrail updated: %s by user %s", guardrail.name, current_user.id)
    return guardrail


@router.delete("/guardrails/{guardrail_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_guardrail(
    guardrail_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a guardrail."""
    await require_admin(current_user)
    result = await db.execute(select(AIGuardrail).where(AIGuardrail.id == guardrail_id))
    guardrail = result.scalar_one_or_none()
    if not guardrail:
        raise HTTPException(status_code=404, detail="Guardrail not found")
    await db.delete(guardrail)
    await db.commit()
    logger.info("Guardrail deleted: %s by user %s", guardrail.name, current_user.id)


# ============================================================================
# Model Allowlist CRUD
# ============================================================================


@router.get("/models/allowlist", response_model=List[ModelAllowlistResponse])
async def list_allowed_models(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all models in the allowlist."""
    await require_admin(current_user)
    result = await db.execute(
        select(AIModelAllowlist).order_by(AIModelAllowlist.model_name)
    )
    return result.scalars().all()


@router.post("/models/allowlist", response_model=ModelAllowlistResponse, status_code=status.HTTP_201_CREATED)
async def add_model_to_allowlist(
    data: ModelAllowlistCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a model to the allowlist."""
    await require_admin(current_user)

    # Check for duplicate
    result = await db.execute(
        select(AIModelAllowlist).where(AIModelAllowlist.model_name == data.model_name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Model '{data.model_name}' already in allowlist")

    model = AIModelAllowlist(**data.model_dump())
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@router.put("/models/allowlist/{model_id}", response_model=ModelAllowlistResponse)
async def update_allowed_model(
    model_id: int,
    data: ModelAllowlistUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update model allowlist entry."""
    await require_admin(current_user)
    result = await db.execute(select(AIModelAllowlist).where(AIModelAllowlist.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found in allowlist")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(model, field, value)

    await db.commit()
    await db.refresh(model)
    return model


@router.delete("/models/allowlist/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_model_from_allowlist(
    model_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a model from the allowlist."""
    await require_admin(current_user)
    result = await db.execute(select(AIModelAllowlist).where(AIModelAllowlist.id == model_id))
    model = result.scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found in allowlist")
    await db.delete(model)
    await db.commit()


# ============================================================================
# Usage Limits CRUD
# ============================================================================


@router.get("/usage-limits", response_model=List[UsageLimitResponse])
async def list_usage_limits(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all usage limits by role."""
    await require_admin(current_user)
    result = await db.execute(
        select(AIUsageLimit).order_by(AIUsageLimit.role)
    )
    return result.scalars().all()


@router.post("/usage-limits", response_model=UsageLimitResponse, status_code=status.HTTP_201_CREATED)
async def create_usage_limit(
    data: UsageLimitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create usage limit for a role."""
    await require_admin(current_user)

    result = await db.execute(
        select(AIUsageLimit).where(AIUsageLimit.role == data.role)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Limit for role '{data.role}' already exists")

    limit = AIUsageLimit(**data.model_dump())
    db.add(limit)
    await db.commit()
    await db.refresh(limit)
    return limit


@router.put("/usage-limits/{limit_id}", response_model=UsageLimitResponse)
async def update_usage_limit(
    limit_id: int,
    data: UsageLimitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a usage limit."""
    await require_admin(current_user)
    result = await db.execute(select(AIUsageLimit).where(AIUsageLimit.id == limit_id))
    limit = result.scalar_one_or_none()
    if not limit:
        raise HTTPException(status_code=404, detail="Usage limit not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(limit, field, value)

    await db.commit()
    await db.refresh(limit)
    return limit


@router.delete("/usage-limits/{limit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_usage_limit(
    limit_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a usage limit."""
    await require_admin(current_user)
    result = await db.execute(select(AIUsageLimit).where(AIUsageLimit.id == limit_id))
    limit = result.scalar_one_or_none()
    if not limit:
        raise HTTPException(status_code=404, detail="Usage limit not found")
    await db.delete(limit)
    await db.commit()


# ============================================================================
# Usage Logs (Audit Trail)
# ============================================================================


@router.get("/usage-logs")
async def list_usage_logs(
    tool_id: Optional[str] = None,
    user_id: Optional[int] = None,
    blocked_only: bool = False,
    days: int = Query(default=7, ge=1, le=90),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List AI usage audit logs with filtering."""
    await require_admin(current_user)

    since = datetime.now(timezone.utc) - timedelta(days=days)
    conditions = [AIUsageLog.created_at >= since]

    if tool_id:
        conditions.append(AIUsageLog.tool_id == tool_id)
    if user_id:
        conditions.append(AIUsageLog.user_id == user_id)
    if blocked_only:
        conditions.append(AIUsageLog.was_blocked == True)

    # Get total count
    count_q = select(func.count(AIUsageLog.id)).where(and_(*conditions))
    total = (await db.execute(count_q)).scalar() or 0

    # Get logs
    query = (
        select(AIUsageLog)
        .where(and_(*conditions))
        .order_by(AIUsageLog.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(query)
    logs = result.scalars().all()

    return {
        "items": [UsageLogResponse.model_validate(log) for log in logs],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/usage-logs/summary")
async def usage_logs_summary(
    days: int = Query(default=7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get summary statistics of AI usage."""
    await require_admin(current_user)

    since = datetime.now(timezone.utc) - timedelta(days=days)

    result = await db.execute(
        select(AIUsageLog).where(AIUsageLog.created_at >= since)
    )
    logs = result.scalars().all()

    total = len(logs)
    blocked = sum(1 for log in logs if log.was_blocked)
    successful = sum(1 for log in logs if log.success and not log.was_blocked)
    failed = sum(1 for log in logs if not log.success)

    # Per-tool breakdown
    tool_usage = {}
    for log in logs:
        tid = log.tool_id or "unknown"
        if tid not in tool_usage:
            tool_usage[tid] = {"total": 0, "blocked": 0, "tokens": 0}
        tool_usage[tid]["total"] += 1
        if log.was_blocked:
            tool_usage[tid]["blocked"] += 1
        tool_usage[tid]["tokens"] += (log.prompt_tokens or 0) + (log.completion_tokens or 0)

    # Guardrails hit counts
    guardrail_hits = {}
    for log in logs:
        for gid in (log.guardrails_triggered or []):
            guardrail_hits[str(gid)] = guardrail_hits.get(str(gid), 0) + 1

    avg_time = 0
    times = [log.generation_time_ms for log in logs if log.generation_time_ms]
    if times:
        avg_time = sum(times) // len(times)

    return {
        "period_days": days,
        "total_requests": total,
        "successful": successful,
        "blocked": blocked,
        "failed": failed,
        "block_rate": round((blocked / total * 100), 1) if total > 0 else 0,
        "avg_generation_time_ms": avg_time,
        "tool_usage": tool_usage,
        "guardrail_hits": guardrail_hits,
    }


# ============================================================================
# AI Tools Admin (expanded management)
# ============================================================================


@router.get("/tools", response_model=List[AIToolAdminResponse])
async def list_all_tools(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all AI tools with full admin details."""
    await require_admin(current_user)
    result = await db.execute(
        select(AITool).order_by(AITool.sort_order, AITool.name)
    )
    return result.scalars().all()


@router.put("/tools/{tool_id}/prompt", response_model=AIToolAdminResponse)
async def update_tool_prompt(
    tool_id: str,
    system_prompt: str = Body(..., min_length=10, embed=True),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update just the system prompt for an AI tool."""
    await require_admin(current_user)

    result = await db.execute(select(AITool).where(AITool.tool_id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail=f"AI tool '{tool_id}' not found")

    tool.system_prompt = system_prompt
    tool.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(tool)
    return tool


@router.put("/tools/{tool_id}/toggle")
async def toggle_tool(
    tool_id: str,
    enabled: bool,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Enable or disable an AI tool."""
    await require_admin(current_user)

    result = await db.execute(select(AITool).where(AITool.tool_id == tool_id))
    tool = result.scalar_one_or_none()
    if not tool:
        raise HTTPException(status_code=404, detail=f"AI tool '{tool_id}' not found")

    tool.enabled = enabled
    tool.updated_by_id = current_user.id
    await db.commit()

    action = "enabled" if enabled else "disabled"
    logger.info("AI tool %s %s by user %s", tool_id, action, current_user.id)
    return {"tool_id": tool_id, "enabled": enabled, "message": f"Tool {action}"}
