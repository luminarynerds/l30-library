"""
Regression: board committees, document delete, and full export must accept DIRECTOR.

Pre-fix the `[ADMIN, SUPER_ADMIN]` role-list excluded DIRECTOR even though the
library director is the routine staff liaison for board committee work and
document/export operations. This test pins the inclusive behavior post-fix.

Companion to backend/tests/test_role_authz_regression.py.
"""
from __future__ import annotations

import pytest

from app.api.v1.dependencies import is_admin
from app.models.user import UserRole


class _U:
    def __init__(self, role: UserRole):
        self.role = role


@pytest.mark.parametrize(
    "role,expected",
    [
        (UserRole.SUPER_ADMIN, True),
        (UserRole.ADMIN, True),
        (UserRole.DIRECTOR, True),
        (UserRole.STAFF, False),
        (UserRole.LEGAL, False),
        (UserRole.PATRON, False),
        (UserRole.TEACHER, False),
    ],
)
def test_is_admin_helper_role_matrix(role: UserRole, expected: bool):
    """is_admin() — the helper used by the fixed board sites — must accept
    SUPER_ADMIN + ADMIN + DIRECTOR, reject everyone else.

    Board endpoints fixed in this PR:
      - committees.py: create/update/dissolve + add/update/remove member (6 sites)
      - documents.py: delete_document
      - export.py: full_board_export
    All call is_admin(current_user); if this helper's role set ever shrinks,
    those endpoints regress to the old `[ADMIN, SUPER_ADMIN]` deny-DIRECTOR
    behavior. This test prevents that.
    """
    assert is_admin(_U(role)) is expected
