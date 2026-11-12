# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Generate test auth tokens for smoke testing."""
import sys
sys.path.insert(0, "/opt/l30/backend")

from app.core.security import create_access_token


def get_staff_token(user_id: int = 1, email: str = "smoke-test@lsc.local") -> str:
    """Create a staff-level JWT for smoke testing."""
    return create_access_token(
        subject=str(user_id),
        email=email,
        role="admin",
    )


def get_auth_headers(user_id: int = 1) -> dict[str, str]:
    """Return Authorization header dict ready for httpx."""
    token = get_staff_token(user_id)
    return {"Authorization": f"Bearer {token}"}


if __name__ == "__main__":
    token = get_staff_token()
    print(f"Token: {token[:50]}...")
    print("Headers:", get_auth_headers())
