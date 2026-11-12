# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from app.core.logging import get_logger
from typing import Optional

import httpx

from app.core.config import Settings
from app.models.acquisition_rationale import AcquisitionRationale
from app.models.catalog import CatalogItem

logger = get_logger(__name__)


class LibrarianAgentClient:

    def __init__(self, settings: Settings):
        self.base_url = (settings.librarian_agent_base_url or "").rstrip("/")
        self.slug = settings.librarian_agent_library_slug
        self.api_key = settings.librarian_agent_api_key or ""
        # Tight timeout so the save path stays responsive when librarian-kb
        # is slow/unreachable. Failures are swallowed anyway.
        self.timeout = 5.0

    # ---------------- internal helpers ----------------

    def _headers(self) -> dict[str, str]:
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if self.api_key:
            h["X-API-Key"] = self.api_key
        return h

    @staticmethod
    def _compose_body(rationale: AcquisitionRationale) -> str:
        summary = (rationale.public_summary or "").strip()
        if summary:
            return summary

        # Fallback composition — keep terse, KB ranker will embed it.
        # Only include clauses with real values so we don't render dangling
        # em-dash placeholders (e.g. "Signal: foo — ." when signal_note empty).
        signal_type = getattr(rationale.signal_type, "value", rationale.signal_type)
        primary = (rationale.primary_use_case_slug or "").strip()
        signal_note = (rationale.signal_note or "").strip()
        policy = (rationale.policy_clause or "").strip()

        parts: list[str] = []
        if primary:
            parts.append(f"Primary use case: {primary}")
        if signal_type:
            if signal_note:
                parts.append(f"Signal: {signal_type} — {signal_note}")
            else:
                parts.append(f"Signal: {signal_type}")
        if policy:
            parts.append(f"Policy: {policy}")
        return ". ".join(parts) + ("." if parts else "")

    @staticmethod
    def _tags(rationale: AcquisitionRationale) -> list[str]:
        raw = ["rationale", rationale.primary_use_case_slug]
        return [t.lower() for t in raw if isinstance(t, str) and t.strip()]

    def _build_emit_payload(
        self,
        *,
        catalog_item: CatalogItem,
        rationale: AcquisitionRationale,
    ) -> dict:
        signal_type = getattr(rationale.signal_type, "value", rationale.signal_type)
        return {
            "slug": self.slug,
            "kind": "acquisition_rationale",
            "external_id": f"rationale-{rationale.id}",
            "title": f"Acquisition rationale: {catalog_item.title}",
            "body": self._compose_body(rationale),
            "metadata": {
                "catalog_item_id": rationale.catalog_item_id,
                "rationale_id": rationale.id,
                "primary_use_case": rationale.primary_use_case_slug,
                "signal_note": (rationale.signal_note or ""),
                "policy_clause": rationale.policy_clause,
                "anticipated_challenge_reasons": list(
                    rationale.anticipated_challenge_reasons or []
                ),
                "signal_type": signal_type,
                "behavior_tags": list(rationale.secondary_use_case_slugs or []),
            },
            "tags": self._tags(rationale),
        }

    # ---------------- public API ----------------

    async def emit_rationale_aku(
        self,
        *,
        catalog_item: CatalogItem,
        rationale: AcquisitionRationale,
    ) -> Optional[str]:
        if not self.base_url:
            return None  # not configured — silent skip

        url = f"{self.base_url}/v1/akus/emit"
        try:
            payload = self._build_emit_payload(
                catalog_item=catalog_item, rationale=rationale,
            )
        except (AttributeError, TypeError, ValueError) as e:  # defensive — payload build should never raise
            logger.warning(
                "librarian-agent emit payload build failed for rationale %s: %s",
                getattr(rationale, "id", "?"), e,
            )
            return None

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
        except httpx.HTTPError as e:
            logger.warning(
                "librarian-agent emit network error for rationale %s: %s",
                rationale.id, e,
            )
            return None
        except Exception as e:  # noqa: BLE001 - belt-and-suspenders boundary: save path must not propagate KB failures
            logger.warning(
                "librarian-agent emit unexpected error for rationale %s: %s",
                rationale.id, e,
            )
            return None

        if resp.status_code < 200 or resp.status_code >= 300:
            logger.warning(
                "librarian-agent emit non-2xx for rationale %s: %s %s",
                rationale.id, resp.status_code, resp.text[:200],
            )
            return None

        try:
            return resp.json().get("aku_id")
        except (ValueError, AttributeError) as e:
            logger.warning(
                "librarian-agent emit bad JSON for rationale %s: %s",
                rationale.id, e,
            )
            return None

    async def search_similar_rationales(
        self,
        *,
        query: str,
        limit: int = 5,
    ) -> list[dict]:
        if not self.base_url:
            return []

        url = f"{self.base_url}/v1/search"
        payload = {
            "query": query,
            "slugs": [self.slug],
            "kind": "acquisition_rationale",
            "limit": limit,
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
        except httpx.HTTPError as e:
            logger.warning("librarian-agent search network error: %s", e)
            return []
        except Exception as e:  # noqa: BLE001 - belt-and-suspenders boundary: search results must degrade gracefully
            logger.warning("librarian-agent search unexpected error: %s", e)
            return []

        if resp.status_code < 200 or resp.status_code >= 300:
            logger.warning(
                "librarian-agent search non-2xx: %s %s",
                resp.status_code, resp.text[:200],
            )
            return []

        try:
            hits = resp.json().get("hits", [])
            return hits if isinstance(hits, list) else []
        except (ValueError, AttributeError) as e:
            logger.warning("librarian-agent search bad JSON: %s", e)
            return []
