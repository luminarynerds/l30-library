#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for library room reservations.

Creates:
- Library study and meeting rooms
- Room reservations and bookings
- Room usage statistics
"""
import asyncio
import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.models.room import (
    Room, RoomType, RoomReservation, ReservationStatus,
    RoomEquipment, RoomUsageStats
)


async def seed_rooms(db):
    """Create library rooms."""
    print("\n" + "=" * 70)
    print("SEEDING LIBRARY ROOMS")
    print("=" * 70 + "\n")

    # Operating hours - all day 9 AM to 9 PM
    operating_hours = {
        "monday": {"open": "09:00", "close": "21:00"},
        "tuesday": {"open": "09:00", "close": "21:00"},
        "wednesday": {"open": "09:00", "close": "21:00"},
        "thursday": {"open": "09:00", "close": "21:00"},
        "friday": {"open": "09:00", "close": "21:00"},
        "saturday": {"open": "10:00", "close": "18:00"},
        "sunday": {"open": "12:00", "close": "18:00"},
    }

    rooms_data = [
        {
            "name": "Study Room A",
            "description": "Quiet study space for individuals or small groups",
            "room_type": RoomType.study_room,
            "capacity": 2,
            "floor": "1",
            "room_number": "101",
            "amenities": ["desk", "chair", "outlet"],
            "requires_approval": False,
            "max_duration_minutes": 120,
            "min_duration_minutes": 30,
            "advance_booking_days": 7,
            "min_advance_hours": 1,
        },
        {
            "name": "Study Room B",
            "description": "Quiet study space for individuals or small groups",
            "room_type": RoomType.study_room,
            "capacity": 2,
            "floor": "1",
            "room_number": "102",
            "amenities": ["desk", "chair", "outlet"],
            "requires_approval": False,
            "max_duration_minutes": 120,
            "min_duration_minutes": 30,
            "advance_booking_days": 7,
            "min_advance_hours": 1,
        },
        {
            "name": "Study Room C",
            "description": "Quiet study space for groups up to 4 people",
            "room_type": RoomType.study_room,
            "capacity": 4,
            "floor": "1",
            "room_number": "103",
            "amenities": ["desks", "chairs", "outlets", "whiteboard"],
            "requires_approval": False,
            "max_duration_minutes": 120,
            "min_duration_minutes": 30,
            "advance_booking_days": 7,
            "min_advance_hours": 1,
        },
        {
            "name": "Community Meeting Room",
            "description": "Medium-sized room for community meetings and programs",
            "room_type": RoomType.meeting_room,
            "capacity": 30,
            "floor": "2",
            "room_number": "201",
            "amenities": ["tables", "chairs", "whiteboard", "screen", "projector"],
            "requires_approval": True,
            "max_duration_minutes": 240,
            "min_duration_minutes": 60,
            "advance_booking_days": 14,
            "min_advance_hours": 24,
            "available_equipment": [
                {"id": "projector", "name": "Projector", "requires_staff": False},
                {"id": "video_conf", "name": "Video Conferencing", "requires_staff": True},
                {"id": "sound_system", "name": "Sound System", "requires_staff": True},
            ],
        },
        {
            "name": "Computer Lab",
            "description": "Lab with 12 computers for digital literacy programs",
            "room_type": RoomType.computer_lab,
            "capacity": 12,
            "floor": "2",
            "room_number": "202",
            "amenities": ["computers", "chairs", "tables", "printer"],
            "requires_approval": False,
            "max_duration_minutes": 180,
            "min_duration_minutes": 60,
            "advance_booking_days": 7,
            "min_advance_hours": 24,
        },
        {
            "name": "Event Space",
            "description": "Large multipurpose space for library events and presentations",
            "room_type": RoomType.event_space,
            "capacity": 100,
            "floor": "1",
            "room_number": "110",
            "amenities": ["stage", "sound_system", "projector", "screen", "chairs"],
            "requires_approval": True,
            "max_duration_minutes": 480,
            "min_duration_minutes": 120,
            "advance_booking_days": 30,
            "min_advance_hours": 48,
            "available_equipment": [
                {"id": "projector", "name": "Projector", "requires_staff": False},
                {"id": "microphone", "name": "Microphone System", "requires_staff": True},
                {"id": "livestream", "name": "Livestream Setup", "requires_staff": True},
            ],
        },
    ]

    created_count = 0

    for room_data in rooms_data:
        # Check if already exists
        result = await db.execute(
            select(Room).where(Room.name == room_data["name"])
        )
        if result.scalar_one_or_none():
            print(f"⊘ SKIPPED: {room_data['name']} (already exists)")
            continue

        try:
            room = Room(
                name=room_data["name"],
                description=room_data["description"],
                room_type=room_data["room_type"],
                capacity=room_data["capacity"],
                floor=room_data["floor"],
                room_number=room_data["room_number"],
                amenities=room_data["amenities"],
                requires_approval=room_data["requires_approval"],
                max_duration_minutes=room_data["max_duration_minutes"],
                min_duration_minutes=room_data["min_duration_minutes"],
                advance_booking_days=room_data["advance_booking_days"],
                min_advance_hours=room_data["min_advance_hours"],
                operating_hours=operating_hours,
                is_active=True,
            )

            if "available_equipment" in room_data:
                room.available_equipment = room_data["available_equipment"]

            db.add(room)
            await db.flush()

            print(f"✓ CREATED: {room_data['name']}")
            print(f"  Type: {room_data['room_type'].value}")
            print(f"  Capacity: {room_data['capacity']} people")
            print(f"  Requires Approval: {room_data['requires_approval']}\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {room_data['name']} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {room_data['name']} - {str(e)}\n")
            continue

    return created_count


async def seed_room_equipment(db):
    """Create room equipment definitions."""
    print("\n" + "=" * 70)
    print("SEEDING ROOM EQUIPMENT")
    print("=" * 70 + "\n")

    equipment_data = [
        {
            "name": "Projector",
            "description": "Ceiling-mounted projector for presentations",
            "equipment_code": "projector",
            "total_quantity": 3,
            "requires_staff_setup": False,
        },
        {
            "name": "Video Conferencing System",
            "description": "Zoom/Teams-compatible video conference system",
            "equipment_code": "video_conf",
            "total_quantity": 2,
            "requires_staff_setup": True,
        },
        {
            "name": "Sound System",
            "description": "Amplified speakers and microphones",
            "equipment_code": "sound_system",
            "total_quantity": 2,
            "requires_staff_setup": True,
        },
        {
            "name": "Whiteboard",
            "description": "Dry erase whiteboard with markers",
            "equipment_code": "whiteboard",
            "total_quantity": 5,
            "requires_staff_setup": False,
        },
        {
            "name": "Microphone System",
            "description": "Professional microphone setup with wireless headsets",
            "equipment_code": "microphone",
            "total_quantity": 1,
            "requires_staff_setup": True,
        },
        {
            "name": "Livestream Setup",
            "description": "Equipment for streaming events online",
            "equipment_code": "livestream",
            "total_quantity": 1,
            "requires_staff_setup": True,
        },
    ]

    created_count = 0

    for eq_data in equipment_data:
        # Check if already exists
        result = await db.execute(
            select(RoomEquipment).where(
                RoomEquipment.equipment_code == eq_data["equipment_code"]
            )
        )
        if result.scalar_one_or_none():
            print(f"⊘ SKIPPED: {eq_data['name']} (already exists)")
            continue

        try:
            equipment = RoomEquipment(
                name=eq_data["name"],
                description=eq_data["description"],
                equipment_code=eq_data["equipment_code"],
                total_quantity=eq_data["total_quantity"],
                requires_staff_setup=eq_data["requires_staff_setup"],
                is_active=True,
            )
            db.add(equipment)
            await db.flush()

            print(f"✓ CREATED: {eq_data['name']}")
            print(f"  Code: {eq_data['equipment_code']}")
            print(f"  Quantity: {eq_data['total_quantity']}\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {eq_data['name']} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {eq_data['name']} - {str(e)}\n")
            continue

    return created_count


async def seed_room_reservations(db):
    """Create room reservations."""
    print("\n" + "=" * 70)
    print("SEEDING ROOM RESERVATIONS")
    print("=" * 70 + "\n")

    # Get test patrons
    result = await db.execute(
        select(User).where(User.email.in_([
            "patron.reader@l30.org",
            "patron.active@l30.org"
        ]))
    )
    patrons = result.scalars().all()

    # Get rooms
    result = await db.execute(select(Room))
    rooms = result.scalars().all()

    if not patrons or not rooms:
        print("⚠️  Not enough patrons or rooms found\n")
        return 0

    created_count = 0
    now = datetime.now(timezone.utc)

    # Create reservations
    reservations_data = [
        {
            "patron_idx": 0,
            "room_idx": 0,
            "start_offset_hours": 24,
            "duration_hours": 1,
            "purpose": "Individual study session",
            "attendee_count": 1,
            "status": ReservationStatus.confirmed,
        },
        {
            "patron_idx": 1,
            "room_idx": 2,
            "start_offset_hours": 48,
            "duration_hours": 2,
            "purpose": "Group project work",
            "attendee_count": 3,
            "status": ReservationStatus.confirmed,
        },
        {
            "patron_idx": 0,
            "room_idx": 1,
            "start_offset_hours": 72,
            "duration_hours": 1.5,
            "purpose": "Test prep study",
            "attendee_count": 1,
            "status": ReservationStatus.pending,
        },
        {
            "patron_idx": 1,
            "room_idx": 3,
            "start_offset_hours": 96,
            "duration_hours": 3,
            "purpose": "Community organization meeting",
            "attendee_count": 15,
            "status": ReservationStatus.pending,
            "equipment": ["projector", "video_conf"],
        },
    ]

    for res_data in reservations_data:
        patron = patrons[res_data["patron_idx"]]
        room = rooms[res_data["room_idx"]]

        try:
            # Calculate times
            start_time = now + timedelta(hours=res_data["start_offset_hours"])
            end_time = start_time + timedelta(hours=res_data["duration_hours"])

            # Check if already exists
            result = await db.execute(
                select(RoomReservation).where(
                    (RoomReservation.room_id == room.id) &
                    (RoomReservation.start_time == start_time) &
                    (RoomReservation.patron_id == patron.id)
                )
            )
            if result.scalar_one_or_none():
                print(f"⊘ SKIPPED: {room.name} ({patron.full_name})")
                continue

            reservation = RoomReservation(
                room_id=room.id,
                patron_id=patron.id,
                start_time=start_time,
                end_time=end_time,
                status=res_data["status"],
                purpose=res_data["purpose"],
                attendee_count=res_data["attendee_count"],
                contact_name=patron.full_name,
                contact_email=patron.email,
            )

            # Add equipment if specified
            if "equipment" in res_data:
                reservation.equipment_requested = res_data["equipment"]

            # If status is confirmed, approve it
            if res_data["status"] == ReservationStatus.confirmed:
                reservation.approved_at = now - timedelta(hours=1)

            db.add(reservation)
            await db.flush()

            print(f"✓ CREATED: {room.name}")
            print(f"  Patron: {patron.full_name}")
            print(f"  Time: {start_time.strftime('%Y-%m-%d %H:%M')} ({res_data['duration_hours']} hours)")
            print(f"  Status: {res_data['status'].value}\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {room.name} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {room.name} - {str(e)}\n")
            continue

    return created_count


async def seed_room_usage_stats(db):
    """Create room usage statistics."""
    print("\n" + "=" * 70)
    print("SEEDING ROOM USAGE STATISTICS")
    print("=" * 70 + "\n")

    # Get rooms
    result = await db.execute(select(Room))
    rooms = result.scalars().all()

    if not rooms:
        print("⚠️  No rooms found\n")
        return 0

    created_count = 0
    now = datetime.now(timezone.utc)

    for room in rooms:
        try:
            # Create stats for today
            stats = RoomUsageStats(
                room_id=room.id,
                date=now,
                total_reservations=3,
                completed_reservations=2,
                cancelled_reservations=0,
                no_show_count=0,
                total_hours_booked=360,  # 6 hours in minutes
                total_attendees=12,
                hourly_usage={
                    "9": 1,
                    "10": 2,
                    "14": 1,
                    "15": 1,
                }
            )
            db.add(stats)
            await db.flush()

            print(f"✓ CREATED: Usage stats for {room.name}\n")
            created_count += 1

        except IntegrityError:
            await db.rollback()
            print(f"⚠️  Stats already exist for {room.name}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {room.name} - {str(e)}\n")
            continue

    return created_count


async def main():
    """Main entry point."""
    async with AsyncSessionLocal() as db:
        try:
            print("\n" + "=" * 70)
            print("LIBRARY ROOM RESERVATIONS SEEDING")
            print("=" * 70)

            rooms_count = await seed_rooms(db)
            await db.commit()

            eq_count = await seed_room_equipment(db)
            await db.commit()

            res_count = await seed_room_reservations(db)
            await db.commit()

            stats_count = await seed_room_usage_stats(db)
            await db.commit()

            # Summary
            print("=" * 70)
            print("SEED COMPLETE")
            print("=" * 70)
            print(f"✓ Rooms: {rooms_count}")
            print(f"✓ Equipment Types: {eq_count}")
            print(f"✓ Reservations: {res_count}")
            print(f"✓ Usage Statistics: {stats_count}")
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
