<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 API Endpoint Inventory

> Derived **from router code** (`@router.<method>` decorators under
> `backend/app/api/`), not from `openapi.json` — that file is a generated
> artifact and is **not committed at `origin/main`**, so it cannot be trusted as
> a source. All routes are mounted under the `/api/v1` prefix via
> `backend/app/api/v1/registry.py`.

## At a glance

| Metric | Count |
|--------|------:|
| Route operations (`@router.get/post/put/patch/delete`) | **4,263** |
| Flat router modules in `api/v1/*.py` | 294 (3,252 routes) |
| Domain sub-packages in `api/v1/*/` | 16 (1,011 routes) |

### By HTTP method

| Method | Count |
|--------|------:|
| GET    | 2,163 |
| POST   | 1,480 |
| DELETE |   222 |
| PUT    |   212 |
| PATCH  |   186 |

The GET-heavy, POST-heavy, low-PUT/PATCH profile reflects a
read-and-action-oriented surface (many list/detail reads + command-style POST
actions) rather than strict REST resource CRUD.

## Domain sub-packages (`api/v1/<dir>/`)

| Package | Routes | Scope |
|---------|------:|-------|
| `staff/`              | 271 | Staff console: cataloging, patron ops, knowledge base, holds, triage |
| `board/`              | 175 | Trustee/board portal: governance, COI, audit, terms |
| `legal/`              | 117 | Compliance, records requests, book challenges, law-enforcement |
| `catalog/`            |  67 | Public + staff catalog search, items, authorities |
| `school_reading/`     |  58 | School/teacher reading, family engagement |
| `acquisition/`        |  57 | Purchase orders, vendors, EDI |
| `staff_lost_damaged/` |  53 | Lost/damaged item workflows |
| `strategic/`          |  46 | Strategic/admin analytics |
| `privacy/`            |  40 | Patron privacy, consent, data export/erasure |
| `outreach/`           |  34 | Community outreach |
| `circulation/`        |  33 | Checkouts, holds, returns |
| `auth/`               |  26 | Login, refresh, OAuth, MFA |
| `staff_fines/`        |  20 | Fines & waivers |
| `setup/`              |  12 | First-run / install setup |
| `images/`             |   1 | Image proxy/serving |
| `_core/`              |   1 | Core/shared |

## Largest flat router modules

The bulk of the surface is ~294 single-file routers directly under `api/v1/`.
The biggest by route count:

| Module | Routes | | Module | Routes |
|--------|------:|-|--------|------:|
| `parent_onboarding.py`    | 88 | | `makerspace.py`           | 37 |
| `equipment.py`            | 56 | | `computers.py`            | 37 |
| `branches.py`            | 53 | | `print_notices.py`        | 36 |
| `immigrant_services.py`   | 48 | | `events.py`               | 35 |
| `genealogy_research.py`   | 48 | | `rfid.py`                 | 33 |
| `storytime.py`            | 46 | | `reading_programs.py`     | 33 |
| `staff_makerspace.py`     | 46 | | `professional_judgment.py`| 33 |
| `signage.py`              | 46 | | `program_planning.py`     | 31 |
| `learning.py`             | 42 | | `staff/patron_operations.py` | 30 |
| `volunteers.py`           | 40 | | `onboarding.py`           | 30 |
| `usage_statistics.py`     | 40 | | `database_subscriptions.py`  | 30 |
| `consortiums.py`          | 38 | | `staff/knowledge.py`      | 28 |

## Cross-cutting request handling

- **Mounting:** `registry.py` lazy-imports and `include_router`s every module
  under `/api/v1`. Shared dependency lists gate groups of routers.
- **Auth:** JWT bearer (`PyJWT`) via dependency injection; refresh tokens;
  public + login endpoints sit behind Cloudflare Turnstile.
- **Feature flags:** AI routers are registered with
  `_ai_deps = [Depends(require_ai_tools_enabled)]`; flags toggle **live** via
  Redis (no redeploy). Frontend mirrors this with `<RequireFeature>`.
- **Rate limiting:** `slowapi`. **Validation:** Pydantic v2 schemas
  (`app/schemas/`, 166 modules). **Errors/telemetry:** Sentry.

## How to drill down

```bash
# Every route in a module, with method + path
grep -nE "@router\.(get|post|put|patch|delete)" backend/app/api/v1/staff/cataloging.py

# Count routes in a sub-package
grep -rEc "@router\.(get|post|put|patch|delete)" backend/app/api/v1/board/

# How a router is mounted / what gates it
grep -n "include_router\|require_" backend/app/api/v1/registry.py

# Regenerate a fresh openapi.json (it is NOT in git)
docker exec l30-backend python -c "import json,app.main as m; print(len(m.app.openapi()['paths']))"
```
