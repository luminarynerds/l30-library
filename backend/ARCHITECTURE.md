<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 Backend Architecture

## Overview

L30 is a full-featured library management system (ILS) built with FastAPI, SQLAlchemy 2.0 (async), and PostgreSQL 16 with pgvector. It serves two domains: **librarians.cloud** and **l30.org**.

## Stack

| Layer | Technology |
|-------|-----------|
| API Framework | FastAPI (Python 3.12) |
| ORM | SQLAlchemy 2.0 async with asyncpg |
| Database | PostgreSQL 16 + pgvector |
| Cache | Redis 7 |
| Rate Limiting | SlowAPI |
| Auth | JWT (access + refresh tokens), magic links, session management |
| Container | Docker Compose (backend, frontend, nginx, database, redis) |
| Frontend | React + TypeScript + Vite + Tailwind CSS |

## Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app, middleware, router registration
│   ├── api/v1/              # Route handlers (405 files)
│   │   ├── registry.py      # Single source of truth for router registration
│   │   ├── feature_guards.py # Feature flag dependencies
│   │   ├── auth/            # Auth package (helpers, login, registration, etc.)
│   │   ├── catalog/         # Catalog package (browse, crud, search, images)
│   │   ├── circulation/     # Circulation package (checkouts, holds, hold_shelf, jobs)
│   │   ├── privacy/         # Privacy/GDPR package
│   │   ├── outreach/        # Community outreach package
│   │   ├── staff/           # Staff operations package
│   │   ├── staff_fines/     # Fine management package
│   │   ├── staff_lost_damaged/ # Lost/damaged items package
│   │   ├── indie/           # Indie author platform package
│   │   ├── board/           # Board governance package
│   │   ├── acquisition/     # Acquisitions package
│   │   ├── legal/           # Legal resources package
│   │   ├── strategic/       # Strategic planning package
│   │   ├── setup/           # Initial setup wizard package
│   │   └── *.py             # Flat route modules (not yet split into packages)
│   ├── models/              # SQLAlchemy models (241 files)
│   ├── schemas/             # Pydantic schemas (146 files)
│   ├── services/            # Business logic (445 files across 16 directories)
│   ├── core/                # Config, database, auth, rate limiting, caching
│   └── middleware/          # Request logging
├── scripts/                 # Seed data scripts
├── tests/                   # Test suite
└── entrypoint.sh            # Container entrypoint (schema sync, seeds, gunicorn)
```

## Route Organization

Routes follow two patterns:

### 1. Domain Packages (preferred)
Large route files are split into packages with sub-modules:

```
api/v1/catalog/
├── __init__.py      # Merges sub-routers, re-exports shared names
├── helpers.py       # Shared utilities (no router)
├── browse.py        # Public read endpoints
├── crud.py          # Staff write endpoints
├── search.py        # Advanced search
└── images.py        # Cover/image management
```

Each sub-module has its own `router = APIRouter()`. The package `__init__.py` merges them:

```python
router = APIRouter(prefix="/catalog", tags=["catalog"])
router.include_router(browse.router)
router.include_router(crud.router)
```

**Current packages:** auth, catalog, circulation, privacy, outreach, staff, staff_fines, staff_lost_damaged, acquisition, board, legal, strategic, setup

### 2. Flat Modules (legacy)
Smaller route files remain as single `.py` files in `api/v1/`. These are registered directly via registry.py.

## Router Registration

`api/v1/registry.py` is the single source of truth for all API routes. It uses lazy imports to avoid loading all 326 routers upfront, significantly reducing startup time during testing.

```python
def register_all_routers(app: FastAPI):
    module = _lazy_import('app.api.v1.some_module')
    app.include_router(module.router, prefix="/api/v1")
```

`main.py` calls `register_all_routers(app)` on startup.

### Feature Guards

Routes are conditionally enabled based on library feature flags. `api/v1/feature_guards.py` defines dependency functions (e.g., `require_acquisition_enabled`, `require_events_enabled`) that are passed as router dependencies in registry.py. This allows libraries to activate only the modules they need.

## Key Patterns

### Authentication
- `get_current_user` dependency in `api/v1/auth/helpers.py` — imported by most route modules
- JWT access tokens (short-lived) + httpOnly refresh token cookie
- `get_optional_user` for endpoints that work with or without auth

### Database
- Async sessions via `get_db` dependency
- Schema sync on startup (entrypoint.sh runs DDL generation from models)
- 1,048 tables in production

### Caching
- Redis-backed with `get_cached`/`set_cached` helpers in `core/cache.py`
- Cache keys generated via `make_cache_key`

### Rate Limiting
- SlowAPI with per-endpoint limits via `@limiter.limit("60/minute")`

### Pagination
- `PaginationDefaults` in `core/pagination_config.py`
- Standard params: `page` (1-based), `per_page` (default 20, max varies)

## Nginx Architecture

```
Internet → System Nginx (SSL termination, /etc/nginx/sites-enabled/)
         → Docker Nginx (nginx.prod.conf, port 8081)
           → Frontend container (React SPA, port 80)
           → Backend container (FastAPI/Gunicorn, port 8000)
```

The Docker nginx config is `nginx/nginx.prod.conf` (not `nginx.conf` — that's the dev fallback).

## Development Notes

- Backend port: 8804 (direct), 8081 (through nginx)
- Database: `l30` user, `l30_library` database, port 5435 (dev) / 5434 (prod)
- Redis: port 6381 (dev) / 6379 (prod)
- Rebuild after code changes: `docker compose up -d --build l30-backend`
- Health check: `curl http://localhost:8081/api/v1/health`
