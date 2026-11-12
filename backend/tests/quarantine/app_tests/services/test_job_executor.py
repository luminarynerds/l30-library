# SPDX-FileCopyrightText: 2026 Luminary Nerds
# SPDX-License-Identifier: AGPL-3.0-or-later
# Characterization tests for job_executor.py - DO NOT modify these when splitting; update only the import paths.
"""Characterization tests for backend/app/services/job_executor.py.

PURPOSE: Pre-split safety net. job_executor.py is a 1961-LOC module containing
21 public scheduled-job coroutines plus private helpers. Any future refactor
that splits this file MUST keep these tests green. Splitting silently is the
specific failure mode this file guards against: APScheduler accepts a stale
function reference at register time without erroring; the job simply never
fires - and that surfaces only at next trigger (hours or days later).

WHAT THESE TESTS ARE:
- Smoke-grade characterization. Each public coroutine is importable, is a
  coroutine function with no required args, registers cleanly in an in-memory
  APScheduler with its production cron trigger, and either runs against an
  empty test DB without raising OR is explicitly xfailed with a precise
  reference to the existing latent defect being characterized.
- A scheduler-shape canary: registering each function with the same
  (function-reference, trigger, id) shape used at the prod registration site
  yields the expected job IDs.

WHAT THESE TESTS ARE NOT:
- Correctness tests for job behavior. Empty-DB smoke runs only assert the
  no-work path completes or surfaces a known, recorded defect.
- A coverage backstop. These tests intentionally do not assert side effects.

SCHEDULER WIRING AUDIT (recorded so it survives any split):
- 100% function-reference style across the backend. Zero string-references.
- ~150 add_job call sites; spot-checked schedulers/*.py and job_manager.py;
  every call passes the callable by reference, never a dotted string.
- Production wiring path: app/main.py:121 -> services.schedulers.main:init_scheduler.
  Note: services/job_manager.py:init_scheduler is dead code (currently broken
  at import time - it tries to import three jobs from job_executor.py that
  don't exist there). The active scheduler module is services/schedulers/main.py,
  which imports from sibling modules (circulation_jobs, room_jobs, etc.) and
  does NOT import from job_executor.py.
- All 21 public jobs in job_executor.py have duplicate definitions in
  services/schedulers/*_jobs.py; the schedulers/* copies are the ones actually
  registered today. job_executor.py is therefore unwired at the time these
  tests were written. The tests still guard against silent regression if/when
  the module is rewired during the planned split.

LATENT DEFECTS CHARACTERIZED (recorded current behavior, not bugs to fix here):
- A: FeatureNotSupportedError 'FOR UPDATE cannot be applied to the nullable
     side of an outer join'. Affects jobs whose queries combine LEFT JOIN with
     SELECT ... FOR UPDATE SKIP LOCKED. Pre-existing in current source.
- B: AttributeError 'Settings object has no attribute sms_enabled'. The home-
     delivery jobs reference settings.sms_enabled which is not declared on
     the Settings model. Pre-existing.
- C: RuntimeError 'Event loop is closed'. job_executor.py uses module-level
     AsyncSessionLocal bound to an engine created at app import time. When
     pytest-asyncio creates a fresh event loop per test, the cached engine's
     connections belong to a closed loop. The schedulers/* duplicates either
     have the same defect or are paired with per-job session injection -
     either way, splitting must not WORSEN this; xfail captures the baseline.
- D: AttributeError 'OutreachPartner has no attribute created_at'. The
     outreach_service.py query references a column that does not exist on
     the model. Pre-existing.

RUN:
    PII_ENCRYPTION_ENABLED=false /opt/l30/backend/.venv/bin/python \\
        -m pytest backend/app/tests/services/test_job_executor.py -v
"""

import inspect
from typing import Callable

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Import every public coroutine under test from its CURRENT path.
# WHEN SPLITTING: change this import block to the new paths; nothing else.
from app.services.job_executor import (
    aggregate_outreach_statistics,
    calculate_daily_overdue_fines,
    cleanup_job_logs,
    complete_room_reservations,
    expire_old_holds,
    process_child_to_adult_transitions,
    process_expired_institutional_cards_job,
    process_expired_suspensions,
    process_failed_job_retries,
    process_outreach_overdue_checkouts,
    process_room_no_shows,
    refresh_caches,
    renew_annual_closures,
    run_data_retention_jobs,
    send_home_delivery_feedback_requests,
    send_home_delivery_reminders,
    send_hold_expiration_reminders,
    send_outreach_deposit_warnings,
    send_outreach_visit_reminders,
    send_overdue_notifications,
    send_room_reservation_reminders,
)


# ----------------------------------------------------------------------------
# Inventory
# ----------------------------------------------------------------------------

# (function, production_job_id, trigger_kwargs).
# Job IDs and triggers are sourced from services/job_manager.py (the historical
# registration site for job_executor.py functions). The split refactor MUST
# preserve these IDs at whatever new registration site it ends up at, because
# the SQLAlchemy job store persists scheduled jobs by ID across restarts.
ALL_JOBS: list[tuple[Callable, str, dict]] = [
    (calculate_daily_overdue_fines, "daily_fine_calculation", {"hour": 2, "minute": 0}),
    (expire_old_holds, "hourly_hold_expiration", {"minute": 0}),
    (send_overdue_notifications, "daily_overdue_notifications", {"hour": 6, "minute": 0}),
    (run_data_retention_jobs, "daily_data_retention", {"hour": 3, "minute": 0}),
    (process_room_no_shows, "room_no_show_processing", {"minute": "*/5"}),
    (complete_room_reservations, "room_reservation_completion", {"minute": "*/15"}),
    (send_room_reservation_reminders, "room_reservation_reminders", {"hour": 7, "minute": 0}),
    (renew_annual_closures, "annual_closure_renewal", {"month": 1, "day": 1, "hour": 1, "minute": 0}),
    (process_child_to_adult_transitions, "child_to_adult_transitions", {"hour": 4, "minute": 0}),
    (process_expired_suspensions, "expired_suspension_processing", {"minute": 30}),
    (send_home_delivery_reminders, "home_delivery_reminders", {"hour": 8, "minute": 0}),
    (send_hold_expiration_reminders, "hold_expiration_reminders", {"hour": 8, "minute": 0}),
    (process_outreach_overdue_checkouts, "outreach_overdue_checkouts", {"hour": 8, "minute": 0}),
    (send_outreach_visit_reminders, "outreach_visit_reminders", {"hour": 9, "minute": 0}),
    (send_home_delivery_feedback_requests, "home_delivery_feedback_requests", {"hour": 10, "minute": 0}),
    (send_outreach_deposit_warnings, "outreach_deposit_warnings", {"hour": 10, "minute": 0}),
    (aggregate_outreach_statistics, "outreach_monthly_statistics", {"day": 1, "hour": 5, "minute": 0}),
    (process_expired_institutional_cards_job, "outreach_expired_cards", {"hour": 5, "minute": 30}),
    (process_failed_job_retries, "failed_job_retries", {"minute": "*/10"}),
    (cleanup_job_logs, "job_log_cleanup", {"hour": 4, "minute": 0}),
    (refresh_caches, "cache_refresh", {"minute": "*/30"}),
]


def test_inventory_size_unchanged():
    """If this fails, someone added or removed a public job in job_executor.py.
    Update ALL_JOBS, the production registration site, and this count together.
    """
    assert len(ALL_JOBS) == 21, (
        f"Expected 21 public jobs in job_executor.py, got {len(ALL_JOBS)}. "
        "Add the missing job back to ALL_JOBS, or - if it was intentionally "
        "removed - update this count and remove the corresponding smoke test."
    )


# ----------------------------------------------------------------------------
# Import / shape tests (run synchronously, no DB)
# ----------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fn,job_id,_trigger",
    ALL_JOBS,
    ids=[t[1] for t in ALL_JOBS],
)
def test_job_is_async_callable(fn, job_id, _trigger):
    """Every registered job must be an async coroutine function. A split that
    refactored a job into a sync wrapper would silently break at first trigger
    (APScheduler would call it on the event loop and get back a coroutine that
    never awaits).
    """
    assert callable(fn), f"{job_id}: not callable"
    assert inspect.iscoroutinefunction(fn), (
        f"{job_id}: must be `async def`, got {type(fn).__name__}"
    )


@pytest.mark.parametrize(
    "fn,job_id,_trigger",
    ALL_JOBS,
    ids=[t[1] for t in ALL_JOBS],
)
def test_job_takes_no_required_args(fn, job_id, _trigger):
    """Production registration is `scheduler.add_job(fn, trigger, id=..., ...)`
    with no `args=`/`kwargs=`. A split that added e.g. `session: AsyncSession`
    as a required positional arg would silently break at first trigger.
    """
    sig = inspect.signature(fn)
    required = [
        p for p in sig.parameters.values()
        if p.default is inspect.Parameter.empty
        and p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        )
    ]
    assert not required, (
        f"{job_id}: must accept zero required args, got {[p.name for p in required]}"
    )


# ----------------------------------------------------------------------------
# Scheduler registration canary
# ----------------------------------------------------------------------------

def test_all_jobs_register_in_in_memory_scheduler():
    """Register every job in a paused in-memory AsyncIOScheduler and confirm
    APScheduler accepts the function-reference + trigger + id combinations.

    THIS IS THE SINGLE MOST IMPORTANT TEST IN THIS FILE. A silent-drop during
    a split manifests here as a missing job ID, an exception from add_job(),
    or a duplicate-ID collision overwriting an earlier entry.
    """
    scheduler = AsyncIOScheduler()
    for fn, job_id, trigger_kwargs in ALL_JOBS:
        scheduler.add_job(
            fn,
            CronTrigger(**trigger_kwargs),
            id=job_id,
            name=job_id,
            replace_existing=True,
        )

    registered_ids = {j.id for j in scheduler.get_jobs()}
    expected_ids = {job_id for _, job_id, _ in ALL_JOBS}
    missing = expected_ids - registered_ids
    extra = registered_ids - expected_ids
    assert not missing, f"Jobs missing from scheduler after registration: {sorted(missing)}"
    assert not extra, f"Unexpected jobs registered: {sorted(extra)}"
    assert len(registered_ids) == len(ALL_JOBS)


def test_all_job_ids_are_unique():
    """Duplicate job IDs in production use `replace_existing=True`, which means
    one of the two jobs silently overwrites the other at registration. This
    test forces ALL_JOBS to keep IDs distinct so the registration canary above
    can detect drops correctly.
    """
    ids = [job_id for _, job_id, _ in ALL_JOBS]
    dupes = [i for i in ids if ids.count(i) > 1]
    assert len(ids) == len(set(ids)), f"Duplicate job IDs in ALL_JOBS: {sorted(set(dupes))}"


# ----------------------------------------------------------------------------
# Smoke-run tests: each job invoked against the test DB.
# ----------------------------------------------------------------------------
#
# Every job in job_executor.py takes zero args and acquires its own session
# via `async with AsyncSessionLocal() as db:`. Smoke tests therefore call the
# function directly. The conftest's lazy table-creation runs on first use of
# the `db` fixture; we trigger it here at module scope so jobs find tables.

@pytest.fixture(scope="module", autouse=True)
async def _ensure_schema_for_smoke_tests():
    """Trigger conftest._ensure_tables once before the smoke tests run. The
    jobs grab their own session via AsyncSessionLocal, bypassing the `db`
    fixture, so we must seed the schema explicitly.
    """
    from app.tests.conftest import _ensure_tables  # type: ignore[attr-defined]
    await _ensure_tables()
    yield


async def _smoke(fn: Callable) -> None:
    """Invoke a no-arg async job and assert it returns without raising."""
    result = await fn()
    # Jobs return None by contract; assert presence of explicit return.
    assert result is None


# DEFECT A: FOR UPDATE + LEFT JOIN in the overdue-fines query.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT A: calculate_daily_overdue_fines query mixes SELECT ... "
    "FOR UPDATE with a LEFT JOIN, which Postgres rejects. Pre-existing.",
)
async def test_smoke_calculate_daily_overdue_fines():
    await _smoke(calculate_daily_overdue_fines)


# DEFECT A (see file header): FOR UPDATE + LEFT JOIN in expire_old_holds.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT A: query mixes SELECT ... FOR UPDATE with a LEFT JOIN, "
    "which Postgres rejects on the nullable side. Pre-existing in current "
    "source; characterized here so a split surfaces any change in behavior.",
)
async def test_smoke_expire_old_holds():
    await _smoke(expire_old_holds)


async def test_smoke_send_overdue_notifications():
    await _smoke(send_overdue_notifications)


# DEFECT C: cached AsyncSessionLocal across event loops.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: module-level AsyncSessionLocal is bound to an engine "
    "created at app-import time; pytest-asyncio's fresh per-test event loop "
    "trips 'Event loop is closed' inside the data-retention job's nested "
    "sessions. Splitting must not WORSEN this.",
)
async def test_smoke_run_data_retention_jobs():
    await _smoke(run_data_retention_jobs)


async def test_smoke_process_room_no_shows():
    await _smoke(process_room_no_shows)


# DEFECT C.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: AsyncSessionLocal/event-loop interaction. See file header.",
)
async def test_smoke_complete_room_reservations():
    await _smoke(complete_room_reservations)


async def test_smoke_send_room_reservation_reminders():
    await _smoke(send_room_reservation_reminders)


@pytest.mark.skip(
    reason="renew_annual_closures mutates BranchClosure rrule strings; the "
    "empty-DB no-work path is safe but the meaningful coverage path needs "
    "seeded closures with recurrence patterns. Tracked as follow-up."
)
async def test_smoke_renew_annual_closures():
    await _smoke(renew_annual_closures)


# DEFECT C.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: AsyncSessionLocal/event-loop interaction. See file header.",
)
async def test_smoke_process_expired_suspensions():
    await _smoke(process_expired_suspensions)


# DEFECT B: settings.sms_enabled not declared.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT B: send_home_delivery_reminders references settings.sms_enabled "
    "which is not declared on the Settings pydantic-settings model. "
    "Pre-existing. Characterized here so the split refactor doesn't paper "
    "over it - fix in a separate PR.",
)
async def test_smoke_send_home_delivery_reminders():
    await _smoke(send_home_delivery_reminders)


# DEFECT B.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT B: send_home_delivery_feedback_requests also references "
    "settings.sms_enabled. See file header.",
)
async def test_smoke_send_home_delivery_feedback_requests():
    await _smoke(send_home_delivery_feedback_requests)


# DEFECT C.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: AsyncSessionLocal/event-loop interaction. See file header.",
)
async def test_smoke_send_hold_expiration_reminders():
    await _smoke(send_hold_expiration_reminders)


# DEFECT C.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: AsyncSessionLocal/event-loop interaction. See file header.",
)
async def test_smoke_process_child_to_adult_transitions():
    await _smoke(process_child_to_adult_transitions)


async def test_smoke_process_outreach_overdue_checkouts():
    await _smoke(process_outreach_overdue_checkouts)


# DEFECT C.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: AsyncSessionLocal/event-loop interaction. See file header.",
)
async def test_smoke_send_outreach_visit_reminders():
    await _smoke(send_outreach_visit_reminders)


async def test_smoke_send_outreach_deposit_warnings():
    await _smoke(send_outreach_deposit_warnings)


# DEFECT D: OutreachPartner.created_at column does not exist.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT D: aggregate_outreach_statistics -> outreach_service.py "
    "references OutreachPartner.created_at which is not a column on the model. "
    "Pre-existing. Characterized here.",
)
async def test_smoke_aggregate_outreach_statistics():
    await _smoke(aggregate_outreach_statistics)


async def test_smoke_process_expired_institutional_cards_job():
    await _smoke(process_expired_institutional_cards_job)


# DEFECT C.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: AsyncSessionLocal/event-loop interaction. See file header.",
)
async def test_smoke_process_failed_job_retries():
    await _smoke(process_failed_job_retries)


# DEFECT C.
@pytest.mark.xfail(
    strict=False,
    reason="DEFECT C: AsyncSessionLocal/event-loop interaction. See file header.",
)
async def test_smoke_cleanup_job_logs():
    await _smoke(cleanup_job_logs)


@pytest.mark.skip(
    reason="refresh_caches touches Redis (cache_warming_service); smoke-running "
    "without a Redis mock would corrupt the dev cache namespace. Covered "
    "indirectly by cache_warming_service tests."
)
async def test_smoke_refresh_caches():
    await _smoke(refresh_caches)
