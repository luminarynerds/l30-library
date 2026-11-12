<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 Architecture — Runtime & Wiring Map

A structured map of how L30 is wired together at runtime: request flow, middleware
stack, router registration, the service layer, cross-cutting concerns, and deploy
mechanics. This complements the existing docs and **does not duplicate** them — read
those first for stack, directory layout, data model, and role list:

- `codebase-map/ARCHITECTURE.md` — top-level: tech stack table, directory map, data
  model (241 models / ~1,048 tables), 11-role list, CI workflow inventory.
- `codebase-map/backend/ARCHITECTURE.md` — backend: route-package vs flat-module
  pattern, registry, pagination/caching helpers.
- `codebase-map/docs/l30-architecture-brief.md` — privacy + cataloging brief
  (local-only AI, MARC21 canonical, BIBFRAME derived).

This doc fills the gap those leave: the *runtime view* — middleware order, feature-gate
mechanics, the real service-layer shape, embedding-provider reality, and deploy/caveats.

Source: read-only `origin/main` worktree. References below use `file:line`
against that tree. Counts and revision totals throughout this doc are a
snapshot as of when it was written, not a live query — they drift as the
codebase changes; treat them as "roughly this many," not exact.

---

## 1. System Topology

Production runs as Docker Compose project **`l30`** (5 app containers) behind a host
nginx, plus a co-located local Ollama instance and Umami analytics.

```
                          Internet (https://l30.org)
                                   │
                                   ▼
                    ┌──────────────────────────────┐
                    │  HOST nginx  (TLS terminate)  │   /etc/nginx/sites-enabled/
                    │  :443  ──►  127.0.0.1:8081    │
                    └───────────────┬──────────────┘
                                    │ :8081
                    ┌───────────────▼──────────────┐
                    │  l30-nginx  (container)       │   nginx/nginx.prod.conf
                    │  routes /api/* ► backend       │   API_BACKEND, FRONTEND_BACKEND
                    │  everything else ► frontend    │
                    └───────┬───────────────┬───────┘
                            │ /api/*        │ /*
                  ┌─────────▼────────┐  ┌───▼──────────────┐
                  │  l30-backend     │  │  l30-frontend    │
                  │  FastAPI/uvicorn │  │  Vite SPA / nginx │
                  │  :8000           │  │  :80             │
                  └───┬──────────┬───┘  └──────────────────┘
                      │          │
          ┌───────────▼──┐  ┌────▼─────────┐      ┌───────────────────────────┐
          │ l30-database │  │  l30-redis   │      │  Ollama (separate compose) │
          │ pgvector/pg16│  │  redis:7     │      │  ollama-zcuy-ollama-1:11434│
          │ :5432 (5434  │  │  :6379       │      │  llama3.2:3b + nomic-embed │
          │  host-mapped)│  └──────────────┘      └───────────────────────────┘
          └──────────────┘
```

| Component | Container | Image / role | Notes |
|-----------|-----------|--------------|-------|
| Host nginx | (host) | TLS termination | proxies `:443 → 127.0.0.1:8081` |
| Edge proxy | `l30-nginx` | baked nginx image | routes `/api/*` → backend, else → frontend (`compose:265-291`) |
| API | `l30-backend` | FastAPI/uvicorn `:8000` | app code baked into image; only `scripts/` bind-mounted |
| SPA | `l30-frontend` | Vite build served by nginx `:80` | static assets `cp`-ed into container on deploy |
| DB | `l30-database` | `pgvector/pgvector:pg16` | extensions/bootstrap via `scripts/init-*.sql` (`compose:58-59`) |
| Cache/sessions/jobstore | `l30-redis` | `redis:7-alpine` | rate-limit counters, cache, APScheduler jobstore, pub/sub bus |
| Local AI | external | Ollama | `llama3.2:3b` (chat) + `nomic-embed-text` (embeddings); **no third-party AI** |
| Analytics | external | Umami | self-hosted, per the privacy brief |

**Two-nginx trap & coexistence.** Host nginx → `l30-nginx` is a deliberate two-hop.
Sibling Docker stacks on shared networks also run their own bare `nginx` containers;
`l30-backend` is named unambiguously (was `backend`) precisely so those sibling
stacks reaching `backend:8000` DNS don't collide — see the rename note at
`docker-compose.prod.yml:194-200`. The backend's TrustedHost middleware also exempts
`/health` because cross-stack probes arrive with `Host: backend:8000`
(`backend/app/main.py:88-110`).

---

## 2. Backend Layers

Request path through the backend, outermost to innermost:

```
HTTP → [middleware stack] → router (api/v1) → DI deps (auth + feature guard)
     → service (*_service.py) → SQLAlchemy 2.0 async model → asyncpg → Postgres
                                          ▲
                              Pydantic schemas validate in/out
```

### Middleware stack (registration order = outer→inner construction)

From `backend/app/main.py` — Starlette executes the *last-added* middleware
**outermost**, so the registration order below is reversed at runtime:

| Added (main.py) | Middleware | Purpose |
|-----------------|-----------|---------|
| `:71` | `RequestLoggingMiddleware` | structured request/response logging |
| `:72` | `PerformanceMiddleware` | timing |
| `:73` | `QueryCounterMiddleware(threshold=8)` | N+1 / query-count guard |
| `:74` | `CachingHeadersMiddleware` | response cache-control |
| `:75` | `GZipMiddleware(min=500)` | compression |
| `:78` | `CORSMiddleware` | `cors_origins_list`, credentials on |
| `:113` | `_HealthExemptTrustedHost` | host-header guard, `/health` exempt |
| `:116` | `ProxyHeadersMiddleware(*)` | trust `X-Forwarded-Proto` for https redirects |
| `:119` | `FirstBootMiddleware` | initial-setup gate |
| `:127` | `CategoryRateLimitMiddleware` | slowapi categories; observe-only by default |
| `:140` | `SecurityHeadersMiddleware` | **added last → outermost**: CSP/HSTS/Permissions-Policy on every response incl. errors |

Note: nginx *also* stamps CSP/Permissions-Policy with `always` at the edge, which wins
for edge traffic; `SecurityHeadersMiddleware` is the source of truth for direct-to-backend
and a defense-in-depth layer (`main.py:131-138`).

Exception handlers register JSON-uniform responses for `APIError`, Starlette
`HTTPException`, and `RequestValidationError` (`main.py:53-67`).

### Router layer — `api/v1/registry.py` (single source of truth)

`register_all_routers(app, debug=)` is called once from `main.py:144`. It uses **lazy
imports** (`_lazy_import` caches `importlib.import_module`) so the ~hundreds of route
modules don't all load at process start — a deliberate startup-time optimization
(`registry.py:73-80`). Two route shapes coexist (detailed in `backend/ARCHITECTURE.md`):
domain **packages** (`catalog/`, `circulation/`, `auth/`, …, each merging sub-routers in
`__init__.py`) and flat legacy `*.py` modules. Every router mounts at `prefix="/api/v1"`.
Router-shadowing order matters: literal routes are mounted before any `/{id}` sibling
(see comments at `registry.py:136-139`, `:172-176`).

### Service layer — the *real* shape

`backend/app/services/` holds **~469 `.py` files**, the bulk being flat
`<domain>_service.py` modules (~338 top-level service files). The pattern is
predominantly **flat service modules**, *not* a pervasive service+repository+facade
stack:

- **Repositories**: only `services/repositories/` exists, with a single real repo
  (`po_repository.py`) — i.e. the repository pattern is **nascent, scoped to the
  purchase-order / acquisitions domain only**.
- **Facades**: exactly one (`po_facade_service.py`) — same domain.
- **Sub-packages** group the larger domains:
  `edi/`, `engagement/`, `federated_search/`, `import_service/`, `legal/`,
  `makerspace/`, `ncip/`, `notifications/`, `reports/`, `reversal/`, `schedulers/`,
  `search/`, `sip2/`.
- Largest flat clusters by name prefix: `board_*` (11), `patron_*` (9), `catalog_*` (8),
  `reading_*` (7), `unified_*` (6), `print_*` (5).

Takeaway: treat services as **mostly flat, single-responsibility modules** invoked
directly by routers; the repo/facade abstraction is an emerging pattern in one domain,
not a system-wide convention.

### Models / persistence

SQLAlchemy 2.0 **async** (asyncpg), sessions via the `get_db` dependency. Relationship
loading is eager (`selectinload`) — no lazy loading in async context; a startup
lazy-load guard is installed (`main.py:163`, `install_lazy_load_guard`). Pydantic schemas
(`app/schemas/`) sit between routers and services for request/response validation.

---

## 3. Request & Auth Flow

```
client ──(Authorization: Bearer <access JWT>)──► backend
   │                                                │
   │  401? ── frontend silently POSTs ──────────────┤
   │          /api/v1/auth/refresh (httpOnly cookie)│
   │  ◄── new access token ──────────────────────────┘
```

- **JWT** access tokens (PyJWT), short-lived: `ACCESS_TOKEN_EXPIRE_MINUTES=15`
  (`core/config.py:38`). Refresh tokens last `REFRESH_TOKEN_EXPIRE_DAYS=7` (`:39`),
  delivered as an **httpOnly cookie**. Signing supports key rotation:
  `JWT_SECRET_KEY` (+ `_PREVIOUS`) with a grace window
  `JWT_KEY_ROTATION_GRACE_HOURS=168` (`config.py:42-44`).
- **Dependency-injected auth**: `get_current_user` (in `api/v1/auth/helpers.py`) is
  imported by most routers; `get_optional_user` for endpoints that work signed-in or
  anonymous. Role checks via `require_admin()`/`require_staff()`/`check_staff_access()`
  (11-role hierarchy — see top-level doc).
- **Turnstile (Cloudflare)** gates public/sensitive auth endpoints —
  `auth/login.py`, `auth/registration.py`, `auth/password.py`, verified via
  `core/turnstile.py`; secret = `CF_TURNSTILE_SECRET` (`config.py:53`).
- **Frontend side**: `lib/api-client.ts` (hand-written `apiClient`) and the generated
  `api/generated/client.ts` (openapi-fetch) both inject the bearer token and run a
  **single-flight silent refresh** on 401 (10s timeout, refresh paths excluded to avoid
  loops). `API_BASE` defaults to `/api/v1`.

### Feature-flag gating (404, not 403)

Two coordinated layers:

- **Backend** — `api/v1/feature_guards.py`: a factory `_make_feature_guard(name, label)`
  builds `require_*_enabled` dependencies (60+ of them) that call
  `OrganizationFeaturesService.is_feature_enabled(db, name)` and raise **HTTP 404** when
  off (`feature_guards.py:19-35`). Applied either at the `app.include_router(...,
  dependencies=[Depends(require_X_enabled)])` call site in `registry.py` (e.g. all
  `indie_*` routers at `:150-157`) or on individual routers. A module-level
  `FEATURE_REGISTRY` accumulates `{key, label}` for introspection.
- **Frontend** — `components/RequireFeature.tsx` + `OrganizationFeaturesContext`: route
  trees in `components/AppRoutes.tsx` wrap feature-gated sections so the SPA hides UI for
  disabled features.

Flags toggle **live via Redis** (org-features service reads the toggle store), so no
redeploy is needed to enable/disable a module.

---

## 4. Cross-Cutting Concerns

| Concern | Where | Notes |
|---------|-------|-------|
| **Feature flags** | `feature_guards.py`, `OrganizationFeaturesService`, `RequireFeature.tsx` | 60+ guards; 404-gate backend, hide-UI frontend; live Redis toggle |
| **i18n** | `frontend/src/i18n/translations`, `I18nContext` | English always loaded as fallback; initial locale awaited before mount (`main.tsx:48-58`); `t()` supports a string `defaultValue` 2nd arg |
| **PII encryption** | `core/encryption.py`, validated at startup | **Fernet** (`cryptography`); `PII_ENCRYPTION_ENABLED=true` default, `PII_ENCRYPTION_KEY` (+ `_PREVIOUS` for rotation); startup validates config + warns on pending re-encryption (`main.py:166`, `:182-220`); separate `EVIDENCE_ENCRYPTION_KEY` for legal evidence |
| **Embeddings / semantic search** | see below | local Ollama, OpenAI-compatible; pgvector cosine distance |
| **Background jobs** | `services/schedulers/` (APScheduler) | ~50+ cron jobs (task target ~53); jobstore in Postgres via `SQLAlchemyJobStore`; `init_scheduler()` at startup (`main.py:171`) |
| **Pub/sub bus** | `services/floor_view_bus` | Redis-backed subscriber started/stopped on app lifecycle (`main.py:175`, shutdown `:240`) |
| **Sentry** | backend `setup_sentry()` (`main.py:35`); frontend `main.tsx:11-18` | frontend lazy-loaded (`@/lib/sentry-lazy`); traces 0.1 in prod |
| **Rate limiting** | `core/rate_limit.py` (slowapi) + `CategoryRateLimitMiddleware` | category middleware **observe-only by default** (`RATE_LIMIT_OBSERVE_ONLY=true`, `config.py:27`); set false to actually throttle |
| **Audit logging** | `services/operations_audit_service.py`, `board_audit_service.py`, `privacy_audit.py` | per-domain audit trails |
| **Observability** | OpenTelemetry tracing middleware (`app/middleware/tracing_middleware.py`) | FastAPI/SQLAlchemy/Redis/httpx instrumentation |
| **PII log scrubbing** | `app/middleware/pii_filter.py` | filters PII from logs |

### Embedding-provider reality (important — defaults are misleading)

The production embedding subsystem is **local**:

**General semantic search** — `services/semantic_search_service.py` +
`models/embeddings.py` (`TextEmbedding`, FAQ). It POSTs to a configurable
**OpenAI-compatible** endpoint using `settings.embedding_api_url` /
`embedding_model` (`semantic_search_service.py:35-36,59-62`). The **config.py defaults
look like OpenAI** (`EMBEDDING_API_URL=…api.openai.com…`, `text-embedding-3-small`,
1536-dim — `config.py:218-220`; `EMBEDDING_DIM` default 1536 in
`models/embeddings.py:60`), **but production env-overrides them to local Ollama**:
`docker-compose.prod.yml` sets
`EMBEDDING_API_URL=…/ollama…:11434/v1/embeddings`, `EMBEDDING_MODEL=nomic-embed-text`,
`EMBEDDING_DIMENSION=768`. Ollama exposes an OpenAI-compatible `/v1/embeddings`, so the
same client code talks to the **local** model. **No third-party AI call leaves the
box** in the reference deployment — the defaults are upstream placeholders, not the
live path.

> A second subsystem — the support-agent RAG embedder (`services/support_agent/`,
> `models/support_agent.py`, `Vector(768)`) — was **removed 2026-06-02**
> along with the only `anthropic` dependency; that path no longer exists.

Chat/LLM extraction (`ollama_service.py`, `policy_extraction.py`) likewise routes to
`OLLAMA_BASE_URL` with model `qwen2.5:3b` in prod (`compose:138-140`). Vector similarity
runs in Postgres via pgvector `cosine_distance` / `<=>`.

---

## 5. Deployment Topology

- **Compose project `l30`**, file `docker-compose.prod.yml`. Container names, ports, and
  volume names are pinned and warned against changing (`compose:6`).
- **Canonical network**: the override declares `l30_network` *without* a `name:`, so
  compose resolves it to **`l30_l30_network`** (`project=l30`). Forcing `name: l30_network`
  would split containers onto an orphan network and break nginx routing — explicit warning
  at `compose:329-339`. Verify network attachment after any backend recreate.
- **Backend deploy = image rebuild.** App code (`backend/app/`) is **baked into the
  image**; only `./backend/scripts:/app/scripts:ro` is bind-mounted (`compose:171`). So a
  code change requires `docker compose up -d --build l30-backend` — editing files in a
  running container is wiped on the next rebuild. Scripts can be hot-edited; app code
  cannot.
- **Frontend deploy = cp-into-container.** `npm run build` then copy `dist/` into the
  `l30-frontend` container (deploy is a `cp`, *not* a build step inside the container) —
  build first, then deploy, or you ship stale assets.
- **Manual deploy, no CI/auto-deploy.** Deploys are manual Docker operations. (CI
  workflows exist in `.github/workflows/` but are effectively dispatch-only / disabled for
  cost; do not rely on push-to-deploy.)
- **DB**: `pgvector/pgvector:pg16`, extensions + bootstrap seeded via
  `scripts/init-db.sql` / `init-bootstrap.sql` mounted into the entrypoint init dir
  (`compose:58-59`). Host port mapped to 5434 (prod) to avoid host-Postgres conflicts.
- **Backend container env** sets `TRUSTED_HOSTS=l30.org,www.l30.org,localhost,l30-nginx`
  (`compose:146`).

---

## 6. Caveats (read before trusting derived artifacts)

- **`openapi.json` is NOT committed at origin/main.** It is a *generated* artifact (the
  frontend `api/generated/schema.d.ts` and `client.ts` are produced from it). A clean
  worktree has **no** `openapi.json` on disk — `grep`/diff tooling that assumes it exists
  will false-negative. Regenerate from the running app or the build step; don't treat its
  absence as a contract break.
- **Alembic ships multiple concurrent heads.** The `backend/alembic/versions/` tree (~205
  revisions) routinely carries **>1 head**, reconciled via merge-revision files
  (`down_revision = (...)` tuple, ~5 present). This is the intended **merge-point pattern**,
  not corruption — expect to resolve heads at deploy, and add new migrations as merges
  rather than rewriting history.
- **Rate limiting is observe-only.** `RATE_LIMIT_OBSERVE_ONLY=true` by default — the
  category middleware classifies and logs `would_block` but enforces nothing until
  explicitly flipped. Don't assume throttling is active in the current phase.
- **Edge vs app security headers.** CSP / Permissions-Policy / X-Frame-Options etc. come
  from **both** nginx (`always`, wins at the edge) and `SecurityHeadersMiddleware`. Changing
  edge-visible headers means changing the nginx/Cloudflare layer, not just the middleware.
