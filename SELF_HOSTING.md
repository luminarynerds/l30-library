<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# Self-Hosting L30

A practical guide for deploying your own L30 library instance. Assumes familiarity with Docker, Docker Compose, and basic Linux server administration.

## Quick Start

Everything builds from source with Docker -- clone, configure, start:

```bash
cd /opt
git clone https://github.com/luminarynerds/l30-library.git l30
cd l30

# Generate secrets and configure your library (creates .env + branding.json)
./setup.sh

# Review .env and adjust anything setup.sh didn't ask about (see
# Environment Variables below). .env.example is a stub, not a working
# config -- don't use it.
nano .env

# Build and start everything (first build takes 10-15 minutes)
docker compose -f docker-compose.dist.yml up -d --build
```

The backend entrypoint handles database initialization and reference-data
seeding automatically on first boot (Alembic migrations are NOT auto-run --
see Database Setup below). Watch the logs to confirm:

```bash
docker compose -f docker-compose.dist.yml logs -f l30-backend
```

The application will be available on 127.0.0.1:8081 (localhost only). You
need a reverse proxy (nginx, Caddy, etc.) in front for SSL termination and
public access -- INSTALL.md Step 7 has a copy-paste host-nginx config. On
first boot the app serves its setup wizard, where you create the founding
admin account.

For local development (direct backend/DB/Redis ports), use the separate
`docker-compose.yml` -- see DEVELOPER_SETUP.md.

L30's own production deployment (l30.org) additionally layers a private
`docker-compose.prod.yml` with operator-specific settings on top of this
same dist flow. That file is not part of the public self-hosting path
documented here -- everything below assumes `docker-compose.dist.yml`.

## Branding Your Instance

### Backend

Set these environment variables in `.env`:

| Variable | Purpose | Default |
|----------|---------|---------|
| `LIBRARY_NAME` | Appears in emails, SIP2, and API responses | `My Library` |
| `FROM_EMAIL` | Sender address for all outgoing email | `noreply@yourlibrary.org` |
| `FRONTEND_URL` | Base URL of your public site | `https://yourlibrary.org` |

### Frontend

The frontend stores brand-related constants in `frontend/src/constants/`:

- `contact.ts` -- email addresses, phone number, physical address
- `brandMessages.ts` -- loading messages, empty states, error messages (uses i18n keys; actual strings are in `frontend/src/i18n/translations/`)

Edit these files and rebuild the frontend container.

The frontend API base URL defaults to `/api/v1` but can be overridden at build time:

```bash
VITE_API_BASE=https://api.yourlibrary.org/api/v1
```

## Environment Variables

The `.env.dist` template documents the ~40 variables you'll typically touch
(the application recognizes far more, almost all with working defaults --
`docs/env-variables.csv` has the full reference). `./setup.sh` generates the
secrets. The ones you must have set:

| Variable | Notes |
|----------|-------|
| `DOMAIN` | Your public domain; feeds `TRUSTED_HOSTS` and the nginx config |
| `DB_PASSWORD` | Used by the Postgres container; the compose file builds `DATABASE_URL` from it |
| `REDIS_PASSWORD` | Required in production; the compose file builds `REDIS_URL` from it |
| `SECRET_KEY` | Min 48 chars. Generate with `python3 -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `JWT_SECRET_KEY` | Same generation method as SECRET_KEY |
| `PII_ENCRYPTION_KEY` | Fernet key. Generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `PII_HASH_KEY` | Required when `PII_ENCRYPTION_ENABLED=true`; the backend refuses to boot in production without it |
| `FRONTEND_URL` | Full URL of your frontend (e.g. `https://yourlibrary.org`) |
| `CORS_ORIGINS` | Comma-separated list of allowed origins |
| `FROM_EMAIL` | Sender address for outgoing email |
| `RESEND_API_KEY` | Required if you want to send email (holds, overdue notices, etc.) via Resend |

### Optional integrations

These are disabled by default and only needed if you use them:

- `SENTRY_DSN` -- error tracking
- `OLLAMA_BASE_URL`, `OLLAMA_MODEL` -- AI-powered recommendations (requires a running Ollama instance)
- `METISLIB_ENABLED` -- cooperative ebook integration
- `SIP2_ENABLED` -- self-checkout kiosk protocol
- `S3_BUCKET` -- S3-compatible storage for uploads (default is local filesystem)

Route-related variables (`ROUTE_*`) have sensible defaults and are covered in the Frontend Route Convention section below.

## Database Setup

Database initialization is automatic. On first boot, the backend entrypoint:

1. Runs `scripts/init_db.py` to create the schema from SQLAlchemy models (with retries until Postgres is ready)
2. Bootstraps core reference data (library system, regions, branches); the full demo/reference seed orchestrator only runs when `SKIP_SEEDS=false`
3. Validates enum values are lowercase (blocks startup if violated)
4. Runs schema drift detection

Alembic migrations are **not** auto-run on startup -- `init_db.py` is the
canonical schema source on a fresh install, and upgrades apply migrations
manually (next section).

The Postgres container also runs two init scripts on first creation (mounted into `/docker-entrypoint-initdb.d/`):

- `scripts/init-db.sql` -- creates extensions: `pg_stat_statements`, `vector` (pgvector), `pg_trgm`
- `scripts/init-bootstrap.sql` -- creates a bootstrap marker table

These only run on the first `docker compose up` when the data volume is empty.

### Manual migration

If you need to run migrations manually (e.g., after pulling an update), **run the preflight gate first** -- the migration tree periodically carries multiple heads, and `alembic upgrade head` will silently advance only one lineage:

```bash
bash scripts/preflight-alembic.sh
docker compose -f docker-compose.dist.yml exec l30-backend alembic upgrade head
```

If preflight reports multiple heads, reconcile them with a merge revision
(`alembic merge heads -m "merge"`) before upgrading.

### Backups

Use `pg_dump` through the container; the redirect writes the dump to the
host:

```bash
docker compose -f docker-compose.dist.yml exec database \
  pg_dump -U l30 l30_library > ./backups/backup_$(date +%Y%m%d).sql
```

For automated nightly backups with off-site replication, see `scripts/automated-backup.sh`. To encrypt those archives at rest, set `BACKUP_AGE_RECIPIENTS_FILE` to the path of a file containing one or more age public recipients (the script header documents the details).

### At-rest encryption

The DB cluster, uploads, audit logs, Redis data, and backup archives can be placed on a LUKS2-encrypted volume (auto-unlocked at boot via Tang/Clevis NBDE). Provisioning script: `scripts/setup-luks-nbde.sh` -- its header documents the full procedure.

## Using a Custom Frontend

The backend is a REST API served at `/api/v1/`. Interactive API docs are available at `/docs` (disabled in production by default; set `API_DOCS_ENABLED=true` to enable).

To use your own frontend:

1. Point your frontend at the API. The default frontend uses:

   ```typescript
   export const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1'
   ```

   If your frontend is on a different domain, set `CORS_ORIGINS` in `.env` to include it.

2. Update the nginx config to proxy to your frontend instead of the built-in one. In `docker-compose.dist.yml`, the nginx service uses environment variables:

   ```yaml
   environment:
     - FRONTEND_BACKEND=http://your-frontend:80
   ```

   Or remove the `frontend` service entirely and serve your frontend separately, proxying only `/api/` to the L30 backend.

3. Set `FRONTEND_URL` to your frontend's public URL. The backend uses this to generate links in emails and notifications.

## Frontend Route Convention

The backend generates URLs for emails, notifications, and redirects using route patterns defined in `backend/app/core/frontend_routes.py`. These are the default routes:

| Route | Default Path | Used For |
|-------|-------------|----------|
| `catalog` | `/catalog` | Category browsing links in emails |
| `catalog_item` | `/catalog/{id}` | Direct item links |
| `account` | `/account` | Account page links |
| `account_holds` | `/my-account/holds` | Hold-ready notifications |
| `account_checkouts` | `/my-account/checkouts` | Checkout reminder emails |
| `reset_password` | `/reset-password` | Password reset emails |
| `verify_email` | `/verify-email` | Email verification links |
| `events` | `/events` | Event notification links |
| `rooms` | `/rooms` | Room booking links |
| `unsubscribe` | `/unsubscribe` | Email unsubscribe links |
| `newsletter_confirm` | `/newsletter/confirm` | Newsletter double opt-in |

If your frontend uses these same paths, everything works out of the box. If your frontend uses different paths, override them with environment variables:

```bash
ROUTE_CATALOG=/browse
ROUTE_CATALOG_ITEM=/browse/{id}
ROUTE_ACCOUNT=/my-account
ROUTE_RESET_PASSWORD=/forgot-password
ROUTE_VERIFY_EMAIL=/confirm-email
```

Every route has a corresponding `ROUTE_*` env var. See `backend/app/core/frontend_routes.py` for the full list.

## Email Branding

Outgoing emails use the `LIBRARY_NAME`, `FROM_EMAIL`, and `FRONTEND_URL` values from your environment.

Email templates are in `backend/app/templates/email/`. The current templates cover purchase order workflows (approval, submission, rejection). If you need deeper customization, edit those HTML templates directly.

The backend builds all email links using the frontend route configuration described above, so setting `FRONTEND_URL` and any necessary `ROUTE_*` overrides is usually sufficient.

## License

L30 is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).
If you modify the source code and make it available over a network, you must
publish your modifications under the same license. Running an unmodified copy
does not trigger this requirement. See the LICENSE file for details.

## Security Checklist

Before going live:

- [ ] Generate unique values for `SECRET_KEY`, `JWT_SECRET_KEY`, `DB_PASSWORD`, `REDIS_PASSWORD`, and `PII_ENCRYPTION_KEY`. Never reuse the example values. (The `setup.sh` script does this automatically.)
- [ ] Set `PII_ENCRYPTION_ENABLED=true` (required for patron data protection).
- [ ] Set `DEBUG=false` and `API_DOCS_ENABLED=false`.
- [ ] Set `CORS_ORIGINS` to only your domain(s). Do not use `*`.
- [ ] Configure SSL termination on your reverse proxy. The L30 nginx container binds to 127.0.0.1:8081 (plain HTTP) and expects a host-level proxy to handle TLS.
- [ ] Firewall: only expose ports 22 (SSH), 80, and 443. Postgres and Redis are not published to the host at all in `docker-compose.dist.yml`; the app port (8081) binds to 127.0.0.1 and should never be public.
- [ ] Set `DOMAIN` (which feeds `TRUSTED_HOSTS`) to your domain.
- [ ] Decide on bot protection: the self-host default is `TURNSTILE_DISABLED=true` (no CAPTCHA on public forms -- registration, contact, password reset). To enable it, get a free Cloudflare Turnstile key pair and set `TURNSTILE_DISABLED=false`, `CF_TURNSTILE_SECRET`, and `VITE_TURNSTILE_SITE_KEY`.
- [ ] Decide on admin 2FA: the self-host default is `REQUIRE_ADMIN_2FA=false` so you can evaluate without an authenticator app. Set it `true` before staff use the system in earnest.
- [ ] Decide on rate-limit enforcement: the default is observe-only (`RATE_LIMIT_OBSERVE_ONLY=true` -- over-limit requests are logged, not blocked). After watching logs for false positives, set it `false` to enforce.
- [ ] Test accounts with fixed passwords are only seeded when `ENVIRONMENT != production` (or `FORCE_SEED=true`). The shipped compose files set `ENVIRONMENT=production`; make sure you haven't set `FORCE_SEED` on a real deployment.
- [ ] Set up log rotation. Docker JSON log driver is configured with size limits (100MB/10 files for backend, 50MB/5 files for Redis), but monitor disk usage.
- [ ] Consider enabling Sentry (`SENTRY_DSN`) for production error tracking.
