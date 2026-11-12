#!/usr/bin/env node
/**
 * SPDX-FileCopyrightText: 2026 Luminary Nerds
 * SPDX-License-Identifier: AGPL-3.0-or-later
 */
/**
 * CI check: verify that the generated TypeScript API types are up to date
 * with the backend OpenAPI specification.
 *
 * Usage:
 *   node scripts/check-api-types-freshness.mjs
 *
 * Exit codes:
 *   0 — types are up to date
 *   1 — types are stale (regeneration needed)
 *
 * How it works:
 *   1. Runs openapi-typescript against the backend spec
 *   2. Compares the output to the committed schema.d.ts
 *   3. Fails if they differ (someone changed the backend without regenerating)
 *
 * Prerequisites:
 *   The backend openapi.json must already exist. In CI this is produced by:
 *     cd backend && DATABASE_URL=... SECRET_KEY=... python scripts/generate_openapi.py --format json
 */

import { execSync } from 'node:child_process'
import { readFileSync, existsSync, unlinkSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(__dirname, '..')
const backendSpec = resolve(frontendRoot, '..', 'backend', 'openapi.json')
const committedTypes = resolve(frontendRoot, 'src', 'api', 'generated', 'schema.d.ts')

// ---------------------------------------------------------------------------
// Preflight
// ---------------------------------------------------------------------------

if (!existsSync(backendSpec)) {
  console.error(
    '❌ backend/openapi.json not found.\n' +
    '   Run "npm run api:generate-spec" first (or generate it in CI).'
  )
  process.exit(1)
}

if (!existsSync(committedTypes)) {
  console.error(
    '❌ src/api/generated/schema.d.ts not found.\n' +
    '   Run "npm run api:generate-types" to create it.'
  )
  process.exit(1)
}

// ---------------------------------------------------------------------------
// Generate fresh types to a temp location and compare
// ---------------------------------------------------------------------------

const tmpOutput = resolve(frontendRoot, 'src', 'api', 'generated', '.schema.d.ts.check')

// Strip ALL leading block comments before comparing. The committed file has
// two (the SPDX header added by spdx_header.py, then the openapi-typescript
// banner); the freshly-generated file has only the banner. Stripping just the
// first block made the comparison banner-vs-content, so the check could never
// pass even with fresh types.
function stripLeadingBlockComments(text) {
  let prev
  do {
    prev = text
    text = text.replace(/^\/\*\*[\s\S]*?\*\/\n/, '')
  } while (text !== prev)
  return text
}

let exitCode = 1
try {
  execSync(
    `npx openapi-typescript ${backendSpec} -o ${tmpOutput}`,
    { cwd: frontendRoot, stdio: 'pipe' }
  )

  const committed = stripLeadingBlockComments(readFileSync(committedTypes, 'utf8'))
  const fresh = stripLeadingBlockComments(readFileSync(tmpOutput, 'utf8'))

  if (committed === fresh) {
    console.log('✅ API types are up to date with the backend spec.')
    exitCode = 0
  } else {
    console.error(
      '❌ API types are STALE — the backend spec has changed.\n' +
      '   Run "npm run api:generate" to regenerate, then commit the result.'
    )
    exitCode = 1
  }
} catch (err) {
  console.error('❌ Failed to generate fresh types for comparison:', err.message)
  exitCode = 1
} finally {
  // Clean up temp file before exiting (process.exit() skips finally blocks)
  try {
    unlinkSync(tmpOutput)
  } catch {
    // ignore — file may not exist if generation failed
  }
}

process.exit(exitCode)
