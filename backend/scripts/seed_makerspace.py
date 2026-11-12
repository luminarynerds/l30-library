#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
"""
Seed script for makerspace equipment and reservations.

Creates:
- Makerspace certification types
- Makerspace resources (3D printers, laser cutters, etc.)
- Patron certifications (active)
- Patron certifications (pending/in-training)
- Equipment maintenance logs
- Equipment reservations
"""
import asyncio
import sys
from datetime import datetime, timedelta, timezone, date
from decimal import Decimal
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import AsyncSessionLocal
from app.models.user import User, UserRole
from app.models.makerspace import (
    MakerspaceCertificationType, MakerspaceResource, ResourceType, ResourceStatus,
    MakerspaceCertification, CertificationStatus,
    MakerspaceReservation, ReservationStatus,
    MakerspaceEquipmentMaintenance, MaintenanceType, MaintenanceStatus
)


async def seed_certification_types(db):
    """Create makerspace certification types."""
    print("\n" + "=" * 70)
    print("SEEDING MAKERSPACE CERTIFICATION TYPES")
    print("=" * 70 + "\n")

    certifications = [
        {
            "name": "3D Printer Basic",
            "description": "Certification for using 3D printers - covers safety, file preparation, and operation",
            "training_duration_hours": Decimal("2.00"),
            "requires_safety_quiz": True,
            "validity_months": 12,
        },
        {
            "name": "Laser Cutter",
            "description": "Certification for laser cutting and engraving equipment",
            "training_duration_hours": Decimal("2.00"),
            "requires_safety_quiz": True,
            "validity_months": 12,
        },
        {
            "name": "CNC Router",
            "description": "Certification for CNC routing and wood working equipment",
            "training_duration_hours": Decimal("3.00"),
            "requires_safety_quiz": True,
            "validity_months": 12,
        },
        {
            "name": "Soldering Station",
            "description": "Certification for electronics soldering and assembly",
            "training_duration_hours": Decimal("1.50"),
            "requires_safety_quiz": True,
            "validity_months": 24,
        },
    ]

    created_count = 0

    for cert_data in certifications:
        # Check if already exists
        result = await db.execute(
            select(MakerspaceCertificationType).where(
                MakerspaceCertificationType.name == cert_data["name"]
            )
        )
        if result.scalar_one_or_none():
            print(f"⊘ SKIPPED: {cert_data['name']} (already exists)")
            continue

        try:
            cert_type = MakerspaceCertificationType(
                name=cert_data["name"],
                description=cert_data["description"],
                training_duration_hours=cert_data["training_duration_hours"],
                requires_safety_quiz=cert_data["requires_safety_quiz"],
                passing_score=80,
                validity_months=cert_data["validity_months"],
                renewal_training_hours=Decimal("0.50"),
                certification_fee=Decimal("0.00"),
                renewal_fee=Decimal("0.00"),
                is_active=True,
            )
            db.add(cert_type)
            await db.flush()

            print(f"✓ CREATED: {cert_data['name']}")
            print(f"  ID: {cert_type.id}")
            print(f"  Duration: {cert_data['training_duration_hours']} hours\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {cert_data['name']} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {cert_data['name']} - {str(e)}\n")
            continue

    return created_count


async def seed_resources(db):
    """Create makerspace resources/equipment."""
    print("\n" + "=" * 70)
    print("SEEDING MAKERSPACE RESOURCES")
    print("=" * 70 + "\n")

    # Get 3D printer certification type
    result = await db.execute(
        select(MakerspaceCertificationType).where(
            MakerspaceCertificationType.name == "3D Printer Basic"
        )
    )
    printer_cert = result.scalar_one_or_none()

    # Get laser cutter certification type
    result = await db.execute(
        select(MakerspaceCertificationType).where(
            MakerspaceCertificationType.name == "Laser Cutter"
        )
    )
    laser_cert = result.scalar_one_or_none()

    resources = [
        {
            "name": "Prusa i3 MK3S+ (Red)",
            "resource_type": ResourceType.printer_3d,
            "location": "Makerspace Bay 1",
            "asset_tag": "3DP-001",
            "manufacturer": "Prusa Research",
            "model": "i3 MK3S+",
            "hourly_cost": Decimal("5.00"),
            "setup_fee": Decimal("0.00"),
            "requires_certification": True,
            "certification_type_id": printer_cert.id if printer_cert else None,
            "build_volume_x": 250,
            "build_volume_y": 210,
            "build_volume_z": 210,
            "supported_materials": '["PLA", "PETG", "ABS"]',
            "supported_file_formats": '[".stl", ".obj", ".gcode"]',
            "max_reservation_hours": 4,
            "min_reservation_hours": 1,
        },
        {
            "name": "Prusa i3 MK3S+ (Blue)",
            "resource_type": ResourceType.printer_3d,
            "location": "Makerspace Bay 1",
            "asset_tag": "3DP-002",
            "manufacturer": "Prusa Research",
            "model": "i3 MK3S+",
            "hourly_cost": Decimal("5.00"),
            "setup_fee": Decimal("0.00"),
            "requires_certification": True,
            "certification_type_id": printer_cert.id if printer_cert else None,
            "build_volume_x": 250,
            "build_volume_y": 210,
            "build_volume_z": 210,
            "supported_materials": '["PLA", "PETG", "ABS"]',
            "supported_file_formats": '[".stl", ".obj", ".gcode"]',
            "max_reservation_hours": 4,
            "min_reservation_hours": 1,
        },
        {
            "name": "xTool M1 Laser Cutter",
            "resource_type": ResourceType.laser_cutter,
            "location": "Makerspace Bay 2",
            "asset_tag": "LASER-001",
            "manufacturer": "xTool",
            "model": "M1",
            "hourly_cost": Decimal("15.00"),
            "setup_fee": Decimal("5.00"),
            "requires_certification": True,
            "certification_type_id": laser_cert.id if laser_cert else None,
            "max_reservation_hours": 3,
            "min_reservation_hours": 1,
        },
        {
            "name": "Sewing Machine Station 1",
            "resource_type": ResourceType.sewing_machine,
            "location": "Makerspace Bay 3",
            "asset_tag": "SEWING-001",
            "manufacturer": "Bernina",
            "model": "B380",
            "hourly_cost": Decimal("2.00"),
            "setup_fee": Decimal("0.00"),
            "requires_certification": False,
            "max_reservation_hours": 6,
            "min_reservation_hours": 1,
        },
        {
            "name": "Soldering Station",
            "resource_type": ResourceType.soldering_station,
            "location": "Electronics Workbench",
            "asset_tag": "SOLDER-001",
            "manufacturer": "Weller",
            "model": "WSD81",
            "hourly_cost": Decimal("1.00"),
            "setup_fee": Decimal("0.00"),
            "requires_certification": True,
            "certification_type_id": None,  # Will be updated if cert type exists
            "max_reservation_hours": 4,
            "min_reservation_hours": 1,
        },
    ]

    created_count = 0

    for res_data in resources:
        # Check if already exists
        result = await db.execute(
            select(MakerspaceResource).where(
                MakerspaceResource.asset_tag == res_data["asset_tag"]
            )
        )
        if result.scalar_one_or_none():
            print(f"⊘ SKIPPED: {res_data['name']} (already exists)")
            continue

        try:
            resource = MakerspaceResource(
                name=res_data["name"],
                resource_type=res_data["resource_type"],
                location=res_data["location"],
                asset_tag=res_data["asset_tag"],
                manufacturer=res_data["manufacturer"],
                model=res_data["model"],
                status=ResourceStatus.available,
                hourly_cost=res_data["hourly_cost"],
                setup_fee=res_data["setup_fee"],
                requires_certification=res_data["requires_certification"],
                certification_type_id=res_data["certification_type_id"],
                max_reservation_hours=res_data["max_reservation_hours"],
                min_reservation_hours=res_data["min_reservation_hours"],
                available_from="09:00",
                available_until="21:00",
                available_days=[0, 1, 2, 3, 4, 5, 6],  # All days
                advance_booking_days=14,
                maintenance_interval_days=30,
                is_active=True,
            )

            # Set optional fields
            if "build_volume_x" in res_data:
                resource.build_volume_x = res_data["build_volume_x"]
                resource.build_volume_y = res_data["build_volume_y"]
                resource.build_volume_z = res_data["build_volume_z"]

            if "supported_materials" in res_data:
                resource.supported_materials = res_data["supported_materials"]
                resource.supported_file_formats = res_data["supported_file_formats"]

            db.add(resource)
            await db.flush()

            print(f"✓ CREATED: {res_data['name']}")
            print(f"  Type: {res_data['resource_type'].value}")
            print(f"  Asset Tag: {res_data['asset_tag']}")
            print(f"  Hourly Cost: ${res_data['hourly_cost']}\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {res_data['name']} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {res_data['name']} - {str(e)}\n")
            continue

    return created_count


async def seed_patron_certifications(db):
    """Create patron certifications."""
    print("\n" + "=" * 70)
    print("SEEDING PATRON CERTIFICATIONS")
    print("=" * 70 + "\n")

    # Get test patrons
    result = await db.execute(
        select(User).where(User.email.in_([
            "patron.reader@l30.org",
            "patron.active@l30.org"
        ]))
    )
    patrons = result.scalars().all()

    # Get certification types
    result = await db.execute(select(MakerspaceCertificationType))
    cert_types = result.scalars().all()

    if not patrons or not cert_types:
        print("⚠️  Not enough patrons or certification types found\n")
        return 0

    created_count = 0

    # Certify first patron for 3D printer
    cert_type = cert_types[0] if cert_types else None
    patron = patrons[0]

    if cert_type and patron:
        try:
            # Check if already exists
            result = await db.execute(
                select(MakerspaceCertification).where(
                    (MakerspaceCertification.user_id == patron.id) &
                    (MakerspaceCertification.certification_type_id == cert_type.id)
                )
            )
            if result.scalar_one_or_none():
                print(f"⊘ SKIPPED: {patron.full_name} - {cert_type.name}")
            else:
                cert = MakerspaceCertification(
                    user_id=patron.id,
                    certification_type_id=cert_type.id,
                    status=CertificationStatus.active,
                    training_completed_at=datetime.now(timezone.utc) - timedelta(days=30),
                    quiz_score=95,
                    quiz_attempts=1,
                    certified_at=datetime.now(timezone.utc) - timedelta(days=30),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=335),
                )
                db.add(cert)
                await db.flush()

                print(f"✓ CREATED: {patron.full_name}")
                print(f"  Certification: {cert_type.name}")
                print(f"  Status: {CertificationStatus.active.value}")
                print(f"  Expires: {(datetime.now(timezone.utc) + timedelta(days=335)).date()}\n")

                created_count += 1

        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {patron.full_name} - {str(e)}\n")

    # Certify second patron for laser cutter if available
    if len(cert_types) > 1 and len(patrons) > 1:
        cert_type = cert_types[1]
        patron = patrons[1]

        try:
            result = await db.execute(
                select(MakerspaceCertification).where(
                    (MakerspaceCertification.user_id == patron.id) &
                    (MakerspaceCertification.certification_type_id == cert_type.id)
                )
            )
            if result.scalar_one_or_none():
                print(f"⊘ SKIPPED: {patron.full_name} - {cert_type.name}")
            else:
                cert = MakerspaceCertification(
                    user_id=patron.id,
                    certification_type_id=cert_type.id,
                    status=CertificationStatus.active,
                    training_completed_at=datetime.now(timezone.utc) - timedelta(days=15),
                    quiz_score=88,
                    quiz_attempts=1,
                    certified_at=datetime.now(timezone.utc) - timedelta(days=15),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=350),
                )
                db.add(cert)
                await db.flush()

                print(f"✓ CREATED: {patron.full_name}")
                print(f"  Certification: {cert_type.name}")
                print(f"  Status: {CertificationStatus.active.value}")
                print(f"  Expires: {(datetime.now(timezone.utc) + timedelta(days=350)).date()}\n")

                created_count += 1

        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {patron.full_name} - {str(e)}\n")

    return created_count


async def seed_pending_certifications(db):
    """Create pending patron certifications (in-training)."""
    print("\n" + "=" * 70)
    print("SEEDING PENDING PATRON CERTIFICATIONS")
    print("=" * 70 + "\n")

    # Try to find additional test users or create pending certifications for existing patrons
    result = await db.execute(
        select(User).where(User.email.in_([
            "patron.reader@l30.org",
            "patron.active@l30.org"
        ]))
    )
    patrons = result.scalars().all()

    # Get certification types
    result = await db.execute(select(MakerspaceCertificationType))
    cert_types = result.scalars().all()

    if not patrons or not cert_types:
        print("⚠️  Not enough patrons or certification types found\n")
        return 0

    created_count = 0

    # Create pending certification for first patron for CNC Router
    if len(cert_types) > 2:
        cert_type = cert_types[2]  # CNC Router
        patron = patrons[0]

        try:
            # Check if already exists
            result = await db.execute(
                select(MakerspaceCertification).where(
                    (MakerspaceCertification.user_id == patron.id) &
                    (MakerspaceCertification.certification_type_id == cert_type.id)
                )
            )
            if result.scalar_one_or_none():
                print(f"⊘ SKIPPED: {patron.full_name} - {cert_type.name} (pending)")
            else:
                cert = MakerspaceCertification(
                    user_id=patron.id,
                    certification_type_id=cert_type.id,
                    status=CertificationStatus.pending,
                    training_completed_at=None,  # Not completed yet
                    quiz_score=None,
                    quiz_attempts=0,
                    certified_at=None,
                    expires_at=None,
                )
                db.add(cert)
                await db.flush()

                print(f"✓ CREATED: {patron.full_name}")
                print(f"  Certification: {cert_type.name} (PENDING)")
                print(f"  Status: {CertificationStatus.pending.value}")
                print(f"  Training Required: {cert_type.training_duration_hours} hours\n")

                created_count += 1

        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {patron.full_name} - {str(e)}\n")

    # Create pending certification for second patron for Soldering Station if available
    if len(cert_types) > 3 and len(patrons) > 1:
        cert_type = cert_types[3]  # Soldering Station
        patron = patrons[1]

        try:
            result = await db.execute(
                select(MakerspaceCertification).where(
                    (MakerspaceCertification.user_id == patron.id) &
                    (MakerspaceCertification.certification_type_id == cert_type.id)
                )
            )
            if result.scalar_one_or_none():
                print(f"⊘ SKIPPED: {patron.full_name} - {cert_type.name} (pending)")
            else:
                cert = MakerspaceCertification(
                    user_id=patron.id,
                    certification_type_id=cert_type.id,
                    status=CertificationStatus.pending,
                    training_completed_at=None,
                    quiz_score=None,
                    quiz_attempts=0,
                    certified_at=None,
                    expires_at=None,
                )
                db.add(cert)
                await db.flush()

                print(f"✓ CREATED: {patron.full_name}")
                print(f"  Certification: {cert_type.name} (PENDING)")
                print(f"  Status: {CertificationStatus.pending.value}")
                print(f"  Training Required: {cert_type.training_duration_hours} hours\n")

                created_count += 1

        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {patron.full_name} - {str(e)}\n")

    return created_count


async def seed_maintenance_logs(db):
    """Create maintenance logs for makerspace equipment."""
    print("\n" + "=" * 70)
    print("SEEDING MAINTENANCE LOGS")
    print("=" * 70 + "\n")

    # Get all resources
    result = await db.execute(select(MakerspaceResource))
    resources = result.scalars().all()

    if not resources:
        print("⚠️  No resources found\n")
        return 0

    created_count = 0
    now = datetime.now(timezone.utc)

    # Create maintenance logs for equipment
    maintenance_records = [
        {
            "resource_idx": 0,  # First 3D printer
            "maintenance_type": MaintenanceType.preventive,
            "title": "Monthly preventive maintenance",
            "description": "Routine cleaning and calibration of nozzle and bed",
            "scheduled_offset_days": -15,  # 15 days ago
            "status": MaintenanceStatus.completed,
        },
        {
            "resource_idx": 1,  # Second 3D printer
            "maintenance_type": MaintenanceType.cleaning,
            "title": "Deep cleaning session",
            "description": "Full disassembly and cleaning of build platform and enclosure",
            "scheduled_offset_days": -30,  # 30 days ago
            "status": MaintenanceStatus.completed,
        },
        {
            "resource_idx": 2,  # Laser cutter
            "maintenance_type": MaintenanceType.preventive,
            "title": "Laser alignment check",
            "description": "Verify laser alignment and mirror condition",
            "scheduled_offset_days": 7,  # 7 days from now
            "status": MaintenanceStatus.scheduled,
        },
        {
            "resource_idx": 3,  # Sewing machine
            "maintenance_type": MaintenanceType.cleaning,
            "title": "Bobbin area cleaning",
            "description": "Clean bobbin case and thread path to prevent jams",
            "scheduled_offset_days": -7,  # 7 days ago
            "status": MaintenanceStatus.completed,
        },
        {
            "resource_idx": 4,  # Soldering station
            "maintenance_type": MaintenanceType.calibration,
            "title": "Temperature calibration",
            "description": "Calibrate soldering iron temperature sensor and controls",
            "scheduled_offset_days": 3,  # 3 days from now
            "status": MaintenanceStatus.scheduled,
        },
    ]

    for maint_data in maintenance_records:
        resource_idx = maint_data["resource_idx"]
        if resource_idx >= len(resources):
            print(f"  ⚠️  Resource index {resource_idx} out of range ({len(resources)} resources), skipping")
            continue

        resource = resources[resource_idx]

        try:
            scheduled_date = (now + timedelta(days=maint_data["scheduled_offset_days"])).date()

            # Check if already exists
            result = await db.execute(
                select(MakerspaceEquipmentMaintenance).where(
                    (MakerspaceEquipmentMaintenance.resource_id == resource.id) &
                    (MakerspaceEquipmentMaintenance.scheduled_date == scheduled_date) &
                    (MakerspaceEquipmentMaintenance.status == maint_data["status"])
                )
            )
            if result.scalar_one_or_none():
                print(f"⊘ SKIPPED: {resource.name} - {maint_data['title']}")
                continue

            maintenance = MakerspaceEquipmentMaintenance(
                resource_id=resource.id,
                maintenance_type=maint_data["maintenance_type"],
                status=maint_data["status"],
                scheduled_date=scheduled_date,
                title=maint_data["title"],
                description=maint_data["description"],
            )
            db.add(maintenance)
            await db.flush()

            print(f"✓ CREATED: {resource.name}")
            print(f"  Type: {maint_data['maintenance_type'].value}")
            print(f"  Scheduled: {scheduled_date}")
            print(f"  Status: {maint_data['status'].value}\n")

            created_count += 1

        except IntegrityError as e:
            await db.rollback()
            print(f"✗ ERROR: {resource.name} - {str(e)}\n")
            continue
        except Exception as e:
            await db.rollback()
            print(f"✗ ERROR: {resource.name} - {str(e)}\n")
            continue

    return created_count


async def seed_reservations(db):
    """Create makerspace reservations."""
    print("\n" + "=" * 70)
    print("SEEDING MAKERSPACE RESERVATIONS")
    print("=" * 70 + "\n")

    # Get test patrons
    result = await db.execute(
        select(User).where(User.email.in_([
            "patron.reader@l30.org",
            "patron.active@l30.org"
        ]))
    )
    patrons = result.scalars().all()

    # Get resources
    result = await db.execute(select(MakerspaceResource))
    resources = result.scalars().all()

    if not patrons or not resources:
        print("⚠️  Not enough patrons or resources found\n")
        return 0

    created_count = 0
    now = datetime.now(timezone.utc)

    # Create a few reservations
    reservations_data = [
        {
            "patron_idx": 0,
            "resource_idx": 0,
            "start_offset_hours": 24,  # Tomorrow at 10:00
            "duration_hours": 2,
            "status": ReservationStatus.confirmed,
        },
        {
            "patron_idx": 1,
            "resource_idx": 2,
            "start_offset_hours": 48,  # Day after tomorrow at 14:00
            "duration_hours": 2,
            "status": ReservationStatus.confirmed,
        },
        {
            "patron_idx": 0,
            "resource_idx": 1,
            "start_offset_hours": 72,  # In 3 days at 11:00
            "duration_hours": 3,
            "status": ReservationStatus.pending,
        },
    ]

    for res_data in reservations_data:
        patron_idx = res_data["patron_idx"]
        resource_idx = res_data["resource_idx"]
        if patron_idx >= len(patrons):
            print(f"  ⚠️  Patron index {patron_idx} out of range ({len(patrons)} patrons), skipping")
            continue
        if resource_idx >= len(resources):
            print(f"  ⚠️  Resource index {resource_idx} out of range ({len(resources)} resources), skipping")
            continue
        patron = patrons[patron_idx]
        resource = resources[resource_idx]

        try:
            # Calculate times
            start_time = now + timedelta(hours=res_data["start_offset_hours"])
            end_time = start_time + timedelta(hours=res_data["duration_hours"])

            # Check if reservation already exists
            result = await db.execute(
                select(MakerspaceReservation).where(
                    (MakerspaceReservation.user_id == patron.id) &
                    (MakerspaceReservation.resource_id == resource.id) &
                    (MakerspaceReservation.start_time == start_time)
                )
            )
            if result.scalar_one_or_none():
                print(f"⊘ SKIPPED: {patron.full_name} - {resource.name}")
                continue

            reservation = MakerspaceReservation(
                user_id=patron.id,
                resource_id=resource.id,
                status=res_data["status"],
                start_time=start_time,
                end_time=end_time,
            )
            db.add(reservation)
            await db.flush()

            print(f"✓ CREATED: Reservation for {patron.full_name}")
            print(f"  Resource: {resource.name}")
            print(f"  Time: {start_time.strftime('%Y-%m-%d %H:%M')} ({res_data['duration_hours']} hours)")
            print(f"  Status: {res_data['status'].value}\n")

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


async def main():
    """Main entry point."""
    async with AsyncSessionLocal() as db:
        try:
            print("\n" + "=" * 70)
            print("MAKERSPACE EQUIPMENT & RESERVATIONS SEEDING")
            print("=" * 70)

            # Check if makerspace tables exist before proceeding
            from sqlalchemy import text as sa_text
            try:
                await db.execute(sa_text("SELECT 1 FROM makerspace_certification_types LIMIT 0"))
            except Exception:
                await db.rollback()
                print("  ⏭️  Makerspace tables not yet created, skipping")
                return 0

            cert_count = await seed_certification_types(db)
            await db.commit()

            res_count = await seed_resources(db)
            await db.commit()

            patron_cert_count = await seed_patron_certifications(db)
            await db.commit()

            pending_cert_count = await seed_pending_certifications(db)
            await db.commit()

            maintenance_count = await seed_maintenance_logs(db)
            await db.commit()

            reservation_count = await seed_reservations(db)
            await db.commit()

            # Summary
            print("=" * 70)
            print("SEED COMPLETE")
            print("=" * 70)
            print(f"✓ Certification Types: {cert_count}")
            print(f"✓ Resources: {res_count}")
            print(f"✓ Patron Certifications (Active): {patron_cert_count}")
            print(f"✓ Patron Certifications (Pending): {pending_cert_count}")
            print(f"✓ Maintenance Logs: {maintenance_count}")
            print(f"✓ Reservations: {reservation_count}")
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
