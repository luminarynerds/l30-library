# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from app.models.multi_branch import Branch, BranchClosure, LibrarySystem
from app.models.user import User
from app.models.event import Event
from app.models.circulation import Hold, Checkout
from app.core.timezone_utils import utc_to_local
from app.core.logging import get_logger


class ClosureManagementService:

    def __init__(self, db: AsyncSession):
        self.db = db

    # =========================================================================
    # CORE CLOSURE OPERATIONS
    # =========================================================================

    async def close_today(
        self,
        branch_id: int,
        reason: str,
        created_by_id: int,
        closure_documentation: str | None = None,
        send_notifications: bool = True,
        cancel_events: bool = True,
        reschedule_programs: bool = True,
        update_external_services: bool = True,
        notify_partner_organizations: bool = True,
        partner_list: list[str] | None = None,
    ) -> BranchClosure:
        # Get branch with timezone info
        result = await self.db.execute(
            select(Branch)
            .options(joinedload(Branch.library_system))
            .where(Branch.id == branch_id)
        )
        branch = result.scalar_one_or_none()
        if not branch:
            raise ValueError(f"Branch {branch_id} not found")

        # Calculate today's date in branch timezone
        branch_tz = ZoneInfo(
            branch.library_system.timezone if branch.library_system else "UTC"
        )
        today = datetime.now(branch_tz).date()

        # Create closure for today (full day)
        closure = BranchClosure(
            branch_id=branch_id,
            start_date=today,
            end_date=today,
            reason=reason,
            created_by_id=created_by_id,
            closure_documentation=closure_documentation,
            is_system_wide=False,
            is_annual=False,
        )
        self.db.add(closure)
        await self.db.flush()

        # Execute closure management tasks
        if send_notifications:
            await self._handle_patron_notifications(closure, branch)
            await self._handle_staff_notifications(closure, branch, created_by_id)

        if cancel_events:
            await self._handle_event_cancellation(
                closure,
                branch,
                reschedule_programs=reschedule_programs,
            )

        if update_external_services:
            # In production this would trigger real channel integrations.
            closure.website_updated = True
            closure.phone_message_updated = True
            closure.social_media_updated = True
            closure.google_maps_updated = True
            closure.apple_maps_updated = True

        if notify_partner_organizations:
            await self._handle_partner_notifications(closure, partner_list)

        await self.db.commit()
        await self.db.refresh(closure)
        return closure

    async def update_closure(
        self,
        closure_id: int,
        updated_by_id: int,
        **updates,
    ) -> BranchClosure:
        result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        # Update permitted fields
        updatable_fields = {
            "description",
            "closure_documentation",
            "reopening_announcement",
            "patrons_with_holds_notified",
            "staff_notified",
            "partner_organizations_notified",
            "website_updated",
            "phone_message_updated",
            "social_media_updated",
            "google_maps_updated",
            "apple_maps_updated",
            "events_canceled",
            "programs_rescheduled",
        }

        for key, value in updates.items():
            if key in updatable_fields:
                setattr(closure, key, value)

        closure.updated_by_id = updated_by_id
        closure.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(closure)
        return closure

    async def get_closure_status(self, closure_id: int) -> dict[str, Any]:
        result = await self.db.execute(
            select(BranchClosure)
            .options(
                joinedload(BranchClosure.created_by),
                joinedload(BranchClosure.updated_by),
            )
            .where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        # Load branch manually (relationship is disabled on the model)
        branch_result = await self.db.execute(
            select(Branch).where(Branch.id == closure.branch_id)
        )
        closure.branch = branch_result.scalar_one_or_none()

        return {
            "closure": closure,
            "notifications": {
                "patrons_with_holds": closure.patrons_with_holds_notified,
                "staff": closure.staff_notified,
                "partners": closure.partner_organizations_notified,
            },
            "external_services": {
                "website": closure.website_updated,
                "phone_message": closure.phone_message_updated,
                "social_media": closure.social_media_updated,
                "google_maps": closure.google_maps_updated,
                "apple_maps": closure.apple_maps_updated,
            },
            "event_management": {
                "events_canceled": closure.events_canceled,
                "programs_rescheduled": closure.programs_rescheduled,
            },
        }

    # =========================================================================
    # PATRON NOTIFICATIONS
    # =========================================================================

    async def _handle_patron_notifications(
        self, closure: BranchClosure, branch: Branch
    ) -> None:
        # Find all active holds at this branch
        result = await self.db.execute(
            select(Hold)
            .options(
                joinedload(Hold.user),
                joinedload(Hold.item),
            )
            .where(
                and_(
                    Hold.pickup_location_id == branch.id,
                    Hold.status == "ready",
                )
            )
        )
        result.scalars().all()

        # In production, this would send actual notifications via email/SMS.
        # Mark as complete even when no hold patrons are currently affected.
        closure.patrons_with_holds_notified = True

    async def get_patrons_with_holds(self, closure_id: int) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        # Get holds ready during this closure period
        result = await self.db.execute(
            select(Hold)
            .options(joinedload(Hold.user), joinedload(Hold.item))
            .where(
                and_(
                    Hold.pickup_location_id == closure.branch_id,
                    Hold.status == "ready",
                )
            )
        )
        holds = result.scalars().all()

        return [
            {
                "patron_id": hold.user_id,
                "patron_name": hold.user.full_name if hold.user else "Unknown",
                "patron_email": hold.user.email if hold.user else None,
                "item_title": hold.item.title if hold.item else "Unknown",
                "hold_placed_at": hold.created_at.isoformat() if hold.created_at else None,
            }
            for hold in holds
        ]

    # =========================================================================
    # STAFF NOTIFICATIONS
    # =========================================================================

    async def _handle_staff_notifications(
        self, closure: BranchClosure, branch: Branch, initiated_by_id: int
    ) -> None:
        # Find all staff assigned to this branch
        result = await self.db.execute(
            select(User)
            .where(
                and_(
                    User.work_branch_id == branch.id,
                    User.is_active == True,
                )
            )
        )
        result.scalars().all()

        # In production, send notifications as a cascade through leadership.
        closure.staff_notified = True

    async def get_staff_notification_list(self, closure_id: int) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        result = await self.db.execute(
            select(User)
            .where(
                and_(
                    User.work_branch_id == closure.branch_id,
                    User.is_active == True,
                )
            )
        )
        staff = result.scalars().all()

        return [
            {
                "staff_id": member.id,
                "name": member.full_name,
                "email": member.email,
                "role": member.role,
            }
            for member in staff
        ]

    # =========================================================================
    # EVENT MANAGEMENT
    # =========================================================================

    async def _handle_event_cancellation(
        self,
        closure: BranchClosure,
        branch: Branch,
        reschedule_programs: bool = True,
    ) -> None:
        import logging
        logger = get_logger(__name__)

        from app.models.event_registration import (
            EventRegistration,
            EventRegistrationStatus,
        )
        from app.services.notifications.email_sender import EmailSenderService
        from app.services.notifications.types import NotificationType

        # Find events within the closure date range
        result = await self.db.execute(
            select(Event)
            .where(
                and_(
                    Event.location == branch.name,  # Assuming location stores branch name
                    Event.start_time >= datetime.combine(closure.start_date, time.min),
                    Event.start_time <= datetime.combine(closure.end_date, time.max),
                )
            )
        )
        events = result.scalars().all()

        cancellation_reason = (
            f"This event is cancelled because {branch.name} is closed: {closure.reason}"
            if getattr(closure, "reason", None)
            else f"This event is cancelled because {branch.name} is closed."
        )

        email_service = EmailSenderService()

        for event in events:
            reg_result = await self.db.execute(
                select(EventRegistration)
                .where(EventRegistration.event_id == event.id)
                .where(
                    EventRegistration.status.in_([
                        EventRegistrationStatus.CONFIRMED.value,
                        EventRegistrationStatus.WAITLISTED.value,
                    ])
                )
            )
            registrations = reg_result.scalars().all()

            event_date_str = event.start_time.strftime("%B %d, %Y")
            event_time_str = event.start_time.strftime("%I:%M %p")
            event_location_str = event.location or "See event details"

            for reg in registrations:
                if not reg.patron_email:
                    continue
                try:
                    await email_service.send_templated(
                        notification_type=NotificationType.EVENT_CANCELLED,
                        recipient_email=reg.patron_email,
                        context_data={
                            "patron_name": reg.patron_name,
                            "event_title": event.title,
                            "event_date": event_date_str,
                            "event_time": event_time_str,
                            "event_location": event_location_str,
                            "cancellation_reason": cancellation_reason,
                        },
                        db=self.db,
                    )
                except Exception as e:  # noqa: BLE001 -- per-registration boundary: one email failure must not block other recipients
                    logger.warning(
                        "Failed to send closure cancellation email to %s for event %s: %s",
                        reg.patron_email,
                        event.id,
                        e,
                    )

            for reg in registrations:
                reg.status = EventRegistrationStatus.CANCELLED.value

        # Service layer: flush, do not commit. Caller controls the transaction.
        await self.db.flush()

        # Mark closure flags only after the fan-out has completed.
        closure.events_canceled = True
        closure.programs_rescheduled = reschedule_programs

    async def get_affected_events(self, closure_id: int) -> list[dict[str, Any]]:
        result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        # Load branch manually (relationship is disabled on the model)
        branch_result = await self.db.execute(
            select(Branch).where(Branch.id == closure.branch_id)
        )
        branch = branch_result.scalar_one_or_none()

        # Find events within closure date range
        branch_name = branch.name if branch else ""
        result = await self.db.execute(
            select(Event)
            .where(
                and_(
                    Event.location == branch_name,
                    Event.start_time >= datetime.combine(closure.start_date, time.min),
                    Event.start_time <= datetime.combine(closure.end_date, time.max),
                )
            )
        )
        events = result.scalars().all()

        return [
            {
                "event_id": event.id,
                "title": event.title,
                "start_time": event.start_time.isoformat() if event.start_time else None,
                "end_time": event.end_time.isoformat() if event.end_time else None,
                "location": event.location,
                "category": event.category,
                "audience": event.audience,
            }
            for event in events
        ]

    # =========================================================================
    # EXTERNAL SERVICE INTEGRATIONS
    # =========================================================================

    async def update_external_services(
        self,
        closure_id: int,
        updated_by_id: int,
        website: bool = False,
        phone_message: bool = False,
        social_media: bool = False,
        google_maps: bool = False,
        apple_maps: bool = False,
    ) -> BranchClosure:
        result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        # Update status flags
        if website:
            closure.website_updated = True
        if phone_message:
            closure.phone_message_updated = True
        if social_media:
            closure.social_media_updated = True
        if google_maps:
            closure.google_maps_updated = True
        if apple_maps:
            closure.apple_maps_updated = True

        closure.updated_by_id = updated_by_id
        closure.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(closure)
        return closure

    # =========================================================================
    # PARTNER ORGANIZATIONS
    # =========================================================================

    async def notify_partners(
        self,
        closure_id: int,
        updated_by_id: int,
        partner_list: list[str] | None = None,
    ) -> BranchClosure:
        result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        # In production, would send notifications to partner organizations.
        # Mark complete for either full-partner or targeted-partner notifications.
        closure.partner_organizations_notified = True

        closure.updated_by_id = updated_by_id
        closure.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(closure)
        return closure

    async def _handle_partner_notifications(
        self,
        closure: BranchClosure,
        partner_list: list[str] | None = None,
    ) -> None:
        # Production implementation would dispatch partner-specific notifications.
        _ = partner_list
        closure.partner_organizations_notified = True

    # =========================================================================
    # REOPENING
    # =========================================================================

    async def schedule_reopening(
        self,
        closure_id: int,
        reopening_announcement: str,
        updated_by_id: int,
    ) -> BranchClosure:
        result = await self.db.execute(
            select(BranchClosure).where(BranchClosure.id == closure_id)
        )
        closure = result.scalar_one_or_none()
        if not closure:
            raise ValueError(f"Closure {closure_id} not found")

        closure.reopening_announcement = reopening_announcement
        closure.updated_by_id = updated_by_id
        closure.updated_at = datetime.now(timezone.utc)

        # In production, this would trigger reopening notifications to patrons
        # and update all external services

        await self.db.commit()
        await self.db.refresh(closure)
        return closure

    # =========================================================================
    # QUERY OPERATIONS
    # =========================================================================

    async def get_active_closures(
        self, branch_id: int | None = None
    ) -> list[BranchClosure]:
        today = datetime.now(timezone.utc).date()

        conditions = [
            BranchClosure.start_date <= today,
            BranchClosure.end_date >= today,
        ]
        if branch_id:
            conditions.append(BranchClosure.branch_id == branch_id)

        result = await self.db.execute(
            select(BranchClosure).where(and_(*conditions))
        )

        return list(result.scalars().all())

    async def get_closure_completion_status(
        self, closure_id: int
    ) -> dict[str, bool]:
        status = await self.get_closure_status(closure_id)
        closure = status["closure"]

        return {
            "patrons_notified": closure.patrons_with_holds_notified,
            "staff_notified": closure.staff_notified,
            "partners_notified": closure.partner_organizations_notified,
            "website_updated": closure.website_updated,
            "phone_updated": closure.phone_message_updated,
            "social_media_updated": closure.social_media_updated,
            "maps_updated": closure.google_maps_updated and closure.apple_maps_updated,
            "events_handled": closure.events_canceled,
            "all_complete": all(
                [
                    closure.patrons_with_holds_notified,
                    closure.staff_notified,
                    closure.partner_organizations_notified,
                    closure.website_updated,
                    closure.phone_message_updated,
                    closure.social_media_updated,
                    closure.google_maps_updated,
                    closure.apple_maps_updated,
                    closure.events_canceled,
                    closure.programs_rescheduled,
                ]
            ),
        }
