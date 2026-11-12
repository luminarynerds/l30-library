# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Tests for the catalog cross-encoder reranker.

Two layers:

* Unit tests (always run) -- mock ``CrossEncoder`` so we never load the
  ~600MB model in CI. Cover the pure ranking logic, passage construction,
  empty-input handling, and latency-log emission.
* Integration test (skipped by default) -- exercises the real model.
  Opt-in via ``SKIP_RERANK_MODEL_TEST=0`` to avoid OOMing the VPS when
  someone runs the full suite. Real-model latency benchmarks belong on
  prod hardware as post-deploy verification, not in pytest.
"""
from __future__ import annotations

import logging
import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services import catalog_reranker
from app.services.catalog_reranker import (
    _build_passage,
    _rerank_sync,
    rerank,
    reset_model_cache,
)


@pytest.fixture(autouse=True)
def _clear_model_cache():
    """Each test starts with no cached model so patches take effect."""
    reset_model_cache()
    yield
    reset_model_cache()


def _make_item(item_id: int, **fields) -> SimpleNamespace:
    """Construct a stand-in for a CatalogItem with just the fields the
    reranker reads. Avoids dragging the ORM into unit tests."""
    defaults = {
        "id": item_id,
        "title": None,
        "author": None,
        "subjects": None,
        "description": None,
    }
    defaults.update(fields)
    return SimpleNamespace(**defaults)


# ---------------------------------------------------------------------------
# _build_passage
# ---------------------------------------------------------------------------


def test_build_passage_orders_fields_title_author_subjects_description():
    item = _make_item(
        1,
        title="The Goldfinch",
        author="Donna Tartt",
        subjects="Coming-of-age fiction",
        description="A boy survives a museum bombing.",
    )
    passage = _build_passage(item)
    # Title leads, description trails -- field order matters when the
    # cross-encoder truncates at 512 tokens.
    assert passage.startswith("The Goldfinch")
    assert "by Donna Tartt" in passage
    assert "Coming-of-age fiction" in passage
    assert passage.endswith("A boy survives a museum bombing.")


def test_build_passage_handles_missing_fields():
    """A bare-title item should produce just the title, no separators."""
    item = _make_item(1, title="Title Only")
    assert _build_passage(item) == "Title Only"


def test_build_passage_iterable_subjects_with_label():
    """Subjects from the join table arrive as objects with .label."""
    subj_a = SimpleNamespace(label="Mystery")
    subj_b = SimpleNamespace(label="Detective fiction")
    item = _make_item(1, title="X", subjects=[subj_a, subj_b])
    passage = _build_passage(item)
    assert "Mystery" in passage and "Detective fiction" in passage


def test_build_passage_truncates_long_description():
    """Description should be clipped at 500 chars so the 512-token cap
    leaves room for title/author/subjects."""
    long_desc = "x" * 800
    item = _make_item(1, title="Y", description=long_desc)
    passage = _build_passage(item)
    # The 500-char clip lives inside passage along with the title+separator.
    assert len(passage) <= len("Y") + len(" - ") + 500


# ---------------------------------------------------------------------------
# _rerank_sync
# ---------------------------------------------------------------------------


def test_rerank_sync_orders_by_score_desc():
    """Mock the model to return known scores and verify the output order."""
    items = [
        _make_item(10, title="A"),
        _make_item(20, title="B"),
        _make_item(30, title="C"),
    ]
    fake_model = MagicMock()
    fake_model.predict.return_value = [0.2, 0.9, 0.5]

    with patch.object(catalog_reranker, "_model", return_value=fake_model):
        result = _rerank_sync("query", items)

    assert result == [(20, 0.9), (30, 0.5), (10, 0.2)]
    # The model was called with (query, passage) pairs in input order.
    call_args = fake_model.predict.call_args
    pairs = call_args.args[0]
    assert [p[0] for p in pairs] == ["query"] * 3
    assert pairs[0][1] == "A" and pairs[1][1] == "B" and pairs[2][1] == "C"


def test_rerank_sync_empty_input_returns_empty_without_loading_model():
    """Empty input must short-circuit before touching the model -- otherwise
    cold-loading 600MB just to rerank zero docs would be a foot-gun."""
    fake_model = MagicMock()
    with patch.object(catalog_reranker, "_model", return_value=fake_model):
        result = _rerank_sync("q", [])
    assert result == []
    fake_model.predict.assert_not_called()


def test_rerank_sync_uses_sigmoid_scores_directly():
    """Passing ``activation_fn=None`` is load-bearing: bge-reranker-v2-m3
    returns sigmoid 0-1 from its own classifier head, and adding another
    sigmoid would compress everything into [0.5, 0.73]."""
    items = [_make_item(1, title="A"), _make_item(2, title="B")]
    fake_model = MagicMock()
    fake_model.predict.return_value = [0.15, 0.42]

    with patch.object(catalog_reranker, "_model", return_value=fake_model):
        _rerank_sync("q", items)

    kwargs = fake_model.predict.call_args.kwargs
    assert kwargs.get("activation_fn") is None
    assert kwargs.get("convert_to_numpy") is True


# ---------------------------------------------------------------------------
# rerank (async wrapper)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rerank_async_returns_sorted_results():
    items = [_make_item(1, title="A"), _make_item(2, title="B")]
    fake_model = MagicMock()
    fake_model.predict.return_value = [0.1, 0.9]

    with patch.object(catalog_reranker, "_model", return_value=fake_model):
        result = await rerank("query", items)

    assert result == [(2, 0.9), (1, 0.1)]


@pytest.mark.asyncio
async def test_rerank_async_emits_latency_log(caplog):
    """Production needs the latency log to tune top_n_candidates without
    deploying patched logging."""
    items = [_make_item(1, title="A")]
    fake_model = MagicMock()
    fake_model.predict.return_value = [0.5]

    caplog.set_level(logging.INFO, logger="app.services.catalog_reranker")
    # app/core/logging.py's setup_logging() (run at import time by app.main,
    # which most other test files import) sets propagate=False on the "app"
    # logger. Once that's happened anywhere in this test session, records
    # from app.services.catalog_reranker never reach caplog's root-attached
    # handler. Attach the handler directly to this logger so the test
    # doesn't depend on suite-wide import order.
    reranker_logger = logging.getLogger("app.services.catalog_reranker")
    reranker_logger.addHandler(caplog.handler)
    try:
        with patch.object(catalog_reranker, "_model", return_value=fake_model):
            await rerank("query", items)
    finally:
        reranker_logger.removeHandler(caplog.handler)

    matching = [r for r in caplog.records if r.message == "catalog.rerank.latency"]
    assert matching, "expected catalog.rerank.latency log line"
    rec = matching[0]
    assert getattr(rec, "n_docs", None) == 1
    assert getattr(rec, "ms_total", None) is not None
    assert getattr(rec, "ms_per_doc", None) is not None


# ---------------------------------------------------------------------------
# Integration -- real model. Skipped by default to keep CI fast and to
# avoid OOMing the shared VPS during pytest runs.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("SKIP_RERANK_MODEL_TEST", "1") == "1",
    reason="real CrossEncoder load is ~600MB; opt in with SKIP_RERANK_MODEL_TEST=0",
)
@pytest.mark.asyncio
@pytest.mark.slow
async def test_real_model_reorders_semantically():
    """Smoke test: the real model puts the topically-aligned doc on top.

    Construct two passages with similar lexeme density to the query but
    very different semantic fit. The cross-encoder should rank the
    children's-book passage above the academic linguistics passage for a
    "picture book about a worried child" query.
    """
    reset_model_cache()
    items = [
        _make_item(
            1,
            title="The Phonology of English",
            author="A. Linguist",
            description=(
                "A scholarly survey of stress assignment, prosodic structure, "
                "and the syntax-phonology interface."
            ),
        ),
        _make_item(
            2,
            title="First Day Jitters",
            author="Julie Danneberg",
            description=(
                "A picture book about a worried child preparing for the "
                "first day of school."
            ),
        ),
    ]
    result = await rerank("picture book about a worried child", items)
    # Picture book wins.
    assert result[0][0] == 2
