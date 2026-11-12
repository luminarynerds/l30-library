# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator

from app.schemas._base import StrictInputSchema


# ==================== Article Versions ====================

class ArticleVersionResponse(BaseModel):
    id: int
    version_number: int
    title: str
    change_notes: Optional[str] = None
    changed_by_id: int
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ==================== Staff Knowledge Article ====================

class StaffKnowledgeArticleCreate(StrictInputSchema):
    title: str = Field(..., min_length=5, max_length=250)
    description: Optional[str] = Field(None, max_length=500)
    content: str = Field(..., min_length=10)
    content_type: str  # policy, procedure, how_to, decision_tree, etc.
    category: str = Field(..., max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = Field(None, max_length=500, description="Plain-language TL;DR")
    transcript: Optional[str] = Field(None, description="Text transcript / alternate format of the article")
    audio_url: Optional[str] = Field(None, max_length=500, description="Optional TTS/audio version")
    is_published: bool = True


class StaffKnowledgeArticleUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=5, max_length=250)
    description: Optional[str] = Field(None, max_length=500)
    content: Optional[str] = Field(None, min_length=10)
    category: Optional[str] = Field(None, max_length=100)
    subcategory: Optional[str] = Field(None, max_length=100)
    tags: Optional[str] = Field(None, max_length=500)
    summary: Optional[str] = Field(None, max_length=500, description="Plain-language TL;DR")
    transcript: Optional[str] = Field(None, description="Text transcript / alternate format of the article")
    audio_url: Optional[str] = Field(None, max_length=500, description="Optional TTS/audio version")
    is_published: Optional[bool] = None
    change_notes: Optional[str] = Field(None, description="Notes about this change for version history")


class StaffKnowledgeArticleResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    content: str
    content_type: str
    category: str
    subcategory: Optional[str] = None
    tags: Optional[str] = None
    summary: Optional[str] = None
    transcript: Optional[str] = None
    audio_url: Optional[str] = None
    is_published: bool
    current_version: int
    view_count: int
    bookmark_count: int
    helpful_count: int
    unhelpful_count: int
    created_by_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_verified_at: datetime | None = None
    model_config = {"from_attributes": True}


class StaffKnowledgeArticleWithVersions(StaffKnowledgeArticleResponse):
    versions: List[ArticleVersionResponse] = []


# ==================== Decision Trees ====================

class DecisionTreeCreate(StrictInputSchema):
    title: str = Field(..., min_length=5, max_length=250)
    description: Optional[str] = Field(None, max_length=500)
    category: str = Field(..., max_length=100)
    tree_data: Any = Field(..., description="JSON structure with decision nodes")
    is_published: bool = True


class DecisionTreeUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=5, max_length=250)
    description: Optional[str] = Field(None, max_length=500)
    tree_data: Optional[Any] = None
    is_published: Optional[bool] = None


class DecisionTreeResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: str
    tree_data: Any
    is_published: bool
    view_count: int
    created_by_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ==================== Video Tutorials ====================

class VideoTutorialCreate(StrictInputSchema):
    title: str = Field(..., min_length=5, max_length=250)
    description: Optional[str] = Field(None, max_length=500)
    category: str = Field(..., max_length=100)
    video_url: str = Field(..., max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    related_article_ids: Optional[List[int]] = None
    is_published: bool = True


class VideoTutorialUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=5, max_length=250)
    description: Optional[str] = Field(None, max_length=500)
    video_url: Optional[str] = Field(None, max_length=500)
    thumbnail_url: Optional[str] = Field(None, max_length=500)
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    related_article_ids: Optional[List[int]] = None
    is_published: Optional[bool] = None


class VideoTutorialResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    category: str
    video_url: str
    thumbnail_url: Optional[str] = None
    duration_seconds: Optional[int] = None
    transcript: Optional[str] = None
    related_article_ids: List[int] = []
    is_published: bool
    view_count: int
    created_by_id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}

    # Older rows were seeded with a NULL related_article_ids (bypassing the ORM
    # default=[]); coerce None to [] so they serialize instead of 500ing.
    @field_validator("related_article_ids", mode="before")
    @classmethod
    def _none_to_empty_list(cls, v):
        return v if v is not None else []


# ==================== Onboarding Checklists ====================

class ChecklistItemUpdate(StrictInputSchema):
    task_id: str
    completed: bool
    completed_at: Optional[datetime] = None


class OnboardingChecklistCreate(StrictInputSchema):
    user_id: int
    title: str = Field(..., min_length=5, max_length=250)
    description: Optional[str] = None
    checklist_items: List[dict] = Field(
        ...,
        description="Array of task objects with id, title, description, due_days, completed, completed_at"
    )
    assigned_by_id: Optional[int] = None


class OnboardingChecklistUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, min_length=5, max_length=250)
    description: Optional[str] = None
    checklist_items: Optional[List[dict]] = None


class OnboardingChecklistResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: Optional[str] = None
    checklist_items: List[dict]
    is_completed: bool
    start_date: datetime
    completed_date: Optional[datetime] = None
    assigned_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model_config = {"from_attributes": True}


# ==================== Staff Q&A ====================

class StaffQACreate(StrictInputSchema):
    question: str = Field(..., min_length=10)
    category: str = Field(..., max_length=100)
    tags: Optional[str] = Field(None, max_length=500)
    related_article_id: Optional[int] = None


class StaffQAAnswerCreate(StrictInputSchema):
    answer: str = Field(..., min_length=10)


class StaffQAResponse(BaseModel):
    id: int
    question: str
    category: str
    tags: Optional[str] = None
    asked_by_id: int
    related_article_id: Optional[int] = None
    is_answered: bool
    is_closed: bool
    answer: Optional[str] = None
    answered_by_id: Optional[int] = None
    answer_upvotes: int
    created_at: datetime | None = None
    answered_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ==================== Bookmarks ====================

class ArticleBookmarkCreate(StrictInputSchema):
    article_id: int


class ArticleBookmarkResponse(BaseModel):
    id: int
    user_id: int
    article_id: int
    created_at: datetime | None = None
    model_config = {"from_attributes": True}


# ==================== Content Flags ====================

class ContentFlagCreate(StrictInputSchema):
    article_id: int
    reason: str = Field(..., max_length=100)  # outdated, incorrect, unclear, etc.
    description: str = Field(..., min_length=10)


class ContentFlagResolve(BaseModel):
    status: str  # resolved, dismissed
    reviewer_notes: Optional[str] = None


class ContentFlagResponse(BaseModel):
    id: int
    article_id: int
    reason: str
    description: str
    status: str
    flagged_by_id: int
    reviewed_by_id: Optional[int] = None
    created_at: datetime | None = None
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None

    model_config = {"from_attributes": True}


# ==================== Search Responses ====================

class ArticleSearchResult(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    summary: Optional[str] = None
    content_type: str
    category: str
    view_count: int
    bookmark_count: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
    last_verified_at: datetime | None = None
    model_config = {"from_attributes": True}


class SearchResponse(BaseModel):
    total: int
    results: List[Any]
