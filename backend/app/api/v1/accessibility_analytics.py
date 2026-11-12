# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Anonymous accessibility usage analytics -- JSONL file storage, no PII."""

import json
from app.core.logging import get_logger
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

logger = get_logger(__name__)

router = APIRouter(prefix="/accessibility-analytics", tags=["accessibility"])

ANALYTICS_FILE = Path("/tmp/a11y-analytics.jsonl")


class AccessibilityEvent(BaseModel):
    setting: str
    value: str
    timestamp: str


class SettingCount(BaseModel):
    setting: str
    count: int


class ModeCount(BaseModel):
    mode: str
    count: int


class AnalyticsSummary(BaseModel):
    top_settings: list[SettingCount]
    color_blind_modes: list[ModeCount]
    period: str


@router.post("/event", status_code=204)
async def record_event(event: AccessibilityEvent):  # noqa: role-check -- public a11y analytics ping, no PII
    try:
        with ANALYTICS_FILE.open("a") as f:
            f.write(json.dumps(event.model_dump()) + "\n")
    except OSError:
        logger.warning("Failed to write analytics event")


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary():
    setting_counts: Counter[str] = Counter()
    color_blind_counts: Counter[str] = Counter()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()

    if ANALYTICS_FILE.exists():
        try:
            for line in ANALYTICS_FILE.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if entry.get("timestamp", "") < cutoff:
                    continue
                setting_counts[entry["setting"]] += 1
                if entry.get("setting") == "colorBlindMode":
                    color_blind_counts[entry["value"]] += 1
        except OSError:
            logger.warning("Failed to read analytics file")

    top_settings = [
        SettingCount(setting=s, count=c)
        for s, c in setting_counts.most_common(5)
    ]
    color_blind_modes = [
        ModeCount(mode=m, count=c)
        for m, c in color_blind_counts.most_common()
    ]

    return AnalyticsSummary(
        top_settings=top_settings,
        color_blind_modes=color_blind_modes,
        period="30d",
    )
