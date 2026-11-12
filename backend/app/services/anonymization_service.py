# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import json
from app.core.logging import get_logger
import re
from dataclasses import dataclass, field
from typing import Optional

from app.services.ollama_service import get_ollama_service

logger = get_logger(__name__)


@dataclass
class AnonymizationResult:
    cleaned_text: str
    detected_pii_types: list[str] = field(default_factory=list)
    ollama_enhanced: bool = False


# ── Regex patterns ────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:\+?1[\s.\-]?)?"
    r"(?:\(?\d{3}\)?[\s.\-]?)"
    r"\d{3}[\s.\-]?\d{4}"
    r"(?!\d)"
)

# Library card: LSC-XXXXXX (6 alphanumeric)
_CARD_NUMBER_RE = re.compile(r"\bLSC-[A-Z0-9]{6}\b", re.IGNORECASE)

# Ebook access card: EAC-XXXXXXXX (8 alphanumeric)
_EAC_NUMBER_RE = re.compile(r"\bEAC-[A-Z0-9]{8}\b", re.IGNORECASE)

# SSN: 123-45-6789 or 123456789
_SSN_RE = re.compile(r"\b\d{3}[\s\-]?\d{2}[\s\-]?\d{4}\b")

# DOB with keyword context
_DOB_KEYWORD_RE = re.compile(
    r"(?:(?:date\s+of\s+birth|DOB|born\s+on|birthday)\s*[:\s]\s*)"
    r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\w+\s+\d{1,2},?\s+\d{4})",
    re.IGNORECASE,
)

_REGEX_RULES: list[tuple[re.Pattern, str, str]] = [
    (_EMAIL_RE, "[EMAIL]", "email"),
    (_CARD_NUMBER_RE, "[CARD_NUMBER]", "card_number"),
    (_EAC_NUMBER_RE, "[CARD_NUMBER]", "card_number"),
    (_SSN_RE, "[SSN]", "ssn"),
    (_PHONE_RE, "[PHONE]", "phone"),
    (_DOB_KEYWORD_RE, "[DOB]", "dob"),
]

# NER placeholder mapping
_NER_LABEL_MAP: dict[str, str] = {
    "person": "[PATRON]",
    "name": "[PATRON]",
    "patron": "[PATRON]",
    "email": "[EMAIL]",
    "phone": "[PHONE]",
    "address": "[ADDRESS]",
    "location": "[ADDRESS]",
    "ssn": "[SSN]",
    "card_number": "[CARD_NUMBER]",
    "dob": "[DOB]",
    "date_of_birth": "[DOB]",
}

_NER_PII_TYPE_MAP: dict[str, str] = {
    "person": "person_name",
    "name": "person_name",
    "patron": "person_name",
    "email": "email",
    "phone": "phone",
    "address": "address",
    "location": "address",
    "ssn": "ssn",
    "card_number": "card_number",
    "dob": "dob",
    "date_of_birth": "dob",
}

_NER_SYSTEM_PROMPT = """You are a PII detection engine. Given the text below, identify ALL personally identifiable information (PII).

Return ONLY a JSON array of objects, each with:
  {"entity": "<the exact text>", "label": "<type>"}

Valid label types: person, email, phone, address, ssn, card_number, dob

If no PII is found, return an empty array: []

IMPORTANT:
- Include full names, first names, and last names as "person"
- Include street addresses, city/state/zip as "address"
- Do NOT include generic terms like "patron", "staff", "library"
- Do NOT include library branch names or public place names
- Return ONLY the JSON array, no explanation"""


class AnonymizationService:

    def __init__(self):
        self._ollama = None

    def _get_ollama(self):
        if self._ollama is None:
            self._ollama = get_ollama_service()
        return self._ollama

    async def anonymize(self, text: str) -> AnonymizationResult:
        if not text or not text.strip():
            return AnonymizationResult(cleaned_text=text)

        detected_types: set[str] = set()
        cleaned = text

        # Layer 1: Regex
        cleaned, regex_types = self._apply_regex(cleaned)
        detected_types.update(regex_types)

        # Layer 2: Ollama NER
        ollama_used = False
        try:
            ollama = self._get_ollama()
            if await ollama.is_available():
                ner_cleaned, ner_types = await self._apply_ner(cleaned)
                if ner_cleaned != cleaned:
                    cleaned = ner_cleaned
                    detected_types.update(ner_types)
                    ollama_used = True
        except Exception as e:  # noqa: BLE001 -- fail-open: Ollama optional, fall back to regex-only on any failure
            logger.warning("Ollama NER unavailable, using regex-only: %s", e)

        return AnonymizationResult(
            cleaned_text=cleaned,
            detected_pii_types=sorted(detected_types),
            ollama_enhanced=ollama_used,
        )

    def _apply_regex(self, text: str) -> tuple[str, set[str]]:
        detected: set[str] = set()
        cleaned = text
        for pattern, replacement, pii_type in _REGEX_RULES:
            if pattern.search(cleaned):
                cleaned = pattern.sub(replacement, cleaned)
                detected.add(pii_type)
        return cleaned, detected

    async def _apply_ner(self, text: str) -> tuple[str, set[str]]:
        import httpx

        ollama = self._get_ollama()
        prompt = f"{_NER_SYSTEM_PROMPT}\n\nText to analyze:\n{text}"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{ollama.base_url}/api/generate",
                    json={
                        "model": ollama.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 1000},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, asyncio.TimeoutError) as e:
            logger.warning("Ollama NER generate failed: %s", e)
            return text, set()

        response_text = data.get("response", "").strip()
        if not response_text:
            return text, set()

        try:
            if response_text.startswith("```"):
                response_text = re.sub(r"^```(?:json)?\n?", "", response_text)
                response_text = re.sub(r"\n?```$", "", response_text)
            entities = json.loads(response_text)
            if not isinstance(entities, list):
                return text, set()
        except (json.JSONDecodeError, ValueError):
            logger.debug("Failed to parse NER response: %s", response_text[:200])
            return text, set()

        detected: set[str] = set()
        cleaned = text

        # Replace longest matches first
        entities.sort(key=lambda e: len(e.get("entity", "")), reverse=True)

        for entity in entities:
            entity_text = entity.get("entity", "").strip()
            label = entity.get("label", "").lower().strip()
            if not entity_text or not label or len(entity_text) < 2:
                continue
            if label not in _NER_LABEL_MAP:
                continue
            if entity_text in cleaned:
                cleaned = cleaned.replace(entity_text, _NER_LABEL_MAP[label])
                detected.add(_NER_PII_TYPE_MAP[label])

        return cleaned, detected
