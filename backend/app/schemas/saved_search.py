# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas._base import StrictInputSchema


_NAME_MIN = 1
_NAME_MAX = 120


class SavedSearchCreate(StrictInputSchema):

    name: str = Field(..., min_length=_NAME_MIN, max_length=_NAME_MAX)
    query: Optional[str] = None
    filters_json: Dict[str, Any] = Field(default_factory=dict)
    sort_by: Optional[str] = Field(default=None, max_length=40)
    view_mode: Optional[str] = Field(default=None, max_length=16)

    notify_on_new: bool = False
    notify_in_app: bool = True
    notify_email: bool = False

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < _NAME_MIN:
            # Pydantic min_length is checked before validators; this guards
            # against names that are entirely whitespace.
            raise ValueError("Saved-search name cannot be blank.")
        return v

    @field_validator("filters_json", mode="before")
    @classmethod
    def _ensure_dict(cls, v: Any) -> Dict[str, Any]:
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("filters_json must be an object.")
        return v


class SavedSearchUpdate(StrictInputSchema):

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(
        default=None, min_length=_NAME_MIN, max_length=_NAME_MAX
    )
    query: Optional[str] = None
    filters_json: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = Field(default=None, max_length=40)
    view_mode: Optional[str] = Field(default=None, max_length=16)

    notify_on_new: Optional[bool] = None
    notify_in_app: Optional[bool] = None
    notify_email: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        if len(v) < _NAME_MIN:
            raise ValueError("Saved-search name cannot be blank.")
        return v

    @field_validator("filters_json")
    @classmethod
    def _validate_filters(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return None
        if not isinstance(v, dict):
            raise ValueError("filters_json must be an object.")
        return v


class SavedSearchResponse(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    query: Optional[str] = None
    filters_json: Dict[str, Any] = Field(default_factory=dict)
    sort_by: Optional[str] = None
    view_mode: Optional[str] = None
    notify_on_new: bool
    notify_in_app: bool
    notify_email: bool
    last_run_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class SavedSearchListResponse(BaseModel):
    items: List[SavedSearchResponse]
    total: int


# -- Run endpoint -----------------------------------------------------------
# Returns the same payload shape as ``POST /api/v1/catalog/search/advanced``
# so the frontend can swap data sources without branching the renderer.


class SavedSearchRunResponse(BaseModel):

    saved_search_id: uuid.UUID
    results: List[Dict[str, Any]]
    total: int
    page: int
    per_page: int
    pages: int
