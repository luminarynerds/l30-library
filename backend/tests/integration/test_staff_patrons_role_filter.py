"""
Integration test for the STAFF-role 500 on `/staff/patrons`.

Before the fix, the PII filter strips `email` from each patron in the response,
but `UserResponse.email` was a required `TestableEmail`. FastAPI response-model
validation then 500'd. This test pins the fix in place.
"""

import pytest


@pytest.mark.integration
async def test_staff_list_patrons_returns_200_with_masked_email(
    client, test_staff, test_patron
):
    """STAFF role can list patrons; response carries `email_masked` instead of `email`."""
    from app.api.v1.auth.helpers import get_current_user
    from app.main import app

    app.dependency_overrides[get_current_user] = lambda: test_staff
    try:
        resp = await client.get("/api/v1/staff/patrons")
    finally:
        app.dependency_overrides.pop(get_current_user, None)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "patrons" in body
    p = next((x for x in body["patrons"] if x["id"] == test_patron.id), None)
    assert p is not None, "seeded patron not in STAFF-filtered list"

    # PII filter contract: STAFF gets the masked email, not the raw one.
    assert p.get("email") in (None, ""), (
        f"STAFF should not see raw email; got {p.get('email')!r}"
    )
    assert p.get("email_masked"), (
        "STAFF response missing email_masked sibling field"
    )
