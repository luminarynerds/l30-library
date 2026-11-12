# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later

import json
import random
import datetime as _dt
from datetime import datetime, timedelta, timezone, date, time

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

utc = timezone.utc


def _past(days_ago: int) -> datetime:
    return datetime.now(utc) - timedelta(days=days_ago)


def _past_date(days_ago: int) -> date:
    return (datetime.now(utc) - timedelta(days=days_ago)).date()


def _future(days_ahead: int) -> datetime:
    return datetime.now(utc) + timedelta(days=days_ahead)


def _future_date(days_ahead: int) -> date:
    return (datetime.now(utc) + timedelta(days=days_ahead)).date()


async def seed_batch_system(session: AsyncSession) -> bool:

    # ── Grab reusable IDs ──────────────────────────────────────────
    users_r = await session.execute(text("SELECT id, role FROM users"))
    users = users_r.fetchall()
    staff_ids = [u[0] for u in users if u[1] not in ("patron", "child")]
    patron_ids = [u[0] for u in users if u[1] in ("patron", "child")]
    all_ids = [u[0] for u in users]
    admin_ids = [u[0] for u in users if u[1] in ("admin", "director", "super_admin")]

    branch_r = await session.execute(text("SELECT id FROM branches"))
    branch_ids = [r[0] for r in branch_r.fetchall()]

    vol_r = await session.execute(text("SELECT id FROM volunteers"))
    volunteer_ids = [r[0] for r in vol_r.fetchall()]

    shift_r = await session.execute(text("SELECT id FROM staff_shifts"))
    shift_ids = [r[0] for r in shift_r.fetchall()]

    pto_r = await session.execute(text("SELECT id FROM pto_requests"))
    pto_ids = [r[0] for r in pto_r.fetchall()]

    legal_r = await session.execute(text("SELECT id FROM legal_documents"))
    legal_doc_ids = [r[0] for r in legal_r.fetchall()]

    catalog_r = await session.execute(text("SELECT id FROM catalog_items"))
    catalog_ids = [r[0] for r in catalog_r.fetchall()]

    partner_r = await session.execute(text("SELECT id FROM outreach_partners"))
    partner_ids = [r[0] for r in partner_r.fetchall()]

    work_r = await session.execute(text("SELECT id FROM bibframe_works"))
    work_ids = [r[0] for r in work_r.fetchall()]

    skill_r = await session.execute(text("SELECT id FROM skills"))
    skill_ids = [r[0] for r in skill_r.fetchall()]

    onboarding_r = await session.execute(text("SELECT id FROM staff_onboarding"))
    onboarding_ids = [r[0] for r in onboarding_r.fetchall()]

    now = datetime.now(utc)
    org_id = 1  # default organization

    # ════════════════════════════════════════════════════════════════
    # 1. SYSTEM HEALTH + METRICS + STATUS LOGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM system_health"))
    if r.scalar() == 0:
        print("  Seeding system_health...")
        for i in range(24):
            hrs_ago = i * 1
            await session.execute(text("""
                INSERT INTO system_health (status, status_reason, share_events_last_hour, share_events_last_24h,
                    db_connection_active, db_connection_idle, db_slow_queries, db_query_avg_time_ms,
                    error_count_last_hour, error_count_last_24h, error_rate_percent,
                    api_response_p50_ms, api_response_p95_ms, api_response_p99_ms, cache_hit_rate_percent, created_at)
                VALUES (:status, :reason, :ev1h, :ev24h, :dba, :dbi, :slow, :avg_ms,
                    :err1h, :err24h, :err_pct, :p50, :p95, :p99, :cache, :created)
            """), {
                "status": random.choice(["healthy", "healthy", "healthy", "degraded"]),
                "reason": None if i % 5 != 0 else "Routine check",
                "ev1h": random.randint(50, 200), "ev24h": random.randint(1200, 4800),
                "dba": random.randint(2, 8), "dbi": random.randint(1, 5),
                "slow": random.randint(0, 2), "avg_ms": round(random.uniform(5, 25), 2),
                "err1h": random.randint(0, 3), "err24h": random.randint(0, 20),
                "err_pct": round(random.uniform(0, 0.5), 3),
                "p50": round(random.uniform(10, 40), 1),
                "p95": round(random.uniform(80, 200), 1),
                "p99": round(random.uniform(200, 500), 1),
                "cache": round(random.uniform(92, 99), 1),
                "created": _past(0) - timedelta(hours=hrs_ago),
            })
        print(f"    Created 24 system_health records")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM system_health_metrics"))
    if r.scalar() == 0:
        print("  Seeding system_health_metrics...")
        for i in range(48):
            await session.execute(text("""
                INSERT INTO system_health_metrics (organization_id, recorded_at,
                    response_time_p50_ms, response_time_p95_ms, response_time_p99_ms,
                    cpu_usage_percent, memory_usage_percent, disk_usage_percent,
                    db_connection_pool_used, db_connection_pool_available, db_query_latency_ms,
                    cache_hit_rate_percent, cache_latency_ms, error_rate_percent, error_count,
                    is_degraded, is_slow, slow_reason)
                VALUES (:org, :recorded, :p50, :p95, :p99, :cpu, :mem, :disk,
                    :pool_used, :pool_avail, :db_lat, :cache_hit, :cache_lat, :err_rate, :err_cnt,
                    :degraded, :slow, :slow_reason)
            """), {
                "org": org_id,
                "recorded": _past(0) - timedelta(minutes=i * 30),
                "p50": round(random.uniform(12, 45), 1),
                "p95": round(random.uniform(80, 250), 1),
                "p99": round(random.uniform(200, 600), 1),
                "cpu": round(random.uniform(15, 65), 1),
                "mem": round(random.uniform(40, 75), 1),
                "disk": round(random.uniform(30, 55), 1),
                "pool_used": random.randint(2, 10),
                "pool_avail": random.randint(10, 18),
                "db_lat": round(random.uniform(1, 15), 2),
                "cache_hit": round(random.uniform(90, 99.5), 1),
                "cache_lat": round(random.uniform(0.5, 3), 2),
                "err_rate": round(random.uniform(0, 0.3), 3),
                "err_cnt": random.randint(0, 5),
                "degraded": i == 20,
                "slow": i in (20, 21),
                "slow_reason": "High DB latency during backup window" if i == 20 else None,
            })
        print(f"    Created 48 system_health_metrics records")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM system_status_logs"))
    if r.scalar() == 0:
        print("  Seeding system_status_logs...")
        logs = [
            ("maintenance", "database", "Scheduled database maintenance",
             "Routine PostgreSQL vacuum and index rebuild",
             "Brief slowdowns expected for 15 minutes", "Scheduled VACUUM FULL on large tables"),
            ("degraded", "search", "Search index rebuild in progress",
             "Solr index is being rebuilt after catalog import",
             "Search results may be incomplete for ~30 minutes", "Solr reindex triggered by bulk MARC import"),
            ("operational", "cache", "Redis cache cleared",
             "Cache was flushed to resolve stale data issue",
             None, "FLUSHDB executed; cache warming in progress"),
            ("degraded", "circulation", "Self-checkout kiosk offline",
             "Kiosk #2 at main branch experiencing hardware issues",
             "Please use kiosk #1 or the circulation desk", "SIP2 connection timeout on kiosk 2"),
            ("operational", "api", "API performance restored",
             "Response times back to normal after load spike",
             None, "Scaled worker pool from 4 to 8 during peak"),
        ]
        for status, component, title, desc, patron_msg, tech_details in logs:
            started = _past(random.randint(1, 90))
            resolved = (started + timedelta(hours=random.randint(1, 4))).replace(tzinfo=None) if status == "operational" else None
            await session.execute(text("""
                INSERT INTO system_status_logs (organization_id, status, component, title, description,
                    patron_message, technical_details, started_at, resolved_at, is_public, is_scheduled,
                    notified_staff, notified_patrons, reported_by_id, resolved_by_id, resolution_notes)
                VALUES (:org, :status, :component, :title, :desc, :patron, :tech, :started,
                    :resolved, :pub, :sched, :staff_n, :patron_n, :reporter, :resolver, :notes)
            """), {
                "org": org_id, "status": status, "component": component,
                "title": title, "desc": desc, "patron": patron_msg, "tech": tech_details,
                "started": started,
                "resolved": resolved,
                "pub": patron_msg is not None, "sched": status == "maintenance",
                "staff_n": True, "patron_n": patron_msg is not None,
                "reporter": random.choice(admin_ids) if admin_ids else random.choice(staff_ids),
                "resolver": random.choice(admin_ids) if resolved and admin_ids else None,
                "notes": "Issue resolved" if resolved else None,
            })
        print(f"    Created {len(logs)} system_status_logs")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 2. SYSTEM SECURITY CHECKS + SYSTEM ACCESS + PROVISIONING
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM system_security_checks"))
    if r.scalar() == 0:
        print("  Seeding system_security_checks...")
        for i in range(10):
            await session.execute(text("""
                INSERT INTO system_security_checks (all_doors_locked, cameras_operational, alarm_armed,
                    alarm_triggered, verified_at, verified_by_id, remote_access_available, created_at, updated_at)
                VALUES (:doors, :cameras, :alarm, :triggered, :verified, :verifier, :remote, :created, :created)
            """), {
                "doors": True, "cameras": random.choice([True, True, True, False]),
                "alarm": True, "triggered": False,
                "verified": _past(i * 3),
                "verifier": random.choice(staff_ids),
                "remote": True, "created": _past(i * 3).replace(tzinfo=None),
            })
        print(f"    Created 10 security checks")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM system_access"))
    if r.scalar() == 0:
        print("  Seeding system_access...")
        systems = [
            ("ILS", "Integrated Library System (Koha/Sierra)", "credential",
             "Create account in ILS admin panel under Staff > New User",
             "Disable account in ILS admin, remove from all permission groups"),
            ("Email", "Library staff email (Google Workspace)", "sso",
             "Add to Google Workspace via admin console, assign to Library Staff OU",
             "Suspend account in Google admin, transfer ownership of Drive files"),
            ("Door_Access", "Building key card access system", "physical",
             "Request key card from facilities; set zone permissions per branch",
             "Deactivate card in access control system; collect physical card"),
            ("VPN", "Remote access VPN for after-hours work", "credential",
             "Create VPN account in FortiGate admin; assign to Staff group",
             "Remove account from FortiGate; revoke any saved credentials"),
            ("Payroll", "ADP payroll system access", "sso",
             "HR adds employee to ADP; assign role based on position",
             "HR deactivates in ADP during offboarding"),
            ("SharePoint", "Staff intranet and document sharing", "sso",
             "Add to SharePoint group matching their department",
             "Remove from all SharePoint groups; archive personal files"),
        ]
        for sys_name, desc, access_type, prov, deprov in systems:
            await session.execute(text("""
                INSERT INTO system_access (system_name, description, access_type,
                    provisioning_instructions, deprovisioning_instructions)
                VALUES (:name, :desc, :type, :prov, :deprov)
            """), {"name": sys_name, "desc": desc, "type": access_type, "prov": prov, "deprov": deprov})
        print(f"    Created {len(systems)} system_access entries")
        await session.commit()

    # system_access_provisioning requires staff_onboarding FK
    if onboarding_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM system_access_provisioning"))
        if r.scalar() == 0:
            print("  Seeding system_access_provisioning...")
            sa_r = await session.execute(text("SELECT id FROM system_access"))
            sa_ids = [r[0] for r in sa_r.fetchall()]
            count = 0
            used = set()
            for ob_id in onboarding_ids[:4]:
                for sa_id in sa_ids[:4]:
                    if (ob_id, sa_id) not in used:
                        used.add((ob_id, sa_id))
                        await session.execute(text("""
                            INSERT INTO system_access_provisioning (onboarding_id, system_access_id,
                                requested_at, requested_by_id, status, provisioned_at, provisioned_by_id,
                                credentials_provided, credentials_provided_at, notes)
                            VALUES (:ob, :sa, :req_at, :req_by, :status, :prov_at, :prov_by,
                                :creds, :creds_at, :notes)
                        """), {
                            "ob": ob_id, "sa": sa_id,
                            "req_at": _past(30), "req_by": random.choice(admin_ids or staff_ids),
                            "status": "provisioned",
                            "prov_at": _past(28),
                            "prov_by": random.choice(admin_ids or staff_ids),
                            "creds": True, "creds_at": _past(28),
                            "notes": "Provisioned during onboarding",
                        })
                        count += 1
            print(f"    Created {count} access provisioning records")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 3. SETTING DEFINITIONS + SETTING OVERRIDES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM setting_definitions"))
    if r.scalar() == 0:
        print("  Seeding setting_definitions...")
        settings = [
            ("checkout.max_items", "Max Checkout Items", "Maximum items a patron can check out", "circulation", "branch", True, "integer", "25", "1", "100", None),
            ("checkout.loan_days", "Default Loan Period", "Default loan period in days for books", "circulation", "branch", True, "integer", "21", "7", "60", None),
            ("hold.max_holds", "Max Holds", "Maximum number of active holds per patron", "circulation", "branch", True, "integer", "15", "1", "50", None),
            ("fine.daily_rate", "Daily Fine Rate", "Daily fine rate for overdue items in dollars", "circulation", "branch", True, "decimal", "0.25", "0", "5.00", None),
            ("fine.max_amount", "Max Fine Amount", "Maximum fine per item in dollars", "circulation", "branch", True, "decimal", "10.00", "0", "50.00", None),
            ("catalog.items_per_page", "Catalog Page Size", "Number of items per page in catalog search", "display", "system", False, "integer", "20", "10", "100", None),
            ("notification.overdue_days", "Overdue Notification Delay", "Days before first overdue notification", "notification", "system", True, "integer", "1", "0", "7", None),
            ("notification.email_enabled", "Email Notifications", "Enable email notifications system-wide", "notification", "system", False, "boolean", "true", None, None, None),
            ("security.session_timeout_min", "Session Timeout", "Session timeout in minutes", "security", "system", False, "integer", "60", "5", "480", None),
            ("security.password_min_length", "Min Password Length", "Minimum password length for staff accounts", "security", "system", False, "integer", "12", "8", "32", None),
            ("display.theme", "UI Theme", "Default UI color theme", "display", "branch", True, "string", "light", None, None, '["light","dark","system"]'),
            ("ebook.concurrent_loans", "Ebook Concurrent Loans", "Max concurrent ebook loans per patron", "digital", "system", True, "integer", "5", "1", "20", None),
        ]
        for key, name, desc, cat, scope, override, dtype, default, min_v, max_v, allowed in settings:
            await session.execute(text("""
                INSERT INTO setting_definitions (key, name, description, category, min_scope_level,
                    allow_override, data_type, default_value, min_value, max_value, allowed_values,
                    is_active, created_at, updated_at)
                VALUES (:key, :name, :desc, :cat, :scope, :override, :dtype, :default,
                    :min, :max, cast(:allowed as json), true, :now, :now)
            """), {
                "key": key, "name": name, "desc": desc, "cat": cat,
                "scope": scope, "override": override, "dtype": dtype,
                "default": default, "min": min_v, "max": max_v,
                "allowed": allowed, "now": now,
            })
        print(f"    Created {len(settings)} setting definitions")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM setting_overrides"))
    if r.scalar() == 0:
        print("  Seeding setting_overrides...")
        sd_r = await session.execute(text("SELECT id, key FROM setting_definitions"))
        sd_map = {r[1]: r[0] for r in sd_r.fetchall()}
        overrides = [
            ("checkout.max_items", "branch", branch_ids[0], "30"),
            ("checkout.loan_days", "branch", branch_ids[1] if len(branch_ids) > 1 else branch_ids[0], "14"),
            ("fine.daily_rate", "branch", branch_ids[0], "0.10"),
        ]
        for key, scope, bid, val in overrides:
            if key in sd_map:
                await session.execute(text("""
                    INSERT INTO setting_overrides (setting_definition_id, scope_level, branch_id,
                        value, set_by_id, set_at, effective_from)
                    VALUES (:sd_id, :scope, :bid, :val, :by, :at, :from)
                """), {
                    "sd_id": sd_map[key], "scope": scope, "bid": bid,
                    "val": val, "by": random.choice(admin_ids or staff_ids),
                    "at": _past(60), "from": _past(60),
                })
        print(f"    Created {len(overrides)} setting overrides")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 4. PERMISSIONS + ROLE_PERMISSIONS + ROLE_SETTINGS + ROLE_REQUIRED_SKILLS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM permissions"))
    if r.scalar() == 0:
        print("  Seeding permissions...")
        perms = [
            ("circ.checkout", "Checkout Items", "Can check out items to patrons", "circulation"),
            ("circ.checkin", "Check In Items", "Can check in returned items", "circulation"),
            ("circ.waive_fines", "Waive Fines", "Can waive patron fines", "circulation"),
            ("circ.override_limits", "Override Limits", "Can override checkout limits", "circulation"),
            ("catalog.create", "Create Catalog Record", "Can create new catalog records", "catalog"),
            ("catalog.edit", "Edit Catalog Record", "Can edit existing catalog records", "catalog"),
            ("catalog.delete", "Delete Catalog Record", "Can delete catalog records", "catalog"),
            ("patron.view", "View Patron Info", "Can view patron information", "patron"),
            ("patron.edit", "Edit Patron Info", "Can edit patron records", "patron"),
            ("patron.create", "Create Patron", "Can register new patrons", "patron"),
            ("staff.manage", "Manage Staff", "Can manage staff accounts and roles", "admin"),
            ("reports.view", "View Reports", "Can view reports and statistics", "reports"),
            ("reports.export", "Export Reports", "Can export report data", "reports"),
            ("system.settings", "System Settings", "Can modify system settings", "admin"),
            ("events.manage", "Manage Events", "Can create and manage events", "events"),
            ("rooms.manage", "Manage Rooms", "Can manage room bookings and settings", "facilities"),
        ]
        for code, name, desc, cat in perms:
            await session.execute(text("""
                INSERT INTO permissions (code, name, description, category, created_at, updated_at)
                VALUES (:code, :name, :desc, :cat, :now, :now)
            """), {"code": code, "name": name, "desc": desc, "cat": cat, "now": now})
        print(f"    Created {len(perms)} permissions")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM role_permissions"))
    if r.scalar() == 0:
        print("  Seeding role_permissions...")
        perm_r = await session.execute(text("SELECT id, code FROM permissions"))
        perm_map = {r[1]: r[0] for r in perm_r.fetchall()}
        role_perms = {
            "staff": ["circ.checkout", "circ.checkin", "patron.view", "patron.create", "reports.view", "events.manage"],
            "admin": ["circ.checkout", "circ.checkin", "circ.waive_fines", "circ.override_limits",
                       "catalog.create", "catalog.edit", "patron.view", "patron.edit", "patron.create",
                       "staff.manage", "reports.view", "reports.export", "events.manage", "rooms.manage"],
            "director": ["circ.checkout", "circ.checkin", "circ.waive_fines", "circ.override_limits",
                          "catalog.create", "catalog.edit", "catalog.delete", "patron.view", "patron.edit",
                          "patron.create", "staff.manage", "reports.view", "reports.export",
                          "system.settings", "events.manage", "rooms.manage"],
        }
        count = 0
        for role, codes in role_perms.items():
            for code in codes:
                if code in perm_map:
                    await session.execute(text("""
                        INSERT INTO role_permissions (role, permission_id)
                        VALUES (:role, :pid)
                    """), {"role": role, "pid": perm_map[code]})
                    count += 1
        print(f"    Created {count} role_permissions")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM role_settings"))
    if r.scalar() == 0:
        print("  Seeding role_settings...")
        rs_data = [
            ("patron", 25, 15, 3, 21, 7, 2500, False, False, 0, 0, True, True, True, True, False, False),
            ("teacher", 100, 50, 5, 42, 14, 0, True, False, 0, 0, True, True, True, True, False, False),
            ("child", 10, 5, 2, 14, 7, 500, False, True, 15, 300, True, False, False, False, True, False),
            ("staff", 50, 25, 5, 28, 10, 0, True, False, 0, 0, True, True, True, True, False, False),
            ("admin", 99, 50, 10, 28, 14, 0, True, False, 0, 0, True, True, True, True, False, False),
            ("director", 99, 99, 99, 28, 14, 0, True, False, 0, 0, True, True, True, True, False, False),
            ("homebond", 15, 10, 3, 28, 7, 2500, False, False, 0, 0, True, True, False, False, False, True),
            ("bookmobile", 15, 10, 3, 28, 7, 2500, False, False, 0, 0, True, True, False, False, False, False),
        ]
        for role, max_co, max_h, max_ren, co_days, hold_days, max_fine, fine_ex, use_rm, min_per_day, max_rm, digital, adult, rooms, printer, guardian, home in rs_data:
            await session.execute(text("""
                INSERT INTO role_settings (role, max_checkouts, max_holds, max_renewals,
                    checkout_duration_days, hold_duration_days, max_fine_amount, fine_exempt,
                    use_reading_minutes, minutes_per_day_overdue, max_reading_minutes_owed,
                    can_use_digital_resources, can_access_adult_content, can_book_meeting_rooms,
                    can_use_3d_printer, requires_guardian, home_delivery_eligible)
                VALUES (:role, :co, :h, :ren, :co_days, :h_days, :fine, :exempt,
                    :use_rm, :min_day, :max_rm, :dig, :adult, :rooms, :printer, :guard, :home)
            """), {
                "role": role, "co": max_co, "h": max_h, "ren": max_ren,
                "co_days": co_days, "h_days": hold_days, "fine": max_fine,
                "exempt": fine_ex, "use_rm": use_rm, "min_day": min_per_day,
                "max_rm": max_rm, "dig": digital, "adult": adult,
                "rooms": rooms, "printer": printer, "guard": guardian, "home": home,
            })
        print(f"    Created {len(rs_data)} role_settings")
        await session.commit()

    if skill_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM role_required_skills"))
        if r.scalar() == 0:
            print("  Seeding role_required_skills...")
            count = 0
            used = set()
            for role in ["staff", "admin", "director"]:
                for sid in random.sample(skill_ids, min(len(skill_ids), 3)):
                    if (role, sid) not in used:
                        used.add((role, sid))
                        await session.execute(text("""
                            INSERT INTO role_required_skills (role, skill_id, required_level, is_mandatory)
                            VALUES (:role, :sid, :level, :mandatory)
                        """), {"role": role, "sid": sid, "level": random.randint(1, 3), "mandatory": random.choice([True, False])})
                        count += 1
            print(f"    Created {count} role_required_skills")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 5. ALERT THRESHOLDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM alert_thresholds"))
    if r.scalar() == 0:
        print("  Seeding alert_thresholds...")
        thresholds = [
            ("High Error Rate", "Alert when error rate exceeds threshold", "system", "percentage", 5, 10, 15, True),
            ("Slow API Response", "Alert when API p95 response time is high", "performance", "milliseconds", 500, 2000, 5, True),
            ("Low Cache Hit Rate", "Alert when cache hit rate drops", "performance", "percentage", 85, 70, 15, True),
            ("High DB Connections", "Alert when DB connection pool is nearly full", "database", "count", 15, 18, 5, True),
            ("Disk Space Low", "Alert when disk usage is high", "infrastructure", "percentage", 80, 90, 60, True),
            ("Failed Login Attempts", "Alert on excessive failed logins", "security", "count", 10, 25, 30, True),
            ("Overdue Holds Queue", "Alert when holds queue is backed up", "circulation", "count", 50, 100, 60, True),
            ("Print Queue Stuck", "Alert when print jobs are stuck", "hardware", "count", 5, 15, 15, False),
        ]
        for name, desc, cat, ttype, warn, crit, window, enabled in thresholds:
            await session.execute(text("""
                INSERT INTO alert_thresholds (name, description, category, threshold_type,
                    warning_level, critical_level, time_window_minutes, enabled, created_at, updated_at)
                VALUES (:name, :desc, :cat, :type, :warn, :crit, :window, :enabled, :now, :now)
            """), {
                "name": name, "desc": desc, "cat": cat, "type": ttype,
                "warn": warn, "crit": crit, "window": window,
                "enabled": enabled, "now": now,
            })
        print(f"    Created {len(thresholds)} alert thresholds")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 6. AI CONFIGURATIONS + GUARDRAILS + MODEL ALLOWLIST + TOOLS + USAGE LIMITS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM ai_configurations"))
    if r.scalar() == 0:
        print("  Seeding ai_configurations...")
        configs = [
            ("default_model", '{"model": "llama3.2:1b", "provider": "ollama"}', "Default AI model for library tools"),
            ("content_moderation", '{"enabled": true, "auto_flag_threshold": 0.8, "categories": ["profanity","spam","harassment"]}', "Content moderation settings"),
            ("recommendation_engine", '{"enabled": true, "min_history_items": 5, "diversity_factor": 0.3}', "Recommendation engine configuration"),
            ("chat_assistant", '{"max_conversation_turns": 20, "include_catalog_context": true}', "Chat assistant configuration"),
        ]
        for key, val, desc in configs:
            await session.execute(text("""
                INSERT INTO ai_configurations (config_key, config_value, description, updated_by_id, created_at, updated_at)
                VALUES (:key, cast(:val as jsonb), :desc, :by, :now, :now)
            """), {"key": key, "val": val, "desc": desc, "by": admin_ids[0] if admin_ids else staff_ids[0], "now": now})
        print(f"    Created {len(configs)} AI configurations")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM ai_guardrails"))
    if r.scalar() == 0:
        print("  Seeding ai_guardrails...")
        guardrails = [
            ("No PII in responses", "Prevent AI from including patron PII in responses", True, "content_filter", '{"block_patterns": ["SSN","credit_card","address"]}', '["chat_assistant","recommendation"]', 1),
            ("Age-appropriate content", "Ensure responses match patron age group", True, "content_filter", '{"check_age_rating": true, "default_rating": "all_ages"}', '["chat_assistant","recommendation"]', 2),
            ("No medical/legal advice", "Block medical or legal advice in responses", True, "topic_restriction", '{"blocked_topics": ["medical_advice","legal_advice","financial_advice"]}', '["chat_assistant"]', 3),
            ("Rate limiting", "Limit requests per user per hour", True, "rate_limit", '{"max_requests_per_hour": 50, "cooldown_minutes": 5}', None, 4),
            ("Response length limit", "Cap response length to prevent runaway generation", True, "output_limit", '{"max_tokens": 2000, "max_characters": 8000}', '["chat_assistant"]', 5),
        ]
        for name, desc, enabled, rtype, config, applies, priority in guardrails:
            await session.execute(text("""
                INSERT INTO ai_guardrails (name, description, enabled, rule_type, rule_config,
                    applies_to_tools, priority, created_at, updated_at, created_by_id)
                VALUES (:name, :desc, :enabled, :rtype, cast(:config as jsonb),
                    cast(:applies as jsonb), :priority, :now, :now, :by)
            """), {
                "name": name, "desc": desc, "enabled": enabled, "rtype": rtype,
                "config": config, "applies": applies, "priority": priority,
                "now": now, "by": admin_ids[0] if admin_ids else staff_ids[0],
            })
        print(f"    Created {len(guardrails)} AI guardrails")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM ai_model_allowlist"))
    if r.scalar() == 0:
        print("  Seeding ai_model_allowlist...")
        models = [
            ("llama3.2:1b", "Llama 3.2 1B", "Lightweight local model via Ollama", 2048, 0.0, 1.0, True),
            ("llama3.2:3b", "Llama 3.2 3B", "Medium local model via Ollama", 4096, 0.0, 1.0, False),
            ("gpt-4o-mini", "GPT-4o Mini", "OpenAI cost-effective model for simple tasks", 4096, 0.0, 2.0, False),
        ]
        for model, display, desc, tokens, temp_min, temp_max, enabled in models:
            await session.execute(text("""
                INSERT INTO ai_model_allowlist (model_name, display_name, description,
                    max_tokens_limit, allowed_temperature_min, allowed_temperature_max, enabled,
                    created_at, updated_at)
                VALUES (:model, :display, :desc, :tokens, :tmin, :tmax, :enabled, :now, :now)
            """), {
                "model": model, "display": display, "desc": desc, "tokens": tokens,
                "tmin": temp_min, "tmax": temp_max, "enabled": enabled, "now": now,
            })
        print(f"    Created {len(models)} AI model allowlist entries")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM ai_tools"))
    if r.scalar() == 0:
        print("  Seeding ai_tools...")
        tools = [
            ("book-recommender", "Book Recommender", "Suggests books based on reading history and preferences",
             "You are a helpful library book recommender. Use the patron's reading history to suggest relevant titles from the catalog. Be warm, concise, and varied in your suggestions.",
             0.7, 1024, "llama3.2:1b", True, False, False, "book-open", "patron", 1),
            ("catalog-search", "Smart Catalog Search", "Natural language catalog search assistant",
             "You help patrons search the library catalog using natural language. Convert their query into structured search parameters. Include format, genre, and availability filters when relevant.",
             0.3, 512, "llama3.2:1b", True, False, False, "search", "patron", 2),
            ("readers-advisory", "Reader's Advisory", "In-depth reading guidance for patrons",
             "You are an experienced reader's advisor at a public library. Help patrons find their next great read by asking about their preferences, mood, and past favorites. Provide thoughtful, personalized recommendations.",
             0.8, 2048, "llama3.2:1b", True, True, True, "message-circle", "patron", 3),
            ("policy-lookup", "Policy Assistant", "Answers questions about library policies",
             "You answer patron and staff questions about library policies accurately. Only cite policies that exist in the provided context. If uncertain, direct the user to speak with staff.",
             0.2, 1024, "llama3.2:1b", True, False, False, "shield", "staff", 4),
        ]
        for tool_id, name, desc, prompt, temp, tokens, model, enabled, in_lib, auth, icon, cat, order in tools:
            await session.execute(text("""
                INSERT INTO ai_tools (tool_id, name, description, system_prompt, temperature,
                    max_tokens, model, enabled, in_library_only, requires_auth, icon, category,
                    sort_order, created_at, updated_at, created_by_id, usage_count, last_used_at)
                VALUES (:tid, :name, :desc, :prompt, :temp, :tokens, :model, :enabled,
                    :in_lib, :auth, :icon, :cat, :order, :now, :now, :by, :usage, :last)
            """), {
                "tid": tool_id, "name": name, "desc": desc, "prompt": prompt,
                "temp": temp, "tokens": tokens, "model": model, "enabled": enabled,
                "in_lib": in_lib, "auth": auth, "icon": icon, "cat": cat,
                "order": order, "now": now,
                "by": admin_ids[0] if admin_ids else staff_ids[0],
                "usage": random.randint(50, 500),
                "last": _past(random.randint(0, 3)),
            })
        print(f"    Created {len(tools)} AI tools")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM ai_usage_limits"))
    if r.scalar() == 0:
        print("  Seeding ai_usage_limits...")
        limits = [
            ("patron", 20, 5, 1024, True),
            ("child", 10, 3, 512, True),
            ("staff", 100, 25, 2048, True),
            ("admin", 200, 50, 4096, True),
            ("director", 500, 100, 4096, True),
        ]
        for role, daily, hourly, tokens, enabled in limits:
            await session.execute(text("""
                INSERT INTO ai_usage_limits (role, daily_limit, hourly_limit,
                    max_tokens_per_request, enabled, created_at, updated_at)
                VALUES (:role, :daily, :hourly, :tokens, :enabled, :now, :now)
            """), {"role": role, "daily": daily, "hourly": hourly, "tokens": tokens, "enabled": enabled, "now": now})
        print(f"    Created {len(limits)} AI usage limits")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 7. PROXY CONFIGURATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM proxy_configurations"))
    if r.scalar() == 0:
        print("  Seeding proxy_configurations...")
        proxies = [
            ("EZproxy Main", "ezproxy", "https://ezproxy.l30.org", "/login", "url", True, True,
             True, False, "Primary EZproxy for database access"),
            ("In-Library Direct", "direct", None, None, None, False, True,
             False, True, "Direct access from library IP ranges"),
        ]
        for name, ptype, base_url, login_path, url_param, is_default, active, req_card, guest, notes in proxies:
            ip_ranges = json.dumps(["10.0.0.0/8", "192.168.1.0/24"]) if ptype == "direct" else None
            await session.execute(text("""
                INSERT INTO proxy_configurations (name, proxy_type, ezproxy_base_url,
                    ezproxy_login_path, ezproxy_url_param, onsite_ip_ranges,
                    requires_library_card, allows_guest_access, is_active, is_default,
                    notes, created_by_id)
                VALUES (:name, :ptype, :base, :login, :param, cast(:ips as jsonb),
                    :card, :guest, :active, :default, :notes, :by)
            """), {
                "name": name, "ptype": ptype, "base": base_url,
                "login": login_path, "param": url_param, "ips": ip_ranges,
                "card": req_card, "guest": guest, "active": active,
                "default": is_default, "notes": notes,
                "by": admin_ids[0] if admin_ids else staff_ids[0],
            })
        print(f"    Created {len(proxies)} proxy configurations")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 8. FOCUS TIME (settings, blocks, tracking, approvals, overrides)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM focus_time_settings"))
    if r.scalar() == 0:
        print("  Seeding focus_time_settings...")
        for bid in branch_ids:
            await session.execute(text("""
                INSERT INTO focus_time_settings (organization_id, branch_id,
                    requires_manager_approval, min_advance_notice_hours, max_duration_hours,
                    min_duration_minutes, max_blocks_per_week, allow_recurring_blocks,
                    allow_emergency_override, require_backup_contact, notification_enabled,
                    notification_reminder_minutes, batch_notification_interval_minutes)
                VALUES (:org, :bid, :approval, :notice, :max_dur, :min_dur, :max_blocks,
                    :recurring, :emergency, :backup, :notify, :remind, :batch)
            """), {
                "org": org_id, "bid": bid, "approval": True, "notice": 24,
                "max_dur": 4, "min_dur": 30, "max_blocks": 3,
                "recurring": True, "emergency": True, "backup": True,
                "notify": True, "remind": 15, "batch": 60,
            })
        print(f"    Created {len(branch_ids)} focus_time_settings")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM focus_time_blocks"))
    if r.scalar() == 0:
        print("  Seeding focus_time_blocks...")
        work_types = ["deep_work", "cataloging", "collection_development", "programming",
                       "report_writing", "professional_development", "grant_writing"]
        statuses = ["completed", "completed", "completed", "approved", "pending_approval", "cancelled"]
        block_ids_created = []
        for i in range(15):
            sid = random.choice(staff_ids)
            backup = random.choice([s for s in staff_ids if s != sid])
            start = _past(random.randint(1, 60)).replace(hour=random.choice([9, 10, 13, 14]), minute=0, second=0, microsecond=0)
            end = start + timedelta(hours=random.choice([1, 2, 3]))
            status = random.choice(statuses)
            r2 = await session.execute(text("""
                INSERT INTO focus_time_blocks (organization_id, user_id, start_time, end_time,
                    work_type, description, status, requires_approval, is_recurring,
                    backup_contact_id, batch_notifications, notification_method,
                    completed_at, cancelled_at)
                VALUES (:org, :uid, :start, :end, :wtype, :desc, :status, true, false,
                    :backup, true, 'email', :completed, :cancelled)
                RETURNING id
            """), {
                "org": org_id, "uid": sid,
                "start": start.replace(tzinfo=None), "end": end.replace(tzinfo=None),
                "wtype": random.choice(work_types),
                "desc": random.choice([
                    "Catalog maintenance and record cleanup",
                    "Collection development review for Q2",
                    "Grant application for LSTA technology funds",
                    "Summer reading program planning",
                    "Professional development coursework",
                    "Weeding project — 700s section",
                    "Annual report data compilation",
                ]),
                "status": status, "backup": backup,
                "completed": end.replace(tzinfo=None) if status == "completed" else None,
                "cancelled": start.replace(tzinfo=None) if status == "cancelled" else None,
            })
            block_ids_created.append(r2.scalar())
        print(f"    Created 15 focus_time_blocks")
        await session.commit()

        # focus_time_tracking
        ftb_r = await session.execute(text("SELECT id FROM focus_time_blocks WHERE status = 'completed'"))
        completed_block_ids = [r[0] for r in ftb_r.fetchall()]
        if completed_block_ids:
            print("  Seeding focus_time_tracking...")
            for bid in completed_block_ids:
                await session.execute(text("""
                    INSERT INTO focus_time_tracking (focus_block_id, interruption_count,
                        work_completed_percentage, tasks_completed, tasks_planned,
                        quality_rating, productivity_rating, self_assessment_notes,
                        would_schedule_again, optimal_time_of_day)
                    VALUES (:bid, :interrupts, :pct, :done, :planned, :quality, :prod, :notes, :again, :tod)
                """), {
                    "bid": bid,
                    "interrupts": random.randint(0, 4),
                    "pct": round(random.uniform(60, 100), 1),
                    "done": random.randint(2, 8),
                    "planned": random.randint(3, 10),
                    "quality": random.randint(3, 5),
                    "prod": random.randint(3, 5),
                    "notes": random.choice(["Very productive session", "Some interruptions but managed well", "Great focus today"]),
                    "again": True,
                    "tod": random.choice(["morning", "afternoon"]),
                })
            print(f"    Created {len(completed_block_ids)} focus_time_tracking records")
            await session.commit()

        # focus_time_approvals
        if block_ids_created:
            print("  Seeding focus_time_approvals...")
            for bid in block_ids_created[:8]:
                status = random.choice(["approved", "approved", "approved", "rejected"])
                await session.execute(text("""
                    INSERT INTO focus_time_approvals (focus_block_id, manager_id, status,
                        decision_comment, requested_at, decided_at)
                    VALUES (:bid, :mgr, :status, :comment, :req, :decided)
                """), {
                    "bid": bid,
                    "mgr": random.choice(admin_ids or staff_ids),
                    "status": status,
                    "comment": "Approved — coverage confirmed" if status == "approved" else "Insufficient staffing that day",
                    "req": _past(random.randint(5, 30)),
                    "decided": _past(random.randint(3, 28)).replace(tzinfo=None),
                })
            print(f"    Created {min(8, len(block_ids_created))} focus_time_approvals")
            await session.commit()

        # focus_time_overrides
        if block_ids_created:
            print("  Seeding focus_time_overrides...")
            for bid in block_ids_created[:3]:
                await session.execute(text("""
                    INSERT INTO focus_time_overrides (focus_block_id, overridden_by_id, reason,
                        description, urgency_level, requires_escalation, is_resolved,
                        resolved_at, resolution_notes)
                    VALUES (:bid, :by, :reason, :desc, :urgency, false, :resolved,
                        :resolved_at, :res_notes)
                """), {
                    "bid": bid,
                    "by": random.choice(admin_ids or staff_ids),
                    "reason": random.choice(["urgent_patron", "staffing_emergency", "system_issue"]),
                    "desc": random.choice([
                        "Patron emergency at circulation desk",
                        "Staff callout — need coverage",
                        "System outage requiring immediate attention",
                    ]),
                    "urgency": random.randint(3, 5),
                    "resolved": True,
                    "resolved_at": _past(random.randint(1, 20)).replace(tzinfo=None),
                    "res_notes": "Situation resolved; focus time rescheduled",
                })
            print(f"    Created 3 focus_time_overrides")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 9. SHIFT PREFERENCES + SHIFT SIGNUPS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM shift_preferences"))
    if r.scalar() == 0:
        print("  Seeding shift_preferences...")
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        count = 0
        for sid in random.sample(staff_ids, min(len(staff_ids), 15)):
            for _ in range(random.randint(1, 3)):
                await session.execute(text("""
                    INSERT INTO shift_preferences (staff_id, branch_id, day_of_week, shift_type,
                        preference_type, preferred_start_time, preferred_end_time, reason,
                        effective_date, end_date)
                    VALUES (:sid, :bid, :day, :stype, :ptype, :start, :end, :reason, :eff, :end_d)
                """), {
                    "sid": sid, "bid": random.choice(branch_ids),
                    "day": random.choice(days),
                    "stype": random.choice(["opening", "closing", "mid_day"]),
                    "ptype": random.choice(["preferred", "acceptable", "unavailable"]),
                    "start": time(random.choice([7, 8, 9, 12, 13])),
                    "end": time(random.choice([15, 16, 17, 20, 21])),
                    "reason": random.choice(["Childcare schedule", "Commute preference", "Class schedule", None]),
                    "eff": _past_date(90),
                    "end_d": _future_date(90),
                })
                count += 1
        print(f"    Created {count} shift_preferences")
        await session.commit()

    # shift_signups require volunteer_shifts — check if any exist
    vol_shift_r = await session.execute(text("SELECT id FROM volunteer_shifts LIMIT 10"))
    vol_shift_ids = [r[0] for r in vol_shift_r.fetchall()]
    if vol_shift_ids and volunteer_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM shift_signups"))
        if r.scalar() == 0:
            print("  Seeding shift_signups...")
            count = 0
            used = set()
            for _ in range(min(20, len(vol_shift_ids) * len(volunteer_ids))):
                vs_id = random.choice(vol_shift_ids)
                v_id = random.choice(volunteer_ids)
                if (vs_id, v_id) not in used:
                    used.add((vs_id, v_id))
                    status = random.choice(["confirmed", "confirmed", "completed", "pending", "cancelled"])
                    signed = _past(random.randint(5, 60))
                    await session.execute(text("""
                        INSERT INTO shift_signups (shift_id, volunteer_id, status, signed_up_at,
                            confirmed_at, actual_hours, completed_at, staff_notes)
                        VALUES (:sid, :vid, :status, :signed, :conf, :hours, :completed, :notes)
                    """), {
                        "sid": vs_id, "vid": v_id, "status": status,
                        "signed": signed,
                        "conf": signed + timedelta(hours=2) if status in ("confirmed", "completed") else None,
                        "hours": round(random.uniform(2, 6), 1) if status == "completed" else None,
                        "completed": signed + timedelta(days=1) if status == "completed" else None,
                        "notes": None,
                    })
                    count += 1
            print(f"    Created {count} shift_signups")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 10. SHIFT SWAPS (listings, claims, matches, notifications, audits)
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM shift_swap_listings"))
    if r.scalar() == 0:
        print("  Seeding shift_swap_listings...")
        listing_ids = []
        for i in range(12):
            uid = random.choice(staff_ids)
            sdate = _future_date(random.randint(1, 30))
            start_h = random.choice([7, 8, 9, 12, 13])
            end_h = start_h + random.choice([4, 6, 8])
            status = random.choice(["open", "open", "claimed", "completed", "expired"])
            r2 = await session.execute(text("""
                INSERT INTO shift_swap_listings (user_id, branch_id, listing_type, shift_date,
                    shift_start_time, shift_end_time, shift_type, is_partial, status,
                    description, expires_at)
                VALUES (:uid, :bid, :ltype, :sdate, :start, :end, :stype, false, :status,
                    :desc, :expires)
                RETURNING id
            """), {
                "uid": uid, "bid": random.choice(branch_ids),
                "ltype": random.choice(["giving_away", "looking_for"]),
                "sdate": sdate,
                "start": time(start_h), "end": time(min(end_h, 23)),
                "stype": random.choice(["opening", "closing", "mid_day"]),
                "status": status,
                "desc": random.choice([
                    "Doctor appointment, need coverage",
                    "Family event that day",
                    "Looking to pick up extra hours",
                    "Schedule conflict with training",
                    None,
                ]),
                "expires": _future(random.randint(1, 14)),
            })
            listing_ids.append(r2.scalar())
        print(f"    Created {len(listing_ids)} shift_swap_listings")
        await session.commit()

        # shift_swap_claims
        if listing_ids:
            print("  Seeding shift_swap_claims...")
            claim_ids = []
            for lid in listing_ids[:6]:
                claimer = random.choice([s for s in staff_ids])
                status = random.choice(["pending", "approved", "completed", "rejected"])
                r2 = await session.execute(text("""
                    INSERT INTO shift_swap_claims (listing_id, claimer_id, status, message,
                        approved_at, approved_by_id, completed_at)
                    VALUES (:lid, :claimer, :status, :msg, :approved, :approver, :completed)
                    RETURNING id
                """), {
                    "lid": lid, "claimer": claimer, "status": status,
                    "msg": random.choice(["I can cover this!", "Available that day", "Happy to swap", None]),
                    "approved": _past(random.randint(1, 5)) if status in ("approved", "completed") else None,
                    "approver": random.choice(admin_ids or staff_ids) if status in ("approved", "completed") else None,
                    "completed": _past(1) if status == "completed" else None,
                })
                claim_ids.append(r2.scalar())
            print(f"    Created {len(claim_ids)} shift_swap_claims")
            await session.commit()

            # shift_swap_matches (need at least 2 listings to pair)
            if len(listing_ids) >= 2:
                print("  Seeding shift_swap_matches...")
                used_pairs = set()
                match_ids = []
                for _ in range(min(4, len(listing_ids) // 2)):
                    g, t = random.sample(listing_ids, 2)
                    if (g, t) not in used_pairs:
                        used_pairs.add((g, t))
                        r2 = await session.execute(text("""
                            INSERT INTO shift_swap_matches (giver_listing_id, taker_listing_id,
                                compatibility_score, status, notified_at)
                            VALUES (:g, :t, :score, :status, :notified)
                            RETURNING id
                        """), {
                            "g": g, "t": t,
                            "score": round(random.uniform(0.5, 1.0), 2),
                            "status": random.choice(["notified", "accepted", "completed"]),
                            "notified": _past(random.randint(1, 10)),
                        })
                        match_ids.append(r2.scalar())
                print(f"    Created {len(match_ids)} shift_swap_matches")
                await session.commit()

                # shift_swap_notifications
                print("  Seeding shift_swap_notifications...")
                notif_count = 0
                for lid in listing_ids[:5]:
                    await session.execute(text("""
                        INSERT INTO shift_swap_notifications (user_id, notification_type,
                            listing_id, title, message, is_read, read_at)
                        VALUES (:uid, :ntype, :lid, :title, :msg, :read, :read_at)
                    """), {
                        "uid": random.choice(staff_ids),
                        "ntype": random.choice(["new_match", "swap_claimed", "claim_approved"]),
                        "lid": lid,
                        "title": random.choice(["New shift swap match found", "Your shift was claimed", "Swap claim approved"]),
                        "msg": "Check your shift swap dashboard for details.",
                        "read": random.choice([True, True, False]),
                        "read_at": _past(random.randint(0, 5)) if random.random() > 0.3 else None,
                    })
                    notif_count += 1
                print(f"    Created {notif_count} shift_swap_notifications")
                await session.commit()

        # shift_swap_audits
        print("  Seeding shift_swap_audits...")
        audit_count = 0
        for _ in range(8):
            await session.execute(text("""
                INSERT INTO shift_swap_audits (user_id, action, shift_date, description)
                VALUES (:uid, :action, :sdate, :desc)
            """), {
                "uid": random.choice(staff_ids),
                "action": random.choice(["created_listing", "claimed_shift", "approved_swap", "completed_swap", "cancelled_listing"]),
                "sdate": _future_date(random.randint(1, 30)),
                "desc": random.choice([
                    "Staff member posted shift for swap",
                    "Shift swap claim submitted",
                    "Manager approved the shift swap",
                    "Swap completed successfully",
                    "Listing withdrawn by poster",
                ]),
            })
            audit_count += 1
        print(f"    Created {audit_count} shift_swap_audits")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 11. SHIFT CHECKLISTS + CONSTRAINT VIOLATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM shift_checklist_sessions"))
    if r.scalar() == 0:
        print("  Seeding shift_checklist_sessions...")
        for i in range(12):
            sid = random.choice(staff_ids)
            sdate = _past(i * 2)
            completed = random.choice([True, True, True, False])
            await session.execute(text("""
                INSERT INTO shift_checklist_sessions (organization_id, staff_id, shift_date,
                    items_completed, total_items, is_completed, completed_at, notes)
                VALUES (:org, :sid, :sdate, :done, :total, :completed, :comp_at, :notes)
            """), {
                "org": org_id, "sid": sid,
                "sdate": sdate.replace(tzinfo=None),
                "done": random.randint(8, 12) if completed else random.randint(3, 7),
                "total": 12,
                "completed": completed,
                "comp_at": sdate + timedelta(hours=1) if completed else None,
                "notes": None if completed else "Interrupted by patron emergency",
            })
        print(f"    Created 12 shift_checklist_sessions")
        await session.commit()

    # shift_constraint_violations need fairness_policies FK
    fp_r = await session.execute(text("SELECT id FROM fairness_policies LIMIT 5"))
    fp_ids = [r[0] for r in fp_r.fetchall()]
    if fp_ids and shift_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM shift_constraint_violations"))
        if r.scalar() == 0:
            print("  Seeding shift_constraint_violations...")
            violations = [
                ("hard_violation", "Clopening shift detected — less than 10 hours between closing and opening"),
                ("soft_violation", "Exceeded 5 consecutive days worked"),
                ("warning", "Weekend shifts unevenly distributed this month"),
                ("soft_violation", "Overtime threshold approaching — 38 hours scheduled"),
                ("warning", "Staff member has not had a Saturday off in 4 weeks"),
            ]
            for vtype, desc in violations:
                await session.execute(text("""
                    INSERT INTO shift_constraint_violations (branch_id, staff_id, policy_id,
                        violation_type, description, affected_shift_id, affected_date,
                        severity_score, is_resolved, detected_at)
                    VALUES (:bid, :sid, :pid, :vtype, :desc, :shift, :adate, :score, :resolved, :detected)
                """), {
                    "bid": random.choice(branch_ids), "sid": random.choice(staff_ids),
                    "pid": random.choice(fp_ids), "vtype": vtype, "desc": desc,
                    "shift": random.choice(shift_ids),
                    "adate": _past_date(random.randint(1, 30)),
                    "score": round(random.uniform(0.3, 1.0), 2),
                    "resolved": random.choice([True, True, False]),
                    "detected": _past(random.randint(1, 30)),
                })
            print(f"    Created {len(violations)} shift_constraint_violations")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 12. ONCALL SCHEDULES + CALLOUT COVERAGE REQUESTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM oncall_schedules"))
    if r.scalar() == 0:
        print("  Seeding oncall_schedules...")
        for i in range(8):
            mgr = random.choice(admin_ids or staff_ids)
            start = _past(7 * (8 - i))
            end = start + timedelta(days=7)
            await session.execute(text("""
                INSERT INTO oncall_schedules (manager_id, start_date, end_date,
                    escalation_level, notes, created_at, updated_at)
                VALUES (:mgr, :start, :end, :level, :notes, :now, :now)
            """), {
                "mgr": mgr, "start": start, "end": end,
                "level": random.randint(1, 3),
                "notes": random.choice(["Primary on-call", "Backup coverage", None]),
                "now": now,
            })
        print(f"    Created 8 oncall_schedules")
        await session.commit()

    if shift_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM callout_coverage_requests"))
        if r.scalar() == 0:
            print("  Seeding callout_coverage_requests...")
            callouts = [
                ("Flu — will not be in", "covered", "medium"),
                ("Car trouble", "covered", "high"),
                ("Family emergency", "uncovered", "emergency"),
                ("Personal day needed", "covered", "low"),
                ("Weather — roads impassable", "partial", "high"),
            ]
            for reason, status, urgency in callouts:
                callout_staff = random.choice(staff_ids)
                sdate = _past_date(random.randint(1, 30))
                await session.execute(text("""
                    INSERT INTO callout_coverage_requests (branch_id, original_shift_id,
                        callout_staff_id, callout_reason, callout_time, shift_date,
                        shift_start, shift_end, status, urgency, staff_contacted_count,
                        auto_match_attempted, covering_staff_id, resolved_at,
                        handled_by_id, created_at, updated_at)
                    VALUES (:bid, :shift, :staff, :reason, :callout_time, :sdate,
                        :start, :end, :status, :urgency, :contacted, :auto,
                        :cover, :resolved, :handler, :now, :now)
                """), {
                    "bid": random.choice(branch_ids),
                    "shift": random.choice(shift_ids),
                    "staff": callout_staff,
                    "reason": reason,
                    "callout_time": _past(random.randint(1, 30)),
                    "sdate": sdate,
                    "start": time(8, 0), "end": time(16, 0),
                    "status": status, "urgency": urgency,
                    "contacted": random.randint(2, 6),
                    "auto": True,
                    "cover": random.choice([s for s in staff_ids if s != callout_staff]) if status == "covered" else None,
                    "resolved": _past(random.randint(0, 29)) if status in ("covered", "partial") else None,
                    "handler": random.choice(admin_ids or staff_ids),
                    "now": now,
                })
            print(f"    Created {len(callouts)} callout_coverage_requests")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 13. SCHEDULE GENERATIONS + BALANCE METRICS + EXPLANATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM schedule_generations"))
    if r.scalar() == 0:
        print("  Seeding schedule_generations...")
        gen_ids = []
        for i in range(4):
            start_d = _past_date(28 * (4 - i))
            end_d = start_d + timedelta(days=14)
            gen_by = random.choice(admin_ids or staff_ids)
            r2 = await session.execute(text("""
                INSERT INTO schedule_generations (branch_id, generated_by_id, period_start, period_end,
                    status, objective_value, solve_time_seconds, total_shifts_assigned, total_violations,
                    fairness_score, is_published, published_at, published_by_id, created_at, updated_at)
                VALUES (:bid, :gen_by, :start, :end, :status, :obj, :solve_time, :shifts, :violations,
                    :fairness, :pub, :pub_at, :pub_by, :now, :now)
                RETURNING id
            """), {
                "bid": random.choice(branch_ids), "gen_by": gen_by,
                "start": start_d, "end": end_d,
                "status": "optimal" if i < 3 else "feasible",
                "obj": round(random.uniform(85, 98), 2),
                "solve_time": round(random.uniform(2, 15), 1),
                "shifts": random.randint(40, 80), "violations": random.randint(0, 3),
                "fairness": round(random.uniform(0.85, 0.99), 3),
                "pub": i < 3,
                "pub_at": _past(28 * (3 - i)) if i < 3 else None,
                "pub_by": gen_by if i < 3 else None,
                "now": now,
            })
            gen_ids.append(r2.scalar())
        print(f"    Created {len(gen_ids)} schedule_generations")
        await session.commit()

        # schedule_balance_metrics
        print("  Seeding schedule_balance_metrics...")
        used_metrics = set()
        met_count = 0
        for sid in random.sample(staff_ids, min(len(staff_ids), 10)):
            bid = random.choice(branch_ids)
            start_d = _past_date(28)
            end_d = start_d + timedelta(days=14)
            key = (sid, bid, start_d, end_d)
            if key not in used_metrics:
                used_metrics.add(key)
                await session.execute(text("""
                    INSERT INTO schedule_balance_metrics (staff_id, branch_id, period_start, period_end,
                        total_hours_scheduled, total_hours_worked, total_overtime_hours,
                        opening_shifts, closing_shifts, midday_shifts, evening_shifts,
                        weekend_shifts, holiday_shifts, max_consecutive_days_worked,
                        min_consecutive_days_off, clopening_count,
                        hours_fairness_score, shift_type_fairness_score,
                        weekend_fairness_score, holiday_fairness_score,
                        overall_fairness_score, hours_vs_average, calculated_at)
                    VALUES (:sid, :bid, :start, :end, :sched, :worked, :ot,
                        :open, :close, :mid, :eve, :wknd, :hol, :consec, :off, :clop,
                        :h_fair, :st_fair, :w_fair, :hol_fair, :overall, :vs_avg, :calc)
                """), {
                    "sid": sid, "bid": bid, "start": start_d, "end": end_d,
                    "sched": round(random.uniform(60, 80), 1),
                    "worked": round(random.uniform(58, 82), 1),
                    "ot": round(random.uniform(0, 4), 1),
                    "open": random.randint(2, 5), "close": random.randint(1, 4),
                    "mid": random.randint(3, 6), "eve": random.randint(0, 3),
                    "wknd": random.randint(1, 3), "hol": 0,
                    "consec": random.randint(3, 6), "off": random.randint(1, 3),
                    "clop": random.randint(0, 1),
                    "h_fair": round(random.uniform(0.8, 1.0), 3),
                    "st_fair": round(random.uniform(0.8, 1.0), 3),
                    "w_fair": round(random.uniform(0.7, 1.0), 3),
                    "hol_fair": round(random.uniform(0.9, 1.0), 3),
                    "overall": round(random.uniform(0.85, 0.99), 3),
                    "vs_avg": round(random.uniform(-5, 5), 1),
                    "calc": now,
                })
                met_count += 1
        print(f"    Created {met_count} schedule_balance_metrics")
        await session.commit()

        # schedule_explanations
        if gen_ids and shift_ids:
            print("  Seeding schedule_explanations...")
            exp_count = 0
            for gid in gen_ids[:2]:
                for _ in range(4):
                    await session.execute(text("""
                        INSERT INTO schedule_explanations (generation_id, shift_id, staff_id,
                            explanation_type, explanation_text, fairness_impact)
                        VALUES (:gid, :shift, :staff, :etype, :etext, :impact)
                    """), {
                        "gid": gid, "shift": random.choice(shift_ids),
                        "staff": random.choice(staff_ids),
                        "etype": random.choice(["preference_honored", "coverage_required", "fairness_balance", "availability"]),
                        "etext": random.choice([
                            "Assigned per staff preference for morning shifts",
                            "Coverage needed — minimum staffing requirement",
                            "Balanced weekend shift distribution",
                            "Only available staff member for this slot",
                        ]),
                        "impact": round(random.uniform(-0.1, 0.1), 3),
                    })
                    exp_count += 1
            print(f"    Created {exp_count} schedule_explanations")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 14. AVAILABILITY PREFERENCES (volunteers)
    # ════════════════════════════════════════════════════════════════
    if volunteer_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM availability_preferences"))
        if r.scalar() == 0:
            print("  Seeding availability_preferences...")
            count = 0
            for vid in volunteer_ids[:10]:
                days = random.sample(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"], random.randint(2, 4))
                days_lit = "'{" + ",".join(days) + "}'::varchar[]"
                loc = random.choice(["Main Branch", "Elmdale Branch", "Jamie Chick Community Annex"])
                locs_lit = "'{" + loc + "}'::varchar[]"
                await session.execute(text(f"""
                    INSERT INTO availability_preferences (volunteer_id, availability_type,
                        available_days, available_time_start, available_time_end,
                        max_hours_per_week, min_hours_per_session,
                        preferred_locations, willing_to_travel,
                        prefers_recurring_shifts, prefers_flexible_shifts)
                    VALUES (:vid, :atype, {days_lit}, :start, :end, :max_h, :min_h,
                        {locs_lit}, :travel, :recurring, :flexible)
                """), {
                    "vid": vid,
                    "atype": random.choice(["specific_days", "flexible", "weekday_only", "weekend_only"]),
                    "start": str(random.choice(["09:00", "10:00", "12:00"])),
                    "end": str(random.choice(["15:00", "17:00", "20:00"])),
                    "max_h": random.randint(8, 20),
                    "min_h": random.choice([1.0, 1.5, 2.0]),
                    "travel": random.choice([True, False]),
                    "recurring": random.choice([True, False]),
                    "flexible": random.choice([True, False]),
                })
                count += 1
            print(f"    Created {count} availability_preferences")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 15. PTO EXTRAS (approvals, conflicts, coverage, recurrences,
    #     reminders, status_history, vacation_celebrations)
    # ════════════════════════════════════════════════════════════════
    if pto_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM pto_approvals"))
        if r.scalar() == 0:
            print("  Seeding pto_approvals...")
            for pid in pto_ids[:5]:
                await session.execute(text("""
                    INSERT INTO pto_approvals (pto_request_id, approver_id, status, notes, coverage_assessment)
                    VALUES (:pid, :approver, :status, :notes, :coverage)
                """), {
                    "pid": pid,
                    "approver": random.choice(admin_ids or staff_ids),
                    "status": random.choice(["approved", "approved", "approved", "denied"]),
                    "notes": random.choice(["Approved — enjoy your time off!", "Coverage confirmed", None]),
                    "coverage": random.choice(["Adequate staffing available", "Partial coverage arranged", None]),
                })
            print(f"    Created {min(5, len(pto_ids))} pto_approvals")
            await session.commit()

        r = await session.execute(text("SELECT COUNT(*) FROM pto_conflicts"))
        if r.scalar() == 0:
            print("  Seeding pto_conflicts...")
            for pid in pto_ids[:3]:
                await session.execute(text("""
                    INSERT INTO pto_conflicts (pto_request_id, conflict_type, conflict_description,
                        is_resolved, detected_at)
                    VALUES (:pid, :ctype, :desc, :resolved, :detected)
                """), {
                    "pid": pid,
                    "ctype": random.choice(["overlap", "minimum_staffing", "blackout_date"]),
                    "desc": random.choice([
                        "Overlaps with another staff member's approved PTO",
                        "Would bring branch below minimum staffing",
                        "Requested date falls during summer reading program",
                    ]),
                    "resolved": random.choice([True, True, False]),
                    "detected": _past(random.randint(5, 30)),
                })
            print(f"    Created {min(3, len(pto_ids))} pto_conflicts")
            await session.commit()

        r = await session.execute(text("SELECT COUNT(*) FROM pto_coverage"))
        if r.scalar() == 0:
            print("  Seeding pto_coverage...")
            for pid in pto_ids[:4]:
                cover_user = random.choice(staff_ids)
                await session.execute(text("""
                    INSERT INTO pto_coverage (pto_request_id, coverage_user_id, coverage_status,
                        coverage_notes, assigned_at)
                    VALUES (:pid, :cover, :status, :notes, :assigned)
                """), {
                    "pid": pid, "cover": cover_user,
                    "status": random.choice(["accepted", "accepted", "pending"]),
                    "notes": "Will cover circulation desk duties",
                    "assigned": _past(random.randint(5, 20)),
                })
            print(f"    Created {min(4, len(pto_ids))} pto_coverage")
            await session.commit()

        r = await session.execute(text("SELECT COUNT(*) FROM pto_recurrences"))
        if r.scalar() == 0:
            print("  Seeding pto_recurrences...")
            for pid in pto_ids[:2]:
                await session.execute(text("""
                    INSERT INTO pto_recurrences (pto_request_id, recurrence_rule, start_date,
                        end_date, next_occurrence_date, is_active, created_at, updated_at)
                    VALUES (:pid, :rule, :start, :end, :next, true, :now, :now)
                """), {
                    "pid": pid,
                    "rule": random.choice(["FREQ=WEEKLY;BYDAY=FR", "FREQ=MONTHLY;BYMONTHDAY=15"]),
                    "start": _past_date(60),
                    "end": _future_date(120),
                    "next": _future_date(random.randint(1, 14)),
                    "now": now,
                })
            print(f"    Created {min(2, len(pto_ids))} pto_recurrences")
            await session.commit()

        r = await session.execute(text("SELECT COUNT(*) FROM pto_status_history"))
        if r.scalar() == 0:
            print("  Seeding pto_status_history...")
            count = 0
            for pid in pto_ids[:5]:
                for old_s, new_s in [("draft", "submitted"), ("submitted", "approved")]:
                    await session.execute(text("""
                        INSERT INTO pto_status_history (pto_request_id, old_status, new_status,
                            changed_by_id, change_reason, changed_at)
                        VALUES (:pid, :old, :new, :by, :reason, :at)
                    """), {
                        "pid": pid, "old": old_s, "new": new_s,
                        "by": random.choice(admin_ids or staff_ids),
                        "reason": None,
                        "at": _past(random.randint(5, 30)),
                    })
                    count += 1
            print(f"    Created {count} pto_status_history records")
            await session.commit()

        r = await session.execute(text("SELECT COUNT(*) FROM pto_vacation_celebrations"))
        if r.scalar() == 0:
            print("  Seeding pto_vacation_celebrations...")
            for pid in pto_ids[:3]:
                await session.execute(text("""
                    INSERT INTO pto_vacation_celebrations (pto_request_id, celebration_message,
                        celebration_sent_at, team_notified, welcome_back_message)
                    VALUES (:pid, :msg, :sent, :notified, :welcome)
                """), {
                    "pid": pid,
                    "msg": random.choice([
                        "Have an amazing vacation! You deserve it!",
                        "Enjoy your time off! We've got things covered.",
                        "Bon voyage! See you when you get back!",
                    ]),
                    "sent": _past(random.randint(3, 20)).replace(tzinfo=None),
                    "notified": True,
                    "welcome": random.choice(["Welcome back! Hope you had a great time!", None]),
                })
            print(f"    Created {min(3, len(pto_ids))} pto_vacation_celebrations")
            await session.commit()

    # pto_reminders (no FK to pto_requests directly, uses user_id)
    r = await session.execute(text("SELECT COUNT(*) FROM pto_reminders"))
    if r.scalar() == 0:
        print("  Seeding pto_reminders...")
        count = 0
        for sid in random.sample(staff_ids, min(len(staff_ids), 8)):
            await session.execute(text("""
                INSERT INTO pto_reminders (user_id, pto_type, days_available, reminder_type,
                    message, sent_at)
                VALUES (:uid, :ptype, :days, :rtype, :msg, :sent)
            """), {
                "uid": sid,
                "ptype": random.choice(["vacation", "sick", "personal"]),
                "days": round(random.uniform(3, 15), 1),
                "rtype": random.choice(["use_it_or_lose_it", "low_balance", "quarterly_reminder"]),
                "msg": random.choice([
                    "You have unused vacation days expiring at year end!",
                    "Your sick leave balance is getting low.",
                    "Quarterly reminder: you have PTO available to use.",
                ]),
                "sent": _past(random.randint(1, 30)),
            })
            count += 1
        print(f"    Created {count} pto_reminders")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 16. PAYROLL RECORDS + EXPORT BATCHES
    # ════════════════════════════════════════════════════════════════
    if shift_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM payroll_records"))
        if r.scalar() == 0:
            print("  Seeding payroll_records...")
            used_pairs = set()
            count = 0
            for sid in random.sample(staff_ids, min(len(staff_ids), 12)):
                shift = random.choice(shift_ids)
                if (sid, shift) in used_pairs:
                    continue
                used_pairs.add((sid, shift))
                pp_start = _past_date(28)
                pp_end = pp_start + timedelta(days=13)
                reg = round(random.uniform(70, 80), 1)
                ot = round(random.uniform(0, 5), 1)
                await session.execute(text("""
                    INSERT INTO payroll_records (staff_id, shift_id, pay_period_start, pay_period_end,
                        regular_hours, overtime_hours, holiday_hours, weekend_differential_hours,
                        evening_differential_hours, overtime_multiplier, holiday_multiplier,
                        weekend_differential, evening_differential, export_status,
                        scheduled_hours, actual_hours, is_approved, approved_by_id, approved_at,
                        created_at, updated_at)
                    VALUES (:sid, :shift, :start, :end, :reg, :ot, :hol, :wknd, :eve,
                        :ot_mult, :hol_mult, :wknd_diff, :eve_diff, :export,
                        :sched, :actual, :approved, :approver, :approved_at, :now, :now)
                """), {
                    "sid": sid, "shift": shift, "start": pp_start, "end": pp_end,
                    "reg": reg, "ot": ot, "hol": 0.0,
                    "wknd": round(random.uniform(0, 16), 1),
                    "eve": round(random.uniform(0, 8), 1),
                    "ot_mult": 1.5, "hol_mult": 2.0, "wknd_diff": 1.5, "eve_diff": 0.5,
                    "export": random.choice(["pending", "exported", "confirmed"]),
                    "sched": reg, "actual": reg + ot,
                    "approved": True,
                    "approver": random.choice(admin_ids or staff_ids),
                    "approved_at": _past(7),
                    "now": now,
                })
                count += 1
            print(f"    Created {count} payroll_records")
            await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM payroll_export_batches"))
    if r.scalar() == 0:
        print("  Seeding payroll_export_batches...")
        for i in range(3):
            pp_start = _past_date(28 * (3 - i))
            pp_end = pp_start + timedelta(days=13)
            await session.execute(text("""
                INSERT INTO payroll_export_batches (batch_id, branch_id, pay_period_start,
                    pay_period_end, total_records, total_regular_hours, total_overtime_hours,
                    total_holiday_hours, export_status, export_format, exported_at, exported_by_id)
                VALUES (:bid, :branch, :start, :end, :records, :reg, :ot, :hol,
                    :status, :format, :exported, :by)
            """), {
                "bid": f"PAY-2026-{i+1:03d}",
                "branch": random.choice(branch_ids),
                "start": pp_start, "end": pp_end,
                "records": random.randint(15, 30),
                "reg": round(random.uniform(800, 1200), 1),
                "ot": round(random.uniform(10, 40), 1),
                "hol": 0.0,
                "status": "exported",
                "format": "CSV",
                "exported": _past(28 * (3 - i)),
                "by": random.choice(admin_ids or staff_ids),
            })
        print(f"    Created 3 payroll_export_batches")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 17. STAFF FATIGUE + SUPPORT RESOURCES + PREFERENCE PROFILES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_fatigue_records"))
    if r.scalar() == 0:
        print("  Seeding staff_fatigue_records...")
        used = set()
        count = 0
        for sid in random.sample(staff_ids, min(len(staff_ids), 10)):
            for d in range(0, 14, 2):
                rd = _past_date(d)
                if (sid, rd) in used:
                    continue
                used.add((sid, rd))
                score = round(random.uniform(10, 90), 1)
                level = "low" if score < 30 else "moderate" if score < 60 else "high" if score < 80 else "critical"
                await session.execute(text("""
                    INSERT INTO staff_fatigue_records (staff_id, record_date, fatigue_level,
                        fatigue_score, consecutive_days_worked, hours_last_7_days, hours_last_14_days,
                        closing_shifts_last_7_days, short_turnarounds_last_14_days,
                        overtime_hours_last_30_days, days_since_last_day_off,
                        weekend_shifts_last_30_days, fatigue_trend,
                        alert_triggered, alert_message, calculated_at)
                    VALUES (:sid, :rd, :level, :score, :consec, :h7, :h14, :close, :turnaround,
                        :ot, :days_off, :wknd, :trend, :alert, :alert_msg, :calc)
                """), {
                    "sid": sid, "rd": rd, "level": level, "score": score,
                    "consec": random.randint(1, 6),
                    "h7": round(random.uniform(30, 50), 1),
                    "h14": round(random.uniform(60, 100), 1),
                    "close": random.randint(0, 3), "turnaround": random.randint(0, 2),
                    "ot": round(random.uniform(0, 8), 1),
                    "days_off": random.randint(0, 5),
                    "wknd": random.randint(2, 6),
                    "trend": random.choice(["improving", "stable", "worsening"]),
                    "alert": level in ("high", "critical"),
                    "alert_msg": f"Fatigue level is {level}" if level in ("high", "critical") else None,
                    "calc": now,
                })
                count += 1
        print(f"    Created {count} staff_fatigue_records")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM staff_support_resources"))
    if r.scalar() == 0:
        print("  Seeding staff_support_resources...")
        resources = [
            ("Employee Assistance Program", "Free confidential counseling and support services for all staff", "mental_health", "1-800-555-0199", "eap@example.com", "https://eap.example.com", None, "Monday-Friday 8am-8pm", False, True, True, False),
            ("Crisis Text Line", "Text HOME to 741741 for free crisis counseling", "crisis", None, None, "https://www.crisistextline.org", "741741", "24/7", True, True, True, False),
            ("AFSCME Local 3456", "Union resources and representation", "union", "555-0188", "local3456@union.org", None, None, "Monday-Friday 9am-5pm", False, False, True, True),
            ("Library Workers Peer Support", "Confidential peer support network", "peer_support", None, "peersupport@library.example.com", None, None, "Scheduled sessions", False, True, True, False),
            ("Workplace Safety Hotline", "Report safety concerns anonymously", "safety", "1-800-555-0177", None, None, None, "24/7", True, True, True, False),
        ]
        for name, desc, rtype, phone, email, web, txt, hours, is_24_7, anon, active, union in resources:
            await session.execute(text("""
                INSERT INTO staff_support_resources (name, description, resource_type,
                    phone, email, website, text_number, hours, is_available_24_7,
                    is_anonymous, is_active, is_union_resource)
                VALUES (:name, :desc, :rtype, :phone, :email, :web, :txt, :hours,
                    :h24, :anon, :active, :union)
            """), {
                "name": name, "desc": desc, "rtype": rtype, "phone": phone,
                "email": email, "web": web, "txt": txt, "hours": hours,
                "h24": is_24_7, "anon": anon, "active": active, "union": union,
            })
        print(f"    Created {len(resources)} staff_support_resources")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM staff_preference_profiles"))
    if r.scalar() == 0:
        print("  Seeding staff_preference_profiles...")
        count = 0
        for sid in random.sample(staff_ids, min(len(staff_ids), 15)):
            await session.execute(text("""
                INSERT INTO staff_preference_profiles (user_id, wants_extra_hours,
                    preferred_shift_types, preferred_days_of_week, days_available,
                    earliest_available_time, latest_available_time,
                    max_extra_hours_per_week, max_consecutive_days,
                    auto_claim_compatible, notify_on_new_matches, notes)
                VALUES (:uid, :extra,
                    '{"opening","mid_day"}'::varchar[], '{"Monday","Wednesday","Friday"}'::varchar[],
                    '{"Monday","Tuesday","Wednesday","Thursday","Friday"}'::varchar[],
                    :earliest, :latest, :max_extra, :max_consec,
                    :auto, :notify, :notes)
            """), {
                "uid": sid,
                "extra": random.choice([True, False]),
                "earliest": time(7, 0),
                "latest": time(21, 0),
                "max_extra": random.randint(4, 12),
                "max_consec": random.randint(4, 6),
                "auto": random.choice([True, False]),
                "notify": True,
                "notes": random.choice(["Prefer not to close on Fridays", "Available for weekend coverage", None]),
            })
            count += 1
        print(f"    Created {count} staff_preference_profiles")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 18. STAFF ACCESS LOGS + INCIDENT REPORTS + PANIC ALERTS + PROJECTS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_access_logs"))
    if r.scalar() == 0:
        print("  Seeding staff_access_logs...")
        for i in range(20):
            sid = random.choice(staff_ids)
            await session.execute(text("""
                INSERT INTO staff_access_logs (organization_id, staff_id, staff_role, access_type,
                    data_category, resource_type, resource_id, target_patron_id, target_is_minor,
                    justification, endpoint, records_accessed_count, ip_address,
                    is_after_hours, is_bulk_access, is_flagged, accessed_at)
                VALUES (:org, :sid, :role, :atype, :dcat, :rtype, :rid, :patron, :minor,
                    :justification, :endpoint, :records, :ip, :after, :bulk, :flagged, :at)
            """), {
                "org": org_id, "sid": sid,
                "role": random.choice(["staff", "admin"]),
                "atype": random.choice(["view", "search", "modify"]),
                "dcat": random.choice(["patron_pii", "checkout_history", "financial_records", "reading_history"]),
                "rtype": random.choice(["patron_record", "checkout_record", "fine_record"]),
                "rid": str(random.randint(1, 200)),
                "patron": random.choice(patron_ids) if patron_ids else None,
                "minor": random.choice([False, False, False, True]),
                "justification": random.choice(["Patron requested account update", "Processing return", "Fine inquiry", None]),
                "endpoint": random.choice(["/api/patrons/{id}", "/api/checkouts", "/api/fines"]),
                "records": random.randint(1, 5),
                "ip": "10.0.1." + str(random.randint(10, 100)),
                "after": i == 19,
                "bulk": False,
                "flagged": i == 19,
                "at": _past(random.randint(0, 30)),
            })
        print(f"    Created 20 staff_access_logs")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM staff_incident_reports"))
    if r.scalar() == 0:
        print("  Seeding staff_incident_reports...")
        incidents_data = [
            ("safety_concern", "medium", "Wet floor near entrance caused a near-slip", "Main entrance lobby"),
            ("patron_behavior", "high", "Patron became verbally aggressive at circulation desk", "Circulation desk"),
            ("equipment_issue", "low", "Self-checkout kiosk screen flickering", "Self-checkout area"),
            ("safety_concern", "low", "Emergency exit light burned out in community room", "Community Room A"),
            ("harassment", "high", "Staff member reported inappropriate comments from patron", "Reference desk"),
        ]
        inc_ids = []
        for itype, severity, desc, loc in incidents_data:
            r2 = await session.execute(text("""
                INSERT INTO staff_incident_reports (reporting_staff_id, incident_type, incident_date,
                    incident_location, severity, status, description, anonymity_level,
                    is_good_faith, union_notified, is_deleted, data_retention_expires_at)
                VALUES (:reporter, :itype, :idate, :loc, :severity, :status, :desc,
                    :anon, true, :union, false, :expires)
                RETURNING id
            """), {
                "reporter": random.choice(staff_ids),
                "itype": itype, "idate": _past(random.randint(5, 90)),
                "loc": loc, "severity": severity,
                "status": random.choice(["open", "investigating", "resolved"]),
                "desc": desc, "anon": "identified",
                "union": severity == "high",
                "expires": _future(365 * 3),
            })
            inc_ids.append(r2.scalar())
        print(f"    Created {len(incidents_data)} staff_incident_reports")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM staff_panic_alerts"))
    if r.scalar() == 0:
        print("  Seeding staff_panic_alerts...")
        for i in range(3):
            sid = random.choice(staff_ids)
            responder = random.choice([s for s in staff_ids if s != sid])
            await session.execute(text("""
                INSERT INTO staff_panic_alerts (staff_id, activated_at, location, status,
                    responder_id, acknowledged_at, responded_at, resolved_at, response_notes,
                    union_notified, is_deleted, data_retention_expires_at)
                VALUES (:sid, :activated, :loc, :status, :responder, :ack, :responded,
                    :resolved, :notes, :union, false, :expires)
            """), {
                "sid": sid,
                "activated": _past(random.randint(10, 60)),
                "loc": random.choice(["Circulation Desk", "Children's Area", "Parking Lot"]),
                "status": "resolved",
                "responder": responder,
                "ack": _past(random.randint(9, 59)),
                "responded": _past(random.randint(8, 58)),
                "resolved": _past(random.randint(7, 57)),
                "notes": "Situation de-escalated. Staff member is safe.",
                "union": True,
                "expires": _future(365 * 3),
            })
        print(f"    Created 3 staff_panic_alerts")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM staff_projects"))
    if r.scalar() == 0:
        print("  Seeding staff_projects...")
        projects = [
            ("Summer Reading Program 2026", "Plan and execute the annual summer reading program for all ages", "in_progress",
             5000.0, 4500.0, 2100.0, True),
            ("RFID Migration", "Convert barcode system to RFID tags library-wide", "approved",
             12000.0, 12000.0, 0.0, True),
            ("Seed Library Expansion", "Expand the seed library to include native plants section", "completed",
             800.0, 750.0, 680.0, True),
            ("Staff Wellness Initiative", "Monthly wellness activities and resources for staff", "in_progress",
             2000.0, 1500.0, 400.0, False),
            ("Digital Literacy Program", "8-week computer skills course for seniors", "proposed",
             1200.0, None, None, False),
        ]
        for title, desc, status, req, approved, spent, innovation in projects:
            lead = random.choice(staff_ids)
            team = json.dumps(random.sample([s for s in staff_ids if s != lead], min(3, len(staff_ids) - 1)))
            await session.execute(text("""
                INSERT INTO staff_projects (organization_id, title, description, status, lead_id,
                    team_member_ids, budget_requested, budget_approved, budget_spent,
                    is_innovation_project, proposed_start_date, proposed_end_date,
                    approved_by_id, tags)
                VALUES (:org, :title, :desc, :status, :lead, cast(:team as jsonb),
                    :req, :approved, :spent, :innovation, :start, :end, :approver, cast(:tags as jsonb))
            """), {
                "org": org_id, "title": title, "desc": desc, "status": status,
                "lead": lead, "team": team,
                "req": req, "approved": approved, "spent": spent,
                "innovation": innovation,
                "start": _past(random.randint(30, 90)),
                "end": _future(random.randint(30, 180)),
                "approver": random.choice(admin_ids or staff_ids) if status != "proposed" else None,
                "tags": json.dumps(["community", "programming"] if innovation else ["operations"]),
            })
        print(f"    Created {len(projects)} staff_projects")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 19. STAFF MEDICAL TRAINING + PROTECTION MEASURES + STATUS NOTIFICATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM staff_medical_training"))
    if r.scalar() == 0:
        print("  Seeding staff_medical_training...")
        count = 0
        for sid in random.sample(staff_ids, min(len(staff_ids), 12)):
            cpr = random.choice([True, True, False])
            fa = random.choice([True, True, False])
            aed = random.choice([True, False])
            await session.execute(text("""
                INSERT INTO staff_medical_training (staff_id, cpr_certified, cpr_expiration_date,
                    first_aid_certified, first_aid_expiration_date, aed_trained, aed_training_date,
                    available_for_emergency_response, medical_response_notes)
                VALUES (:sid, :cpr, :cpr_exp, :fa, :fa_exp, :aed, :aed_date, :avail, :notes)
            """), {
                "sid": sid, "cpr": cpr,
                "cpr_exp": _future(random.randint(60, 365)) if cpr else None,
                "fa": fa,
                "fa_exp": _future(random.randint(60, 365)) if fa else None,
                "aed": aed,
                "aed_date": _past(random.randint(30, 365)) if aed else None,
                "avail": cpr or fa,
                "notes": "Trained at Red Cross facility" if cpr else None,
            })
            count += 1
        print(f"    Created {count} staff_medical_training records")
        await session.commit()

    # staff_protection_measures needs staff_incident_reports
    inc_r = await session.execute(text("SELECT id FROM staff_incident_reports LIMIT 5"))
    inc_ids = [r[0] for r in inc_r.fetchall()]
    if inc_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM staff_protection_measures"))
        if r.scalar() == 0:
            print("  Seeding staff_protection_measures...")
            measures = [
                ("schedule_change", "Adjusted schedule to avoid contact with problematic patron"),
                ("security_escort", "Security escort to parking lot after evening shifts"),
                ("desk_reassignment", "Moved from public desk to back office temporarily"),
            ]
            for mtype, desc in measures:
                await session.execute(text("""
                    INSERT INTO staff_protection_measures (staff_id, measure_type, description,
                        incident_report_id, effective_date, is_active, approved_by_id)
                    VALUES (:sid, :mtype, :desc, :inc, :eff, true, :approver)
                """), {
                    "sid": random.choice(staff_ids), "mtype": mtype, "desc": desc,
                    "inc": random.choice(inc_ids),
                    "eff": _past(random.randint(5, 30)),
                    "approver": random.choice(admin_ids or staff_ids),
                })
            print(f"    Created {len(measures)} staff_protection_measures")
            await session.commit()

    # staff_status_notifications needs system_status_logs
    ssl_r = await session.execute(text("SELECT id FROM system_status_logs LIMIT 5"))
    ssl_ids = [r[0] for r in ssl_r.fetchall()]
    if ssl_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM staff_status_notifications"))
        if r.scalar() == 0:
            print("  Seeding staff_status_notifications...")
            for ssl_id in ssl_ids[:3]:
                await session.execute(text("""
                    INSERT INTO staff_status_notifications (organization_id, issue_id,
                        notification_type, title, message,
                        patron_talking_points, workaround_instructions)
                    VALUES (:org, :issue, :ntype, :title, :msg, :talking, :workaround)
                """), {
                    "org": org_id, "issue": ssl_id,
                    "ntype": random.choice(["issue_detected", "issue_resolved", "degradation_warning"]),
                    "title": "System Status Update",
                    "msg": "Please be aware of the current system status and use workarounds as needed.",
                    "talking": "If patrons ask, let them know we are working on a fix and service will be restored shortly.",
                    "workaround": "Use manual processes for affected operations until resolved.",
                })
            print(f"    Created {min(3, len(ssl_ids))} staff_status_notifications")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 20. DOCUMENT VERSIONS + REVIEWS + REVIEW CYCLES + AUDIT LOGS
    # ════════════════════════════════════════════════════════════════
    if legal_doc_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM document_versions"))
        if r.scalar() == 0:
            print("  Seeding document_versions...")
            ver_ids = []
            for doc_id in legal_doc_ids:
                for major in [1, 2]:
                    for minor in [0, 1]:
                        ver = f"{major}.{minor}"
                        is_current = (major == 2 and minor == 1)
                        r2 = await session.execute(text("""
                            INSERT INTO document_versions (document_id, version_number,
                                major_version, minor_version, change_summary, is_current,
                                created_at, created_by_id)
                            VALUES (:doc, :ver, :major, :minor, :summary, :current, :created, :by)
                            RETURNING id
                        """), {
                            "doc": doc_id, "ver": ver, "major": major, "minor": minor,
                            "summary": f"Version {ver} — {'Initial release' if ver == '1.0' else 'Updates and corrections'}",
                            "current": is_current,
                            "created": _past(365 - (major * 180 + minor * 30)),
                            "by": random.choice(admin_ids or staff_ids),
                        })
                        ver_ids.append(r2.scalar())
            print(f"    Created {len(ver_ids)} document_versions")
            await session.commit()

        # document_review_cycles
        r = await session.execute(text("SELECT COUNT(*) FROM document_review_cycles"))
        if r.scalar() == 0:
            print("  Seeding document_review_cycles...")
            cycle_ids = []
            for doc_id in legal_doc_ids:
                r2 = await session.execute(text("""
                    INSERT INTO document_review_cycles (document_id, review_frequency,
                        scheduled_date, due_date, status, assigned_to_id,
                        reminder_sent, created_at, created_by_id)
                    VALUES (:doc, :freq, :sched, :due, :status, :assigned,
                        :reminded, :now, :by)
                    RETURNING id
                """), {
                    "doc": doc_id,
                    "freq": random.choice(["annual", "biannual", "triennial"]),
                    "sched": _future_date(random.randint(30, 180)),
                    "due": _future_date(random.randint(60, 210)),
                    "status": random.choice(["pending", "in_progress"]),
                    "assigned": random.choice(admin_ids or staff_ids),
                    "reminded": False,
                    "now": now,
                    "by": random.choice(admin_ids or staff_ids),
                })
                cycle_ids.append(r2.scalar())
            print(f"    Created {len(cycle_ids)} document_review_cycles")
            await session.commit()

            # document_reviews
            r = await session.execute(text("SELECT COUNT(*) FROM document_reviews"))
            if r.scalar() == 0 and cycle_ids:
                print("  Seeding document_reviews...")
                for cid in cycle_ids:
                    await session.execute(text("""
                        INSERT INTO document_reviews (review_cycle_id, reviewer_id, review_date,
                            status, findings, recommendations, requires_update,
                            legal_accuracy_rating, clarity_rating, completeness_rating,
                            approved, created_at)
                        VALUES (:cid, :reviewer, :rdate, :status, :findings, :recs, :update,
                            :legal, :clarity, :complete, :approved, :now)
                    """), {
                        "cid": cid,
                        "reviewer": random.choice(admin_ids or staff_ids),
                        "rdate": _past_date(random.randint(5, 30)),
                        "status": random.choice(["approved", "pending", "flagged"]),
                        "findings": "Document is current and accurate",
                        "recs": "Minor formatting updates recommended",
                        "update": random.choice([True, False]),
                        "legal": random.randint(4, 5), "clarity": random.randint(3, 5),
                        "complete": random.randint(4, 5),
                        "approved": True, "now": now,
                    })
                print(f"    Created {len(cycle_ids)} document_reviews")
                await session.commit()

        # document_audit_logs
        r = await session.execute(text("SELECT COUNT(*) FROM document_audit_logs"))
        if r.scalar() == 0:
            print("  Seeding document_audit_logs...")
            events = [
                ("created", "Document created"),
                ("published", "Document published"),
                ("updated", "Document content updated"),
                ("reviewed", "Annual review completed"),
                ("version_created", "New version 2.1 created"),
            ]
            for doc_id in legal_doc_ids[:3]:
                for etype, edesc in events:
                    await session.execute(text("""
                        INSERT INTO document_audit_logs (document_id, event_type, event_description,
                            user_id, user_role, created_at)
                        VALUES (:doc, :etype, :edesc, :uid, :role, :created)
                    """), {
                        "doc": doc_id, "etype": etype, "edesc": edesc,
                        "uid": random.choice(admin_ids or staff_ids),
                        "role": "admin",
                        "created": _past(random.randint(1, 365)),
                    })
            print(f"    Created {len(legal_doc_ids[:3]) * len(events)} document_audit_logs")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 21. LIBRARY DOCUMENTS + CHUNKS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM library_documents"))
    if r.scalar() == 0:
        print("  Seeding library_documents...")
        lib_docs = [
            ("Staff Handbook 2026", "handbook", "Complete staff handbook with policies and procedures",
             "This handbook outlines all policies, procedures, and expectations for library staff members. It covers scheduling, patron services, emergency protocols, and professional development opportunities."),
            ("Collection Development Plan", "policy", "Strategic plan for collection growth and weeding",
             "This plan outlines selection criteria, budget allocation, weeding schedules, and community-driven collection priorities for fiscal year 2026."),
            ("Emergency Procedures Guide", "procedure", "Step-by-step emergency response procedures",
             "Detailed procedures for fire, severe weather, medical emergency, active threat, and building evacuation scenarios."),
            ("Annual Report 2025", "report", "Annual statistical and narrative report to the state",
             "Summary of library usage statistics, program outcomes, financial data, and community impact for calendar year 2025."),
        ]
        doc_ids_created = []
        for title, dtype, desc, full_text in lib_docs:
            words = len(full_text.split())
            chunks = max(1, words // 50)
            r2 = await session.execute(text("""
                INSERT INTO library_documents (title, document_type, description, full_text,
                    chunk_count, uploaded_by_id, created_at, updated_at)
                VALUES (:title, :dtype, :desc, :text, :chunks, :by, :now, :now)
                RETURNING id
            """), {
                "title": title, "dtype": dtype, "desc": desc, "text": full_text,
                "chunks": chunks,
                "by": random.choice(admin_ids or staff_ids),
                "now": now,
            })
            doc_ids_created.append(r2.scalar())
        print(f"    Created {len(lib_docs)} library_documents")
        await session.commit()

        # library_document_chunks
        if doc_ids_created:
            print("  Seeding library_document_chunks...")
            chunk_count = 0
            for doc_id in doc_ids_created:
                for ci in range(3):
                    text_chunk = f"This is chunk {ci + 1} of the document. It contains relevant content for search and retrieval purposes."
                    await session.execute(text("""
                        INSERT INTO library_document_chunks (document_id, chunk_index,
                            section_title, chunk_text, word_count, created_at)
                        VALUES (:doc, :idx, :section, :text, :words, :now)
                    """), {
                        "doc": doc_id, "idx": ci,
                        "section": f"Section {ci + 1}",
                        "text": text_chunk,
                        "words": len(text_chunk.split()),
                        "now": now,
                    })
                    chunk_count += 1
            print(f"    Created {chunk_count} library_document_chunks")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 22. BACKGROUND CHECKS
    # ════════════════════════════════════════════════════════════════
    if volunteer_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM background_checks"))
        if r.scalar() == 0:
            print("  Seeding background_checks...")
            count = 0
            for vid in volunteer_ids[:10]:
                status = random.choice(["clear", "clear", "clear", "in_progress", "expired"])
                await session.execute(text("""
                    INSERT INTO background_checks (volunteer_id, status, check_type,
                        initiated_at, completed_at, expires_at, provider_name,
                        result_summary, issues_found, approved_by_id, approved_at)
                    VALUES (:vid, :status, :ctype, :init, :completed, :expires, :provider,
                        :result, '{}'::varchar[], :approver, :approved_at)
                """), {
                    "vid": vid, "status": status,
                    "ctype": "standard",
                    "init": _past(random.randint(90, 365)),
                    "completed": _past(random.randint(80, 355)) if status != "in_progress" else None,
                    "expires": _future_date(random.randint(30, 365)) if status == "clear" else _past_date(30) if status == "expired" else None,
                    "provider": "National Background Check Inc.",
                    "result": "Clear" if status == "clear" else None,
                    "approver": random.choice(admin_ids or staff_ids) if status == "clear" else None,
                    "approved_at": _past(random.randint(79, 354)) if status == "clear" else None,
                })
                count += 1
            print(f"    Created {count} background_checks")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 23. BAN REPORTS + BAN ALERT NOTIFICATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM ban_reports"))
    if r.scalar() == 0:
        print("  Seeding ban_reports...")
        bans = [
            ("978-0-06-112008-4", "To Kill a Mockingbird", "Harper Lee", "TX", "challenged", "racial language", "pen_america"),
            ("978-0-14-028329-7", "The Color Purple", "Alice Walker", "FL", "banned", "sexual content", "ala"),
            ("978-0-06-093546-7", "To Kill a Mockingbird", "Harper Lee", "SC", "restricted", "racial themes", "news"),
            ("978-0-385-33348-1", "Beloved", "Toni Morrison", "VA", "challenged", "violence, sexual content", "pen_america"),
            ("978-0-06-440055-8", "Charlotte's Web", "E.B. White", "KS", "challenged", "talking animals", "staff_entry"),
        ]
        ban_ids = []
        for isbn, title, author, state, btype, reason, source in bans:
            cat_match = random.choice(catalog_ids) if catalog_ids else None
            r2 = await session.execute(text("""
                INSERT INTO ban_reports (isbn, title, author, state, ban_type, reason,
                    source, date_reported, catalog_match_id, created_by_id, created_at, updated_at)
                VALUES (:isbn, :title, :author, :state, :btype, :reason,
                    :source, :reported, :match, :by, :now, :now)
                RETURNING id
            """), {
                "isbn": isbn, "title": title, "author": author, "state": state,
                "btype": btype, "reason": reason, "source": source,
                "reported": _past_date(random.randint(30, 365)),
                "match": cat_match,
                "by": random.choice(admin_ids or staff_ids),
                "now": now,
            })
            ban_ids.append(r2.scalar())
        print(f"    Created {len(bans)} ban_reports")
        await session.commit()

        # ban_alert_notifications
        if ban_ids:
            print("  Seeding ban_alert_notifications...")
            count = 0
            for bid in ban_ids[:3]:
                for uid in random.sample(staff_ids, min(len(staff_ids), 3)):
                    await session.execute(text("""
                        INSERT INTO ban_alert_notifications (ban_report_id, user_id, seen_at, created_at, updated_at)
                        VALUES (:bid, :uid, :seen, :now, :now)
                    """), {
                        "bid": bid, "uid": uid,
                        "seen": _past(random.randint(0, 5)) if random.random() > 0.3 else None,
                        "now": now,
                    })
                    count += 1
            print(f"    Created {count} ban_alert_notifications")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 24. CONSENT RECORDS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM consent_records"))
    if r.scalar() == 0:
        print("  Seeding consent_records...")
        count = 0
        for uid in random.sample(all_ids, min(len(all_ids), 30)):
            for ctype in random.sample(["account_creation", "reading_history_tracking", "email_notifications", "data_analytics"], random.randint(1, 3)):
                await session.execute(text("""
                    INSERT INTO consent_records (user_id, consent_type, status, method,
                        policy_version, ip_address, created_at)
                    VALUES (:uid, :ctype, :status, :method, :ver, :ip, :created)
                """), {
                    "uid": uid, "ctype": ctype,
                    "status": "granted",
                    "method": random.choice(["web_form", "in_person", "implicit_account_creation"]),
                    "ver": "1.0",
                    "ip": "10.0.1." + str(random.randint(10, 200)),
                    "created": _past(random.randint(1, 365)),
                })
                count += 1
        print(f"    Created {count} consent_records")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 25. MODERATION ALERTS + CONTENT FLAGS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM moderation_alerts"))
    if r.scalar() == 0:
        print("  Seeding moderation_alerts...")
        alerts = [
            ("review_queue", "medium", 5, 2, "Review queue has 5 pending items"),
            ("flagged_content", "high", 3, 1, "Flagged content requires immediate review"),
            ("spam_detection", "low", 2, 0, "Potential spam reviews detected"),
            ("overdue_moderation", "high", 0, 4, "4 items overdue for moderation review"),
        ]
        for atype, severity, pending, overdue, desc in alerts:
            await session.execute(text("""
                INSERT INTO moderation_alerts (alert_type, severity, pending_count, overdue_count,
                    description, is_resolved, triggered_at, updated_at)
                VALUES (:atype, :severity, :pending, :overdue, :desc, :resolved, :triggered, :now)
            """), {
                "atype": atype, "severity": severity, "pending": pending,
                "overdue": overdue, "desc": desc,
                "resolved": random.choice([True, False]),
                "triggered": _past(random.randint(1, 14)),
                "now": now,
            })
        print(f"    Created {len(alerts)} moderation_alerts")
        await session.commit()

    # content_flags — skipped (no review data to reference)

    # ════════════════════════════════════════════════════════════════
    # 26. PASSWORD HISTORY + PHONE VERIFICATIONS
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM password_history"))
    if r.scalar() == 0:
        print("  Seeding password_history...")
        count = 0
        for uid in random.sample(staff_ids, min(len(staff_ids), 10)):
            for i in range(random.randint(1, 3)):
                await session.execute(text("""
                    INSERT INTO password_history (user_id, password_hash, created_at)
                    VALUES (:uid, :hash, :created)
                """), {
                    "uid": uid,
                    "hash": f"$2b$12${'x' * 53}",  # Placeholder hash
                    "created": _past(random.randint(30, 365) + i * 90),
                })
                count += 1
        print(f"    Created {count} password_history records")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM phone_verifications"))
    if r.scalar() == 0:
        print("  Seeding phone_verifications...")
        count = 0
        for uid in random.sample(all_ids, min(len(all_ids), 15)):
            await session.execute(text("""
                INSERT INTO phone_verifications (user_id, phone_number, verification_code_hash,
                    attempts, max_attempts, expires_at, verified_at, is_verified)
                VALUES (:uid, :phone, :hash, :attempts, :max, :expires, :verified, :is_v)
            """), {
                "uid": uid,
                "phone": f"555-01{random.randint(10, 99)}-{random.randint(1000, 9999)}",
                "hash": f"$2b$12${'y' * 53}",
                "attempts": random.randint(1, 3),
                "max": 5,
                "expires": _future(1),
                "verified": _past(random.randint(1, 90)) if random.random() > 0.2 else None,
                "is_v": random.random() > 0.2,
            })
            count += 1
        print(f"    Created {count} phone_verifications")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 27. INTERNET POLICY ACCEPTANCES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM internet_policy_acceptances"))
    if r.scalar() == 0:
        print("  Seeding internet_policy_acceptances...")
        count = 0
        for _ in range(25):
            uid = random.choice(all_ids)
            await session.execute(text("""
                INSERT INTO internet_policy_acceptances (patron_id, session_id, policy_type,
                    policy_version, is_minor, patron_type, accepted_at, ip_address,
                    workstation_id, branch_location)
                VALUES (:uid, :session, :ptype, :ver, :minor, :ptype2, :accepted, :ip, :ws, :branch)
            """), {
                "uid": uid,
                "session": f"sess-{random.randint(100000, 999999)}",
                "ptype": random.choice(["internet_use", "computer_lab", "wifi_access"]),
                "ver": "2.0",
                "minor": uid in patron_ids and random.random() > 0.7,
                "ptype2": random.choice(["adult", "teen", "child"]),
                "accepted": _past(random.randint(0, 90)),
                "ip": "10.0.1." + str(random.randint(10, 200)),
                "ws": random.choice(["WS-01", "WS-02", "WS-03", "WS-04", "WS-05", None]),
                "branch": random.choice(["Main Branch", "Elmdale Branch", "Jamie Chick Community Annex"]),
            })
            count += 1
        print(f"    Created {count} internet_policy_acceptances")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 28. INTEREST CATEGORIES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM interest_categories"))
    if r.scalar() == 0:
        print("  Seeding interest_categories...")
        categories = [
            ("Fiction", "fiction", "Novels, short stories, and literary fiction", "book-open", "#3B82F6", None, "800", "899", 1),
            ("Mystery & Thriller", "mystery-thriller", "Crime fiction, detective stories, and thrillers", "search", "#EF4444", None, "813", "813", 2),
            ("Science Fiction", "science-fiction", "Sci-fi, speculative fiction, and dystopian", "rocket", "#8B5CF6", None, "813", "813", 3),
            ("Romance", "romance", "Contemporary and historical romance", "heart", "#EC4899", None, "813", "813", 4),
            ("History", "history", "World and American history", "clock", "#F59E0B", None, "900", "999", 5),
            ("Science & Nature", "science-nature", "Biology, physics, astronomy, environment", "leaf", "#10B981", None, "500", "599", 6),
            ("Biography", "biography", "Autobiographies and biographies", "user", "#6366F1", None, "920", "929", 7),
            ("Children's Books", "childrens", "Picture books, early readers, and chapter books", "baby", "#F97316", None, None, None, 8),
            ("Young Adult", "young-adult", "Teen fiction and nonfiction", "zap", "#14B8A6", None, None, None, 9),
            ("Cooking & Food", "cooking-food", "Cookbooks, food culture, and nutrition", "utensils", "#84CC16", None, "641", "641", 10),
            ("Gardening", "gardening", "Home gardening, landscaping, and botany", "flower", "#059669", None, "635", "635", 11),
            ("Technology", "technology", "Computers, programming, and digital literacy", "monitor", "#64748B", None, "004", "006", 12),
        ]
        for name, slug, desc, icon, color, parent, dstart, dend, order in categories:
            await session.execute(text("""
                INSERT INTO interest_categories (name, slug, description, icon, color,
                    parent_id, dewey_range_start, dewey_range_end, is_active, display_order)
                VALUES (:name, :slug, :desc, :icon, :color, :parent, :dstart, :dend, true, :order)
            """), {
                "name": name, "slug": slug, "desc": desc, "icon": icon,
                "color": color, "parent": parent, "dstart": dstart, "dend": dend,
                "order": order,
            })
        print(f"    Created {len(categories)} interest_categories")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 29. POSITIVITY ENTRIES + BRIGHT SPOTS + APPRECIATION RECORDS + THANK YOU MESSAGES
    # ════════════════════════════════════════════════════════════════
    r = await session.execute(text("SELECT COUNT(*) FROM positivity_entries"))
    if r.scalar() == 0:
        print("  Seeding positivity_entries...")
        entries = [
            ("patron_compliment", "A patron told me the library is the best part of their week. Made my day!", "patron", "Mrs. Johnson"),
            ("community_feedback", "The school principal called to thank us for the summer reading partnership.", "patron", None),
            ("staff_recognition", "Angela stayed late to help a patron with a complex genealogy research question.", "staff", None),
            ("bright_moment", "A child who struggled with reading all year just finished their first chapter book!", "staff", None),
            ("patron_compliment", "A teen said our makerspace changed their career plans — they want to study engineering now.", "patron", "Alex T."),
            ("community_feedback", "The food bank sent a thank-you note for hosting their winter clothing drive.", "patron", None),
            ("staff_recognition", "Tom noticed a confused elderly patron and walked them through the self-checkout step by step.", "staff", None),
            ("bright_moment", "Our storytime attendance hit an all-time high — 47 kids and parents!", "staff", None),
        ]
        for etype, txt, source, patron_name in entries:
            await session.execute(text("""
                INSERT INTO positivity_entries (organization_id, user_id, entry_type, text, source,
                    patron_name, flagged_for_advocacy, moderation_status, created_at, updated_at)
                VALUES (:org, :uid, :etype, :text, :source, :pname, false, 'approved', :created, :created)
            """), {
                "org": org_id, "uid": random.choice(staff_ids),
                "etype": etype, "text": txt, "source": source,
                "pname": patron_name,
                "created": _past(random.randint(1, 60)),
            })
        print(f"    Created {len(entries)} positivity_entries")
        await session.commit()

    r = await session.execute(text("SELECT COUNT(*) FROM bright_spots"))
    if r.scalar() == 0:
        print("  Seeding bright_spots...")
        spots = [
            ("Found a patron's lost wallet and reunited it before they left", "bright_spot", "grateful", "team"),
            ("The look on a kid's face when they got their first library card", "bright_spot", "heartwarming", "organization"),
            ("Ernie the library cat fell asleep on the new arrivals display again", "funny_moment", "funny", "public"),
            ("A patron drew a picture of the library and gave it to the front desk", "kid_drawing", "delightful", "public"),
            ("Local newspaper wrote a feature about our seed library program", "community_love_letter", "inspiring", "organization"),
        ]
        for desc, mtype, mood, vis in spots:
            await session.execute(text("""
                INSERT INTO bright_spots (organization_id, user_id, description, moment_type,
                    mood, visibility, is_featured, created_at)
                VALUES (:org, :uid, :desc, :mtype, :mood, :vis, :featured, :created)
            """), {
                "org": org_id, "uid": random.choice(staff_ids),
                "desc": desc, "mtype": mtype, "mood": mood, "vis": vis,
                "featured": random.choice([True, False]),
                "created": _past(random.randint(1, 90)),
            })
        print(f"    Created {len(spots)} bright_spots")
        await session.commit()

    if volunteer_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM appreciation_records"))
        if r.scalar() == 0:
            print("  Seeding appreciation_records...")
            appreciations = [
                ("thank_you_email", "Thank you for 50 hours of shelving service", "Milestone hours"),
                ("certificate", "Certificate of Appreciation — Summer Reading 2025", "Outstanding volunteer"),
                ("public_recognition", "Recognized at board meeting for community impact", "Board recognition"),
                ("badge", "Tech Helper badge for digital literacy assistance", "Skill badge"),
            ]
            for atype, desc, reason in appreciations:
                await session.execute(text("""
                    INSERT INTO appreciation_records (volunteer_id, appreciation_type, description,
                        reason, given_at, given_by_id, made_public)
                    VALUES (:vid, :atype, :desc, :reason, :given, :by, :public)
                """), {
                    "vid": random.choice(volunteer_ids),
                    "atype": atype, "desc": desc, "reason": reason,
                    "given": _past(random.randint(5, 90)),
                    "by": random.choice(admin_ids or staff_ids),
                    "public": random.choice([True, False]),
                })
            print(f"    Created {len(appreciations)} appreciation_records")
            await session.commit()

    # thank_you_messages needs outreach_partners FK
    if partner_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM thank_you_messages"))
        if r.scalar() == 0:
            print("  Seeding thank_you_messages...")
            messages = [
                ("Thank you for your partnership!", "Thank you for your continued support of library programs. Your contributions make a real difference in our community."),
                ("Summer Reading Partnership", "We appreciate your sponsorship of the Summer Reading Program. Over 200 kids participated thanks to your support."),
                ("Holiday Book Drive", "Thank you for donating 150 books to our holiday book drive. Each one found a happy home!"),
            ]
            for subject, body in messages:
                await session.execute(text("""
                    INSERT INTO thank_you_messages (partner_id, subject, message_body,
                        message_type, sent_date, sent_by_id, received_confirmation)
                    VALUES (:pid, :subject, :body, :mtype, :sent, :by, :confirmed)
                """), {
                    "pid": random.choice(partner_ids),
                    "subject": subject, "body": body,
                    "mtype": "thank_you",
                    "sent": _past_date(random.randint(10, 90)),
                    "by": random.choice(admin_ids or staff_ids),
                    "confirmed": random.choice([True, False]),
                })
            print(f"    Created {len(messages)} thank_you_messages")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 30. (Removed — strain_reviews / review_helpful_votes tables no longer exist)
    # ════════════════════════════════════════════════════════════════

    # ════════════════════════════════════════════════════════════════
    # 31. READING PREFERENCE PROFILES + READING EXPORTS
    # ════════════════════════════════════════════════════════════════
    # reading_preference_profiles FK: homebound_enrollments — skip if empty
    he_r = await session.execute(text("SELECT id FROM homebound_enrollments LIMIT 10"))
    he_ids = [r[0] for r in he_r.fetchall()]
    if he_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM reading_preference_profiles"))
        if r.scalar() == 0:
            print("  Seeding reading_preference_profiles...")
            for eid in he_ids[:5]:
                await session.execute(text("""
                    INSERT INTO reading_preference_profiles (enrollment_id, format_preferences,
                        preferred_genres, excluded_genres, favorite_authors, excluded_authors,
                        fiction_preference, content_rating, interests,
                        prefers_large_print, prefers_audiobooks, notes)
                    VALUES (:eid, '{"large_print","audiobook"}'::varchar[],
                        '{"mystery","romance"}'::varchar[], '{"horror"}'::varchar[],
                        '{"James Patterson","Nora Roberts"}'::varchar[], '{}'::varchar[],
                        :fiction, :rating, '{"cozy_mystery","gardening"}'::varchar[],
                        :large, :audio, :notes)
                """), {
                    "eid": eid,
                    "fiction": round(random.uniform(0.5, 0.9), 2),
                    "rating": "all_ages",
                    "large": random.choice([True, False]),
                    "audio": random.choice([True, False]),
                    "notes": "Prefers lighthearted reads",
                })
            print(f"    Created {min(5, len(he_ids))} reading_preference_profiles")
            await session.commit()
    else:
        print("  Skipping reading_preference_profiles (no homebound_enrollments)")

    r = await session.execute(text("SELECT COUNT(*) FROM reading_exports"))
    if r.scalar() == 0:
        print("  Seeding reading_exports...")
        count = 0
        for uid in random.sample(all_ids, min(len(all_ids), 8)):
            await session.execute(text("""
                INSERT INTO reading_exports (user_id, verification_code, date_from, date_to,
                    teacher_name, school_name, total_minutes, total_sessions, expires_at)
                VALUES (:uid, :code, :from, :to, :teacher, :school, :mins, :sessions, :expires)
            """), {
                "uid": uid,
                "code": f"RX-{random.randint(100000, 999999)}",
                "from": _past_date(90),
                "to": _past_date(1),
                "teacher": random.choice(["Mrs. Thompson", "Mr. Garcia", "Ms. Lee", None]),
                "school": random.choice(["Lincoln Elementary", "Washington Middle School", None]),
                "mins": random.randint(500, 5000),
                "sessions": random.randint(20, 100),
                "expires": _future(30),
            })
            count += 1
        print(f"    Created {count} reading_exports")
        await session.commit()

    # ════════════════════════════════════════════════════════════════
    # 32. HIDDEN GEM SCORES + CROSS FORMAT DISCOVERY
    # ════════════════════════════════════════════════════════════════
    if catalog_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM hidden_gem_scores"))
        if r.scalar() == 0:
            print("  Seeding hidden_gem_scores...")
            used = set()
            count = 0
            for cid in random.sample(catalog_ids, min(len(catalog_ids), 15)):
                key = ("catalog_item", cid)
                if key not in used:
                    used.add(key)
                    gem_score = round(random.uniform(0.1, 1.0), 3)
                    await session.execute(text("""
                        INSERT INTO hidden_gem_scores (entity_type, entity_id, source_collection,
                            title, author, avg_similarity_to_popular, popularity_score,
                            circulation_count, gem_score, last_calculated_at, created_at)
                        VALUES (:etype, :eid, :source, :title, :author, :sim, :pop,
                            :circ, :gem, :calc, :now)
                    """), {
                        "etype": "catalog_item", "eid": cid,
                        "source": random.choice(["general", "indie"]),
                        "title": f"Hidden Gem #{count + 1}",
                        "author": random.choice(["Unknown Author", "Jane Doe", "John Smith"]),
                        "sim": round(random.uniform(0.1, 0.5), 3),
                        "pop": round(random.uniform(0.01, 0.3), 3),
                        "circ": random.randint(1, 10),
                        "gem": gem_score,
                        "calc": now,
                        "now": now,
                    })
                    count += 1
            print(f"    Created {count} hidden_gem_scores")
            await session.commit()

    if work_ids:
        r = await session.execute(text("SELECT COUNT(*) FROM cross_format_discovery"))
        if r.scalar() == 0:
            print("  Seeding cross_format_discovery...")
            count = 0
            for wid in work_ids[:5]:
                slug = f"series-{wid}-{random.randint(1000, 9999)}"
                await session.execute(text("""
                    INSERT INTO cross_format_discovery (primary_work_id, series_name, series_slug,
                        format_counts, available_formats, total_popularity_score, is_trending, last_updated)
                    VALUES (:wid, :name, :slug, cast(:fcounts as jsonb), cast(:formats as jsonb),
                        :pop, :trending, :now)
                """), {
                    "wid": wid,
                    "name": f"Cross-Format Series {count + 1}",
                    "slug": slug,
                    "fcounts": json.dumps({"book": random.randint(1, 5), "ebook": random.randint(0, 3), "audiobook": random.randint(0, 2)}),
                    "formats": json.dumps(["book", "ebook", "audiobook"]),
                    "pop": random.randint(10, 500),
                    "trending": random.choice([True, False]),
                    "now": now,
                })
                count += 1
            print(f"    Created {count} cross_format_discovery records")
            await session.commit()

    # ════════════════════════════════════════════════════════════════
    # FIX SEQUENCES
    # ════════════════════════════════════════════════════════════════
    seq_tables = [
        "system_health", "system_health_metrics", "system_status_logs",
        "system_security_checks", "system_access", "system_access_provisioning",
        "setting_definitions", "setting_overrides",
        "permissions", "role_permissions", "role_settings", "role_required_skills",
        "alert_thresholds",
        "ai_configurations", "ai_guardrails", "ai_model_allowlist", "ai_tools", "ai_usage_limits",
        "proxy_configurations",
        "focus_time_settings", "focus_time_blocks", "focus_time_tracking",
        "focus_time_approvals", "focus_time_overrides",
        "shift_preferences", "shift_signups",
        "shift_swap_listings", "shift_swap_claims", "shift_swap_matches",
        "shift_swap_notifications", "shift_swap_audits",
        "shift_checklist_sessions", "shift_constraint_violations",
        "oncall_schedules", "callout_coverage_requests",
        "schedule_generations", "schedule_balance_metrics", "schedule_explanations",
        "availability_preferences",
        "pto_approvals", "pto_conflicts", "pto_coverage", "pto_recurrences",
        "pto_reminders", "pto_status_history", "pto_vacation_celebrations",
        "payroll_records", "payroll_export_batches",
        "staff_fatigue_records", "staff_support_resources", "staff_preference_profiles",
        "staff_access_logs", "staff_incident_reports", "staff_panic_alerts", "staff_projects",
        "staff_medical_training", "staff_protection_measures", "staff_status_notifications",
        "document_versions", "document_reviews", "document_review_cycles", "document_audit_logs",
        "library_documents", "library_document_chunks",
        "background_checks",
        "ban_reports", "ban_alert_notifications",
        "consent_records",
        "moderation_alerts", "content_flags",
        "password_history", "phone_verifications",
        "internet_policy_acceptances",
        "interest_categories",
        "positivity_entries", "bright_spots", "appreciation_records", "thank_you_messages",
        "reading_preference_profiles", "reading_exports",
        "hidden_gem_scores", "cross_format_discovery",
    ]
    for table in seq_tables:
        try:
            async with session.begin_nested():
                await session.execute(text(
                    f"SELECT setval('{table}_id_seq', COALESCE((SELECT MAX(id) FROM {table}), 0) + 1, false)"
                ))
        except SQLAlchemyError:
            pass
    await session.commit()

    print("  Batch system seeding complete!")
    return True
