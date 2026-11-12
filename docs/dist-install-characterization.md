# L30 Distribution Install — Failure Surface Characterization (2026-07-05)

> Historical report against the July 5 revision below. It is not a current
> list of unresolved defects. Use [INSTALL.md](../INSTALL.md) for the current
> source-install path and the Dist Install Smoke workflow to verify a release.

**Method:** fresh clone of `luminarynerds/l30` (HEAD `8d2d7c5`), local Docker Desktop
on macOS (arm64), built from source (GHCR images are private/unpullable). Domain
`orange.local`, library name "City of Orange Public Library", admin email
`admin@orange.local` per the task brief. All findings below are reproduced against
running containers, not inferred from code reading alone, unless explicitly marked
"(static analysis)".

This doc supersedes the 2026-07-03 notes in
`~/docs/library-onboarding/l30-dist-install-findings.md` for anything schema/init
related — that doc predates the `deferred_tables.txt` skip-list mechanism.

---

## 1. Defects reproduced, in the order a fresh installer would hit them

### 1.1 `setup.sh` is not macOS/BSD-sed compatible (NEW — not in prior notes)

`setup.sh` uses GNU-only syntax: `sed -i "s|...|...|" .env` (no backup-extension
argument). BSD/macOS `sed` requires `sed -i '' "s|...|...|"`. Under `set -euo
pipefail`, the script dies on the very first substitution:

```
sed: 1: ".env
": invalid command code .
```

Result: `.env` is left as a byte-for-byte copy of `.env.dist` (all `CHANGE_ME`
placeholders, no domain/name/email filled in), and the script exits 1 with no
error message pointing at the real cause (the failure looks like a raw shell
syntax error, not "wrong sed dialect"). No `gsed` was available to work around it.
I reproduced the substitutions manually in Python to get a usable `.env` for the
rest of this characterization.

Prod is Linux so this doesn't block the VPS today, but it blocks any contributor,
onboarding demo, or fork evaluation done from a Mac laptop — plausible for the
Orange PL case and any future fork-and-gift target.

**Non-TTY / non-interactive behavior:** does NOT hang. With `.env` already
present, piping empty stdin hits the "Overwrite? (y/N)" prompt, defaults to N,
exits 1 immediately. With no `.env`, empty stdin fails the `[ -z ... ]` required-field
check and exits 1 immediately with "Error: All fields are required." So the
"hangs on non-TTY" concern in the brief did not reproduce — the real defect is
narrower: **no flag/env-var driven mode**, so a scripted fork-and-deploy pipeline
still can't drive it unattended (needs expect-style scripting or a TTY).

### 1.2 `branding.json` is a tracked file that `setup.sh` overwrites in place (NEW)

`branding.json` (not `.example`) is checked into git with placeholder content
("My Library", `mylibrary.org`). `setup.sh` writes real per-library values
directly into this tracked file. After running setup, `git status` shows a
dirty tracked file — any future `git pull`/rebase from upstream for updates
will conflict on every fork's local branding. Reverted before this commit;
recommend Task 3 gitignore `branding.json` and treat `branding.json.example`
as the only tracked template (mirrors how `.env`/`.env.dist` already work).

### 1.3 GHCR images unpullable (confirmed, brief's defect #11)

`docker-compose.dist.yml` references `ghcr.io/luminarynerds/l30/{backend,frontend,nginx}:latest`.
These are private; pulling without `read:packages` fails. Built all three from
source instead via a scratch `docker-compose.dist.local.yml` (git-ignored,
mirrors `docker-compose.prod.yml`'s `build:` blocks + `pgvector/pgvector:pg16`).
All three images built cleanly (~4 min total, mostly `sentence-transformers`/
`torch` wheel downloads for the backend). No build-side defects found.

### 1.4 `PII_HASH_KEY` required but never generated or documented (confirmed, brief's expected finding)

Backend refuses to boot. Exact error from `l30-backend` logs:

```
❌ Error: 1 validation error for Settings
  Value error, PII_HASH_KEY must be set in production when PII encryption is
  enabled, so blind indexes (phone_hash, email_hash, name hashes) key on a
  dedicated secret instead of silently falling back to SECRET_KEY. Generate one
  with: python -c "import secrets; print(secrets.token_urlsafe(32))"
```
(`backend/app/core/config.py:426`, validator fires when `environment ==
"production"` and `pii_encryption_enabled` — both are the dist compose
defaults.)

Confirmed: `PII_HASH_KEY` appears in **neither** `.env.dist` nor `setup.sh`'s
secret-generation block (which does generate `PII_ENCRYPTION_KEY`,
`WATERMARK_SECRET_SALT`, `DOWNLOAD_IP_HASH_SALT`, etc. — just not this one).
Every fresh dist install is DOA until an operator manually generates and wires
this key in twice (once in `.env`, once in the compose `environment:` block,
since `docker-compose.dist.yml`'s `l30-backend` service doesn't forward it).
Container restart-looped 10x (`MAX_RETRIES` in `entrypoint.sh`) before giving
up and continuing anyway with zero schema — i.e. even the "fail" mode doesn't
fail cleanly, it staggers on with an empty database and then aborts later
("❌ No branches found after bootstrap; aborting startup").

Unblocked with a throwaway `PII_HASH_KEY` (openssl rand -hex 32) added to
`.env` and to the scratch compose's backend `environment:` block, per the brief.

### 1.5 Turnstile fails CLOSED — no admin can ever log in out of the box (NEW, severe)

With `PII_HASH_KEY` unblocked, the stack boots healthy and the wizard's
`POST /setup/admin` works. But `POST /api/v1/auth/login` unconditionally 400s:

```json
{"error":{"code":"HTTP_400","message":"Captcha verification failed. Please retry."}}
```

Root cause (`backend/app/core/turnstile.py:14-30`): `verify_turnstile()` checks
`environment == "production"` — true in the dist compose — and if
`CF_TURNSTILE_SECRET` is unset, **fails closed** (returns `False`, logs "refusing
bot verification"). It only fails *open* in non-production. `.env.dist` has no
`CF_TURNSTILE_SECRET` entry, `setup.sh` never prompts for or generates one (it's
an external Cloudflare account credential — can't be generated locally), and
there is no `TURNSTILE_DISABLED`/offline-mode escape hatch anywhere in
`config.py`.

**Net effect: a fresh distribution install cannot be logged into at all**,
by design, unless the installer separately signs up for Cloudflare Turnstile
and wires a secret before first login — a self-hosting/"fork it yourself"
blocker more severe than anything else found here, since it silently blocks
the single most basic path (log in as the admin you just created) with no
error message pointing at the actual cause from the wizard UI's perspective.

### 1.6 `.local` TLD (the exact domain the brief tells you to test with) fails email validation (NEW)

`POST /setup/admin` with `admin@orange.local` (verbatim per brief step 2/setup
instructions) 422s:

```json
{"details":[{"field":"body.email","message":"value is not a valid email address: The part after the @-sign is a special-use or reserved name that cannot be used with email."}]}
```
`email-validator` (used by pydantic's `EmailStr`) rejects reserved/special-use
TLDs including `.local`. Worked around with `admin@orangepubliclibrary.example.com`
to continue characterization. This is a real papercut for anyone testing a fork
locally without a real domain yet (which is exactly the fork-evaluation scenario
this whole distribution effort is for).

---

## 2. Schema reality: created vs. deferred vs. stale entries

Inside the running container:

| Metric | Count | Source |
|---|---|---|
| Total SQLAlchemy metadata tables | **1094** | `len(Base.metadata.tables)` inside container |
| Unique `__tablename__` string literals (static grep) | 1096 | brief's grep command — slightly overcounts vs. above due to string dedup artifacts; not a reliable proxy, use the metadata count |
| `deferred_tables.txt` entries (non-comment, non-blank) | **959** | `grep -v '^#' \| grep -vc '^\s*$'` |
| Deferred entries that match a real table name | **932** | cross-checked in-container |
| Deferred entries that match **no** table (stale/typo/renamed) | **27** | dead weight in the skip-list — worth pruning but harmless (no-op) |
| Non-deferred tables (init attempts to create) | **162** | `1094 - 932` |
| Tables actually created in Postgres | **140** | `psql … information_schema.tables` count, matches init log |
| Tables that failed to create despite being non-deferred | **22** | see §3 |

`psql` cross-check:
```
SELECT count(*) FROM information_schema.tables WHERE table_schema='public';
 count
-------
   140
```

## 3. A second, independent bug: 22 non-deferred tables still fail to create

Not a deferral-list problem — these 22 tables are **not** in
`deferred_tables.txt`, so `init_schema_async_raw_sql.py` tries to create them,
but the FK-stripping logic in `_patch_create_table_sql()` (backend/scripts/
init_schema_async_raw_sql.py:111-149) breaks on certain FK line shapes, emitting
invalid SQL:

```
❌ collection_items: syntax error at or near "FOREIGN"
❌ board_recusal_declarations: syntax error at or near "FOREIGN"
❌ board_minutes_amendments: syntax error at or near "FOREIGN"
❌ reading_list_requests: syntax error at or near "FOREIGN"
❌ library_visit_requests: syntax error at or near "FOREIGN"
❌ program_booklist: syntax error at or near "FOREIGN"
❌ course_stage_transitions: syntax error at or near "FOREIGN"
❌ legal_eligibility_thresholds: syntax error at or near "FOREIGN"
❌ engagement_surveys: syntax error at or near "FOREIGN"
❌ support_ticket_events: syntax error at or near "FOREIGN"
❌ parent_resource_guide_flags: syntax error at or near "FOREIGN"
❌ parent_connection_group_meetings: syntax error at or near "FOREIGN"
❌ home_visit_status_history: syntax error at or near "FOREIGN"
❌ parent_onboarding_followups: syntax error at or near "FOREIGN"
❌ parent_onboarding_referrals: syntax error at or near "FOREIGN"
❌ parent_onboarding_session_handouts: syntax error at or near "FOREIGN"
❌ outcome_indicators: syntax error at or near "FOREIGN"
❌ theory_of_change_claims: syntax error at or near "FOREIGN"
❌ engagement_survey_questions: relation "engagement_surveys" does not exist   (cascades from above)
❌ engagement_survey_responses: relation "engagement_surveys" does not exist   (cascades from above)
❌ engagement_user_demographics: relation "engagement_survey_responses" does not exist
❌ engagement_survey_outcomes: relation "engagement_survey_responses" does not exist
```

None of these 22 are on the catalog/circ/events/semantic-search critical path
(they're board-governance, engagement-survey, course, and parent-onboarding
tables) — but they are real, silent data loss for whatever features do depend
on them, and the "cascading `relation does not exist`" pattern shows the bug
compounds (one broken CREATE TABLE takes out every table that FKs to it).
Flagging for Task 4/5: this needs a fix in `_patch_create_table_sql`, not a
deferral-list edit.

## 4. Minimal set of tables that must be un-deferred (evidence-based)

Cross-checked every table touched by `catalog.py`, `circulation.py`,
`circulation_policy.py`, `catalog_authority.py`, `catalog_demand_signal.py`,
`catalog_state_event.py`, `event*.py`, and `embeddings.py` against
`deferred_tables.txt`:

**Already created, no action needed** (core catalog/circ/events already work):
`branches`, `library_systems`, `system_settings`, `users`, `catalog_items`,
`circulation_policy`, `checkouts`, `holds`, `catalog_state_events`,
`catalog_demand_signals`, `authority_terms`, `authority_term_relations`,
`events`, `event_registrations`, `event_waitlist_entries`,
`event_program_partners`, `event_reviews`.

**Deferred and blocking a real feature — must un-defer:**

| Table | Blocks | Evidence |
|---|---|---|
| `text_embeddings` | semantic search | reproduced: `GET /api/v1/search/semantic?q=...` → HTTP 500 |
| `author_embeddings` | "similar authors" | static analysis (`semantic_search.py:398`) |
| `hidden_gem_scores` | hidden-gems discovery | static analysis (`semantic_search.py:327`) |
| `embedding_metadata` | embedding pipeline bookkeeping | static analysis |
| `semantic_search_cache` | semantic search caching **and** a scheduler job that crash-loops without it (see §5) | reproduced |
| `catalog_images` | catalog item cover images | static analysis (`catalog.py:375`) |

**Deferred, not feature-blocking for MVP demo (leave deferred, note for later):**
all 7 event-marketing tables (`event_marketing_campaigns`,
`event_distributions`, `social_media_configs`, `event_flyers`,
`event_graphics`, `event_registration_sources`, `event_feedback`) — nice-to-have
marketing add-ons, not core event browsing/registration.

**Minimal un-defer list to make demo seed + catalog/circ/events/semantic-search
fully work: 6 tables** (`text_embeddings`, `author_embeddings`,
`hidden_gem_scores`, `embedding_metadata`, `semantic_search_cache`,
`catalog_images`).

## 5. Deferred tables that background schedulers touch unconditionally (NEW, operationally serious)

Independent of any user-facing feature, the APScheduler jobs that start with
the backend query several deferred tables unconditionally, with no
try/except around the missing-table case. In ~7 minutes of uptime with zero
user traffic, this produced **21 error-level log lines** for 8 distinct
missing relations:

```
relation "coppa_compliance" does not exist
relation "database_subscriptions" does not exist
relation "indie_ebook_borrows" does not exist
relation "journey_events" does not exist
relation "notification_queue" does not exist
relation "role_settings" does not exist
relation "semantic_search_cache" does not exist   (also blocks semantic search, see §4)
relation "transit_requests" does not exist
```

Example (`notification_queue_job`):
```
Notification queue processing failed: (sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError)
<class 'asyncpg.exceptions.UndefinedTableError'>: relation "notification_queue" does not exist
```

This is a continuous, unbounded log-spam and wasted-scheduler-tick defect on
**every** fresh install using the current deferral list — not tied to any
specific feature a librarian would need to click on. Recommend for Task 4/5:
either un-defer these 7 tables (`notification_queue`, `coppa_compliance`,
`database_subscriptions`, `indie_ebook_borrows`, `journey_events`,
`role_settings`, `transit_requests` — `semantic_search_cache` already counted
in §4) or guard the scheduler jobs to skip gracefully when their table is
absent. Un-deferring is the lower-risk fix given the FK-stripping bug in §3.

**Combined minimal un-defer set (features + scheduler stability): 13 tables.**

## 6. Demo seed (`demo/seed.sql`) — wizard path is doubly broken

### 6.1 The seed file is never packaged into the backend image (NEW, confirmed)

`POST /setup/demo/load` (backend/app/api/v1/setup/router.py:295-325) shells out
to `psql <db_url> -f <seed_file>`, searching three candidate paths:
`/opt/l30/demo/seed.sql`, `/app/demo/seed.sql`, and a dev-relative path under
the repo checkout. Reproduced: hitting the endpoint on a fresh setup-required
DB returns

```json
{"error":{"code":"HTTP_404","message":"Demo seed file not found"}}
```

because `backend/Dockerfile.prod` never `COPY`s the `demo/` directory into the
image (its `COPY` list is `pyproject.toml`, `app/`, `scripts/`, `alembic.ini`,
`alembic/`, `entrypoint.sh` — no `demo/`). Confirmed via
`docker exec l30-backend ls /app` — no `demo` dir present. Grepped
`docker-compose.prod.yml`, `docker-compose.dist.yml`, and `Dockerfile.prod` for
any mount/copy of `demo/` — none exists anywhere in the current build/compose
topology (this is a code-level finding from this checkout; I did not touch or
inspect the live `/opt/l30` VPS to see whether it has an out-of-band copy).
**The "Explore Demo" wizard button is non-functional as currently packaged.**

### 6.2 Even bypassing the packaging bug, the SQL itself fails against the current schema (NEW, confirmed)

Copied `demo/seed.sql` directly into the container and ran it via `psql` against
the 140-table schema from §2. It fails immediately:

```
INSERT 0 1        -- library_systems: ok
INSERT 0 2        -- branches: ok
INSERT 0 1        -- system_settings: ok
ERROR:  there is no unique or exclusion constraint matching the ON CONFLICT specification
-- (line 122: `... ) ON CONFLICT (email) DO NOTHING;` on the users/staff insert)
```

`users.email` has **no unique constraint** — the app looks up users by
`email_hash` (a blind index over the PII-encrypted email; see `\d users`:
`ix_users_email_hash UNIQUE btree`), not by plaintext `email`. `demo/seed.sql`
still targets the pre-PII-encryption schema shape. Because the whole seed file
is one `BEGIN`/`COMMIT` transaction with no savepoints, this single error
aborts everything after it — all patron, catalog, checkout, and event inserts
(lines 123-605) are silently dropped (Postgres reports "current transaction is
aborted" for every subsequent statement, then `ROLLBACK`).

Patched `ON CONFLICT (email)` → bare `ON CONFLICT DO NOTHING` in a scratch copy
to see how far the rest of the file gets: it fails again, one insert later:

```
ERROR:  null value in column "patron_status" of relation "users" violates not-null constraint
```

`User.patron_status` (`backend/app/models/user.py:93-98`) is declared
`default=PatronStatus.ACTIVE` (a **Python/ORM-side** default), not
`server_default=`. The raw-SQL schema generator
(`init_schema_async_raw_sql.py`) compiles `CreateTable()` DDL, which only
emits `server_default`s — Python-side `default=` values never reach the
database. So the column is `NOT NULL` with no DB-level default, and any
INSERT that doesn't go through the SQLAlchemy ORM (like this hand-written
`demo/seed.sql`) must supply every such column explicitly or it 400s at the DB
layer.

**This is not an isolated bug — it's systemic.** A repo-wide static scan found
roughly **1,200 columns** across the model layer using the same
`nullable=False` + `default=...` (no `server_default`) pattern (heuristic
regex count, single-line `Column(...)` defs only — real count is likely higher
once multi-line definitions are included). Any current or future raw-SQL
seed/fixture file is one of these columns away from an identical failure. The
ORM-driven bootstrap seed (`app.seeds.bootstrap_library_system`, which created
branches/regions/settings successfully during boot — see §7) doesn't hit this
because SQLAlchemy fills Python-side defaults before INSERT; only hand-written
SQL against this schema is at risk.

**Recommendation for Task 4/5:** either (a) rewrite `demo/seed.sql` as an
ORM-driven Python seeder so it inherits model defaults for free, or (b) if it
stays raw SQL, explicitly enumerate every NOT-NULL/no-default column for each
of the 7 tables it inserts into. (a) is far less fragile long-term given the
~1,200-column surface area.

## 7. What *does* work cleanly

- Backend boots healthy, frontend boots healthy, nginx proxies both, once
  `PII_HASH_KEY` is supplied.
- ORM-driven bootstrap seed (`bootstrap_library_system`) works perfectly:
  created 1 library system, 3 regions, 4 branches, 28 branch-hours rows for
  "City of Orange Public Library" with zero errors.
- Enum-case assertion and enum/schema drift checks both pass cleanly
  (`✅ No enum drift detected`, `✅ No schema drift detected`).
- `docker compose build` for all three images (backend/frontend/nginx) from
  source succeeds with no Dockerfile-level defects.

## 8. Lower-priority findings (noted, not blocking, out of scope for Task 4/5's schema focus)

- `frontend/index.html` hardcodes `https://l30.org/` in `<link rel=canonical>`,
  `og:url`, `og:image`, `twitter:image`, and JSON-LD `@id` — not templated from
  `branding.json`/`DOMAIN` at build or runtime. Every fork ships with L30's own
  domain in its meta tags/structured data until this is templated. Relevant to
  a later "branding/white-label" task, not schema.

---

## Summary table for Task 4/5 planning

| # | Defect | Severity | Fix surface |
|---|---|---|---|
| 1 | `setup.sh` BSD-sed incompatibility | Medium (Mac-only) | `setup.sh` |
| 2 | `branding.json` tracked + mutated in place | Low-Medium | `.gitignore` + setup.sh |
| 3 | GHCR images private/unpullable | High (already known, #11) | CI/publish config |
| 4 | `PII_HASH_KEY` required, never generated/documented | **Critical** | `setup.sh` + `.env.dist` + `docker-compose.dist.yml` |
| 5 | Turnstile fails closed, no Cloudflare secret path for self-host | **Critical** | `config.py` / `turnstile.py` needs an explicit offline/self-host escape hatch |
| 6 | `.local` TLD rejected by email validation | Low (papercut, but exactly what the brief's setup instructions suggest) | docs, or validator config |
| 7 | 22 non-deferred tables fail via FK-strip bug | Medium | `init_schema_async_raw_sql.py:_patch_create_table_sql` |
| 8 | 27 stale entries in `deferred_tables.txt` | Cosmetic | `deferred_tables.txt` |
| 9 | 6 tables deferred but feature-required (semantic search, cover images) | High | `deferred_tables.txt` |
| 10 | 7 tables deferred but touched unconditionally by schedulers → log-spam | Medium-High (operational) | `deferred_tables.txt` or scheduler guards |
| 11 | `demo/seed.sql` never copied into backend image | **Critical** (feature is dead) | `backend/Dockerfile.prod` |
| 12 | `demo/seed.sql` stale `ON CONFLICT (email)` + missing NOT-NULL columns, whole-file single transaction | **Critical** (feature is dead even once packaged) | `demo/seed.sql` — recommend ORM rewrite |
| 13 | ~1,200 columns with Python-side `default=` but no `server_default=` | High (systemic, informs future raw-SQL work) | awareness/guardrail for Task 4/5, not a one-shot fix |
