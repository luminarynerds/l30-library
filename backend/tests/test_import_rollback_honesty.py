# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Regression tests: import rollback honesty (H4).

ImportService.rollback() marks UPDATED records as ROLLED_BACK without
restoring their data. The API response must distinguish:
  - records_actually_deleted: CREATED records that were physically deleted
  - records_marked_only: UPDATED records only marked (data unchanged)

And surface a warning when records_marked_only > 0.
"""
import pytest

from app.schemas.import_schemas import RollbackResponse


def test_rollback_response_has_separate_count_fields():
    """
    RollbackResponse must expose separate counts so callers know which
    records were actually undone vs only marked as rolled-back.
    """
    fields = RollbackResponse.model_fields
    assert "records_actually_deleted" in fields, (
        "records_actually_deleted missing — rollback falsely conflates deleted "
        "CREATED records with data-unchanged UPDATED records"
    )
    assert "records_marked_only" in fields, (
        "records_marked_only missing — callers cannot tell how many UPDATED "
        "records were only status-flagged rather than truly reverted"
    )
    assert "warning" in fields, (
        "warning missing — no way to surface the 'update rollback is partial' message"
    )


def test_rollback_response_warning_is_optional():
    """warning field must be Optional so clean rollbacks (no updates) don't include it."""
    from typing import get_args, get_origin, Union
    import types

    field = RollbackResponse.model_fields["warning"]
    # Optional[str] means the field can be None
    annotation = field.annotation
    # Accept Optional[str] (Union[str, None]) or just str with default None
    is_optional = (
        get_origin(annotation) is Union and type(None) in get_args(annotation)
    ) or annotation is type(None)
    has_none_default = field.default is None

    assert is_optional or has_none_default, (
        "warning field must be Optional[str] with default None"
    )


def test_rollback_response_backward_compatible():
    """records_rolled_back must still exist for backward compat."""
    assert "records_rolled_back" in RollbackResponse.model_fields
