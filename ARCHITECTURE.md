<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 Architecture

## Overview

L30 is a free, open-source integrated library system (ILS) for public
libraries. It supports patron accounts, circulation, cataloging, events,
reading programs, and staff operations.

This document is a map of the system. For installation and local development,
start with [README.md](README.md); for contribution conventions, see
[CONTRIBUTING.md](CONTRIBUTING.md).

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend API | Python 3.12 / FastAPI 0.109+ / Uvicorn |
| ORM | SQLAlchemy 2.0 (async) / asyncpg |
| Database | PostgreSQL 16 with pgvector extension |
| Cache / Sessions | Redis 7 |
| Frontend | React 18 / TypeScript / Vite / Tailwind CSS |
| Data Fetching | TanStack Query (React Query) / openapi-fetch |
| Routing | react-router-dom |
| Charts | Recharts |
| Icons | Lucide React |
| Observability | Sentry (frontend @sentry/browser, backend sentry-sdk) / OpenTelemetry |
| Auth | JWT (PyJWT) / bcrypt / TOTP (pyotp) |
| Containerization | Docker Compose |
| Reverse Proxy | nginx (container) + nginx (host) |
| CI/CD | GitHub Actions (20 workflows) |
| Package Management | uv (Python) / npm (frontend) |

## Directory Map

```
/opt/l30/
├── backend/
│   └── app/
│       ├── api/v1/          # 405 route files, 13 domain packages
│       │   ├── acquisition/  # Acquisitions endpoints
│       │   ├── auth/         # Authentication package
│       │   ├── board/        # Board governance endpoints
│       │   ├── catalog/      # Catalog CRUD, browse, search, images
│       │   ├── circulation/  # Checkouts, holds, hold shelf, jobs
│       │   ├── legal/        # Legal/law enforcement endpoints
│       │   ├── outreach/     # Community outreach endpoints
│       │   ├── privacy/      # Privacy/GDPR package
│       │   ├── setup/        # Initial setup wizard
│       │   ├── staff/        # Staff operations endpoints
│       │   ├── staff_fines/  # Fine management endpoints
│       │   ├── staff_lost_damaged/ # Lost/damaged item endpoints
│       │   └── strategic/    # Strategic planning endpoints
│       ├── models/          # 241 SQLAlchemy models
│       ├── services/        # Business logic (16 directories, 445 files)
│       ├── schemas/         # Pydantic request/response validation (146 files)
│       ├── core/            # Auth, config, middleware, security
│       ├── seeds/           # Database seed scripts
│       ├── templates/       # Email/document templates (Jinja2)
│       ├── tests/           # Test files (pytest)
│       └── main.py          # FastAPI app entry point
├── frontend/
│   └── src/
│       ├── pages/           # 21 page directories (route-based)
│       ├── components/      # 72 component directories
│       ├── features/        # 8 feature modules
│       ├── api/             # API client layer + generated types
│       │   └── generated/
│       │       └── schema.d.ts  # ~273K lines, auto-generated from OpenAPI
│       ├── hooks/           # Custom React hooks
│       ├── contexts/        # React context providers
│       ├── types/           # TypeScript type definitions
│       ├── i18n/            # Internationalization
│       ├── theme/           # Design tokens and theming
│       ├── App.tsx          # Root component
│       └── main.tsx         # Vite entry point + Sentry init
├── docker-compose.prod.yml  # Production compose (pinned names)
├── docker-compose.yml       # Local development compose
├── nginx/
│   └── nginx.prod.conf      # Container nginx config
├── scripts/                 # Deployment, backup, utility scripts
├── .github/workflows/       # 20 CI/CD workflows
├── docs/                    # Project documentation
└── .env.example             # Environment variable template
```

## Service Topology

Five Docker containers in production:

```
                    ┌─────────────────┐
    Internet ───────│  Host nginx     │
    (l30   │  :443 -> :8081  │
     .com)          └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  l30-nginx      │
                    │  :8081 -> :80   │
                    └───┬─────────┬───┘
                        │         │
               ┌────────▼──┐  ┌──▼────────┐
               │ l30-backend│  │l30-frontend│
               │ FastAPI    │  │ Vite/nginx │
               │ :8000      │  │ :80        │
               └──┬──────┬──┘  └────────────┘
                  │      │
         ┌────────▼┐  ┌──▼───────┐
         │l30-data- │  │l30-redis │
         │base      │  │ :6379    │
         │PG16:5432 │  └──────────┘
         └──────────┘
```

Host nginx handles TLS termination and proxies to container nginx on port 8081. Container nginx routes /api/* to the backend and everything else to the frontend.

Database is exposed on host port 5434 (not 5432) for direct access without conflicting with any host PostgreSQL.

## Data Model

241 SQLAlchemy models across 1,048 database tables, organized by domain:

| Domain | Key Models | Description |
|--------|-----------|-------------|
| Core | User, Branch, Permission | Users with 11 roles, multi-branch support |
| Circulation | Checkout, Hold, Fine | Check in/out, holds queue, fine management |
| Catalog | CatalogItem, Series, Comic | Books, audiobooks, comics, manga |
| Events | Event, EventRegistration, EventReview | Programs, registration, feedback |
| Community | BookClub, BookClubMeeting, Announcement | Clubs, meetings, public announcements |
| Rooms | Room, RoomReservation | Study rooms, meeting rooms, makerspace |
| Learning | LearningPath, Achievement, UserStats | Courses, gamification, progress tracking |
| Indie Authors | IndieAuthor, IndieEbook | Local author self-publishing platform |
| Makerspace | Equipment, Booking | 3D printers, laser cutters, reservations |
| Cannabis Ed | CannabisStrain | Educational cannabis information |
| Genealogy | GenealogyInquiry, GenealogyResearch | Family history research support |
| Operations | StaffSchedule, PTO, ShiftSwap, CashDrawer | Staff scheduling, time off, cash handling |
| Emergency | EmergencyAlert, PanicAlert, ThreatResponse | Safety and emergency protocols |
| Digital | EbookAccessCard, OverdriveIntegration | Digital lending, Overdrive, Libby |
| Compliance | CIPACompliance, PrivacyLedger, DMCA | Legal compliance, patron privacy |

## API Surface

405 route files providing RESTful endpoints across 326 registered routers. Routes are organized as:
- 14 domain packages in api/v1/ for complex domains (auth, catalog, circulation, etc.)
- Top-level files in api/v1/ for smaller features
- Registry pattern: all routers registered via lazy imports in api/v1/registry.py
- Feature guards: routes are conditionally enabled based on library feature flags

## Authentication and Authorization

- JWT-based: Access tokens issued on login, passed via Authorization header
- 11 roles (highest to lowest privilege): SUPER_ADMIN, ADMIN, DIRECTOR, LEGAL, LIBRARY_ADMIN, STAFF, TEACHER, BOOKMOBILE, HOMEBOND, PATRON, CHILD
- Role enforcement: Dependency injection (require_admin(), require_staff(), check_staff_access()) in route decorators
- COPPA compliance: Age threshold of 13, CHILD role for minors
- Patron statuses: ACTIVE, SUSPENDED (auto-liftable), BLOCKED (manual), DECEASED
- 2FA support: TOTP via pyotp with QR code generation

## Frontend Architecture

- Routing: react-router-dom with page-based organization (21 page directories)
- Data fetching: TanStack Query for server state, openapi-fetch for type-safe API calls
- Type generation: OpenAPI schema generates schema.d.ts (~273K lines, not hand-written)
- State management: React context providers for auth, theme, i18n, accessibility
- Styling: Tailwind CSS with some inline styles (known issue)
- Error tracking: Sentry initialized in main.tsx
- i18n: Internationalization support built in
- Accessibility: Neurodivergent UX system with focus mode, quiet mode, and sensory presets

## CI/CD

20 GitHub Actions workflows in .github/workflows/:

| Workflow | Purpose |
|----------|---------|
| ci.yml | Main CI pipeline |
| backend-tests.yml | pytest suite |
| frontend-build.yml | Vite build verification |
| lint.yml | Code linting |
| security-scan.yml | Security vulnerability scanning |
| secrets-scan.yml | Detect committed secrets |
| deploy-production.yml | Production deployment |
| build-images.yml | Docker image builds |
| api-contract-tests.yml | API schema contract validation |
| api-coverage.yml | API endpoint coverage |
| accessibility.yml | a11y checks |
| journey-smoke-tests.yml | End-to-end user journey tests |
| mutation-testing.yml | Mutation testing |
| perf-benchmarks.yml | Performance benchmarks |
| public-pages-tests.yml | Public page rendering |
| test-405-errors.yml | Method-not-allowed validation |
| drift-check.yml | Configuration drift detection |
| release.yml | Release management |
| claude-code-review.yml | AI-assisted code review |
| claude.yml | Claude integration |

## Key Design Decisions

- Async throughout: SQLAlchemy async with selectinload() for relationship loading. No lazy loading in async context.
- pgvector: Semantic search via PostgreSQL vector extension rather than a separate vector DB.
- Monorepo: Backend and frontend in one repo for coordinated deploys.
- Generated types: Frontend TypeScript types generated from backend OpenAPI schema, not manually maintained.
- Seed-first development: Rich seed data so the app looks lived-in from first run.
- Feature guards: Routes are conditionally enabled via feature flags, allowing libraries to activate only the modules they need.
- Rate limiting: slowapi integrated and enabled by default, in observe-only mode (limits are classified and logged but not enforced). Set `RATE_LIMIT_OBSERVE_ONLY=false` to actually throttle.
- OpenTelemetry: Full observability stack (traces for FastAPI, SQLAlchemy, Redis, httpx) with OTLP exporter.
