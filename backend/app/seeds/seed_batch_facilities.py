# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
from datetime import datetime, timedelta, timezone, date, time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


async def seed_batch_facilities(session: AsyncSession) -> bool:

    # Grab reusable IDs
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]

    branches_r = await session.execute(text("SELECT id, name FROM branches"))
    branches = branches_r.fetchall()
    branch_ids = [b[0] for b in branches]

    rooms_r = await session.execute(text("SELECT id, name FROM rooms"))
    rooms = rooms_r.fetchall()
    room_ids = [r[0] for r in rooms]

    printers_r = await session.execute(text("SELECT id, name FROM printers"))
    printers = printers_r.fetchall()
    printer_ids = [p[0] for p in printers]

    now = datetime.now(utc)

    # ════════════════════════════════════════════════════════════════
    # 1. SECURITY SYSTEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM security_systems"))
    if r.scalar() == 0:
        print("  Seeding security_systems...")
        systems = [
            ("camera", "Main Branch Camera Network", "IP camera system covering all public and staff areas", "Main Branch", "Building-wide", "All floors",
             "https://nvr.library.local/api", True, 30),
            ("alarm", "ADT Alarm Panel - Main", "Monitored alarm system for main branch", "Main Branch", "Building-wide", "All zones",
             "https://adt-api.library.local/api", True, 60),
            ("access_control", "Keri Systems Access Control", "Electronic door access system with card readers", "Main Branch", "Building-wide", "All entries",
             "https://keri.library.local/api", True, 15),
            ("camera", "Elmdale Branch Camera System", "4-camera surveillance system", "Elmdale Branch", "Building-wide", "Floor 1",
             "https://nvr-north.library.local/api", True, 30),
            ("alarm", "SimpliSafe - Elmdale Branch", "Alarm system for Elmdale Branch", "Elmdale Branch", "Building-wide", "All zones",
             None, True, 60),
        ]
        for sys_type, name, desc, loc, zone, area, endpoint, connected, timeout in systems:
            await session.execute(text("""
                INSERT INTO security_systems (system_type, system_name, description, location, zone, area,
                    status, api_endpoint, is_connected, last_heartbeat, connection_timeout_seconds)
                VALUES (:stype, :name, :desc, :loc, :zone, :area,
                    'active', :endpoint, :connected, :heartbeat, :timeout)
            """), {
                "stype": sys_type, "name": name, "desc": desc, "loc": loc,
                "zone": zone, "area": area, "endpoint": endpoint,
                "connected": connected, "heartbeat": _past(0),
                "timeout": timeout,
            })
        print(f"    Created {len(systems)} security systems")
        await session.commit()

    # Get security_system IDs for child tables
    ss_r = await session.execute(text("SELECT id, system_type, system_name FROM security_systems"))
    sec_systems = ss_r.fetchall()
    camera_sys_ids = [s[0] for s in sec_systems if s[1] == "camera"]
    alarm_sys_ids = [s[0] for s in sec_systems if s[1] == "alarm"]
    access_sys_ids = [s[0] for s in sec_systems if s[1] == "access_control"]
    all_sec_ids = [s[0] for s in sec_systems]

    # ════════════════════════════════════════════════════════════════
    # 2. SECURITY SYSTEM LOGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM security_system_logs"))
    if r.scalar() == 0 and all_sec_ids:
        print("  Seeding security_system_logs...")
        log_entries = [
            ("heartbeat", True, None),
            ("connection_established", True, None),
            ("firmware_update", True, None),
            ("heartbeat", True, None),
            ("connection_lost", False, "Network timeout after 30 seconds"),
            ("connection_established", True, None),
            ("alert_triggered", True, None),
            ("heartbeat", True, None),
            ("system_armed", True, None),
            ("system_disarmed", True, None),
            ("heartbeat", True, None),
            ("config_changed", True, None),
            ("heartbeat", True, None),
            ("connection_lost", False, "DNS resolution failed"),
            ("connection_established", True, None),
        ]
        for evt_type, success, error_msg in log_entries:
            await session.execute(text("""
                INSERT INTO security_system_logs (security_system_id, event_type, success, error_message)
                VALUES (:ssid, :evt, :success, :error)
            """), {
                "ssid": random.choice(all_sec_ids),
                "evt": evt_type, "success": success, "error": error_msg,
            })
        print(f"    Created {len(log_entries)} security system logs")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. CAMERA SYSTEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM camera_systems"))
    if r.scalar() == 0 and camera_sys_ids:
        print("  Seeding camera_systems...")
        cameras = [
            (camera_sys_ids[0], "CAM-MAIN-01", "Main Entrance Camera", "Main entrance lobby", "180-degree wide angle",
             "rtsp://nvr.library.local/cam01", True, "/recordings/cam01/", True, 90),
            (camera_sys_ids[0], "CAM-MAIN-02", "Circulation Desk Camera", "Behind circulation desk", "Fixed overhead",
             "rtsp://nvr.library.local/cam02", True, "/recordings/cam02/", True, 90),
            (camera_sys_ids[0], "CAM-MAIN-03", "Parking Lot Camera", "Front parking lot, pole-mounted", "PTZ outdoor",
             "rtsp://nvr.library.local/cam03", True, "/recordings/cam03/", True, 30),
            (camera_sys_ids[1] if len(camera_sys_ids) > 1 else camera_sys_ids[0], "CAM-NORTH-01", "Elmdale Branch Entrance", "Front door, Elmdale Branch", "Fixed wide angle",
             "rtsp://nvr-north.library.local/cam01", True, "/recordings/north-cam01/", True, 60),
        ]
        for ssid, cam_id, cam_name, loc, angle, stream, rec_enabled, storage, auto_rec, retention in cameras:
            await session.execute(text("""
                INSERT INTO camera_systems (security_system_id, camera_id, camera_name, location, angle,
                    stream_url, recording_enabled, recording_storage, auto_record_on_alert, retention_days)
                VALUES (:ssid, :cam_id, :cam_name, :loc, :angle,
                    :stream, :rec_enabled, :storage, :auto_rec, :retention)
            """), {
                "ssid": ssid, "cam_id": cam_id, "cam_name": cam_name, "loc": loc,
                "angle": angle, "stream": stream, "rec_enabled": rec_enabled,
                "storage": storage, "auto_rec": auto_rec, "retention": retention,
            })
        print(f"    Created {len(cameras)} camera systems")
        await session.commit()

    # Get camera_systems IDs for recordings
    cs_r = await session.execute(text("SELECT id FROM camera_systems"))
    cam_sys_ids = [r[0] for r in cs_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 4. CAMERA RECORDINGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM camera_recordings"))
    if r.scalar() == 0 and cam_sys_ids:
        print("  Seeding camera_recordings...")
        count = 0
        for i in range(10):
            started = _past(random.randint(1, 60))
            duration = random.randint(30, 3600)
            ended = started + timedelta(seconds=duration)
            file_size = round(duration * 0.5, 1)  # ~0.5 MB per second
            await session.execute(text("""
                INSERT INTO camera_recordings (camera_system_id, recording_id, started_at, ended_at,
                    duration_seconds, file_path, file_size_mb, storage_location)
                VALUES (:csid, :rec_id, :started, :ended, :duration, :path, :size, :storage)
            """), {
                "csid": random.choice(cam_sys_ids),
                "rec_id": f"REC-{started.strftime('%Y%m%d')}-{i+1:04d}",
                "started": started, "ended": ended, "duration": duration,
                "path": f"/recordings/archive/{started.strftime('%Y/%m/%d')}/rec_{i+1:04d}.mp4",
                "size": file_size, "storage": "local_nas",
            })
            count += 1
        print(f"    Created {count} camera recordings")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. DOOR LOCKS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM door_locks"))
    if r.scalar() == 0 and access_sys_ids:
        print("  Seeding door_locks...")
        locks = [
            ("LOCK-MAIN-FRONT", "Main Front Entrance", "Main entrance lobby", "Front double doors", False, True, True, False, True),
            ("LOCK-MAIN-REAR", "Main Rear Entrance", "Rear staff entrance", "Staff rear door", True, True, True, True, False),
            ("LOCK-MAIN-STAFF", "Staff Office Suite", "Staff offices hallway", "Staff suite door", True, False, True, True, False),
            ("LOCK-MAIN-SERVER", "Server Room", "IT closet, 2nd floor", "Server room door", True, False, True, True, False),
            ("LOCK-MAIN-MEETING", "Meeting Room Wing", "Meeting rooms corridor", "Meeting wing door", False, True, True, False, True),
            ("LOCK-MAIN-CHILD", "Children's Area Gate", "Children's section", "Children's area entry gate", False, True, False, False, False),
            ("LOCK-MAIN-MAKER", "Makerspace Door", "Makerspace entrance", "Makerspace door", True, False, True, True, False),
            ("LOCK-MAIN-EMERG", "Emergency Exit - South", "South side emergency exit", "Emergency exit door", False, True, False, False, True),
        ]
        ssid = access_sys_ids[0]
        for lock_id, name, loc, door, locked, accessible, remote, lock_alert, unlock_alert in locks:
            await session.execute(text("""
                INSERT INTO door_locks (security_system_id, lock_id, lock_name, location, door_name,
                    is_locked, is_accessible, last_state_change, can_control_remotely,
                    lock_on_alert, unlock_on_alert)
                VALUES (:ssid, :lid, :name, :loc, :door,
                    :locked, :accessible, :changed, :remote,
                    :lock_alert, :unlock_alert)
            """), {
                "ssid": ssid, "lid": lock_id, "name": name, "loc": loc,
                "door": door, "locked": locked, "accessible": accessible,
                "changed": _past(random.randint(0, 3)), "remote": remote,
                "lock_alert": lock_alert, "unlock_alert": unlock_alert,
            })
        print(f"    Created {len(locks)} door locks")
        await session.commit()

    # Get door lock IDs
    dl_r = await session.execute(text("SELECT id FROM door_locks"))
    door_lock_ids = [r[0] for r in dl_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 6. DOOR LOCK EVENTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM door_lock_events"))
    if r.scalar() == 0 and door_lock_ids:
        print("  Seeding door_lock_events...")
        events = [
            ("unlock", "Staff arrival - morning opening", True, None),
            ("lock", "End of day closing procedure", True, None),
            ("unlock", "Scheduled meeting room access", True, None),
            ("lock", "Meeting room secured after event", True, None),
            ("unlock", "Staff badge scan", True, None),
            ("unlock", "Maintenance access request", True, None),
            ("lock", "Automatic lock after timeout", True, None),
            ("unlock", "Emergency exit test", True, None),
            ("lock", "Security patrol check", True, None),
            ("unlock", "Delivery entrance access", True, None),
            ("lock_failed", "Remote lock attempt", False, "Communication timeout with lock controller"),
            ("unlock", "Staff badge scan", True, None),
            ("lock", "Weekend closing procedure", True, None),
            ("unlock", "Morning opening - automated schedule", True, None),
            ("lock", "Automated end-of-day lock", True, None),
            ("unlock", "Staff badge scan", True, None),
            ("lock", "Manual lock by staff", True, None),
            ("unlock", "Janitorial access window", True, None),
            ("lock", "Janitorial access window closed", True, None),
            ("unlock", "Morning opening - staff arrival", True, None),
        ]
        for evt_type, reason, succeeded, error in events:
            await session.execute(text("""
                INSERT INTO door_lock_events (door_lock_id, event_type, action_reason,
                    triggered_by_id, succeeded, error_message)
                VALUES (:dlid, :evt, :reason, :uid, :succeeded, :error)
            """), {
                "dlid": random.choice(door_lock_ids),
                "evt": evt_type, "reason": reason,
                "uid": random.choice(staff_ids),
                "succeeded": succeeded, "error": error,
            })
        print(f"    Created {len(events)} door lock events")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. ALARM SYSTEM INTEGRATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM alarm_system_integrations"))
    if r.scalar() == 0 and alarm_sys_ids:
        print("  Seeding alarm_system_integrations...")
        integrations = [
            (alarm_sys_ids[0], "ADT Commercial", "ADT-78234", "4421-8837", True, 30,
             json.dumps([{"zone": "1", "name": "Front Entrance"}, {"zone": "2", "name": "Rear Entrance"}, {"zone": "3", "name": "Server Room"}])),
            (alarm_sys_ids[1] if len(alarm_sys_ids) > 1 else alarm_sys_ids[0],
             "SimpliSafe Business", "SS-991245", "NB-2024-445", False, 60,
             json.dumps([{"zone": "1", "name": "Main Door"}, {"zone": "2", "name": "Back Door"}])),
        ]
        for ssid, provider, acct_id, acct_num, auto_arm, delay, zones_json in integrations:
            await session.execute(text("""
                INSERT INTO alarm_system_integrations (security_system_id, provider_name, account_id,
                    account_number, auto_arm_on_alert, arm_delay_seconds, zones)
                VALUES (:ssid, :provider, :acct_id, :acct_num, :auto_arm, :delay,
                    cast(:zones as json))
            """), {
                "ssid": ssid, "provider": provider, "acct_id": acct_id,
                "acct_num": acct_num, "auto_arm": auto_arm, "delay": delay,
                "zones": zones_json,
            })
        print(f"    Created {len(integrations)} alarm system integrations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. EMERGENCY CONTACTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM emergency_contacts"))
    if r.scalar() == 0:
        print("  Seeding emergency_contacts...")
        contacts = [
            ("security_primary", "SecureGuard Dispatch", "555-0100", "dispatch@secureguard.example.com", "Security Dispatch", "SecureGuard Inc.", None, True, True, 1, "24/7 monitoring dispatch center"),
            ("security_backup", "SecureGuard Supervisor", "555-0101", "supervisor@secureguard.example.com", "Shift Supervisor", "SecureGuard Inc.", None, True, True, 2, "Backup contact if dispatch unavailable"),
            ("manager_oncall", "Marlene Weldon", "555-0201", "marlene.weldon@library.example.com", "Library Director", None, None, True, False, 1, "Primary after-hours contact for library emergencies"),
            ("manager_oncall", "David Okonkwo", "555-0202", "david.o@library.example.com", "Assistant Director", None, None, True, False, 2, "Secondary after-hours contact"),
            ("manager_oncall", "Susan Park", "555-0203", "susan.park@library.example.com", "Operations Manager", None, None, True, False, 3, "Weekend and holiday on-call manager"),
            ("police_nonemergency", "County Sheriff Non-Emergency", "555-0300", None, "Non-Emergency Dispatch", "County Sheriff", None, True, True, 1, "For non-urgent security concerns and reports"),
            ("police_dispatch", "911 Dispatch Center", "911", None, "Emergency Dispatch", "County 911", None, True, True, 1, "Emergency calls only"),
            ("facilities", "Johnson Building Services", "555-0400", "service@johnsonbldg.example.com", "Facilities Manager", "Johnson Building Services", None, True, False, 1, "HVAC, plumbing, electrical emergencies"),
            ("facilities", "Apex Fire Protection", "555-0401", "service@apexfire.example.com", "Fire System Technician", "Apex Fire Protection", None, True, True, 2, "Fire alarm and suppression system issues"),
            ("facilities", "City Water Department", "555-0402", "emergency@citywater.example.com", "Emergency Line", "City Utilities", None, True, True, 3, "Water main breaks, flooding"),
            ("executive", "Board Chair - Patricia Hamilton", "555-0500", "p.hamilton@boardmail.example.com", "Board Chairperson", "Library Board of Trustees", None, True, False, 1, "Notify for major incidents only"),
            ("executive", "City Manager - Robert Torres", "555-0501", "r.torres@citymanager.example.com", "City Manager", "City Administration", None, True, False, 2, "Notify for building closures and emergencies"),
            ("police_nonemergency", "Campus Security (nearby)", "555-0310", "security@college.example.com", "Patrol Dispatch", "Community College Security", None, True, True, 2, "Adjacent campus, can respond quickly for minor issues"),
            ("facilities", "PowerGrid Electric", "555-0410", "emergency@powergrid.example.com", "Emergency Electrician", "PowerGrid Electric Co.", None, True, True, 4, "Electrical emergencies, generator service"),
            ("security_backup", "Night Patrol Officer", "555-0102", None, "Night Patrol", "SecureGuard Inc.", None, True, True, 3, "On-site night patrol, arrives within 15 minutes"),
        ]
        for ctype, name, phone, email, title, org, uid, active, avail24, escalation, notes in contacts:
            await session.execute(text("""
                INSERT INTO emergency_contacts (contact_type, name, phone_number, email, title,
                    organization, user_id, is_active, available_24h, escalation_level, notes,
                    created_at, updated_at)
                VALUES (:ctype, :name, :phone, :email, :title,
                    :org, :uid, :active, :avail24, :escalation, :notes,
                    :now, :now)
            """), {
                "ctype": ctype, "name": name, "phone": phone, "email": email,
                "title": title, "org": org, "uid": uid, "active": active,
                "avail24": avail24, "escalation": escalation, "notes": notes,
                "now": now,
            })
        print(f"    Created {len(contacts)} emergency contacts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. EMERGENCY CONTACT CASCADES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM emergency_contact_cascades"))
    if r.scalar() == 0:
        print("  Seeding emergency_contact_cascades...")
        cascades = [
            ("Security Breach Cascade", "Contact chain for intrusion, break-in, or unauthorized access",
             True, json.dumps(["INTRUSION", "SECURITY_BREACH"]), False, 3,
             "ALERT: Security incident at {location}. {description}. Please respond immediately.",
             True, True, True),
            ("Building Emergency Cascade", "Contact chain for fire, flood, or structural issues",
             True, json.dumps(["FIRE", "ENVIRONMENTAL", "EQUIPMENT_FAILURE"]), True, 4,
             "EMERGENCY: Building issue at {location}. Type: {incident_type}. {description}.",
             True, True, True),
            ("After-Hours Incident Cascade", "Contact chain for any after-hours incidents",
             True, json.dumps(["ALARM", "SUSPICIOUS_ACTIVITY"]), False, 2,
             "After-hours alert at {location}: {description}. Security has been notified.",
             False, False, True),
        ]
        for name, desc, active, events_json, approval, max_levels, template, services, restoration, interim in cascades:
            await session.execute(text("""
                INSERT INTO emergency_contact_cascades (cascade_name, cascade_description, is_active,
                    auto_trigger_events, manual_approval_required, max_contact_levels, message_template,
                    include_affected_services, include_estimated_restoration, include_interim_procedures,
                    created_by_id)
                VALUES (:name, :desc, :active,
                    cast(:events as json), :approval, :max_levels, :template,
                    :services, :restoration, :interim,
                    :creator)
            """), {
                "name": name, "desc": desc, "active": active,
                "events": events_json, "approval": approval, "max_levels": max_levels,
                "template": template, "services": services, "restoration": restoration,
                "interim": interim, "creator": staff_ids[0],
            })
        print(f"    Created {len(cascades)} emergency contact cascades")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. EMERGENCY RESOURCES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM emergency_resources"))
    if r.scalar() == 0:
        print("  Seeding emergency_resources...")
        resources = [
            ("National Suicide Prevention Lifeline", "hotline", "mental_health", "988", "1-800-273-8255", "988",
             "https://988lifeline.org", "24/7, free and confidential support for people in distress.",
             "If you or someone you know is in emotional distress or suicidal crisis.", True, None,
             '{"en","es"}', 1, True),
            ("Crisis Text Line", "hotline", "mental_health", None, None, "741741",
             "https://www.crisistextline.org", "Free 24/7 text-based mental health support. Text HOME to 741741.",
             "When you prefer texting over calling for emotional support.", True, None,
             '{"en","es"}', 2, True),
            ("National Domestic Violence Hotline", "hotline", "domestic_violence", "1-800-799-7233", "1-800-799-7233", None,
             "https://www.thehotline.org", "Confidential support for victims of domestic violence.",
             "If you are experiencing domestic violence or abuse.", True, None,
             '{"en","es","zh","ko","vi"}', 3, True),
            ("SAMHSA National Helpline", "hotline", "substance_abuse", "1-800-662-4357", "1-800-662-4357", None,
             "https://www.samhsa.gov/find-help/national-helpline", "Free referral and information service for substance abuse.",
             "For individuals or families facing mental health or substance use disorders.", True, None,
             '{"en","es"}', 4, False),
            ("Local Emergency Shelter", "shelter", "homelessness", "555-0600", None, None,
             None, "County emergency shelter providing beds, meals, and case management.",
             "When someone needs immediate shelter or is experiencing homelessness.",
             False, "Intake hours: 4 PM - 8 PM daily. Walk-ins accepted.",
             '{"en","es"}', 5, False),
            ("County Mental Health Crisis Center", "crisis_center", "mental_health", "555-0610", None, None,
             "https://countymentalhealth.example.com", "Walk-in crisis stabilization center staffed by licensed counselors.",
             "When someone is experiencing a mental health crisis but not in immediate danger.",
             False, "Open Mon-Fri 8 AM - 10 PM, Sat-Sun 10 AM - 6 PM.",
             '{"en","es"}', 6, False),
            ("Legal Aid Society", "crisis_center", "legal_assistance", "555-0620", "1-800-555-0620", None,
             "https://legalaid.example.com", "Free legal assistance for qualifying low-income residents.",
             "When a patron needs legal help with housing, family, or immigration matters.",
             False, "Mon-Fri 9 AM - 5 PM. Appointments recommended.",
             '{"en","es","ar"}', 7, False),
            ("County Emergency Filing Office", "emergency_filing", "protective_orders", "555-0630", None, None,
             None, "Emergency protective order filing available through county court.",
             "When someone needs an emergency protective order after hours.",
             False, "After-hours filings through on-call judge. Call first.",
             '{"en"}', 8, False),
            ("Police Community Liaison", "police", "safety", "555-0300", None, None,
             None, "Non-emergency police community liaison for safety concerns.",
             "When a patron reports feeling unsafe or needs police assistance for a non-emergency.",
             False, "Mon-Fri 8 AM - 5 PM. After hours call non-emergency dispatch.",
             '{"en","es"}', 9, False),
            ("Childhelp National Child Abuse Hotline", "hotline", "child_abuse", "1-800-422-4453", "1-800-422-4453", None,
             "https://www.childhelp.org", "24/7 hotline for child abuse prevention and intervention.",
             "When there is suspected child abuse or neglect.", True, None,
             '{"en","es"}', 10, True),
        ]
        for name, rtype, situation, phone, toll_free, text_num, website, desc, when, is24, hours, langs, order, featured in resources:
            await session.execute(text(f"""
                INSERT INTO emergency_resources (name, resource_type, situation, phone, phone_toll_free,
                    text_number, website, description, when_to_call, is_24_7, hours_description,
                    languages_available, display_order, is_featured, is_active)
                VALUES (:name, :rtype, :situation, :phone, :toll_free,
                    :text_num, :website, :desc, :when, :is24, :hours,
                    '{langs}'::varchar[], :display_order, :featured, true)
            """), {
                "name": name, "rtype": rtype, "situation": situation, "phone": phone,
                "toll_free": toll_free, "text_num": text_num, "website": website,
                "desc": desc, "when": when, "is24": is24, "hours": hours,
                "display_order": order, "featured": featured,
            })
        print(f"    Created {len(resources)} emergency resources")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. FIRST AID KIT LOCATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM first_aid_kit_locations"))
    if r.scalar() == 0:
        print("  Seeding first_aid_kit_locations...")
        kits = [
            (branch_ids[0], "Behind main circulation desk, bottom drawer", "CIRC-100", "1", "Staff know location; accessible during all open hours", True, True, "standard", True),
            (branch_ids[0], "Staff break room, wall-mounted cabinet", "STAFF-102", "1", "Red cross cabinet on east wall", True, True, "standard", True),
            (branch_ids[0], "Children's area, behind service desk", "CHILD-110", "1", "Under counter, labeled red bag", True, True, "pediatric", True),
            (branch_ids[0], "Makerspace, next to fire extinguisher", "MAKER-120", "1", "Wall-mounted, includes burn care supplies", True, True, "industrial", True),
            (branch_ids[1], "Front desk, staff side", "NB-100", "1", "Under front counter", True, True, "standard", True),
            (branch_ids[2], "Main service area, supply closet", "SB-100", "1", "Supply closet B, top shelf", False, True, "standard", True),
        ]
        for bid, desc, room, floor, access, signage, trained, kit_type, in_service in kits:
            await session.execute(text("""
                INSERT INTO first_aid_kit_locations (branch_id, location_description, room_number, floor,
                    access_instructions, visible_signage, staff_trained, kit_type, last_checked_date, in_service)
                VALUES (:bid, :desc, :room, :floor, :access, :signage, :trained, :kit_type, :checked, :in_service)
            """), {
                "bid": bid, "desc": desc, "room": room, "floor": floor,
                "access": access, "signage": signage, "trained": trained,
                "kit_type": kit_type, "checked": _past(random.randint(7, 90)),
                "in_service": in_service,
            })
        print(f"    Created {len(kits)} first aid kit locations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. EMERGENCY LIGHTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM emergency_lights"))
    if r.scalar() == 0 and all_sec_ids:
        print("  Seeding emergency_lights...")
        lights = [
            ("EL-MAIN-01", "Main Entrance Emergency Light", "Main entrance lobby", "Zone A", False, 100, True, True),
            ("EL-MAIN-02", "Stairwell A Emergency Light", "Stairwell A, floor 1", "Zone A", False, 100, True, True),
            ("EL-MAIN-03", "Stairwell B Emergency Light", "Stairwell B, floor 1", "Zone B", False, 100, True, True),
            ("EL-MAIN-04", "Rear Exit Emergency Light", "Rear emergency exit corridor", "Zone B", False, 100, True, False),
            ("EL-MAIN-05", "Children's Area Emergency Light", "Children's section, main aisle", "Zone A", False, 100, True, False),
            ("EL-MAIN-06", "Meeting Room Corridor Light", "Meeting room hallway", "Zone C", False, 100, True, False),
            ("EL-NORTH-01", "Elmdale Branch Entrance Light", "Elmdale Branch main entrance", "Zone A", False, 100, True, True),
            ("EL-NORTH-02", "Elmdale Branch Rear Light", "Elmdale Branch rear exit", "Zone A", False, 100, True, False),
        ]
        for lid, name, loc, zone, is_on, brightness, activate, strobe in lights:
            await session.execute(text("""
                INSERT INTO emergency_lights (security_system_id, light_id, light_name, location, zone,
                    is_on, brightness_percent, activate_on_alert, strobe_enabled)
                VALUES (:ssid, :lid, :name, :loc, :zone, :is_on, :brightness, :activate, :strobe)
            """), {
                "ssid": all_sec_ids[0], "lid": lid, "name": name, "loc": loc,
                "zone": zone, "is_on": is_on, "brightness": brightness,
                "activate": activate, "strobe": strobe,
            })
        print(f"    Created {len(lights)} emergency lights")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 13. RALLY POINTS (must come before evacuation_routes)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM rally_points"))
    if r.scalar() == 0:
        print("  Seeding rally_points...")
        points = [
            (branch_ids[0], "Front Parking Lot Rally Point", "Southeast corner of front parking lot, near flagpole",
             39.9612, -82.9988, "100 Library Lane - Front Lot", 200, False,
             "Proceed to the flagpole in the SE corner of the front lot. Supervisors take headcount. Do not re-enter building.",
             True, True),
            (branch_ids[0], "Rear Field Rally Point", "Grass area behind the library, near maintenance shed",
             39.9608, -82.9985, "100 Library Lane - Rear Field", 150, False,
             "Use rear exit. Proceed to grassy area by maintenance shed. Wait for all-clear from fire department.",
             False, True),
            (branch_ids[1], "Elmdale Branch Parking Rally Point", "East end of parking lot, near bus stop",
             40.0012, -82.9900, "200 North Reading Dr - Parking Lot", 100, True,
             "Exit through nearest door. Gather at bus stop shelter in east parking lot.",
             True, True),
        ]
        for bid, name, desc, lat, lon, addr, cap, covered, instructions, primary, active in points:
            await session.execute(text("""
                INSERT INTO rally_points (branch_id, name, description, latitude, longitude, address,
                    max_capacity, covered, assembly_instructions, is_primary, is_active,
                    created_at, updated_at)
                VALUES (:bid, :name, :desc, :lat, :lon, :addr, :cap, :covered, :instructions,
                    :primary, :active, :now, :now)
            """), {
                "bid": bid, "name": name, "desc": desc, "lat": lat, "lon": lon,
                "addr": addr, "cap": cap, "covered": covered,
                "instructions": instructions, "primary": primary, "active": active,
                "now": now,
            })
        print(f"    Created {len(points)} rally points")
        await session.commit()

    # Get rally point IDs for evacuation routes
    rp_r = await session.execute(text("SELECT id FROM rally_points"))
    rally_point_ids = [r[0] for r in rp_r.fetchall()]

    # ════════════════════════════════════════════════════════════════
    # 14. EVACUATION ROUTES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM evacuation_routes"))
    if r.scalar() == 0 and rally_point_ids:
        print("  Seeding evacuation_routes...")
        routes = [
            (branch_ids[0], "Main Floor - Front Exit Route", "Primary evacuation route through main floor to front entrance",
             "Main circulation area", "Front entrance doors",
             json.dumps(["Pass through lobby", "Exit front doors", "Turn right toward parking lot"]),
             120, 150, True),
            (branch_ids[0], "Main Floor - Rear Exit Route", "Secondary evacuation route through staff corridor to rear exit",
             "Staff work area", "Rear staff entrance",
             json.dumps(["Through staff corridor", "Past break room", "Out rear staff door"]),
             90, 80, True),
            (branch_ids[0], "Second Floor - Stairwell A Route", "Second floor evacuation via Stairwell A to front lot",
             "Second floor reading area", "Front entrance via Stairwell A",
             json.dumps(["To Stairwell A", "Down to first floor", "Through lobby", "Exit front doors"]),
             180, 100, True),
            (branch_ids[1], "Elmdale Branch - Main Exit", "Primary evacuation route for Elmdale Branch",
             "Service desk area", "Main entrance doors",
             json.dumps(["Proceed to main hallway", "Exit through front doors", "Go to parking lot rally point"]),
             60, 80, True),
        ]
        for i, (bid, name, desc, start, exit_pt, waypoints_json, duration, cap, active) in enumerate(routes):
            rpid = rally_point_ids[min(i, len(rally_point_ids) - 1)]
            await session.execute(text("""
                INSERT INTO evacuation_routes (branch_id, route_name, description, starting_point, exit_point,
                    rally_point_id, waypoints, estimated_duration_seconds, capacity, is_active,
                    last_tested, created_at, updated_at)
                VALUES (:bid, :name, :desc, :start, :exit,
                    :rpid, cast(:waypoints as json), :duration, :cap, :active,
                    :tested, :now, :now)
            """), {
                "bid": bid, "name": name, "desc": desc, "start": start, "exit": exit_pt,
                "rpid": rpid, "waypoints": waypoints_json, "duration": duration,
                "cap": cap, "active": active, "tested": _past(random.randint(30, 180)),
                "now": now,
            })
        print(f"    Created {len(routes)} evacuation routes")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 15. SAFETY INSPECTIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM safety_inspections"))
    if r.scalar() == 0:
        print("  Seeding safety_inspections...")
        inspections = [
            (1, "fire_safety", "Main Branch - All floors", 180, 12, True,
             "James Fletcher", "County Fire Marshal Office", "FM-2024-1187", "555-0700",
             json.dumps({"items_checked": ["extinguishers", "sprinklers", "alarms", "exits", "signage"], "overall": "pass"}),
             True, 0, 1, False, None, False, None, False, None, "Annual fire safety inspection - all clear"),
            (1, "building_code", "Main Branch - Structure", 365, 24, True,
             "Robert Marsh", "County Building Inspector", "BI-2023-4432", "555-0701",
             json.dumps({"items_checked": ["structural", "electrical", "plumbing", "HVAC", "ADA"], "overall": "pass_with_notes"}),
             True, 0, 2, True, None, True, None, True, None, "Minor ADA signage update needed in restroom corridor"),
            (1, "emergency_preparedness", "Main Branch", 90, 6, False,
             "Internal - Stevie Leigh", "Library Staff", None, "555-0201",
             json.dumps({"drills_conducted": 2, "response_time_avg_seconds": 145, "issues_found": []}),
             True, 0, 0, False, None, False, None, False, None, "Bi-annual emergency drill evaluation"),
            (1, "equipment_safety", "Makerspace - All equipment", 60, 6, False,
             "Internal - Tom Rodriguez", "Library Staff", None, "555-0205",
             json.dumps({"equipment_checked": ["3D_printers", "laser_cutter", "sewing_machines", "hand_tools"], "issues": ["laser_cutter_filter_needs_replacement"]}),
             False, 0, 1, True, None, False, None, False, None, "Laser cutter HEPA filter at 90% capacity, ordered replacement"),
            (1, "electrical", "Main Branch - Electrical Systems", 270, 12, True,
             "Sarah Kim", "PowerGrid Electric Co.", "EL-2024-8891", "555-0410",
             json.dumps({"panels_inspected": 4, "circuits_tested": 48, "issues": []}),
             True, 0, 0, False, None, False, None, False, None, "Annual electrical inspection, all panels within code"),
            (2, "fire_safety", "Elmdale Branch - All areas", 150, 12, True,
             "James Fletcher", "County Fire Marshal Office", "FM-2024-1188", "555-0700",
             json.dumps({"items_checked": ["extinguishers", "alarms", "exits"], "overall": "pass"}),
             True, 0, 0, False, None, False, None, False, None, "All clear at Elmdale Branch"),
            (3, "accessibility", "Jamie Chick Community Annex - Public areas", 200, 24, True,
             "Dana Williams", "ADA Compliance Consultants", "ADA-2024-0092", "555-0750",
             json.dumps({"areas_checked": ["entrance", "restrooms", "service_desk", "shelving", "parking"], "issues": ["shelf_height_adjustment_needed"]}),
             True, 0, 1, True, None, True, None, True, None, "Two shelving units need lowering for wheelchair access"),
            (4, "plumbing", "Bookmobile", 120, 12, True,
             "Mike Brennan", "City Plumbing Services", "PL-2024-3310", "555-0760",
             json.dumps({"items_checked": ["pipes", "fixtures", "water_heater", "drainage"], "overall": "pass"}),
             True, 0, 0, False, None, False, None, False, None, "Routine plumbing inspection, no issues found"),
        ]
        for org_id, itype, loc, days_ago, freq, regulatory, inspector, company, lic, contact, findings_json, passed, critical, non_critical, remediation_req, rem_deadline, rem_complete, rem_date, rem_verified, photos_json, notes in inspections:
            last_date = _past_date(days_ago)
            next_due = last_date + timedelta(days=freq * 30)
            await session.execute(text("""
                INSERT INTO safety_inspections (organization_id, inspection_type, location, last_inspection_date,
                    next_inspection_due, frequency_months, regulatory_requirement, inspector_name, inspector_company,
                    inspector_license, inspector_contact, findings, passed, critical_issues, non_critical_issues,
                    remediation_required, remediation_completed, remediation_verified, notes)
                VALUES (:org_id, :itype, :loc, :last_date, :next_due, :freq, :regulatory,
                    :inspector, :company, :license, :contact, cast(:findings as jsonb),
                    :passed, :critical, :non_critical, :rem_req, :rem_complete, :rem_verified, :notes)
            """), {
                "org_id": org_id, "itype": itype, "loc": loc, "last_date": last_date,
                "next_due": next_due, "freq": freq, "regulatory": regulatory,
                "inspector": inspector, "company": company, "license": lic,
                "contact": contact, "findings": json.dumps(json.loads(findings_json)),
                "passed": passed, "critical": critical, "non_critical": non_critical,
                "rem_req": remediation_req, "rem_complete": rem_complete,
                "rem_verified": rem_verified, "notes": notes,
            })
        print(f"    Created {len(inspections)} safety inspections")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 16. HVAC CONTROLS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM hvac_controls"))
    if r.scalar() == 0 and all_sec_ids:
        print("  Seeding hvac_controls...")
        hvac_units = [
            ("HVAC-MAIN-01", "Main Branch HVAC - Zone A",
             json.dumps([{"zone": "A", "area": "Main floor east", "current_temp_c": 21.5, "target_temp_c": 22.0}]),
             True, 0.8, True, 15.0, True),
            ("HVAC-MAIN-02", "Main Branch HVAC - Zone B",
             json.dumps([{"zone": "B", "area": "Main floor west", "current_temp_c": 22.0, "target_temp_c": 22.0}]),
             True, 0.8, True, 15.0, True),
            ("HVAC-MAIN-03", "Main Branch HVAC - Zone C",
             json.dumps([{"zone": "C", "area": "Second floor", "current_temp_c": 21.0, "target_temp_c": 21.5}]),
             True, 0.8, False, None, True),
            ("HVAC-NORTH-01", "Elmdale Branch HVAC",
             json.dumps([{"zone": "Main", "area": "Entire building", "current_temp_c": 22.5, "target_temp_c": 22.0}]),
             True, 1.0, True, 15.0, False),
        ]
        for i, (sys_id, name, zones_json, smoke_extract, threshold, temp_override, temp_c, close_dampers) in enumerate(hvac_units):
            await session.execute(text("""
                INSERT INTO hvac_controls (security_system_id, system_id, system_name, zones,
                    activate_smoke_extraction_on_alert, smoke_detection_threshold,
                    emergency_temperature_override, emergency_temperature_celsius,
                    close_intake_dampers_on_alert)
                VALUES (:ssid, :sys_id, :name, cast(:zones as json),
                    :smoke, :threshold, :temp_override, :temp_c, :dampers)
            """), {
                "ssid": all_sec_ids[i % len(all_sec_ids)], "sys_id": sys_id, "name": name,
                "zones": zones_json, "smoke": smoke_extract,
                "threshold": threshold, "temp_override": temp_override,
                "temp_c": temp_c, "dampers": close_dampers,
            })
        print(f"    Created {len(hvac_units)} HVAC controls")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 17. PA SYSTEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM pa_systems"))
    if r.scalar() == 0 and all_sec_ids:
        print("  Seeding pa_systems...")
        pa = [
            ("PA-MAIN-01", "Main Branch PA System",
             json.dumps([{"zone": "all_floors", "speakers": 12}, {"zone": "exterior", "speakers": 2}]),
             json.dumps({"fire_alarm": "Attention: Fire alarm has been activated. Please evacuate immediately using the nearest exit.", "lockdown": "Attention: The building is now in lockdown. Remain in your current location.", "all_clear": "All clear. Normal operations may resume."}),
             True,
             json.dumps(["all_floors", "exterior"])),
            ("PA-NORTH-01", "Elmdale Branch PA System",
             json.dumps([{"zone": "main_floor", "speakers": 6}]),
             json.dumps({"fire_alarm": "Fire alarm activated. Please exit the building immediately.", "all_clear": "All clear. You may re-enter the building."}),
             True,
             json.dumps(["main_floor"])),
            ("PA-SOUTH-01", "Jamie Chick Community Annex PA System",
             json.dumps([{"zone": "main_area", "speakers": 4}]),
             json.dumps({"fire_alarm": "Please evacuate the building immediately.", "all_clear": "All clear."}),
             False,
             json.dumps(["main_area"])),
        ]
        for i, (sys_id, name, zones_json, templates_json, auto_broadcast, broadcast_zones_json) in enumerate(pa):
            await session.execute(text("""
                INSERT INTO pa_systems (security_system_id, system_id, system_name, zones,
                    announcement_templates, auto_broadcast_on_alert, broadcast_zones)
                VALUES (:ssid, :sys_id, :name, cast(:zones as json),
                    cast(:templates as json), :auto, cast(:broadcast as json))
            """), {
                "ssid": all_sec_ids[i % len(all_sec_ids)], "sys_id": sys_id, "name": name,
                "zones": zones_json, "templates": templates_json,
                "auto": auto_broadcast, "broadcast": broadcast_zones_json,
            })
        print(f"    Created {len(pa)} PA systems")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 18. VISITOR MANAGEMENT SYSTEMS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM visitor_management_systems"))
    if r.scalar() == 0 and all_sec_ids:
        print("  Seeding visitor_management_systems...")
        vms = [
            ("VMS-MAIN-01", "Main Branch Visitor Kiosk", "https://vms.library.local/api", True, 120, True),
            ("VMS-NORTH-01", "Elmdale Branch Visitor Check-in", "https://vms-north.library.local/api", True, 60, False),
        ]
        for i, (sys_id, name, endpoint, lockout, duration, quarantine) in enumerate(vms):
            await session.execute(text("""
                INSERT INTO visitor_management_systems (security_system_id, system_id, system_name,
                    api_endpoint, lockout_on_alert, lockout_duration_minutes, quarantine_check_in_on_alert)
                VALUES (:ssid, :sys_id, :name, :endpoint, :lockout, :duration, :quarantine)
            """), {
                "ssid": all_sec_ids[i % len(all_sec_ids)], "sys_id": sys_id, "name": name,
                "endpoint": endpoint, "lockout": lockout,
                "duration": duration, "quarantine": quarantine,
            })
        print(f"    Created {len(vms)} visitor management systems")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 19. BUILDING CLOSURES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM building_closures"))
    if r.scalar() == 0:
        print("  Seeding building_closures...")
        closures = [
            ("weather", "Winter storm - heavy snow and ice accumulation", "moderate",
             _past(75), _past(75) + timedelta(hours=36), _past(75) + timedelta(hours=34),
             False, True, True, True, True,
             "The library is closed today due to severe winter weather. Please stay safe.",
             "All staff: Library closed due to winter storm. Do not attempt to come in unless contacted by your supervisor.",
             "Library closed due to winter storm. We will reopen when conditions improve.",
             "CLOSED TODAY - Winter Storm. Check back for reopening updates.",
             True, True, True, False,
             json.dumps(["circulation", "reference", "programs"]),
             json.dumps(["in-person services", "meeting rooms"]),
             "Online resources remain available. Digital card sign-up at our website."),
            ("holiday", "Thanksgiving Day - library closed", "low",
             _past(120), _past(120) + timedelta(hours=24), _past(120) + timedelta(hours=24),
             False, True, True, True, True,
             "Happy Thanksgiving! The library is closed today. We reopen Friday at 9 AM.",
             "Happy Thanksgiving! Enjoy the day off. See you Friday.",
             "Closed for Thanksgiving. Reopening Friday, November 28 at 9:00 AM.",
             "CLOSED - Thanksgiving Day. Reopening Friday 9 AM.",
             True, False, True, False,
             json.dumps(["all"]),
             json.dumps(["all in-person services"]),
             "24/7 digital resources available at library website."),
            ("maintenance", "HVAC system replacement - planned closure", "low",
             _past(200), _past(200) + timedelta(days=3), _past(200) + timedelta(days=3),
             False, True, True, True, True,
             "The main branch will be closed Oct 15-17 for HVAC system replacement. Elmdale Branch and Jamie Chick Community Annex remain open.",
             "Main branch closed Oct 15-17 for HVAC work. Report to your assigned alternate location.",
             "Main branch closed Oct 15-17 for building maintenance. Other branches open normal hours.",
             "CLOSED Oct 15-17 for maintenance. Other branches open.",
             True, True, True, False,
             json.dumps(["circulation", "reference", "meeting rooms"]),
             json.dumps(["main branch services"]),
             "Patrons may use Elmdale or Jamie Chick Community Annex branches during closure."),
            ("weather", "Severe thunderstorm warning - early closure", "moderate",
             _past(45), _past(45) + timedelta(hours=6), _past(45) + timedelta(hours=5),
             False, True, True, True, True,
             "Library closing early today at 3 PM due to severe thunderstorm warning. Please plan accordingly.",
             "Early closure at 3 PM today. Complete closing procedures by 2:45 PM.",
             "Early closure at 3 PM due to severe weather. Stay safe!",
             "CLOSING EARLY at 3 PM - Severe Weather",
             True, True, True, False,
             json.dumps(["all afternoon programs"]),
             json.dumps(["in-person services after 3 PM"]),
             None),
            ("emergency", "Water main break - emergency closure", "high",
             _past(300), _past(300) + timedelta(hours=48), _past(300) + timedelta(hours=52),
             False, True, True, True, True,
             "Library closed due to water main break. City crews are working on repairs. We apologize for the inconvenience.",
             "Emergency closure - water main break. Do not enter the building. Await further instructions.",
             "Emergency closure due to water main break. Estimated reopening in 2 days.",
             "CLOSED - Water Main Break. Check back for updates.",
             True, True, True, True,
             json.dumps(["all"]),
             json.dumps(["all services"]),
             "Book drops are closed. Returns will not accrue fines during closure."),
        ]
        for reason, details, severity, start, est_reopen, actual_reopen, is_active, patron_notif, staff_notif, vol_notif, board_notif, patron_msg, staff_msg, public_msg, website, email, sms, social, emergency_alert, services_affected_json, services_unavail_json, interim in closures:
            await session.execute(text("""
                INSERT INTO building_closures (closure_reason, reason_details, severity_level,
                    closure_start, estimated_reopening, actual_reopening, is_active,
                    patrons_notified, staff_notified, volunteers_notified, board_notified,
                    patron_message, staff_message, public_message, website_update,
                    email_sent, sms_sent, social_media_posted, emergency_alert_issued,
                    services_affected, services_unavailable, interim_services,
                    created_by_id, updated_by_id, created_at, updated_at)
                VALUES (:reason, :details, :severity,
                    :start, :est_reopen, :actual_reopen, :is_active,
                    :patron_notif, :staff_notif, :vol_notif, :board_notif,
                    :patron_msg, :staff_msg, :public_msg, :website,
                    :email, :sms, :social, :emergency_alert,
                    cast(:services as json), cast(:unavail as json), :interim,
                    :creator, :updater, :start, :start)
            """), {
                "reason": reason, "details": details, "severity": severity,
                "start": start, "est_reopen": est_reopen, "actual_reopen": actual_reopen,
                "is_active": is_active, "patron_notif": patron_notif,
                "staff_notif": staff_notif, "vol_notif": vol_notif, "board_notif": board_notif,
                "patron_msg": patron_msg, "staff_msg": staff_msg,
                "public_msg": public_msg, "website": website,
                "email": email, "sms": sms, "social": social,
                "emergency_alert": emergency_alert,
                "services": services_affected_json, "unavail": services_unavail_json,
                "interim": interim, "creator": staff_ids[0], "updater": staff_ids[0],
            })
        print(f"    Created {len(closures)} building closures")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 20. BUILDING STATUS LOGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM building_status_logs"))
    if r.scalar() == 0:
        print("  Seeding building_status_logs...")
        logs = [
            ("closed", "Winter storm closure", 75),
            ("open", "Reopened after winter storm", 73),
            ("closed", "Thanksgiving Day", 120),
            ("open", "Post-Thanksgiving reopening", 119),
            ("closed", "HVAC replacement - planned maintenance", 200),
            ("open", "HVAC replacement complete, building reopened", 197),
            ("closing", "Early closure due to severe thunderstorm warning", 45),
            ("closed", "Closed - severe weather", 45),
            ("open", "Reopened after severe weather", 44),
            ("emergency", "Water main break - emergency closure", 300),
            ("closed", "Building closed for water main repair", 300),
            ("open", "Reopened after water main repair", 298),
        ]
        for status, reason, days_ago in logs:
            await session.execute(text("""
                INSERT INTO building_status_logs (status, changed_by_id, reason, created_at, updated_at)
                VALUES (:status, :uid, :reason, :created, :created)
            """), {
                "status": status, "uid": random.choice(staff_ids),
                "reason": reason, "created": _past(days_ago),
            })
        print(f"    Created {len(logs)} building status logs")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 21. BRANCH CLOSURES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM branch_closures"))
    if r.scalar() == 0:
        print("  Seeding branch_closures...")
        br_closures = [
            (branch_ids[0], _past_date(120), _past_date(120), None, None, "Thanksgiving Day",
             "All branches closed for Thanksgiving", True, True, True, True, True, True, True, True, True, True, True),
            (branch_ids[0], _past_date(75), _past_date(73), None, None, "Winter Storm Closure",
             "Closed due to heavy snow and ice", True, False, True, True, True, True, True, True, True, True, False),
            (branch_ids[1], _past_date(90), _past_date(88), None, None, "Pipe Repair",
             "Elmdale Branch closed for emergency pipe repair in restrooms", False, False, True, True, False, True, True, True, True, False, False),
            (branch_ids[2], _past_date(150), _past_date(147), None, None, "Carpet Replacement",
             "Jamie Chick Community Annex closed for carpet installation in main reading area", False, False, True, True, False, True, True, True, False, False, False),
            (branch_ids[0], _past_date(365), _past_date(365), None, None, "New Year's Day",
             "All branches closed for New Year's Day", True, True, True, True, True, True, True, True, True, True, True),
            (branch_ids[3], _past_date(60), _past_date(59), time(12, 0), time(17, 0), "Staff Training Day",
             "Northeastern branch closing early at noon for all-staff training", False, False, True, True, False, True, True, True, True, False, False),
        ]
        for bid, start, end, start_t, end_t, reason, desc, system_wide, annual, holds, staff, partner, website, phone, social, google, apple, events in br_closures:
            await session.execute(text("""
                INSERT INTO branch_closures (branch_id, start_date, end_date, start_time, end_time,
                    reason, description, is_system_wide, is_annual,
                    patrons_with_holds_notified, staff_notified, partner_organizations_notified,
                    website_updated, phone_message_updated, social_media_updated,
                    google_maps_updated, apple_maps_updated, events_canceled,
                    created_by_id, updated_by_id)
                VALUES (:bid, :start, :end, :start_t, :end_t,
                    :reason, :desc, :sys_wide, :annual,
                    :holds, :staff, :partner,
                    :website, :phone, :social,
                    :google, :apple, :events,
                    :creator, :updater)
            """), {
                "bid": bid, "start": start, "end": end,
                "start_t": start_t, "end_t": end_t,
                "reason": reason, "desc": desc,
                "sys_wide": system_wide, "annual": annual,
                "holds": holds, "staff": staff, "partner": partner,
                "website": website, "phone": phone, "social": social,
                "google": google, "apple": apple, "events": events,
                "creator": staff_ids[0], "updater": staff_ids[0],
            })
        print(f"    Created {len(br_closures)} branch closures")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 22. ROOM USAGE STATS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM room_usage_stats"))
    if r.scalar() == 0 and room_ids:
        print("  Seeding room_usage_stats...")
        count = 0
        for room_id in room_ids[:6]:  # First 6 rooms
            for days_ago in range(1, 8):  # Last 7 days
                total_res = random.randint(2, 8)
                completed = random.randint(1, total_res)
                cancelled = random.randint(0, total_res - completed)
                no_show = total_res - completed - cancelled
                hourly = {}
                for h in range(9, 21):
                    hourly[str(h)] = random.randint(0, 1)
                await session.execute(text("""
                    INSERT INTO room_usage_stats (room_id, date, total_reservations, completed_reservations,
                        cancelled_reservations, no_show_count, total_hours_booked, total_attendees,
                        hourly_usage)
                    VALUES (:rid, :dt, :total, :completed, :cancelled, :no_show, :hours, :attendees,
                        cast(:hourly as jsonb))
                """), {
                    "rid": room_id, "dt": _past(days_ago),
                    "total": total_res, "completed": completed,
                    "cancelled": cancelled, "no_show": no_show,
                    "hours": random.randint(4, 10),
                    "attendees": random.randint(5, 30),
                    "hourly": json.dumps(hourly),
                })
                count += 1
        print(f"    Created {count} room usage stats")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 23. ROOM QUEUES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM room_queues"))
    if r.scalar() == 0 and room_ids and patron_ids:
        print("  Seeding room_queues...")
        count = 0
        used_combos = set()
        for i in range(5):
            rid = random.choice(room_ids[:4])
            pid = random.choice(patron_ids)
            if (rid, pid) in used_combos:
                continue
            used_combos.add((rid, pid))
            joined = _past(0) - timedelta(minutes=random.randint(5, 120))
            est_ready = joined + timedelta(minutes=random.randint(30, 90))
            await session.execute(text("""
                INSERT INTO room_queues (room_id, patron_id, position, joined_at, estimated_ready_at)
                VALUES (:rid, :pid, :pos, :joined, :ready)
            """), {
                "rid": rid, "pid": pid, "pos": i + 1,
                "joined": joined, "ready": est_ready,
            })
            count += 1
        print(f"    Created {count} room queue entries")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 24. ROOM OCCUPANCY SENSORS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM room_occupancy_sensors"))
    if r.scalar() == 0 and room_ids:
        print("  Seeding room_occupancy_sensors...")
        count = 0
        for rid in room_ids[:6]:
            occupied = random.choice([True, True, False])
            await session.execute(text("""
                INSERT INTO room_occupancy_sensors (room_id, is_occupied, confidence, sensor_type,
                    detected_at, last_motion_at)
                VALUES (:rid, :occupied, :confidence, :sensor, :detected, :motion)
            """), {
                "rid": rid, "occupied": occupied,
                "confidence": random.randint(85, 99),
                "sensor": random.choice(["infrared", "ultrasonic", "pir"]),
                "detected": _past(0) - timedelta(minutes=random.randint(1, 30)),
                "motion": _past(0) - timedelta(minutes=random.randint(0, 15)) if occupied else None,
            })
            count += 1
        print(f"    Created {count} room occupancy sensors")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 25. PRINT RELEASE STATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM print_release_stations"))
    if r.scalar() == 0:
        print("  Seeding print_release_stations...")
        stations = [
            ("Main Floor Release Station", "Next to Main Floor B&W printer", "Patron self-service station",
             "barcode", True, True, True, True, True, True, True, 4, 15, True, 1247, 623.50),
            ("Reference Area Release Station", "Adjacent to Reference Desk B&W printer", "Staff-assisted release available",
             "barcode", True, False, False, False, True, True, True, 4, 15, True, 834, 417.00),
            ("Youth Services Release Station", "Near Youth Services Color printer", "Color printing available here",
             "library_card", True, True, True, True, True, True, True, 4, 10, True, 562, 843.00),
            ("Makerspace Print Station", "Makerspace area, large format", "For large format and specialty prints",
             "library_card", False, False, False, True, True, True, False, 6, 30, False, 189, 945.00),
        ]
        for name, loc, notes, reader, display, touch, cash, card, active, online, pin, pin_len, pin_exp, pay_first, jobs, payments in stations:
            await session.execute(text("""
                INSERT INTO print_release_stations (name, location, notes, card_reader_type,
                    has_display, has_touchscreen, has_cash_payment, has_card_payment,
                    is_active, is_online, last_heartbeat, use_pin_code, pin_length,
                    pin_expiration_minutes, require_payment_before_release,
                    total_jobs_released, total_payments_collected, added_at)
                VALUES (:name, :loc, :notes, :reader,
                    :display, :touch, :cash, :card,
                    :active, :online, :heartbeat, :pin, :pin_len,
                    :pin_exp, :pay_first,
                    :jobs, :payments, :added)
            """), {
                "name": name, "loc": loc, "notes": notes, "reader": reader,
                "display": display, "touch": touch, "cash": cash, "card": card,
                "active": active, "online": online, "heartbeat": _past(0),
                "pin": pin, "pin_len": pin_len, "pin_exp": pin_exp,
                "pay_first": pay_first, "jobs": jobs, "payments": payments,
                "added": _past(random.randint(180, 365)),
            })
        print(f"    Created {len(stations)} print release stations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 26. PRINTER ALERTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM printer_alerts"))
    if r.scalar() == 0 and printer_ids:
        print("  Seeding printer_alerts...")
        alerts = [
            (printer_ids[0], "low_toner", "warning", "Toner level at 15% - order replacement", True, 10),
            (printer_ids[0], "paper_jam", "error", "Paper jam in tray 2 - cleared by staff", True, 5),
            (printer_ids[1], "offline", "error", "Printer offline - network cable disconnected", True, 3),
            (printer_ids[2], "low_paper", "warning", "Paper tray 1 low - 50 sheets remaining", False, None),
            (printer_ids[3], "maintenance_due", "info", "Scheduled maintenance due in 500 prints", False, None),
        ]
        for pid, alert_type, severity, msg, resolved, days_ago_resolved in alerts:
            resolved_at = _past(days_ago_resolved) if resolved and days_ago_resolved else None
            await session.execute(text("""
                INSERT INTO printer_alerts (printer_id, alert_type, severity, message,
                    resolved, resolved_at, resolved_by_id)
                VALUES (:pid, :atype, :severity, :msg, :resolved, :resolved_at, :resolved_by)
            """), {
                "pid": pid, "atype": alert_type, "severity": severity,
                "msg": msg, "resolved": resolved,
                "resolved_at": resolved_at,
                "resolved_by": random.choice(staff_ids) if resolved else None,
            })
        print(f"    Created {len(alerts)} printer alerts")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 27. PRINT PRICING
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM print_pricing"))
    if r.scalar() == 0:
        print("  Seeding print_pricing...")
        pricing = [
            (0.10, 0.50, 10, 100, 0.10, 10, 5, True,
             _past(365), None, "Standard pricing tier - current"),
            (0.08, 0.40, 15, 50, 0.08, 15, 10, False,
             _past(730), _past(365), "Previous pricing tier - superseded"),
        ]
        for bw, color, bulk_disc, bulk_thresh, minimum, dbl_disc, copy_surcharge, active, eff_from, eff_to, notes in pricing:
            await session.execute(text("""
                INSERT INTO print_pricing (blackwhite_price_per_page, color_price_per_page,
                    discount_percentage_for_bulk, bulk_threshold_pages, minimum_charge,
                    double_sided_discount_percentage, copy_machine_surcharge_percentage,
                    is_active, effective_from, effective_to, notes, created_by_id)
                VALUES (:bw, :color, :bulk_disc, :bulk_thresh, :minimum,
                    :dbl_disc, :copy_surcharge,
                    :active, :eff_from, :eff_to, :notes, :creator)
            """), {
                "bw": bw, "color": color, "bulk_disc": bulk_disc,
                "bulk_thresh": bulk_thresh, "minimum": minimum,
                "dbl_disc": dbl_disc, "copy_surcharge": copy_surcharge,
                "active": active, "eff_from": eff_from, "eff_to": eff_to,
                "notes": notes, "creator": staff_ids[0],
            })
        print(f"    Created {len(pricing)} print pricing tiers")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 28. PRINT QUOTAS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM print_quotas"))
    if r.scalar() == 0 and patron_ids:
        print("  Seeding print_quotas...")
        count = 0
        used_users = set()
        for pid in random.sample(patron_ids, min(len(patron_ids), 20)):
            if pid in used_users:
                continue
            used_users.add(pid)
            monthly_limit = random.choice([50, 100, 200])
            dollar_limit = monthly_limit * 0.10
            pages_used = random.randint(0, monthly_limit)
            cost = round(pages_used * 0.10, 2)
            await session.execute(text("""
                INSERT INTO print_quotas (user_id, monthly_pages_limit, monthly_dollar_limit,
                    pages_used_this_month, cost_incurred_this_month, month_starts_on,
                    quota_override_enabled, enforce_quota, allow_overage)
                VALUES (:uid, :pages, :dollars, :used, :cost, :month_start,
                    false, true, false)
            """), {
                "uid": pid, "pages": monthly_limit, "dollars": dollar_limit,
                "used": pages_used, "cost": cost,
                "month_start": datetime(now.year, now.month, 1, tzinfo=utc),
            })
            count += 1
        print(f"    Created {count} print quotas")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "security_systems", "security_system_logs",
        "camera_systems", "camera_recordings",
        "door_locks", "door_lock_events",
        "alarm_system_integrations",
        "emergency_contacts", "emergency_contact_cascades",
        "emergency_resources",
        "first_aid_kit_locations", "emergency_lights",
        "evacuation_routes", "rally_points",
        "safety_inspections",
        "hvac_controls", "pa_systems", "visitor_management_systems",
        "building_closures", "building_status_logs", "branch_closures",
        "room_usage_stats", "room_queues", "room_occupancy_sensors",
        "print_release_stations", "printer_alerts", "print_pricing",
        "print_quotas",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass  # Some tables might not have standard sequence naming

    await session.commit()
    print("  Facilities/security/emergency seeding complete!")
    return True
