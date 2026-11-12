# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import asyncio
from app.core.logging import get_logger
import time
from functools import lru_cache
from typing import Any, Sequence

from ..core.config import get_settings

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _model() -> Any:
    from sentence_transformers import CrossEncoder

    return CrossEncoder(
        get_settings().catalog_rerank_model_path,
        max_length=512,
        # CPU only on L30 (no GPU on stacks). Do not pass device=; let
        # the library auto-detect and use cpu.
    )


def _build_passage(item: Any) -> str:
    parts: list[str] = []
    if getattr(item, "title", None):
        parts.append(str(item.title))
    if getattr(item, "author", None):
        parts.append(f"by {item.author}")
    # subjects can come from the join table (list of Subject objects via
    # CatalogItem.subjects relationship) OR from the legacy denormalized
    # ``subjects`` text column on older rows. Handle both.
    subjects = getattr(item, "subjects", None)
    if subjects:
        if isinstance(subjects, str):
            parts.append(subjects[:300])
        else:
            try:
                labels = [
                    str(getattr(s, "label", s))
                    for s in subjects
                    if getattr(s, "label", s)
                ]
                if labels:
                    parts.append(", ".join(labels)[:300])
            except TypeError:
                # Not iterable -- give up on subjects rather than 500.
                pass
    description = getattr(item, "description", None)
    if description:
        parts.append(str(description)[:500])
    return " - ".join(p for p in parts if p)


def _rerank_sync(query: str, items: Sequence[Any]) -> list[tuple[int, float]]:
    if not items:
        return []
    pairs = [(query, _build_passage(it)) for it in items]
    scores = _model().predict(
        pairs,
        activation_fn=None,
        convert_to_numpy=True,
    )
    return sorted(
        [(int(it.id), float(s)) for it, s in zip(items, scores)],
        key=lambda pair: pair[1],
        reverse=True,
    )


async def rerank(query: str, items: Sequence[Any]) -> list[tuple[int, float]]:
    t0 = time.perf_counter()
    result = await asyncio.to_thread(_rerank_sync, query, list(items))
    ms = (time.perf_counter() - t0) * 1000.0
    logger.info(
        "catalog.rerank.latency",
        extra={
            "n_docs": len(items),
            "ms_total": round(ms, 1),
            "ms_per_doc": round(ms / max(len(items), 1), 1),
            "query_len": len(query),
        },
    )
    return result


def reset_model_cache() -> None:
    _model.cache_clear()
