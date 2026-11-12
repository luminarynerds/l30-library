# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Admin Integrations Status router.

Read-only view of which external integrations are wired up plus a Test button
per integration. Recipients of test emails are hard-coded server-side to the
calling admin's address -- the request body is never trusted for routing.
"""

from fastapi import APIRouter, Depends

from .auth import get_current_user
from .dependencies import require_admin
from ...services import integration_probes

router = APIRouter(prefix="/admin/integrations", tags=["admin-integrations"])


@router.get("", dependencies=[Depends(require_admin)])
async def list_integrations():
    """Return every integration's configured-state + last-probe state."""
    rows = await integration_probes.snapshot_all()
    return {"integrations": [r.__dict__ for r in rows]}


@router.post("/{integration_id}/probe")
async def run_probe(
    integration_id: str,
    current_user=Depends(require_admin),
):
    """Run a live probe for one integration. Updates the in-memory cache."""
    result = await integration_probes.run(
        integration_id, admin_user_id=getattr(current_user, "id", None)
    )
    return result.__dict__


@router.post("/email/send-test")
async def send_test_email(current_user=Depends(require_admin)):
    """Send a test email to the currently-authenticated admin.

    Recipient is hard-coded server-side to ``current_user.email``. Any TO
    field in the request body is intentionally ignored to prevent the
    endpoint from becoming a phishing/abuse vector.
    """
    admin_email = getattr(current_user, "email", "") or ""
    ok, detail = await integration_probes.send_test_email(current_user, admin_email)
    return {"ok": ok, "detail": detail, "sent_to": admin_email}
