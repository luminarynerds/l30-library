# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import asyncio
from app.core.logging import get_logger
from typing import Any

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.branding import branding
from ..models.bibframe import (
    AuthorityLink,
    AuthoritySource,
    BibframeContributor,
    BibframeSubject,
)

logger = get_logger(__name__)

LC_NAMES_SUGGEST = "https://id.loc.gov/authorities/names/suggest2"
LC_SUBJECTS_SUGGEST = "https://id.loc.gov/authorities/subjects/suggest2"
REQUEST_DELAY = 1.0  # seconds between LC API calls


async def _query_lc_suggest(
    client: httpx.AsyncClient,
    url: str,
    query: str,
) -> list[dict[str, str]]:
    try:
        resp = await client.get(url, params={"q": query})
        resp.raise_for_status()
        data = resp.json()
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError):
        logger.debug("LC suggest2 request failed for %r", query)
        return []

    # suggest2 returns {"hits": [{"uri": ..., "aLabel": ...}, ...]}
    hits = data.get("hits", [])
    results = []
    for hit in hits:
        label = hit.get("aLabel") or hit.get("suggestLabel") or ""
        uri = hit.get("uri", "")
        if label and uri:
            results.append({"label": label, "uri": uri})
    return results


def _normalize(name: str) -> str:
    return name.lower().strip().rstrip(".,;:")


def _extract_authority_id(uri: str) -> str:
    return uri.rstrip("/").split("/")[-1]


async def reconcile_unlinked_contributors(
    db: AsyncSession,
    batch_size: int = 50,
) -> dict[str, Any]:

    subq = (
        select(AuthorityLink.contributor_id)
        .where(AuthorityLink.contributor_id.isnot(None))
    )
    stmt = (
        select(BibframeContributor)
        .where(~BibframeContributor.id.in_(subq))
        .limit(batch_size)
    )
    result = await db.execute(stmt)
    unlinked = result.scalars().all()

    total = len(unlinked)
    new_links = 0
    processed = 0

    async with httpx.AsyncClient(
        timeout=15,
        headers={"User-Agent": branding.USER_AGENT},
        follow_redirects=True,
    ) as client:
        for contributor in unlinked:
            processed += 1
            if not contributor.name:
                continue

            candidates = await _query_lc_suggest(
                client, LC_NAMES_SUGGEST, contributor.name
            )

            for candidate in candidates:
                if _normalize(candidate["label"]) == _normalize(contributor.name):
                    authority_id = _extract_authority_id(candidate["uri"])
                    link = AuthorityLink(
                        source=AuthoritySource.LCNAF,
                        authority_id=authority_id,
                        authority_uri=candidate["uri"],
                        authority_label=candidate["label"],
                        link_type="exactMatch",
                        confidence=1.0,
                        verified=False,
                        contributor_id=contributor.id,
                    )
                    db.add(link)
                    contributor.lcnaf_id = authority_id
                    new_links += 1
                    break

            if processed % 10 == 0 or processed == total:
                logger.info(
                    "Reconciled %d/%d contributors, %d new links created",
                    processed, total, new_links,
                )

            await asyncio.sleep(REQUEST_DELAY)

    await db.commit()
    return {"processed": processed, "new_links": new_links, "total_unlinked": total}


async def reconcile_unlinked_subjects(
    db: AsyncSession,
    batch_size: int = 50,
) -> dict[str, Any]:

    subq = (
        select(AuthorityLink.subject_id)
        .where(AuthorityLink.subject_id.isnot(None))
    )
    stmt = (
        select(BibframeSubject)
        .where(~BibframeSubject.id.in_(subq))
        .limit(batch_size)
    )
    result = await db.execute(stmt)
    unlinked = result.scalars().all()

    total = len(unlinked)
    new_links = 0
    processed = 0

    async with httpx.AsyncClient(
        timeout=15,
        headers={"User-Agent": branding.USER_AGENT},
        follow_redirects=True,
    ) as client:
        for subject in unlinked:
            processed += 1
            if not subject.label:
                continue

            candidates = await _query_lc_suggest(
                client, LC_SUBJECTS_SUGGEST, subject.label
            )

            for candidate in candidates:
                if _normalize(candidate["label"]) == _normalize(subject.label):
                    authority_id = _extract_authority_id(candidate["uri"])
                    link = AuthorityLink(
                        source=AuthoritySource.LCSH,
                        authority_id=authority_id,
                        authority_uri=candidate["uri"],
                        authority_label=candidate["label"],
                        link_type="exactMatch",
                        confidence=1.0,
                        verified=False,
                        subject_id=subject.id,
                    )
                    db.add(link)
                    subject.lcsh_id = authority_id
                    subject.source = AuthoritySource.LCSH
                    new_links += 1
                    break

            if processed % 10 == 0 or processed == total:
                logger.info(
                    "Reconciled %d/%d subjects, %d new links created",
                    processed, total, new_links,
                )

            await asyncio.sleep(REQUEST_DELAY)

    await db.commit()
    return {"processed": processed, "new_links": new_links, "total_unlinked": total}


async def get_reconciliation_stats(db: AsyncSession) -> dict[str, Any]:

    total_contributors = await db.scalar(
        select(func.count()).select_from(BibframeContributor)
    )
    linked_contributors = await db.scalar(
        select(func.count(func.distinct(AuthorityLink.contributor_id))).where(
            AuthorityLink.contributor_id.isnot(None)
        )
    )

    total_subjects = await db.scalar(
        select(func.count()).select_from(BibframeSubject)
    )
    linked_subjects = await db.scalar(
        select(func.count(func.distinct(AuthorityLink.subject_id))).where(
            AuthorityLink.subject_id.isnot(None)
        )
    )

    return {
        "contributors": {
            "total": total_contributors or 0,
            "linked": linked_contributors or 0,
            "unlinked": (total_contributors or 0) - (linked_contributors or 0),
        },
        "subjects": {
            "total": total_subjects or 0,
            "linked": linked_subjects or 0,
            "unlinked": (total_subjects or 0) - (linked_subjects or 0),
        },
    }
