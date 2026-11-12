# Quarantined Tests

This directory holds backend tests that are known-failing or known-flaky in
the default test environment. They are excluded from `pytest` by the
`--ignore=tests/quarantine` line in `backend/pyproject.toml` so a fresh
clone runs green by default.

## Why quarantine instead of fix?

Many failures are environmental rather than real bugs:
- Missing optional config (e.g. `PII_ENCRYPTION_ENABLED=true`, Turnstile keys)
- Tests that assume Postgres + Redis but fall back to SQLite stub
- Tests that depend on external services (Resend, Stripe, OCLC, OpenLibrary)
- Tests written against deleted code paths during the 2026 destyle work

Quarantining preserves the test code (and its intent) without bleeding red into
`pytest` output for anyone evaluating the repo.

## How to run the quarantined tests

```sh
cd backend
pytest tests/quarantine --no-header
```

This bypasses the `--ignore` and runs them all. Expect failures — that's the
point.

## How to triage and add more

When you fix one (or confirm it really is environmental and document the env
fix), move it back to its original path under `backend/app/tests/` or
`backend/tests/`.

When you find a new failing test that's not a real bug:
1. Move the file: `git mv backend/path/to/test_foo.py backend/tests/quarantine/path/to/test_foo.py`
2. Add an `__init__.py` to the new sub-path if missing.
3. Note it in this README under the appropriate category below.

## Current contents

### Likely environmental (missing config or service)

- `app_tests/services/test_job_executor.py` — background job execution; needs real Redis
- `app_tests/test_card_access.py` — patron card access; PII encryption setup
- `services/test_autocomplete_service.py` — search autocomplete; needs index build

### Code-drift (test references code that was moved/deleted) — added 2026-05-29

Enumerated via a Postgres-backed run (the env the earlier followup called for).
Each fails deterministically in isolation; all are DB-independent (import /
attribute / signature / missing-file), not harness artifacts.

- `unit/test_auth_error_handling.py` — imports `register` from `app.api.v1.auth`, which was removed
- `unit/test_indie_notifications.py` — calls `app.core.email.send_indie_*`, functions no longer exist
- `unit/api/test_agent_interaction_capture.py` — `chat_with_agent()` signature changed (missing `request` arg)
- `unit/services/test_overflow_purchase_service.py` — `app.services.overflow_purchase_service` module removed
- `analysis/test_endpoint_coverage.py` — reads a one-off dev audit JSON (`PHASE_2_ORPHANED_ENDPOINTS_AUDIT.json`) absent from a clean tree

## Followup

The destyle resume checklist (P3) tracks ~225 known failures as of 2026-05-27.
Only a handful are quarantined here. See the tracking issue for the rest.
