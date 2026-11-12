<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 Frontend Component Inventory

> React 18 + Vite + TypeScript + TailwindCSS SPA under `frontend/src/`.
> Structured map grouped by route area, component family, and shared
> primitives — not an exhaustive per-file list.

## At a glance

| Metric | Count | Location |
|--------|------:|----------|
| Page components | 788 | `src/pages/**/*.tsx` |
| Components | 1,082 | `src/components/**/*.tsx` |
| React contexts | 10 (+ `index.ts` barrel) | `src/contexts/` |
| Hooks | 86 | `src/hooks/` |
| Feature modules | 9 | `src/features/` |

## Routing

Entry: `src/main.tsx` → `App.tsx` → `components/AppRoutes.tsx`. Routes are
split into area files under `src/routes/`, code-split with **`lazyWithRetry`**
(`src/routes/*` — chunk-per-area lazy loading with stale-chunk retry):

| Route file | Area |
|------------|------|
| `public.tsx`    | Public site (home, about, accessibility, catalog browse) |
| `StaffRoutes.tsx` | Staff console (`/staff/*`) |
| `BoardRoutes.tsx` | Trustee/board portal (`/board/*`) |
| `IndieRoutes.tsx` | Indie authors / ebooks |
| `LearnRoutes.tsx` | Learning paths / courses |
| `catalog.tsx`, `genealogy.tsx`, `legal.tsx` | Domain route groups |
| `routeGuards.tsx`, `routeMap.ts` | Auth/role guards + central route map |

### Pages by cluster (top prefixes)

| Prefix | Pages | | Prefix | Pages |
|--------|------:|-|--------|------:|
| `Staff*`  | 59 | | `Home*`    | 5 |
| `Admin*`  | 46 | | `Event*`   | 5 |
| `Indie*`  | 12 | | `About*`   | 5 |
| `Genealogy*` | 6 | | `Board*`   | 4 |
| `Learn*`  | 5 | | `Legal*` / `Acquisition*` | 3 each |

(Remaining ~580 pages are domain-named without a shared prefix.)

## Component families (`src/components/<dir>/`)

~85 sub-directories group components by domain. Notable families:

- **Shared primitives:** `ui/` (design-system primitives), `shells/`
  (`AdminShell`, `AdminStaffShell` page chrome), `dialogs/`, `charts/`,
  `skeletons/`, `navigation/`, `header/`, `footer/`, `selector/`, `settings/`,
  `notifications/`.
- **Catalog/biblio:** `catalog/`, `cataloging/`, `bibframe/`, `linked-data/`,
  `collection/`, `shelf/`, `discover/`, `recommendations/`, `reading-lists/`.
- **Staff/ops:** `staff/`, `staff-picks/`, `staff-lost-damaged/`, `circulation/`,
  `acquisition/`, `reports/`, `annual-reports/`, `analytics/`, `strategic-admin/`,
  `admin/`, `closure-management/`, `shift-swap/`, `lifecycle/`, `link-health/`.
- **Governance/legal:** `board/`, `board-demo/`, `legal/`, `content-flags/`,
  `challenges/`, `banned-books/`, `ban-tracker/`, `law-enforcement/`,
  `advocacy/`, `review-responses/`, `room-reports/`.
- **Programs/community:** `events/`, `EventCalendarView/`, `programs/`,
  `attendance/`, `engagement/`, `family-tree/`, `learning/`, `learning-paths/`,
  `training/`, `training-pipeline/`, `rubrics/`, `book-clubs/`,
  `parent-onboarding/`, `onboarding/`.
- **Spaces/devices:** `rfid/`, `tech-booking/`, `tech-support/`, `databases/`,
  `print/`, `delivery/`, `marketing/`, `marketing-hub/`.
- **Safety/accessibility:** `neurodivergent/`, `nudges/`, `emergency-cascade/`,
  `medical-emergency/`, `patron-segmentation/`, `library-agents/`, `releases/`,
  `indie/`, `blog/`, `home/`, `about/`, `account/`, `register/`, `setup/`,
  `knowledge-base/`, `header-search/`, `CommandPalette/`.

### Feature modules (`src/features/`)
`accessibility`, `account`, `admin`, `computers`, `equipment`,
`federated-search`, `patron`, `printing`, `rooms` — self-contained
feature slices (components + logic co-located).

## Global state — contexts (`src/contexts/`)

| Context | Responsibility |
|---------|----------------|
| `AuthContext`            | Session, user, roles, token refresh |
| `BrandingContext`        | Runtime branding (inline-styles override CSS vars) |
| `OrganizationFeaturesContext` | Feature-flag availability |
| `PreferencesContext`     | Patron preferences (theme, defaults) |
| `EssentialsModeContext`  | Opt-in simplified UI mode |
| `AdvancedSearchContext`  | Advanced catalog search state |
| `OnboardingContext`      | Onboarding flow progress |
| `NudgeContext`           | Behavioral nudges |
| `PanicAlertContext`      | Emergency / panic-button alerting |
| `ToneContext`            | Tone/voice adaptation |

## Key shared patterns

- **`<RequireFeature>`** (`components/RequireFeature.tsx`) — frontend mirror of
  the backend `Depends(require_*)` flag gate.
- **`lazyWithRetry`** — every route area is a separate lazy chunk; entry-chunk
  hash stays stable when entry code is unchanged.
- **Shells** (`components/shells/`) — `AdminShell`/staff shells provide
  consistent page chrome (title, subtitle, icon, actions).
- **`ErrorBoundary`** + stale-chunk error handling for deploy-time chunk drift.
- **API access:** `src/lib/api-client` (typed via `openapi-fetch` /
  `openapi-typescript` codegen against the backend schema).

## Key libraries (runtime)

`react` 18 · `react-router-dom` 6 · `@tanstack/react-query` 5 (server state) ·
`@tanstack/react-virtual` (long lists) · `@tiptap/*` 3 (rich-text editor) ·
`recharts` 3 (charts) · `leaflet` + `react-leaflet` (maps) · `lucide-react`
(icons) · `dompurify` (sanitization) · `react-hot-toast` · `date-fns` ·
`focus-trap-react` (a11y) · `@radix-ui/react-dropdown-menu`. See
`DEPENDENCIES.md` for the full inventory.

## How to drill down

```bash
# Pages in an area
ls frontend/src/pages | grep -i staff

# What a route area mounts
grep -nE "lazyWithRetry|path=" frontend/src/routes/StaffRoutes.tsx

# Components in a family
ls frontend/src/components/cataloging/
```
