# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import re
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema


# Per-item mood tags this bucket can aggregate. Same set used by the
# frontend getMoodTags / patron-facing mood pill rendering. Kept in code
# (not a DB enum) because adding a new value requires a code change to
# render and filter it across the UI.
ALLOWED_MOOD_TAGS = (
    "Calm",
    "Gentle",
    "Funny",
    "Hopeful",
    "Intense",
    "Dark",
    "Mind-bending",
    "Personal",
    "Fast-paced",
)

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _validate_tags(values: List[str]) -> List[str]:
    bad = [v for v in values if v not in ALLOWED_MOOD_TAGS]
    if bad:
        raise ValueError(
            f"Unknown mood tag(s): {bad}. Allowed: {list(ALLOWED_MOOD_TAGS)}"
        )
    seen, out = set(), []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _validate_slug(value: str) -> str:
    value = value.strip().lower()
    if not _SLUG_RE.match(value):
        raise ValueError(
            "Slug must be lowercase letters, digits, and hyphens "
            "(e.g. 'quiet', 'feel-good')"
        )
    return value


class MoodCategoryBase(BaseModel):
    label: str = Field(..., min_length=1, max_length=120)
    slug: str = Field(..., min_length=1, max_length=60)
    icon: str = Field(..., min_length=1, max_length=60)
    tags: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    display_order: int = 0
    is_active: bool = True

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: str) -> str:
        return _validate_slug(v)

    @field_validator("tags")
    @classmethod
    def _tags(cls, v: List[str]) -> List[str]:
        return _validate_tags(v)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v: List[str]) -> List[str]:
        cleaned = [k.strip() for k in v if k and k.strip()]
        seen, out = set(), []
        for k in cleaned:
            kl = k.lower()
            if kl not in seen:
                seen.add(kl)
                out.append(k)
        return out


class MoodCategoryCreate(StrictInputSchema, MoodCategoryBase):
    pass


class MoodCategoryUpdate(StrictInputSchema):
    label: Optional[str] = Field(None, min_length=1, max_length=120)
    slug: Optional[str] = Field(None, min_length=1, max_length=60)
    icon: Optional[str] = Field(None, min_length=1, max_length=60)
    tags: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None

    @field_validator("slug")
    @classmethod
    def _slug(cls, v: Optional[str]) -> Optional[str]:
        return None if v is None else _validate_slug(v)

    @field_validator("tags")
    @classmethod
    def _tags(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        return None if v is None else _validate_tags(v)

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is None:
            return None
        cleaned = [k.strip() for k in v if k and k.strip()]
        seen, out = set(), []
        for k in cleaned:
            kl = k.lower()
            if kl not in seen:
                seen.add(kl)
                out.append(k)
        return out


class MoodCategoryResponse(MoodCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MoodCategoryReorder(BaseModel):
    ids: List[int] = Field(..., min_length=1)
