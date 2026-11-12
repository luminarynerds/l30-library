# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
from app.core.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from redis.exceptions import RedisError
from sqlalchemy import select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.cache import get_redis
from ..core.cache_strategies import CacheTTL
from ..models.organization_features import OrganizationFeatures
from ..models.operations_audit_log import PolicyChangeLog
from ..models.user import User

logger = get_logger(__name__)

# Redis key for the cached feature snapshot
_CACHE_KEY = "org_features:snapshot"
# TTL ensures stale data is never served for long, even if
# invalidation fails. 60 seconds is safe since toggles rarely change
# and invalidate_cache() is called on every update.
_CACHE_TTL_SECONDS = CacheTTL.SHORT  # 1 minute


class OrganizationFeaturesService:

    # ------------------------------------------------------------------
    # Cache helpers
    # ------------------------------------------------------------------

    @staticmethod
    async def _get_cached_snapshot() -> Optional[Dict[str, Any]]:
        try:
            redis = await get_redis()
            if redis is None:
                return None
            raw = await redis.get(_CACHE_KEY)
            if raw is None:
                return None
            return json.loads(raw)
        except (RedisError, json.JSONDecodeError):
            logger.warning("Redis cache miss for feature toggles", exc_info=True)
            return None

    @staticmethod
    async def _set_cached_snapshot(features: OrganizationFeatures) -> None:
        try:
            redis = await get_redis()
            if redis is None:
                return
            # Serialize all boolean columns + id
            data: Dict[str, Any] = {}
            for col in OrganizationFeatures.__table__.columns:
                val = getattr(features, col.name, None)
                if isinstance(val, (bool, int, float, str, list, dict)) or val is None:
                    data[col.name] = val
                elif isinstance(val, datetime):
                    data[col.name] = val.isoformat()
            await redis.set(_CACHE_KEY, json.dumps(data), ex=int(_CACHE_TTL_SECONDS))
        except (RedisError, TypeError):
            logger.warning("Failed to set Redis cache for feature toggles", exc_info=True)

    @staticmethod
    async def invalidate_cache() -> None:
        try:
            redis = await get_redis()
            if redis is None:
                return
            await redis.delete(_CACHE_KEY)
        except RedisError:
            logger.warning("Failed to invalidate feature toggle cache", exc_info=True)

    # ------------------------------------------------------------------
    # Defaults
    # ------------------------------------------------------------------

    @staticmethod
    def _create_default_features_instance() -> OrganizationFeatures:
        return OrganizationFeatures(
            id=0,
            gamification_enabled=True,
            reading_programs_enabled=True,
            board_features_enabled=True,
            training_modules_enabled=True,
            community_features_enabled=True,
            email_notifications_enabled=True,
            banned_books_tracking_enabled=True,
            patron_portal_enabled=True,
            self_checkout_enabled=True,
            acquisition_enabled=True,
            indie_platform_enabled=True,
            learning_platform_enabled=True,
            for_teachers_enabled=True,
            home_delivery_enabled=True,
            ai_tools_enabled=True,
            makerspace_enabled=True,
            meeting_rooms_enabled=True,
            events_enabled=True,
            ill_enabled=True,
            genealogy_enabled=True,
            free_ebooks_enabled=True,
            outreach_enabled=True,
            legal_services_enabled=True,
            strategic_planning_enabled=True,
            literacy_programs_enabled=True,
            tech_services_enabled=True,
            emergency_services_enabled=True,
            compliance_enabled=True,
            volunteers_enabled=True,
            notifications_enabled=True,
            family_card_enabled=True,
            marketing_enabled=True,
            streaming_enabled=True,
            staff_scheduling_enabled=True,
            beta_features_enabled=False,
            storytime_enabled=True,
            digital_access_enabled=True,
            collection_management_enabled=True,
            patron_engagement_enabled=True,
            staff_wellness_enabled=True,
            faq_chatbot_enabled=True,
            financial_reports_enabled=True,
            book_clubs_enabled=True,
            sip2_rfid_enabled=True,
            signage_enabled=True,
            printing_enabled=True,
            ama_enabled=False,
            saved_searches_enabled=True,
            reading_programs_booklist_enabled=False,
            reading_programs_paper_log_enabled=False,
            community_outcomes_enabled=True,
            front_desk_enabled=True,
            serials_enabled=True,
            migration_enabled=True,
            parent_onboarding_enabled=True,
            home_visit_safety_enabled=False,
            home_visit_day_plan_enabled=False,
            processing_queue_enabled=True,
            reading_goals_enabled=True,
            reading_shelf_enabled=True,
            shelf_data_export_enabled=True,
            circulation_print_slip_enabled=True,
            circulation_hold_trap_card_enabled=True,
            customer_display_enabled=False,
            pickup_authorization_enabled=False,
            cohort_enabled=False,
            aggregate_trending_enabled=True,
            enabled_focus_modes=["pomodoro", "zen", "timed"],
            enabled_themes=["light", "dark", "high-contrast"],
            enabled_fonts=["default", "dyslexia-friendly", "large"],
            default_daily_goal_minutes=30,
            max_holds_per_patron=10,
            max_checkouts_per_patron=5,
            configuration={},
            age_group_limits=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            updated_by_id=None,
        )

    # ------------------------------------------------------------------
    # Core CRUD
    # ------------------------------------------------------------------

    @staticmethod
    async def get_or_create_features(db: AsyncSession) -> OrganizationFeatures:
        try:
            result = await db.execute(select(OrganizationFeatures))
            features = result.scalar_one_or_none()

            if not features:
                logger.info("Creating default organization features in database")
                features = OrganizationFeaturesService._create_default_features_instance()
                db.add(features)
                await db.commit()
                await db.refresh(features)

            # Populate cache on every DB read so subsequent checks are fast
            await OrganizationFeaturesService._set_cached_snapshot(features)
            return features

        except ProgrammingError as e:
            if "organization_features" in str(e) or "relation" in str(e).lower():
                logger.warning(
                    "Organization features table does not exist. "
                    "Returning default feature settings."
                )
                await db.rollback()
                return OrganizationFeaturesService._create_default_features_instance()
            raise

    @staticmethod
    async def update_features(
        db: AsyncSession, update_data: Dict[str, Any], updated_by: User
    ) -> OrganizationFeatures:
        try:
            features = await OrganizationFeaturesService.get_or_create_features(db)

            # Snapshot before-state for the fields being changed
            before_state: Dict[str, Any] = {}
            fields_changed: list[str] = []
            reason = update_data.get("reason")

            for key, value in update_data.items():
                if key == "reason" or not hasattr(features, key):
                    continue
                old_val = getattr(features, key)
                if old_val != value:
                    before_state[key] = old_val
                    fields_changed.append(key)
                setattr(features, key, value)

            features.updated_at = datetime.now(timezone.utc)
            features.updated_by_id = updated_by.id

            # Write audit trail if anything actually changed
            if fields_changed:
                after_state = {k: update_data[k] for k in fields_changed}
                audit_entry = PolicyChangeLog(
                    policy_type="organization_features",
                    policy_name="Feature toggle" if len(fields_changed) == 1
                        else f"Feature toggles ({len(fields_changed)} fields)",
                    changed_by_staff_id=updated_by.id,
                    changed_by_identifier=f"email:{updated_by.email}",
                    before_value=before_state,
                    after_value=after_state,
                    fields_changed=fields_changed,
                    reason=reason,
                )
                db.add(audit_entry)

            await db.commit()
            await db.refresh(features)

            # Invalidate then re-populate so all instances pick up the change
            await OrganizationFeaturesService.invalidate_cache()
            await OrganizationFeaturesService._set_cached_snapshot(features)

            logger.info(
                "Organization features updated by %s (changed: %s). Reason: %s",
                updated_by.email,
                ", ".join(fields_changed) if fields_changed else "none",
                reason or "Not provided",
            )

            return features

        except ProgrammingError as e:
            if "organization_features" in str(e) or "relation" in str(e).lower():
                logger.error(
                    "Cannot update organization features: table does not exist. "
                    "Run database migrations before attempting updates."
                )
            raise

    @staticmethod
    async def is_feature_enabled(db: AsyncSession, feature_name: str) -> bool:
        # Fast path: check Redis cache
        snapshot = await OrganizationFeaturesService._get_cached_snapshot()
        if snapshot is not None:
            val = snapshot.get(feature_name)
            if val is not None:
                return bool(val)

        # Slow path: DB query (also repopulates cache)
        try:
            features = await OrganizationFeaturesService.get_or_create_features(db)
            return getattr(features, feature_name, True)
        except ProgrammingError as e:
            if "organization_features" in str(e) or "relation" in str(e).lower():
                logger.debug(
                    "Organization features table missing; returning default for %s",
                    feature_name,
                )
                default_features = OrganizationFeaturesService._create_default_features_instance()
                return getattr(default_features, feature_name, True)
            raise
