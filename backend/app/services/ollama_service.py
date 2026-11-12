# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import hashlib
import json
from app.core.logging import get_logger
import os
import time
from typing import Any, List, Optional

import httpx

from ..core.cache import get_cached, set_cached
from ..core.config import get_settings

logger = get_logger(__name__)


def _build_llm_cache_key(
    *,
    model: str,
    system_prompt: Optional[str],
    payload: Any,
    max_tokens: int,
    temperature: float,
) -> str:
    blob = json.dumps(
        {
            "m": model,
            "s": system_prompt,
            "p": payload,
            "n": max_tokens,
            "t": temperature,
        },
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(blob.encode()).hexdigest()[:24]
    return f"llm:ollama:{digest}"


class OllamaService:

    def __init__(self, base_url: str = None, model: str = "llama3.2"):
        base_url = base_url or get_settings().ollama_base_url
        self.base_url = base_url
        self.model = model
        self.timeout = 120.0  # 2 minutes for generation

    async def is_available(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            logger.debug(f"Ollama not available: {e}")
            return False

    async def list_models(self) -> list[str]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
        except (httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError) as e:
            logger.error(f"Failed to list Ollama models: {e}")
        return []

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        cache_ttl: Optional[int] = None,
    ) -> dict:
        start_time = time.time()

        cache_key: Optional[str] = None
        if cache_ttl is not None:
            cache_key = _build_llm_cache_key(
                model=self.model,
                system_prompt=system_prompt,
                payload=prompt,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            cached = await get_cached(cache_key)
            if cached is not None:
                cached["cached"] = True
                cached["generation_time_ms"] = 0
                return cached

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

                generation_time = int((time.time() - start_time) * 1000)

                result = {
                    "response": data.get("message", {}).get("content", ""),
                    "model": self.model,
                    "generation_time_ms": generation_time,
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "cached": False,
                }

                if cache_key is not None and result["response"]:
                    await set_cached(cache_key, result, ttl_seconds=cache_ttl)

                return result

        except httpx.ConnectError as e:
            logger.error("Ollama connection failed - is the service running?")
            raise OllamaError(
                "Ollama service not running. Start with: ollama serve"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("Ollama request timed out")
            raise OllamaError(
                "Request timed out - model may be too slow or prompt too long"
            ) from e
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise OllamaError(f"Generation failed: {str(e)}") from e

    async def chat(
        self,
        messages: List[dict],
        system_prompt: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        cache_ttl: Optional[int] = None,
    ) -> dict:
        start_time = time.time()

        cache_key: Optional[str] = None
        if cache_ttl is not None:
            cache_key = _build_llm_cache_key(
                model=self.model,
                system_prompt=system_prompt,
                payload=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            cached = await get_cached(cache_key)
            if cached is not None:
                cached["cached"] = True
                cached["generation_time_ms"] = 0
                return cached

        chat_messages = []
        if system_prompt:
            chat_messages.append({"role": "system", "content": system_prompt})
        chat_messages.extend(messages)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model,
                        "messages": chat_messages,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": max_tokens,
                        },
                    },
                )
                response.raise_for_status()
                data = response.json()

                generation_time = int((time.time() - start_time) * 1000)

                result = {
                    "response": data.get("message", {}).get("content", ""),
                    "model": self.model,
                    "generation_time_ms": generation_time,
                    "prompt_tokens": data.get("prompt_eval_count", 0),
                    "completion_tokens": data.get("eval_count", 0),
                    "cached": False,
                }

                if cache_key is not None and result["response"]:
                    await set_cached(cache_key, result, ttl_seconds=cache_ttl)

                return result

        except httpx.ConnectError as e:
            logger.error("Ollama connection failed - is the service running?")
            raise OllamaError(
                "Ollama service not running. Start with: ollama serve"
            ) from e
        except httpx.TimeoutException as e:
            logger.error("Ollama request timed out")
            raise OllamaError(
                "Request timed out - model may be too slow or prompt too long"
            ) from e
        except Exception as e:
            logger.error(f"Ollama error: {e}")
            raise OllamaError(f"Generation failed: {str(e)}") from e


class OllamaError(Exception):

    pass


# Singleton instance with default config
_default_service: Optional[OllamaService] = None


def get_ollama_service(base_url: str = None, model: str = None) -> OllamaService:
    global _default_service

    # Use environment variables or defaults
    base_url = base_url or get_settings().ollama_base_url
    model = model or os.getenv("OLLAMA_MODEL", "llama3.2")

    if (
        _default_service is None
        or _default_service.base_url != base_url
        or _default_service.model != model
    ):
        _default_service = OllamaService(base_url=base_url, model=model)

    return _default_service
