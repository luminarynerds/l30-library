<!--
  SPDX-FileCopyrightText: 2026 Luminary Nerds
  SPDX-License-Identifier: AGPL-3.0-or-later
-->
# L30 Dependency Inventory

> From manifests + lockfiles in a clean `origin/main` worktree.
> Backend: `backend/pyproject.toml` + `backend/uv.lock`.
> Frontend: `frontend/package.json` + lockfile.

## At a glance

| | Direct | Resolved (with transitives) |
|---|------:|------:|
| **Backend** (Python ≥3.11, `uv`) | 41 | 127 |
| **Frontend** (Node / Vite) | 28 runtime + 48 dev | — |

## Backend — runtime (`pyproject.toml`, 41 direct)

### Web framework & server
`fastapi>=0.109` · `uvicorn[standard]>=0.27` · `gunicorn>=21` ·
`python-multipart>=0.0.27` · `slowapi>=0.1.9` (rate limiting)

### Data & persistence
`sqlalchemy>=2.0.25` · `asyncpg>=0.29` (async PG driver) ·
`psycopg2-binary>=2.9.9` (sync/migrations) · `alembic>=1.13` · `mako>=1.3.12` ·
`pgvector>=0.4` (vector search) · `redis>=5.0.1` · `numpy>=1.21`

### Validation & config
`pydantic[email]>=2.5.3` · `pydantic-settings>=2.1` · `packaging>=24`

### Auth, crypto & security
`PyJWT>=2.12` · `bcrypt>=4.0.1` · `pyotp>=2.9` (TOTP/MFA) ·
`cryptography>=46.0.7` (Fernet PII encryption) ·
`nh3>=0.2.17` (HTML sanitization)

### Library / bibliographic domain
`pymarc>=5.0` (MARC21) · `rapidfuzz>=3.0` (fuzzy dedup/matching)

### HTTP / integrations
`httpx>=0.26` · `aiohttp>=3.9` · `aiofiles>=23` · `paramiko>=3.4`
(SSH/SFTP — EDI vendor transport) · `apscheduler>=3.10` (~50+ background jobs)

### Documents & media
`reportlab>=4.0` · `openpyxl>=3.1` (xlsx) · `python-pptx>=0.6.21` ·
`python-docx>=1.2` · `pypdf>=6.10.1` · `pikepdf>=10.0` · `pillow>=12.2` ·
`qrcode>=7.4` · `jinja2>=3.1.6` (templating)

### Observability / misc
`sentry-sdk>=1.40` · `python-json-logger>=2.0.7` · `python-dateutil>=2.8`

> Notable: AI inference is **fully local** (Ollama) — there is **no third-party
> AI SDK** in the dependency set. The lone external-AI package (`anthropic`) was
> removed 2026-06-02 with the AI support agent. `paramiko` exists for
> EDI SFTP, not general remote access.

## Frontend — runtime (`package.json`, 28)

### Core
`react ^18.2` · `react-dom ^18.2` · `react-router-dom ^6.21` — **React 18 /
Router 6, not 19/7.**

### Data & state
`@tanstack/react-query ^5.90` · `@tanstack/react-virtual ^3.13` ·
`openapi-fetch ^0.17` (typed API client)

### Rich text (TipTap 3)
`@tiptap/react` · `@tiptap/starter-kit` · `@tiptap/pm` ·
`@tiptap/extension-image` · `@tiptap/extension-link` (all `^3.22`)

### UI / viz / icons
`@radix-ui/react-dropdown-menu ^2.1` · `recharts ^3.6` · `lucide-react ^0.453` ·
`@tailwindcss/typography ^0.5` · `clsx ^2.1` · `react-hot-toast ^2.4` ·
`qrcode.react ^4.2`

### Maps
`leaflet ^1.9` · `react-leaflet ^4.2`

### Content & safety
`react-markdown ^9.1` · `markdown-it ^14.1` · `remark-gfm ^4.0` ·
`dompurify ^3.3` (XSS sanitization) · `focus-trap-react ^10.3` (a11y) ·
`date-fns ^3.0` · `@sentry/browser ^10.39` · `prop-types ^15.8`

## Frontend — dev/build (48)

### Build & bundling
`vite ^6.4` · `@vitejs/plugin-react ^4.2` · `typescript ^5.3` ·
`vite-plugin-compression2 ^2.5` (brotli/gzip) · `terser ^5.46` ·
`rollup-plugin-visualizer ^6.0` · `autoprefixer` · `postcss` · `tailwindcss ^3.4` ·
`sharp ^0.34` (image processing)

### Testing
`vitest ^4.0` · `@vitest/coverage-v8` · `@testing-library/{react,dom,jest-dom,user-event}` ·
`happy-dom ^20.8` · `msw ^2.12` (API mocking) · `@playwright/test ^1.58`

### Accessibility testing
`@axe-core/playwright` · `@axe-core/react` · `jest-axe` · `@types/jest-axe` ·
`eslint-plugin-jsx-a11y ^6.10` · `@storybook/addon-a11y` · `@lhci/cli`
(Lighthouse CI) · `linkinator` (link checking)

### Lint / codegen / analysis
`eslint ^9` · `typescript-eslint ^8` · `eslint-plugin-react-hooks ^7` ·
`eslint-plugin-react-refresh` · `knip ^6.14` (dead-code) · `ts-morph ^28` ·
`openapi-typescript ^7.13` (API type codegen) · `tsc-files`

### Storybook
`storybook ^8.6` + `@storybook/{react,react-vite,addon-essentials,addon-interactions,addon-links}` (all `^8.6`)

> Dependabot tracks ~10 open upgrade PRs; the Storybook 8→10 bump is flagged
> risky. React stays on 18 (not 19).

## How to drill down

```bash
# Backend: direct deps
python3 -c "import tomllib;print(*tomllib.load(open('backend/pyproject.toml','rb'))['project']['dependencies'],sep='\n')"
# Backend: resolved tree
grep -c "^name = " backend/uv.lock

# Frontend
cat frontend/package.json | python3 -c "import json,sys;d=json.load(sys.stdin);print(len(d['dependencies']),'runtime',len(d['devDependencies']),'dev')"
```
