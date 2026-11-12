# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Regression guard: the speculative ``survey`` lesson type is gone.

If a future change re-adds it, this test fails before it lands. Drops
the value across both the SQLAlchemy and Pydantic mirror enums.
"""
from app.models.learning import LessonType as ModelLessonType
from app.schemas.learning import LessonType as SchemaLessonType


def test_model_lesson_type_has_no_survey() -> None:
    values = [t.value for t in ModelLessonType]
    assert "survey" not in values
    assert set(values) == {"article", "video", "quiz", "sandbox", "lab"}


def test_schema_lesson_type_has_no_survey() -> None:
    values = [t.value for t in SchemaLessonType]
    assert "survey" not in values
    assert set(values) == {"article", "video", "quiz", "sandbox", "lab"}
