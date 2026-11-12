# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas._base import StrictInputSchema

# ===== PathCourse Schemas =====


class PathCourseBase(BaseModel):

    course_id: int
    sort_order: int = 0
    is_required: bool = True
    prerequisite_course_ids: List[int] = Field(default_factory=list)
    description: Optional[str] = None


class PathCourseCreate(StrictInputSchema, PathCourseBase):

    pass


class PathCourseUpdate(StrictInputSchema):

    sort_order: Optional[int] = None
    is_required: Optional[bool] = None
    prerequisite_course_ids: Optional[List[int]] = None
    description: Optional[str] = None


class PathCourseResponse(PathCourseBase):

    id: int
    learning_path_id: int
    created_at: datetime | None = None
    class Config:
        from_attributes = True


class PathCourseWithDetails(PathCourseResponse):

    course_title: Optional[str] = None
    course_thumbnail: Optional[str] = None
    course_estimated_minutes: Optional[int] = None
    course_difficulty: Optional[str] = None
    is_completed: bool = False
    can_access: bool = True


# ===== LearningPath Schemas =====


class LearningPathBase(BaseModel):

    title: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str = "draft"
    is_public: bool = False
    estimated_hours: Optional[int] = Field(None, ge=0)
    difficulty: Optional[str] = "beginner"
    tags: List[str] = Field(default_factory=list)
    enforce_prerequisites: bool = True


class LearningPathCreate(StrictInputSchema, LearningPathBase):

    courses: List[PathCourseCreate] = Field(default_factory=list)


class LearningPathUpdate(StrictInputSchema):

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None
    estimated_hours: Optional[int] = Field(None, ge=0)
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None
    enforce_prerequisites: Optional[bool] = None


class LearningPathResponse(LearningPathBase):

    id: int
    created_at: datetime | None = None
    updated_at: Optional[datetime]
    created_by_id: Optional[int]
    total_courses: int = 0

    class Config:
        from_attributes = True


class LearningPathDetail(LearningPathResponse):

    courses: List[PathCourseWithDetails] = Field(default_factory=list)
    total_courses: int = 0
    required_courses: int = 0
    optional_courses: int = 0
    # Sum of constituent course durations, computed in the detail handler.
    # Source of truth for the path's "X hours" stat (the freehand
    # estimated_hours field is decoupled from actual course content).
    total_minutes: int = 0
    is_enrolled: bool = False
    enrollment_progress: int = 0


# ===== PathEnrollment Schemas =====


class PathEnrollmentBase(BaseModel):

    learning_path_id: int


class PathEnrollmentCreate(StrictInputSchema, PathEnrollmentBase):

    pass


class PathEnrollmentResponse(PathEnrollmentBase):

    id: int
    user_id: int
    status: str
    progress_percentage: int
    completed_course_ids: List[int]
    enrolled_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    last_accessed_at: Optional[datetime]

    class Config:
        from_attributes = True


class PathEnrollmentDetail(PathEnrollmentResponse):

    path_title: str
    path_thumbnail: Optional[str] = None
    path_description: Optional[str] = None
    total_courses: int = 0
    completed_courses: int = 0
    next_course_id: Optional[int] = None


# ===== Bulk Operations =====


class BulkAddCoursesRequest(StrictInputSchema):

    courses: List[PathCourseCreate]


class PathProgressUpdate(StrictInputSchema):

    course_id: int
    completed: bool = True
