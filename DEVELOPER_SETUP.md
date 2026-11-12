<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# Developer Setup

Start with an isolated source installation for code review and evaluation.
Use a separate machine or Docker environment from any library deployment:
the Compose files use fixed container and volume names.

## Prerequisites

- Git, Docker, and Docker Compose v2
- Python 3.12 and Node.js 20+ for tests outside Docker

## Start an evaluation instance

```bash
git clone https://github.com/luminarynerds/l30-library.git
cd l30-library
./setup.sh --domain yourlibrary.example --email admin@yourlibrary.example --name "Example Library"
docker compose -f docker-compose.dist.yml up -d --build
docker compose -f docker-compose.dist.yml ps
curl -f http://127.0.0.1:8081/health
```

Open `http://localhost:8081` and create an administrator through the setup
wizard. Setup generates `.env` with private secrets and `branding.json`.
`.env.example` is a short reference stub; it is not a complete working
configuration. Do not copy it over the generated `.env`.

The distribution images are runtime images, not test environments. Their
backend and frontend ports are internal; use the reverse proxy on port 8081.
The database starts with bootstrap/reference data, not a guaranteed list of
sample patrons or shared test passwords. The install smoke test explicitly
creates its own synthetic administrator and demo data.

## Inspect logs and rebuild

```bash
docker compose -f docker-compose.dist.yml logs --tail=100 l30-backend
docker compose -f docker-compose.dist.yml up -d --build l30-backend frontend
```

See [INSTALL.md](INSTALL.md) for server installation and HTTPS, and
[SELF_HOSTING.md](SELF_HOSTING.md) for environment variables and optional
integrations. Mail, AI, and other external integrations need their own
configuration; they are not prerequisites for the basic evaluation.

## Run the install smoke test

On an isolated Docker host with port 8081 free:

```bash
./scripts/dist-smoke.sh
```

This builds from source, starts a synthetic evaluation instance, checks
health and login, loads demo records, and attempts a checkout. It removes
its own test containers and volumes on exit. It does not certify every
feature. The same test is available in the manual **Dist Install Smoke**
GitHub Actions workflow.

## Contributor tests

Frontend tests run from source, rather than inside the nginx runtime image:

```bash
cd frontend
npm ci
npm run typecheck
npm test
```

Backend tests need a Python test environment and an isolated PostgreSQL
instance with pgvector, pg_trgm and pgcrypto. Tests use the database name
`l30_test`; never point them at a production database. Follow the service,
dependency and environment setup in
[the backend workflow](.github/workflows/backend-tests.yml) or
[the focused contract workflow](.github/workflows/off-button-contract.yml).
Set `TEST_REQUIRE_POSTGRES=1` so a failed PostgreSQL connection cannot silently
substitute SQLite.

The root `docker-compose.yml` is a reference development configuration with
different port mappings and an `.env.prod` requirement. It is not interchangeable
with the distribution Compose file used above.

## Repository and contributions

The release repository is [luminarynerds/l30-library](https://github.com/luminarynerds/l30-library).
See [CONTRIBUTING.md](CONTRIBUTING.md) for pull-request conventions and
[SECURITY.md](SECURITY.md) for vulnerability reports.
