# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema


# ============ RUBRIC CRITERION SCHEMAS ============


class RubricCriterionBase(BaseModel):
    name: str = Field(..., max_length=255, description="Name of the criterion (e.g., 'Fairness and Bias')")
    description: Optional[str] = Field(None, description="Expanded description of this criterion")
    levels: Dict[str, List[str]] = Field(
        ...,
        description="Score to description mapping. Keys are score strings ('4','3','2','1'), values are lists of bullet points."
    )
    weight: int = Field(default=1, ge=1, description="Weight for scoring (1 = normal)")
    sort_order: int = Field(default=0, description="Display order")


class RubricCriterionCreate(StrictInputSchema, RubricCriterionBase):
    pass


class RubricCriterionUpdate(StrictInputSchema):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    levels: Optional[Dict[str, List[str]]] = None
    weight: Optional[int] = Field(None, ge=1)
    sort_order: Optional[int] = None


class RubricCriterionResponse(RubricCriterionBase):
    id: int
    rubric_id: int

    class Config:
        from_attributes = True


# ============ RUBRIC SCHEMAS ============


class RubricBase(BaseModel):
    title: str = Field(..., max_length=255, description="Title of the rubric")
    description: Optional[str] = Field(None, description="Description of the rubric's purpose and usage")
    source_url: Optional[str] = Field(None, max_length=500, description="Original source URL")
    source_attribution: Optional[str] = Field(None, description="Attribution text (author, license)")
    max_score: int = Field(default=4, ge=1, description="Maximum score per criterion")
    min_score: int = Field(default=1, ge=0, description="Minimum score per criterion")
    level_labels: Dict[str, str] = Field(
        default={"4": "Excellent", "3": "Good", "2": "Fair", "1": "Poor"},
        description="Labels for each score level"
    )
    category: Optional[str] = Field(None, max_length=100, description="Category for organization")
    tags: List[str] = Field(default_factory=list, description="Searchable tags")
    access_level: str = Field(default="patron", description="Required access level: patron, staff, admin")


class RubricCreate(StrictInputSchema, RubricBase):
    criteria: List[RubricCriterionCreate] = Field(
        default_factory=list,
        description="Initial criteria to create with the rubric"
    )
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None


class RubricUpdate(StrictInputSchema):
    title: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    source_url: Optional[str] = Field(None, max_length=500)
    source_attribution: Optional[str] = None
    max_score: Optional[int] = Field(None, ge=1)
    min_score: Optional[int] = Field(None, ge=0)
    level_labels: Optional[Dict[str, str]] = None
    category: Optional[str] = Field(None, max_length=100)
    tags: Optional[List[str]] = None
    access_level: Optional[str] = None
    is_published: Optional[bool] = None
    is_featured: Optional[bool] = None
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None


class RubricResponse(RubricBase):
    id: int
    is_published: bool
    is_featured: bool
    course_id: Optional[int] = None
    lesson_id: Optional[int] = None
    created_by_id: Optional[int] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RubricWithCriteria(RubricResponse):
    criteria: List[RubricCriterionResponse] = []


class RubricListItem(RubricResponse):
    criteria_count: int = 0


# ============ RUBRIC ASSESSMENT SCHEMAS ============


class RubricAssessmentBase(BaseModel):
    target_identifier: str = Field(..., max_length=255, description="What is being assessed (e.g., 'ChatGPT', 'self')")
    target_description: Optional[str] = Field(None, description="Description of what's being assessed")
    scores: Dict[str, int] = Field(default_factory=dict, description="Criterion ID to score mapping")
    notes: Dict[str, str] = Field(default_factory=dict, description="Criterion ID to notes mapping")
    overall_notes: Optional[str] = Field(None, description="Overall assessment notes")


class RubricAssessmentCreate(StrictInputSchema, RubricAssessmentBase):
    rubric_id: int


class RubricAssessmentUpdate(StrictInputSchema):
    target_identifier: Optional[str] = Field(None, max_length=255)
    target_description: Optional[str] = None
    scores: Optional[Dict[str, int]] = None
    notes: Optional[Dict[str, str]] = None
    overall_notes: Optional[str] = None
    is_complete: Optional[bool] = None


class RubricAssessmentResponse(RubricAssessmentBase):
    id: int
    rubric_id: int
    user_id: int
    total_score: Optional[int] = None
    max_possible_score: Optional[int] = None
    percentage: Optional[int] = None
    is_complete: bool
    completed_at: Optional[datetime] = None
    created_at: datetime | None = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class RubricAssessmentWithRubric(RubricAssessmentResponse):
    rubric: RubricWithCriteria


# ============ BULK OPERATIONS ============


class RubricBulkCriteriaCreate(StrictInputSchema):
    criteria: List[RubricCriterionCreate]


class RubricImport(BaseModel):
    rubric: RubricCreate
    criteria: List[RubricCriterionCreate]


# ============ ANALYTICS ============


class RubricUsageStats(BaseModel):
    rubric_id: int
    rubric_title: str
    total_assessments: int = 0
    completed_assessments: int = 0
    average_score: Optional[float] = None
    average_percentage: Optional[float] = None
