# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""AI Settings API endpoints for admin fine-tuning."""

from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings

from ...core.database import get_db
from ...core.shortcuts import get_or_404
from ...models.ai_config import AIConfiguration
from ...models.user import User
from .dependencies import check_admin_access, require_admin
from .auth import get_current_user

router = APIRouter(prefix="/admin/ai", tags=["admin-ai"])


# ============ SSRF Protection ============


def _validate_ollama_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Invalid Ollama URL scheme")
    # The operator-configured default (from env OLLAMA_BASE_URL, not user input)
    # is trusted even when it resolves to a Docker-gateway/internal address.
    # User-supplied override URLs still fall through to the SSRF checks below.
    _trusted = urlparse(get_settings().ollama_base_url)
    if (parsed.hostname, parsed.port) == (_trusted.hostname, _trusted.port):
        return
    # Block cloud metadata and internal networks
    blocked_hosts = ["169.254.169.254", "metadata.google.internal", "metadata.internal"]
    if parsed.hostname in blocked_hosts:
        raise HTTPException(status_code=400, detail="Blocked URL target")
    blocked_prefixes = [
        "10.", "172.16.", "172.17.", "172.18.", "172.19.", "172.20.", "172.21.",
        "172.22.", "172.23.", "172.24.", "172.25.", "172.26.", "172.27.",
        "172.28.", "172.29.", "172.30.", "172.31.", "192.168.",
    ]
    if any(parsed.hostname.startswith(p) for p in blocked_prefixes):
        # Allow localhost and known Docker service names for local Ollama
        if parsed.hostname not in ("localhost", "127.0.0.1", "ollama", "l30-ollama"):
            raise HTTPException(status_code=400, detail="Blocked internal URL target")


# ============ Pydantic Schemas ============


class AIConfigResponse(BaseModel):
    id: int
    config_key: str
    config_value: dict
    description: Optional[str] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AIConfigUpdate(BaseModel):
    config_value: dict


class OllamaModelInfo(BaseModel):
    name: str
    size: Optional[int] = None
    modified_at: Optional[str] = None
    digest: Optional[str] = None


class OllamaStatus(BaseModel):
    connected: bool
    base_url: str
    models: List[OllamaModelInfo] = []
    error: Optional[str] = None


class TestGenerationRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 500


class TestGenerationResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    model: Optional[str] = None
    generation_time_ms: Optional[int] = None
    error: Optional[str] = None


# ============ Endpoints ============


@router.get("/configs", response_model=List[AIConfigResponse])
async def get_all_configs(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get all AI configurations (admin only)."""
    check_admin_access(current_user)

    result = await db.execute(
        select(AIConfiguration).order_by(AIConfiguration.config_key)
    )
    configs = result.scalars().all()
    return configs


@router.get("/configs/{config_key}", response_model=AIConfigResponse)
async def get_config(
    config_key: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a specific AI configuration (admin only)."""
    check_admin_access(current_user)

    result = await db.execute(select(AIConfiguration).where(AIConfiguration.config_key == config_key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")
    return config


@router.put("/configs/{config_key}", response_model=AIConfigResponse)
async def update_config(
    config_key: str,
    update: AIConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update an AI configuration (admin only)."""
    check_admin_access(current_user)

    result = await db.execute(select(AIConfiguration).where(AIConfiguration.config_key == config_key))
    config = result.scalar_one_or_none()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    config.config_value = update.config_value
    config.updated_by_id = current_user.id
    config.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(config)
    return config


@router.get("/ollama/status", response_model=OllamaStatus)
async def get_ollama_status(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Check Ollama server status and available models (admin only)."""
    check_admin_access(current_user)

    # Get Ollama config
    result = await db.execute(
        select(AIConfiguration).where(AIConfiguration.config_key == "ollama")
    )
    config = result.scalar_one_or_none()
    base_url = get_settings().ollama_base_url
    if config and config.config_value:
        base_url = config.config_value.get("base_url", base_url)

    _validate_ollama_url(base_url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                models = [
                    OllamaModelInfo(
                        name=m.get("name", ""),
                        size=m.get("size"),
                        modified_at=m.get("modified_at"),
                        digest=m.get("digest"),
                    )
                    for m in data.get("models", [])
                ]
                return OllamaStatus(connected=True, base_url=base_url, models=models)
            else:
                return OllamaStatus(
                    connected=False,
                    base_url=base_url,
                    error=f"HTTP {response.status_code}",
                )
    except httpx.ConnectError:
        return OllamaStatus(
            connected=False,
            base_url=base_url,
            error="Connection refused - Ollama may not be running",
        )
    except Exception as e:  # noqa: BLE001  # external Ollama probe — surface any error as status
        return OllamaStatus(connected=False, base_url=base_url, error=str(e))


@router.post("/test-generation", response_model=TestGenerationResponse)
async def test_generation(
    request: TestGenerationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Test AI generation with custom prompt (admin only)."""
    check_admin_access(current_user)

    # Get configs
    result = await db.execute(
        select(AIConfiguration).where(AIConfiguration.config_key == "ollama")
    )
    ollama_config = result.scalar_one_or_none()
    base_url = get_settings().ollama_base_url
    if ollama_config and ollama_config.config_value:
        base_url = ollama_config.config_value.get("base_url", base_url)

    _validate_ollama_url(base_url)

    result = await db.execute(
        select(AIConfiguration).where(AIConfiguration.config_key == "agent_chat")
    )
    agent_chat_config = result.scalar_one_or_none()

    # Use provided model or default
    model = request.model
    if not model and agent_chat_config and agent_chat_config.config_value:
        model = agent_chat_config.config_value.get("model", "llama3.2:3b")
    if not model:
        model = "llama3.2:3b"

    import time

    start_time = time.time()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "model": model,
                "prompt": request.prompt,
                "stream": False,
                "options": {
                    "temperature": request.temperature,
                    "num_predict": request.max_tokens,
                },
            }
            if request.system_prompt:
                payload["system"] = request.system_prompt

            response = await client.post(f"{base_url}/api/generate", json=payload)

            if response.status_code == 200:
                data = response.json()
                generation_time = int((time.time() - start_time) * 1000)
                return TestGenerationResponse(
                    success=True,
                    response=data.get("response", ""),
                    model=model,
                    generation_time_ms=generation_time,
                )
            else:
                return TestGenerationResponse(
                    success=False, error=f"HTTP {response.status_code}: {response.text}"
                )
    except httpx.ConnectError:
        return TestGenerationResponse(
            success=False, error="Connection refused - Ollama may not be running"
        )
    except Exception as e:  # noqa: BLE001  # external Ollama probe — surface any error as status
        return TestGenerationResponse(success=False, error=str(e))


@router.post("/ollama/pull-model")
async def pull_ollama_model(
    model_name: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Start pulling an Ollama model (admin only). Returns immediately, pull happens in background."""
    check_admin_access(current_user)

    # Get Ollama config
    result = await db.execute(
        select(AIConfiguration).where(AIConfiguration.config_key == "ollama")
    )
    config = result.scalar_one_or_none()
    base_url = get_settings().ollama_base_url
    if config and config.config_value:
        base_url = config.config_value.get("base_url", base_url)

    _validate_ollama_url(base_url)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Just initiate the pull - it will continue in background
            response = await client.post(
                f"{base_url}/api/pull",
                json={"name": model_name, "stream": False},
                timeout=300.0,  # 5 minute timeout for pull
            )
            if response.status_code == 200:
                return {"message": f"Model {model_name} pulled successfully"}
            else:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Failed to pull model: {response.text}",
                )
    except httpx.ConnectError:
        raise HTTPException(status_code=503, detail="Ollama server not reachable") from None
    except httpx.TimeoutException:
        return {
            "message": f"Model {model_name} pull initiated - this may take several minutes"
        }


@router.get("/stats")
async def get_ai_stats(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    """Get AI usage statistics (admin only)."""
    check_admin_access(current_user)

    from ...models.board import BoardMeetingBrief

    # Count briefs by status
    result = await db.execute(select(BoardMeetingBrief))
    briefs = result.scalars().all()

    total = len(briefs)
    completed = sum(1 for b in briefs if b.status == "completed")
    failed = sum(1 for b in briefs if b.status == "failed")
    generating = sum(1 for b in briefs if b.status == "generating")

    # Average generation time
    times = [b.generation_time_ms for b in briefs if b.generation_time_ms]
    avg_time = sum(times) / len(times) if times else 0

    # Models used
    models = {}
    for b in briefs:
        if b.ai_model_used:
            models[b.ai_model_used] = models.get(b.ai_model_used, 0) + 1

    return {
        "total_generations": total,
        "completed": completed,
        "failed": failed,
        "generating": generating,
        "success_rate": (completed / total * 100) if total > 0 else 0,
        "average_generation_time_ms": int(avg_time),
        "models_used": models,
    }
