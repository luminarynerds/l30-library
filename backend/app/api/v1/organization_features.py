# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""API endpoints for organization-wide feature management."""

import copy
from app.core.logging import get_logger
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import get_settings
from ...core.database import get_db
from ...core.email_config import resolve_marketing_email_key
from ...models.user import User, UserRole
from ...schemas.organization_features import (OrganizationFeaturesResponse,
                                              OrganizationFeaturesUpdate)
from ...models.organization_features import OrganizationFeatures
from ...services.organization_features_service import \
    OrganizationFeaturesService
from .auth import get_current_user
from .feature_guards import FEATURE_REGISTRY

# All boolean field names on the OrganizationFeatures model
_BOOLEAN_FIELDS = [
    col.name
    for col in OrganizationFeatures.__table__.columns
    if isinstance(col.type, type(OrganizationFeatures.gamification_enabled.type))
    or str(col.type) == "BOOLEAN"
]

PRESETS: dict[str, dict[str, bool]] = {
    "barebones": {
        field: field in {
            "email_notifications_enabled",
            "front_desk_enabled",
            "notifications_enabled",
            "circulation_print_slip_enabled",
            "circulation_hold_trap_card_enabled",
        }
        for field in _BOOLEAN_FIELDS
    },
    "full": {
        field: True
        for field in _BOOLEAN_FIELDS
    },
    "small_library": {
        field: field in {
            "front_desk_enabled",
            "collection_management_enabled",
            "community_features_enabled",
            "events_enabled",
            "email_notifications_enabled",
            "notifications_enabled",
            "processing_queue_enabled",
            "circulation_print_slip_enabled",
            "circulation_hold_trap_card_enabled",
        }
        for field in _BOOLEAN_FIELDS
    },
}

logger = get_logger(__name__)
router = APIRouter(prefix="/organization-features", tags=["organization-features"])


def _ensure_admin(current_user: User) -> None:
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPER_ADMIN, UserRole.DIRECTOR]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to modify organization features",
        )


def _serialize_features(features: OrganizationFeatures) -> OrganizationFeaturesResponse:
    response = OrganizationFeaturesResponse.model_validate(features)
    config = response.configuration
    if not isinstance(config, dict):
        config = {}

    email_marketing = config.get("email_marketing")
    db_em = email_marketing if isinstance(email_marketing, dict) else None

    redacted_config = copy.deepcopy(config)
    existing_em = redacted_config.get("email_marketing")
    redacted_em: dict[str, Any] = existing_em if isinstance(existing_em, dict) else {}
    _, source = resolve_marketing_email_key(db_em)
    redacted_em.pop("sendgrid_api_key", None)
    redacted_em["sendgrid_api_key_present"] = source != "none"
    redacted_em["sendgrid_api_key_source"] = source
    redacted_config["email_marketing"] = redacted_em

    response.configuration = redacted_config
    return response


@router.get("", response_model=OrganizationFeaturesResponse)
async def get_organization_features(
    db: AsyncSession = Depends(get_db),
) -> OrganizationFeaturesResponse:
    """
    Get organization-wide feature settings.

    Public endpoint - no authentication required.
    Frontend needs this data before login to render available features correctly.
    Contains only non-sensitive feature flags and configuration.
    """
    features = await OrganizationFeaturesService.get_or_create_features(db)
    return _serialize_features(features)


@router.put("", response_model=OrganizationFeaturesResponse)
async def update_organization_features(
    payload: OrganizationFeaturesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationFeaturesResponse:
    """
    Update organization-wide feature settings.

    Admin-only endpoint. Performs partial update - only provided fields are changed.
    Requires the organization_features table to exist in the database.
    """
    _ensure_admin(current_user)

    try:
        update_data = payload.dict(exclude_unset=True)

        # Reject attempts to set the marketing email-provider key in the
        # DB when the server already has one from env -- env is the source of
        # truth and we don't want admins thinking they're rotating a key that
        # actually comes from elsewhere.
        # NOTE: the DB field name is "sendgrid_api_key" for historical
        # reasons (Resend replaced SendGrid); renaming requires a coordinated
        # frontend + DB migration.
        config_update = update_data.get("configuration")
        if isinstance(config_update, dict):
            email_marketing = config_update.get("email_marketing")
            if isinstance(email_marketing, dict):
                incoming_key = (email_marketing.get("sendgrid_api_key") or "").strip()
                if incoming_key:
                    settings = get_settings()
                    env_key = (settings.resend_api_key or "").strip()
                    if env_key:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=(
                                "Email provider is already configured via an "
                                "environment variable. Contact your system administrator to change it."
                            ),
                        )

        features = await OrganizationFeaturesService.update_features(
            db=db, update_data=update_data, updated_by=current_user
        )
        return _serialize_features(features)

    except ProgrammingError as e:
        # Table doesn't exist - cannot perform updates without it
        if "organization_features" in str(e) or "relation" in str(e).lower():
            logger.error(
                f"Update failed: organization_features table does not exist. "
                f"Admin {current_user.email} attempted to update features."
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Organization features table not initialized. "
                "Please run database migrations before attempting updates.",
            ) from e
        else:
            raise


@router.patch("", response_model=OrganizationFeaturesResponse)
async def patch_organization_features(
    payload: OrganizationFeaturesUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationFeaturesResponse:
    """
    Partially update organization-wide feature settings.

    Admin-only endpoint. Same behavior as PUT - only provided fields are changed.
    """
    return await update_organization_features(payload, db, current_user)


@router.post("/presets/{preset_name}", response_model=OrganizationFeaturesResponse)
async def apply_feature_preset(
    preset_name: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> OrganizationFeaturesResponse:
    """
    Apply a feature preset (bulk toggle).

    Admin-only endpoint. Accepted preset names: "barebones", "full", "small_library".
    """
    _ensure_admin(current_user)

    if preset_name not in PRESETS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown preset '{preset_name}'. Valid presets: {', '.join(PRESETS)}",
        )

    update_data = PRESETS[preset_name]
    features = await OrganizationFeaturesService.update_features(
        db=db, update_data=update_data, updated_by=current_user
    )
    return _serialize_features(features)


@router.get("/check/{feature_name}")
async def check_feature_enabled(
    feature_name: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Check if a specific feature is enabled.

    Public endpoint (no auth required) for quick feature checks.
    """
    is_enabled = await OrganizationFeaturesService.is_feature_enabled(db, feature_name)
    return {"feature_name": feature_name, "enabled": is_enabled}


@router.get("/registry")
async def get_feature_registry() -> list[dict[str, str]]:
    """Return the catalog of toggleable features (key + human label).

    Drives the admin UI so every declared `_make_feature_guard` shows up as a
    toggle without hardcoding. Public — no sensitive data.
    """
    return FEATURE_REGISTRY
