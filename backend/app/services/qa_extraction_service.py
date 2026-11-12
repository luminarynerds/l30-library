# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from app.core.logging import get_logger
from typing import Optional

from app.core.cache_strategies import CacheTTL
from app.services.ollama_service import OllamaService

logger = get_logger(__name__)

QA_EXTRACTION_PROMPT = """Given this library document excerpt, generate 1-3 question-answer pairs that a library patron might ask about the information contained in it.

Rules:
- Questions should be natural, like a patron would actually ask
- Answers should be complete and directly sourced from the text
- Do not invent information not in the text
- Return ONLY a valid JSON array, no other text

Document text:
{text}

Return format: [{{"question": "...", "answer": "..."}}]"""


class QAExtractionService:
    def __init__(self):
        self.ollama = OllamaService()

    async def _call_ollama(self, prompt: str) -> Optional[str]:
        result = await self.ollama.generate(prompt, cache_ttl=CacheTTL.LONG)
        return result.get("response") if isinstance(result, dict) else None

    async def extract_from_text(self, text: str) -> list[dict]:
        try:
            prompt = QA_EXTRACTION_PROMPT.format(text=text[:3000])
            response = await self._call_ollama(prompt)
            if not response:
                return []

            response = response.strip()
            if response.startswith("```"):
                response = response.split("\n", 1)[-1].rsplit("```", 1)[0].strip()

            pairs = json.loads(response)
            if not isinstance(pairs, list):
                return []

            valid = []
            for pair in pairs:
                if isinstance(pair, dict) and "question" in pair and "answer" in pair:
                    valid.append({
                        "question": str(pair["question"]).strip(),
                        "answer": str(pair["answer"]).strip(),
                    })
            return valid

        except json.JSONDecodeError:
            logger.warning("Failed to parse Q&A extraction response as JSON")
            return []
        except Exception as e:  # noqa: BLE001 -- LLM extraction boundary: degrade to empty list on any failure, never crash caller
            logger.warning(f"Q&A extraction failed: {e}")
            return []

    async def extract_from_chunks(self, chunks: list[str]) -> list[dict]:
        all_pairs = []
        for chunk in chunks:
            pairs = await self.extract_from_text(chunk)
            all_pairs.extend(pairs)
        return all_pairs
