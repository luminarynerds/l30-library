<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# Known Issues

This is an honest self-assessment of known technical debt and operational
risks. It helps contributors focus audits on gaps that still need attention.

## God Files

A handful of backend and frontend modules have grown past 1,000-2,000+ lines
and are on the refactor list — for example `api/v1/events.py`,
`api/v1/staff/patron_operations.py`, `api/v1/reading_programs.py`, and
`api/v1/learning.py` on the backend, and `StaffComputersPage.tsx`,
`StaffPatronsPage.tsx`, and `ConnectionGroupLifecycleModals.tsx` on the
frontend. They work and are tested, but several mix concerns that would split
cleanly — moderation/calendar bolted onto event CRUD, staff-only routes
interleaved with patron-facing ones, multiple modal workflows sharing one
page's open/close state.

Several of the largest past offenders have already been decomposed: `auth.py`,
`catalog.py`, `circulation.py`, `privacy.py`, `outreach.py`, and
`staff_fines.py` are now packages (directories of sub-modules) rather than
single files. The remainder are being split the same way over time. None of
this affects running the software.

Note: `api/generated/schema.d.ts` (~295K lines) is auto-generated from OpenAPI
and excluded from this list.

## Exception Handling

1,023 broad except Exception clauses exist throughout the backend. Zero bare except: clauses. The broad catches silently swallow specific errors and mask real problems.

This is assigned to another team but not yet started.

## Inline Styles

266 inline style={{}} occurrences in the frontend. Tailwind classes are preferred. These work but are inconsistent with the rest of the styling approach.

## Rate Limiting

Rate limiting (via slowapi) is integrated and ships **enabled** by default
(`rate_limit_enabled` / `RATE_LIMIT_ENABLED` defaults to `true` in
`app/core/config.py`) — but in **observe-only mode**:
`RATE_LIMIT_OBSERVE_ONLY` also defaults to `true`, so over-limit requests are
classified and logged (`would_block`) rather than rejected. Set
`RATE_LIMIT_OBSERVE_ONLY=false` to actually enforce the limits, after watching
the logs for false positives.

## Security History

This source release uses a fresh repository history. The private development
repository previously contained committed credentials; publishing that old
repository or its pull-request references is not the release process.

Scan the complete release history before publication, review each finding,
and keep real environment files, databases, uploads, and operator credentials
out of the repository. Test fixtures and UI storage keys can produce scanner
matches; those need specific review rather than broad exclusions being treated
as proof that no secrets exist.

## Delegated Work

The following items are assigned to another team. Not yet started.

- API client consolidation: Frontend has multiple patterns for making API calls. Needs consolidation around openapi-fetch.
- API directory reorganization: 173 route files in api/v1/. Some could be better grouped into subdirectories by domain.
- Broad exception handling: 1,023 except Exception clauses throughout the backend. Catch-all exception handlers that swallow errors silently. Needs targeted replacement with specific exception types.

## Redundant Abstractions

Some domains still have repetitive endpoint structures, overlapping helpers,
and more model coverage than the active product surface needs. Refactors should
reduce duplication while preserving tested behavior.

## Test Coverage

There are several hundred backend test files (pytest) and several hundred
frontend test files (Vitest). Coverage is broad but we have not fully
characterized its depth. We would love the team to evaluate whether these
tests are actually testing meaningful behavior or just hitting lines.

## What We Do Not Know

The above is everything we have identified ourselves. The real value of this audit is finding what we missed. Architecture problems, security holes, performance bottlenecks, patterns that will not scale. Tell us what you see.
