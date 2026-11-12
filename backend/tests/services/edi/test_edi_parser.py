# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Unit tests for the EDIFACT DESADV parser.

Pure-Python tests (no DB). Pin the MEA segment behavior so the C174
composite is parsed in the order the spec defines: unit qualifier
(data element 6411) first, measurement value (6314) second.

Reference: UN/EDIFACT D.96A composite C174, components 010 (6411,
Measure unit qualifier, mandatory) and 020 (6314, Measurement value,
conditional).
"""

from __future__ import annotations

import logging
from decimal import Decimal

import pytest

from app.services.edi.edi_parser import EDIParser


def _wrap_desadv(*body_segments: str) -> str:
    """Build a minimal valid DESADV message around the given body segments.

    Keeps the envelope (UNB/UNH/BGM/.../UNT/UNZ) minimal but parseable,
    matching the structure the parser expects.
    """
    head = (
        "UNB+UNOA:1+SENDER:ZZ+RECEIVER:ZZ+260101:1200+REF0001'"
        "UNH+1+DESADV:D:96A:UN'"
        "BGM+351+SHIP123+9'"
    )
    body = "".join(body_segments)
    tail = "UNT+10+1'UNZ+1+REF0001'"
    return head + body + tail


def test_mea_standard_kgm_unit_first_value_second():
    """Standard MEA: weight unit (KGM) parsed before value (5.4)."""
    msg = _wrap_desadv("MEA+WT++KGM:5.4'")
    result = EDIParser().parse_desadv(msg)
    assert result.weight_unit == "KGM"
    assert result.total_weight == Decimal("5.4")


def test_mea_pound_unit():
    """LB unit and 12.0 value parse correctly."""
    msg = _wrap_desadv("MEA+WT++LB:12.0'")
    result = EDIParser().parse_desadv(msg)
    assert result.weight_unit == "LB"
    assert result.total_weight == Decimal("12.0")


def test_mea_missing_value_unit_preserved():
    """Missing measurement value -> unit preserved, total_weight None, no exception."""
    msg = _wrap_desadv("MEA+WT++KGM:'")
    result = EDIParser().parse_desadv(msg)
    assert result.weight_unit == "KGM"
    assert result.total_weight is None


def test_mea_malformed_value_logs_warning_and_returns_none(caplog):
    """Unparseable measurement value -> warning logged, total_weight None, no exception."""
    # app.services.edi.edi_parser's logger is a child of the "app" logger,
    # which is configured with propagate=False (app/core/logging.py) --
    # caplog's default root-attached handler never sees it. Attach directly.
    logger = logging.getLogger("app.services.edi.edi_parser")
    logger.addHandler(caplog.handler)
    logger.setLevel(logging.WARNING)
    try:
        msg = _wrap_desadv("MEA+WT++KGM:notanumber'")
        with caplog.at_level(logging.WARNING, logger="app.services.edi.edi_parser"):
            result = EDIParser().parse_desadv(msg)
    finally:
        logger.removeHandler(caplog.handler)
    assert result.weight_unit == "KGM"
    assert result.total_weight is None
    assert any("Failed to parse decimal" in record.message for record in caplog.records)


def test_no_mea_segment_keeps_defaults():
    """Positive control: DESADV without a MEA segment keeps dataclass defaults."""
    msg = _wrap_desadv()  # no body segments beyond the envelope
    result = EDIParser().parse_desadv(msg)
    assert result.total_weight is None
    assert result.weight_unit == "LB"
