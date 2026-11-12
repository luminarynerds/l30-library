# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public branding endpoint -- returns library identity for the frontend."""

from fastapi import APIRouter, Depends, HTTPException
from ...models.user import User
from .dependencies import require_admin, require_super_admin
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ...core.branding import branding
from ...core.cache_strategies import CacheTTL
from ...core.database import get_db
from ...core.http_cache import cache_for
from ...models.library_branding import LibraryBranding

router = APIRouter()


@router.get(
    "/branding",
    tags=["branding"],
    summary="Library branding config",
    dependencies=[Depends(cache_for(CacheTTL.SHORT))],
)
async def get_branding_config(db: AsyncSession = Depends(get_db)):
    """
    Public endpoint returning library branding, contact info, and colors.

    No authentication required -- this is public information the frontend
    needs to render the site correctly.
    """
    result = await db.execute(select(LibraryBranding).where(LibraryBranding.id == 1))
    db_row = result.scalar_one_or_none()

    response = {
        "library_name": branding.library_name,
        "library_short_name": branding.library_short_name,
        "domain": branding.domain,
        "contact_email": branding.contact_email,
        "privacy_email": branding.privacy_email,
        "indie_email": branding.indie_email,
        "giving_email": branding.giving_email,
        "events_email": branding.events_email,
        "print_email": branding.print_email,
        "makerspace_email": branding.makerspace_email,
        "phone": branding.phone,
        "address_line1": branding.address_line1,
        "address_line2": branding.address_line2,
        "city": branding.city,
        "state": branding.state,
        "zip_code": branding.zip_code,
        "primary_color": branding.primary_color,
        "accent_color": branding.accent_color,
        "is_demo": branding.is_demo,
        "bluesky_url": branding.bluesky_url,
        "mastodon_url": branding.mastodon_url,
        "seasonal_callout_active": branding.seasonal_callout_active,
        "card_prefix": branding.CARD_PREFIX,
        "product_name": branding.PRODUCT_NAME,
        "product_tagline": branding.PRODUCT_TAGLINE,
        "hero_title": "",
        "hero_subtitle": "You belong here.",
        "tagline": "",
        "logo_url": "",
        "hero_image_url": "",
        "display_font": "",
        "body_font": "",
        "secondary_color": "",
        "surface_color": "",
        "ink_color": "",
        "nav_style": "default",
        "donate_config": branding.donate_config,
        "about_story": None,
        # ND access fields -- None by default, overridden from DB row below
        "quiet_hours": None,
        "sensory_friendly_times": None,
        "low_stim_seating": None,
    }

    # DB values override file/env defaults
    if db_row:
        for key in response:
            db_val = getattr(db_row, key, None)
            if db_val:
                response[key] = db_val

    # city/state/zip (and phone, when unset above) aren't LibraryBranding
    # columns -- the library's own system record (setup wizard / seeder) is
    # the source of truth over the stock file/env defaults.
    from ...models.multi_branch import LibrarySystem

    sys_row = (await db.execute(select(LibrarySystem).limit(1))).scalar_one_or_none()
    if sys_row:
        for key in ("city", "state", "zip_code"):
            val = getattr(sys_row, key, None)
            if val:
                response[key] = val
        if not (db_row and db_row.phone) and sys_row.phone:
            response["phone"] = sys_row.phone

    return response


@router.put("/branding", tags=["branding"])
async def update_branding(
    data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Save branding configuration. Admin-only (setup wizard creates first admin before branding)."""

    result = await db.execute(select(LibraryBranding).where(LibraryBranding.id == 1))
    row = result.scalar_one_or_none()
    if not row:
        row = LibraryBranding(id=1)
        db.add(row)
    for key, value in data.items():
        if hasattr(row, key) and key not in ("id", "updated_at"):
            setattr(row, key, value)
    await db.commit()
    return {"status": "ok"}


@router.get("/branding/setup-status", tags=["branding"])
async def get_setup_status(db: AsyncSession = Depends(get_db)):
    from ...models.multi_branch import SystemSettings
    from ...models.user import User, UserRole

    result = await db.execute(select(SystemSettings.setup_complete).order_by(SystemSettings.id.desc()).limit(1))
    setup_complete = result.scalar_one_or_none() or False

    result = await db.execute(
        select(func.count(User.id)).where(
            User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR])
        )
    )
    admin_count = result.scalar_one()

    return {"setup_complete": bool(setup_complete), "has_admin": admin_count > 0}


class FirstAdminCreate(BaseModel):
    name: str
    email: str
    password: str


@router.post("/branding/create-first-admin", tags=["branding"])  # noqa: role-check -- first-run admin bootstrap, self-gated (refuses if any admin exists)
async def create_first_admin(data: FirstAdminCreate, db: AsyncSession = Depends(get_db)):
    from ...models.user import User, UserRole
    from ...core.security import hash_password

    # Safety: refuse if any admin exists
    result = await db.execute(
        select(func.count(User.id)).where(
            User.role.in_([UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR])
        )
    )
    if result.scalar_one() > 0:
        raise HTTPException(status_code=400, detail="Admin account already exists")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=UserRole.DIRECTOR,
        is_active=True,
        email_verified=True,
    )
    db.add(user)
    await db.commit()
    return {"status": "ok", "user_id": user.id}


@router.post("/branding/complete-setup", tags=["branding"])
async def complete_setup(
    db: AsyncSession = Depends(get_db),
    _current_user=Depends(require_super_admin),
):
    from ...models.multi_branch import SystemSettings

    result = await db.execute(select(SystemSettings).order_by(SystemSettings.id.desc()).limit(1))
    settings = result.scalar_one_or_none()
    if settings:
        settings.setup_complete = True
        await db.commit()
    return {"status": "ok"}
