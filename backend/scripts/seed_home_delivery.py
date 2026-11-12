#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for home delivery patron delivery services.

Creates:
- HomeDelivery applications and enrollments
- Reading preference profiles
- Delivery volunteers
- Delivery routes and deliveries
- Volunteer hour logs
"""
import asyncio
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole, PatronStatus, NoticePreference
from app.models.home_delivery import (
    HomeDeliveryApplication, HomeDeliveryApplicationStatus,
    HomeDeliveryEnrollment, HomeDeliveryEnrollmentStatus,
    ReadingPreferenceProfile, ReadingFormatPreference,
    DeliveryVolunteer, VolunteerStatus,
    DeliveryRoute, RouteStatus, Delivery, DeliveryStatus,
    DeliveryFrequency, VolunteerHourLog
)


async def get_or_create_test_users(db):
    """Get test users, creating home-delivery-specific ones if needed."""
    users = {}

    # Get existing test users
    test_emails = [
        "patron.reader@l30.org",
        "patron.active@l30.org",
        "staff@l30.org"
    ]

    for email in test_emails:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()
        if user:
            users[email] = user

    # Create home-delivery-specific patrons if needed
    home_delivery_patron_emails = [
        ("home.delivery.patient@l30.org", "Margaret", "Johnson"),
        ("home.delivery.senior@l30.org", "Robert", "Chen"),
    ]

    for email, first_name, last_name in home_delivery_patron_emails:
        result = await db.execute(
            select(User).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                email=email,
                first_name=first_name,
                last_name=last_name,
                password_hash="placeholder_hash",
                role=UserRole.PATRON,
                is_active=True,
                patron_status=PatronStatus.ACTIVE,
                notice_preference=NoticePreference.EMAIL,
                email_verified=True,
                track_reading_history=True,
            )
            db.add(user)
            await db.flush()

        users[email] = user

    return users


async def seed_home_delivery_applications(db, users):
    """Create home delivery applications and enrollments."""
    print("\n" + "=" * 70)
    print("SEEDING HOME DELIVERY APPLICATIONS & ENROLLMENTS")
    print("=" * 70 + "\n")

    applications_data = [
        {
            "patron_email": "home.delivery.patient@l30.org",
            "reason": "Recovering from surgery - mobility restricted for 3 months",
            "delivery_address": "123 Oak Street, Apt 4B",
            "delivery_instructions": "Leave on front porch, cannot climb stairs",
            "contact_phone": "555-0101",
            "preferred_frequency": DeliveryFrequency.biweekly,
            "preferred_day": "Tuesday",
            "preferred_time_start": "09:00",
            "preferred_time_end": "12:00",
        },
        {
            "patron_email": "home.delivery.senior@l30.org",
            "reason": "Age-related mobility limitations",
            "delivery_address": "456 Elm Avenue",
            "delivery_instructions": "Ring doorbell three times, I may be slow to answer",
            "contact_phone": "555-0102",
            "preferred_frequency": DeliveryFrequency.weekly,
            "preferred_day": "Monday",
            "preferred_time_start": "10:00",
            "preferred_time_end": "13:00",
        },
    ]

    created_count = 0

    for app_data in applications_data:
        patron = users.get(app_data["patron_email"])
        if not patron:
            print(f"⚠️  Patron not found: {app_data['patron_email']}")
            continue

        # Check if already has enrollment
        result = await db.execute(
            select(HomeDeliveryEnrollment).where(
                HomeDeliveryEnrollment.patron_id == patron.id
            )
        )
        if result.scalar_one_or_none():
            print(f"⊘ SKIPPED: {patron.full_name} (already enrolled)")
            continue

        try:
            # Create application
            application = HomeDeliveryApplication(
                patron_id=patron.id,
                status=HomeDeliveryApplicationStatus.approved,
                reason=app_data["reason"],
                medical_documentation=True,
                delivery_address=app_data["delivery_address"],
                delivery_instructions=app_data["delivery_instructions"],
                contact_phone=app_data["contact_phone"],
                preferred_frequency=app_data["preferred_frequency"],
                preferred_day=app_data["preferred_day"],
                preferred_time_start=app_data["preferred_time_start"],
                preferred_time_end=app_data["preferred_time_end"],
                reviewed_at=datetime.now(timezone.utc),
            )
            db.add(application)
            await db.flush()

            # Create enrollment
            enrollment = HomeDeliveryEnrollment(
                patron_id=patron.id,
                application_id=application.id,
                status=HomeDeliveryEnrollmentStatus.active,
                delivery_address=app_data["delivery_address"],
                delivery_instructions=app_data["delivery_instructions"],
                contact_phone=app_data["contact_phone"],
                delivery_frequency=app_data["preferred_frequency"],
                preferred_day=app_data["preferred_day"],
                preferred_time_start=app_data["preferred_time_start"],
                preferred_time_end=app_data["preferred_time_end"],
                next_scheduled_delivery=date.today() + timedelta(days=7),
            )
            db.add(enrollment)
            await db.flush()

            # Create reading preferences
            reading_prefs = ReadingPreferenceProfile(
                enrollment_id=enrollment.id,
                format_preferences=["standard_print", "large_print"],
                preferred_genres=["mystery", "historical_fiction", "biography"],
                favorite_authors=["Agatha Christie", "Stephen King", "Nora Roberts"],
                fiction_preference=0.7,
                content_rating="general",
                language_preference="English",
                interests=["gardening", "history", "cooking"],
                prefers_large_print=True,
                prefers_short_books=False,
            )
            db.add(reading_prefs)

            print(f"✓ CREATED: {patron.full_name}")
            print(f"  Enrollment ID: {enrollment.id}")
            print(f"  Delivery Frequency: {app_data['preferred_frequency'].value}")
            print(f"  Address: {app_data['delivery_address']}\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {patron.full_name} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {patron.full_name} - {str(e)}\n")
            continue

    return created_count


async def seed_volunteers(db, users):
    """Create delivery volunteers."""
    print("\n" + "=" * 70)
    print("SEEDING DELIVERY VOLUNTEERS")
    print("=" * 70 + "\n")

    volunteers_data = [
        {
            "name": "Angela Martinez",
            "email": "volunteer.angela@l30.org",
            "phone": "555-0201",
            "has_vehicle": True,
            "vehicle_type": "Honda Civic",
            "available_days": ["Monday", "Tuesday", "Thursday"],
            "available_time_start": "09:00",
            "available_time_end": "16:00",
        },
        {
            "name": "David Wong",
            "email": "volunteer.david@l30.org",
            "phone": "555-0202",
            "has_vehicle": True,
            "vehicle_type": "Toyota Corolla",
            "available_days": ["Wednesday", "Friday", "Saturday"],
            "available_time_start": "10:00",
            "available_time_end": "17:00",
        },
    ]

    created_count = 0

    for vol_data in volunteers_data:
        # Check if volunteer user exists
        result = await db.execute(
            select(User).where(User.email == vol_data["email"])
        )
        user = result.scalar_one_or_none()

        if not user:
            # Create volunteer user
            user = User(
                email=vol_data["email"],
                first_name=vol_data["name"].split()[0],
                last_name=vol_data["name"].split()[1],
                password_hash="placeholder_hash",
                role=UserRole.PATRON,  # Volunteers can be patrons or special role
                is_active=True,
                patron_status=PatronStatus.ACTIVE,
                notice_preference=NoticePreference.EMAIL,
                email_verified=True,
            )
            db.add(user)
            await db.flush()

        # Check if already a volunteer
        result = await db.execute(
            select(DeliveryVolunteer).where(DeliveryVolunteer.user_id == user.id)
        )
        if result.scalar_one_or_none():
            print(f"⊘ SKIPPED: {vol_data['name']} (already registered)")
            continue

        try:
            volunteer = DeliveryVolunteer(
                user_id=user.id,
                status=VolunteerStatus.active,
                phone=vol_data["phone"],
                has_vehicle=vol_data["has_vehicle"],
                vehicle_type=vol_data["vehicle_type"],
                can_transport_large_items=True,
                background_check_completed=True,
                background_check_date=date.today() - timedelta(days=30),
                background_check_expiry=date.today() + timedelta(days=365),
                training_completed=True,
                training_date=date.today() - timedelta(days=7),
                available_days=vol_data["available_days"],
                available_time_start=vol_data["available_time_start"],
                available_time_end=vol_data["available_time_end"],
                max_deliveries_per_day=5,
                max_deliveries_per_week=15,
                preferred_areas=["downtown", "eastside"],
                max_driving_distance=20,
                recognition_level="silver",
                approved_at=datetime.now(timezone.utc),
            )
            db.add(volunteer)
            await db.flush()

            print(f"✓ CREATED: {vol_data['name']}")
            print(f"  Volunteer ID: {volunteer.id}")
            print(f"  Status: {VolunteerStatus.active.value}")
            print(f"  Available Days: {', '.join(vol_data['available_days'])}\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {vol_data['name']} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {vol_data['name']} - {str(e)}\n")
            continue

    return created_count


async def seed_routes_and_deliveries(db):
    """Create delivery routes and scheduled deliveries."""
    print("\n" + "=" * 70)
    print("SEEDING DELIVERY ROUTES & DELIVERIES")
    print("=" * 70 + "\n")

    # Get volunteers and enrollments
    result = await db.execute(select(DeliveryVolunteer).options(selectinload(DeliveryVolunteer.user)))
    volunteers = result.scalars().all()

    result = await db.execute(select(HomeDeliveryEnrollment))
    enrollments = result.scalars().all()

    if not volunteers or not enrollments:
        print("⚠️  No volunteers or enrollments found, skipping routes\n")
        return 0

    created_count = 0

    # Create a route for upcoming delivery
    route_date = date.today() + timedelta(days=3)

    try:
        route = DeliveryRoute(
            name=f"Weekly Route - {route_date.strftime('%A, %B %d')}",
            date=route_date,
            status=RouteStatus.planned,
            volunteer_id=volunteers[0].id,
            estimated_duration_minutes=120,
            estimated_distance_miles=25.5,
            planned_start_time="09:00",
            planned_end_time="11:00",
            total_stops=len(enrollments),
        )
        db.add(route)
        await db.flush()

        # Create deliveries for this route
        for idx, enrollment in enumerate(enrollments):
            delivery = Delivery(
                enrollment_id=enrollment.id,
                route_id=route.id,
                route_order=idx + 1,
                status=DeliveryStatus.scheduled,
                scheduled_date=route_date,
                scheduled_time_start=f"{9 + idx:02d}:00",
                scheduled_time_end=f"{9 + idx:02d}:30",
                delivery_address=enrollment.delivery_address,
                delivery_instructions=enrollment.delivery_instructions,
                items_count=3,
            )
            db.add(delivery)

        await db.flush()

        print(f"✓ CREATED: Route '{route.name}'")
        print(f"  Route ID: {route.id}")
        print(f"  Volunteer: {volunteers[0].user.full_name}")
        print(f"  Deliveries: {len(enrollments)}\n")

        created_count = 1

    except IntegrityError as e:
        await db.rollback()
        print(f"✗ ERROR creating route: {str(e)}\n")
    except Exception as e:
        await db.rollback()
        print(f"✗ ERROR creating route: {str(e)}\n")

    return created_count


async def seed_volunteer_hours(db):
    """Create volunteer hour logs."""
    print("\n" + "=" * 70)
    print("SEEDING VOLUNTEER HOUR LOGS")
    print("=" * 70 + "\n")

    result = await db.execute(select(DeliveryVolunteer).options(selectinload(DeliveryVolunteer.user)))
    volunteers = result.scalars().all()

    if not volunteers:
        print("⚠️  No volunteers found, skipping hour logs\n")
        return 0

    created_count = 0

    for volunteer in volunteers:
        try:
            # Create hour logs for past activities
            for i in range(3):
                log_date = date.today() - timedelta(days=i*7)
                log = VolunteerHourLog(
                    volunteer_id=volunteer.id,
                    date=log_date,
                    hours=2.5 + (i * 0.5),
                    activity_type="delivery",
                    notes=f"Completed deliveries on {log_date.strftime('%A')}",
                    verified=True,
                )
                db.add(log)

            # Update volunteer statistics
            volunteer.total_deliveries = len(volunteers) * 3
            volunteer.total_volunteer_hours = 7.5
            volunteer.last_active_at = datetime.now(timezone.utc)

            created_count += 3
            print(f"✓ CREATED: 3 hour logs for {volunteer.user.full_name}\n")

        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR for {volunteer.user.full_name}: {str(e)}\n")
            continue

    return created_count


async def main():
    """Main entry point."""
    async with AsyncSessionLocal() as db:
        try:
            print("\n" + "=" * 70)
            print("HOME DELIVERY SERVICE SEEDING")
            print("=" * 70)

            # Get/create test users
            users = await get_or_create_test_users(db)
            await db.commit()

            # Seed applications and enrollments
            app_count = await seed_home_delivery_applications(db, users)
            await db.commit()

            # Seed volunteers
            vol_count = await seed_volunteers(db, users)
            await db.commit()

            # Seed routes and deliveries
            route_count = await seed_routes_and_deliveries(db)
            await db.commit()

            # Seed volunteer hours
            hours_count = await seed_volunteer_hours(db)
            await db.commit()

            # Summary
            print("=" * 70)
            print("SEED COMPLETE")
            print("=" * 70)
            print(f"✓ Applications/Enrollments: {app_count}")
            print(f"✓ Volunteers: {vol_count}")
            print(f"✓ Routes Created: {route_count}")
            print(f"✓ Hour Logs: {hours_count}")
            print("=" * 70 + "\n")

            return 0

        except Exception as e:
            await db.rollback()
            print(f"\n✗ Error during seeding: {str(e)}\n")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
