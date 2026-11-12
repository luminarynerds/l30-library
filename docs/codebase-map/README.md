<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 Codebase Map

Structural reference map of the L30 codebase, prepared from a clean
`origin/main` worktree on 2026-06-01 and refreshed on 2026-06-02.

Grouped-with-counts-and-drill-down, not exhaustive enumeration — they describe
shape and where to look, and link out to the existing narrative docs rather than
duplicating them.

| Doc | Covers |
|-----|--------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System topology, backend layers, request/auth flow, cross-cutting concerns, deploy topology |
| [DATABASE.md](DATABASE.md) | ~253 model modules / ~861 ORM classes grouped by domain, alembic/migrations, conventions |
| [API.md](API.md) | ~4,263 route operations by method, domain sub-package, and largest routers |
| [COMPONENTS.md](COMPONENTS.md) | 788 pages / 1,082 components / 10 contexts / 86 hooks, routing & shared patterns |
| [DEPENDENCIES.md](DEPENDENCIES.md) | Backend (41 direct / 127 resolved) + frontend (28 runtime / 48 dev) inventory |

## Related existing docs (not duplicated here)

- `ARCHITECTURE.md`, `DESIGN.md`, `FEATURES.md`, `PRODUCT.md` (repo root) — high-level overviews
- `docs/l30-architecture-brief.md` — privacy / cataloging / standards brief
- `backend/ARCHITECTURE.md`, `backend/docs/` — backend conventions + feature-specific guides
  (`MODEL_CONVENTIONS.md`, `QUICK_REFERENCE.md`, `event-collection-architecture.md`)

## Caveats baked into these maps

- `backend/openapi.json` is a **generated artifact, not committed** at `origin/main` — the API inventory is derived from router code instead.
- Alembic uses a **merge-point pattern**; main can transiently carry multiple heads during parallel waves, reconciled by `*_mergepoint` revisions (currently converged to a single head, `staff_kb_summary_001`).
- The backend image **bakes** `app/` + `alembic/`; schema/code changes require a rebuild.
- Prod data has a known **reseeded system-id divergence** (see ops notes); these maps describe code structure, not live data state.
- Counts are code-authoritative as of `origin/main` HEAD `d559910c7` (2026-06-02); they drift as the codebase changes.
