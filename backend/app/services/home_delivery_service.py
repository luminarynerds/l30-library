# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
import math
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from ..models.catalog import CatalogItem
from ..models.circulation import Checkout, CheckoutStatus
from ..models.home_delivery import (
    Delivery, DeliveryFeedback, DeliveryFrequency, DeliveryItem,
    DeliveryItemStatus, DeliveryRoute, DeliveryStatus, DeliveryVolunteer,
    HomeDeliveryApplication, HomeDeliveryApplicationStatus, HomeDeliveryEnrollment,
    HomeDeliveryEnrollmentStatus, HomeDeliveryItemRequest, ReadingPreferenceProfile,
    RouteStatus, VolunteerHourLog, VolunteerSchedule, DeliveryVolunteerStatus
)
from ..models.inventory import ItemCopy
from ..models.user import User
from .geocoding_service import GeocodingService


class HomeDeliveryApplicationService:

    @staticmethod
    async def create_application(
        db: AsyncSession,
        patron_id: int,
        data: dict
    ) -> HomeDeliveryApplication:
        # Check if patron already has a pending/approved application
        existing = await db.execute(
            select(HomeDeliveryApplication)
            .where(
                HomeDeliveryApplication.patron_id == patron_id,
                HomeDeliveryApplication.status.in_([
                    HomeDeliveryApplicationStatus.pending,
                    HomeDeliveryApplicationStatus.under_review,
                    HomeDeliveryApplicationStatus.approved
                ])
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("Patron already has an active application")

        # Check if patron is already enrolled
        enrolled = await db.execute(
            select(HomeDeliveryEnrollment)
            .where(
                HomeDeliveryEnrollment.patron_id == patron_id,
                HomeDeliveryEnrollment.status.in_([
                    HomeDeliveryEnrollmentStatus.active,
                    HomeDeliveryEnrollmentStatus.paused
                ])
            )
        )
        if enrolled.scalar_one_or_none():
            raise ValueError("Patron is already enrolled in home delivery service")

        application = HomeDeliveryApplication(
            patron_id=patron_id,
            **data
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)
        return application

    @staticmethod
    async def review_application(
        db: AsyncSession,
        application_id: int,
        reviewer_id: int,
        status: HomeDeliveryApplicationStatus,
        review_notes: Optional[str] = None,
        denial_reason: Optional[str] = None
    ) -> HomeDeliveryApplication:
        result = await db.execute(
            select(HomeDeliveryApplication)
            .where(HomeDeliveryApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise ValueError("Application not found")

        if application.status not in [
            HomeDeliveryApplicationStatus.pending,
            HomeDeliveryApplicationStatus.under_review,
            HomeDeliveryApplicationStatus.waitlisted
        ]:
            raise ValueError(f"Cannot review application in {application.status} status")

        application.status = status
        application.reviewed_by_id = reviewer_id
        application.reviewed_at = datetime.now(timezone.utc)
        application.review_notes = review_notes
        application.denial_reason = denial_reason

        await db.commit()
        await db.refresh(application)
        return application


class HomeDeliveryEnrollmentService:

    @staticmethod
    async def create_enrollment(
        db: AsyncSession,
        application_id: int,
        enrolled_by_id: int,
        overrides: Optional[dict] = None
    ) -> HomeDeliveryEnrollment:
        result = await db.execute(
            select(HomeDeliveryApplication)
            .where(HomeDeliveryApplication.id == application_id)
        )
        application = result.scalar_one_or_none()
        if not application:
            raise ValueError("Application not found")

        if application.status != HomeDeliveryApplicationStatus.approved:
            raise ValueError("Application must be approved before enrollment")

        # Check if enrollment already exists
        existing = await db.execute(
            select(HomeDeliveryEnrollment)
            .where(HomeDeliveryEnrollment.patron_id == application.patron_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Enrollment already exists for this patron")

        # Create enrollment with application data (can be overridden)
        enrollment_data = {
            "patron_id": application.patron_id,
            "application_id": application_id,
            "delivery_address": application.delivery_address,
            "delivery_instructions": application.delivery_instructions,
            "contact_phone": application.contact_phone,
            "alternate_contact_name": application.alternate_contact_name,
            "alternate_contact_phone": application.alternate_contact_phone,
            "delivery_frequency": application.preferred_frequency,
            "preferred_day": application.preferred_day,
            "preferred_time_start": application.preferred_time_start,
            "preferred_time_end": application.preferred_time_end,
            "enrolled_by_id": enrolled_by_id,
        }

        # Apply overrides
        if overrides:
            for key, value in overrides.items():
                if value is not None:
                    enrollment_data[key] = value

        enrollment = HomeDeliveryEnrollment(**enrollment_data)
        db.add(enrollment)

        # Create default reading preferences
        reading_prefs = ReadingPreferenceProfile(
            enrollment=enrollment,
            format_preferences=["standard_print"],
            preferred_genres=[],
            excluded_genres=[],
            favorite_authors=[],
            excluded_authors=[],
            interests=[],
            current_series=[]
        )
        db.add(reading_prefs)

        await db.commit()
        await db.refresh(enrollment)
        return enrollment

    @staticmethod
    async def calculate_next_delivery_date(
        frequency: DeliveryFrequency,
        preferred_day: Optional[str] = None,
        from_date: Optional[date] = None
    ) -> date:
        base = from_date or date.today()

        if frequency == DeliveryFrequency.weekly:
            delta = timedelta(days=7)
        elif frequency == DeliveryFrequency.biweekly:
            delta = timedelta(days=14)
        elif frequency == DeliveryFrequency.monthly:
            delta = timedelta(days=30)
        else:  # on_demand
            return base

        next_date = base + delta

        # Adjust to preferred day if specified
        if preferred_day:
            days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
            try:
                target_weekday = days.index(preferred_day)
                current_weekday = next_date.weekday()
                days_until = (target_weekday - current_weekday) % 7
                if days_until == 0:
                    days_until = 7  # Move to next week if already on that day
                next_date = next_date + timedelta(days=days_until)
            except ValueError:
                pass  # Invalid day name, use calculated date

        return next_date

    @staticmethod
    async def update_enrollment_status(
        db: AsyncSession,
        enrollment_id: int,
        status: HomeDeliveryEnrollmentStatus,
        pause_reason: Optional[str] = None,
        pause_until: Optional[date] = None,
        termination_reason: Optional[str] = None
    ) -> HomeDeliveryEnrollment:
        result = await db.execute(
            select(HomeDeliveryEnrollment)
            .where(HomeDeliveryEnrollment.id == enrollment_id)
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise ValueError("Enrollment not found")

        enrollment.status = status

        if status == HomeDeliveryEnrollmentStatus.paused:
            enrollment.paused_at = datetime.now(timezone.utc)
            enrollment.pause_reason = pause_reason
            enrollment.pause_until = pause_until
        elif status == HomeDeliveryEnrollmentStatus.terminated:
            enrollment.terminated_at = datetime.now(timezone.utc)
            enrollment.termination_reason = termination_reason
        elif status == HomeDeliveryEnrollmentStatus.active:
            enrollment.paused_at = None
            enrollment.pause_reason = None
            enrollment.pause_until = None

        await db.commit()
        await db.refresh(enrollment)
        return enrollment


class DeliveryVolunteerService:

    @staticmethod
    async def create_volunteer(
        db: AsyncSession,
        user_id: int,
        data: dict
    ) -> DeliveryVolunteer:
        # Check if volunteer profile already exists
        existing = await db.execute(
            select(DeliveryVolunteer)
            .where(DeliveryVolunteer.user_id == user_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Volunteer profile already exists for this user")

        volunteer = DeliveryVolunteer(
            user_id=user_id,
            status=DeliveryVolunteerStatus.pending_approval,
            **data
        )
        db.add(volunteer)
        await db.commit()
        await db.refresh(volunteer)
        return volunteer

    @staticmethod
    async def approve_volunteer(
        db: AsyncSession,
        volunteer_id: int,
        approved_by_id: int
    ) -> DeliveryVolunteer:
        result = await db.execute(
            select(DeliveryVolunteer)
            .where(DeliveryVolunteer.id == volunteer_id)
        )
        volunteer = result.scalar_one_or_none()
        if not volunteer:
            raise ValueError("Volunteer not found")

        if volunteer.status != DeliveryVolunteerStatus.pending_approval:
            raise ValueError("Volunteer is not pending approval")

        if not volunteer.background_check_completed:
            raise ValueError("Background check must be completed before approval")

        if not volunteer.training_completed:
            raise ValueError("Training must be completed before approval")

        volunteer.status = DeliveryVolunteerStatus.active
        volunteer.approved_at = datetime.now(timezone.utc)
        volunteer.approved_by_id = approved_by_id

        await db.commit()
        await db.refresh(volunteer)
        return volunteer

    @staticmethod
    async def log_volunteer_hours(
        db: AsyncSession,
        volunteer_id: int,
        date: date,
        hours: float,
        activity_type: str,
        delivery_route_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> VolunteerHourLog:
        hour_log = VolunteerHourLog(
            volunteer_id=volunteer_id,
            date=date,
            hours=hours,
            activity_type=activity_type,
            delivery_route_id=delivery_route_id,
            notes=notes
        )
        db.add(hour_log)

        # Update volunteer's total hours
        result = await db.execute(
            select(DeliveryVolunteer)
            .where(DeliveryVolunteer.id == volunteer_id)
        )
        volunteer = result.scalar_one_or_none()
        if volunteer:
            volunteer.total_volunteer_hours += hours
            volunteer.last_active_at = datetime.now(timezone.utc)

            # Update recognition level based on total hours
            await DeliveryVolunteerService._update_recognition_level(volunteer)

        await db.commit()
        await db.refresh(hour_log)
        return hour_log

    @staticmethod
    async def _update_recognition_level(volunteer: DeliveryVolunteer) -> None:
        total_hours = volunteer.total_volunteer_hours
        if total_hours >= 500:
            volunteer.recognition_level = "platinum"
        elif total_hours >= 250:
            volunteer.recognition_level = "gold"
        elif total_hours >= 100:
            volunteer.recognition_level = "silver"
        else:
            volunteer.recognition_level = "bronze"

    @staticmethod
    async def get_available_volunteers(
        db: AsyncSession,
        date: date,
        area: Optional[str] = None
    ) -> list[DeliveryVolunteer]:
        day_name = date.strftime("%A")

        # Get active volunteers
        query = (
            select(DeliveryVolunteer)
            .where(DeliveryVolunteer.status == DeliveryVolunteerStatus.active)
        )

        result = await db.execute(query)
        all_volunteers = result.scalars().all()

        available = []
        for volunteer in all_volunteers:
            # Check if day is in their available days
            if day_name not in (volunteer.available_days or []):
                continue

            # Check for specific schedule overrides
            schedule_result = await db.execute(
                select(VolunteerSchedule)
                .where(
                    VolunteerSchedule.volunteer_id == volunteer.id,
                    VolunteerSchedule.date == date
                )
            )
            schedule = schedule_result.scalar_one_or_none()
            if schedule and not schedule.is_available:
                continue

            # Check area preference if specified
            if area and volunteer.preferred_areas:
                if area not in volunteer.preferred_areas:
                    continue

            available.append(volunteer)

        return available


class DeliveryService:

    @staticmethod
    async def create_delivery(
        db: AsyncSession,
        enrollment_id: int,
        scheduled_date: date,
        scheduled_time_start: Optional[str] = None,
        scheduled_time_end: Optional[str] = None,
        route_id: Optional[int] = None,
        staff_notes: Optional[str] = None
    ) -> Delivery:
        # Get enrollment
        result = await db.execute(
            select(HomeDeliveryEnrollment)
            .where(HomeDeliveryEnrollment.id == enrollment_id)
        )
        enrollment = result.scalar_one_or_none()
        if not enrollment:
            raise ValueError("Enrollment not found")

        if enrollment.status != HomeDeliveryEnrollmentStatus.active:
            raise ValueError("Cannot create delivery for non-active enrollment")

        delivery = Delivery(
            enrollment_id=enrollment_id,
            scheduled_date=scheduled_date,
            scheduled_time_start=scheduled_time_start or enrollment.preferred_time_start,
            scheduled_time_end=scheduled_time_end or enrollment.preferred_time_end,
            delivery_address=enrollment.delivery_address,
            delivery_instructions=enrollment.delivery_instructions,
            route_id=route_id,
            staff_notes=staff_notes
        )
        db.add(delivery)
        await db.commit()
        await db.refresh(delivery)
        return delivery

    @staticmethod
    async def add_item_to_delivery(
        db: AsyncSession,
        delivery_id: int,
        item_id: int,
        item_copy_id: Optional[int],
        selected_by_id: int,
        selection_reason: Optional[str] = None,
        patron_requested: bool = False
    ) -> DeliveryItem:
        # Get delivery
        result = await db.execute(
            select(Delivery).where(Delivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            raise ValueError("Delivery not found")

        if delivery.status not in [DeliveryStatus.scheduled, DeliveryStatus.items_selected]:
            raise ValueError("Cannot add items to delivery in current status")

        # Get catalog item details
        item_result = await db.execute(
            select(CatalogItem).where(CatalogItem.id == item_id)
        )
        catalog_item = item_result.scalar_one_or_none()
        if not catalog_item:
            raise ValueError("Catalog item not found")

        # Get item copy if specified
        barcode = None
        if item_copy_id:
            copy_result = await db.execute(
                select(ItemCopy).where(ItemCopy.id == item_copy_id)
            )
            item_copy = copy_result.scalar_one_or_none()
            if item_copy:
                barcode = item_copy.barcode

        delivery_item = DeliveryItem(
            delivery_id=delivery_id,
            item_id=item_id,
            item_copy_id=item_copy_id,
            item_title=catalog_item.title,
            item_author=catalog_item.author,
            item_format=str(catalog_item.item_type) if catalog_item.item_type else None,
            item_barcode=barcode,
            status=DeliveryItemStatus.selected,
            selected_by_id=selected_by_id,
            selection_reason=selection_reason,
            patron_requested=patron_requested
        )
        db.add(delivery_item)

        # Update delivery status and count
        delivery.status = DeliveryStatus.items_selected
        delivery.items_count = (delivery.items_count or 0) + 1

        await db.commit()
        await db.refresh(delivery_item)
        return delivery_item

    @staticmethod
    async def update_delivery_status(
        db: AsyncSession,
        delivery_id: int,
        status: DeliveryStatus,
        staff_id: Optional[int] = None,
        volunteer_notes: Optional[str] = None,
        delivery_signature: Optional[str] = None,
        delivery_photo: Optional[str] = None,
        failure_reason: Optional[str] = None,
        reschedule_date: Optional[date] = None
    ) -> Delivery:
        result = await db.execute(
            select(Delivery)
            .options(selectinload(Delivery.items), selectinload(Delivery.enrollment))
            .where(Delivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            raise ValueError("Delivery not found")

        now = datetime.now(timezone.utc)
        delivery.status = status
        delivery.volunteer_notes = volunteer_notes

        if status == DeliveryStatus.packed:
            delivery.packed_at = now
            delivery.packed_by_id = staff_id
            # Update all items to packed
            for item in delivery.items:
                if item.status == DeliveryItemStatus.selected:
                    item.status = DeliveryItemStatus.packed

        elif status == DeliveryStatus.out_for_delivery:
            delivery.out_for_delivery_at = now

        elif status == DeliveryStatus.delivered:
            delivery.delivered_at = now
            delivery.delivery_signature = delivery_signature
            delivery.delivery_photo = delivery_photo
            # Update items and check out
            delivered_count = 0
            for item in delivery.items:
                if item.status == DeliveryItemStatus.packed:
                    item.status = DeliveryItemStatus.delivered
                    delivered_count += 1
                    # Checkout will be handled separately by checkout integration
            delivery.items_delivered = delivered_count

            # Update enrollment statistics
            if delivery.enrollment:
                delivery.enrollment.total_deliveries += 1
                delivery.enrollment.last_delivery_date = delivery.scheduled_date

        elif status == DeliveryStatus.delivery_failed:
            delivery.delivery_failed_at = now
            delivery.failure_reason = failure_reason
            delivery.reschedule_date = reschedule_date

        elif status == DeliveryStatus.picked_up:
            delivery.picked_up_at = now
            # Update returned items
            picked_up_count = 0
            for item in delivery.items:
                if item.status == DeliveryItemStatus.delivered:
                    item.status = DeliveryItemStatus.returned
                    item.returned_at = now
                    picked_up_count += 1
            delivery.items_picked_up = picked_up_count

        await db.commit()
        await db.refresh(delivery)
        return delivery

    @staticmethod
    async def checkout_delivery_items(
        db: AsyncSession,
        delivery_id: int,
        checkout_days: int = 28
    ) -> list[Checkout]:
        result = await db.execute(
            select(Delivery)
            .options(
                selectinload(Delivery.items),
                selectinload(Delivery.enrollment)
            )
            .where(Delivery.id == delivery_id)
        )
        delivery = result.scalar_one_or_none()
        if not delivery:
            raise ValueError("Delivery not found")

        if delivery.status != DeliveryStatus.delivered:
            raise ValueError("Can only checkout items for delivered deliveries")

        checkouts = []
        now = datetime.now(timezone.utc)
        due_date = now + timedelta(days=checkout_days)

        for item in delivery.items:
            if item.status == DeliveryItemStatus.delivered and not item.checkout_id:
                # Create checkout
                checkout = Checkout(
                    user_id=delivery.enrollment.patron_id,
                    item_id=item.item_id,
                    item_copy_id=item.item_copy_id,
                    status=CheckoutStatus.active,
                    checked_out_at=now,
                    due_date=due_date
                )
                db.add(checkout)
                await db.flush()

                # Increment total_checkouts on the catalog item
                await db.execute(
                    update(CatalogItem)
                    .where(CatalogItem.id == item.item_id)
                    .values(total_checkouts=func.coalesce(CatalogItem.total_checkouts, 0) + 1)
                )

                # Link to delivery item
                item.checkout_id = checkout.id
                item.checked_out_at = now
                item.due_date = due_date.date()

                checkouts.append(checkout)

        await db.commit()
        return checkouts


class DeliveryRouteService:

    @staticmethod
    async def create_route(
        db: AsyncSession,
        name: str,
        date: date,
        created_by_id: int,
        volunteer_id: Optional[int] = None,
        planned_start_time: Optional[str] = None,
        planned_end_time: Optional[str] = None,
        notes: Optional[str] = None
    ) -> DeliveryRoute:
        route = DeliveryRoute(
            name=name,
            date=date,
            volunteer_id=volunteer_id,
            planned_start_time=planned_start_time,
            planned_end_time=planned_end_time,
            notes=notes,
            created_by_id=created_by_id
        )
        db.add(route)
        await db.commit()
        await db.refresh(route)
        return route

    @staticmethod
    async def assign_deliveries_to_route(
        db: AsyncSession,
        route_id: int,
        delivery_ids: list[int]
    ) -> DeliveryRoute:
        result = await db.execute(
            select(DeliveryRoute)
            .options(selectinload(DeliveryRoute.deliveries))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one_or_none()
        if not route:
            raise ValueError("Route not found")

        if route.status not in [RouteStatus.draft, RouteStatus.planned]:
            raise ValueError("Cannot modify route in current status")

        # Get deliveries
        delivery_result = await db.execute(
            select(Delivery).where(Delivery.id.in_(delivery_ids))
        )
        deliveries = delivery_result.scalars().all()

        # Assign to route
        for i, delivery in enumerate(deliveries):
            delivery.route_id = route_id
            delivery.route_order = i + 1

        route.total_stops = len(deliveries)
        route.total_items = sum(d.items_count or 0 for d in deliveries)

        await db.commit()
        await db.refresh(route)
        return route

    @staticmethod
    async def optimize_route(
        db: AsyncSession,
        route_id: int,
        start_location: Optional[str] = None
    ) -> DeliveryRoute:
        result = await db.execute(
            select(DeliveryRoute)
            .options(selectinload(DeliveryRoute.deliveries))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one_or_none()
        if not route:
            raise ValueError("Route not found")

        deliveries = list(route.deliveries)
        if len(deliveries) < 2:
            return route

        # Prepare stops for optimization
        stops = [
            {
                "id": d.id,
                "address": d.delivery_address,
            }
            for d in deliveries
        ]

        # Get starting coordinates if provided
        start_coords = None
        if start_location:
            start_coords = await GeocodingService.geocode_address(start_location)

        # Optimize using real distance calculations
        optimized_stops, total_distance, estimated_duration = (
            await GeocodingService.optimize_route_by_distance(stops, start_coords)
        )

        # Create a mapping from delivery ID to optimized order
        id_to_order = {stop["id"]: i + 1 for i, stop in enumerate(optimized_stops)}

        # Update route order for each delivery
        optimized_order = []
        route_geometry = []
        for delivery in deliveries:
            new_order = id_to_order.get(delivery.id, len(deliveries))
            delivery.route_order = new_order

        # Sort by new order and build optimized_order list
        sorted_deliveries = sorted(deliveries, key=lambda d: d.route_order)
        for delivery in sorted_deliveries:
            optimized_order.append(delivery.id)
            # Find matching stop to get coordinates for geometry
            for stop in optimized_stops:
                if stop["id"] == delivery.id and stop.get("lat") and stop.get("lon"):
                    route_geometry.append({
                        "delivery_id": delivery.id,
                        "lat": stop["lat"],
                        "lon": stop["lon"],
                        "address": delivery.delivery_address
                    })
                    break

        route.optimized_order = optimized_order
        route.route_geometry = route_geometry if route_geometry else None
        route.estimated_distance_miles = round(total_distance, 2)
        route.estimated_duration_minutes = int(estimated_duration)

        await db.commit()
        await db.refresh(route)
        return route

    @staticmethod
    async def start_route(
        db: AsyncSession,
        route_id: int
    ) -> DeliveryRoute:
        result = await db.execute(
            select(DeliveryRoute).where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one_or_none()
        if not route:
            raise ValueError("Route not found")

        route.status = RouteStatus.in_progress
        route.actual_start_time = datetime.now(timezone.utc)

        await db.commit()
        await db.refresh(route)
        return route

    @staticmethod
    async def complete_route(
        db: AsyncSession,
        route_id: int,
        volunteer_id: int
    ) -> DeliveryRoute:
        result = await db.execute(
            select(DeliveryRoute)
            .options(selectinload(DeliveryRoute.deliveries))
            .where(DeliveryRoute.id == route_id)
        )
        route = result.scalar_one_or_none()
        if not route:
            raise ValueError("Route not found")

        route.status = RouteStatus.completed
        route.actual_end_time = datetime.now(timezone.utc)

        # Calculate completed stops
        completed = sum(1 for d in route.deliveries if d.status == DeliveryStatus.delivered)
        route.completed_stops = completed

        # Calculate hours worked
        if route.actual_start_time:
            duration = route.actual_end_time - route.actual_start_time
            hours = duration.total_seconds() / 3600

            # Log volunteer hours
            if route.volunteer_id:
                await DeliveryVolunteerService.log_volunteer_hours(
                    db=db,
                    volunteer_id=route.volunteer_id,
                    date=route.date,
                    hours=round(hours, 2),
                    activity_type="delivery",
                    delivery_route_id=route_id,
                    notes=f"Completed route {route.name}: {completed} deliveries"
                )

        await db.commit()
        await db.refresh(route)
        return route


class HomeDeliveryFeedbackService:

    @staticmethod
    async def submit_feedback(
        db: AsyncSession,
        delivery_id: int,
        data: dict
    ) -> DeliveryFeedback:
        # Check if feedback already exists
        existing = await db.execute(
            select(DeliveryFeedback)
            .where(DeliveryFeedback.delivery_id == delivery_id)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Feedback already submitted for this delivery")

        # Verify delivery exists and is delivered
        delivery_result = await db.execute(
            select(Delivery).where(Delivery.id == delivery_id)
        )
        delivery = delivery_result.scalar_one_or_none()
        if not delivery:
            raise ValueError("Delivery not found")

        if delivery.status not in [DeliveryStatus.delivered, DeliveryStatus.picked_up]:
            raise ValueError("Can only submit feedback for completed deliveries")

        # Flag low ratings for follow-up
        requires_follow_up = data.get("overall_rating", 5) <= 2

        feedback = DeliveryFeedback(
            delivery_id=delivery_id,
            requires_follow_up=requires_follow_up,
            **data
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)
        return feedback

    @staticmethod
    async def complete_follow_up(
        db: AsyncSession,
        feedback_id: int,
        staff_id: int,
        notes: str
    ) -> DeliveryFeedback:
        result = await db.execute(
            select(DeliveryFeedback)
            .where(DeliveryFeedback.id == feedback_id)
        )
        feedback = result.scalar_one_or_none()
        if not feedback:
            raise ValueError("Feedback not found")

        feedback.follow_up_completed = True
        feedback.follow_up_by_id = staff_id
        feedback.follow_up_at = datetime.now(timezone.utc)
        feedback.follow_up_notes = notes

        await db.commit()
        await db.refresh(feedback)
        return feedback


class HomeDeliveryReportService:

    @staticmethod
    async def get_summary_stats(db: AsyncSession) -> dict:
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Total enrolled patrons
        total_enrolled = await db.execute(
            select(func.count(HomeDeliveryEnrollment.id))
        )

        # Active enrolled patrons
        active_enrolled = await db.execute(
            select(func.count(HomeDeliveryEnrollment.id))
            .where(HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.active)
        )

        # Pending applications
        pending_apps = await db.execute(
            select(func.count(HomeDeliveryApplication.id))
            .where(HomeDeliveryApplication.status == HomeDeliveryApplicationStatus.pending)
        )

        # Active volunteers
        active_volunteers = await db.execute(
            select(func.count(DeliveryVolunteer.id))
            .where(DeliveryVolunteer.status == DeliveryVolunteerStatus.active)
        )

        # Deliveries this month
        deliveries_month = await db.execute(
            select(func.count(Delivery.id))
            .where(
                Delivery.scheduled_date >= month_start.date(),
                Delivery.status == DeliveryStatus.delivered
            )
        )

        # Items delivered this month
        items_month = await db.execute(
            select(func.sum(Delivery.items_delivered))
            .where(
                Delivery.scheduled_date >= month_start.date(),
                Delivery.status == DeliveryStatus.delivered
            )
        )

        # Average rating
        avg_rating = await db.execute(
            select(func.avg(DeliveryFeedback.overall_rating))
            .join(Delivery)
            .where(Delivery.scheduled_date >= month_start.date())
        )

        # Volunteer hours this month
        volunteer_hours = await db.execute(
            select(func.sum(VolunteerHourLog.hours))
            .where(VolunteerHourLog.date >= month_start.date())
        )

        _avg_rating_val = avg_rating.scalar()

        return {
            "total_enrolled_patrons": total_enrolled.scalar() or 0,
            "active_enrolled_patrons": active_enrolled.scalar() or 0,
            "pending_applications": pending_apps.scalar() or 0,
            "active_volunteers": active_volunteers.scalar() or 0,
            "total_deliveries_this_month": deliveries_month.scalar() or 0,
            "total_items_delivered_this_month": items_month.scalar() or 0,
            "average_delivery_rating": round(_avg_rating_val, 2) if _avg_rating_val else None,
            "total_volunteer_hours_this_month": round(volunteer_hours.scalar() or 0, 2)
        }

    @staticmethod
    async def get_patron_reports(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict]:
        result = await db.execute(
            select(HomeDeliveryEnrollment)
            .options(
                joinedload(HomeDeliveryEnrollment.patron),
                joinedload(HomeDeliveryEnrollment.assigned_volunteer).joinedload(DeliveryVolunteer.user)
            )
            .where(HomeDeliveryEnrollment.status == HomeDeliveryEnrollmentStatus.active)
            .order_by(HomeDeliveryEnrollment.enrolled_at.desc())
            .limit(limit)
            .offset(offset)
        )
        enrollments = result.unique().scalars().all()

        reports = []
        for enrollment in enrollments:
            # Get average rating given by this patron
            rating_result = await db.execute(
                select(func.avg(DeliveryFeedback.overall_rating))
                .join(Delivery)
                .where(Delivery.enrollment_id == enrollment.id)
            )
            avg_rating = rating_result.scalar()

            # Get total items received
            items_result = await db.execute(
                select(func.sum(Delivery.items_delivered))
                .where(
                    Delivery.enrollment_id == enrollment.id,
                    Delivery.status == DeliveryStatus.delivered
                )
            )
            total_items = items_result.scalar() or 0

            reports.append({
                "patron_id": enrollment.patron_id,
                "patron_name": enrollment.patron.full_name if enrollment.patron else "Unknown",
                "enrolled_since": enrollment.enrolled_at.date() if enrollment.enrolled_at else None,
                "total_deliveries": enrollment.total_deliveries,
                "total_items_received": total_items,
                "average_rating_given": round(avg_rating, 2) if avg_rating else None,
                "last_delivery_date": enrollment.last_delivery_date,
                "assigned_volunteer": (
                    enrollment.assigned_volunteer.user.full_name
                    if enrollment.assigned_volunteer and enrollment.assigned_volunteer.user
                    else None
                )
            })

        return reports

    @staticmethod
    async def get_volunteer_reports(
        db: AsyncSession,
        limit: int = 50,
        offset: int = 0
    ) -> list[dict]:
        result = await db.execute(
            select(DeliveryVolunteer)
            .options(joinedload(DeliveryVolunteer.user))
            .order_by(DeliveryVolunteer.total_volunteer_hours.desc())
            .limit(limit)
            .offset(offset)
        )
        volunteers = result.unique().scalars().all()

        reports = []
        for volunteer in volunteers:
            # Get assigned patron count
            patron_count = await db.execute(
                select(func.count(HomeDeliveryEnrollment.id))
                .where(HomeDeliveryEnrollment.assigned_volunteer_id == volunteer.id)
            )

            # Get average rating from feedback on their deliveries
            rating_result = await db.execute(
                select(func.avg(DeliveryFeedback.volunteer_rating))
                .join(Delivery)
                .join(DeliveryRoute)
                .where(DeliveryRoute.volunteer_id == volunteer.id)
            )
            avg_rating = rating_result.scalar()

            reports.append({
                "volunteer_id": volunteer.id,
                "volunteer_name": volunteer.user.full_name if volunteer.user else "Unknown",
                "status": volunteer.status,
                "total_deliveries": volunteer.total_deliveries,
                "total_hours": round(volunteer.total_volunteer_hours, 2),
                "recognition_level": volunteer.recognition_level,
                "assigned_patrons": patron_count.scalar() or 0,
                "average_rating": round(avg_rating, 2) if avg_rating else None,
                "joined_date": volunteer.approved_at.date() if volunteer.approved_at else None
            })

        return reports
