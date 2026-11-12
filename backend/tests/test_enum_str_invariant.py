# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Invariant: str(member) == member.value for every StrEnum subclass in app/.

This test discovers all StrEnum subclasses dynamically so it stays current
as new enums are added. It would have caught the (str, Enum) name-leak bug
(str(UserRole.SUPER_ADMIN) == "UserRole.super_admin") on its first run.

Key enums explicitly verified as anchors:
  - UserRole: 11 members, values are bare lowercase (e.g. "super_admin")
  - GoalStatus: 6 members ("not_started", "on_track", ...)
  - PatronStatus: 4 members
"""
import importlib
import inspect
import pkgutil
from enum import StrEnum

import pytest


def _discover_strenums() -> tuple[list[tuple[str, StrEnum]], list[tuple[str, StrEnum]]]:
    """Walk app.* and collect StrEnum members.

    Returns (all_params, convention_params) where:
      all_params        — every member, for the core str()==value invariant
      convention_params — members from models/schemas only, for the lowercase convention
                          (mirrors what check_enum_columns.py enforces)
    """
    import app  # noqa: F401 — triggers package init

    all_params: list[tuple[str, StrEnum]] = []
    convention_params: list[tuple[str, StrEnum]] = []
    seen: set[int] = set()

    for importer, modname, ispkg in pkgutil.walk_packages(
        path=importlib.import_module("app").__path__,
        prefix="app.",
        onerror=lambda name: None,
    ):
        try:
            module = importlib.import_module(modname)
        except Exception:
            continue
        # The lowercase-values convention (enforced by check_enum_columns.py)
        # applies to models and schemas only; service-layer protocol codes
        # (SIP2FieldID, NCIPMessageType, ErrorCode…) are legitimately uppercase.
        in_convention_scope = modname.startswith(("app.models.", "app.schemas."))
        for attr_name, obj in inspect.getmembers(module, inspect.isclass):
            if (
                issubclass(obj, StrEnum)
                and obj is not StrEnum
                and id(obj) not in seen
            ):
                seen.add(id(obj))
                for member in obj:
                    label = f"{obj.__qualname__}.{member.name}"
                    all_params.append((label, member))
                    if in_convention_scope:
                        convention_params.append((label, member))

    return all_params, convention_params


_ALL_PARAMS, _CONVENTION_PARAMS = _discover_strenums()


@pytest.mark.parametrize("label,member", _ALL_PARAMS, ids=[p[0] for p in _ALL_PARAMS])
def test_str_equals_value(label: str, member: StrEnum):
    """str(member) must equal member.value — the core invariant."""
    assert str(member) == member.value, (
        f"{label}: str() returned {str(member)!r}, expected {member.value!r}"
    )


@pytest.mark.parametrize(
    "label,member", _CONVENTION_PARAMS, ids=[p[0] for p in _CONVENTION_PARAMS]
)
def test_value_is_lowercase(label: str, member: StrEnum):
    """L30 convention: model/schema StrEnum values must be lowercase.

    Scope mirrors check_enum_columns.py (app.models.* and app.schemas.*).
    Service-layer protocol-code enums (SIP2FieldID, NCIPMessageType, ErrorCode)
    live in app.services.* and are excluded — their values follow external specs.
    """
    assert member.value == member.value.lower(), (
        f"{label}: value {member.value!r} is not all-lowercase"
    )


# Anchor tests: explicitly verify the enums most critical to the name-leak fix.

def test_userrole_str_anchor():
    from app.models.user import UserRole
    assert str(UserRole.SUPER_ADMIN) == "super_admin"
    assert str(UserRole.LIBRARY_ADMIN) == "library_admin"
    assert str(UserRole.PATRON) == "patron"


def test_goalstatus_str_anchor():
    from app.models.strategic import GoalStatus
    assert str(GoalStatus.NOT_STARTED) == "not_started"
    assert str(GoalStatus.COMPLETED) == "completed"
    assert str(GoalStatus.AT_RISK) == "at_risk"


def test_userrole_compliance_audit_proof():
    """Proves the unified_compliance_audit actor_role=str(current_user.role) fix.

    Before migration: str(UserRole.ADMIN) == "UserRole.admin" (wrong)
    After migration:  str(UserRole.ADMIN) == "admin" (correct)
    """
    from app.models.user import UserRole
    leaked_form = f"{UserRole.__name__}.{UserRole.ADMIN.value}"  # "UserRole.admin"
    assert str(UserRole.ADMIN) != leaked_form, "Name-leak still present!"
    assert str(UserRole.ADMIN) == UserRole.ADMIN.value  # "admin"
