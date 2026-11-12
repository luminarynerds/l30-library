# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import asyncio
import random
import uuid
from datetime import datetime, timedelta, timezone, time
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.models.computer import (
    Computer, ComputerReservation, ComputerWaitlist,
    ComputerUsageStats, ComputerSystemLog,
    GuestPass, SessionExtensionRequest,
    ComputerType, ComputerStatus, ComputerReservationStatus,
    ComputerWaitlistStatus, ExtensionStatus
)
from app.models.cipa_compliance import (
    ComputerSession, InternetPolicyAcceptance,
    ComputerSessionStatus, PolicyType
)

utc = timezone.utc


def past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(
        days=days_ago, hours=random.randint(0, 23), minutes=random.randint(0, 59)
    )


def future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


async def seed_computers():
    async with AsyncSessionLocal() as session:
        print("\n=== Seeding Computer Lab and Digital Services Data ===\n")

        # Fetch patron IDs
        users_result = await session.execute(
            text("SELECT id FROM users WHERE role IN ('patron', 'child')")
        )
        patron_ids = [row[0] for row in users_result.fetchall()]

        # Fetch staff IDs
        staff_result = await session.execute(
            text("SELECT id FROM users WHERE role IN ('staff', 'admin', 'director', 'super_admin')")
        )
        staff_ids = [row[0] for row in staff_result.fetchall()]

        # Fetch branches
        branches_result = await session.execute(text("SELECT id FROM branches"))
        branch_ids = [row[0] for row in branches_result.fetchall()]

        if not patron_ids or not staff_ids or not branch_ids:
            print("ERROR: Missing required data (patrons, staff, or branches). Aborting.")
            return False

        print(f"Found {len(patron_ids)} patrons, {len(staff_ids)} staff, {len(branch_ids)} branches\n")

        # ========== COMPUTERS ==========
        print("Creating public computers...")
        computers_to_create = [
            # Adult area (8 desktops)
            {
                "name": "PC-A01", "number": "A01", "type": ComputerType.adult,
                "location": "Adult Services - Main Floor, North Wall",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "pdf_reader"],
                "specs": "Desktop, Ethernet, Printing enabled"
            },
            {
                "name": "PC-A02", "number": "A02", "type": ComputerType.adult,
                "location": "Adult Services - Main Floor, North Wall",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "pdf_reader"],
                "specs": "Desktop, Ethernet, Printing enabled"
            },
            {
                "name": "PC-A03", "number": "A03", "type": ComputerType.adult,
                "location": "Adult Services - Main Floor, South Wall",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "pdf_reader"],
                "specs": "Desktop, Ethernet, Printing enabled"
            },
            {
                "name": "PC-A04", "number": "A04", "type": ComputerType.adult,
                "location": "Adult Services - Main Floor, South Wall",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "pdf_reader"],
                "specs": "Desktop, Ethernet, Printing enabled"
            },
            {
                "name": "PC-A05", "number": "A05", "type": ComputerType.adult,
                "location": "Adult Services - Study Room A",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["word", "excel", "firefox", "chrome"],
                "specs": "Desktop, WiFi, Printing enabled"
            },
            {
                "name": "PC-A06", "number": "A06", "type": ComputerType.adult,
                "location": "Adult Services - Study Room B",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["word", "excel", "firefox", "chrome"],
                "specs": "Desktop, WiFi, Printing enabled"
            },
            {
                "name": "PC-A07", "number": "A07", "type": ComputerType.adult,
                "location": "Adult Services - Main Floor, East Wall",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "pdf_reader", "autocad"],
                "specs": "Desktop, Ethernet, Printing enabled, CAD software"
            },
            {
                "name": "PC-A08", "number": "A08", "type": ComputerType.adult,
                "location": "Adult Services - Main Floor, East Wall",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "pdf_reader"],
                "specs": "Desktop, Ethernet, Printing enabled"
            },
            # Teen area (4 desktops)
            {
                "name": "PC-T01", "number": "T01", "type": ComputerType.teen,
                "location": "Teen Zone - Upper Floor",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["word", "firefox", "chrome", "youtube_restricted"],
                "specs": "Desktop, WiFi, Printing enabled, Content filtered"
            },
            {
                "name": "PC-T02", "number": "T02", "type": ComputerType.teen,
                "location": "Teen Zone - Upper Floor",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["word", "firefox", "chrome", "youtube_restricted"],
                "specs": "Desktop, WiFi, Printing enabled, Content filtered"
            },
            {
                "name": "PC-T03", "number": "T03", "type": ComputerType.teen,
                "location": "Teen Zone - Gaming Alcove",
                "os": "Windows 11", "processor": "Intel i7-11700", "ram": 16, "storage": 512,
                "software": ["firefox", "chrome", "minecraft_edu", "scratch"],
                "specs": "Desktop, Ethernet, No printing, Educational gaming"
            },
            {
                "name": "PC-T04", "number": "T04", "type": ComputerType.teen,
                "location": "Teen Zone - Upper Floor",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["word", "firefox", "chrome", "youtube_restricted"],
                "specs": "Desktop, WiFi, Printing enabled, Content filtered"
            },
            # Children's area (3 desktops)
            {
                "name": "PC-C01", "number": "C01", "type": ComputerType.kids,
                "location": "Children's Library - Activity Zone",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["firefox", "chrome", "abcmouse", "khan_academy"],
                "specs": "Desktop, WiFi, No printing, Fully filtered, Kid-friendly UI"
            },
            {
                "name": "PC-C02", "number": "C02", "type": ComputerType.kids,
                "location": "Children's Library - Activity Zone",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["firefox", "chrome", "abcmouse", "khan_academy"],
                "specs": "Desktop, WiFi, No printing, Fully filtered, Kid-friendly UI"
            },
            {
                "name": "PC-C03", "number": "C03", "type": ComputerType.kids,
                "location": "Children's Library - Reading Corner",
                "os": "Windows 11", "processor": "Intel i5-12600", "ram": 8, "storage": 256,
                "software": ["firefox", "chrome", "abcmouse", "khan_academy"],
                "specs": "Desktop, WiFi, No printing, Fully filtered, Kid-friendly UI"
            },
            # Accessible workstations (2)
            {
                "name": "PC-ACC-01", "number": "ACC-01", "type": ComputerType.accessible,
                "location": "Accessible Services - Main Floor",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 32, "storage": 1024,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "nvda", "magnifier", "jaws"],
                "specs": "Desktop, Ethernet, High RAM, Screen reader, Magnifier, Keyboard options",
                "accessibility": ["screen_reader", "magnifier", "keyboard_options", "voice_control"]
            },
            {
                "name": "PC-ACC-02", "number": "ACC-02", "type": ComputerType.accessible,
                "location": "Accessible Services - Study Room",
                "os": "Windows 11", "processor": "Intel i7-12700", "ram": 32, "storage": 1024,
                "software": ["word", "excel", "zoom", "firefox", "chrome", "nvda", "magnifier", "jaws"],
                "specs": "Desktop, Ethernet, High RAM, Screen reader, Magnifier, Keyboard options",
                "accessibility": ["screen_reader", "magnifier", "keyboard_options", "voice_control"]
            },
            # Laptops for checkout (4)
            {
                "name": "LAPTOP-01", "number": "LAP-01", "type": ComputerType.adult,
                "location": "Circulating Collection - Laptop Station",
                "os": "Windows 11", "processor": "Intel i7-1255U", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome"],
                "specs": "Laptop, WiFi, Portable, Printing via AirPrint"
            },
            {
                "name": "LAPTOP-02", "number": "LAP-02", "type": ComputerType.adult,
                "location": "Circulating Collection - Laptop Station",
                "os": "Windows 11", "processor": "Intel i7-1255U", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome"],
                "specs": "Laptop, WiFi, Portable, Printing via AirPrint"
            },
            {
                "name": "LAPTOP-03", "number": "LAP-03", "type": ComputerType.adult,
                "location": "Circulating Collection - Laptop Station",
                "os": "Windows 11", "processor": "Intel i7-1255U", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome"],
                "specs": "Laptop, WiFi, Portable, Printing via AirPrint"
            },
            {
                "name": "LAPTOP-04", "number": "LAP-04", "type": ComputerType.adult,
                "location": "Circulating Collection - Laptop Station",
                "os": "Windows 11", "processor": "Intel i7-1255U", "ram": 16, "storage": 512,
                "software": ["word", "excel", "zoom", "firefox", "chrome"],
                "specs": "Laptop, WiFi, Portable, Printing via AirPrint"
            },
        ]

        # Check existing computers
        existing = await session.execute(text("SELECT COUNT(*) FROM computers"))
        computer_count = existing.scalar()

        if computer_count == 0:
            computers = []
            for comp_data in computers_to_create:
                comp = Computer(
                    name=comp_data["name"],
                    computer_number=comp_data["number"],
                    computer_type=comp_data["type"],
                    location=comp_data["location"],
                    os_type=comp_data["os"],
                    processor=comp_data["processor"],
                    ram_gb=comp_data["ram"],
                    storage_gb=comp_data["storage"],
                    installed_software=comp_data.get("software", []),
                    status=random.choice([ComputerStatus.available, ComputerStatus.available, ComputerStatus.maintenance]),
                    is_active=True,
                    branch_id=random.choice(branch_ids),
                    has_internet=True,
                    internet_type="Ethernet" if "Ethernet" in comp_data["specs"] else "WiFi",
                    has_print_release=True if "Printing" in comp_data["specs"] else False,
                    max_session_minutes=60,
                    is_extendable=True,
                    max_extension_minutes=60,
                    max_extensions_per_day=1,
                    accessibility_features=comp_data.get("accessibility", []),
                )
                computers.append(comp)
            session.add_all(computers)
            await session.flush()
            print(f"  Created {len(computers)} computers")
        else:
            print(f"  Computers already exist ({computer_count}), skipping")
            computers_result = await session.execute(text("SELECT id FROM computers"))
            computer_ids = [row[0] for row in computers_result.fetchall()]

        # Get all computers for reservations
        if computer_count == 0:
            computer_ids = [c.id for c in computers]
        else:
            computers_result = await session.execute(text("SELECT id FROM computers"))
            computer_ids = [row[0] for row in computers_result.fetchall()]

        # ========== COMPUTER RESERVATIONS ==========
        print("Creating computer reservations...")
        existing_reservations = await session.execute(text("SELECT COUNT(*) FROM computer_reservations"))
        if existing_reservations.scalar() == 0:
            reservations = []

            # Past completed reservations (60)
            for _ in range(60):
                days_ago = random.randint(1, 90)
                hour = random.randint(9, 18)
                start = past(days_ago).replace(hour=hour, minute=0, second=0, microsecond=0)
                end = start + timedelta(hours=1)
                checked_in = start + timedelta(minutes=random.randint(0, 10))
                actual_end = checked_in + timedelta(minutes=random.randint(30, 65))

                res = ComputerReservation(
                    computer_id=random.choice(computer_ids),
                    patron_id=random.choice(patron_ids),
                    reserved_start_time=start,
                    reserved_end_time=end,
                    session_duration_minutes=60,
                    status=random.choice([
                        ComputerReservationStatus.completed,
                        ComputerReservationStatus.completed,
                        ComputerReservationStatus.no_show,
                    ]),
                    checked_in_at=checked_in if random.random() > 0.2 else None,
                    actual_start_time=checked_in if random.random() > 0.2 else None,
                    actual_end_time=actual_end if random.random() > 0.1 else None,
                    created_at=start - timedelta(days=random.randint(1, 30))
                )
                reservations.append(res)

            # Past cancelled/extended (20)
            for _ in range(20):
                days_ago = random.randint(1, 60)
                start = past(days_ago).replace(hour=random.randint(9, 18), minute=0)
                end = start + timedelta(hours=1)

                res = ComputerReservation(
                    computer_id=random.choice(computer_ids),
                    patron_id=random.choice(patron_ids),
                    reserved_start_time=start,
                    reserved_end_time=end,
                    session_duration_minutes=60,
                    status=random.choice([ComputerReservationStatus.cancelled, ComputerReservationStatus.extended]),
                    created_at=start - timedelta(days=random.randint(1, 20))
                )
                if res.status == ComputerReservationStatus.extended:
                    res.extended_until = end + timedelta(hours=1)
                    res.extensions_used = 1
                if res.status == ComputerReservationStatus.cancelled:
                    res.cancelled_at = start - timedelta(minutes=random.randint(10, 120))
                    res.cancelled_by = random.choice(staff_ids)
                    res.cancellation_reason = random.choice([
                        "Computer unavailable", "Patron request", "Schedule conflict"
                    ])
                reservations.append(res)

            # Future confirmed (20)
            for _ in range(20):
                days_ahead = random.randint(1, 30)
                start = future(days_ahead).replace(hour=random.randint(9, 18), minute=0)
                end = start + timedelta(hours=1)

                res = ComputerReservation(
                    computer_id=random.choice(computer_ids),
                    patron_id=random.choice(patron_ids),
                    reserved_start_time=start,
                    reserved_end_time=end,
                    session_duration_minutes=60,
                    status=ComputerReservationStatus.confirmed,
                    confirmation_sent_at=datetime.now(utc) - timedelta(days=random.randint(1, 10))
                )
                reservations.append(res)

            session.add_all(reservations)
            await session.flush()
            print(f"  Created {len(reservations)} reservations")

        # ========== COMPUTER SESSIONS (CIPA COMPLIANCE) ==========
        print("Creating computer sessions...")
        existing_sessions = await session.execute(text("SELECT COUNT(*) FROM computer_sessions"))
        if existing_sessions.scalar() == 0:
            sessions = []
            policy_acceptances = []

            # 200 sessions across past 90 days
            for _ in range(200):
                days_ago = random.randint(1, 90)
                hour = random.choice([10, 11, 12, 13, 14, 15, 16, 17, 18])  # Peak hours

                # Weight weekdays heavier
                is_weekday = random.random() > 0.3
                if is_weekday:
                    # 9am-6pm peak
                    session_date = past(days_ago).replace(hour=hour, minute=0, second=0)
                else:
                    # Sunday morning quiet times
                    session_date = past(days_ago).replace(hour=random.randint(9, 11), minute=0)

                patron_id = random.choice(patron_ids)
                is_minor = random.random() < 0.3

                # Create policy acceptance
                policy = InternetPolicyAcceptance(
                    patron_id=patron_id if random.random() > 0.2 else None,
                    session_id=str(uuid.uuid4()),
                    policy_type=PolicyType.COMPUTER_LAB,
                    policy_version="2.1",
                    is_minor=is_minor,
                    patron_type="child" if is_minor else "adult",
                    accepted_at=session_date - timedelta(minutes=5),
                    workstation_id=f"PC-{random.randint(1,20):03d}",
                )
                policy_acceptances.append(policy)
                await session.flush()

                # Session duration 30-75 minutes
                duration = random.randint(30, 75)
                session_end = session_date + timedelta(minutes=duration)
                actual_end = session_date + timedelta(minutes=random.randint(25, 80))

                comp_session = ComputerSession(
                    patron_id=patron_id,
                    session_token=str(uuid.uuid4()),
                    status=random.choice([ComputerSessionStatus.ENDED, ComputerSessionStatus.ENDED, ComputerSessionStatus.ACTIVE]),
                    is_minor=is_minor,
                    patron_type="child" if is_minor else "adult",
                    workstation_id=f"WS-{random.randint(1,20):03d}",
                    policy_acceptance_id=policy.id,
                    content_filtering_enabled=is_minor,
                    minor_filtering_enabled=is_minor,
                    started_at=session_date,
                    scheduled_end=session_end,
                    ended_at=actual_end if random.random() > 0.1 else None,
                    max_duration_minutes=120,
                    extension_count=0,
                )
                sessions.append(comp_session)

            session.add_all(sessions)
            await session.flush()
            print(f"  Created {len(sessions)} sessions with policy acceptances")

        # ========== USAGE STATISTICS ==========
        print("Creating daily usage statistics...")
        existing_stats = await session.execute(text("SELECT COUNT(*) FROM computer_usage_stats"))
        if existing_stats.scalar() == 0:
            stats = []

            # Daily stats for past 30 days
            for days_ago in range(1, 31):
                stat_date = past(days_ago).replace(hour=0, minute=0, second=0, microsecond=0)

                # Busier on weekdays
                is_weekday = stat_date.weekday() < 5
                multiplier = 1.4 if is_weekday else 0.7

                total_reservations = int(random.randint(15, 25) * multiplier)
                completed = int(random.randint(12, 22) * multiplier)
                cancelled = total_reservations - completed - random.randint(0, 2)
                no_shows = random.randint(0, 2)

                hourly_usage = {
                    str(hour): int(random.randint(2, 8) * multiplier)
                    for hour in range(9, 19)
                }

                comp_stat = ComputerUsageStats(
                    computer_id=random.choice(computer_ids),
                    date=stat_date,
                    total_reservations=total_reservations,
                    completed_sessions=completed,
                    cancelled_reservations=cancelled,
                    no_show_count=no_shows,
                    total_minutes_used=completed * random.randint(40, 70),
                    guest_sessions=random.randint(0, 3),
                    cardholders_sessions=completed - random.randint(0, 3),
                    extension_requests=random.randint(0, 5),
                    extension_requests_granted=random.randint(0, 4),
                    hourly_usage=hourly_usage,
                    print_jobs_count=random.randint(5, 15),
                )
                stats.append(comp_stat)

            session.add_all(stats)
            await session.flush()
            print(f"  Created {len(stats)} daily usage statistics")

        # ========== SYSTEM LOGS ==========
        print("Creating computer system logs...")
        existing_logs = await session.execute(text("SELECT COUNT(*) FROM computer_system_logs"))
        if existing_logs.scalar() == 0:
            logs = []
            event_types = [
                "reservation_created", "session_started", "session_ended",
                "auto_logout", "extension_requested", "computer_maintenance",
                "session_timeout", "patron_logout"
            ]

            # 100 logs
            for _ in range(100):
                log_date = past(random.randint(1, 90))

                log = ComputerSystemLog(
                    event_type=random.choice(event_types),
                    description=f"Computer lab event: {random.choice(event_types)}",
                    computer_id=random.choice(computer_ids) if random.random() > 0.1 else None,
                    user_id=random.choice(patron_ids + staff_ids) if random.random() > 0.2 else None,
                    severity=random.choice(["debug", "info", "warning", "error"]),
                    created_at=log_date,
                    system_metadata={
                        "event_source": "computer_lab_system",
                        "region": "main",
                    }
                )
                logs.append(log)

            session.add_all(logs)
            await session.flush()
            print(f"  Created {len(logs)} system logs")

        # ========== GUEST PASSES ==========
        print("Creating guest passes...")
        existing_passes = await session.execute(text("SELECT COUNT(*) FROM guest_passes"))
        if existing_passes.scalar() == 0:
            passes = []

            names = ["John Smith", "Maria Garcia", "Ahmed Hassan", "Lisa Wong", "Carlos Rodriguez",
                    "Priya Patel", "Michael O'Brien", "Sophie Leclerc"]

            for _ in range(15):
                guest_name = random.choice(names)
                pass_code = "GP-" + "".join(random.choices("0123456789ABCDEF", k=6))

                guest_pass = GuestPass(
                    guest_name=guest_name,
                    guest_email=f"{guest_name.lower().replace(' ', '.')}@temp.local",
                    guest_phone=f"555-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
                    pass_code=pass_code,
                    max_sessions=1,
                    max_duration_minutes_per_session=60,
                    valid_until=future(random.randint(7, 30)),
                    is_active=True if random.random() > 0.3 else False,
                    issued_by_staff_id=random.choice(staff_ids),
                    allowed_computer_types=["adult"] if random.random() > 0.5 else ["adult", "accessible"],
                )
                passes.append(guest_pass)

            session.add_all(passes)
            await session.flush()
            print(f"  Created {len(passes)} guest passes")

        # ========== WAITLIST ==========
        print("Creating computer waitlist entries...")
        existing_waitlist = await session.execute(text("SELECT COUNT(*) FROM computer_waitlist"))
        if existing_waitlist.scalar() == 0:
            waitlist_entries = []

            # 10 pending waitlist entries for busy times
            for i in range(10):
                patron_id = random.choice(patron_ids)
                desired_start = future(random.randint(1, 7)).replace(hour=random.randint(10, 16), minute=0)

                entry = ComputerWaitlist(
                    computer_id=random.choice(computer_ids),
                    patron_id=patron_id,
                    desired_start_time=desired_start,
                    desired_duration_minutes=60,
                    status=random.choice([ComputerWaitlistStatus.pending, ComputerWaitlistStatus.notified]),
                    queue_position=i + 1,
                    expires_at=desired_start + timedelta(hours=24),
                    created_at=datetime.now(utc),
                )
                if entry.status == ComputerWaitlistStatus.notified:
                    entry.notified_at = datetime.now(utc) - timedelta(hours=1)
                    entry.notification_method = random.choice(["sms", "email"])

                waitlist_entries.append(entry)

            session.add_all(waitlist_entries)
            await session.flush()
            print(f"  Created {len(waitlist_entries)} waitlist entries")

        # Commit all changes
        await session.commit()
        print("\n=== Computer Lab Seeding Complete ===\n")
        return True


async def main():
    try:
        success = await seed_computers()
        return 0 if success else 1
    except Exception as e:  # noqa: BLE001  # CLI seed script — outer boundary reports any failure to operator
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
